from __future__ import annotations

import csv
import io
import math
import ssl
from dataclasses import replace
from pathlib import Path
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import List, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

import astropy.units as u
from astropy.coordinates import AltAz, SkyCoord
from astropy.time import Time

from .astronomy import J2000_FRAME
from .catalog import Source
from .config import GAIA_CACHE_TTL_SECONDS, GAIA_QUERY_TIMEOUT_SECONDS, GAIA_TAP_URL


class GaiaQueryError(RuntimeError):
    """A bounded online query failed; never confuse failure with zero stars."""

    def __init__(self, message: str, *, metadata: dict | None = None):
        super().__init__(message)
        self.metadata = metadata if metadata is not None else {}


MAX_CACHE_ENTRIES = 32
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_CONCURRENT_QUERIES = 2
# Small/default queries use the synchronous TAP endpoint. A primary request is
# allowed 30 seconds; larger requests use UWS async TAP with the separate,
# finite total polling/download budget below.
QUERY_TIMEOUT_SECONDS = float(GAIA_QUERY_TIMEOUT_SECONDS)
ASYNC_TOTAL_BUDGET_SECONDS = 30.0
ASYNC_QUERY_TIMEOUT_SECONDS = ASYNC_TOTAL_BUDGET_SECONDS
ASYNC_POLL_INTERVAL_SECONDS = 0.25
ASYNC_CLEANUP_RESERVE_SECONDS = 0.5
DEFAULT_RADIUS_DEG = 1.0
DEFAULT_LIMIT = 10
DEFAULT_MAX_MAG = 10.0
MAX_RADIUS_DEG = 5.0
GAIA_MAX_ROWS = 500
LARGE_QUERY_RADIUS_DEG = DEFAULT_RADIUS_DEG
LARGE_QUERY_LIMIT = DEFAULT_LIMIT
LARGE_QUERY_MAX_MAG = DEFAULT_MAX_MAG
FALLBACK_SUBCONE_COUNT = 5
FALLBACK_QUERY_TIMEOUT_SECONDS = 4.0
# A synchronous timeout fallback is finite and independently bounded. The
# async path never enters it, so its 30-second polling/download budget remains
# the declared upper bound for every large-query request.
TOTAL_QUERY_BUDGET_SECONDS = QUERY_TIMEOUT_SECONDS + FALLBACK_SUBCONE_COUNT * FALLBACK_QUERY_TIMEOUT_SECONDS
_CACHE = OrderedDict()
_CACHE_LOCK = threading.Lock()
_QUERY_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT_QUERIES)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def pointing_icrs(at_time: datetime, telescope) -> SkyCoord:
    frame = AltAz(obstime=Time(_utc(at_time)), location=telescope.location, pressure=0 * u.hPa)
    return SkyCoord(az=telescope.pointing_azimuth_deg * u.deg,
                    alt=telescope.pointing_altitude_deg * u.deg, frame=frame).icrs


def _cone_condition(center: SkyCoord, radius_deg: float) -> str:
    return (
        "1=CONTAINS(POINT('ICRS', ra, dec), "
        f"CIRCLE('ICRS', {center.ra.deg:.8f}, {center.dec.deg:.8f}, {radius_deg:.6f}))"
    )


def _adql(
    center: SkyCoord, radius_deg: float, limit: int, max_mag: float,
    boundary_center: SkyCoord | None = None, boundary_radius_deg: float | None = None,
    order_center: SkyCoord | None = None,
) -> str:
    conditions = [
        "phot_g_mean_mag IS NOT NULL",
        f"phot_g_mean_mag <= {max_mag:.3f}",
        _cone_condition(center, radius_deg),
    ]
    # Fallback subcones may overlap the edge of the requested cone. Keep the
    # original cone as an explicit ADQL predicate so no fallback request can
    # widen the returned footprint.
    if boundary_center is not None and boundary_radius_deg is not None:
        conditions.append(_cone_condition(boundary_center, boundary_radius_deg))
    query = (
        f"SELECT TOP {limit} source_id, ra, dec, parallax, parallax_error, pmra, pmra_error, pmdec, pmdec_error, phot_g_mean_mag, phot_bp_mean_mag, phot_rp_mean_mag, bp_rp, ruwe, visibility_periods_used "
        "FROM gaiadr3.gaia_source WHERE " + " AND ".join(conditions)
    )
    # The service performs a bounded nearest-neighbour ordering before TOP is
    # applied. The client repeats the angular sort after frame conversion so a
    # provider or test double cannot silently return an arbitrary subset.
    distance_center = order_center or center
    query += (
        " ORDER BY DISTANCE(POINT('ICRS', ra, dec), "
        f"POINT('ICRS', {distance_center.icrs.ra.deg:.8f}, {distance_center.icrs.dec.deg:.8f}))"
    )
    return query


