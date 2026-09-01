from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

import app.windows as windows
from app.catalog import catalog
from app.constraints import ConstraintEvaluation
from app.schemas import ConstraintSet
from app.windows import _grid, calculate_catalogue_windows, calculate_windows

from .helpers import FakeSeries, source


def test_grid_includes_exact_end_without_exceeding_it():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(seconds=125)
    values = _grid(start, end, 60)
    assert values == [start, start + timedelta(seconds=60), start + timedelta(seconds=120), end]


def test_effective_grid_step_is_second_resolution_for_all_duration_modes():
    assert windows._effective_grid_step(ConstraintSet(), 60) == 1
    assert windows._effective_grid_step(ConstraintSet(minimum_window_seconds=10), 60) == 1
    assert windows._effective_grid_step(ConstraintSet(minimum_window_seconds=180), 60) == 1


def test_window_boundary_is_refined_below_one_second(monkeypatch):
    src = source()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(seconds=180)
    times = _grid(start, end, 60)
    boundary = 37.25

    def fake_compute(_source, values):
        if isinstance(values, datetime):
            values = [values]
        timestamps = np.asarray([value.timestamp() for value in values])
        elapsed = timestamps - start.timestamp()
        altitude = elapsed - boundary
        return FakeSeries(
            unix_seconds=timestamps,
            target_altitude_deg=altitude,
            target_zenith_deg=90.0 - altitude,
            sun_altitude_deg=np.full_like(elapsed, -30.0),
            moon_separation_deg=np.full_like(elapsed, 90.0),
        )

    monkeypatch.setattr(windows, "compute_geometry", fake_compute)
    result = calculate_windows(src, start, end, ConstraintSet())
    assert len(result.center_windows) == 1
    refined = (result.center_windows[0].start - start).total_seconds()
    assert refined == pytest.approx(boundary, abs=0.5)
    assert result.center_windows[0].end == end


def test_short_window_between_original_minute_samples_is_detected(monkeypatch):
    src = source()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(seconds=180)

    def fake_compute(_source, values):
        if isinstance(values, datetime):
            values = [values]
        timestamps = np.asarray([value.timestamp() for value in values])
        elapsed = timestamps - start.timestamp()
        altitude = np.where((elapsed >= 10.0) & (elapsed <= 20.0), 1.0, -1.0)
        return FakeSeries(
            unix_seconds=timestamps,
            target_altitude_deg=altitude,
            target_zenith_deg=90.0 - altitude,
            sun_altitude_deg=np.full_like(elapsed, -30.0),
            moon_separation_deg=np.full_like(elapsed, 90.0),
        )

    monkeypatch.setattr(windows, "compute_geometry", fake_compute)
    result = calculate_windows(src, start, end, ConstraintSet(minimum_window_seconds=5))
    assert result.center_windows
    assert result.center_windows[0].duration_seconds >= 5
    # The UI default of zero means "no duration filtering", so it must not
    # revert to the former 60-second grid and lose this 10-second interval.
    default_result = calculate_windows(src, start, end, ConstraintSet())
    assert default_result.center_windows
    assert default_result.center_windows[0].duration_seconds >= 10


def test_minimum_duration_filters_short_windows(monkeypatch):
    src = source()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(seconds=180)

    def fake_compute(_source, values):
        if isinstance(values, datetime):
            values = [values]
        timestamps = np.asarray([value.timestamp() for value in values])
        elapsed = timestamps - start.timestamp()
        # Above horizon only from seconds 40 through 100.
        altitude = np.minimum(elapsed - 40.0, 100.0 - elapsed)
        return FakeSeries(
            unix_seconds=timestamps,
            target_altitude_deg=altitude,
            target_zenith_deg=90.0 - altitude,
            sun_altitude_deg=np.full_like(elapsed, -30.0),
            moon_separation_deg=np.full_like(elapsed, 90.0),
        )

    monkeypatch.setattr(windows, "compute_geometry", fake_compute)
    result = calculate_windows(
        src, start, end, ConstraintSet(minimum_window_seconds=61)
    )
    assert result.center_windows == []
    result = calculate_windows(
        src, start, end, ConstraintSet(minimum_window_seconds=59)
    )
    assert len(result.center_windows) == 1
    assert result.center_windows[0].duration_seconds == pytest.approx(60.0, abs=1.0)


