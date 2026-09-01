from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Sequence

import numpy as np

from .astronomy import CatalogGeometrySeries, compute_catalog_geometry
from .catalog import Source
from .config import FOV_RADIUS_DEG, LACT_TELESCOPE, MAX_STATUS_SAMPLES, TelescopeConfig
from .constraints import evaluate_constraints
from .schemas import ConstraintSet


@dataclass
class SourceStatus:
    source: Source
    status: str
    center_pass: bool
    footprint_pass: bool
    reasons: List[str]
    geometry: dict
    extension_inside_fov: bool
    minimum_window_seconds: int
    telescope: TelescopeConfig
    current_pointing_enforced: bool = False

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "center_pass": self.center_pass,
            "footprint_pass": self.footprint_pass,
            # Reason values intentionally remain stable machine codes in API
            # responses. The local client maps them to bilingual human labels.
            "reasons": self.reasons,
            "geometry": self.geometry,
            "extension_inside_fov": self.extension_inside_fov,
            "minimum_window_seconds": self.minimum_window_seconds,
            "current_pointing_enforced": self.current_pointing_enforced,
            "telescope": self.telescope.to_dict(),
        }


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _reasons(
    center_pass: bool,
    footprint_pass: bool,
    point_failures: Sequence[str],
    footprint_failures: Sequence[str],
    minimum_window_failed_center: bool = False,
    minimum_window_failed_footprint: bool = False,
) -> List[str]:
    """Produce machine-readable reason codes without misleading pass/fail text."""
    reasons: List[str] = []
    if not center_pass:
        reasons.extend("center_" + name for name in point_failures)
        if minimum_window_failed_center:
            reasons.append("center_cannot_hold_for_minimum_window")
    elif not footprint_pass:
        for name in footprint_failures:
            aliases = {
                "extension_inside_fov": "extension_edge_exceeds_fov",
                "extension_inside_current_fov": "extension_edge_exceeds_current_fov",
                "extension_above_horizon": "extension_edge_below_horizon",
                "extension_max_zenith": "extension_edge_exceeds_horizon_limit",
            }
            reasons.append(aliases.get(name, "extension_edge_" + name))
        if minimum_window_failed_footprint:
            reasons.append("extension_cannot_hold_for_minimum_window")
    return reasons or ["all_enabled_geometry_conditions_pass"]


def _from_series(
    sources: Sequence[Source],
    series: CatalogGeometrySeries,
    constraints: ConstraintSet,
    telescope: TelescopeConfig = LACT_TELESCOPE,
    *,
    enforce_current_pointing: bool = False,
) -> List[SourceStatus]:
    """Classify each source from one shared series using exactly one rule set.

    The all-sky map calls this with the telescope pointing requirement enabled.
    Detail/result status uses normal planned-target geometry instead, allowing a
    selected target to be evaluated as the future pointing centre.
    """
    statuses: List[SourceStatus] = []
    for index, source in enumerate(sources):
        # Old test fixtures and non-live callers need no pointing separation.
        # Require it only for the all-sky rendering path that actually enforces
        # the present telescope direction.
        common = {"fov_radius_deg": telescope.fov_radius_deg}
        if enforce_current_pointing:
            common.update(
                target_pointing_separation_deg=series.target_pointing_separation_deg[index],
                enforce_current_pointing=True,
            )
        point_eval = evaluate_constraints(
            series.target_altitude_deg[index],
            series.target_zenith_deg[index],
            series.sun_altitude_deg,
            series.moon_separation_deg[index],
            0.0,
            constraints,
            **common,
        )
        full_eval = evaluate_constraints(
            series.target_altitude_deg[index],
            series.target_zenith_deg[index],
            series.sun_altitude_deg,
            series.moon_separation_deg[index],
            source.ext,
            constraints,
            **common,
        )
        point_now = bool(point_eval.center_pass[0])
        full_now = bool(full_eval.footprint_pass[0])
        center_pass = point_now and bool(np.all(point_eval.center_pass))
        footprint_pass = full_now and bool(np.all(full_eval.footprint_pass))
        reasons = _reasons(
            center_pass,
            footprint_pass,
            point_eval.failure_labels("center", 0),
            full_eval.failure_labels("footprint", 0),
            minimum_window_failed_center=point_now and not center_pass,
            minimum_window_failed_footprint=full_now and not footprint_pass,
        )
        statuses.append(
            SourceStatus(
                source=source,
                status="GREEN" if center_pass and footprint_pass else "YELLOW" if center_pass else "RED",
                center_pass=center_pass,
                footprint_pass=footprint_pass,
                reasons=reasons,
                geometry=series.source_at(index, 0),
                extension_inside_fov=source.ext <= telescope.fov_radius_deg,
                minimum_window_seconds=constraints.minimum_duration,
                telescope=telescope,
                current_pointing_enforced=enforce_current_pointing,
            )
        )
    return statuses


