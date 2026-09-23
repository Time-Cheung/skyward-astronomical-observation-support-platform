from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

import numpy as np

from .astronomy import compute_catalog_geometry
from .catalog import POINT_SOURCE_FALLBACK_WARNING, Source
from .config import LACT_TELESCOPE, TelescopeConfig
from .constraints import evaluate_constraints
from .schemas import ConstraintSet
from .windows import WindowInterval, calculate_windows, iso_utc


MAX_COARSE_SAMPLES = 4321
MAX_COARSE_CANDIDATES = 1000
MAX_EXACT_SPAN_SECONDS = 86_400
SOURCE_CHUNK_SIZE = 128


@dataclass(frozen=True)
class CandidateWindow:
    source: Source
    start: datetime
    end: datetime
    metrics: dict


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def window_metrics(
    target_start: datetime, target_end: datetime,
    candidate_start: datetime, candidate_end: datetime,
) -> dict:
    target_start, target_end = _utc(target_start), _utc(target_end)
    candidate_start, candidate_end = _utc(candidate_start), _utc(candidate_end)
    overlap = max(0.0, (min(target_end, candidate_end) - max(target_start, candidate_start)).total_seconds())
    if overlap:
        gap = 0.0
    elif candidate_end <= target_start:
        gap = (target_start - candidate_end).total_seconds()
    else:
        gap = (candidate_start - target_end).total_seconds()
    target_duration = (target_end - target_start).total_seconds()
    candidate_duration = (candidate_end - candidate_start).total_seconds()
    return {
        "overlap_seconds": round(overlap, 3),
        "gap_seconds": round(max(0.0, gap), 3),
        "target_window_seconds": round(target_duration, 3),
        "candidate_window_seconds": round(candidate_duration, 3),
        "duration_difference_seconds": round(abs(candidate_duration - target_duration), 3),
    }


def metric_sort_key(metrics: dict, source_key: str) -> tuple:
    return (
        -float(metrics["overlap_seconds"]),
        float(metrics["gap_seconds"]),
        float(metrics["duration_difference_seconds"]),
        -float(metrics["candidate_window_seconds"]),
        source_key,
    )


