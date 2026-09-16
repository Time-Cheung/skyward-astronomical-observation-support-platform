from __future__ import annotations

import csv
import io
import math
import ssl
from pathlib import Path
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import astropy.units as u
from astropy.coordinates import AltAz, SkyCoord
from astropy.time import Time

from .astronomy import J2000_FRAME
from .catalog import Source
from .config import GAIA_CACHE_TTL_SECONDS, GAIA_TAP_URL


class GaiaQueryError(RuntimeError):
    """A bounded online query failed; never confuse failure with zero stars."""


MAX_CACHE_ENTRIES = 32
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_CONCURRENT_QUERIES = 2
# Real default 5-degree cones need ~10-12 s from this TAP deployment even
# without sorting. Allow a bounded 20 s operation, still independent of maps.
QUERY_TIMEOUT_SECONDS = 20.0
_CACHE = OrderedDict()
_CACHE_LOCK = threading.Lock()
_QUERY_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_QUERIES)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def pointing_icrs(at_time: datetime, telescope) -> SkyCoord:
    frame = AltAz(obstime=Time(_utc(at_time)), location=telescope.location, pressure=0 * u.hPa)
    return SkyCoord(az=telescope.pointing_azimuth_deg * u.deg,
                    alt=telescope.pointing_altitude_deg * u.deg, frame=frame).icrs


def _adql(center: SkyCoord, radius_deg: float, limit: int, max_mag: float) -> str:
    return (
        f"SELECT TOP {limit} source_id, ra, dec, phot_g_mean_mag "
        "FROM gaiadr3.gaia_source WHERE phot_g_mean_mag IS NOT NULL "
        f"AND phot_g_mean_mag <= {max_mag:.3f} "
        "AND 1=CONTAINS(POINT('ICRS', ra, dec), "
        f"CIRCLE('ICRS', {center.ra.deg:.8f}, {center.dec.deg:.8f}, {radius_deg:.6f}))"
        # No global ORDER BY: a dense 5-degree cone can contain hundreds of
        # thousands of eligible stars. Sorting it defeats the bounded TOP
        # query. This is an unordered subset, NOT the brightest N stars.
    )


