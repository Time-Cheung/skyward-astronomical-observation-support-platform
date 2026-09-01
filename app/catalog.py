from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence

import astropy.units as u
from astropy.coordinates import FK5, SkyCoord
from astropy.time import Time

from .config import (
    CATALOG_ACCEPTED_COLUMNS,
    CATALOG_CANONICAL_COLUMNS,
    CATALOG_EXPECTED_ROWS,
    CATALOG_PATH,
    ENRICHMENT_PATH,
)


class CatalogError(ValueError):
    """Raised when a catalogue violates its declared schema."""


@dataclass(frozen=True)
class Source:
    """One fixed J2000 source from a selected request-scoped catalogue."""

    index: int
    name: str
    ext: float
    # Missing uncertainty fields must stay unknown rather than becoming 0.
    ext_err: Optional[float]
    ra: float
    dec: float
    l: float
    b: float
    p_err_95: Optional[float]
    catalogue_label: str = "2LHAASO"

    @property
    def display_name(self) -> str:
        # Negative indexes are deliberately reserved for temporary operator
        # targets. They are not catalogue records and therefore have no prefix.
        if self.index < 0:
            return self.name
        return f"{self.catalogue_label} {self.name}".strip()

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["p_err(95%)"] = payload.pop("p_err_95")
        payload["catalogue"] = payload.pop("catalogue_label")
        payload["display_name"] = self.display_name
        return payload


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _optional_float(row: dict, *keys: str) -> Optional[float]:
    """Read an optional numeric value without turning missing into zero."""
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip() != "":
            return float(value)
    return None


def _galactic_from_fk5(ra_deg: float, dec_deg: float) -> tuple[float, float]:
    """Derive Galactic coordinates from uploaded FK5 J2000 RA/Dec."""
    coordinate = SkyCoord(
        ra=ra_deg * u.deg, dec=dec_deg * u.deg,
        frame=FK5(equinox=Time("J2000")),
    ).galactic
    return float(coordinate.l.deg), float(coordinate.b.deg)


def _validate_sources(
    rows: Sequence[dict], *, label: str, require_canonical_indexes: bool
) -> List[Source]:
    """Validate built-in rows and minimal in-memory upload rows."""
    sources: List[Source] = []
    seen_indexes = set()
    seen_names = set()
    for line_number, row in enumerate(rows, start=2):
        try:
            ra = float(row["ra"])
            dec = float(row["dec"])
            l = _optional_float(row, "l")
            b = _optional_float(row, "b")
            if l is None or b is None:
                l, b = _galactic_from_fk5(ra, dec)
            source = Source(
                index=int(row["index"]), name=str(row["name"]).strip(),
                ext=float(row.get("ext", 0.0) or 0.0),
                ext_err=_optional_float(row, "ext_err"),
                ra=ra, dec=dec, l=l, b=b,
                p_err_95=_optional_float(row, "p_err_95", "p_err(95%)"),
                catalogue_label=label,
            )
        except (TypeError, ValueError, KeyError) as exc:
            raise CatalogError(f"Invalid row at line {line_number}: {exc}") from exc
        values = (source.ext, source.ra, source.dec, source.l, source.b)
        optional_values = (source.ext_err, source.p_err_95)
        if not source.name:
            raise CatalogError(f"Empty source name at line {line_number}")
        if not all(math.isfinite(value) for value in values) or not all(
            value is None or math.isfinite(value) for value in optional_values
        ):
            raise CatalogError(f"Non-finite value at line {line_number}")
        if not (0.0 <= source.ra < 360.0):
            raise CatalogError(f"RA outside [0, 360) at line {line_number}")
        if not (-90.0 <= source.dec <= 90.0):
            raise CatalogError(f"Dec outside [-90, 90] at line {line_number}")
        if source.ext < 0 or any(value is not None and value < 0 for value in optional_values):
            raise CatalogError(f"Negative uncertainty/extension at line {line_number}")
        if source.index in seen_indexes:
            raise CatalogError(f"Duplicate index {source.index}")
        if source.name.casefold() in seen_names:
            raise CatalogError(f"Duplicate source name {source.name}")
        seen_indexes.add(source.index)
        seen_names.add(source.name.casefold())
        sources.append(source)
    if not sources:
        raise CatalogError("Catalogue contains no source rows")
    if require_canonical_indexes:
        expected_indexes = list(range(CATALOG_EXPECTED_ROWS))
        if [source.index for source in sources] != expected_indexes:
            raise CatalogError("Catalogue indexes must be contiguous and ordered 0-189")
    return sources

