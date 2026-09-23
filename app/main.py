from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import numpy as np
from astropy.coordinates import AltAz, SkyCoord, get_body, get_sun
from astropy.time import Time
import astropy.units as u

from fastapi import Depends, File, FastAPI, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from .alternatives import find_alternatives
from .astronomy import compute_catalog_geometry, compute_geometry, format_ra_dec, iers_status
from .catalog import BUILTIN_CATALOGUES, installed_catalogue, resolve_source, CatalogError, CatalogCollection, Source, TemporaryCatalog, catalog, enrichment_store, temporary_catalogues
from .gaia import GaiaQueryError, query_gaia_stars
from .config import (
    BASE_DIR,
    CAPABILITIES,
    COORDINATE_FRAME_LABEL,
    DEFAULT_DISPLAY_COORDINATE_FRAME,
    DISPLAY_COORDINATE_FRAMES,
    DEFAULT_PLANNER_CONSTRAINT_VALUES,
    FOV_DIAMETER_DEG,
    FOV_RADIUS_DEG,
    GEOMETRY_ONLY,
    LACT_TELESCOPE,
    SITE_METADATA,
    TelescopeConfig,
    custom_telescope,
    SITE_TIMEZONE,
    SITE_TIMEZONE_NAME,
)
from .plotting import render_window_plot
from .schemas import AlternativeWindowRequest, ConstraintSet, SkyRequest, WindowRequest
from .sky_map import render_all_sky_svg, render_local_fov_svg
from .status import source_status
from .targets import normalise_temporary_target_name
from .windows import calculate_catalogue_windows, calculate_windows

app = FastAPI(
    title="Skyward Astronomical Observation Support Platform",
    version="2.1.20260924",
    description="LAN-only geometry planning prototype with a current LACT adapter and extensible catalogue/display interfaces.",
    docs_url=None,
    redoc_url=None,
)
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=5)
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


def _resolve_catalogue(catalog_token: Optional[str] = None):
    """Return the reviewed catalogue or a short-lived in-memory CSV upload."""
    if not catalog_token or catalog_token == catalog.identifier:
        return catalog
    try:
        return installed_catalogue(catalog_token) if catalog_token in BUILTIN_CATALOGUES else temporary_catalogues.get(catalog_token)
    except (KeyError, CatalogError) as exc:
        raise ValueError(str(exc)) from exc


def _resolve_catalogues(catalog_token: Optional[str] = None, catalog_tokens: Optional[str] = None):
    raw = catalog_tokens if catalog_tokens is not None else catalog_token
    tokens = [item.strip() for item in (raw or "").split(",") if item.strip()]
    selected = [catalog] if raw is None else []
    for token in tokens:
        if token == "gaia-dr3":
            continue
        if token == catalog.identifier:
            if catalog not in selected:
                selected.append(catalog)
        else:
            selected.append(_resolve_catalogue(token))
    return selected


def _resolve_target_identity(identity, catalog_token=None, catalog_tokens=None):
    """Keep legacy single-upload numeric rows without reinterpreting new keys.

    A singular token and no plural selection is the historical request-scoped
    numeric API. Explicit plural selection is a display layer only. Once a
    stable key/global index is returned, clients should always use that value.
    """
    if isinstance(identity, str) and ":" in identity:
        if len(identity) > 256:
            raise ValueError("source_key must not exceed 256 characters")
        return resolve_source(identity)
    index = int(identity)
    if catalog_token and catalog_tokens is None and catalog_token != "2lhaaso":
        table = _resolve_catalogue(catalog_token)
        try:
            return table.get(index)
        except KeyError:
            for source in table.sources:
                if source.original_row == index:
                    return source
            raise KeyError(f"Unknown source index {index} in catalogue {catalog_token}")
    return resolve_source(index)


def _catalogue_collection(catalogues):
    return CatalogCollection(catalogues)


def _catalogue_metadata(selected) -> dict:
    """Expose selected-table provenance without exposing operator upload bytes."""
    return {
        "token": getattr(selected, "token", ""),
        "identifier": getattr(selected, "identifier", getattr(selected, "token", "upload")),
        "provenance": getattr(selected, "provenance", {}),
        "label": selected.label,
        "display": getattr(selected, "display", {}),
        "sha256": selected.sha256,
        "count": len(selected.sources),
        "temporary": isinstance(selected, TemporaryCatalog),
    }


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_optional_float(value: Optional[str]) -> Optional[float]:
    if value is None or not value.strip():
        return None
    return float(value)


def _parse_optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or not value.strip():
        return None
    return int(value)


def _human_reason_text(reasons: list[str] | str) -> str:
    """Format stable reason codes for server-rendered, no-JavaScript fallback.

    JSON responses retain machine-readable codes. HTML must remain readable
    before the local client applies its bilingual translations, so this helper
    deliberately replaces underscore codes with concise human wording.
    """
    if isinstance(reasons, str):
        values = [reasons]
    else:
        values = list(reasons)
    conditions = {
        "target_above_horizon": "target above horizon",
        "target_inside_current_fov": "target inside current FoV",
        "sun_altitude": "Sun altitude",
        "moon_separation": "Moon separation",
        "target_min_zenith": "minimum target zenith angle",
        "target_max_zenith": "maximum target zenith angle",
        "extension_inside_fov": "extension inside FoV",
        "extension_inside_current_fov": "extension inside current FoV",
        "extension_above_horizon": "extension above horizon",
        "extension_max_zenith": "extension within horizon limit",
        "minimum_window": "minimum continuous window",
    }

    def condition(value: str) -> str:
        return conditions.get(value, value.replace("_", " "))

    def one(value: str) -> str:
        if value == "all_enabled_geometry_conditions_pass":
            return "All enabled geometry conditions pass"
        if value == "range_start":
            return "Requested-range start"
        if value == "range_end":
            return "Requested-range end"
        if value == "constraint_boundary":
            return "Constraint boundary"
        if value.startswith("became_valid_after: "):
            return "Became valid after: " + ", ".join(
                condition(item) for item in value[20:].split(", ")
            )
        if value.startswith("became_invalid_after: "):
            return "Became invalid after: " + ", ".join(
                condition(item) for item in value[22:].split(", ")
            )
        if value == "center_cannot_hold_for_minimum_window":
            return "Target centre: minimum continuous window"
        if value == "extension_cannot_hold_for_minimum_window":
            return "Source edge: minimum continuous window"
        if value.startswith("center_"):
            return "Target centre: " + condition(value[7:])
        aliases = {
            "extension_edge_exceeds_fov": "extension_inside_fov",
            "extension_edge_exceeds_current_fov": "extension_inside_current_fov",
            "extension_edge_below_horizon": "extension_above_horizon",
            "extension_edge_exceeds_horizon_limit": "extension_max_zenith",
        }
        if value in aliases:
            return "Source edge: " + condition(aliases[value])
        if value.startswith("extension_edge_"):
            return "Source edge: " + condition(value[15:])
        return condition(value)

    return " · ".join(one(value) for value in values if value) or "—"


templates.env.globals["human_reason_text"] = _human_reason_text


def _parse_form_datetime(
    value: str,
    display_timezone: Optional[str],
    observer_timezone=SITE_TIMEZONE,
) -> datetime:
    """Interpret a browser ``datetime-local`` value in its selected display zone.

    HTML datetime-local values deliberately have no offset.  The LAN site uses
    Beijing time by default, while the header also permits an explicit UTC view.
    Keeping this conversion at the HTTP boundary prevents a UTC screen from
    being silently reinterpreted as Asia/Shanghai by the domain model.
    """
    # Python 3.9's datetime.fromisoformat does not accept the trailing ``Z``
    # emitted by the API/window serializer.  Normalise it before parsing so a
    # result-page theme/timezone refresh preserves the exact UTC instant.
    normalized = value[:-1] + "+00:00" if value.endswith(("Z", "z")) else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is not None:
        return parsed
    return parsed.replace(
        tzinfo=timezone.utc if display_timezone == "utc" else observer_timezone
    )


def _observer_timezone(telescope: TelescopeConfig):
    """Use the selected observatory offset for local planner wall-clock input."""
    return timezone(timedelta(hours=telescope.timezone_offset_hours))


def _local_input(value: datetime, observer_timezone=SITE_TIMEZONE) -> str:
    return value.astimezone(observer_timezone).strftime("%Y-%m-%dT%H:%M")


def _local_iso(value: datetime, observer_timezone=SITE_TIMEZONE) -> str:
    return value.astimezone(observer_timezone).isoformat()


def _normalise_plot_theme(value: Optional[str], display_theme: str) -> str:
    """Select a safe server-side palette without changing the user preference.

    ``display_theme`` deliberately retains the operator's choice (including
    ``auto``) for localStorage and future refreshes.  Browsers additionally
    submit their currently resolved light/dark palette through ``plot_theme``
    so Matplotlib can render an SVG that matches the active system theme.
    A non-JavaScript form submission has no resolved palette, for which light
    is the deterministic fallback unless the explicit preference is dark.
    """
    if value in {"light", "dark"}:
        return value
    return "dark" if display_theme == "dark" else "light"


def _canonical_form_time(
    value: str, display_timezone: Optional[str], observer_timezone=SITE_TIMEZONE
) -> str:
    """Return a UTC ISO value for client-side date controls, or an empty string.

    Validation rerenders can occur after an unrelated invalid field.  Preserve
    valid start/end instants in canonical UTC form so switching the display
    zone after that rerender never shifts the planner by eight hours.
    """
    try:
        return _parse_form_datetime(value, display_timezone, observer_timezone).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        return ""