def _status_times(at_time: datetime, constraints: ConstraintSet) -> List[datetime]:
    at_time = _utc(at_time)
    minimum = constraints.minimum_duration
    if not minimum:
        return [at_time]
    sample_count = max(2, min(MAX_STATUS_SAMPLES, minimum // 60 + 2))
    return [
        datetime.fromtimestamp(timestamp, tz=timezone.utc)
        for timestamp in np.linspace(at_time.timestamp(), at_time.timestamp() + minimum, sample_count)
    ]


def source_status(
    source: Source,
    at_time: datetime,
    constraints: ConstraintSet,
    telescope: TelescopeConfig = LACT_TELESCOPE,
    *,
    enforce_current_pointing: bool = False,
) -> SourceStatus:
    series = compute_catalog_geometry([source], _status_times(at_time, constraints), telescope)
    return _from_series(
        [source], series, constraints, telescope, enforce_current_pointing=enforce_current_pointing
    )[0]


def sky_snapshot(
    sources: Iterable[Source],
    at_time: datetime,
    constraints: ConstraintSet,
    telescope: TelescopeConfig = LACT_TELESCOPE,
) -> dict:
    """Return all-sky geometry and current-telescope red/yellow/green states."""
    at_time = _utc(at_time)
    sources = list(sources)
    series = compute_catalog_geometry(sources, _status_times(at_time, constraints), telescope)
    statuses = _from_series(sources, series, constraints, telescope, enforce_current_pointing=True)
    return {
        "at_time": at_time.isoformat().replace("+00:00", "Z"),
        "warnings": series.warnings,
        "telescope": telescope.to_dict(),
        "sources": [
            {
                **status.source.to_dict(),
                "status": status.status,
                "center_pass": status.center_pass,
                "footprint_pass": status.footprint_pass,
                "reasons": status.reasons,
                "geometry": status.geometry,
            }
            for status in statuses
        ],
    }


def sky_trajectory_snapshot(
    sources: Iterable[Source],
    start_time: datetime,
    end_time: datetime,
    constraints: ConstraintSet,
    telescope: TelescopeConfig = LACT_TELESCOPE,
    max_samples: int = 1441,
    enforce_current_pointing: bool = True,
    time_ranges: Sequence[tuple[datetime, datetime]] | None = None,
    display_time: datetime | None = None,
) -> dict:
    """Classify sources by whether their trajectory is ever observable in a range.

    This is a display-summary mode for the result-page all-sky map.  It uses
    vectorised shared ephemerides and never changes the exact per-second window
    result for the selected planning target.  A 60-second-or-finer grid is used
    for a one-day range, preserving practical response time for a 190-source
    catalogue while showing a conservative trajectory overview.
    """
    start = _utc(start_time)
    end = _utc(end_time)
    display_time = _utc(display_time) if display_time is not None else start
    sources = list(sources)
    ranges = [(start, end)] if time_ranges is None else [(_utc(begin), _utc(finish)) for begin, finish in time_ranges]
    if any(finish <= begin for begin, finish in ranges):
        raise ValueError("trajectory ranges must contain forward intervals")
    # An empty explicit list means the selected target has no full-footprint
    # window. Preserve every catalogue row and classify all as unavailable.
    if not ranges:
        empty_series = compute_catalog_geometry(sources, [display_time], telescope)
        items = [{
            **source.to_dict(), "status": "RED", "center_pass": False,
            "footprint_pass": False, "geometry": empty_series.source_at(index, 0),
        } for index, source in enumerate(sources)]
        return {
            "at_time": start.isoformat().replace("+00:00", "Z"),
            "end_time": end.isoformat().replace("+00:00", "Z"),
            "sources": items, "warnings": empty_series.warnings,
            "telescope": telescope.to_dict(), "status_mode": "trajectory",
            "enforce_current_pointing": enforce_current_pointing,
        }
    start = min(begin for begin, _ in ranges)
    end = max(finish for _, finish in ranges)
    times = []
    range_slices = []
    for begin, finish in ranges:
        duration = (finish - begin).total_seconds()
        count = max(2, min(max_samples, int(duration // 60) + 1))
        first = len(times)
        times.extend(datetime.fromtimestamp(value, timezone.utc) for value in np.linspace(begin.timestamp(), finish.timestamp(), count))
        range_slices.append((first, len(times)))
    series = compute_catalog_geometry(sources, times, telescope)
    display_series = compute_catalog_geometry(sources, [display_time], telescope)
    def holds_for_duration(mask: np.ndarray) -> tuple[bool, int]:
        """Find a valid run within one full-footprint interval; never bridge gaps."""
        valid = np.asarray(mask, dtype=bool)
        required = constraints.minimum_duration
        for first, stop in range_slices:
            run_start = None
            for time_index in range(first, stop):
                passes = valid[time_index]
                if passes and run_start is None:
                    run_start = time_index
                if not passes and run_start is not None:
                    if (times[time_index - 1] - times[run_start]).total_seconds() >= required:
                        return True, run_start
                    run_start = None
            if run_start is not None and (times[stop - 1] - times[run_start]).total_seconds() >= required:
                return True, run_start
        return False, 0

    items = []
    for index, source in enumerate(sources):
        common = {"fov_radius_deg": telescope.fov_radius_deg}
        if enforce_current_pointing:
            common.update({
                "target_pointing_separation_deg": series.target_pointing_separation_deg[index],
                "enforce_current_pointing": True,
            })
        centre = evaluate_constraints(series.target_altitude_deg[index], series.target_zenith_deg[index], series.sun_altitude_deg, series.moon_separation_deg[index], 0.0, constraints, **common)
        footprint = evaluate_constraints(series.target_altitude_deg[index], series.target_zenith_deg[index], series.sun_altitude_deg, series.moon_separation_deg[index], source.ext, constraints, **common)
        # Trajectory colours answer whether the enabled constraints can hold
        # continuously for the requested minimum duration, not merely whether
        # one sampled instant happens to pass.
        center_any, center_index = holds_for_duration(centre.center_pass)
        full_any, full_index = holds_for_duration(footprint.footprint_pass)
        del center_index, full_index
        items.append({
            **source.to_dict(),
            "status": "GREEN" if full_any else "YELLOW" if center_any else "RED",
            "center_pass": center_any,
            "footprint_pass": full_any,
            # Every source and solar-system body is drawn at one common
            # display instant; status colours still summarize the full ranges.
            "geometry": display_series.source_at(index, 0),
        })
    return {"at_time": start.isoformat().replace("+00:00", "Z"), "end_time": end.isoformat().replace("+00:00", "Z"), "sources": items, "warnings": series.warnings, "telescope": telescope.to_dict(), "status_mode": "trajectory", "enforce_current_pointing": enforce_current_pointing}
