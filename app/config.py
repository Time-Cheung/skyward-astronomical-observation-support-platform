from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from zoneinfo import ZoneInfo

import astropy.units as u
from astropy.coordinates import EarthLocation

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CATALOG_PATH = DATA_DIR / "2LHAASO.txt"
ENRICHMENT_PATH = DATA_DIR / "source_enrichment.json"
IERS_BUNDLED_PATH = DATA_DIR / "iers" / "finals2000A.all"

# Confirmed LACT site parameters. The legacy constants stay public because
# external scripts and the API configuration endpoint already use them.
SITE_LONGITUDE_DEG = 100.0266666667
SITE_LATITUDE_DEG = 29.3575
SITE_ALTITUDE_M = 4410.0
SITE_TIMEZONE_NAME = "Asia/Shanghai"
SITE_TIMEZONE = ZoneInfo(SITE_TIMEZONE_NAME)
SITE_LOCATION = EarthLocation(
    lon=SITE_LONGITUDE_DEG * u.deg,
    lat=SITE_LATITUDE_DEG * u.deg,
    height=SITE_ALTITUDE_M * u.m,
)

FOV_DIAMETER_DEG = 8.3
FOV_RADIUS_DEG = FOV_DIAMETER_DEG / 2.0
COORDINATE_FRAME_LABEL = "FK5 J2000"
GEOMETRY_ONLY = True

# The homepage colours use these values in addition to the current telescope
# pointing/FoV check. Keep the values as plain data here so the HTTP layer,
# templates and future telescope adapters cannot accidentally drift apart.
DEFAULT_PLANNER_CONSTRAINT_VALUES = {
    "sun_max_altitude_deg": -18.0,
    "moon_min_separation_deg": 30.0,
    "target_min_zenith_deg": 0.0,
    "target_max_zenith_deg": 60.0,
    "minimum_window_seconds": 0,
}


@dataclass(frozen=True)
class TelescopeConfig:
    """Immutable site, FoV and current-pointing context for one calculation.

    Pointing is deliberately an adapter boundary. LACT telemetry is not yet
    connected, so the current implementation supplies zenith. Every astronomy,
    constraint and SVG function receives this object instead of silently
    reading module globals. This keeps a future live Alt/Az feed and the
    temporary custom-observatory mode scientifically consistent.
    """

    name: str
    longitude_deg: float
    latitude_deg: float
    altitude_m: float
    timezone_offset_hours: float
    fov_diameter_deg: float
    pointing_altitude_deg: float = 90.0
    pointing_azimuth_deg: float = 0.0
    pointing_mode: str = "fixed_zenith_pending_telemetry"
    source: str = "Operator-provided configuration"

    def __post_init__(self) -> None:
        numeric = (
            self.longitude_deg,
            self.latitude_deg,
            self.altitude_m,
            self.timezone_offset_hours,
            self.fov_diameter_deg,
            self.pointing_altitude_deg,
            self.pointing_azimuth_deg,
        )
        if not all(isfinite(float(value)) for value in numeric):
            raise ValueError("telescope configuration values must be finite")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("longitude must be within -180° to 180°")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude must be within -90° to 90°")
        if not -12.0 <= self.timezone_offset_hours <= 14.0:
            raise ValueError("UTC offset must be within -12 to +14 hours")
        if not 0.01 <= self.fov_diameter_deg <= 180.0:
            raise ValueError("telescope FoV diameter must be within 0.01° to 180°")
        if not -90.0 <= self.pointing_altitude_deg <= 90.0:
            raise ValueError("pointing altitude must be within -90° to 90°")
        if not 0.0 <= self.pointing_azimuth_deg < 360.0:
            raise ValueError("pointing azimuth must be within 0° to 360°")

    @property
    def location(self) -> EarthLocation:
        return EarthLocation(
            lon=self.longitude_deg * u.deg,
            lat=self.latitude_deg * u.deg,
            height=self.altitude_m * u.m,
        )

    @property
    def fov_radius_deg(self) -> float:
        return self.fov_diameter_deg / 2.0

    @property
    def timezone_label(self) -> str:
        sign = "+" if self.timezone_offset_hours >= 0 else "-"
        absolute = abs(self.timezone_offset_hours)
        hours = int(absolute)
        minutes = int(round((absolute - hours) * 60))
        return "UTC{}{:02d}:{:02d}".format(sign, hours, minutes)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "longitude_deg": self.longitude_deg,
            "latitude_deg": self.latitude_deg,
            "altitude_m": self.altitude_m,
            "timezone_offset_hours": self.timezone_offset_hours,
            "timezone_label": self.timezone_label,
            "fov_diameter_deg": self.fov_diameter_deg,
            "fov_radius_deg": self.fov_radius_deg,
            "pointing": {
                "altitude_deg": self.pointing_altitude_deg,
                "azimuth_deg": self.pointing_azimuth_deg,
                "mode": self.pointing_mode,
            },
            "source": self.source,
        }