def _telescope_from_form(
    telescope_mode: Optional[str],
    custom_longitude_deg: Optional[str] = None,
    custom_latitude_deg: Optional[str] = None,
    custom_altitude_m: Optional[str] = None,
    custom_timezone_offset_hours: Optional[str] = None,
    custom_fov_diameter_deg: Optional[str] = None,
) -> TelescopeConfig:
    """Resolve LACT or one non-persistent WGS-84 custom observatory."""
    mode = telescope_mode or "lact"
    if mode == "lact":
        return LACT_TELESCOPE
    if mode != "custom":
        raise ValueError("select LACT or a custom telescope")
    raw = {
        "longitude": custom_longitude_deg,
        "latitude": custom_latitude_deg,
        "altitude": custom_altitude_m,
        "timezone": custom_timezone_offset_hours,
        "FoV": custom_fov_diameter_deg,
    }
    if any(value is None or not value.strip() for value in raw.values()):
        raise ValueError("all custom telescope fields must be supplied")
    return custom_telescope(
        float(custom_longitude_deg),
        float(custom_latitude_deg),
        float(custom_altitude_m),
        float(custom_timezone_offset_hours),
        float(custom_fov_diameter_deg),
    )


def _telescope_query(
    telescope_mode: str = Query("lact"),
    custom_longitude_deg: Optional[float] = Query(None, ge=-180, le=180),
    custom_latitude_deg: Optional[float] = Query(None, ge=-90, le=90),
    custom_altitude_m: Optional[float] = Query(None, ge=-500, le=10000),
    custom_timezone_offset_hours: Optional[float] = Query(None, ge=-12, le=14),
    custom_fov_diameter_deg: Optional[float] = Query(None, gt=0, le=180),
) -> TelescopeConfig:
    """FastAPI dependency mirroring the non-persistent planner configuration."""
    if telescope_mode == "lact":
        return LACT_TELESCOPE
    if telescope_mode != "custom" or None in {
        custom_longitude_deg, custom_latitude_deg, custom_altitude_m,
        custom_timezone_offset_hours, custom_fov_diameter_deg,
    }:
        raise HTTPException(status_code=422, detail="complete custom telescope configuration is required")
    try:
        return custom_telescope(
            custom_longitude_deg, custom_latitude_deg, custom_altitude_m,
            custom_timezone_offset_hours, custom_fov_diameter_deg,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

def _constraints_from_values(
    sun_max_altitude_deg: Optional[str] = None,
    moon_min_separation_deg: Optional[str] = None,
    target_min_zenith_deg: Optional[str] = None,
    target_max_zenith_deg: Optional[str] = None,
    minimum_window_seconds: Optional[str] = None,
    *,
    require_all: bool = False,
) -> ConstraintSet:
    # Form values arrive as strings. Normalise here so HTML form and API share
    # one domain model. The planner itself requires all five values explicitly.
    raw_values = {
        "sun_max_altitude_deg": sun_max_altitude_deg,
        "moon_min_separation_deg": moon_min_separation_deg,
        "target_min_zenith_deg": target_min_zenith_deg,
        "target_max_zenith_deg": target_max_zenith_deg,
        "minimum_window_seconds": minimum_window_seconds,
    }
    if require_all and any(value is None or not value.strip() for value in raw_values.values()):
        raise ValueError("all planning constraints must be supplied")
    return ConstraintSet(
        sun_max_altitude_deg=_parse_optional_float(sun_max_altitude_deg),
        moon_min_separation_deg=_parse_optional_float(moon_min_separation_deg),
        target_min_zenith_deg=_parse_optional_float(target_min_zenith_deg),
        target_max_zenith_deg=_parse_optional_float(target_max_zenith_deg),
        minimum_window_seconds=_parse_optional_int(minimum_window_seconds),
    )


def _planner_target(
    source_selection: str,
    region_ra_deg: Optional[str],
    region_dec_deg: Optional[str],
    region_radius_deg: Optional[str],
    region_name: Optional[str] = None,
    selected_catalogue=catalog,
    catalog_token: Optional[str] = None,
    catalog_tokens: Optional[str] = None,
) -> tuple[str, Optional[Source], bool]:
    """Resolve one immutable catalogue or transient operator-defined target.

    Browser-created targets are intentionally not catalogued.  Their provided
    name is retained for the result page and TXT plan, while an empty field is
    deterministically converted to a ``TMP JHHMM±DDMM`` coordinate name.
    ``none`` is accepted only for backwards-compatible API/form submissions;
    it is not exposed in the current user interface.
    """
    if source_selection == "none":
        return "Current LACT FoV (zenith pointing)", None, True
    if source_selection == "region":
        ra = _parse_optional_float(region_ra_deg)
        dec = _parse_optional_float(region_dec_deg)
        radius = _parse_optional_float(region_radius_deg)
        if ra is None or dec is None or radius is None:
            raise ValueError("region RA, Dec and radius are required")
        if not (0.0 <= ra < 360.0 and -90.0 <= dec <= 90.0 and 0.0 < radius <= 90.0):
            raise ValueError("region coordinates or radius are outside the allowed range")
        name = normalise_temporary_target_name(region_name, ra, dec)
        return (
            f"{name}: RA {ra:.3f}°, Dec {dec:+.3f}°, radius {radius:.3f}°",
            Source(-1, name, radius, 0.0, ra, dec, 0.0, 0.0, 0.0),
            False,
        )
    try:
        source = _resolve_target_identity(source_selection, catalog_token, catalog_tokens)
        return source.display_name, source, False
    except (ValueError, KeyError) as exc:
        raise ValueError("select a catalogue source, current LACT FoV, or custom region") from exc


def _highlighted_window_fov_sources(
    sources, windows, telescope: TelescopeConfig, target: Source
) -> list[int]:
    """Return catalogue sources entering a target-centred tracked FoV.

    During every full-footprint target window LACT tracks the selected target,
    so this uses source-to-target separation rather than today's placeholder
    zenith pointing. Fixed J2000 catalogue separations are time-independent.
    """
    if not windows:
        return []
    target_coordinate = SkyCoord(ra=target.ra, dec=target.dec, unit="deg", frame="fk5")
    rows = list(sources)
    coordinates = SkyCoord(ra=[item.ra for item in rows], dec=[item.dec for item in rows], unit="deg", frame="fk5")
    separations = target_coordinate.separation(coordinates).deg
    return [item.index for item, separation in zip(rows, separations) if item.index != target.index and float(separation) <= telescope.fov_radius_deg]

def _current_fov_constraints(
    constraints: ConstraintSet, telescope: TelescopeConfig = LACT_TELESCOPE
) -> ConstraintSet:
    """Limit legacy bulk planning to the selected telescope current FoV radius."""
    current_limit = constraints.target_max_zenith_deg
    fov_limit = telescope.fov_radius_deg if current_limit is None else min(current_limit, telescope.fov_radius_deg)
    return constraints.model_copy(update={"target_max_zenith_deg": fov_limit})

def _query_constraints(
    sun_max_altitude_deg: Optional[float] = Query(None, ge=-90, le=-15),
    moon_min_separation_deg: Optional[float] = Query(None, ge=0, le=180),
    target_min_zenith_deg: Optional[float] = Query(None, ge=0, le=90),
    target_max_zenith_deg: Optional[float] = Query(None, ge=0, le=90),
    minimum_window_seconds: Optional[int] = Query(None, ge=0, le=2_678_400),
) -> ConstraintSet:
    # Cross-field validation happens in ConstraintSet. Convert its Pydantic
    # errors to JSON-safe HTTP 422 details for GET query consumers.
    try:
        return ConstraintSet(
            sun_max_altitude_deg=sun_max_altitude_deg,
            moon_min_separation_deg=moon_min_separation_deg,
            target_min_zenith_deg=target_min_zenith_deg,
            target_max_zenith_deg=target_max_zenith_deg,
            minimum_window_seconds=minimum_window_seconds,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": list(error.get("loc", ())),
                    "msg": error["msg"],
                    "type": error["type"],
                }
                for error in exc.errors()
            ],
        ) from exc


def _base_context(
    request: Request, telescope: TelescopeConfig = LACT_TELESCOPE
) -> Dict[str, Any]:
    return {
        # The shared template contract avoids duplicating immutable scientific
        # configuration in every route and keeps page/API provenance aligned.
        "request": request,
        "site": {
            "longitude_deg": telescope.longitude_deg,
            "latitude_deg": telescope.latitude_deg,
            "altitude_m": telescope.altitude_m,
            "timezone": telescope.timezone_label,
            "source": telescope.source,
        },
        "telescope": telescope,
        "fov_diameter": telescope.fov_diameter_deg,
        "fov_radius": telescope.fov_radius_deg,
        "frame_label": COORDINATE_FRAME_LABEL,
        "catalog_hash": catalog.sha256,
        "catalog_count": len(catalog.sources),
        "catalogue": _catalogue_metadata(catalog),
        "geometry_only": GEOMETRY_ONLY,
        "timezone_name": SITE_TIMEZONE_NAME if telescope is LACT_TELESCOPE else telescope.timezone_label,
    }


