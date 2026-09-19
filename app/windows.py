from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import inspect
from typing import Iterable, List, Sequence

import numpy as np
from astropy.time import Time

from .astronomy import GeometrySeries, compute_catalog_geometry, compute_geometry
from .catalog import Source
from .config import (
    BOUNDARY_TOLERANCE_SECONDS,
    DEFAULT_GRID_STEP_SECONDS,
    LACT_TELESCOPE,
    MAX_GRID_POINTS,
    TelescopeConfig,
    WINDOW_SCAN_CHUNK_SECONDS,
)
from .constraints import ConstraintEvaluation, scalar_evaluation, evaluate_constraints
from .schemas import ConstraintSet


@dataclass
class WindowInterval:
    start: datetime
    end: datetime
    duration_seconds: float
    start_reason: str
    end_reason: str
    minimum_target_zenith_deg: float
    maximum_sun_altitude_deg: float
    minimum_moon_separation_deg: float
    plan_start: datetime | None = None
    plan_end: datetime | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["start"] = iso_utc(self.start)
        payload["end"] = iso_utc(self.end)
        payload["duration_seconds"] = round(self.duration_seconds, 3)
        payload["plan_start"] = iso_utc(self.plan_start) if self.plan_start else None
        payload["plan_end"] = iso_utc(self.plan_end) if self.plan_end else None
        for key in (
            "minimum_target_zenith_deg",
            "maximum_sun_altitude_deg",
            "minimum_moon_separation_deg",
        ):
            payload[key] = round(float(payload[key]), 5)
        return payload


@dataclass
class WindowResult:
    source: Source
    start: datetime
    end: datetime
    constraints: ConstraintSet
    sample_times: List[datetime]
    series: GeometrySeries
    center_windows: List[WindowInterval]
    full_footprint_windows: List[WindowInterval]
    warnings: List[str]
    # Exact observer/FoV context used for every calculated interval.
    telescope: TelescopeConfig = LACT_TELESCOPE

    def __post_init__(self):
        if not self.source.footprint_known:
            self.full_footprint_windows = []
            self.warnings = [*self.warnings, "full_footprint_not_evaluated: supply an explicit nominal radius to assess a footprint"]

    def to_dict(self, max_samples: int = 1200) -> dict:
        sample_indices = _downsample_indices(len(self.sample_times), max_samples)
        samples = []
        for index in sample_indices:
            item = self.series.at(index)
            item["time"] = iso_utc(self.sample_times[index])
            samples.append(item)
        return {
            "geometry_only": True,
            "full_footprint_evaluated": self.source.footprint_known,
            "footprint_assessment": "nominal_radius" if self.source.footprint_known else "full_footprint_not_evaluated",
            "source": self.source.to_dict(),
            "start": iso_utc(self.start),
            "end": iso_utc(self.end),
            "constraints": self.constraints.model_dump(),
            "enabled_constraints": self.constraints.enabled_labels(),
            "samples": samples,
            "center_windows": [window.to_dict() for window in self.center_windows],
            "full_footprint_windows": [
                window.to_dict() for window in self.full_footprint_windows
            ],
            "warnings": self.warnings,
            "telescope": self.telescope.to_dict(),
        }


def iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _geometry_for_telescope(source: Source, values, telescope: TelescopeConfig) -> GeometrySeries:
    """Call production geometry with telescope context and retain test-spy compatibility.

    The deployed astronomy adapter takes ``(source, values, telescope)``. A few
    isolated numerical tests replace it with historic two-argument synthetic
    functions. Signature inspection avoids masking a true TypeError thrown by
    the production astronomy code while keeping those synthetic tests focused.
    """
    if len(inspect.signature(compute_geometry).parameters) >= 3:
        return compute_geometry(source, values, telescope)
    return compute_geometry(source, values)


def _catalogue_geometry_for_telescope(
    sources: Sequence[Source], values, telescope: TelescopeConfig
):
    """Catalogue counterpart preserving legacy two-argument test doubles."""
    if len(inspect.signature(compute_catalog_geometry).parameters) >= 3:
        return compute_catalog_geometry(sources, values, telescope)
    return compute_catalog_geometry(sources, values)


def _effective_grid_step(constraints: ConstraintSet, requested_step: int) -> int:
    """Choose a complete one-second candidate grid for the bounded request."""
    del constraints, requested_step
    # A one-second cadence is intentionally used for the candidate grid. The
    # request duration is bounded to thirty days, so 2,592,001 samples fit below
    # the explicit MAX_GRID_POINTS guard; geometry remains chunked. Vectorized Astropy evaluation makes each
    # retained short window observable rather than assuming it cannot occur
    # between coarse samples.
    return 1


