from __future__ import annotations

import html
import math
from datetime import datetime, timezone
from typing import Iterable, Optional, Tuple

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, SkyCoord, get_body, get_sun
from astropy.time import Time

from .astronomy import J2000_FRAME, source_coord
from .catalog import Source
from .config import DISPLAY_COORDINATE_FRAMES, LACT_TELESCOPE, TelescopeConfig
from .schemas import ConstraintSet
from .status import sky_snapshot, sky_trajectory_snapshot

STATUS_CLASS = {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}
MAP_LABELS = {
    "en": {"horizon": "Horizon", "north": "N", "east": "E", "south": "S", "west": "W", "sun": "Sun", "moon": "Moon", "north_local": "North", "east_local": "East", "radius": "radius", "extension_outside": "extension exceeds local-map range"},
    "zh": {"horizon": "地平线", "north": "北", "east": "东", "south": "南", "west": "西", "sun": "太阳", "moon": "月亮", "north_local": "北", "east_local": "东", "radius": "半径", "extension_outside": "extension 超出局部图显示范围"},
}


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _labels(language: str) -> dict:
    return MAP_LABELS["zh" if language == "zh" else "en"]


def _polar(altitude: float, azimuth: float, cx: float, cy: float, radius: float) -> Tuple[float, float, bool]:
    visible = altitude >= 0.0
    zenith_distance = max(0.0, min(180.0, 90.0 - altitude))
    radial = radius * min(zenith_distance / 90.0, 1.0)
    azimuth_rad = math.radians(azimuth)
    return cx + radial * math.sin(azimuth_rad), cy - radial * math.cos(azimuth_rad), visible


def _normalise_display_frame(value: str) -> str:
    return value if value in DISPLAY_COORDINATE_FRAMES else "altaz"


def _display_label(value: str) -> str:
    return DISPLAY_COORDINATE_FRAMES[_normalise_display_frame(value)]


def _zenith_coordinate(at_time: datetime, telescope: TelescopeConfig) -> SkyCoord:
    frame = AltAz(obstime=Time(_utc(at_time)), location=telescope.location, pressure=0 * u.hPa)
    return SkyCoord(az=0 * u.deg, alt=90 * u.deg, frame=frame)


def _project_coordinate(coordinate: SkyCoord, center: SkyCoord, cx: float, cy: float, radius: float, visible: bool) -> tuple[float, float, bool, float]:
    separation = float(center.separation(coordinate).deg)
    position_angle = float(center.position_angle(coordinate).deg)
    radial = radius * min(separation / 90.0, 1.0)
    angle = math.radians(position_angle)
    return cx + radial * math.sin(angle), cy - radial * math.cos(angle), visible and separation <= 90.0, position_angle


def _project_source(source: Source, geometry: dict, at_time: datetime, telescope: TelescopeConfig, frame_key: str, cx: float, cy: float, radius: float) -> tuple[float, float, bool, float]:
    if frame_key == "altaz":
        x, y, visible = _polar(float(geometry["target_altitude_deg"]), float(geometry["target_azimuth_deg"]), cx, cy, radius)
        return x, y, visible, float(geometry["target_azimuth_deg"])
    display_frame = J2000_FRAME if frame_key == "j2000" else "galactic"
    coordinate = source_coord(source).transform_to(display_frame)
    center = _zenith_coordinate(at_time, telescope).transform_to(display_frame)
    return _project_coordinate(coordinate, center, cx, cy, radius, float(geometry["target_altitude_deg"]) >= 0.0)


def _project_body(altitude: float, azimuth: float, at_time: datetime, telescope: TelescopeConfig, frame_key: str, cx: float, cy: float, radius: float) -> tuple[float, float, bool, float]:
    if frame_key == "altaz":
        x, y, visible = _polar(altitude, azimuth, cx, cy, radius)
        return x, y, visible, azimuth
    altaz_frame = AltAz(obstime=Time(_utc(at_time)), location=telescope.location, pressure=0 * u.hPa)
    coordinate = SkyCoord(az=azimuth * u.deg, alt=altitude * u.deg, frame=altaz_frame)
    display_frame = J2000_FRAME if frame_key == "j2000" else "galactic"
    return _project_coordinate(coordinate.transform_to(display_frame), _zenith_coordinate(at_time, telescope).transform_to(display_frame), cx, cy, radius, altitude >= 0.0)


def _star_points(x: float, y: float, outer: float = 7.0, inner: float = 3.0) -> str:
    return " ".join(
        f"{x + (outer if index % 2 == 0 else inner) * math.cos(math.radians(-90.0 + index * 36.0)):.1f},{y + (outer if index % 2 == 0 else inner) * math.sin(math.radians(-90.0 + index * 36.0)):.1f}"
        for index in range(10)
    )


