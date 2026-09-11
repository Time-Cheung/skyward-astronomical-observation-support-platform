from __future__ import annotations

import csv
import io
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import astropy.units as u
from astropy.coordinates import AltAz, SkyCoord
from astropy.time import Time

from .astronomy import J2000_FRAME
from .catalog import Source
from .config import GAIA_CACHE_TTL_SECONDS, GAIA_QUERY_TIMEOUT_SECONDS, GAIA_TAP_URL


class GaiaQueryError(RuntimeError):
    """Raised when the online Gaia DR3 service cannot answer a bounded query."""


_CACHE: Dict[Tuple[float, float, float, int, float], Tuple[float, List[Source]]] = {}
_CACHE_LOCK = threading.Lock()


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def pointing_icrs(at_time: datetime, telescope) -> SkyCoord:
    moment = Time(_utc(at_time))
    frame = AltAz(obstime=moment, location=telescope.location, pressure=0 * u.hPa)
    return SkyCoord(
        az=telescope.pointing_azimuth_deg * u.deg,
        alt=telescope.pointing_altitude_deg * u.deg,
        frame=frame,
    ).transform_to("icrs")


def _adql(center: SkyCoord, radius_deg: float, limit: int, max_mag: float) -> str:
    ra = float(center.ra.deg)
    dec = float(center.dec.deg)
    return (
        "SELECT TOP {limit} source_id, ra, dec, phot_g_mean_mag "
        "FROM gaiadr3.gaia_source "
        "WHERE phot_g_mean_mag IS NOT NULL "
        "AND phot_g_mean_mag <= {max_mag:.3f} "
        "AND 1=CONTAINS(POINT('ICRS', ra, dec), "
        "CIRCLE('ICRS', {ra:.8f}, {dec:.8f}, {radius:.6f})) "
        "ORDER BY phot_g_mean_mag"
    ).format(limit=limit, max_mag=max_mag, ra=ra, dec=dec, radius=radius_deg)


def _parse_csv(payload: bytes, limit: int) -> List[Source]:
    try:
        text = payload.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or not {"source_id", "ra", "dec"}.issubset(reader.fieldnames):
            raise ValueError("Gaia response did not contain source_id, ra and dec columns")
        rows = list(reader)
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise GaiaQueryError(str(exc)) from exc
    sources: List[Source] = []
    for index, row in enumerate(rows[:limit]):
        try:
            source_id = str(row["source_id"]).strip()
            icrs = SkyCoord(ra=float(row["ra"]) * u.deg, dec=float(row["dec"]) * u.deg, frame="icrs")
            fk5 = icrs.transform_to(J2000_FRAME)
            l = float(fk5.galactic.l.deg)
            b = float(fk5.galactic.b.deg)
            magnitude_text = str(row.get("phot_g_mean_mag", "")).strip()
            magnitude = float(magnitude_text) if magnitude_text else None
            if magnitude is not None and not (-100.0 < magnitude < 100.0):
                raise ValueError("phot_g_mean_mag is outside a finite range")
            sources.append(Source(
                index=index,
                name=source_id,
                ext=0.0,
                ext_err=None,
                ra=float(fk5.ra.deg),
                dec=float(fk5.dec.deg),
                l=l,
                b=b,
                p_err_95=None,
                catalogue_label="Gaia DR3",
                source_type="gaia",
                gaia_mag=magnitude,
            ))
        except (TypeError, ValueError, KeyError) as exc:
            raise GaiaQueryError(f"Invalid Gaia row: {exc}") from exc
    return sources


def query_gaia_stars(
    at_time: datetime, telescope, radius_deg: float = 5.0,
    limit: int = 500, max_mag: float = 18.0,
) -> Tuple[List[Source], dict]:
    """Query a bounded Gaia DR3 cone around the current telescope pointing.

    Results are process-cached for a few hours. The caller can therefore keep
    the LAN page responsive while the underlying service is rate-limited or
    temporarily unreachable.
    """
    radius_deg = max(0.1, min(float(radius_deg), 15.0))
    limit = max(1, min(int(limit), 2000))
    max_mag = max(5.0, min(float(max_mag), 22.0))
    center = pointing_icrs(at_time, telescope)
    key = (round(float(center.ra.deg), 3), round(float(center.dec.deg), 3), round(radius_deg, 2), limit, round(max_mag, 1))
    now = time.monotonic()
    with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and now - cached[0] < GAIA_CACHE_TTL_SECONDS:
            return list(cached[1]), {"cached": True, "center_ra_icrs_deg": key[0], "center_dec_icrs_deg": key[1]}
    query = _adql(center, radius_deg, limit, max_mag)
    params = urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": query})
    request = Request(
        f"{GAIA_TAP_URL}?{params}",
        headers={"Accept": "text/csv", "User-Agent": "Skyward/0.2 LAN astronomy helper"},
    )
    try:
        with urlopen(request, timeout=GAIA_QUERY_TIMEOUT_SECONDS) as response:
            payload = response.read(8 * 1024 * 1024 + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise GaiaQueryError(f"Gaia DR3 online query failed: {exc}") from exc
    if len(payload) > 8 * 1024 * 1024:
        raise GaiaQueryError("Gaia DR3 response exceeded the bounded 8 MiB limit")
    sources = _parse_csv(payload, limit)
    with _CACHE_LOCK:
        _CACHE[key] = (now, list(sources))
    return sources, {"cached": False, "center_ra_icrs_deg": key[0], "center_dec_icrs_deg": key[1]}