def _optional_number(row: dict, key: str) -> float | None:
    value = row.get(key)
    if value is None or str(value).strip() == "":
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid Gaia {key}") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Invalid Gaia {key}")
    return parsed


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
            values = {key: _optional_number(row, key) for key in (
                "parallax", "parallax_error", "pmra", "pmra_error", "pmdec", "pmdec_error",
                "phot_g_mean_mag", "phot_bp_mean_mag", "phot_rp_mean_mag", "bp_rp", "ruwe",
                "visibility_periods_used",
            )}
            magnitude = values["phot_g_mean_mag"]
            if magnitude is not None and not -100 < magnitude < 100:
                raise ValueError("Invalid Gaia G magnitude")
            parallax = values["parallax"]
            inverse_distance = 1000.0 / parallax if parallax is not None and parallax > 0 else None
            notes = {
                "source_id": ids[index], "input_frame": "ICRS", "reference_epoch": "J2016.0",
                "output_frame": "FK5 J2000", "proper_motion_applied": False,
                "query_fields": {
                    "parallax_mas": values["parallax"], "parallax_error_mas": values["parallax_error"],
                    "pmra_mas_per_year": values["pmra"], "pmra_error_mas_per_year": values["pmra_error"],
                    "pmdec_mas_per_year": values["pmdec"], "pmdec_error_mas_per_year": values["pmdec_error"],
                    "phot_g_mag": values["phot_g_mean_mag"], "phot_bp_mag": values["phot_bp_mean_mag"],
                    "phot_rp_mag": values["phot_rp_mean_mag"], "bp_rp_mag": values["bp_rp"],
                    "ruwe": values["ruwe"], "visibility_periods_used": values["visibility_periods_used"],
                },
                "distance": {
                    "inverse_parallax_distance_pc": inverse_distance,
                    "method": "1000 / parallax_mas; no prior or uncertainty correction",
                    "status": "estimate_from_positive_parallax" if inverse_distance is not None else "not_available",
                },
            }
            sources.append(Source(
                # Query-local, collision-free presentation index only. Never
                # persist it as Gaia identity; source_key/source_id are strings.
                index=1_000_000_000_000_000 + index,
                name=ids[index], ext=0.0, ext_err=None,
                ra=float(fk5.ra[index].deg), dec=float(fk5.dec[index].deg),
                l=float(galactic.l[index].deg), b=float(galactic.b[index].deg), p_err_95=None,
                catalogue_label="Gaia DR3", catalogue_id="gaia-dr3", original_id=ids[index],
                source_type="gaia", gaia_mag=magnitude, footprint_kind="point",
                notes=notes,
            ))
        return sources
    except (UnicodeDecodeError, csv.Error, ValueError, KeyError, TypeError) as exc:
        raise GaiaQueryError(f"Invalid Gaia response: {exc}") from exc


def _nearest_sources(sources: List[Source], center: SkyCoord, limit: int) -> List[Source]:
    """Return the nearest eligible Gaia sources in deterministic order."""
    center_j2000 = center.transform_to(J2000_FRAME)
    def distance_key(source: Source) -> tuple[float, str]:
        coordinate = SkyCoord(ra=source.ra * u.deg, dec=source.dec * u.deg, frame=J2000_FRAME)
        return (float(coordinate.separation(center_j2000).deg), str(source.original_id))
    return sorted(sources, key=distance_key)[:limit]


