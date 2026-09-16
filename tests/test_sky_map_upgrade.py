"""Scientific SVG acceptance tests, independent of the observing-window solver."""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
import math
import re
import xml.etree.ElementTree as ET

import astropy.units as u
import numpy as np
import pytest
from astropy.coordinates import SkyCoord

from app.astronomy import J2000_FRAME, source_coord
from app.catalog import Source
from app.config import LACT_TELESCOPE
from app.schemas import ConstraintSet
from app import sky_map as sm

AT = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)


def source(index=0, ra=359.99, dec=25, ext=0, kind="catalogue"):
    return Source(index, f"test-{index}", ext, None, ra, dec, 0, 0, None, "Gaia DR3" if kind == "gaia" else "Test", kind)


def members(root, cls):
    return [node for node in root.iter() if cls in node.get("class", "").split()]


def position(marker):
    return float(marker.get("data-x")), float(marker.get("data-y"))


def path_points(node):
    return np.array([(float(x), float(y)) for x, y in re.findall(r"[ML](-?[\d.]+),(-?[\d.]+)", node.get("d"))])


def fake_snapshot(sources, at_time, constraints, telescope, **kwargs):
    coordinates = SkyCoord(ra=np.array([s.ra for s in sources]) * u.deg, dec=np.array([s.dec for s in sources]) * u.deg, frame=J2000_FRAME).transform_to(sm._altaz(at_time, telescope))
    return {"sources": [{**s.to_dict(), "status": "GREEN", "geometry": {"target_altitude_deg": float(c.alt.deg), "target_azimuth_deg": float(c.az.deg), "sun_altitude_deg": -40, "sun_azimuth_deg": 25, "moon_altitude_deg": -30, "moon_azimuth_deg": 130}} for s, c in zip(sources, coordinates)]}


@pytest.mark.parametrize("frame", ["altaz", "j2000", "galactic"])
def test_local_projection_grid_markers_and_directions_share_frame(frame):
    central = source(ra=359.99, dec=25, ext=.4)
    other = source(1, ra=.01, dec=25.01, kind="gaia")
    root = ET.fromstring(sm.render_local_fov_svg(central, [central, other], AT, display_frame=frame))
    markers = members(root, "source-marker")
    assert len(markers) == 2
    assert position(markers[0]) == pytest.approx((330, 300), abs=1e-7)
    centre_coord = source_coord(central).transform_to(sm._frame(frame, AT, LACT_TELESCOPE))
    candidate = source_coord(other).transform_to(centre_coord.frame)
    separation = centre_coord.separation(candidate).deg
    pa = centre_coord.position_angle(candidate).rad
    scale = 235 / max(6.5, LACT_TELESCOPE.fov_radius_deg * 1.4)
    assert position(markers[1]) == pytest.approx((330 + separation * scale * math.sin(pa), 300 - separation * scale * math.cos(pa)), abs=1e-7)
    assert markers[0].find("polygon") is None
    assert markers[1].find("polygon") is not None
    for marker, original in zip(markers, [central, other]):
        assert marker.get("role") == "button"
        assert marker.get("tabindex") == "0"
        assert marker.get("data-source-key") == original.source_key
        assert marker.get("data-source-index") == str(original.index)
        assert len(marker.get("data-x").split(".")[1]) >= 6
    axes = {line.get("data-axis") for line in members(root, "coordinate-grid")}
    assert axes == ({"Az", "Alt"} if frame == "altaz" else {"RA", "Dec"} if frame == "j2000" else {"l", "b"})
    assert members(root, "coordinate-tick")
    assert members(root, "map-clipped")[0].get("clip-path")


@pytest.mark.parametrize("frame", ["altaz", "j2000", "galactic"])
def test_all_sky_is_zenith_centered_and_matches_astropy(monkeypatch, frame):
    monkeypatch.setattr(sm, "sky_snapshot", fake_snapshot)
    horizontal = SkyCoord(az=[0, 90, 180, 270] * u.deg, alt=[55, 35, 15, 45] * u.deg, frame=sm._altaz(AT, LACT_TELESCOPE))
    fk5 = horizontal.transform_to(J2000_FRAME)
    sources = [source(i, float(c.ra.deg), float(c.dec.deg)) for i, c in enumerate(fk5)]
    svg, meta = sm.render_all_sky_svg(sources, AT, ConstraintSet(), display_frame=frame)
    root = ET.fromstring(svg)
    assert root.get("data-center") == "zenith"
    markers = members(root, "source-marker")
    assert len(markers) == 4
    display = sm._frame(frame, AT, LACT_TELESCOPE)
    center = sm._zenith_coordinate(AT, LACT_TELESCOPE).transform_to(display)
    for marker, horizontal_coord in zip(markers, horizontal):
        if frame == "altaz":
            angle, radius = horizontal_coord.az.rad, (90 - horizontal_coord.alt.deg) * 260 / 90
        else:
            coord = horizontal_coord.transform_to(display)
            angle, radius = center.position_angle(coord).rad, center.separation(coord).deg * 260 / 90
        assert position(marker) == pytest.approx((350 + radius * math.sin(angle), 335 - radius * math.cos(angle)), abs=2e-4)
    assert meta["visible_source_count"] == 4
    assert len(members(root, "coordinate-tick")) > 2


