from datetime import datetime, timezone

import numpy as np
import pytest
from astropy.coordinates import AltAz
from astropy.time import Time
import astropy.units as u

from app.astronomy import (
    IERS_TABLE,
    compute_catalog_geometry,
    compute_geometry,
    format_ra_dec,
    iers_status,
    source_coord,
)
from app.catalog import catalog
from app.config import SITE_LATITUDE_DEG, SITE_LOCATION


def test_fk5_j2000_coordinate_and_sexagesimal_format():
    crab = catalog.get(11)
    coord = source_coord(crab)
    assert coord.frame.name == "fk5"
    assert coord.equinox.jyear == pytest.approx(2000.0)
    formatted = format_ra_dec(crab)
    assert formatted["ra_hms"].startswith("05:34")
    assert formatted["dec_dms"].startswith("+22:00")


def test_vectorized_catalog_geometry_matches_single_source():
    moment = datetime(2026, 8, 18, 16, 0, tzinfo=timezone.utc)
    sources = [catalog.get(0), catalog.get(11), catalog.get(168)]
    batch = compute_catalog_geometry(sources, [moment])
    for index, source in enumerate(sources):
        single = compute_geometry(source, moment)
        assert batch.target_altitude_deg[index, 0] == pytest.approx(
            single.target_altitude_deg[0], abs=1e-9
        )
        assert batch.target_azimuth_deg[index, 0] == pytest.approx(
            single.target_azimuth_deg[0], abs=1e-9
        )
        assert batch.moon_separation_deg[index, 0] == pytest.approx(
            single.moon_separation_deg[0], abs=1e-9
        )


def test_transit_altitude_matches_spherical_expectation():
    source = catalog.get(11)
    # Search one sidereal day at one-minute resolution; maximum sampled altitude
    # should agree with 90 - |latitude - declination| within sampling precision.
    times = Time("2026-12-15T00:00:00") + np.arange(0, 24 * 60 + 1) * u.min
    frame = AltAz(obstime=times, location=SITE_LOCATION, pressure=0 * u.hPa)
    altitudes = source_coord(source).transform_to(frame).alt.deg
    expected = 90.0 - abs(SITE_LATITUDE_DEG - source.dec)
    assert float(np.max(altitudes)) == pytest.approx(expected, abs=0.02)


def test_sun_moon_outputs_are_finite_and_physical():
    geometry = compute_geometry(
        catalog.get(189), datetime(2028, 2, 29, 12, 0, tzinfo=timezone.utc)
    )
    for array in (
        geometry.target_altitude_deg,
        geometry.target_azimuth_deg,
        geometry.sun_altitude_deg,
        geometry.moon_altitude_deg,
        geometry.moon_separation_deg,
    ):
        assert np.all(np.isfinite(array))
    assert -90 <= geometry.target_altitude_deg[0] <= 90
    assert 0 <= geometry.target_azimuth_deg[0] <= 360
    assert 0 <= geometry.moon_separation_deg[0] <= 180


def test_moon_and_sun_separations_are_observer_frame_angles():
    source = catalog.get(11)
    moment = datetime(2026, 12, 15, 16, 0, tzinfo=timezone.utc)
    geometry = compute_geometry(source, moment)
    frame = AltAz(obstime=Time(moment), location=SITE_LOCATION, pressure=0 * u.hPa)
    target = source_coord(source).transform_to(frame)
    from astropy.coordinates import get_body, get_sun

    moon = get_body("moon", Time(moment), SITE_LOCATION).transform_to(frame)
    sun = get_sun(Time(moment)).transform_to(frame)
    assert geometry.moon_separation_deg[0] == pytest.approx(
        target.separation(moon).deg, abs=1e-9
    )
    assert geometry.sun_separation_deg[0] == pytest.approx(
        target.separation(sun).deg, abs=1e-9
    )
    assert geometry.moon_separation_deg[0] > 90.0


def test_bundled_iers_table_covers_current_deployment_date():
    status = iers_status()
    assert status["auto_download"] is False
    assert "data/iers/finals2000A.all" in status["source"]
    assert status["covers_current_time"] is True
    assert status["last_mjd"] >= Time("2027-08-01").mjd
    assert status["predictive_mjd"] is not None


def test_in_range_future_geometry_has_no_iers_degraded_warning():
    geometry = compute_geometry(
        catalog.get(11),
        [
            datetime(2026, 12, 15, tzinfo=timezone.utc),
            datetime(2026, 12, 16, tzinfo=timezone.utc),
        ],
    )
    assert not any("outside of range covered by IERS" in text for text in geometry.warnings)
    assert not any("after IERS data is valid" in text for text in geometry.warnings)