def _tls_context() -> ssl.SSLContext:
    tls = ssl.create_default_context()
    # Supplement a gateway-provided CA with the OS public root store without
    # disabling certificate or hostname verification.
    system_ca = ssl.get_default_verify_paths().openssl_cafile
    if system_ca and Path(system_ca).is_file():
        tls.load_verify_locations(cafile=system_ca)
    return tls


def _read_gaia_payload(
    center: SkyCoord, radius_deg: float, limit: int, max_mag: float,
    timeout_seconds: float, boundary_center: SkyCoord | None = None,
    boundary_radius_deg: float | None = None, order_center: SkyCoord | None = None,
) -> bytes:
    params = urlencode({
        "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv",
        "QUERY": _adql(center, radius_deg, limit, max_mag, boundary_center, boundary_radius_deg, order_center),
    })
    request = Request(f"{GAIA_TAP_URL}?{params}", headers={"Accept": "text/csv", "User-Agent": "Skyward/2.1"})
    tls = _tls_context()
    started = time.monotonic()
    with urlopen(request, timeout=timeout_seconds, context=tls) as response:
        chunks, received = [], 0
        while True:
            remaining = timeout_seconds - (time.monotonic() - started)
            if remaining <= 0:
                raise GaiaQueryError("Gaia response exceeded query timeout")
            # urllib's read timeout alone is per read. Reduce it to the
            # remaining operation budget so a slow stream cannot extend it.
            raw = getattr(getattr(response, "fp", None), "raw", None)
            sock = getattr(raw, "_sock", None)
            if sock is not None:
                sock.settimeout(remaining)
            reader = getattr(response, "read1", response.read)
            chunk = reader(min(65536, MAX_RESPONSE_BYTES + 1 - received))
            if not chunk:
                break
            chunks.append(chunk)
            received += len(chunk)
            if received > MAX_RESPONSE_BYTES:
                raise GaiaQueryError("Gaia response exceeded bounded byte limit")
    return b"".join(chunks)


def _async_tap_url(sync_url: str | None = None) -> str:
    """Derive the UWS endpoint from the configured synchronous TAP URL."""
    parsed = urlsplit(GAIA_TAP_URL if sync_url is None else sync_url)
    path = parsed.path.rstrip("/")
    if not path.endswith("/sync"):
        raise GaiaQueryError("Configured Gaia TAP URL must end with /sync")
    return urlunsplit((parsed.scheme, parsed.netloc, path[:-len("sync")] + "async", "", ""))


def _response_bytes(response, deadline: float, received: int = 0) -> bytes:
    """Read one HTTP response without exceeding the shared deadline/cap."""
    chunks: list[bytes] = []
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GaiaQueryError("Gaia async TAP total polling/download budget exhausted")
        raw = getattr(getattr(response, "fp", None), "raw", None)
        sock = getattr(raw, "_sock", None)
        if sock is not None:
            sock.settimeout(remaining)
        reader = getattr(response, "read1", response.read)
        chunk = reader(min(65536, MAX_RESPONSE_BYTES + 1 - received))
        if not chunk:
            break
        chunks.append(chunk)
        received += len(chunk)
        if received > MAX_RESPONSE_BYTES:
            raise GaiaQueryError("Gaia response exceeded bounded byte limit")
    return b"".join(chunks)


def _response_header(response, name: str) -> str | None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    value = headers.get(name) if hasattr(headers, "get") else None
    if not value:
        getheader = getattr(response, "getheader", None)
        value = getheader(name) if getheader is not None else None
    return str(value) if value else None


def _close_response(response) -> None:
    close = getattr(response, "close", None)
    if close is not None:
        close()