def _source_detail(
    source_index: int,
    at_time: datetime,
    constraints: ConstraintSet,
    telescope: TelescopeConfig = LACT_TELESCOPE,
    selected_catalogue=catalog,
    *,
    enforce_current_pointing: bool = False,
    catalog_token: Optional[str] = None,
    catalog_tokens: Optional[str] = None,
    nominal_radius_deg: Optional[float] = None,
) -> dict:
    try:
        source = _nominal_source(_resolve_target_identity(source_index, catalog_token, catalog_tokens), nominal_radius_deg)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Keep the legacy query parameter for old clients, but do not apply it:
    # this release has no authoritative live pointing telemetry, so source
    # observability is always evaluated from the shared geometry-only rule.
    del enforce_current_pointing
    status = source_status(
        source, at_time, constraints, telescope,
        enforce_current_pointing=False,
    )
    # Source records remain raw, but this response adds user-facing coordinate
    # formats, current geometry and only locally curated enrichment fields.
    return {
        **source.to_dict(),
        **format_ra_dec(source),
        "coordinate_frame": COORDINATE_FRAME_LABEL,
        "status": status.to_dict(),
        "enrichment": enrichment_store.get(source.original_row if source.original_row is not None else source.index) if source.catalogue_id == "2lhaaso" and source.source_type == "catalogue" else (source.notes or {"verification_status": "not_available_for_temporary_catalogue"}),
        "notes": source.notes or {},
        "geometry_only": True,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    now = _now_utc()
    telescope = LACT_TELESCOPE
    constraints = ConstraintSet(**DEFAULT_PLANNER_CONSTRAINT_VALUES)
    sky_svg, snapshot = render_all_sky_svg(catalog.sources, now, constraints, telescope=telescope, language="zh")
    start = now.replace(second=0, microsecond=0)
    end = start + timedelta(hours=24)
    context = _base_context(request, telescope)
    context.update(
        {
            "sources": catalog.sources,
            "catalogue": _catalogue_metadata(catalog),
            "sky_svg": sky_svg,
            "snapshot": snapshot,
            "now_local": now.astimezone(_observer_timezone(telescope)),
            "default_start": _local_input(start, _observer_timezone(telescope)),
            "default_end": _local_input(end, _observer_timezone(telescope)),
            "default_start_utc": start.isoformat().replace("+00:00", "Z"),
            "default_end_utc": end.isoformat().replace("+00:00", "Z"),
            "selected_source": None,
            "form_values": {
                "source_index": "region",
                "telescope_mode": "lact",
                "custom_longitude_deg": "",
                "custom_latitude_deg": "",
                "custom_altitude_m": "",
                "custom_timezone_offset_hours": "",
                "custom_fov_diameter_deg": "",
                "region_name": "",
                "region_ra_deg": "",
                "region_dec_deg": "",
                "region_radius_deg": "",
                "sun_max_altitude_deg": "-18",
                "moon_min_separation_deg": "30",
                "target_min_zenith_deg": "0",
        "target_max_zenith_deg": "60",
        "minimum_window_seconds": "0",
        "display_theme": "auto",
        "plot_theme": "light",
        "display_timezone": "local",
            },
            "error": None,
        }
    )
    return templates.TemplateResponse(request, "index.html", context)


@app.post("/result", response_class=HTMLResponse)
def result_page(
    request: Request,
    source_index: str = Form("region"),
    source_key: Optional[str] = Form(None),
    nominal_radius_deg: Optional[float] = Form(None, gt=0, le=90),
    start_time: str = Form(...),
    end_time: str = Form(...),
    region_ra_deg: Optional[str] = Form(None),
    region_dec_deg: Optional[str] = Form(None),
    region_radius_deg: Optional[str] = Form(None),
    region_name: Optional[str] = Form(None),
    catalog_token: Optional[str] = Form(None),
    catalog_tokens: Optional[str] = Form(None),
    telescope_mode: Optional[str] = Form(None),
    custom_longitude_deg: Optional[str] = Form(None),
    custom_latitude_deg: Optional[str] = Form(None),
    custom_altitude_m: Optional[str] = Form(None),
    custom_timezone_offset_hours: Optional[str] = Form(None),
    custom_fov_diameter_deg: Optional[str] = Form(None),
    display_theme: Optional[str] = Form(None),
    plot_theme: Optional[str] = Form(None),
    display_timezone: Optional[str] = Form(None),
    sun_max_altitude_deg: Optional[str] = Form(None),
    moon_min_separation_deg: Optional[str] = Form(None),
    target_min_zenith_deg: Optional[str] = Form(None),
    target_max_zenith_deg: Optional[str] = Form(None),
    minimum_window_seconds: Optional[str] = Form(None),
) -> HTMLResponse:
    """Render either one selected target or all sources crossing the fixed zenith FoV."""
    source_index = source_key or source_index
    telescope: TelescopeConfig = LACT_TELESCOPE
    selected_catalogue = catalog
    observer_timezone = _observer_timezone(telescope)
    context = _base_context(request, telescope)
    # Keep invalid custom telescope values inside the normal validation rerender
    # path rather than raising an unhandled error before template context exists.
    try:
        telescope = _telescope_from_form(
            telescope_mode, custom_longitude_deg, custom_latitude_deg, custom_altitude_m,
            custom_timezone_offset_hours, custom_fov_diameter_deg,
        )
        observer_timezone = _observer_timezone(telescope)
        context = _base_context(request, telescope)
        selected_catalogue = _catalogue_collection(_resolve_catalogues(catalog_token, catalog_tokens))
    except ValueError as telescope_error:
        telescope_error_message = str(telescope_error)
    form_values = {
        "source_index": source_index,
        "source_key": source_key or (source_index if ":" in source_index else ""),
        "nominal_radius_deg": nominal_radius_deg if nominal_radius_deg is not None else "",
        "catalog_token": catalog_token or "",
        "catalog_tokens": catalog_tokens if catalog_tokens is not None else (catalog_token if catalog_token is not None else "2lhaaso"),
        "start_time": start_time,
        "end_time": end_time,
        "planner_start_utc": _canonical_form_time(start_time, display_timezone, observer_timezone),
        "planner_end_utc": _canonical_form_time(end_time, display_timezone, observer_timezone),
        "telescope_mode": telescope_mode or "lact",
        "custom_longitude_deg": custom_longitude_deg or "",
        "custom_latitude_deg": custom_latitude_deg or "",
        "custom_altitude_m": custom_altitude_m or "",
        "custom_timezone_offset_hours": custom_timezone_offset_hours or "",
        "custom_fov_diameter_deg": custom_fov_diameter_deg or "",
        "region_ra_deg": region_ra_deg or "",
        "region_dec_deg": region_dec_deg or "",
        "region_radius_deg": region_radius_deg or "",
        "region_name": region_name or "",
        "display_theme": display_theme if display_theme in {"auto", "light", "dark"} else "auto",
        "plot_theme": "light",
        "display_timezone": "utc" if display_timezone == "utc" else "local",
        "sun_max_altitude_deg": sun_max_altitude_deg or "",
        "moon_min_separation_deg": moon_min_separation_deg or "",
        "target_min_zenith_deg": target_min_zenith_deg or "",
        "target_max_zenith_deg": target_max_zenith_deg or "",
        "minimum_window_seconds": minimum_window_seconds or "",
    }
    form_values["plot_theme"] = _normalise_plot_theme(plot_theme, form_values["display_theme"])
    try:
        if "telescope_error_message" in locals():
            raise ValueError(telescope_error_message)
        constraints = _constraints_from_values(
            sun_max_altitude_deg, moon_min_separation_deg, target_min_zenith_deg,
            target_max_zenith_deg, minimum_window_seconds, require_all=True,
        )
        request_model = WindowRequest(
            source_index=int(source_index) if source_index not in {"none", "region"} and ":" not in source_index else None,
            source_key=source_index if ":" in source_index else None,
            nominal_radius_deg=nominal_radius_deg,
            all_sources=source_index == "none",
            region_ra_deg=_parse_optional_float(region_ra_deg) if source_index == "region" else None,
            region_dec_deg=_parse_optional_float(region_dec_deg) if source_index == "region" else None,
            region_radius_deg=_parse_optional_float(region_radius_deg) if source_index == "region" else None,
            region_name=(region_name.strip() if region_name and region_name.strip() else None) if source_index == "region" else None,
            start_time=_parse_form_datetime(start_time, display_timezone, observer_timezone),
            end_time=_parse_form_datetime(end_time, display_timezone, observer_timezone),
            constraints=constraints,
        )
        form_values["planner_start_utc"] = request_model.start_utc.isoformat().replace("+00:00", "Z")
        form_values["planner_end_utc"] = request_model.end_utc.isoformat().replace("+00:00", "Z")
        target_label, source, all_sources = _planner_target(
            source_index, region_ra_deg, region_dec_deg, region_radius_deg, region_name, selected_catalogue,
            catalog_token, catalog_tokens,
        )
        _validate_iers_range(request_model.start_utc, request_model.end_utc)
        if all_sources:
            # In the current no-telemetry phase, LACT points at zenith. Restrict
            # every catalogue computation to the 4.15 degree FoV radius.
            fov_constraints = _current_fov_constraints(constraints, telescope)
            # "All sources" means sources inside the current LACT FoV at the
            # requested start instant, not a costly all-night scan of every catalogue row.
            # The displayed real-time pointing is presently fixed at zenith.
            _, start_snapshot = render_all_sky_svg(
                selected_catalogue.sources, request_model.start_utc, constraints, telescope=telescope, language="zh"
            )
            candidate_indexes = [
                item["index"] for item in start_snapshot["sources"]
                if item["geometry"]["target_pointing_separation_deg"] <= telescope.fov_radius_deg
            ]
            candidate_sources = [selected_catalogue.get(index) for index in candidate_indexes]
            calculated_results = calculate_catalogue_windows(
                candidate_sources, request_model.start_utc, request_model.end_utc, fov_constraints, telescope
            )
            summaries = [
                {
                    "source": candidate,
                    "center_windows": candidate_result.center_windows,
                    "full_windows": candidate_result.full_footprint_windows,
                }
                for candidate, candidate_result in zip(candidate_sources, calculated_results)
            ]
            sky_svg, snapshot = render_all_sky_svg(
                selected_catalogue.sources, request_model.start_utc, constraints, telescope=telescope, language="zh"
            )
            context.update({
                "target_label": target_label, "summaries": summaries, "constraints": fov_constraints,
                "original_constraints": constraints, "sky_svg": sky_svg, "snapshot": snapshot,
                "form_values": form_values, "start_local": request_model.start_utc.astimezone(observer_timezone),
                "end_local": request_model.end_utc.astimezone(observer_timezone),
                "result_start_utc": request_model.start_utc.isoformat().replace("+00:00", "Z"),
                "result_end_utc": request_model.end_utc.isoformat().replace("+00:00", "Z"),
                "error": None,
            })
            return templates.TemplateResponse(request, "bulk_result.html", context)

        assert source is not None
        source = _nominal_source(source, nominal_radius_deg)
        # Promote legacy local numeric identity before storing result controls;
        # subsequent display-layer changes must never rebind this target.
        if source.index >= 0:
            form_values["source_key"] = source.source_key
            form_values["source_index"] = str(source.index)
        result = calculate_windows(
            source, request_model.start_utc, request_model.end_utc, constraints, telescope=telescope
        )
        status = source_status(source, request_model.start_utc, constraints, telescope)
        highlighted_indexes = _highlighted_window_fov_sources(
            selected_catalogue.sources, result.full_footprint_windows, telescope, source
        )
        result_map_sources = [source if item.source_key == source.source_key else item for item in selected_catalogue.sources]
        if not any(item.source_key == source.source_key for item in result_map_sources):
            result_map_sources.append(source)
        sky_svg, snapshot = render_all_sky_svg(
            result_map_sources, request_model.start_utc, constraints,
            selected_index=source.index, telescope=telescope, language="zh",
        )
        fov_svg = render_local_fov_svg(
            source, selected_catalogue.sources, request_model.start_utc, status.to_dict(), telescope, language="zh"
        )
        plot_theme = form_values["plot_theme"]
        # The plot receives a concrete label rather than assuming Beijing for
        # a temporary observatory. UTC remains an explicit display preference.
        plot_timezone_label = "UTC" if form_values["display_timezone"] == "utc" else telescope.timezone_label
        plot_svg = render_window_plot(
            result, theme=plot_theme, timezone_label=plot_timezone_label,
            timezone_offset_hours=telescope.timezone_offset_hours,
        )
        result_dict = result.to_dict()
        source_detail = _source_detail(
            source.source_key, request_model.start_utc, constraints, telescope, selected_catalogue,
            nominal_radius_deg=nominal_radius_deg,
        ) if source.index >= 0 else None
        context.update({
            "sources": selected_catalogue.sources, "catalogue": _catalogue_metadata(selected_catalogue), "source": source, "source_detail": source_detail, "result": result,
            "result_dict": result_dict, "status": status, "constraints": constraints, "sky_svg": sky_svg,
            "fov_svg": fov_svg, "plot_svg": plot_svg, "snapshot": snapshot, "form_values": form_values,
            "highlighted_indexes": highlighted_indexes,
            "window_display_time": (
                result.full_footprint_windows[0].start if result.full_footprint_windows
                else request_model.start_utc
            ).isoformat().replace("+00:00", "Z"),
            "full_window_ranges_json": json.dumps([
                [window.to_dict()["start"], window.to_dict()["end"]] for window in result.full_footprint_windows
            ], separators=(",", ":")),
            "target_label": target_label, "start_local": request_model.start_utc.astimezone(observer_timezone),
            "end_local": request_model.end_utc.astimezone(observer_timezone), "error": None,
        })
        return templates.TemplateResponse(request, "result.html", context)
    except HTTPException:
        # IERS coverage failures are already structured HTTP 422 responses.
        # Preserve them rather than converting them into an HTML server error.
        raise
    except (ValidationError, ValueError, KeyError) as exc:
        # Keep valid datetime controls in canonical UTC form after an unrelated
        # validation error (for example a zenith range). The browser can then
        # render them accurately in either Beijing time or UTC.
        form_values["planner_start_utc"] = _canonical_form_time(start_time, display_timezone, observer_timezone)
        form_values["planner_end_utc"] = _canonical_form_time(end_time, display_timezone, observer_timezone)
        now = _now_utc()
        fallback_telescope = locals().get("telescope", LACT_TELESCOPE)
        fallback_timezone = _observer_timezone(fallback_telescope)
        sky_svg, snapshot = render_all_sky_svg(
            selected_catalogue.sources, now, ConstraintSet(**DEFAULT_PLANNER_CONSTRAINT_VALUES), telescope=fallback_telescope, language="zh"
        )
        context = _base_context(request, fallback_telescope)
        context.update({
            "sources": selected_catalogue.sources, "catalogue": _catalogue_metadata(selected_catalogue), "sky_svg": sky_svg, "snapshot": snapshot,
            "now_local": now.astimezone(fallback_timezone), "default_start": start_time,
            "default_end": end_time, "default_start_utc": "", "default_end_utc": "", "selected_source": None, "form_values": form_values,
            "error": str(exc),
        })
        return templates.TemplateResponse(request, "index.html", context, status_code=422)


@app.get("/result", response_class=HTMLResponse)
def result_page_get(
    request: Request,
    source_index: str = Query("region"),
    source_key: Optional[str] = Query(None),
    nominal_radius_deg: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    region_ra_deg: Optional[str] = Query(None),
    region_dec_deg: Optional[str] = Query(None),
    region_radius_deg: Optional[str] = Query(None),
    region_name: Optional[str] = Query(None),
    catalog_token: Optional[str] = Query(None),
    catalog_tokens: Optional[str] = Query(None),
    telescope_mode: Optional[str] = Query(None),
    custom_longitude_deg: Optional[str] = Query(None),
    custom_latitude_deg: Optional[str] = Query(None),
    custom_altitude_m: Optional[str] = Query(None),
    custom_timezone_offset_hours: Optional[str] = Query(None),
    custom_fov_diameter_deg: Optional[str] = Query(None),
    display_theme: Optional[str] = Query(None),
    plot_theme: Optional[str] = Query(None),
    display_timezone: Optional[str] = Query(None),
    sun_max_altitude_deg: Optional[str] = Query(None),
    moon_min_separation_deg: Optional[str] = Query(None),
    target_min_zenith_deg: Optional[str] = Query(None),
    target_max_zenith_deg: Optional[str] = Query(None),
    minimum_window_seconds: Optional[str] = Query(None),
) -> HTMLResponse:
    """Rebuild a calculated result from its URL-safe form state."""
    if not start_time or not end_time:
        return index(request)
    try:
        parsed_nominal_radius = _parse_optional_float(nominal_radius_deg)
        if parsed_nominal_radius is not None and not 0 < parsed_nominal_radius <= 90:
            raise ValueError
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=[{
                "type": "value_error",
                "loc": ["query", "nominal_radius_deg"],
                "msg": "nominal_radius_deg must be a number in (0, 90]",
                "input": nominal_radius_deg,
            }],
        ) from exc
    return result_page(
        request=request, source_index=source_index, source_key=source_key,
        nominal_radius_deg=parsed_nominal_radius, start_time=start_time, end_time=end_time,
        region_ra_deg=region_ra_deg, region_dec_deg=region_dec_deg, region_radius_deg=region_radius_deg,
        region_name=region_name, catalog_token=catalog_token, catalog_tokens=catalog_tokens,
        telescope_mode=telescope_mode, custom_longitude_deg=custom_longitude_deg,
        custom_latitude_deg=custom_latitude_deg, custom_altitude_m=custom_altitude_m,
        custom_timezone_offset_hours=custom_timezone_offset_hours, custom_fov_diameter_deg=custom_fov_diameter_deg,
        display_theme=display_theme, plot_theme=plot_theme, display_timezone=display_timezone,
        sun_max_altitude_deg=sun_max_altitude_deg, moon_min_separation_deg=moon_min_separation_deg,
        target_min_zenith_deg=target_min_zenith_deg, target_max_zenith_deg=target_max_zenith_deg,
        minimum_window_seconds=minimum_window_seconds,
    )