def _grid(start: datetime, end: datetime, step_seconds: int) -> List[datetime]:
    start = _as_utc(start)
    end = _as_utc(end)
    if step_seconds <= 0:
        raise ValueError("grid step must be positive")
    total = (end - start).total_seconds()
    count = int(np.floor(total / step_seconds)) + 1
    if count > MAX_GRID_POINTS:
        raise ValueError("requested time range produces too many samples")
    values = [start + timedelta(seconds=i * step_seconds) for i in range(count)]
    if values[-1] < end:
        values.append(end)
    elif values[-1] > end:
        values[-1] = end
    return values


def _append_geometry_series(parts: List[GeometrySeries], series: GeometrySeries) -> None:
    """Append a chunk while removing its duplicated left boundary sample."""
    if not parts:
        parts.append(series)
        return
    # Adjacent chunks share exactly one timestamp. Rebuild the aggregate only
    # after all chunks have been calculated, so Astropy never holds an entire
    # day of intermediate coordinate objects at once.
    parts.append(
        GeometrySeries(
            times=series.times[1:],
            unix_seconds=series.unix_seconds[1:],
            target_altitude_deg=series.target_altitude_deg[1:],
            target_azimuth_deg=series.target_azimuth_deg[1:],
            target_zenith_deg=series.target_zenith_deg[1:],
            target_pointing_separation_deg=series.target_pointing_separation_deg[1:],
            sun_altitude_deg=series.sun_altitude_deg[1:],
            sun_azimuth_deg=series.sun_azimuth_deg[1:],
            moon_altitude_deg=series.moon_altitude_deg[1:],
            moon_azimuth_deg=series.moon_azimuth_deg[1:],
            moon_separation_deg=series.moon_separation_deg[1:],
            sun_separation_deg=series.sun_separation_deg[1:],
            warnings=series.warnings,
        )
    )


def _combine_geometry_series(parts: Sequence[GeometrySeries]) -> GeometrySeries:
    """Concatenate chunked geometry arrays into the normal result contract."""
    if not parts:
        raise ValueError("at least one geometry chunk is required")
    first = parts[0]
    warnings = sorted({warning for part in parts for warning in part.warnings})
    return GeometrySeries(
        times=Time(np.concatenate([np.atleast_1d(part.times.jd) for part in parts]), format="jd", scale=first.times.scale),
        unix_seconds=np.concatenate([part.unix_seconds for part in parts]),
        target_altitude_deg=np.concatenate([part.target_altitude_deg for part in parts]),
        target_azimuth_deg=np.concatenate([part.target_azimuth_deg for part in parts]),
        target_zenith_deg=np.concatenate([part.target_zenith_deg for part in parts]),
        target_pointing_separation_deg=np.concatenate([part.target_pointing_separation_deg for part in parts]),
        sun_altitude_deg=np.concatenate([part.sun_altitude_deg for part in parts]),
        sun_azimuth_deg=np.concatenate([part.sun_azimuth_deg for part in parts]),
        moon_altitude_deg=np.concatenate([part.moon_altitude_deg for part in parts]),
        moon_azimuth_deg=np.concatenate([part.moon_azimuth_deg for part in parts]),
        moon_separation_deg=np.concatenate([part.moon_separation_deg for part in parts]),
        sun_separation_deg=np.concatenate([part.sun_separation_deg for part in parts]),
        warnings=warnings,
    )


def _chunked_geometry(
    source: Source,
    start: datetime,
    end: datetime,
    telescope: TelescopeConfig = LACT_TELESCOPE,
) -> tuple[List[datetime], GeometrySeries]:
    """Evaluate one-second geometry in bounded chunks, retaining every second."""
    times: List[datetime] = []
    parts: List[GeometrySeries] = []
    chunk_start = start
    first_chunk = True
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(seconds=WINDOW_SCAN_CHUNK_SECONDS), end)
        chunk_times = _grid(chunk_start, chunk_end, 1)
        chunk_series = _geometry_for_telescope(source, chunk_times, telescope)
        if first_chunk:
            times.extend(chunk_times)
            parts.append(chunk_series)
            first_chunk = False
        else:
            times.extend(chunk_times[1:])
            _append_geometry_series(parts, chunk_series)
        chunk_start = chunk_end
    if not parts:
        # The schema forbids an empty range, but retain a deterministic helper
        # behavior for pure-Python callers.
        only_times = _grid(start, end, 1)
        return only_times, _geometry_for_telescope(source, only_times, telescope)
    # Test doubles and short production requests may consist of one chunk.
    # Returning it verbatim also avoids requiring non-production series types
    # to expose Astropy's ``times`` attribute merely for unit testing.
    if len(parts) == 1:
        return times, parts[0]
    return times, _combine_geometry_series(parts)