def _async_gaia_payload(
    center: SkyCoord, radius_deg: float, limit: int, max_mag: float,
) -> tuple[bytes, dict]:
    """Submit and collect one bounded UWS TAP job."""
    started = time.monotonic()
    deadline = started + ASYNC_TOTAL_BUDGET_SECONDS
    operation_deadline = deadline - ASYNC_CLEANUP_RESERVE_SECONDS
    total_bytes = 0
    attempts = 0
    job_url: str | None = None
    cleanup_attempted = False
    cleanup_error: str | None = None
    detail = {
        "query_strategy": "async_tap",
        "query_strategy_metadata": {
            "mode": "async_tap", "large_query": True,
            "budget_seconds": ASYNC_TOTAL_BUDGET_SECONDS,
            "response_byte_cap": MAX_RESPONSE_BYTES,
        },
        "async_job_url": None,
        "async_poll_attempts": 0,
        "async_cleanup_attempted": False,
        "async_cleanup_error": None,
        "bytes": 0,
        "total_query_budget_seconds": ASYNC_TOTAL_BUDGET_SECONDS,
    }
    try:
        params = urlencode({
            "REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "PHASE": "RUN",
            "QUERY": _adql(center, radius_deg, limit, max_mag),
        }).encode("ascii")
        remaining = operation_deadline - time.monotonic()
        if remaining <= 0:
            raise GaiaQueryError("Gaia async TAP total polling/download budget exhausted")
        submit = Request(
            _async_tap_url(), data=params,
            headers={"Accept": "text/plain", "Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Skyward/2.1"},
            method="POST",
        )
        attempts += 1
        response = urlopen(submit, timeout=remaining, context=_tls_context())
        try:
            location = _response_header(response, "Location")
            geturl = getattr(response, "geturl", None)
            response_url = str(geturl()) if geturl is not None else ""
            body = _response_bytes(response, operation_deadline, total_bytes)
            total_bytes += len(body)
        finally:
            _close_response(response)
        if not location and response_url and response_url.rstrip("/") != _async_tap_url().rstrip("/"):
            location = response_url
        if not location:
            body_location = body.decode("utf-8", "replace").strip()
            if body_location.startswith("http"):
                location = body_location
        if not location:
            raise GaiaQueryError("Gaia async TAP submission returned no job location")
        job_url = urljoin(_async_tap_url() + "/", location)
        detail["async_job_url"] = job_url
        phase_url = urljoin(job_url.rstrip("/") + "/", "phase")

        while True:
            remaining = operation_deadline - time.monotonic()
            if remaining <= 0:
                raise GaiaQueryError("Gaia async TAP total polling/download budget exhausted")
            phase_request = Request(phase_url, headers={"Accept": "text/plain", "User-Agent": "Skyward/2.1"}, method="GET")
            attempts += 1
            phase_response = urlopen(phase_request, timeout=remaining, context=_tls_context())
            try:
                phase_body = _response_bytes(phase_response, operation_deadline, total_bytes)
                total_bytes += len(phase_body)
            finally:
                _close_response(phase_response)
            phase = phase_body.decode("utf-8", "replace").strip().upper()
            phase_token = phase.split()[0].rstrip(":") if phase else ""
            detail["async_poll_attempts"] += 1
            if phase_token == "COMPLETED":
                break
            if phase_token in {"ERROR", "ABORTED", "HELD", "REJECTED", "DESTROYED"}:
                reason = phase_body.decode("utf-8", "replace").strip() or phase_token
                raise GaiaQueryError(f"Gaia async TAP job failed ({phase_token}): {reason}")
            sleep_for = min(ASYNC_POLL_INTERVAL_SECONDS, operation_deadline - time.monotonic())
            if sleep_for <= 0:
                raise GaiaQueryError("Gaia async TAP total polling/download budget exhausted")
            time.sleep(sleep_for)

        result_url = urljoin(job_url.rstrip("/") + "/", "results/result")
        remaining = operation_deadline - time.monotonic()
        if remaining <= 0:
            raise GaiaQueryError("Gaia async TAP total polling/download budget exhausted")
        result_request = Request(result_url, headers={"Accept": "text/csv", "User-Agent": "Skyward/2.1"}, method="GET")
        attempts += 1
        result_response = urlopen(result_request, timeout=remaining, context=_tls_context())
        try:
            result = _response_bytes(result_response, operation_deadline, total_bytes)
            total_bytes += len(result)
        finally:
            _close_response(result_response)
        detail.update({"bytes": total_bytes, "async_attempts": attempts})
        return result, detail
    except (HTTPError, URLError, TimeoutError, OSError, GaiaQueryError) as exc:
        reason = str(_query_error(exc))
        detail.update({"bytes": total_bytes, "async_attempts": attempts, "actual_failure_reason": reason})
        raise GaiaQueryError(reason, metadata=detail) from exc
    finally:
        if job_url and time.monotonic() < deadline:
            cleanup_attempted = True
            detail["async_cleanup_attempted"] = True
            remaining = max(0.001, deadline - time.monotonic())
            cleanup = Request(job_url, headers={"User-Agent": "Skyward/2.1"}, method="DELETE")
            try:
                response = urlopen(cleanup, timeout=remaining, context=_tls_context())
                _close_response(response)
            except (HTTPError, URLError, TimeoutError, OSError, GaiaQueryError) as exc:
                cleanup_error = str(_query_error(exc))
                detail["async_cleanup_error"] = cleanup_error
        detail["async_cleanup_attempted"] = cleanup_attempted
        detail["async_cleanup_error"] = cleanup_error
        detail["bytes"] = total_bytes