def _body_icon(x: float, y: float, kind: str, label: str) -> str:
    """Return an orange Sun/Moon marker only when the body is above horizon."""
    glyph = "☀︎" if kind == "sun" else "☾"
    return (
        f'<g class="body-marker body-{kind}" role="img" aria-label="{_esc(label)}" tabindex="0">'
        f'<title>{_esc(label)}</title><text class="{kind}-glyph" x="{x:.1f}" y="{y:.1f}" text-anchor="middle" dominant-baseline="central">{glyph}</text>'
        f'<text x="{x + 13:.1f}" y="{y + 4:.1f}">{_esc(label)}</text></g>'
    )


def _fov_boundary(at_time: datetime, telescope: TelescopeConfig, cx: float, cy: float, radius: float, display_frame: str = "altaz") -> str:
    """Trace a true spherical FoV boundary through the same map projection."""
    boundary = SkyCoord(
        az=telescope.pointing_azimuth_deg * u.deg,
        alt=telescope.pointing_altitude_deg * u.deg,
        frame=AltAz(obstime=Time(_utc(at_time)), location=telescope.location, pressure=0 * u.hPa),
    ).directional_offset_by(np.linspace(0, 2 * np.pi, 145) * u.rad, telescope.fov_radius_deg * u.deg)
    points = []
    center = _zenith_coordinate(at_time, telescope).transform_to(J2000_FRAME if display_frame == "j2000" else "galactic")
    for altitude, azimuth in zip(boundary.alt.deg, boundary.az.deg):
        if display_frame == "altaz":
            x, y, _ = _polar(float(altitude), float(azimuth), cx, cy, radius)
        else:
            altaz_frame = AltAz(obstime=Time(_utc(at_time)), location=telescope.location, pressure=0 * u.hPa)
            coordinate = SkyCoord(az=float(azimuth) * u.deg, alt=float(altitude) * u.deg, frame=altaz_frame)
            x, y, _, _ = _project_coordinate(coordinate.transform_to(J2000_FRAME if display_frame == "j2000" else "galactic"), center, cx, cy, radius, float(altitude) >= 0.0)
        points.append(f"{x:.2f},{y:.2f}")
    return " ".join(points)