@app.get("/about", response_class=HTMLResponse)
def about(request: Request) -> HTMLResponse:
    context = _base_context(request)
    context.update({"iers": iers_status(), "capabilities": CAPABILITIES})
    return templates.TemplateResponse(request, "about.html", context)


@app.get("/api/v1", response_class=HTMLResponse)
def api_reference(request: Request) -> HTMLResponse:
    context = _base_context(request)
    context.update(
        {
            "endpoints": [
                ("GET", "/api/v1/health", "源表、IERS 与补充数据健康状态"),
                ("GET", "/api/v1/config", "站点、FoV 与能力边界"),
                ("GET", "/api/v1/catalogues", "已安装、临时和结果页 Gaia 源表元数据"),
                ("GET", "/api/v1/sources?q=&limit=&catalog_tokens=", "按已选源表检索普通目录源"),
                ("GET", "/api/v1/sources/{source_key}", "源详情与指定时刻几何状态"),
                ("GET", "/api/v1/sky/current", "全天图 SVG 与已选普通源表状态"),
                ("GET", "/api/v1/sky/local-fov", "目标中心局部图 SVG 与共享模式状态"),
                ("GET", "/api/v1/gaia?map_kind=local-fov", "按筛选条件查询并着色局部 Gaia 图层"),
                ("POST", "/api/v1/windows/calculate", "中心和完整 footprint 观测窗口"),
                ("POST", "/api/v1/windows/alternatives", "观测计划备选源：粗筛后精确验证，最多返回 3 个"),
                ("GET", "/api/v1/windows/plot-overlay", "含 Zenith-Time 对比曲线的窗口 SVG"),
                ("GET", "/openapi.json", "机器可读 OpenAPI schema"),
            ]
        }
    )
    return templates.TemplateResponse(request, "api.html", context)


