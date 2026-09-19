"""Scientific SVG acceptance tests for the shared map marker contract."""
from datetime import datetime, timezone
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


@pytest.mark.parametrize("frame", ["altaz", "j2000", "galactic"])
def test_local_projection_and_grid_share_each_display_frame(frame):
    central = source(ra=359.99, dec=25, ext=.4)
    other = source(1, ra=.01, dec=25.01, kind="gaia")
    root = ET.fromstring(sm.render_local_fov_svg(central, [central, other], AT, display_frame=frame))
    markers = members(root, "source-marker")
    assert len(markers) == 2
    assert position(markers[0]) == pytest.approx((330, 300), abs=1e-7)
    centre = source_coord(central).transform_to(sm._frame(frame, AT, LACT_TELESCOPE))
    candidate = source_coord(other).transform_to(centre.frame)
    separation, pa = centre.separation(candidate).deg, centre.position_angle(candidate).rad
    scale = 235 / max(6.5, LACT_TELESCOPE.fov_radius_deg * 1.4)
    assert position(markers[1]) == pytest.approx((330 + separation * scale * np.sin(pa), 300 - separation * scale * np.cos(pa)), abs=1e-7)
    assert {line.get("data-axis") for line in members(root, "coordinate-grid")} == ({"Az", "Alt"} if frame == "altaz" else {"RA", "Dec"} if frame == "j2000" else {"l", "b"})


def test_shared_marker_contract_gaia_dot_catalogue_star_extension_tracking_and_target():
    normal = source(0, ext=.25)
    gaia = source(1, ra=.01, dec=25.01, kind="gaia")
    root = ET.fromstring(sm.render_local_fov_svg(normal, [normal, gaia], AT, display_frame="j2000"))
    catalogue, gaia_marker = members(root, "source-marker")
    assert members(catalogue, "source-star")
    assert not members(gaia_marker, "source-star")
    assert members(gaia_marker, "gaia-dot")
    extension = members(catalogue, "extension-ring")[0]
    assert extension.get("data-angular-radius-deg") == "0.250000000"
    assert extension.tag == "path"
    for marker in (catalogue, gaia_marker):
        hit = members(marker, "source-hit-target")[0]
        assert hit.get("style") == "fill:transparent;stroke:none;stroke-width:0;filter:none"
    selected_svg = sm.render_local_fov_svg(normal, [normal], AT, display_frame="j2000")
    selected = members(ET.fromstring(selected_svg), "source-marker")[0]
    assert members(selected, "selected-symbol")
    tracked_svg, _ = sm.render_all_sky_svg([normal], AT, ConstraintSet(), highlighted_indexes=[0], trajectory_end=AT.replace(hour=13))
    tracked = members(ET.fromstring(tracked_svg), "source-marker")[0]
    assert members(tracked, "tracking-ring")


def test_sparse_grid_and_deep_zoom_keep_two_axes_and_real_extension_radius():
    central = source(ra=120, dec=25, ext=.25)
    intervals = []
    for zoom in (1, 4, 20, 1000):
        root = ET.fromstring(sm.render_local_fov_svg(central, [central], AT, display_frame="j2000", zoom=zoom))
        assert {line.get("data-axis") for line in members(root, "coordinate-grid")} == {"RA", "Dec"}
        assert 2 <= len(members(root, "coordinate-grid")) <= 16
        intervals.append(max(float(root.get("data-grid-longitude-step-deg")), float(root.get("data-grid-latitude-step-deg"))))
    assert intervals == sorted(intervals, reverse=True)
    roots = [ET.fromstring(sm.render_local_fov_svg(central, [central], AT, display_frame="j2000", zoom=zoom)) for zoom in (1, 1000)]
    assert members(roots[0], "extension-ring")[0].get("d") == members(roots[1], "extension-ring")[0].get("d")


def test_all_sky_default_grid_is_sparse_60_by_30():
    svg, meta = sm.render_all_sky_svg([], AT, ConstraintSet(), display_frame="galactic")
    root = ET.fromstring(svg)
    assert root.get("data-grid-longitude-step-deg") == "60.000000000"
    assert root.get("data-grid-latitude-step-deg") == "30.000000000"
    assert meta["grid_longitude_step_deg"] == 60
    assert meta["grid_latitude_step_deg"] == 30


def test_unknown_footprint_never_draws_extension_and_css_isolated():
    unknown = Source(0, "unknown", 1, None, 10, 20, 0, 0, None, "Test", footprint_known=False)
    root = ET.fromstring(sm.render_local_fov_svg(unknown, [unknown], AT))
    assert not members(root, "extension-ring")
    css = root.find("style").text
    extension_rule = next(line for line in css.splitlines() if ".extension-ring" in line)
    hit_rule = next(line for line in css.splitlines() if '[data-hit-target="true"]' in line)
    assert "#00b8c6" in extension_rule and "stroke-dasharray:5 4" in extension_rule
    assert "stroke:none!important" in hit_rule and "stroke-width:0!important" in hit_rule
