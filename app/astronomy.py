from __future__ import annotations

import os
import threading
import time as _time_module
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import astropy.units as u
import numpy as np
from astropy.coordinates import AltAz, FK5, SkyCoord, get_body, get_sun
from astropy.time import Time
from astropy.utils import iers
from astropy.utils.exceptions import AstropyWarning

from .catalog import Source
from .config import (
    IERS_BUNDLED_PATH, IERS_CACHE_DIR, IERS_CACHE_PATH, IERS_ONLINE_URL,
    IERS_REFRESH_INTERVAL_SECONDS, IERS_REQUEST_TIMEOUT_SECONDS,
    LACT_TELESCOPE, TelescopeConfig,
)

# Use an explicit bounded updater instead of Astropy's implicit downloader.
# Geometry remains available from the project-bundled file when the LAN has no
# egress; a successful online refresh atomically replaces only the user cache.
iers.conf.auto_download = False
iers.conf.auto_max_age = None
iers.conf.iers_degraded_accuracy = "warn"
IERS_LOCK = threading.RLock()
IERS_REFRESH_STATE = {"last_attempt": None, "last_success": None, "last_error": None}


def _open_iers(path: Path):
    table = iers.IERS_A.open(str(path))
    iers.earth_orientation_table.set(table)
    return table


def _cache_is_fresh() -> bool:
    try:
        return IERS_CACHE_PATH.is_file() and (
            _time_module.time() - IERS_CACHE_PATH.stat().st_mtime
            < IERS_REFRESH_INTERVAL_SECONDS
        )
    except OSError:
        return False


if _cache_is_fresh():
    IERS_TABLE = _open_iers(IERS_CACHE_PATH)
    IERS_SOURCE_PATH = IERS_CACHE_PATH
    IERS_SOURCE_KIND = "online_cache"
else:
    fallback_path = IERS_BUNDLED_PATH if IERS_BUNDLED_PATH.exists() else Path(iers.IERS_A_FILE)
    IERS_TABLE = _open_iers(fallback_path)
    IERS_SOURCE_PATH = fallback_path
    IERS_SOURCE_KIND = "bundled"


