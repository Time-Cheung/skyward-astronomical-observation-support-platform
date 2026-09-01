from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Sequence

import numpy as np

from .config import FOV_RADIUS_DEG
from .schemas import ConstraintSet


@dataclass
class ConstraintEvaluation:
    center_margins: Dict[str, np.ndarray]
    footprint_margins: Dict[str, np.ndarray]
    center_pass: np.ndarray
    footprint_pass: np.ndarray

    def failure_labels(self, kind: str = "center", index: int = 0) -> list[str]:
        margins = self.center_margins if kind == "center" else self.footprint_margins
        return [name for name, values in margins.items() if float(values[index]) < 0.0]


def _array(value: Sequence[float] | np.ndarray) -> np.ndarray:
    return np.asarray(value, dtype=float)


def evaluate_constraints(
    target_altitude_deg: Sequence[float] | np.ndarray,
    target_zenith_deg: Sequence[float] | np.ndarray,
    sun_altitude_deg: Sequence[float] | np.ndarray,
    moon_separation_deg: Sequence[float] | np.ndarray,
    extension_deg: float,
    constraints: ConstraintSet,
    *,
    fov_radius_deg: float = FOV_RADIUS_DEG,
    target_pointing_separation_deg: Sequence[float] | np.ndarray | None = None,
    enforce_current_pointing: bool = False,
) -> ConstraintEvaluation:
    """Return signed margins for a source centre and circular footprint.

    The normal window planner treats the selected source as the planned
    pointing centre; therefore its FoV check asks whether the source extension
    fits inside the configured hard FoV. The all-sky status enables a distinct
    current-pointing check with a live target-to-pointing separation, so its
    red/yellow/green markers answer whether this target can be observed now at
    the current telescope direction.
    """
    altitude = _array(target_altitude_deg)
    zenith = _array(target_zenith_deg)
    sun_altitude = _array(sun_altitude_deg)
    moon_separation = _array(moon_separation_deg)
    ext = max(0.0, float(extension_deg))
    fov_radius = float(fov_radius_deg)

    center: Dict[str, np.ndarray] = {"target_above_horizon": altitude}
    footprint: Dict[str, np.ndarray] = {
        "extension_inside_fov": np.full_like(altitude, fov_radius - ext),
        "extension_above_horizon": altitude - ext,
    }
    if enforce_current_pointing:
        if target_pointing_separation_deg is None:
            raise ValueError("current-pointing status requires target separation")
        pointing_separation = _array(target_pointing_separation_deg)
        center["target_inside_current_fov"] = fov_radius - pointing_separation
        footprint["extension_inside_current_fov"] = fov_radius - (pointing_separation + ext)

    if constraints.sun_max_altitude_deg is not None:
        margin = constraints.sun_max_altitude_deg - sun_altitude
        center["sun_altitude"] = margin
        footprint["sun_altitude"] = margin
    if constraints.moon_min_separation_deg is not None:
        center["moon_separation"] = moon_separation - constraints.moon_min_separation_deg
        footprint["moon_separation"] = moon_separation - ext - constraints.moon_min_separation_deg
    if constraints.target_min_zenith_deg is not None:
        center["target_min_zenith"] = zenith - constraints.target_min_zenith_deg
        nearest_edge_zenith = np.maximum(0.0, zenith - ext)
        footprint["target_min_zenith"] = nearest_edge_zenith - constraints.target_min_zenith_deg
    if constraints.target_max_zenith_deg is not None:
        center["target_max_zenith"] = constraints.target_max_zenith_deg - zenith
        footprint["target_max_zenith"] = constraints.target_max_zenith_deg - (zenith + ext)
    else:
        footprint["extension_max_zenith"] = 90.0 - (zenith + ext)

    center_stack = np.vstack(list(center.values()))
    footprint_stack = np.vstack(list(footprint.values()))
    return ConstraintEvaluation(
        center_margins=center,
        footprint_margins=footprint,
        center_pass=np.all(center_stack >= 0.0, axis=0),
        footprint_pass=np.all(footprint_stack >= 0.0, axis=0),
    )


def scalar_evaluation(
    geometry: Mapping[str, float],
    extension_deg: float,
    constraints: ConstraintSet,
    *,
    fov_radius_deg: float = FOV_RADIUS_DEG,
) -> ConstraintEvaluation:
    """Evaluate one supplied geometry record for ordinary window calculations."""
    return evaluate_constraints(
        [geometry["target_altitude_deg"]],
        [geometry["target_zenith_deg"]],
        [geometry["sun_altitude_deg"]],
        [geometry["moon_separation_deg"]],
        extension_deg,
        constraints,
        fov_radius_deg=fov_radius_deg,
    )