@app.get("/api/v1/health")
def health() -> dict:
    iers = iers_status()
    return {
        "status": "ok" if iers["covers_current_time"] else "degraded",
        "catalogue": {
            "loaded": True,
            "rows": len(catalog.sources),
            "sha256": catalog.sha256,
        },
        "iers": iers,
        "enrichment": {
            "loaded": enrichment_store.load_error is None,
            "error": enrichment_store.load_error,
        },
    }


@app.get("/api/v1/config")
def config() -> dict:
    return {
        "site": SITE_METADATA.__dict__,
        "telescope": LACT_TELESCOPE.to_dict(),
        "coordinate_frame": COORDINATE_FRAME_LABEL,
        "fov_diameter_deg": FOV_DIAMETER_DEG,
        "fov_radius_deg": FOV_RADIUS_DEG,
        "capabilities": CAPABILITIES,
        "joint_observation_evaluated": False,
        "weather_evaluated": False,
        "telemetry_evaluated": False,
        "geometry_only": True,
    }


@app.get("/api/v1/catalogues")
def catalogue_options() -> dict:
    """List installed catalogue choices; uploads remain operator-session local."""
    choices = [{**_catalogue_metadata(catalog), "available": True}]
    for identifier, (label, _, count) in BUILTIN_CATALOGUES.items():
        try:
            choices.append({**_catalogue_metadata(installed_catalogue(identifier)), "available": True})
        except (ValueError, OSError) as exc:
            choices.append({"identifier": identifier, "label": label, "count": count, "available": False, "error": str(exc)})
    choices.append({"identifier": "gaia-dr3", "label": "Gaia DR3", "available": True, "online": True, "temporary": False, "selection_scope": "result_local_fov_only"})
    return {"catalogues": choices}


@app.post("/api/v1/catalogues/upload")
async def upload_catalogue(file: UploadFile = File(...)) -> dict:
    """Validate one temporary CSV source table without writing it to disk."""
    try:
        selected = temporary_catalogues.create_from_csv(
            await file.read(), file.filename or "uploaded catalogue"
        )
    except CatalogError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {**_catalogue_metadata(selected), "sources": [source.to_dict() for source in selected.sources]}