def _fallback_centres(center: SkyCoord, radius_deg: float) -> list[SkyCoord]:
    """Return a finite cross-shaped set of bounded fallback query centres."""
    offset = radius_deg / 2.0
    return [
        center,
        *(center.directional_offset_by(angle * u.deg, offset * u.deg) for angle in (0, 90, 180, 270)),
    ]


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, (HTTPError, URLError, TimeoutError)):
        return True
    return isinstance(exc, GaiaQueryError) and "timeout" in str(exc).lower()


def _query_error(exc: BaseException) -> GaiaQueryError:
    if isinstance(exc, GaiaQueryError):
        return exc
    return GaiaQueryError(f"Gaia DR3 online query failed: {exc}")


def query_gaia_stars(
    at_time: datetime, telescope, radius_deg: float = DEFAULT_RADIUS_DEG,
    limit: int = DEFAULT_LIMIT, max_mag: float = DEFAULT_MAX_MAG,
    target_ra_deg: float | None = None, target_dec_deg: float | None = None,
) -> Tuple[List[Source], dict]:
    """Return a bounded Gaia subset; only explicitly large queries use UWS."""
    if not all(math.isfinite(float(value)) for value in (radius_deg, limit, max_mag)):
        raise GaiaQueryError("Gaia query parameters must be finite")
    if not (0.1 <= radius_deg <= MAX_RADIUS_DEG and 1 <= limit <= GAIA_MAX_ROWS and 5 <= max_mag <= 22):
        raise GaiaQueryError(f"Gaia query parameters exceed bounds (radius <= {MAX_RADIUS_DEG}, maximum {GAIA_MAX_ROWS} rows)")
    if (target_ra_deg is None) != (target_dec_deg is None):
        raise GaiaQueryError("Both target coordinates are required")
    if target_ra_deg is not None:
        if not (0 <= target_ra_deg < 360 and -90 <= target_dec_deg <= 90):
            raise GaiaQueryError("Invalid target coordinates")
        center = SkyCoord(ra=target_ra_deg * u.deg, dec=target_dec_deg * u.deg, frame=J2000_FRAME).icrs
    else:
        center = pointing_icrs(at_time, telescope)
    effective_limit = int(limit)
    is_large_query = (
        float(radius_deg) > LARGE_QUERY_RADIUS_DEG
        or effective_limit > LARGE_QUERY_LIMIT
        or float(max_mag) > LARGE_QUERY_MAX_MAG
    )
    query_strategy = "async_tap" if is_large_query else "sync_tap"
    strategy_metadata = {
        "mode": query_strategy, "large_query": is_large_query,
        "large_query_rule": "radius_deg > 1.0 or limit > 10 or max_mag > 10.0",
        "sync_url": GAIA_TAP_URL,
    }
    # Exact query arguments in cache key: nearby but distinct cones are never
    # substituted for one another (important at the cone boundary).
    key = (float(center.ra.deg), float(center.dec.deg), float(radius_deg), effective_limit, float(max_mag))
    now = time.monotonic()
    with _CACHE_LOCK:
        for expired in [k for k, v in _CACHE.items() if now - v[0] >= GAIA_CACHE_TTL_SECONDS]:
            del _CACHE[expired]
        cached = _CACHE.get(key)
        if cached:
            _CACHE.move_to_end(key)
            cached_meta = {
                **cached[2], "cached": True, "cache_hit": True,
                "cache": {"hit": True, "backend": "memory", "ttl_seconds": GAIA_CACHE_TTL_SECONDS},
            }
            return list(cached[1]), cached_meta
    if not _QUERY_SLOTS.acquire(blocking=False):
        raise GaiaQueryError("Gaia query concurrency limit reached; retry later", metadata={
            "query_strategy": query_strategy, "query_strategy_metadata": strategy_metadata,
            "cache": {"hit": False, "backend": "memory"}, "cache_hit": False,
        })

    started = time.monotonic()
    attempts = 0
    total_bytes = 0
    fallback_used = False
    fallback_errors: list[str] = []
    primary_error: str | None = None
    truncated = False
    sources: list[Source] = []
    async_detail: dict = {}
    try:
        if is_large_query:
            attempts += 1
            payload, async_detail = _async_gaia_payload(center, radius_deg, effective_limit + 1, max_mag)
            attempts = int(async_detail.get("async_attempts", attempts))
            total_bytes = int(async_detail.get("bytes", len(payload)))
            parsed = _parse_csv(payload, effective_limit + 1)
            truncated = len(parsed) > effective_limit
            sources = _nearest_sources(parsed, center, effective_limit)
        else:
            attempts += 1
            try:
                payload = _read_gaia_payload(center, radius_deg, effective_limit + 1, max_mag, QUERY_TIMEOUT_SECONDS)
                total_bytes += len(payload)
                parsed = _parse_csv(payload, effective_limit + 1)
                truncated = len(parsed) > effective_limit
                sources = _nearest_sources(parsed, center, effective_limit)
            except (HTTPError, URLError, TimeoutError, OSError, GaiaQueryError) as exc:
                error = _query_error(exc)
                primary_error = str(error)
                if not _should_retry(exc):
                    raise error from exc
                fallback_used = True

            if fallback_used:
                boundary_center_j2000 = center.transform_to(J2000_FRAME)
                subcone_radius = radius_deg / 2.0
                subcone_limit = max(1, math.ceil(effective_limit / FALLBACK_SUBCONE_COUNT))
                deadline = started + TOTAL_QUERY_BUDGET_SECONDS
                collected: list[Source] = []
                for subcone_index, subcone_center in enumerate(_fallback_centres(center, radius_deg), start=1):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        fallback_errors.append("total Gaia query budget exhausted")
                        break
                    attempts += 1
                    timeout = min(FALLBACK_QUERY_TIMEOUT_SECONDS, remaining)
                    try:
                        payload = _read_gaia_payload(
                            subcone_center, subcone_radius, subcone_limit + 1, max_mag, timeout,
                            boundary_center=center, boundary_radius_deg=radius_deg, order_center=center,
                        )
                        total_bytes += len(payload)
                        parsed = _parse_csv(payload, subcone_limit + 1)
                        truncated = truncated or len(parsed) > subcone_limit
                        collected.extend(
                            source for source in parsed[:subcone_limit]
                            if SkyCoord(ra=source.ra * u.deg, dec=source.dec * u.deg, frame=J2000_FRAME).separation(boundary_center_j2000).deg <= radius_deg + 1e-7
                        )
                    except (HTTPError, URLError, TimeoutError, OSError, GaiaQueryError) as exc:
                        fallback_errors.append(f"subcone {subcone_index}: {str(_query_error(exc))}")

                seen_ids: set[str] = set()
                for source in collected:
                    source_id = str(source.original_id)
                    if source_id in seen_ids:
                        continue
                    seen_ids.add(source_id)
                    sources.append(source)
                    if len(sources) >= effective_limit:
                        break
                sources = _nearest_sources(sources, center, effective_limit)
                truncated = True
                if not sources and len(fallback_errors) >= FALLBACK_SUBCONE_COUNT:
                    details = "; ".join(filter(None, [primary_error, *fallback_errors]))
                    raise GaiaQueryError(f"Gaia DR3 online query failed after bounded fallback: {details}")

        for index, source in enumerate(sources):
            sources[index] = replace(source, index=1_000_000_000_000_000 + index)
        query_context = {
            "at_time": _utc(at_time).isoformat().replace("+00:00", "Z"),
            "center_ra_icrs_deg": float(center.ra.deg), "center_dec_icrs_deg": float(center.dec.deg),
            "radius_deg": float(radius_deg), "max_mag": float(max_mag), "row_limit": effective_limit,
            "map_query_boundary": "bounded cone; not an all-sky completeness claim",
            "query_strategy": "timeout_subcones" if fallback_used else query_strategy,
            "fallback_used": fallback_used,
        }
        for source in sources:
            if isinstance(source.notes, dict):
                source.notes["query_context"] = query_context
    except GaiaQueryError as exc:
        async_strategy_meta = async_detail.get("query_strategy_metadata", {})
        existing_strategy_meta = exc.metadata.get("query_strategy_metadata", {})
        async_lifecycle = {
            key: async_detail[key] for key in (
                "async_job_url", "async_poll_attempts", "async_cleanup_attempted", "async_cleanup_error",
            ) if key in async_detail
        }
        exc.metadata.update({
            **async_lifecycle,
            "query_strategy": "timeout_subcones" if fallback_used else query_strategy,
            "query_strategy_metadata": {**strategy_metadata, **async_strategy_meta, **existing_strategy_meta},
            "cache": {"hit": False, "backend": "memory"}, "cache_hit": False,
            "actual_failure_reason": exc.metadata.get("actual_failure_reason", str(exc)), "bytes": total_bytes, "attempts": attempts,
        })
        raise
    finally:
        _QUERY_SLOTS.release()

    warning = (
        "Sources are ordered by angular distance to the target within the requested cone and magnitude cut; at most the nearest N eligible rows are returned. "
        + ("The primary query timed out, so bounded overlapping subcones inside the original cone were used; this result may be incomplete. " if fallback_used else "")
        + "Frame conversion only; Gaia J2016.0 positions are not propagated for proper motion."
    )
    meta = {
        "cached": False, "cache_hit": False, "cache": {"hit": False, "backend": "memory", "ttl_seconds": GAIA_CACHE_TTL_SECONDS},
        "count": len(sources), "zero": not sources, "limit": effective_limit,
        "truncated": truncated, "error": None, "status": "ok" if sources else "zero",
        "bytes": total_bytes, "center_ra_icrs_deg": key[0], "center_dec_icrs_deg": key[1],
        "center_mode": "target" if target_ra_deg is not None else "current_pointing",
        "radius_deg": radius_deg, "max_mag": max_mag, "reference_epoch": "J2016.0",
        "input_frame": "ICRS", "output_frame": "FK5 J2000", "proper_motion_applied": False,
        "query_strategy": "timeout_subcones" if fallback_used else query_strategy,
        "query_strategy_metadata": {**strategy_metadata, **async_detail},
        "async_job_url": async_detail.get("async_job_url"),
        "async_poll_attempts": async_detail.get("async_poll_attempts", 0),
        "async_cleanup_attempted": async_detail.get("async_cleanup_attempted", False),
        "async_cleanup_error": async_detail.get("async_cleanup_error"),
        "query_timeout_seconds": QUERY_TIMEOUT_SECONDS,
        "total_query_budget_seconds": ASYNC_TOTAL_BUDGET_SECONDS if is_large_query else TOTAL_QUERY_BUDGET_SECONDS,
        "attempts": attempts, "fallback_used": fallback_used, "fallback_errors": fallback_errors,
        "fallback_reason": primary_error, "selection": "nearest_by_angular_distance", "ordering": "angular_distance_asc",
        "brightest_n": False, "complete": not truncated and not fallback_used, "incomplete": truncated or fallback_used,
        "warning": warning,
    }
    with _CACHE_LOCK:
        _CACHE[key] = (time.monotonic(), list(sources), meta)
        while len(_CACHE) > MAX_CACHE_ENTRIES:
            _CACHE.popitem(last=False)
    return sources, meta