def _downsample_indices(length: int, maximum: int) -> List[int]:
    if length <= maximum:
        return list(range(length))
    return sorted(set(np.linspace(0, length - 1, maximum).round().astype(int).tolist()))


def _margin_names(evaluation: ConstraintEvaluation, kind: str) -> List[str]:
    return list(
        (evaluation.center_margins if kind == "center" else evaluation.footprint_margins).keys()
    )


def _margin_value(
    source: Source,
    timestamp: datetime,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    name: str,
    telescope: TelescopeConfig,
) -> float:
    geometry = _geometry_for_telescope(source, timestamp, telescope).at(0)
    evaluation = scalar_evaluation(
        geometry, extension, constraints, fov_radius_deg=telescope.fov_radius_deg
    )
    margins = evaluation.center_margins if kind == "center" else evaluation.footprint_margins
    return float(margins[name][0])


def _bisect_root(
    source: Source,
    left: datetime,
    right: datetime,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    name: str,
    telescope: TelescopeConfig,
) -> datetime:
    left_value = _margin_value(source, left, extension, constraints, kind, name, telescope)
    right_value = _margin_value(source, right, extension, constraints, kind, name, telescope)
    if left_value == 0.0:
        return left
    if right_value == 0.0:
        return right
    if left_value * right_value > 0:
        return left if abs(left_value) < abs(right_value) else right
    while (right - left).total_seconds() > BOUNDARY_TOLERANCE_SECONDS:
        middle = left + (right - left) / 2
        middle_value = _margin_value(source, middle, extension, constraints, kind, name, telescope)
        if middle_value == 0.0:
            return middle
        if left_value * middle_value <= 0:
            right, right_value = middle, middle_value
        else:
            left, left_value = middle, middle_value
    return left + (right - left) / 2

def _candidate_boundaries(
    source: Source,
    times: Sequence[datetime],
    evaluation: ConstraintEvaluation,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    telescope: TelescopeConfig,
) -> List[datetime]:
    margins = evaluation.center_margins if kind == "center" else evaluation.footprint_margins
    boundaries: List[datetime] = []
    for name, values in margins.items():
        values = np.asarray(values, dtype=float)
        for index in range(len(times) - 1):
            left_value = float(values[index])
            right_value = float(values[index + 1])
            if left_value == 0.0:
                boundaries.append(times[index])
            if left_value * right_value < 0.0 or right_value == 0.0:
                boundaries.append(
                    _bisect_root(
                        source,
                        times[index],
                        times[index + 1],
                        extension,
                        constraints,
                        kind,
                        name,
                        telescope,
                    )
                )
        if len(times) and float(values[-1]) == 0.0:
            boundaries.append(times[-1])
    return boundaries


def _dedupe_times(values: Iterable[datetime]) -> List[datetime]:
    result: List[datetime] = []
    for value in sorted(values):
        if not result or (value - result[-1]).total_seconds() > 0.5:
            result.append(value)
    return result


def _failure_labels_at(
    source: Source,
    timestamp: datetime,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    telescope: TelescopeConfig,
) -> List[str]:
    geometry = _geometry_for_telescope(source, timestamp, telescope).at(0)
    return scalar_evaluation(
        geometry, extension, constraints, fov_radius_deg=telescope.fov_radius_deg
    ).failure_labels(kind, 0)


def _reason_for_start(
    source: Source,
    timestamp: datetime,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    range_start: datetime,
    telescope: TelescopeConfig,
) -> str:
    if timestamp == range_start:
        return "range_start"
    before = timestamp - timedelta(seconds=2)
    before_failures = _failure_labels_at(source, before, extension, constraints, kind, telescope)
    if before_failures:
        # At a start boundary the condition changes from failing to passing.
        # Returning "passed" together with the previous failure name was
        # contradictory in the UI (for example "passed: sun_altitude").
        return "became_valid_after: " + ", ".join(before_failures)
    return "constraint_boundary"