@app.get("/api/v1/sources")
def sources(
    q: str = Query(default="", max_length=80),
    limit: int = Query(default=100, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    catalog_token: Optional[str] = Query(None),
    catalog_tokens: Optional[str] = Query(None, max_length=4000),
) -> dict:
    try:
        selected = _catalogue_collection(_resolve_catalogues(catalog_token, catalog_tokens))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    all_matches = selected.search(q, None)
    matches = all_matches[offset:offset + limit]
    return {
        "count": len(matches),
        "total": len(all_matches),
        "offset": offset,
        "next_offset": offset + len(matches) if offset + len(matches) < len(all_matches) else None,
        "catalogue": _catalogue_metadata(selected),
        "catalogue_sha256": selected.sha256,
        "sources": [source.to_dict() for source in matches],
    }


@app.get("/api/v1/sources/{source_index:path}")
def source_detail(
    source_index: str,
    nominal_radius_deg: Optional[float] = Query(None, gt=0, le=90),
    at_time: Optional[datetime] = None,
    catalog_token: Optional[str] = Query(None),
    catalog_tokens: Optional[str] = Query(None, max_length=4000),
    display_frame: str = Query(DEFAULT_DISPLAY_COORDINATE_FRAME, pattern="^(altaz|j2000|galactic)$"),
    enforce_current_pointing: bool = Query(False),
    constraints: ConstraintSet = Depends(_query_constraints),
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    try:
        selected = _catalogue_collection(_resolve_catalogues(catalog_token, catalog_tokens))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    moment = at_time or _now_utc()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=SITE_TIMEZONE)
    moment = moment.astimezone(timezone.utc)
    _validate_iers_range(moment, moment)
    return _source_detail(
        source_index, moment, constraints, telescope, selected,
        enforce_current_pointing=enforce_current_pointing,
        catalog_token=catalog_token, catalog_tokens=catalog_tokens,
        nominal_radius_deg=nominal_radius_deg,
    )


def _validate_iers_range(start: datetime, end: datetime) -> None:
    """Reject work outside bundled Earth-orientation coverage for reproducibility."""
    status = iers_status()
    start_mjd = float(Time(start).mjd)
    end_mjd = float(Time(end).mjd)
    if start_mjd < status["first_mjd"] or end_mjd > status["last_mjd"]:
        raise HTTPException(
            status_code=422,
            detail=(
                "requested time is outside bundled IERS coverage "
                f"[{status['first_mjd']}, {status['last_mjd']}] MJD"
            ),
        )


@app.get("/api/v1/sky/bodies")
def current_bodies(
    at_time: datetime = Query(...),
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    """Return lightweight Sun/Moon horizon coordinates for the shared header."""
    moment = at_time.astimezone(timezone.utc) if at_time.tzinfo else at_time.replace(tzinfo=timezone.utc)
    _validate_iers_range(moment, moment)
    frame = AltAz(obstime=Time(moment), location=telescope.location, pressure=0 * u.hPa)
    sun = get_sun(Time(moment)).transform_to(frame)
    moon = get_body("moon", Time(moment), telescope.location).transform_to(frame)
    return {
        "at_time": moment.isoformat().replace("+00:00", "Z"),
        "sun": {"altitude_deg": float(sun.alt.deg), "azimuth_deg": float(sun.az.deg)},
        "moon": {"altitude_deg": float(moon.alt.deg), "azimuth_deg": float(moon.az.deg)},
        "telescope": telescope.to_dict(),
    }


def _map_bounds(value: Optional[str]):
    if value is None or value == "":
        return None
    try:
        parsed = json.loads(value) if value.startswith("[") else [float(part) for part in value.split(",")]
        if len(parsed) != 4 or not all(np.isfinite(float(part)) for part in parsed) or float(parsed[2]) <= 0 or float(parsed[3]) <= 0:
            raise ValueError
        return tuple(float(part) for part in parsed)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="bounds must be finite SVG x,y,width,height with positive size") from exc


@app.get("/api/v1/gaia")
def gaia_stars(
    at_time: Optional[datetime] = None,
    map_kind: str = Query("current", pattern="^(current|local-fov)$"),
    status_mode: str = Query("instant", pattern="^(instant|trajectory|specified)$"),
    specified_kind: str = Query("point", pattern="^(point|range)$"),
    specified_end: Optional[datetime] = None,
    trajectory_end: Optional[datetime] = None,
    trajectory_enforce_current_pointing: bool = Query(False),
    trajectory_ranges: Optional[str] = Query(None, max_length=24000),
    trajectory_display_time: Optional[datetime] = None,
    selected_source_key: Optional[str] = Query(None, max_length=256),
    target_source_key: Optional[str] = Query(None, max_length=256),
    target_radius_deg: float = Query(0.1, gt=0, le=90),
    target_name: Optional[str] = Query(None, max_length=80),
    display_frame: str = Query(DEFAULT_DISPLAY_COORDINATE_FRAME, pattern="^(altaz|j2000|galactic)$"),
    language: str = Query("en", pattern="^(en|zh)$"),
    zoom: float = Query(1.0, ge=1, le=1000),
    bounds: Optional[str] = Query(None, max_length=200),
    target_ra_deg: Optional[float] = Query(None, ge=0, lt=360),
    target_dec_deg: Optional[float] = Query(None, ge=-90, le=90),
    radius_deg: float = Query(1.0, ge=0.1, le=5.0),
    limit: int = Query(10, ge=1, le=500),
    max_mag: float = Query(10.0, ge=5.0, le=22.0),
    constraints: ConstraintSet = Depends(_query_constraints),
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    """Independent bounded online layer; failures do not block the base sky."""
    target = None
    target_source_key = target_source_key or selected_source_key
    if target_source_key is not None:
        try:
            target = resolve_source(target_source_key)
            target_ra_deg, target_dec_deg = target.ra, target.dec
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    if (target_ra_deg is None) != (target_dec_deg is None):
        raise HTTPException(status_code=422, detail="both target coordinates are required")
    moment = at_time or _now_utc()
    moment = moment.replace(tzinfo=SITE_TIMEZONE) if moment.tzinfo is None else moment
    moment = moment.astimezone(timezone.utc)
    render_status_mode = status_mode
    if status_mode == "specified":
        if specified_kind == "point":
            if specified_end is not None:
                raise HTTPException(status_code=422, detail="specified point must not include specified_end")
            trajectory_end = None
        else:
            if specified_end is None:
                raise HTTPException(status_code=422, detail="specified range requires specified_end")
            trajectory_end = specified_end
        render_status_mode = "trajectory" if specified_kind == "range" else "instant"
    parsed_ranges = None
    if status_mode == "specified" and trajectory_ranges:
        raise HTTPException(status_code=422, detail="specified time range cannot use trajectory_ranges")
    if trajectory_ranges:
        try:
            raw_ranges = json.loads(trajectory_ranges)
            if not isinstance(raw_ranges, list):
                raise ValueError
            parsed_ranges = []
            for raw in raw_ranges:
                if not isinstance(raw, list) or len(raw) != 2:
                    raise ValueError
                begin = _parse_form_datetime(str(raw[0]), "utc")
                finish = _parse_form_datetime(str(raw[1]), "utc")
                if finish <= begin:
                    raise ValueError
                parsed_ranges.append((begin, finish))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="trajectory_ranges must be a JSON array of forward UTC intervals") from exc
    if render_status_mode == "trajectory":
        if trajectory_end is None:
            raise HTTPException(status_code=422, detail="trajectory_end is required for trajectory status mode")
        if trajectory_end.tzinfo is None:
            trajectory_end = trajectory_end.replace(tzinfo=SITE_TIMEZONE)
        trajectory_end = trajectory_end.astimezone(timezone.utc)
        if trajectory_end <= moment:
            raise HTTPException(status_code=422, detail="trajectory_end must be later than at_time")
        if status_mode == "specified" and (trajectory_end - moment).total_seconds() > 86400:
            raise HTTPException(status_code=422, detail="specified time range cannot exceed 24 hours")
        _validate_iers_range(moment, trajectory_end)
    else:
        trajectory_end = None
        _validate_iers_range(moment, moment)
    try:
        rows, metadata = query_gaia_stars(moment, telescope, radius_deg, limit, max_mag, target_ra_deg, target_dec_deg)
        map_bounds = _map_bounds(bounds)
        if map_kind == "local-fov":
            if target is None:
                if target_ra_deg is None:
                    raise HTTPException(status_code=422, detail="local Gaia layer requires a target")
                target = Source(-1, target_name or "Target", target_radius_deg, None, target_ra_deg, target_dec_deg, 0, 0, None)
            svg = render_local_fov_svg(
                target, rows, moment, None, telescope, language, display_frame, zoom, map_bounds, None, constraints,
                trajectory_end=trajectory_end,
                trajectory_enforce_current_pointing=trajectory_enforce_current_pointing,
                trajectory_ranges=parsed_ranges,
                trajectory_display_time=trajectory_display_time,
            )
        else:
            svg, _ = render_all_sky_svg(
                rows, moment, constraints, telescope=telescope, language=language,
                trajectory_end=trajectory_end,
                trajectory_enforce_current_pointing=trajectory_enforce_current_pointing,
                trajectory_ranges=parsed_ranges,
                trajectory_display_time=trajectory_display_time,
                display_frame=display_frame, zoom=zoom, bounds=map_bounds,
            )
        root = ET.fromstring(svg)
        markers = [element for element in root.iter() if "source-type-gaia" in element.attrib.get("class", "").split()]
        overlay = '<svg xmlns="http://www.w3.org/2000/svg">' + ''.join(ET.tostring(element, encoding="unicode") for element in markers) + '</svg>'
        status_by_key = {}
        status_counts = {"GREEN": 0, "RED": 0, "UNKNOWN": 0}
        for marker in markers:
            classes = marker.attrib.get("class", "").split()
            status = next((value[len("status-"):].upper() for value in classes if value.startswith("status-")), "UNKNOWN")
            key = marker.attrib.get("data-source-key", "")
            if key:
                status_by_key[key] = status
            status_counts[status if status in status_counts else "UNKNOWN"] += 1
        metadata["drawn_count"] = len(markers)
        metadata["status_counts"] = status_counts
        metadata["status_mode"] = status_mode
        metadata["specified_kind"] = specified_kind if status_mode == "specified" else None
        metadata["display_time"] = (trajectory_display_time or moment).isoformat().replace("+00:00", "Z")
        metadata["specified_end"] = trajectory_end.isoformat().replace("+00:00", "Z") if status_mode == "specified" and trajectory_end else None
        return {**metadata, "gaia": metadata, "overlay_svg": overlay, "sources": [{**row.to_dict(include_notes=True), "source_id": row.original_id, "status": status_by_key.get(row.source_key, "UNKNOWN")} for row in rows]}
    except GaiaQueryError as exc:
        # Keep query failures structurally distinct from a successful zero-row
        # response. The front end can therefore show the actual upstream
        # reason without treating an unavailable TAP service as no stars.
        error = str(exc)
        failure_meta = getattr(exc, "metadata", {})
        metadata = {
            "status": "error", "error": error, "error_reason": error,
            "actual_failure_reason": failure_meta.get("actual_failure_reason", error),
            "count": 0, "zero": False, "cached": False, "cache_hit": False,
            "cache": {"hit": False, "backend": "memory"},
            "limit": limit, "truncated": False, "incomplete": True,
            "query_strategy": failure_meta.get("query_strategy", "async_tap" if (radius_deg > 1 or limit > 100 or max_mag > 10) else "sync_tap"),
            "query_strategy_metadata": failure_meta.get("query_strategy_metadata", {}),
            "async_cleanup_attempted": failure_meta.get("async_cleanup_attempted", False),
            "async_cleanup_error": failure_meta.get("async_cleanup_error"),
            "selection": "nearest_by_angular_distance", "ordering": "angular_distance_asc",
            "brightest_n": False,
            "warning": "Gaia DR3 could not be queried; no stars are treated as a successful zero-row result.",
            "status_mode": status_mode,
            "specified_kind": specified_kind if status_mode == "specified" else None,
            "display_time": (trajectory_display_time or moment).isoformat().replace("+00:00", "Z"),
        }
        return {**metadata, "gaia": metadata, "sources": [], "overlay_svg": ""}


@app.get("/api/v1/sky/current")
def current_sky(
    at_time: Optional[datetime] = None,
    selected_source_index: Optional[int] = Query(None, ge=0),
    selected_source_key: Optional[str] = Query(None, max_length=256),
    nominal_radius_deg: Optional[float] = Query(None, gt=0, le=90),
    catalog_token: Optional[str] = Query(None),
    catalog_tokens: Optional[str] = Query(None, max_length=4000),
    include_gaia: bool = Query(False),
    gaia_radius_deg: float = Query(1.0, ge=0.1, le=5.0),
    gaia_limit: int = Query(10, ge=1, le=500),
    gaia_max_mag: float = Query(10.0, ge=5.0, le=22.0),
    zoom: float = Query(1.0, ge=1, le=1000),
    bounds: Optional[str] = Query(None, max_length=200),
    grid_step_deg: Optional[float] = Query(None, gt=0, le=90),
    display_frame: str = Query(DEFAULT_DISPLAY_COORDINATE_FRAME, pattern="^(altaz|j2000|galactic)$"),
    language: str = Query("en", pattern="^(en|zh)$"),
    status_mode: str = Query("instant", pattern="^(instant|trajectory|specified)$"),
    specified_kind: str = Query("point", pattern="^(point|range)$"),
    specified_end: Optional[datetime] = None,
    trajectory_end: Optional[datetime] = None,
    highlight_indexes: Optional[str] = Query(None, max_length=6000),
    trajectory_enforce_current_pointing: bool = Query(False),
    trajectory_ranges: Optional[str] = Query(None, max_length=24000),
    trajectory_display_time: Optional[datetime] = Query(None),
    constraints: ConstraintSet = Depends(_query_constraints),
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    try:
        selected = _catalogue_collection(_resolve_catalogues(catalog_token, catalog_tokens))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if catalog_tokens and "gaia-dr3" in {item.strip() for item in catalog_tokens.split(",")}:
        include_gaia = True
    gaia_status = {"requested": include_gaia, "loaded": False, "deferred": include_gaia, "endpoint": "/api/v1/gaia", "error": None, "count": 0}
    render_sources = list(selected.sources)
    if selected_source_key is not None or selected_source_index is not None:
        try:
            target = _nominal_source(_resolve_target_identity(selected_source_key if selected_source_key is not None else selected_source_index, catalog_token, catalog_tokens), nominal_radius_deg)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        selected_source_index = target.index
        render_sources = [target if source.source_key == target.source_key else source for source in render_sources]
        if not any(source.source_key == target.source_key for source in render_sources):
            render_sources.append(target)
    sky_request = SkyRequest(
        at_time=at_time,
        selected_source_index=selected_source_index,
        constraints=constraints,
    )
    render_status_mode = status_mode
    if status_mode == "specified":
        if specified_kind == "point":
            if specified_end is not None:
                raise HTTPException(status_code=422, detail="specified point must not include specified_end")
            trajectory_end = None
        else:
            if specified_end is None:
                raise HTTPException(status_code=422, detail="specified range requires specified_end")
            trajectory_end = specified_end
        render_status_mode = "trajectory" if specified_kind == "range" else "instant"
    if render_status_mode == "trajectory":
        if trajectory_end is None:
            raise HTTPException(status_code=422, detail="trajectory_end is required for trajectory status mode")
        if trajectory_end.tzinfo is None:
            trajectory_end = trajectory_end.replace(tzinfo=SITE_TIMEZONE)
        trajectory_end = trajectory_end.astimezone(timezone.utc)
        if trajectory_end <= sky_request.at_utc:
            raise HTTPException(status_code=422, detail="trajectory_end must be later than at_time")
        if status_mode == "specified" and (trajectory_end - sky_request.at_utc).total_seconds() > 86400:
            raise HTTPException(status_code=422, detail="specified time range cannot exceed 24 hours")
        _validate_iers_range(sky_request.at_utc, trajectory_end)
    else:
        trajectory_end = None
        _validate_iers_range(sky_request.at_utc, sky_request.at_utc)
    try:
        highlights = [int(value) for value in (highlight_indexes or "").split(",") if value.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="highlight_indexes must be a comma-separated index list") from exc
    parsed_ranges = None
    if status_mode == "specified" and trajectory_ranges:
        raise HTTPException(status_code=422, detail="specified time range cannot use trajectory_ranges")
    if trajectory_ranges:
        try:
            raw_ranges = json.loads(trajectory_ranges)
            if not isinstance(raw_ranges, list):
                raise ValueError
            parsed_ranges = []
            for raw in raw_ranges:
                if not isinstance(raw, list) or len(raw) != 2:
                    raise ValueError
                begin = _parse_form_datetime(str(raw[0]), "utc")
                finish = _parse_form_datetime(str(raw[1]), "utc")
                if finish <= begin:
                    raise ValueError
                parsed_ranges.append((begin, finish))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="trajectory_ranges must be a JSON array of forward UTC intervals") from exc
    allowed_indexes = {source.index for source in render_sources}
    highlights = [value for value in highlights if value in allowed_indexes]
    # Purple tracked-FoV markers belong exclusively to observation-window mode
    # and never override the selected target's own status marker.
    if render_status_mode != "trajectory":
        highlights = []
    elif selected_source_index is not None:
        highlights = [value for value in highlights if value != selected_source_index]
    svg, snapshot = render_all_sky_svg(
        render_sources,
        sky_request.at_utc,
        sky_request.constraints,
        selected_index=selected_source_index,
        telescope=telescope,
        language=language,
        highlighted_indexes=highlights,
        trajectory_end=trajectory_end,
        trajectory_enforce_current_pointing=trajectory_enforce_current_pointing,
        trajectory_ranges=parsed_ranges,
        trajectory_display_time=trajectory_display_time,
        display_frame=display_frame,
        zoom=zoom, bounds=_map_bounds(bounds), grid_step_deg=grid_step_deg,
    )
    snapshot.update({
        "geometry_only": True,
        "status_mode": status_mode,
        "specified_kind": specified_kind if status_mode == "specified" else None,
        "specified_end": trajectory_end.isoformat().replace("+00:00", "Z") if status_mode == "specified" and trajectory_end else None,
        "gaia": gaia_status,
        "display_frame": display_frame,
        "svg": svg,
        "constraints": sky_request.constraints.model_dump(),
        "catalogue": _catalogue_metadata(selected),
    })
    return snapshot


def _source_catalogue_sha256(source: Source):
    if source.index < 0:
        return None  # An operator-defined target has no source catalogue.
    return _resolve_catalogue(source.catalogue_id).sha256


def _nominal_source(source: Source, radius: Optional[float]) -> Source:
    if radius is None:
        return source
    if not np.isfinite(radius) or not 0 < radius <= 90:
        raise ValueError("nominal_radius_deg must be in (0, 90]")
    return replace(source, ext=radius, footprint_known=True, footprint_kind="operator_nominal_radius")


def _api_target(
    selected_catalogue, target_source_index: Optional[int], target_ra_deg: Optional[float],
    target_dec_deg: Optional[float], target_radius_deg: Optional[float], target_name: Optional[str],
    target_source_key: Optional[str] = None, nominal_radius_deg: Optional[float] = None,
    catalog_token: Optional[str] = None, catalog_tokens: Optional[str] = None,
) -> Source:
    """Resolve stable targets, with explicit singular-token numeric legacy support."""
    if target_source_key is not None or target_source_index is not None:
        return _nominal_source(_resolve_target_identity(target_source_key if target_source_key is not None else target_source_index, catalog_token, catalog_tokens), nominal_radius_deg)
    if None in {target_ra_deg, target_dec_deg, target_radius_deg}:
        raise HTTPException(status_code=422, detail="target source index or complete target coordinates are required")
    return Source(
        -1, normalise_temporary_target_name(target_name, target_ra_deg, target_dec_deg),
        target_radius_deg, 0.0, target_ra_deg, target_dec_deg, 0.0, 0.0, 0.0,
    )


@app.get("/api/v1/windows/zenith-overlay")
def zenith_overlay(
    source_index: Optional[int] = Query(None, ge=0),
    source_key: Optional[str] = Query(None, max_length=256),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    catalog_token: Optional[str] = Query(None),
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    """Return a comparison source's zenith series for a result-page overlay.

    The result page redraws only its visualization from this data. No target
    selection, window boundary or saved observing plan is altered.
    """
    try:
        selected = _resolve_catalogue(catalog_token)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    start = start_time.replace(tzinfo=SITE_TIMEZONE) if start_time.tzinfo is None else start_time
    end = end_time.replace(tzinfo=SITE_TIMEZONE) if end_time.tzinfo is None else end_time
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if end <= start:
        raise HTTPException(status_code=422, detail="end_time must be later than start_time")
    _validate_iers_range(start, end)
    samples = min(1441, max(2, int((end - start).total_seconds() // 60) + 1))
    times = [datetime.fromtimestamp(value, timezone.utc) for value in np.linspace(start.timestamp(), end.timestamp(), samples)]
    try:
        source = _resolve_target_identity(source_key if source_key is not None else source_index, catalog_token)
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    series = compute_geometry(source, times, telescope)
    return {
        "source": source.to_dict(),
        "times": [value.isoformat().replace("+00:00", "Z") for value in times],
        "zenith_deg": [float(value) for value in series.target_zenith_deg],
        "telescope": telescope.to_dict(),
    }


@app.get("/api/v1/windows/plot-overlay")
def plot_overlay(
    comparison_source_index: List[int] = Query(default=[]),
    comparison_source_key: List[str] = Query(default=[]),
    comparison_colour: List[str] = Query(default=[]),
    comparison_line_style: List[str] = Query(default=[]),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    target_source_index: Optional[int] = Query(None, ge=0),
    target_source_key: Optional[str] = Query(None, max_length=256),
    nominal_radius_deg: Optional[float] = Query(None, gt=0, le=90),
    target_ra_deg: Optional[float] = Query(None, ge=0, lt=360),
    target_dec_deg: Optional[float] = Query(None, ge=-90, le=90),
    target_radius_deg: Optional[float] = Query(None, gt=0, le=90),
    target_name: Optional[str] = Query(None, max_length=80),
    catalog_token: Optional[str] = Query(None),
    catalog_tokens: Optional[str] = Query(None, max_length=4000),
    theme: str = Query("light", pattern="^(light|dark)$"),
    timezone_label: str = Query("UTC", max_length=40),
    constraints: ConstraintSet = Depends(_query_constraints),
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    """Render an optional dashed zenith comparison over the target plot.

    This route is intentionally display-only: it recalculates the target with
    the original constraints and overlays a second catalogue source without
    changing the selected target, windows or observing plan.
    """
    try:
        selected = _catalogue_collection(_resolve_catalogues(catalog_token, catalog_tokens))
        target = _api_target(selected, target_source_index, target_ra_deg, target_dec_deg, target_radius_deg, target_name, target_source_key, nominal_radius_deg, catalog_token, catalog_tokens)
        comparison_indexes = list(dict.fromkeys(comparison_source_index))
        if any(index < 0 for index in comparison_indexes):
            raise ValueError("comparison source indexes must be non-negative")
        identities = comparison_source_key or comparison_indexes
        if len(identities) > 32:
            raise ValueError("at most 32 comparison sources are allowed")
        comparisons = [_resolve_target_identity(identity, catalog_token, catalog_tokens) for identity in dict.fromkeys(identities)]
        default_colours = ["#ff8c42", "#8b5cf6", "#00a6a6", "#d14f9b", "#8a9a22", "#7a6ff0"]
        colours = [
            value if re.fullmatch(r"#[0-9A-Fa-f]{6}", value) else default_colours[index % len(default_colours)]
            for index, value in enumerate(comparison_colour[:len(comparisons)])
        ]
        while len(colours) < len(comparisons):
            colours.append(default_colours[len(colours) % len(default_colours)])
        allowed_styles = {"solid", "dotted", "dashdot"}
        line_styles = [value if value in allowed_styles else "dashdot" for value in comparison_line_style[:len(comparisons)]]
        line_styles.extend(["dashdot"] * (len(comparisons) - len(line_styles)))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    start = start_time.replace(tzinfo=SITE_TIMEZONE) if start_time.tzinfo is None else start_time
    end = end_time.replace(tzinfo=SITE_TIMEZONE) if end_time.tzinfo is None else end_time
    start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
    if end <= start:
        raise HTTPException(status_code=422, detail="end_time must be later than start_time")
    _validate_iers_range(start, end)
    result = calculate_windows(target, start, end, constraints, telescope=telescope)
    companions = [compute_geometry(item, result.sample_times, telescope) for item in comparisons]
    return {
        "svg": render_window_plot(
            result, theme=theme, timezone_label=timezone_label,
            timezone_offset_hours=telescope.timezone_offset_hours,
            zenith_overlays=[
                (item.index, item.display_name, series.target_zenith_deg, colour, line_style)
                for item, series, colour, line_style in zip(comparisons, companions, colours, line_styles)
            ],
        ),
        "comparison_sources": [item.to_dict() for item in comparisons],
        # Keep the original singular field for existing one-overlay clients.
        "comparison_source": comparisons[0].to_dict() if len(comparisons) == 1 else None,
    }


@app.get("/api/v1/sky/local-fov")
def local_fov(
    at_time: datetime = Query(...),
    status_mode: str = Query("instant", pattern="^(instant|trajectory|specified)$"),
    specified_kind: str = Query("point", pattern="^(point|range)$"),
    specified_end: Optional[datetime] = None,
    trajectory_end: Optional[datetime] = None,
    trajectory_enforce_current_pointing: bool = Query(False),
    trajectory_ranges: Optional[str] = Query(None, max_length=24000),
    trajectory_display_time: Optional[datetime] = None,
    highlight_indexes: Optional[str] = Query(None, max_length=6000),
    target_source_index: Optional[int] = Query(None, ge=0),
    target_source_key: Optional[str] = Query(None, max_length=256),
    nominal_radius_deg: Optional[float] = Query(None, gt=0, le=90),
    target_ra_deg: Optional[float] = Query(None, ge=0, lt=360),
    target_dec_deg: Optional[float] = Query(None, ge=-90, le=90),
    target_radius_deg: Optional[float] = Query(None, gt=0, le=90),
    target_name: Optional[str] = Query(None, max_length=80),
    catalog_token: Optional[str] = Query(None),
    catalog_tokens: Optional[str] = Query(None, max_length=4000),
    language: str = Query("en", pattern="^(en|zh)$"),
    display_frame: str = Query(DEFAULT_DISPLAY_COORDINATE_FRAME, pattern="^(altaz|j2000|galactic)$"),
    zoom: float = Query(1.0, ge=1, le=1000),
    bounds: Optional[str] = Query(None, max_length=200),
    grid_step_deg: Optional[float] = Query(None, gt=0, le=90),
    constraints: ConstraintSet = Depends(_query_constraints),
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    """Render the selected target's local FoV in the requested UI language."""
    try:
        selected = _catalogue_collection(_resolve_catalogues(catalog_token, catalog_tokens))
        target = _api_target(selected, target_source_index, target_ra_deg, target_dec_deg, target_radius_deg, target_name, target_source_key, nominal_radius_deg, catalog_token, catalog_tokens)
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    moment = at_time.replace(tzinfo=SITE_TIMEZONE) if at_time.tzinfo is None else at_time
    moment = moment.astimezone(timezone.utc)
    render_status_mode = status_mode
    if status_mode == "specified":
        if specified_kind == "point":
            if specified_end is not None:
                raise HTTPException(status_code=422, detail="specified point must not include specified_end")
            trajectory_end = None
        else:
            if specified_end is None:
                raise HTTPException(status_code=422, detail="specified range requires specified_end")
            trajectory_end = specified_end
        render_status_mode = "trajectory" if specified_kind == "range" else "instant"
    parsed_ranges = None
    if status_mode == "specified" and trajectory_ranges:
        raise HTTPException(status_code=422, detail="specified time range cannot use trajectory_ranges")
    if trajectory_ranges:
        try:
            raw_ranges = json.loads(trajectory_ranges)
            if not isinstance(raw_ranges, list):
                raise ValueError
            parsed_ranges = []
            for raw in raw_ranges:
                if not isinstance(raw, list) or len(raw) != 2:
                    raise ValueError
                begin = _parse_form_datetime(str(raw[0]), "utc")
                finish = _parse_form_datetime(str(raw[1]), "utc")
                if finish <= begin:
                    raise ValueError
                parsed_ranges.append((begin, finish))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=422, detail="trajectory_ranges must be a JSON array of forward UTC intervals") from exc
    if render_status_mode == "trajectory":
        if trajectory_end is None:
            raise HTTPException(status_code=422, detail="trajectory_end is required for trajectory status mode")
        if trajectory_end.tzinfo is None:
            trajectory_end = trajectory_end.replace(tzinfo=SITE_TIMEZONE)
        trajectory_end = trajectory_end.astimezone(timezone.utc)
        if trajectory_end <= moment:
            raise HTTPException(status_code=422, detail="trajectory_end must be later than at_time")
        if status_mode == "specified" and (trajectory_end - moment).total_seconds() > 86400:
            raise HTTPException(status_code=422, detail="specified time range cannot exceed 24 hours")
        _validate_iers_range(moment, trajectory_end)
    else:
        trajectory_end = None
        _validate_iers_range(moment, moment)
    try:
        highlights = [int(value) for value in (highlight_indexes or "").split(",") if value.strip()]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="highlight_indexes must be a comma-separated index list") from exc
    allowed_indexes = {item.index for item in selected.sources} | {target.index}
    highlights = [value for value in highlights if value in allowed_indexes]
    if render_status_mode != "trajectory":
        highlights = []
    selected_status = source_status(target, moment, constraints, telescope) if render_status_mode != "trajectory" else None
    return {
        "svg": render_local_fov_svg(
            target, selected.sources, moment, selected_status.to_dict() if selected_status else None,
            telescope, language, display_frame, zoom, _map_bounds(bounds), grid_step_deg, constraints,
            trajectory_end=trajectory_end,
            trajectory_enforce_current_pointing=trajectory_enforce_current_pointing,
            trajectory_ranges=parsed_ranges,
            trajectory_display_time=trajectory_display_time,
            selected_index=target.index,
            highlighted_indexes=highlights,
        ),
        "source": target.to_dict(),
        "status_mode": status_mode,
        "specified_kind": specified_kind if status_mode == "specified" else None,
        "display_time": (trajectory_display_time or moment).isoformat().replace("+00:00", "Z"),
        "specified_end": trajectory_end.isoformat().replace("+00:00", "Z") if status_mode == "specified" and trajectory_end else None,
    }


@app.post("/api/v1/windows/alternatives")
def windows_alternatives(
    payload: AlternativeWindowRequest,
    telescope: TelescopeConfig = Depends(_telescope_query),
) -> dict:
    """Return a bounded, explainable set of catalogue alternatives.

    Candidate geometry never applies the current-pointing FoV because this
    deployment has no authoritative pointing telemetry. The telescope hard FoV
    still limits each source footprint.
    """
    _validate_iers_range(payload.search_start_utc, payload.search_end_utc)
    try:
        selected = _catalogue_collection(_resolve_catalogues(payload.catalog_token, payload.catalog_tokens))
        target = _nominal_source(
            _resolve_target_identity(
                payload.source_key, payload.catalog_token, payload.catalog_tokens
            ),
            payload.nominal_radius_deg,
        )
        if payload.alternative_catalog_token:
            alternative_catalogue = _resolve_catalogue(payload.alternative_catalog_token)
            candidate_sources = alternative_catalogue.sources
            candidate_catalogues = [alternative_catalogue]
            candidate_scope = "uploaded_alternative_catalogue"
        else:
            candidate_sources = selected.sources
            candidate_catalogues = list(selected.catalogues)
            candidate_scope = "selected_catalogues"
        result = find_alternatives(
            candidate_sources, target, payload.target_start_utc, payload.target_end_utc,
            payload.search_start_utc, payload.search_end_utc, payload.constraints, telescope,
            max_alternatives=payload.max_alternatives,
            coarse_step_seconds=payload.coarse_step_seconds,
            shortlist_limit=payload.shortlist_limit,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result["catalogues"] = [_catalogue_metadata(table) for table in selected.catalogues]
    result["candidate_catalogues"] = [_catalogue_metadata(table) for table in candidate_catalogues]
    result["candidate_scope"] = candidate_scope
    result["geometry_only"] = True
    return result


@app.post("/api/v1/windows/calculate")
def windows_calculate(payload: WindowRequest) -> dict:
    """Calculate a selected source, custom J2000 region, or current zenith FoV.

    API bulk responses intentionally return compact interval summaries. The web
    planner uses the same code path but renders the detailed source view only
    after the operator selects a concrete source.
    """
    _validate_iers_range(payload.start_utc, payload.end_utc)
    try:
        selected = _catalogue_collection(_resolve_catalogues(payload.catalog_token, payload.catalog_tokens))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if payload.all_sources:
        fov_constraints = _current_fov_constraints(payload.constraints, LACT_TELESCOPE)
        _, start_snapshot = render_all_sky_svg(selected.sources, payload.start_utc, ConstraintSet())
        candidates = [
            selected.get(item["index"])
            for item in start_snapshot["sources"]
            if item["geometry"]["target_pointing_separation_deg"] <= LACT_TELESCOPE.fov_radius_deg
        ]
        calculated_results = calculate_catalogue_windows(
            candidates, payload.start_utc, payload.end_utc, fov_constraints
        )
        results = [
            {
                "source": candidate.to_dict(),
                "center_windows": [window.to_dict() for window in calculated.center_windows],
                "full_footprint_windows": [window.to_dict() for window in calculated.full_footprint_windows],
            }
            for candidate, calculated in zip(candidates, calculated_results)
        ]
        return {
            "target_mode": "current_lact_fov_fixed_zenith",
            "pointing": {"altitude_deg": 90.0, "azimuth_deg": 0.0},
            "constraints": fov_constraints.model_dump(), "results": results,
            "fov_diameter_deg": FOV_DIAMETER_DEG, "catalogue_sha256": selected.sha256,
            "catalogues": [_catalogue_metadata(table) for table in selected.catalogues],
            "geometry_only": True,
        }
    if payload.source_index is not None or payload.source_key is not None:
        try:
            source = _nominal_source(_resolve_target_identity(payload.source_key if payload.source_key is not None else payload.source_index, payload.catalog_token, payload.catalog_tokens), payload.nominal_radius_deg)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    else:
        assert payload.region_ra_deg is not None and payload.region_dec_deg is not None and payload.region_radius_deg is not None
        source = Source(
            -1,
            normalise_temporary_target_name(payload.region_name, payload.region_ra_deg, payload.region_dec_deg),
            payload.region_radius_deg,
            0.0,
            payload.region_ra_deg,
            payload.region_dec_deg,
            0.0,
            0.0,
            0.0,
        )
    result = calculate_windows(source, payload.start_utc, payload.end_utc, payload.constraints)
    response = result.to_dict()
    response.update({
        "target_mode": "catalogue_source" if source.index >= 0 else "custom_region",
        "fov_diameter_deg": FOV_DIAMETER_DEG, "fov_radius_deg": FOV_RADIUS_DEG,
        "joint_observation_evaluated": False, "weather_evaluated": False,
        "telemetry_evaluated": False, "catalogue_sha256": _source_catalogue_sha256(source),
    })
    return response