def test_window_boundary_reasons_describe_direction_of_constraint_change(monkeypatch):
    """Start/end reasons must not claim a failed condition has already passed."""
    src = source()
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(seconds=180)

    def fake_compute(_source, values):
        if isinstance(values, datetime):
            values = [values]
        timestamps = np.asarray([value.timestamp() for value in values])
        elapsed = timestamps - start.timestamp()
        # Keep the target above horizon; only the Sun threshold creates edges.
        return FakeSeries(
            unix_seconds=timestamps,
            target_altitude_deg=np.full_like(elapsed, 30.0),
            target_zenith_deg=np.full_like(elapsed, 60.0),
            sun_altitude_deg=np.where((elapsed >= 40) & (elapsed <= 120), -20.0, -10.0),
            moon_separation_deg=np.full_like(elapsed, 90.0),
        )

    monkeypatch.setattr(windows, "compute_geometry", fake_compute)
    result = calculate_windows(src, start, end, ConstraintSet(sun_max_altitude_deg=-15))
    interval = result.center_windows[0]
    assert interval.start_reason == "became_valid_after: sun_altitude"
    assert interval.end_reason == "became_invalid_after: sun_altitude"


def test_full_footprint_window_includes_conservative_valid_plan_seconds():
    """Plan defaults must be whole-second instants that still pass geometry."""
    from app.catalog import Source
    from app.constraints import scalar_evaluation
    from app.astronomy import compute_geometry

    # This narrow, real-Astropy case previously exposed a false default after
    # rounding a sub-second full-footprint root onto the invalid side.
    src = Source(-1, "TMP boundary", 0.001, 0.0, 34.485, 29.230, 0.0, 0.0, 0.0)
    start = datetime(2026, 12, 15, 14, tzinfo=timezone.utc)
    result = calculate_windows(
        src,
        start,
        start + timedelta(minutes=3),
        ConstraintSet(
            sun_max_altitude_deg=-18,
            moon_min_separation_deg=30,
            target_min_zenith_deg=0,
            target_max_zenith_deg=0.5,
        ),
    )
    assert result.full_footprint_windows
    window = result.full_footprint_windows[0]
    assert window.plan_start is not None and window.plan_end is not None
    assert window.start <= window.plan_start < window.plan_end <= window.end
    for instant in (window.plan_start, window.plan_end):
        geometry = compute_geometry(src, instant).at(0)
        assert scalar_evaluation(geometry, src.ext, result.constraints).footprint_pass[0]


def test_real_crab_winter_window_and_footprint_are_consistent():
    start = datetime(2026, 12, 15, 10, tzinfo=timezone.utc)
    end = start + timedelta(hours=24)
    constraints = ConstraintSet(
        sun_max_altitude_deg=-18,
        target_max_zenith_deg=50,
        minimum_window_seconds=1800,
    )
    result = calculate_windows(catalog.get(11), start, end, constraints)
    assert len(result.center_windows) == 1
    assert len(result.full_footprint_windows) == 1
    center = result.center_windows[0]
    full = result.full_footprint_windows[0]
    assert center.start < full.start < full.end < center.end
    assert center.duration_seconds > 7 * 3600
    assert (center.start - start).total_seconds() == pytest.approx(13056, abs=2)
    assert not result.warnings


def test_moon_constraint_uses_observer_frame_and_can_leave_a_crab_window():
    start = datetime(2026, 12, 15, 10, tzinfo=timezone.utc)
    result = calculate_windows(
        catalog.get(11),
        start,
        start + timedelta(hours=24),
        ConstraintSet(moon_min_separation_deg=20),
    )
    assert result.center_windows
    assert result.full_footprint_windows
    assert result.center_windows[0].minimum_moon_separation_deg > 90.0


def _window_dicts(windows_to_compare):
    """Keep batch/single equivalence assertions focused on public output."""
    return [window.to_dict() for window in windows_to_compare]