def render_all_sky_svg(
    sources: Iterable[Source], at_time: datetime, constraints: ConstraintSet,
    selected_index: Optional[int] = None, telescope: TelescopeConfig = LACT_TELESCOPE,
    language: str = "en", highlighted_indexes: Optional[Iterable[int]] = None,
    trajectory_end: Optional[datetime] = None,
    trajectory_enforce_current_pointing: bool = True,
    trajectory_ranges: Optional[Iterable[tuple[datetime, datetime]]] = None,
    trajectory_display_time: Optional[datetime] = None,
    display_frame: str = "altaz",
) -> tuple[str, dict]:
    """Render a bilingual instantaneous or trajectory-status all-sky map."""
    display_frame = _normalise_display_frame(display_frame)
    sources = list(sources)
    highlighted = set(highlighted_indexes or ())
    text = _labels(language)
    snapshot = (sky_trajectory_snapshot(
        sources, at_time, trajectory_end, constraints, telescope,
        enforce_current_pointing=trajectory_enforce_current_pointing,
        time_ranges=list(trajectory_ranges) if trajectory_ranges is not None else None,
        display_time=trajectory_display_time,
    ) if trajectory_end is not None else sky_snapshot(sources, at_time, constraints, telescope))
    width, height = 760.0, 700.0
    cx, cy, radius = 350.0, 335.0, 260.0
    lines = [
        f'<svg class="sky-map-svg" data-display-frame="{_esc(display_frame)}" viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="{_esc(telescope.name)} {_esc(_display_label(display_frame))} map">',
        f'<title>{_esc(telescope.name)} {_esc(_display_label(display_frame))} map</title>',
        f'<desc>{_esc(_display_label(display_frame))} display; the centre is the zenith reference and the outer circle is the 90 degree display boundary.</desc>',
        '<defs><clipPath id="sky-clip"><circle cx="350" cy="335" r="260" /></clipPath></defs>',
        f'<circle class="sky-surface" cx="{cx}" cy="{cy}" r="{radius}" />',
    ]
    for fraction, label in ((1 / 3, "60°"), (2 / 3, "30°"), (1.0, text["horizon"])):
        ring_radius = radius * fraction
        lines.append(f'<circle class="sky-grid" cx="{cx}" cy="{cy}" r="{ring_radius:.1f}" />')
        if fraction == 1.0:
            lines.append(f'<text class="ring-label horizon-label" x="{cx - radius * .92:.1f}" y="{cy - radius * .62:.1f}" text-anchor="middle">{_esc(label)}</text>')
        else:
            lines.append(f'<text class="ring-label" x="{cx + ring_radius + 5:.1f}" y="{cy + 4:.1f}">{label}</text>')
    for azimuth, key in ((0, "north"), (90, "east"), (180, "south"), (270, "west")):
        x, y, _ = _polar(0, azimuth, cx, cy, radius)
        lines.append(f'<line class="sky-spoke" x1="{cx}" y1="{cy}" x2="{cx + (x-cx)*.96:.1f}" y2="{cy + (y-cy)*.96:.1f}" />')
        lines.append(f'<text class="compass-label" x="{cx + (x-cx)*1.08:.1f}" y="{cy + (y-cy)*1.08 + 5:.1f}" text-anchor="middle">{text[key]}</text>')

    pointing_x, pointing_y, _ = _polar(telescope.pointing_altitude_deg, telescope.pointing_azimuth_deg, cx, cy, radius)
    lines.append(f'<polyline class="realtime-fov-ring" points="{_fov_boundary(at_time, telescope, cx, cy, radius, display_frame)}" role="img" aria-label="{_esc(telescope.name)} FoV, diameter {telescope.fov_diameter_deg:.2f} degrees" tabindex="0"><title>{_esc(telescope.name)} FoV: {telescope.fov_diameter_deg:.2f}° diameter</title></polyline>')
    lines.append(f'<text class="realtime-fov-label" x="{pointing_x:.1f}" y="{pointing_y + 31:.1f}" text-anchor="middle">{_esc(telescope.name)} FoV</text>')

    visible_count = below_count = 0
    source_by_index = {source.index: source for source in sources}
    for item in snapshot["sources"]:
        geometry = item["geometry"]
        item_source = source_by_index[item["index"]]
        x, y, visible, _ = _project_source(item_source, geometry, at_time, telescope, display_frame, cx, cy, radius)
        if not visible and trajectory_end is None and item["index"] != selected_index:
            below_count += 1
            continue
        if not visible:
            # Observation-window sources and the selected planning target stay
            # represented at the horizon boundary even when below the horizon.
            if display_frame == "altaz":
                x, y, _ = _polar(0.0, float(geometry["target_azimuth_deg"]), cx, cy, radius)
            below_count += 1
        else:
            visible_count += 1
        status = STATUS_CLASS.get(item["status"], "red")
        selected = " selected-source" if item["index"] == selected_index else ""
        highlight = " trajectory-highlight" if item["index"] in highlighted else ""
        title = f'{item["display_name"]} | {item["status"]}'
        if item_source.is_calibration_star:
            shape = f'<polygon points="{_star_points(x, y, 8.0, 3.2)}" />'
        else:
            extension_radius = max(2.5, min(18.0, 2.5 + float(item_source.ext) * 3.0))
            shape = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{extension_radius:.1f}" />'
        lines.append(f'<g class="source-marker source-type-{_esc(item_source.source_type)} status-{status}{selected}{highlight}" data-source-index="{item["index"]}" tabindex="0" role="button" aria-label="{_esc(title)}"><title>{_esc(title)}</title>{shape}</g>')
    if snapshot["sources"]:
        geometry = snapshot["sources"][0]["geometry"]
        for kind in ("sun", "moon"):
            altitude = float(geometry[f"{kind}_altitude_deg"])
            if altitude >= 0.0:
                x, y, _, _ = _project_body(altitude, float(geometry[f"{kind}_azimuth_deg"]), at_time, telescope, display_frame, cx, cy, radius)
                lines.append(_body_icon(x, y, kind, text[kind]))
        snapshot["sun"] = {"altitude_deg": geometry["sun_altitude_deg"], "azimuth_deg": geometry["sun_azimuth_deg"]}
        snapshot["moon"] = {"altitude_deg": geometry["moon_altitude_deg"], "azimuth_deg": geometry["moon_azimuth_deg"]}
    lines.append("</svg>")
    snapshot.update({"display_frame": display_frame, "display_frame_label": _display_label(display_frame), "visible_source_count": visible_count, "below_horizon_source_count": below_count, "lact_pointing": {"mode": telescope.pointing_mode, "altitude_deg": telescope.pointing_altitude_deg, "azimuth_deg": telescope.pointing_azimuth_deg, "fov_diameter_deg": telescope.fov_diameter_deg, "fov_radius_deg": telescope.fov_radius_deg}, "highlighted_source_indexes": sorted(highlighted)})
    return "".join(lines), snapshot