def _sample_times(start: datetime, end: datetime, step_seconds: int) -> list[datetime]:
    duration = (end - start).total_seconds()
    count = int(duration // step_seconds) + 1
    if count > MAX_COARSE_SAMPLES:
        raise ValueError("coarse search exceeds the bounded sample budget")
    times = [start + timedelta(seconds=index * step_seconds) for index in range(count)]
    if times[-1] < end:
        times.append(end)
    return times


def _mask_windows(mask: np.ndarray, times: Sequence[datetime]) -> list[tuple[datetime, datetime]]:
    valid = np.asarray(mask, dtype=bool)
    windows: list[tuple[datetime, datetime]] = []
    first = None
    for index, passes in enumerate(valid):
        if passes and first is None:
            first = index
        if not passes and first is not None:
            finish = max(first + 1, index - 1)
            windows.append((times[first], times[finish]))
            first = None
    if first is not None:
        windows.append((times[first], times[-1]))
    return [(start, end) for start, end in windows if end > start]


def _best_window(
    source: Source,
    windows: Sequence[tuple[datetime, datetime]],
    target_start: datetime,
    target_end: datetime,
) -> CandidateWindow | None:
    candidates = [
        CandidateWindow(source, start, end, window_metrics(target_start, target_end, start, end))
        for start, end in windows if end > start
    ]
    return min(candidates, key=lambda item: metric_sort_key(item.metrics, source.source_key)) if candidates else None


def _exact_bounds(
    candidate: CandidateWindow,
    target_start: datetime,
    target_end: datetime,
    search_start: datetime,
    search_end: datetime,
    step_seconds: int,
    minimum_duration: int,
) -> tuple[datetime, datetime, bool]:
    desired_start = max(search_start, min(candidate.start, target_start) - timedelta(seconds=step_seconds))
    desired_end = min(search_end, max(candidate.end, target_end) + timedelta(seconds=step_seconds))
    maximum = min(MAX_EXACT_SPAN_SECONDS, max(7200, minimum_duration + 2 * step_seconds))
    if (desired_end - desired_start).total_seconds() <= maximum:
        return desired_start, desired_end, False
    anchor_start = max(candidate.start, target_start)
    anchor_end = min(candidate.end, target_end)
    anchor = anchor_start + (anchor_end - anchor_start) / 2 if anchor_end > anchor_start else min(
        max(target_start, candidate.start), candidate.end
    )
    half = timedelta(seconds=maximum / 2)
    start = max(search_start, anchor - half)
    end = min(search_end, start + timedelta(seconds=maximum))
    if (end - start).total_seconds() < maximum:
        start = max(search_start, end - timedelta(seconds=maximum))
    return start, end, True


def find_alternatives(
    sources: Sequence[Source],
    target: Source,
    target_start: datetime,
    target_end: datetime,
    search_start: datetime,
    search_end: datetime,
    constraints: ConstraintSet,
    telescope: TelescopeConfig = LACT_TELESCOPE,
    *,
    max_alternatives: int = 3,
    coarse_step_seconds: int = 900,
    shortlist_limit: int = 8,
) -> dict:
    target_start, target_end = _utc(target_start), _utc(target_end)
    search_start, search_end = _utc(search_start), _utc(search_end)
    candidates = [
        source for source in sources
        if source.source_key != target.source_key
        and source.source_type != "gaia"
        and source.evaluation_radius_deg <= telescope.fov_radius_deg
    ]
    candidate_total = len(candidates)
    if candidate_total > MAX_COARSE_CANDIDATES:
        target_ra = np.deg2rad(target.ra)
        target_dec = np.deg2rad(target.dec)
        def angular_key(source: Source) -> tuple:
            ra = np.deg2rad(source.ra)
            dec = np.deg2rad(source.dec)
            cosine = np.sin(target_dec) * np.sin(dec) + np.cos(target_dec) * np.cos(dec) * np.cos(target_ra - ra)
            return (float(np.arccos(np.clip(cosine, -1.0, 1.0))), source.source_key)
        candidates.sort(key=angular_key)
        candidates = candidates[:MAX_COARSE_CANDIDATES]
    candidate_pool_truncated = candidate_total > len(candidates)
    times = _sample_times(search_start, search_end, coarse_step_seconds)
    coarse: list[CandidateWindow] = []
    coarse_warnings: set[str] = set()
    for offset in range(0, len(candidates), SOURCE_CHUNK_SIZE):
        chunk = candidates[offset:offset + SOURCE_CHUNK_SIZE]
        series = compute_catalog_geometry(chunk, times, telescope)
        coarse_warnings.update(series.warnings)
        for index, source in enumerate(chunk):
            evaluation = evaluate_constraints(
                series.target_altitude_deg[index], series.target_zenith_deg[index],
                series.sun_altitude_deg, series.moon_separation_deg[index],
                source.evaluation_radius_deg, constraints,
                fov_radius_deg=telescope.fov_radius_deg,
                enforce_current_pointing=False,
            )
            windows = _mask_windows(evaluation.footprint_pass, times)
            best = _best_window(source, windows, target_start, target_end)
            if best is not None:
                coarse.append(best)
    coarse.sort(key=lambda item: metric_sort_key(item.metrics, item.source.source_key))
    shortlist = coarse[:shortlist_limit]
    exact_rows = []
    exact_failures = []
    for coarse_candidate in shortlist:
        exact_start, exact_end, clipped = _exact_bounds(
            coarse_candidate, target_start, target_end, search_start, search_end,
            coarse_step_seconds, constraints.minimum_duration,
        )
        try:
            result = calculate_windows(
                coarse_candidate.source, exact_start, exact_end, constraints,
                telescope=telescope,
            )
        except (ValueError, RuntimeError) as exc:
            exact_failures.append(f"{coarse_candidate.source.source_key}: {exc}")
            continue
        exact_windows = [(window.start, window.end) for window in result.full_footprint_windows]
        best = _best_window(coarse_candidate.source, exact_windows, target_start, target_end)
        if best is None:
            continue
        warnings = list(result.warnings)
        if coarse_candidate.source.point_source_fallback and POINT_SOURCE_FALLBACK_WARNING not in warnings:
            warnings.append(POINT_SOURCE_FALLBACK_WARNING)
        if clipped:
            warnings.append("exact_validation_clipped_to_bounded_local_slice")
        exact_rows.append((best, warnings, clipped))
    exact_rows.sort(key=lambda row: metric_sort_key(row[0].metrics, row[0].source.source_key))
    selected = exact_rows[:max_alternatives]
    alternatives = []
    for rank, (candidate, warnings, clipped) in enumerate(selected, start=1):
        metrics = dict(candidate.metrics)
        metrics["rank"] = rank
        metrics["sort_label"] = "overlap_desc,gap_asc,duration_difference_asc,candidate_duration_desc,source_key_asc"
        alternatives.append({
            "source": candidate.source.to_dict(),
            "window": {
                "start": iso_utc(candidate.start),
                "end": iso_utc(candidate.end),
                "duration_seconds": metrics["candidate_window_seconds"],
            },
            "metrics": metrics,
            "rank": rank,
            "selection_stage": "coarse_then_exact_local",
            "warnings": warnings,
            "exact_validation_clipped": clipped,
            "pointing_constraint_applied": False,
        })
    shortfall = None
    if len(alternatives) < max_alternatives:
        shortfall = f"requested {max_alternatives}; found {len(alternatives)} after exact validation"
    complete = not candidate_pool_truncated and not exact_failures and not any(row[2] for row in selected)
    warnings = sorted(coarse_warnings)
    if candidate_pool_truncated:
        warnings.append(f"coarse candidate pool limited to the {MAX_COARSE_CANDIDATES} nearest catalogue sources")
    if exact_failures:
        warnings.append("some shortlisted sources failed exact validation")
    return {
        "status": "ok",
        "target": target.to_dict(),
        "target_window": {"start": iso_utc(target_start), "end": iso_utc(target_end)},
        "alternatives": alternatives,
        "candidate_shortfall": shortfall,
        "pointing_constraint_applied": False,
        "search_summary": {
            "search_start": iso_utc(search_start),
            "search_end": iso_utc(search_end),
            "coarse_step_seconds": coarse_step_seconds,
            "candidate_count": candidate_total,
            "coarse_candidate_count": len(candidates),
            "candidate_pool_truncated": candidate_pool_truncated,
            "coarse_pass_count": len(coarse),
            "shortlist_count": len(shortlist),
            "exact_validated_count": len(exact_rows),
            "returned_count": len(alternatives),
            "complete": complete,
            "candidate_shortfall": shortfall,
            "exact_failures": exact_failures,
            "warnings": warnings,
        },
    }