class Catalog:
    """Reviewed built-in 2LHAASO catalogue with strict provenance checks."""

    identifier = "2lhaaso"
    label = "2LHAASO"

    def __init__(self, path: Path = CATALOG_PATH) -> None:
        self.path = Path(path)
        self.sha256 = self._hash_file()
        self.sources = self._load()
        self._by_index = {source.index: source for source in self.sources}

    def _hash_file(self) -> str:
        if not self.path.is_file():
            raise CatalogError(f"Catalogue not found: {self.path}")
        return _hash_bytes(self.path.read_bytes())

    def _load(self) -> List[Source]:
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = tuple(reader.fieldnames or ())
            if columns not in (CATALOG_CANONICAL_COLUMNS, CATALOG_ACCEPTED_COLUMNS):
                raise CatalogError(
                    f"Unexpected catalogue columns: {columns}; expected one of "
                    f"{CATALOG_CANONICAL_COLUMNS} or {CATALOG_ACCEPTED_COLUMNS}"
                )
            error_column = "p_err(95%)" if "p_err(95%)" in columns else "p_err(95\\%)"
            rows = list(reader)
        if len(rows) != CATALOG_EXPECTED_ROWS:
            raise CatalogError(f"Expected {CATALOG_EXPECTED_ROWS} rows, found {len(rows)}")
        normalised = [{**row, "p_err_95": row[error_column]} for row in rows]
        return _validate_sources(normalised, label=self.label, require_canonical_indexes=True)

    def get(self, index: int) -> Source:
        try:
            return self._by_index[index]
        except KeyError as exc:
            raise KeyError(f"Unknown source index: {index}") from exc

    def search(self, query: str = "", limit: int = 190) -> List[Source]:
        needle = query.strip().casefold()
        matches = (source for source in self.sources if not needle or needle in source.name.casefold() or needle in source.display_name.casefold())
        return list(matches)[: max(0, min(limit, CATALOG_EXPECTED_ROWS))]


@dataclass(frozen=True)
class TemporaryCatalog:
    """A browser upload held only in this process for a short bounded TTL."""

    token: str
    label: str
    sha256: str
    sources: tuple[Source, ...]
    expires_at: float

    def get(self, index: int) -> Source:
        for source in self.sources:
            if source.index == index:
                return source
        raise KeyError(f"Unknown source index: {index}")

    def search(self, query: str = "", limit: int = 1000) -> List[Source]:
        needle = query.strip().casefold()
        return [source for source in self.sources if not needle or needle in source.name.casefold() or needle in source.display_name.casefold()][:limit]


class TemporaryCatalogStore:
    """Process-memory CSV upload store; it never writes user data to disk."""

    MAX_BYTES = 512 * 1024
    MAX_ROWS = 1000
    TTL_SECONDS = 30 * 60

    def __init__(self) -> None:
        self._catalogues: Dict[str, TemporaryCatalog] = {}

    def _purge(self) -> None:
        now = time.monotonic()
        for token in [key for key, value in self._catalogues.items() if value.expires_at <= now]:
            del self._catalogues[token]

    def create_from_csv(self, raw: bytes, filename: str = "uploaded catalogue") -> TemporaryCatalog:
        """Parse an in-memory UTF-8 CSV with name, ra, dec and optional fields."""
        self._purge()
        if not raw:
            raise CatalogError("Uploaded catalogue is empty")
        if len(raw) > self.MAX_BYTES:
            raise CatalogError(f"Uploaded catalogue exceeds {self.MAX_BYTES // 1024} KiB")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise CatalogError("Uploaded catalogue must be UTF-8 CSV") from exc
        reader = csv.DictReader(io.StringIO(text))
        aliases = {"ra_deg": "ra", "dec_deg": "dec", "extension_deg": "ext", "source_name": "name"}
        rows = []
        for row in reader:
            rows.append({aliases.get(str(key).strip().casefold(), str(key).strip().casefold()): value for key, value in row.items()})
        if not rows or not {"name", "ra", "dec"}.issubset(rows[0]):
            raise CatalogError("CSV must contain name, ra and dec columns (degrees, J2000)")
        if len(rows) > self.MAX_ROWS:
            raise CatalogError(f"Uploaded catalogue exceeds {self.MAX_ROWS} source rows")
        for index, row in enumerate(rows):
            row["index"] = index
        label = Path(filename or "Uploaded catalogue").stem.strip()[:48] or "Uploaded catalogue"
        sources = tuple(_validate_sources(rows, label=label, require_canonical_indexes=False))
        temporary = TemporaryCatalog(
            token=secrets.token_urlsafe(18), label=label, sha256=_hash_bytes(raw),
            sources=sources, expires_at=time.monotonic() + self.TTL_SECONDS,
        )
        self._catalogues[temporary.token] = temporary
        return temporary

    def get(self, token: str) -> TemporaryCatalog:
        self._purge()
        try:
            return self._catalogues[token]
        except KeyError as exc:
            raise KeyError("Uploaded catalogue is unavailable or has expired; upload it again") from exc


class EnrichmentStore:
    def __init__(self, path: Path = ENRICHMENT_PATH) -> None:
        self.path = Path(path)
        self.schema_version = 1
        self._sources: Dict[str, dict] = {}
        self.load_error: Optional[str] = None
        self._load()

    def _load(self) -> None:
        if not self.path.is_file():
            self.load_error = f"Enrichment file not found: {self.path}"
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.schema_version = int(payload.get("schema_version", 1))
            sources = payload.get("sources", {})
            if not isinstance(sources, dict):
                raise ValueError("sources must be an object keyed by catalogue index")
            self._sources = sources
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.load_error = str(exc)
            self._sources = {}

    def get(self, index: int) -> dict:
        base = {"spectral_model": None, "spatial_model": None, "distance": None, "associated_sources": [], "tevcat_name": None, "tevcat_url": None, "provenance": [], "retrieved_at": None, "verification_status": "unverified"}
        stored = self._sources.get(str(index), {})
        if isinstance(stored, dict):
            base.update(stored)
        return base


catalog = Catalog()
temporary_catalogues = TemporaryCatalogStore()
enrichment_store = EnrichmentStore()