def _reason_for_end(
    source: Source,
    timestamp: datetime,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    range_end: datetime,
    telescope: TelescopeConfig,
) -> str:
    if timestamp == range_end:
        return "range_end"
    after = timestamp + timedelta(seconds=2)
    failures = _failure_labels_at(source, after, extension, constraints, kind, telescope)
    if failures:
        return "became_invalid_after: " + ", ".join(failures)
    return "constraint_boundary"


def _interval_metrics(series: GeometrySeries, times: Sequence[datetime], left: datetime, right: datetime) -> tuple[float, float, float]:
    unix = series.unix_seconds
    left_ts = left.timestamp()
    right_ts = right.timestamp()
    mask = (unix >= left_ts) & (unix <= right_ts)
    if not bool(mask.any()):
        midpoint = left + (right - left) / 2
        # The caller normally has grid points in range. This fallback keeps
        # metadata useful for sub-second intervals.
        return 0.0, 0.0, 0.0
    return (
        float(np.min(series.target_zenith_deg[mask])),
        float(np.max(series.sun_altitude_deg[mask])),
        float(np.min(series.moon_separation_deg[mask])),
    )


def _first_valid_second(
    source: Source,
    start: datetime,
    end: datetime,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    telescope: TelescopeConfig,
) -> datetime | None:
    """Return an inward whole-second endpoint only when it passes geometry.

    The window root is sub-second. A browser ``datetime-local`` input has only
    second precision, so checking the first inward candidate prevents a plan
    default from landing on the invalid side. If no representable instant
    exists, ``None`` tells the UI not to offer a misleading plan button.
    """
    moment = start.replace(microsecond=0)
    if moment < start:
        moment += timedelta(seconds=1)
    if moment > end:
        return None
    geometry = _geometry_for_telescope(source, moment, telescope).at(0)
    evaluation = scalar_evaluation(
        geometry, extension, constraints, fov_radius_deg=telescope.fov_radius_deg
    )
    passed = bool(evaluation.center_pass[0] if kind == "center" else evaluation.footprint_pass[0])
    return moment if passed else None


def _last_valid_second(
    source: Source,
    start: datetime,
    end: datetime,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    telescope: TelescopeConfig,
) -> datetime | None:
    """Return the latest whole-second instant satisfying one interval."""
    moment = end.replace(microsecond=0)
    if moment < start:
        return None
    geometry = _geometry_for_telescope(source, moment, telescope).at(0)
    evaluation = scalar_evaluation(
        geometry, extension, constraints, fov_radius_deg=telescope.fov_radius_deg
    )
    passed = bool(evaluation.center_pass[0] if kind == "center" else evaluation.footprint_pass[0])
    return moment if passed else None

def _build_intervals(
    source: Source,
    start: datetime,
    end: datetime,
    times: Sequence[datetime],
    series: GeometrySeries,
    coarse_evaluation: ConstraintEvaluation,
    extension: float,
    constraints: ConstraintSet,
    kind: str,
    telescope: TelescopeConfig,
) -> List[WindowInterval]:
    boundaries = _dedupe_times(
        [start, end]
        + _candidate_boundaries(
            source, times, coarse_evaluation, extension, constraints, kind, telescope
        )
    )
    intervals: List[WindowInterval] = []
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        if right <= left:
            continue
        midpoint = left + (right - left) / 2
        geometry = _geometry_for_telescope(source, midpoint, telescope).at(0)
        evaluation = scalar_evaluation(
            geometry, extension, constraints, fov_radius_deg=telescope.fov_radius_deg
        )
        passed = bool(
            evaluation.center_pass[0] if kind == "center" else evaluation.footprint_pass[0]
        )
        if not passed:
            continue
        duration = (right - left).total_seconds()
        if duration < constraints.minimum_duration:
            continue
        minimum_z, maximum_sun, minimum_moon = _interval_metrics(
            series, times, left, right
        )
        plan_start = _first_valid_second(
            source, left, right, extension, constraints, kind, telescope
        )
        plan_end = _last_valid_second(
            source, left, right, extension, constraints, kind, telescope
        )
        # A sub-second mathematical interval may contain fewer than two
        # representable valid seconds. Keep it in the scientific result, but
        # do not advertise a zero-length downloadable observation plan.
        if plan_start is not None and plan_end is not None and plan_start >= plan_end:
            plan_start = plan_end = None
        intervals.append(
            WindowInterval(
                start=left,
                end=right,
                duration_seconds=duration,
                start_reason=_reason_for_start(
                    source, left, extension, constraints, kind, start, telescope
                ),
                end_reason=_reason_for_end(
                    source, right, extension, constraints, kind, end, telescope
                ),
                minimum_target_zenith_deg=minimum_z,
                maximum_sun_altitude_deg=maximum_sun,
                minimum_moon_separation_deg=minimum_moon,
                plan_start=plan_start,
                plan_end=plan_end,
            )
        )
    # Adjacent intervals can result from a root shared by two constraints.
    merged: List[WindowInterval] = []
    for interval in intervals:
        if merged and abs((interval.start - merged[-1].end).total_seconds()) <= 1.0:
            previous = merged[-1]
            previous.end = interval.end
            previous.duration_seconds = (previous.end - previous.start).total_seconds()
            previous.end_reason = interval.end_reason
            previous.plan_start = previous.plan_start or interval.plan_start
            previous.plan_end = interval.plan_end
            previous.minimum_target_zenith_deg = min(
                previous.minimum_target_zenith_deg, interval.minimum_target_zenith_deg
            )
            previous.maximum_sun_altitude_deg = max(
                previous.maximum_sun_altitude_deg, interval.maximum_sun_altitude_deg
            )
            previous.minimum_moon_separation_deg = min(
                previous.minimum_moon_separation_deg, interval.minimum_moon_separation_deg
            )
        else:
            merged.append(interval)
    return merged