LACT_TELESCOPE = TelescopeConfig(
    name="LACT",
    longitude_deg=SITE_LONGITUDE_DEG,
    latitude_deg=SITE_LATITUDE_DEG,
    altitude_m=SITE_ALTITUDE_M,
    timezone_offset_hours=8.0,
    fov_diameter_deg=FOV_DIAMETER_DEG,
    source="Operator-provided LHAASO site coordinates",
)


def custom_telescope(
    longitude_deg: float,
    latitude_deg: float,
    altitude_m: float,
    timezone_offset_hours: float,
    fov_diameter_deg: float,
) -> TelescopeConfig:
    """Create one non-persistent WGS-84 observer configuration for this request."""
    return TelescopeConfig(
        name="Custom telescope",
        longitude_deg=float(longitude_deg),
        latitude_deg=float(latitude_deg),
        altitude_m=float(altitude_m),
        timezone_offset_hours=float(timezone_offset_hours),
        fov_diameter_deg=float(fov_diameter_deg),
        source="Operator-supplied WGS-84 configuration; not persisted",
    )


DEFAULT_GRID_STEP_SECONDS = 60
# Sampling is intentionally one-second rather than relying on a heuristic
# crossing detector. It covers all candidate windows without assuming an
# unproven angular-rate bound for every possible future constraint.
BOUNDARY_TOLERANCE_SECONDS = 1.0
# Guaranteed one-second window discovery is intentionally memory bounded.
# A one-day request has 86,401 samples and completes with a measured peak below
# 200 MiB on the target LAN server. Longer horizons will be reintroduced only
# with a validated, streaming/event-solver implementation.
MAX_CALCULATION_DAYS = 1
# At 86,401 samples per requested day, 10-minute chunks reduce temporary
# Astropy coordinate allocations while still sharing Sun/Moon ephemerides
# across all fixed-FoV candidates.
WINDOW_SCAN_CHUNK_SECONDS = 600
# One-second candidate sampling covers the maximum one-day request range
# (86,401 instants including both endpoints), while a 300,000-point safety
# ceiling leaves room for explicitly appended endpoints and future diagnostics.
MAX_GRID_POINTS = 300_000
CURRENT_STATUS_LOOKAHEAD_SECONDS = 7 * 24 * 3600
MAX_STATUS_SAMPLES = 3_601

CATALOG_ACCEPTED_COLUMNS = (
    "index", "name", "ext", "ext_err", "ra", "dec", "l", "b", "p_err(95\%)",
)
CATALOG_CANONICAL_COLUMNS = (
    "index", "name", "ext", "ext_err", "ra", "dec", "l", "b", "p_err(95%)",
)
CATALOG_EXPECTED_COLUMNS = CATALOG_CANONICAL_COLUMNS
CATALOG_EXPECTED_ROWS = 190

CAPABILITIES = {
    "geometry": True,
    "catalogue": True,
    "interactive_sky_map": True,
    "custom_telescope": True,
    "joint_observation": False,
    "weather": False,
    "telemetry": False,
    "authentication": False,
}


@dataclass(frozen=True)
class SiteMetadata:
    longitude_deg: float = SITE_LONGITUDE_DEG
    latitude_deg: float = SITE_LATITUDE_DEG
    altitude_m: float = SITE_ALTITUDE_M
    timezone: str = SITE_TIMEZONE_NAME
    source: str = "Operator-provided LHAASO site coordinates"


SITE_METADATA = SiteMetadata()