def _parse_csv(payload: bytes, limit: int) -> List[Source]:
    try:
        reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
        if not reader.fieldnames or not {"source_id", "ra", "dec"}.issubset(reader.fieldnames):
            raise ValueError("Gaia response missing source_id/ra/dec")
        rows = list(reader)[:limit]
        ids = [str(row["source_id"]).strip() for row in rows]
        if any(not value.isdecimal() for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("Invalid or duplicate Gaia source_id")
        if not rows:
            return []
        ra = [float(row["ra"]) for row in rows]
        dec = [float(row["dec"]) for row in rows]
        if any(not math.isfinite(a) or not math.isfinite(d) or not (0 <= a < 360 and -90 <= d <= 90) for a, d in zip(ra, dec)):
            raise ValueError("Invalid Gaia coordinates")
        # This is only a frame conversion of the published epoch J2016.0
        # direction. No space motion / proper motion propagation is performed.
        fk5 = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs").transform_to(J2000_FRAME)
        galactic = fk5.galactic
        sources = []
        for index, row in enumerate(rows):
            magnitude = float(row["phot_g_mean_mag"]) if row.get("phot_g_mean_mag", "").strip() else None
            if magnitude is not None and (not math.isfinite(magnitude) or not -100 < magnitude < 100):
                raise ValueError("Invalid Gaia G magnitude")
            sources.append(Source(
                # Query-local, collision-free presentation index only. Never
                # persist it as Gaia identity; source_key/source_id are strings.
                index=1_000_000_000_000_000 + index,
                name=ids[index], ext=0.0, ext_err=None,
                ra=float(fk5.ra[index].deg), dec=float(fk5.dec[index].deg),
                l=float(galactic.l[index].deg), b=float(galactic.b[index].deg), p_err_95=None,
                catalogue_label="Gaia DR3", catalogue_id="gaia-dr3", original_id=ids[index],
                source_type="gaia", gaia_mag=magnitude, footprint_kind="point",
                notes={"source_id": ids[index], "input_frame": "ICRS", "reference_epoch": "J2016.0",
                       "output_frame": "FK5 J2000", "proper_motion_applied": False},
            ))
        return sources
    except (UnicodeDecodeError, csv.Error, ValueError, KeyError, TypeError) as exc:
        raise GaiaQueryError(f"Invalid Gaia response: {exc}") from exc


def query_gaia_stars(
    at_time: datetime, telescope, radius_deg: float = 5.0,
    limit: int = 500, max_mag: float = 18.0,
    target_ra_deg: float | None = None, target_dec_deg: float | None = None,
) -> Tuple[List[Source], dict]:
    """Bounded cone query, separately requested after the base map is ready."""
    if not all(math.isfinite(float(value)) for value in (radius_deg, limit, max_mag)):
        raise GaiaQueryError("Gaia query parameters must be finite")
    if not (0.1 <= radius_deg <= 15 and 1 <= limit <= 2000 and 5 <= max_mag <= 22):
        raise GaiaQueryError("Gaia query parameters exceed bounds")
    if (target_ra_deg is None) != (target_dec_deg is None):
        raise GaiaQueryError("Both target coordinates are required")
    if target_ra_deg is not None:
        if not (0 <= target_ra_deg < 360 and -90 <= target_dec_deg <= 90):
            raise GaiaQueryError("Invalid target coordinates")
        center = SkyCoord(ra=target_ra_deg * u.deg, dec=target_dec_deg * u.deg, frame=J2000_FRAME).icrs
    else:
        center = pointing_icrs(at_time, telescope)
    # Exact query arguments in cache key: nearby but distinct cones are never
    # substituted for one another (important at the cone boundary).
    key = (float(center.ra.deg), float(center.dec.deg), float(radius_deg), int(limit), float(max_mag))
    now = time.monotonic()
    with _CACHE_LOCK:
        for expired in [k for k, v in _CACHE.items() if now - v[0] >= GAIA_CACHE_TTL_SECONDS]:
            del _CACHE[expired]
        cached = _CACHE.get(key)
        if cached:
            _CACHE.move_to_end(key)
            return list(cached[1]), {**cached[2], "cached": True}
    if not _QUERY_SLOTS.acquire(blocking=False):
        raise GaiaQueryError("Gaia query concurrency limit reached; retry later")
    started = time.monotonic()
    try:
        params = urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": _adql(center, radius_deg, int(limit) + 1, max_mag)})
        request = Request(f"{GAIA_TAP_URL}?{params}", headers={"Accept": "text/csv", "User-Agent": "Skyward/0.3"})
        tls = ssl.create_default_context()
        # The Axon node may set SSL_CERT_FILE to its private gateway CA only.
        # Supplement it with the OS public root store; never disable verification.
        system_ca = ssl.get_default_verify_paths().openssl_cafile
        if system_ca and Path(system_ca).is_file():
            tls.load_verify_locations(cafile=system_ca)
        with urlopen(request, timeout=QUERY_TIMEOUT_SECONDS, context=tls) as response:
            chunks, received = [], 0
            while True:
                remaining = QUERY_TIMEOUT_SECONDS - (time.monotonic() - started)
                if remaining <= 0:
                    raise GaiaQueryError("Gaia response exceeded query timeout")
                # urllib's read timeout alone is per read. Reduce it to the
                # remaining operation budget so a slow stream cannot extend
                # the network phase indefinitely. BytesIO test doubles have
                # no socket; production HTTPSResponse exposes the SSLSocket.
                raw = getattr(getattr(response, "fp", None), "raw", None)
                sock = getattr(raw, "_sock", None)
                if sock is not None:
                    sock.settimeout(remaining)
                chunk = response.read1(min(65536, MAX_RESPONSE_BYTES + 1 - received))
                if not chunk:
                    break
                chunks.append(chunk)
                received += len(chunk)
                if received > MAX_RESPONSE_BYTES:
                    raise GaiaQueryError("Gaia response exceeded bounded byte limit")
            payload = b"".join(chunks)
        all_sources = _parse_csv(payload, int(limit) + 1)
        sources = all_sources[:int(limit)]
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise GaiaQueryError(f"Gaia DR3 online query failed: {exc}") from exc
    finally:
        _QUERY_SLOTS.release()
    meta = {
        "cached": False, "count": len(sources), "zero": not sources, "limit": int(limit),
        "truncated": len(all_sources) > limit, "error": None, "status": "ok" if sources else "zero",
        "bytes": len(payload), "center_ra_icrs_deg": key[0], "center_dec_icrs_deg": key[1],
        "center_mode": "target" if target_ra_deg is not None else "current_pointing",
        "radius_deg": radius_deg, "max_mag": max_mag, "reference_epoch": "J2016.0",
        "input_frame": "ICRS", "output_frame": "FK5 J2000", "proper_motion_applied": False,
        "query_timeout_seconds": QUERY_TIMEOUT_SECONDS,
        "selection": "bounded_unordered_subset", "ordering": "unspecified",
        "brightest_n": False, "complete": len(all_sources) <= limit,
        "warning": "Bounded unordered subset within the requested cone and magnitude cut; not the brightest N or a representative sample. Frame conversion only; Gaia J2016.0 positions are not propagated for proper motion.",
    }
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), list(sources), meta)
        while len(_CACHE) > MAX_CACHE_ENTRIES:
            _CACHE.popitem(last=False)
    return sources, meta