def calculate_windows_from_series(
    source: Source,
    start: datetime,
    end: datetime,
    constraints: ConstraintSet,
    times: Sequence[datetime],
    series: GeometrySeries,
    telescope: TelescopeConfig = LACT_TELESCOPE,
) -> WindowResult:
    """Build one source's windows from already-computed site geometry.

    This is used by the legacy fixed-FoV bulk endpoint, where Sun and Moon are
    common to every candidate and target coordinates can be transformed in one
    vectorized catalogue call. Its inputs retain the same per-second sampling
    contract as :func:`calculate_windows`.
    """
    start = _as_utc(start)
    end = _as_utc(end)
    evaluation = evaluate_constraints(
        series.target_altitude_deg,
        series.target_zenith_deg,
        series.sun_altitude_deg,
        series.moon_separation_deg,
        source.ext,
        constraints,
        fov_radius_deg=telescope.fov_radius_deg,
    )
    center_windows = _build_intervals(
        source, start, end, times, series, evaluation, 0.0, constraints, "center", telescope
    )
    full_windows = _build_intervals(
        source, start, end, times, series, evaluation, source.ext, constraints, "footprint", telescope
    )
    return WindowResult(
        source=source,
        start=start,
        end=end,
        constraints=constraints,
        sample_times=list(times),
        series=series,
        center_windows=center_windows,
        full_footprint_windows=full_windows,
        warnings=list(series.warnings),
        telescope=telescope,
    )


