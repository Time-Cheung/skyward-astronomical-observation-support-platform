import numpy as np

from app.schemas import ConstraintSet
from app.status import _from_series

from .helpers import fake_catalog_series, source


def test_green_when_center_and_full_nominal_extension_pass():
    src = source(ext=1.0)
    status = _from_series([src], fake_catalog_series([[45.0]]), ConstraintSet())[0]
    assert status.status == "GREEN"
    assert status.center_pass is True
    assert status.footprint_pass is True


def test_yellow_only_when_center_passes_but_extension_fails():
    src = source(ext=5.0)
    status = _from_series([src], fake_catalog_series([[45.0]]), ConstraintSet())[0]
    assert status.status == "YELLOW"
    assert status.center_pass is True
    assert status.footprint_pass is False
    assert "extension_edge_exceeds_fov" in status.reasons


def test_red_when_center_is_below_horizon():
    src = source(ext=0.0)
    status = _from_series([src], fake_catalog_series([[-0.01]]), ConstraintSet())[0]
    assert status.status == "RED"
    assert status.center_pass is False
    assert any("target_above_horizon" in reason for reason in status.reasons)


def test_global_sun_failure_is_red_not_yellow():
    src = source(ext=1.0)
    status = _from_series(
        [src],
        fake_catalog_series([[45.0]], sun=-5.0),
        ConstraintSet(sun_max_altitude_deg=-18),
    )[0]
    assert status.status == "RED"
    assert "center_sun_altitude" in status.reasons


def test_minimum_window_changes_current_status_only_if_future_fails():
    src = source(ext=0.0)
    series = fake_catalog_series([[20.0, 10.0, -1.0]])
    status = _from_series(
        [src], series, ConstraintSet(minimum_window_seconds=120)
    )[0]
    assert status.status == "RED"
    assert status.geometry["target_altitude_deg"] == 20.0
    assert "center_cannot_hold_for_minimum_window" in status.reasons


def test_minimum_window_can_make_full_extension_yellow_while_center_holds():
    src = source(ext=2.0)
    series = fake_catalog_series([[5.0, 2.1, 1.9]])
    status = _from_series(
        [src], series, ConstraintSet(minimum_window_seconds=120)
    )[0]
    assert status.status == "YELLOW"
    assert status.center_pass
    assert not status.footprint_pass
    assert "extension_cannot_hold_for_minimum_window" in status.reasons