def refresh_iers(*, blocking: bool = False) -> None:
    """Refresh the IERS-A cache when its substantive weekly cycle is due."""
    if not blocking:
        thread = threading.Thread(target=lambda: refresh_iers(blocking=True), daemon=True, name="skyward-iers-refresh")
        thread.start()
        return
    global IERS_TABLE, IERS_SOURCE_PATH, IERS_SOURCE_KIND
    with IERS_LOCK:
        IERS_REFRESH_STATE["last_attempt"] = datetime.now(timezone.utc).isoformat()
    try:
        IERS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        request = Request(
            IERS_ONLINE_URL,
            headers={"Accept": "text/plain", "User-Agent": "Skyward/2.1 LAN astronomy helper"},
        )
        with urlopen(request, timeout=IERS_REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read(16 * 1024 * 1024 + 1)
        if len(payload) > 16 * 1024 * 1024:
            raise OSError("IERS response exceeded the bounded 16 MiB limit")
        temporary = IERS_CACHE_PATH.with_suffix(".download")
        temporary.write_bytes(payload)
        # Parse the download before publishing it as the active cache. A
        # truncated or HTML error response must never poison the last-known
        # good cache used by the offline geometry path.
        table = iers.IERS_A.open(str(temporary))
        os.replace(temporary, IERS_CACHE_PATH)
        iers.earth_orientation_table.set(table)
        with IERS_LOCK:
            IERS_TABLE = table
            IERS_SOURCE_PATH = IERS_CACHE_PATH
            IERS_SOURCE_KIND = "online_cache"
            IERS_REFRESH_STATE["last_success"] = datetime.now(timezone.utc).isoformat()
            IERS_REFRESH_STATE["last_error"] = None
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        with IERS_LOCK:
            IERS_REFRESH_STATE["last_error"] = str(exc)


def _start_iers_refresh() -> None:
    # Never make the first page request wait for the network.
    refresh_iers(blocking=False)


_start_iers_refresh()

J2000_FRAME = FK5(equinox=Time("J2000"))


@dataclass
class CatalogGeometrySeries:
    times: Time
    target_altitude_deg: np.ndarray
    target_azimuth_deg: np.ndarray
    target_zenith_deg: np.ndarray
    sun_altitude_deg: np.ndarray
    sun_azimuth_deg: np.ndarray
    moon_altitude_deg: np.ndarray
    moon_azimuth_deg: np.ndarray
    moon_separation_deg: np.ndarray
    sun_separation_deg: np.ndarray
    warnings: list[str]
    # Optional only to preserve historic synthetic test fixtures. Production
    # vector geometry always fills this with the live pointing separation.
    target_pointing_separation_deg: np.ndarray | None = None

    def source_at(self, source_index: int, time_index: int = 0) -> dict:
        return {
            "target_altitude_deg": float(self.target_altitude_deg[source_index, time_index]),
            "target_azimuth_deg": float(self.target_azimuth_deg[source_index, time_index]),
            "target_zenith_deg": float(self.target_zenith_deg[source_index, time_index]),
            "target_pointing_separation_deg": float(
                self.target_pointing_separation_deg[source_index, time_index]
            ) if self.target_pointing_separation_deg is not None else 0.0,
            "sun_altitude_deg": float(self.sun_altitude_deg[time_index]),
            "sun_azimuth_deg": float(self.sun_azimuth_deg[time_index]),
            "moon_altitude_deg": float(self.moon_altitude_deg[time_index]),
            "moon_azimuth_deg": float(self.moon_azimuth_deg[time_index]),
            "moon_separation_deg": float(self.moon_separation_deg[source_index, time_index]),
            "sun_separation_deg": float(self.sun_separation_deg[source_index, time_index]),
        }


@dataclass
class GeometrySeries:
    times: Time
    unix_seconds: np.ndarray
    target_altitude_deg: np.ndarray
    target_azimuth_deg: np.ndarray
    target_zenith_deg: np.ndarray
    target_pointing_separation_deg: np.ndarray
    sun_altitude_deg: np.ndarray
    sun_azimuth_deg: np.ndarray
    moon_altitude_deg: np.ndarray
    moon_azimuth_deg: np.ndarray
    moon_separation_deg: np.ndarray
    sun_separation_deg: np.ndarray
    warnings: list[str]

    def at(self, index: int) -> dict:
        return {
            "target_altitude_deg": float(self.target_altitude_deg[index]),
            "target_azimuth_deg": float(self.target_azimuth_deg[index]),
            "target_zenith_deg": float(self.target_zenith_deg[index]),
            "target_pointing_separation_deg": float(self.target_pointing_separation_deg[index]),
            "sun_altitude_deg": float(self.sun_altitude_deg[index]),
            "sun_azimuth_deg": float(self.sun_azimuth_deg[index]),
            "moon_altitude_deg": float(self.moon_altitude_deg[index]),
            "moon_azimuth_deg": float(self.moon_azimuth_deg[index]),
            "moon_separation_deg": float(self.moon_separation_deg[index]),
            "sun_separation_deg": float(self.sun_separation_deg[index]),
        }


def source_coord(source: Source) -> SkyCoord:
    return SkyCoord(ra=source.ra * u.deg, dec=source.dec * u.deg, frame=J2000_FRAME)


def catalog_coords(sources: Sequence[Source]) -> SkyCoord:
    return SkyCoord(
        ra=np.asarray([source.ra for source in sources]) * u.deg,
        dec=np.asarray([source.dec for source in sources]) * u.deg,
        frame=J2000_FRAME,
    )


def _time(value: Union[Time, datetime, Sequence[datetime], np.ndarray]) -> Time:
    """Normalise all geometry requests to a one-dimensional UTC Astropy time."""
    if isinstance(value, Time):
        return Time(np.atleast_1d(value.jd), format="jd", scale=value.scale)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return Time([value.astimezone(timezone.utc)])
    normalized = []
    for item in value:
        if isinstance(item, datetime) and item.tzinfo is None:
            item = item.replace(tzinfo=timezone.utc)
        if isinstance(item, datetime):
            item = item.astimezone(timezone.utc)
        normalized.append(item)
    return Time(normalized)


def _frames(obstime: Time, telescope: TelescopeConfig) -> tuple[AltAz, AltAz, SkyCoord]:
    """Build shared topocentric frames and the current pointing direction."""
    body_frame = AltAz(obstime=obstime, location=telescope.location, pressure=0 * u.hPa)
    target_frame = AltAz(
        obstime=obstime[np.newaxis, :], location=telescope.location, pressure=0 * u.hPa
    )
    pointing = SkyCoord(
        az=np.full(obstime.size, telescope.pointing_azimuth_deg) * u.deg,
        alt=np.full(obstime.size, telescope.pointing_altitude_deg) * u.deg,
        frame=body_frame,
    )
    return target_frame, body_frame, pointing


def compute_catalog_geometry(
    sources: Sequence[Source],
    times: Union[Time, datetime, Sequence[datetime], np.ndarray],
    telescope: TelescopeConfig = LACT_TELESCOPE,
) -> CatalogGeometrySeries:
    """Vectorized observer-frame geometry for every catalogue source.

    Sun and Moon separations are measured only after transforming all bodies to
    the same site-specific AltAz frame. The same frame also gives a direct
    target-to-current-pointing angular separation for the live all-sky status.
    """
    obstime = _time(times)
    coords = catalog_coords(sources)
    target_frame, body_frame, pointing_altaz = _frames(obstime, telescope)
    with warnings.catch_warnings(record=True) as warning_records:
        warnings.simplefilter("always", AstropyWarning)
        target_altaz = coords[:, np.newaxis].transform_to(target_frame)
        sun_altaz = get_sun(obstime).transform_to(body_frame)
        moon_altaz = get_body("moon", obstime, telescope.location).transform_to(body_frame)
        moon_sep = target_altaz.separation(moon_altaz).to_value(u.deg)
        sun_sep = target_altaz.separation(sun_altaz).to_value(u.deg)
        pointing_sep = target_altaz.separation(pointing_altaz).to_value(u.deg)
        caught = sorted({str(record.message) for record in warning_records})
    altitude = np.asarray(target_altaz.alt.to_value(u.deg), dtype=float)
    return CatalogGeometrySeries(
        times=obstime,
        target_altitude_deg=altitude,
        target_azimuth_deg=np.asarray(target_altaz.az.to_value(u.deg), dtype=float),
        target_zenith_deg=90.0 - altitude,
        target_pointing_separation_deg=np.asarray(pointing_sep, dtype=float),
        sun_altitude_deg=np.atleast_1d(sun_altaz.alt.to_value(u.deg)).astype(float),
        sun_azimuth_deg=np.atleast_1d(sun_altaz.az.to_value(u.deg)).astype(float),
        moon_altitude_deg=np.atleast_1d(moon_altaz.alt.to_value(u.deg)).astype(float),
        moon_azimuth_deg=np.atleast_1d(moon_altaz.az.to_value(u.deg)).astype(float),
        moon_separation_deg=np.asarray(moon_sep, dtype=float),
        sun_separation_deg=np.asarray(sun_sep, dtype=float),
        warnings=caught,
    )


def compute_geometry(
    source: Source,
    times: Union[Time, datetime, Sequence[datetime], np.ndarray],
    telescope: TelescopeConfig = LACT_TELESCOPE,
) -> GeometrySeries:
    """Return one source's topocentric geometry for one or more UTC times."""
    obstime = _time(times)
    _, body_frame, pointing_altaz = _frames(obstime, telescope)
    target = source_coord(source)
    with warnings.catch_warnings(record=True) as warning_records:
        warnings.simplefilter("always", AstropyWarning)
        target_altaz = target.transform_to(body_frame)
        sun_altaz = get_sun(obstime).transform_to(body_frame)
        moon_altaz = get_body("moon", obstime, telescope.location).transform_to(body_frame)
        moon_sep = target_altaz.separation(moon_altaz).to_value(u.deg)
        sun_sep = target_altaz.separation(sun_altaz).to_value(u.deg)
        pointing_sep = target_altaz.separation(pointing_altaz).to_value(u.deg)
        caught = sorted({str(record.message) for record in warning_records})

    target_alt = np.atleast_1d(target_altaz.alt.to_value(u.deg)).astype(float)
    return GeometrySeries(
        times=obstime,
        unix_seconds=np.atleast_1d(obstime.unix).astype(float),
        target_altitude_deg=target_alt,
        target_azimuth_deg=np.atleast_1d(target_altaz.az.to_value(u.deg)).astype(float),
        target_zenith_deg=90.0 - target_alt,
        target_pointing_separation_deg=np.atleast_1d(pointing_sep).astype(float),
        sun_altitude_deg=np.atleast_1d(sun_altaz.alt.to_value(u.deg)).astype(float),
        sun_azimuth_deg=np.atleast_1d(sun_altaz.az.to_value(u.deg)).astype(float),
        moon_altitude_deg=np.atleast_1d(moon_altaz.alt.to_value(u.deg)).astype(float),
        moon_azimuth_deg=np.atleast_1d(moon_altaz.az.to_value(u.deg)).astype(float),
        moon_separation_deg=np.atleast_1d(moon_sep).astype(float),
        sun_separation_deg=np.atleast_1d(sun_sep).astype(float),
        warnings=caught,
    )


def format_ra_dec(source: Source) -> dict:
    coord = source_coord(source)
    return {
        "ra_hms": coord.ra.to_string(unit=u.hour, sep=":", precision=2, pad=True),
        "dec_dms": coord.dec.to_string(unit=u.deg, sep=":", precision=1, alwayssign=True, pad=True),
    }


def iers_status() -> dict:
    """Expose coverage and non-blocking online refresh state."""
    table = IERS_TABLE
    first_mjd = float(table["MJD"][0].value)
    last_mjd = float(table["MJD"][-1].value)
    predictive_mjd = table.meta.get("predictive_mjd")
    now_mjd = float(Time.now().mjd)
    try:
        age_seconds = max(0.0, _time_module.time() - Path(IERS_SOURCE_PATH).stat().st_mtime)
    except OSError:
        age_seconds = None
    return {
        "source": str(IERS_SOURCE_PATH),
        "source_kind": IERS_SOURCE_KIND,
        "first_mjd": first_mjd,
        "last_mjd": last_mjd,
        "predictive_mjd": float(predictive_mjd) if predictive_mjd is not None else None,
        "current_mjd": now_mjd,
        "covers_current_time": first_mjd <= now_mjd <= last_mjd,
        "current_values_are_predicted": bool(predictive_mjd is not None and now_mjd >= float(predictive_mjd)),
        "online_priority": True,
        "auto_download": False,
        "cache_path": str(IERS_CACHE_PATH),
        "age_seconds": age_seconds,
        "update_interval_days": IERS_REFRESH_INTERVAL_SECONDS / 86400,
        "update_due": age_seconds is None or age_seconds >= IERS_REFRESH_INTERVAL_SECONDS,
        "last_attempt": IERS_REFRESH_STATE.get("last_attempt"),
        "last_success": IERS_REFRESH_STATE.get("last_success"),
        "last_error": IERS_REFRESH_STATE.get("last_error"),
    }