def test_extension_is_true_spherical_radius_not_hit_radius_and_zoom_invariant():
    central = source(ext=.25)
    roots = [ET.fromstring(sm.render_local_fov_svg(central, [central], AT, display_frame="j2000", zoom=z)) for z in (1, 1000)]
    paths = [members(root, "extension-ring")[0] for root in roots]
    assert paths[0].get("d") == paths[1].get("d")
    points = path_points(paths[0])
    radius = np.hypot(points[:, 0] - 330, points[:, 1] - 300)
    assert radius == pytest.approx(np.full(len(radius), .25 * 235 / 6.5), abs=1e-7)
    hit = members(roots[0], "source-hit-target")[0]
    assert float(hit.get("r")) != pytest.approx(radius[0])
    assert paths[0].get("data-angular-radius-deg") == "0.250000000"
    assert float(roots[1].get("data-grid-step-deg")) < float(roots[0].get("data-grid-step-deg"))


def test_deep_zoom_keeps_subpixel_neighbours_distinct():
    central = source()
    other = source(1, ra=central.ra + .00003, dec=central.dec, kind="gaia")
    root = ET.fromstring(sm.render_local_fov_svg(central, [central, other], AT, display_frame="j2000", zoom=1000))
    first, second = members(root, "source-marker")
    dx = position(second)[0] - position(first)[0]
    assert .0001 < dx < .01  # old two-decimal output collapsed this distance
    assert root.get("viewBox") == "329.660000000 299.690000000 0.680000000 0.620000000"
    assert members(root, "coordinate-tick")


@pytest.mark.parametrize("dec", [89.99, -89.99])
def test_polar_wrap_grid_is_finite_clipped_and_has_no_false_chords(dec):
    central = source(ra=359.99, dec=dec)
    root = ET.fromstring(sm.render_local_fov_svg(central, [central], AT, display_frame="j2000", zoom=4))
    grids = members(root, "coordinate-grid")
    assert len(grids) < 150
    assert members(root, "coordinate-tick")
    for grid in grids:
        assert "nan" not in grid.get("d").lower()
        assert "Z" not in grid.get("d")
        for segment in grid.get("d").split("M")[1:]:
            points = np.array([(float(x), float(y)) for x, y in re.findall(r"(-?[\d.]+),(-?[\d.]+)", segment)])
            if len(points) > 1:
                assert np.max(np.hypot(*np.diff(points, axis=0).T)) <= 235 * .4 + 1e-6


def test_grid_points_are_actual_meridians_and_parallels():
    central = source(ra=359.99, dec=25)
    root = ET.fromstring(sm.render_local_fov_svg(central, [central], AT, display_frame="j2000"))
    center = source_coord(central)
    for grid in members(root, "coordinate-grid"):
        points = path_points(grid)
        inside = np.hypot(points[:, 0] - 330, points[:, 1] - 300) < 230
        points = points[inside][::20]
        if not len(points):
            continue
        dx, dy = points[:, 0] - 330, 300 - points[:, 1]
        coordinates = center.directional_offset_by(np.arctan2(dx, dy) * u.rad, np.hypot(dx, dy) * 6.5 / 235 * u.deg)
        expected = float(grid.get("data-coordinate-deg"))
        if grid.get("data-axis") == "RA":
            error = (coordinates.ra.deg - expected + 180) % 360 - 180
        else:
            error = coordinates.dec.deg - expected
        assert np.max(np.abs(error)) < 1e-7


def test_trajectory_uses_display_instant_for_every_projection(monkeypatch):
    later = AT + timedelta(hours=5)
    def snapshot(sources, start, end, constraints, telescope, **kwargs):
        return fake_snapshot(sources, kwargs["display_time"], constraints, telescope)
    monkeypatch.setattr(sm, "sky_trajectory_snapshot", snapshot)
    star = source()
    svg, meta = sm.render_all_sky_svg([star], AT, ConstraintSet(), trajectory_end=later + timedelta(hours=2), trajectory_display_time=later, display_frame="galactic")
    root = ET.fromstring(svg)
    geometry = fake_snapshot([star], later, ConstraintSet(), LACT_TELESCOPE)["sources"][0]["geometry"]
    expected = sm._project_body(max(0, geometry["target_altitude_deg"]), geometry["target_azimuth_deg"], later, LACT_TELESCOPE, "galactic", 350, 335, 260)
    assert position(members(root, "source-marker")[0]) == pytest.approx(expected[:2], abs=1e-7)
    assert meta["map_display_time"] == later.isoformat()


@pytest.mark.parametrize("kwargs", [{"zoom": 0}, {"zoom": 1001}, {"bounds": (0, 0, 0, 5)}, {"grid_step_deg": 0}])
def test_invalid_display_settings_fail_without_mutating_science(kwargs):
    with pytest.raises(ValueError):
        sm.render_local_fov_svg(source(), [], AT, **kwargs)


def test_offcentre_bounds_keeps_target_projection_and_stable_identity():
    central = source()
    root = ET.fromstring(sm.render_local_fov_svg(central, [], AT, display_frame="j2000", bounds=(329, 299, 2, 2), grid_step_deg=.01))
    assert position(members(root, "source-marker")[0]) == pytest.approx((330, 300), abs=1e-8)
    assert root.get("data-grid-step-deg") == "0.010000000"
    assert root.get("viewBox") == "329.000000000 299.000000000 2.000000000 2.000000000"


def test_unknown_footprint_never_draws_a_measured_extension():
    central = replace(source(ext=1), footprint_known=False)
    root = ET.fromstring(sm.render_local_fov_svg(central, [central], AT))
    assert not members(root, "extension-ring")
    assert members(root, "source-symbol")


def test_styles_are_per_map_zoom_and_allow_client_symbol_scaling_only():
    css = sm._styles(1000)
    assert '.sky-map-svg[data-zoom="1000.000000000"]' in css
    assert '--map-icon-scale' in css
    extension_rule = next(line for line in css.splitlines() if '.extension-ring' in line)
    assert 'transform:none' in extension_rule
    assert 'scale(var(' not in extension_rule