def calculate_catalogue_windows(
    sources: Sequence[Source],
    start: datetime,
    end: datetime,
    constraints: ConstraintSet,
    telescope: TelescopeConfig = LACT_TELESCOPE,
) -> List[WindowResult]:
    """Compute same-period windows for a small catalogue subset efficiently.

    The fixed-FoV compatibility route can contain several sources. Transform
    them jointly by ten-minute batches so Sun/Moon ephemerides are shared and
    a one-day bulk request remains practical without relaxing the one-second
    discovery guarantee.
    """
    start = _as_utc(start)
    end = _as_utc(end)
    if not sources:
        return []
    times: List[datetime] = []
    target_altitude_parts = [[] for _ in sources]
    target_azimuth_parts = [[] for _ in sources]
    target_zenith_parts = [[] for _ in sources]
    target_pointing_separation_parts = [[] for _ in sources]
    moon_separation_parts = [[] for _ in sources]
    sun_separation_parts = [[] for _ in sources]
    sun_altitude_parts: List[np.ndarray] = []
    sun_azimuth_parts: List[np.ndarray] = []
    moon_altitude_parts: List[np.ndarray] = []
    moon_azimuth_parts: List[np.ndarray] = []
    warnings: set[str] = set()
    chunk_start = start
    first_chunk = True
    while chunk_start < end:
        chunk_end = min(chunk_start + timedelta(seconds=WINDOW_SCAN_CHUNK_SECONDS), end)
        chunk_times = _grid(chunk_start, chunk_end, 1)
        catalogue_series = _catalogue_geometry_for_telescope(sources, chunk_times, telescope)
        offset = 0 if first_chunk else 1
        times.extend(chunk_times[offset:])
        for index in range(len(sources)):
            target_altitude_parts[index].append(catalogue_series.target_altitude_deg[index, offset:])
            target_azimuth_parts[index].append(catalogue_series.target_azimuth_deg[index, offset:])
            target_zenith_parts[index].append(catalogue_series.target_zenith_deg[index, offset:])
            # Synthetic catalogue fixtures written before current-pointing
            # support do not expose this optional array. A zero fallback is
            # safe here because ordinary catalogue window calculation never
            # enforces current pointing; production geometry always provides it.
            pointing = catalogue_series.target_pointing_separation_deg
            target_pointing_separation_parts[index].append(
                pointing[index, offset:] if pointing is not None
                else np.zeros_like(catalogue_series.target_altitude_deg[index, offset:])
            )
            moon_separation_parts[index].append(catalogue_series.moon_separation_deg[index, offset:])
            sun_separation_parts[index].append(catalogue_series.sun_separation_deg[index, offset:])
        sun_altitude_parts.append(catalogue_series.sun_altitude_deg[offset:])
        sun_azimuth_parts.append(catalogue_series.sun_azimuth_deg[offset:])
        moon_altitude_parts.append(catalogue_series.moon_altitude_deg[offset:])
        moon_azimuth_parts.append(catalogue_series.moon_azimuth_deg[offset:])
        warnings.update(catalogue_series.warnings)
        first_chunk = False
        chunk_start = chunk_end
    unix_seconds = np.asarray([moment.timestamp() for moment in times], dtype=float)
    shared = {
        "times": Time(unix_seconds, format="unix", scale="utc"),
        "unix_seconds": unix_seconds,
        "sun_altitude_deg": np.concatenate(sun_altitude_parts),
        "sun_azimuth_deg": np.concatenate(sun_azimuth_parts),
        "moon_altitude_deg": np.concatenate(moon_altitude_parts),
        "moon_azimuth_deg": np.concatenate(moon_azimuth_parts),
        "warnings": sorted(warnings),
    }
    results: List[WindowResult] = []
    for index, source in enumerate(sources):
        series = GeometrySeries(
            **shared,
            target_altitude_deg=np.concatenate(target_altitude_parts[index]),
            target_azimuth_deg=np.concatenate(target_azimuth_parts[index]),
            target_zenith_deg=np.concatenate(target_zenith_parts[index]),
            target_pointing_separation_deg=np.concatenate(target_pointing_separation_parts[index]),
            moon_separation_deg=np.concatenate(moon_separation_parts[index]),
            sun_separation_deg=np.concatenate(sun_separation_parts[index]),
        )
        results.append(
            calculate_windows_from_series(source, start, end, constraints, times, series, telescope)
        )
    return results

def calculate_windows(
    source: Source,
    start: datetime,
    end: datetime,
    constraints: ConstraintSet,
    grid_step_seconds: int = DEFAULT_GRID_STEP_SECONDS,
    telescope: TelescopeConfig = LACT_TELESCOPE,
) -> WindowResult:
    """Calculate centre and full-footprint intervals for a single target.

    Every second in the requested interval is evaluated. Detected pass/fail
    transitions are then bisected below one second, which makes the result
    complete for any window at least one sampled second wide, including the
    public default ``minimum_window_seconds=0`` mode.
    """
    start = _as_utc(start)
    end = _as_utc(end)
    grid_step_seconds = _effective_grid_step(constraints, grid_step_seconds)
    # The candidate grid is deliberately one second. It is the only simple,
    # auditable guarantee that a pass/fail excursion cannot disappear entirely
    # between samples when the user asks to retain all durations.
    times, series = _chunked_geometry(source, start, end, telescope)
    evaluation = evaluate_constraints(
        series.target_altitude_deg,
        series.target_zenith_deg,
        series.sun_altitude_deg,
        series.moon_separation_deg,
        source.ext,
        constraints,
        fov_radius_deg=telescope.fov_radius_deg,
    )
    # Keep the series in the result payload because the primary response plots
    # and full-source plan are based on these sampled constraints.
    center_windows = _build_intervals(
        source,
        start,
        end,
        times,
        series,
        evaluation,
        0.0,
        constraints,
        "center",
        telescope,
    )
    full_windows = _build_intervals(
        source,
        start,
        end,
        times,
        series,
        evaluation,
        source.ext,
        constraints,
        "footprint",
        telescope,
    )
    return WindowResult(
        source=source,
        start=start,
        end=end,
        constraints=constraints,
        sample_times=list(times),
        series=series,
        center_windows=center_windows,
        full_footprint_windows=full_windows,
        warnings=list(series.warnings),
        telescope=telescope,
    )
