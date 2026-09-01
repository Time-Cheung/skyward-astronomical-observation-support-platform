import numpy as np
import pytest
from pydantic import ValidationError

from app.constraints import evaluate_constraints
from app.schemas import ConstraintSet


def test_center_horizon_is_always_active():
    evaluation = evaluate_constraints([-0.001, 0.0, 1.0], [90.001, 90.0, 89.0], [-20] * 3, [90] * 3, 0.0, ConstraintSet())
    assert evaluation.center_pass.tolist() == [False, True, True]


def test_optional_constraints_are_disabled_when_empty():
    evaluation = evaluate_constraints([20], [70], [30], [1], 0.0, ConstraintSet())
    assert set(evaluation.center_margins) == {"target_above_horizon"}
    assert evaluation.center_pass[0]


def test_all_optional_center_constraints_and_margins():
    constraints = ConstraintSet(
        sun_max_altitude_deg=-18,
        moon_min_separation_deg=30,
        target_min_zenith_deg=5,
        target_max_zenith_deg=60,
    )
    evaluation = evaluate_constraints([40], [50], [-20], [35], 2, constraints)
    assert evaluation.center_pass[0]
    assert evaluation.footprint_pass[0]
    assert evaluation.center_margins["sun_altitude"][0] == pytest.approx(2)
    assert evaluation.footprint_margins["moon_separation"][0] == pytest.approx(3)
    assert evaluation.footprint_margins["target_max_zenith"][0] == pytest.approx(8)


def test_extension_edge_and_fov_fail_without_changing_center():
    evaluation = evaluate_constraints([20], [70], [-20], [90], 5.0, ConstraintSet())
    assert evaluation.center_pass[0]
    assert not evaluation.footprint_pass[0]
    assert evaluation.footprint_margins["extension_inside_fov"][0] == pytest.approx(-0.85)


def test_ext_err_and_position_error_are_not_constraint_inputs():
    # The constraint API accepts only nominal extension. Catalogue uncertainties
    # cannot accidentally alter status through this layer.
    first = evaluate_constraints([20], [70], [-20], [90], 1.0, ConstraintSet())
    second = evaluate_constraints([20], [70], [-20], [90], 1.0, ConstraintSet())
    assert np.array_equal(first.footprint_pass, second.footprint_pass)
    assert first.footprint_margins.keys() == second.footprint_margins.keys()


def test_invalid_zenith_range_and_angle_inputs_are_rejected():
    with pytest.raises(ValidationError, match="target_min_zenith_deg"):
        ConstraintSet(target_min_zenith_deg=40, target_max_zenith_deg=20)
    with pytest.raises(ValidationError):
        ConstraintSet(moon_min_separation_deg=181)
    with pytest.raises(ValidationError):
        ConstraintSet(sun_max_altitude_deg=-91)