def _local_position(center, other) -> tuple[float, float]:
    return float(center.separation(other).to_value(u.deg)), float(center.position_angle(other).to_value(u.deg))


def render_local_fov_svg(
    source: Source, sources: Iterable[Source], at_time: datetime,
    selected_status: Optional[dict] = None, telescope: TelescopeConfig = LACT_TELESCOPE,
    language: str = "en",
) -> str:
    """Render a target-centred local FoV; below-horizon bodies are hidden."""
    del selected_status
    text = _labels(language)
    time = Time(_utc(at_time))
    frame = AltAz(obstime=time, location=telescope.location, pressure=0 * u.hPa)
    center = source_coord(source).transform_to(frame)
    sun = get_sun(time).transform_to(frame)
    moon = get_body("moon", time, telescope.location).transform_to(frame)
    view_radius_deg, cx, cy, diagram_radius = max(6.5, telescope.fov_radius_deg * 1.4), 330.0, 300.0, 235.0
    scale = diagram_radius / view_radius_deg
    lines = [
        '<svg class="fov-map-svg" viewBox="0 0 680 620" role="img" aria-label="Telescope local FoV map">',
        '<title>Telescope local FoV map</title>',
        f'<desc>Centre is selected source; circle is a {telescope.fov_diameter_deg:.2f} degree hard FoV.</desc>',
        f'<circle class="fov-surface" cx="{cx}" cy="{cy}" r="{diagram_radius}" />',
        f'<circle class="fov-ring" cx="{cx}" cy="{cy}" r="{telescope.fov_radius_deg * scale:.1f}" />',
        f'<circle class="fov-crosshair" cx="{cx}" cy="{cy}" r="3" />',
        f'<line class="fov-axis" x1="{cx}" y1="{cy - diagram_radius}" x2="{cx}" y2="{cy + diagram_radius}" />',
        f'<line class="fov-axis" x1="{cx - diagram_radius}" y1="{cy}" x2="{cx + diagram_radius}" y2="{cy}" />',
        f'<text class="fov-label" x="{cx}" y="{cy - diagram_radius - 10}" text-anchor="middle">{text["north_local"]}</text>',
        f'<text class="fov-label" x="{cx + diagram_radius + 12}" y="{cy + 4}">{text["east_local"]}</text>',
        f'<text class="fov-ring-label" x="{cx + telescope.fov_radius_deg * scale + 8:.1f}" y="{cy + 4:.1f}">{text["radius"]} {telescope.fov_radius_deg:.2f}°</text>',
        f'<text class="selected-label" x="{cx}" y="{cy + diagram_radius + 34}" text-anchor="middle">{_esc(source.display_name)}</text>',
    ]
    ext_radius = min(max(source.ext, 0.0), view_radius_deg) * scale
    if source.ext > 0:
        lines.append(f'<circle class="extension-ring" cx="{cx}" cy="{cy}" r="{ext_radius:.1f}" />')
        if source.ext > view_radius_deg:
            lines.append(f'<text class="warning-label" x="20" y="570">{text["extension_outside"]}: {source.ext:.3f}°</text>')
    for candidate in sources:
        candidate_altaz = source_coord(candidate).transform_to(frame)
        separation, position_angle = _local_position(center, candidate_altaz)
        if separation > view_radius_deg and candidate.index != source.index:
            continue
        angle = math.radians(position_angle)
        x, y = cx + separation * scale * math.sin(angle), cy - separation * scale * math.cos(angle)
        css = "local-selected-star" if candidate.index == source.index else "local-source-star"
        outer, inner = (9, 4) if candidate.index == source.index else (6, 2.5)
        extra = '' if candidate.index == source.index else ' tabindex="0" role="button"'
        lines.append(f'<polygon class="{css}" points="{_star_points(x, y, outer, inner)}" data-source-index="{candidate.index}"{extra} />')
    for body, kind in ((sun, "sun"), (moon, "moon")):
        if float(body.alt.deg) < 0.0:
            continue
        separation, position_angle = _local_position(center, body)
        if separation <= view_radius_deg:
            angle = math.radians(position_angle)
            x, y = cx + separation * scale * math.sin(angle), cy - separation * scale * math.cos(angle)
            lines.append(_body_icon(x, y, kind, f'{text[kind]} {separation:.1f}°'))
    lines.append("</svg>")
    return "".join(lines)
