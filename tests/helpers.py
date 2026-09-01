from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, List, Sequence

import numpy as np

from app.catalog import Source
from app.constraints import ConstraintEvaluation
from app.schemas import ConstraintSet
from app.status import SourceStatus, _from_series
from app.windows import WindowInterval, _build_intervals, _grid


@dataclass(frozen=True)
class FakeSeries:
    unix_seconds: np.ndarray
    target_altitude_deg: np.ndarray
    target_zenith_deg: np.ndarray
    sun_altitude_deg: np.ndarray
    moon_separation_deg: np.ndarray
    warnings: tuple = ()
    target_pointing_separation_deg: np.ndarray | None = None

    def at(self, index: int) -> dict:
        return {
            "target_altitude_deg": float(self.target_altitude_deg[index]),
            "target_azimuth_deg": 0.0,
            "target_zenith_deg": float(self.target_zenith_deg[index]),
            "target_pointing_separation_deg": float(self.target_pointing_separation_deg[index]) if self.target_pointing_separation_deg is not None else 0.0,
            "sun_altitude_deg": float(self.sun_altitude_deg[index]),
            "sun_azimuth_deg": 0.0,
            "moon_altitude_deg": 0.0,
            "moon_azimuth_deg": 0.0,
            "moon_separation_deg": float(self.moon_separation_deg[index]),
            "sun_separation_deg": 90.0,
        }


@dataclass(frozen=True)
class FakeCatalogSeries:
    target_altitude_deg: np.ndarray
    target_zenith_deg: np.ndarray
    sun_altitude_deg: np.ndarray
    moon_separation_deg: np.ndarray

    def source_at(self, source_index: int, time_index: int = 0) -> dict:
        return {
            "target_altitude_deg": float(self.target_altitude_deg[source_index, time_index]),
            "target_azimuth_deg": 0.0,
            "target_zenith_deg": float(self.target_zenith_deg[source_index, time_index]),
            "sun_altitude_deg": float(self.sun_altitude_deg[time_index]),
            "sun_azimuth_deg": 0.0,
            "moon_altitude_deg": 0.0,
            "moon_azimuth_deg": 0.0,
            "moon_separation_deg": float(self.moon_separation_deg[source_index, time_index]),
            "sun_separation_deg": 90.0,
        }


def source(index: int = 0, ext: float = 0.0, **overrides) -> Source:
    values = {
        "index": index,
        "name": f"J{index:04d}",
        "ext": ext,
        "ext_err": 0.1,
        "ra": 80.0,
        "dec": 22.0,
        "l": 180.0,
        "b": 0.0,
        "p_err_95": 0.2,
    }
    values.update(overrides)
    return Source(**values)


def fake_catalog_series(altitude, sun=-20.0, moon=90.0) -> FakeCatalogSeries:
    altitude = np.asarray(altitude, dtype=float)
    if altitude.ndim == 1:
        altitude = altitude[np.newaxis, :]
    times = altitude.shape[1]
    return FakeCatalogSeries(
        target_altitude_deg=altitude,
        target_zenith_deg=90.0 - altitude,
        sun_altitude_deg=np.full(times, sun, dtype=float),
        moon_separation_deg=np.full(altitude.shape, moon, dtype=float),
    )


def fake_evaluation(times: Sequence, boundary_seconds: float) -> ConstraintEvaluation:
    values = np.asarray([t.timestamp() - times[0].timestamp() - boundary_seconds for t in times])
    margins = {"synthetic": values}
    return ConstraintEvaluation(
        center_margins=margins,
        footprint_margins=margins,
        center_pass=values >= 0,
        footprint_pass=values >= 0,
    )