def test_catalogue_windows_match_single_source_across_chunk_boundary():
    """Batch geometry must preserve every second and every refined boundary.

    The interval crosses the ten-minute batch boundary at 00:10 UTC.  Using
    real astrometry rather than a shared test double checks the vectorized
    AltAz transformation, duplicate-boundary removal and per-source window
    reconstruction against the ordinary single-target implementation.
    """
    sources = [catalog.get(11), catalog.get(57), catalog.get(168)]
    start = datetime(2026, 12, 15, 0, 8, tzinfo=timezone.utc)
    end = start + timedelta(minutes=5)
    constraints = ConstraintSet(
        sun_max_altitude_deg=-18,
        moon_min_separation_deg=30,
        target_min_zenith_deg=0,
        target_max_zenith_deg=60,
        minimum_window_seconds=0,
    )

    batch = calculate_catalogue_windows(sources, start, end, constraints)

    assert len(batch) == len(sources)
    for source_item, batch_result in zip(sources, batch):
        single = calculate_windows(source_item, start, end, constraints)
        assert batch_result.sample_times == single.sample_times
        assert len(batch_result.sample_times) == 301
        assert _window_dicts(batch_result.center_windows) == _window_dicts(single.center_windows)
        assert _window_dicts(batch_result.full_footprint_windows) == _window_dicts(single.full_footprint_windows)
        np.testing.assert_allclose(
            batch_result.series.target_altitude_deg,
            single.series.target_altitude_deg,
            atol=1e-9,
        )
        np.testing.assert_allclose(
            batch_result.series.moon_separation_deg,
            single.series.moon_separation_deg,
            atol=1e-9,
        )


def test_catalogue_windows_keep_a_short_interval_at_chunk_boundary(monkeypatch):
    """The shared edge of two 600-second chunks must not lose a short window."""
    src = source(index=1)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    end = start + timedelta(seconds=620)

    def fake_catalog_geometry(sources, values):
        timestamps = np.asarray([value.timestamp() for value in values])
        elapsed = timestamps - start.timestamp()
        # This valid span straddles the duplicated 600-second chunk boundary.
        altitude = np.where((elapsed >= 599.0) & (elapsed <= 601.0), 1.0, -1.0)
        from app.astronomy import CatalogGeometrySeries
        from astropy.time import Time
        return CatalogGeometrySeries(
            times=Time(values),
            target_altitude_deg=np.repeat(altitude[np.newaxis, :], len(sources), axis=0),
            target_azimuth_deg=np.zeros((len(sources), len(values))),
            target_zenith_deg=np.repeat((90.0 - altitude)[np.newaxis, :], len(sources), axis=0),
            sun_altitude_deg=np.full(len(values), -30.0),
            sun_azimuth_deg=np.zeros(len(values)),
            moon_altitude_deg=np.zeros(len(values)),
            moon_azimuth_deg=np.zeros(len(values)),
            moon_separation_deg=np.full((len(sources), len(values)), 90.0),
            sun_separation_deg=np.full((len(sources), len(values)), 90.0),
            warnings=[],
        )

    monkeypatch.setattr(windows, "compute_catalog_geometry", fake_catalog_geometry)
    # Boundary refinement uses the single-source scalar helper. Match its
    # synthetic field to the bulk field so the test remains deterministic.
    def fake_single_geometry(_source, values):
        if isinstance(values, datetime):
            values = [values]
        timestamps = np.asarray([value.timestamp() for value in values])
        altitude = np.where(
            ((timestamps - start.timestamp()) >= 599.0)
            & ((timestamps - start.timestamp()) <= 601.0),
            1.0,
            -1.0,
        )
        return FakeSeries(
            unix_seconds=timestamps,
            target_altitude_deg=altitude,
            target_zenith_deg=90.0 - altitude,
            sun_altitude_deg=np.full_like(timestamps, -30.0),
            moon_separation_deg=np.full_like(timestamps, 90.0),
        )

    monkeypatch.setattr(windows, "compute_geometry", fake_single_geometry)

    result = calculate_catalogue_windows([src], start, end, ConstraintSet())[0]
    assert len(result.sample_times) == 621
    assert len(result.center_windows) == 1
    interval = result.center_windows[0]
    assert (interval.start - start).total_seconds() == pytest.approx(599.0, abs=0.5)
    assert (interval.end - start).total_seconds() == pytest.approx(601.0, abs=0.5)
