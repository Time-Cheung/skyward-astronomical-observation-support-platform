from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import secrets
import time
import unicodedata
from dataclasses import asdict, dataclass, replace
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


POINT_SOURCE_FALLBACK_WARNING = "point_source_fallback"


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
    catalogue_label: str = "1LHAASO"
    source_type: str = "catalogue"
    gaia_mag: Optional[float] = None
    catalogue_id: str = "1lhaaso"
    original_id: str = ""
    original_row: Optional[int] = None
    footprint_known: bool = True
    footprint_kind: str = "catalogue_radius"
    notes: Optional[dict] = None
    planner_constraints: Optional[dict] = None

    @property
    def planning_radius_deg(self) -> Optional[float]:
        return self.ext if self.footprint_known else None

    @property
    def evaluation_radius_deg(self) -> float:
        """Radius used for geometry when the catalogue footprint is unknown."""
        return self.ext if self.footprint_known else 0.0

    @property
    def point_source_fallback(self) -> bool:
        return not self.footprint_known

    @property
    def display_name(self) -> str:
        # Negative indexes are deliberately reserved for temporary operator
        # targets. They are not catalogue records and therefore have no prefix.
        if self.index < 0:
            return self.name
        label = self.catalogue_label
        name = self.name.strip()
        # Fermi catalogue rows already carry their survey prefix. Keep the
        # display label concise without changing raw names or source identity.
        if self.catalogue_id == "fermi-3fhl":
            label = "3FHL"
            for prefix in ("Fermi 3FHL ", "3FHL "):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break
        elif self.catalogue_id == "fermi-fl16y":
            label = "FL16Y"
            for prefix in ("Fermi FL16Y ", "FL16Y "):
                if name.startswith(prefix):
                    name = name[len(prefix):]
                    break
        return f"{label} {name}".strip()

    def to_dict(self, include_notes: bool = False) -> dict:
        # Avoid recursively copying thousands of bibliography/raw-field blocks
        # into every sky marker and paginated selection response.
        payload = {key: value for key, value in self.__dict__.items() if key != "notes"}
        if include_notes:
            payload["notes"] = self.notes
        payload["p_err(95%)"] = payload.pop("p_err_95")
        payload["catalogue"] = payload.pop("catalogue_label")
        payload["display_name"] = self.display_name
        payload["source_key"] = self.source_key
        payload["original_id"] = self.original_id or self.name
        payload["planning_radius_deg"] = self.planning_radius_deg
        if self.source_type == "gaia":
            payload["source_id"] = self.original_id or self.name
        payload["ext"] = self.planning_radius_deg
        if self.point_source_fallback:
            payload["warnings"] = [POINT_SOURCE_FALLBACK_WARNING]
        return payload

    @property
    def source_key(self) -> str:
        return f"{self.catalogue_id}:{self.original_id or self.name}"

    @property
    def is_calibration_star(self) -> bool:
        return self.source_type == "gaia"


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
    rows: Sequence[dict], *, label: str, require_canonical_indexes: bool,
    source_type: str = "catalogue",
) -> List[Source]:
    """Validate built-in rows and minimal in-memory upload rows."""
    sources: List[Source] = []
    seen_indexes = set()
    seen_names = set()
    seen_ids = set()
    for line_number, row in enumerate(rows, start=2):
        try:
            ra = float(row["ra"])
            dec = float(row["dec"])
            l = _optional_float(row, "l")
            b = _optional_float(row, "b")
            if l is None or b is None:
                l, b = _galactic_from_fk5(ra, dec)
            planner_constraints = {
                key: value for key in (
                    "sun_max_altitude_deg", "moon_min_separation_deg", "target_min_zenith_deg",
                    "target_max_zenith_deg", "minimum_window_seconds",
                ) if (value := _optional_float(row, key)) is not None
            }
            source = Source(
                index=int(row["index"]), name=str(row["name"]).strip(),
                ext=float(row.get("ext", 0.0) or 0.0),
                ext_err=_optional_float(row, "ext_err"),
                ra=ra, dec=dec, l=l, b=b,
                p_err_95=_optional_float(row, "p_err_95", "p_err(95%)"),
                catalogue_label=label,
                source_type=source_type,
                original_id=str(row.get("original_id", row["name"])).strip(),
                original_row=int(row["index"]),
                planner_constraints=planner_constraints or None,
            )
        except (TypeError, ValueError, KeyError) as exc:
            raise CatalogError(f"Invalid row at line {line_number}: {exc}") from exc
        values = (source.ext, source.ra, source.dec, source.l, source.b)
        optional_values = (source.ext_err, source.p_err_95)
        if not source.name:
            raise CatalogError(f"Empty source name at line {line_number}")
        # Upload names/IDs must fit every planner/detail/query identity field.
        # Unicode and URL-reserved punctuation are valid; controls are not.
        if len(source.name) > 80 or not 1 <= len(source.original_id) <= 80:
            raise CatalogError(f"Source name and original_id must contain 1-80 characters at line {line_number}")
        if any(ord(char) < 32 or ord(char) == 127 for char in source.name + source.original_id):
            raise CatalogError(f"Control characters in source identity at line {line_number}")
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
        if source.original_id in seen_ids:
            raise CatalogError(f"Duplicate original_id {source.original_id}")
        seen_ids.add(source.original_id)
        seen_indexes.add(source.index)
        seen_names.add(source.name.casefold())
        sources.append(source)
    if not sources:
        raise CatalogError("Catalogue contains no source rows")
    if require_canonical_indexes:
        expected_indexes = list(range(CATALOG_EXPECTED_ROWS))
        if [source.index for source in sources] != expected_indexes:
            raise CatalogError(f"Catalogue indexes must be contiguous and ordered 0-{CATALOG_EXPECTED_ROWS - 1}")
    return sources

class CatalogCollection:
    """A request-scoped view preserving globally stable source identities."""

    def __init__(self, catalogues: Sequence[object]) -> None:
        self.catalogues = tuple(catalogues)
        rows: List[Source] = []
        seen = set()
        for catalogue in self.catalogues:
            for source in catalogue.sources:
                if source.source_key not in seen:
                    rows.append(source)
                    seen.add(source.source_key)
        self.sources = rows
        self._by_key = {source.source_key: source for source in rows}
        self._by_index = {source.index: source for source in rows}
        self.label = " + ".join(getattr(item, "label", "Catalogue") for item in self.catalogues)
        self.identifier = ",".join(getattr(item, "identifier", getattr(item, "token", "upload")) for item in self.catalogues)
        self.sha256 = _hash_bytes("|".join(getattr(item, "sha256", "") for item in self.catalogues).encode("utf-8"))
        self.provenance = getattr(self.catalogues[0], "provenance", {}) if len(self.catalogues) == 1 else {}
        self.display = getattr(self.catalogues[0], "display", {}) if len(self.catalogues) == 1 else {}

    def get(self, index: int | str) -> Source:
        try:
            return self._by_key[index] if isinstance(index, str) and ":" in index else self._by_index[int(index)]
        except (KeyError, ValueError) as exc:
            raise KeyError(f"Unknown source identity: {index}") from exc

    def search(self, query: str = "", limit: Optional[int] = None, offset: int = 0) -> List[Source]:
        needle = query.strip().casefold()
        matches = [source for source in self.sources if not needle or needle in source.name.casefold() or needle in source.display_name.casefold() or needle in source.source_key.casefold()]
        matches.sort(key=lambda source: (source.name.casefold(), source.catalogue_label.casefold(), source.index))
        return matches[offset:] if limit is None else matches[offset:offset + max(0, limit)]


class Catalog:
    """Legacy CSV catalogue loader retained for operator-supplied compatibility."""

    identifier = "legacy-csv"
    label = "Legacy CSV"

    def __init__(self, path: Path) -> None:
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
        matches = [source for source in self.sources if not needle or needle in source.name.casefold() or needle in source.display_name.casefold()]
        matches.sort(key=lambda source: (source.name.casefold(), source.index))
        return matches[: max(0, min(limit, CATALOG_EXPECTED_ROWS))]


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
        matches = [source for source in self.sources if not needle or needle in source.name.casefold() or needle in source.display_name.casefold()]
        matches.sort(key=lambda source: (source.name.casefold(), source.index))
        return matches[:limit]


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

    @staticmethod
    def _label(value: object) -> str:
        label = str(value or "Uploaded catalogue").strip()[:48] or "Uploaded catalogue"
        normalized = "".join(
            character for character in unicodedata.normalize("NFKC", label).casefold()
            if character.isalnum()
        )
        if normalized.startswith("2lhaaso"):
            raise CatalogError("Uploaded catalogue labels must not use the reserved unpublished 2LHAASO name")
        return label

    def create_from_rows(
        self, rows: Sequence[dict], label: str, source_type: str = "catalogue",
        raw: Optional[bytes] = None,
    ) -> TemporaryCatalog:
        self._purge()
        if not rows:
            raise CatalogError("Catalogue contains no source rows")
        if len(rows) > self.MAX_ROWS:
            raise CatalogError(f"Uploaded catalogue exceeds {self.MAX_ROWS} source rows")
        normalised = [dict(row) for row in rows]
        for index, row in enumerate(normalised):
            row.setdefault("index", index)
        safe_label = self._label(label)
        sources = tuple(_validate_sources(
            normalised, label=safe_label, require_canonical_indexes=False, source_type=source_type
        ))
        digest = _hash_bytes(raw) if raw is not None else _hash_bytes(
            json.dumps(normalised, sort_keys=True, ensure_ascii=False).encode("utf-8")
        )
        temporary = TemporaryCatalog(
            token=secrets.token_urlsafe(18), label=safe_label, sha256=digest,
            sources=sources, expires_at=time.monotonic() + self.TTL_SECONDS,
        )
        temporary = self._identify(temporary)
        self._catalogues[temporary.token] = temporary
        return temporary

    def create_from_csv(self, raw: bytes, filename: str = "uploaded catalogue", *, require_extension: bool = False) -> TemporaryCatalog:
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
        if require_extension and any(str(row.get("ext", "")).strip() == "" for row in rows):
            raise CatalogError("Target-list CSV must provide ext/extension_deg for every row")
        if len(rows) > self.MAX_ROWS:
            raise CatalogError(f"Uploaded catalogue exceeds {self.MAX_ROWS} source rows")
        for index, row in enumerate(rows):
            row["index"] = index
        label = self._label(Path(filename or "Uploaded catalogue").stem)
        sources = tuple(_validate_sources(rows, label=label, require_canonical_indexes=False))
        temporary = TemporaryCatalog(
            token=secrets.token_urlsafe(18), label=label, sha256=_hash_bytes(raw),
            sources=sources, expires_at=time.monotonic() + self.TTL_SECONDS,
        )
        temporary = self._identify(temporary)
        self._catalogues[temporary.token] = temporary
        return temporary

    def _identify(self, temporary: TemporaryCatalog) -> TemporaryCatalog:
        # Stay inside JavaScript's exact integer range; token identity survives
        # any display-table selection or ordering within this upload lifetime.
        base = 1_000_000 + int(hashlib.sha256(temporary.token.encode()).hexdigest()[:9], 16) * 1024
        return replace(temporary, sources=tuple(
            replace(source, index=base + row, catalogue_id=temporary.token)
            for row, source in enumerate(temporary.sources)
        ))

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


class JSONCatalog:
    """Reviewed normalized table, preserving original identity and notes."""

    def __init__(self, path: Path, identifier: str, offset: int, expected: int | None):
        raw = path.read_bytes()
        payload = json.loads(raw)
        if payload.get("schema_version") not in (1, 2) or payload.get("catalogue_id") != identifier:
            raise CatalogError(f"Invalid catalogue envelope: {path}")
        self.identifier, self.label = identifier, payload["label"]
        self.display = payload.get("display", {}) if isinstance(payload.get("display", {}), dict) else {}
        self.sha256, self.provenance = _hash_bytes(raw), payload.get("provenance", {})
        rows = payload["sources"]
        if expected is not None and len(rows) != expected:
            raise CatalogError(f"Expected {expected} {identifier} rows, found {len(rows)}")
        self.sources = []
        seen = set()
        for ordinal, row in enumerate(rows):
            original_id = str(row["original_id"]).strip()
            if not original_id or original_id in seen:
                raise CatalogError(f"Empty or duplicated original ID: {original_id}")
            seen.add(original_id)
            ra, dec = float(row["ra_deg"]), float(row["dec_deg"])
            if not math.isfinite(ra) or not math.isfinite(dec) or not (0 <= ra < 360 and -90 <= dec <= 90):
                raise CatalogError(f"Invalid coordinates: {original_id}")
            radius = row.get("planning_radius_deg")
            known = bool(row.get("footprint_known", False)) and radius is not None
            if radius is not None and (not math.isfinite(float(radius)) or not 0 <= float(radius) <= 90):
                raise CatalogError(f"Invalid planning radius: {original_id}")
            l, b = row.get("l_deg"), row.get("b_deg")
            if l is None or b is None:
                l, b = _galactic_from_fk5(ra, dec)
            self.sources.append(Source(
                offset + ordinal, row["name"], float(radius) if known else 0.0,
                None, ra, dec, float(l), float(b), row.get("p_err_95"),
                catalogue_label=self.label, catalogue_id=identifier,
                original_id=original_id, original_row=int(row.get("original_row", ordinal)),
                footprint_known=known, footprint_kind=row.get("footprint_kind", "unknown"),
                notes=row.get("notes", {}),
            ))
        self._collection = CatalogCollection([self])

    def get(self, identity):
        return self._collection.get(identity)

    def search(self, query: str = "", limit: Optional[int] = None, offset: int = 0) -> List[Source]:
        return self._collection.search(query, limit, offset)


BUILTIN_CATALOGUES = {
    "fermi-fl16y": ("Fermi FL16Y", 10_000, 7224),
    "fermi-3fhl": ("Fermi 3FHL", 30_000, 1556),
    "tevcat": ("TeVCat", 40_000, None),
}
_BUILTIN_CACHE = {}


def installed_catalogue(identifier: str):
    if identifier == "1lhaaso":
        return catalog
    if identifier not in BUILTIN_CATALOGUES:
        raise KeyError(identifier)
    path = CATALOG_PATH.parent / f"{identifier}.json"
    if not path.is_file():
        raise CatalogError(f"Catalogue not installed: {identifier}")
    stamp = path.stat().st_mtime_ns
    cached = _BUILTIN_CACHE.get(identifier)
    if cached and cached[0] == stamp:
        return cached[1]
    _, offset, expected = BUILTIN_CATALOGUES[identifier]
    loaded = JSONCatalog(path, identifier, offset, expected)
    _BUILTIN_CACHE[identifier] = (stamp, loaded)
    return loaded


def resolve_source(identity: int | str) -> Source:
    """Resolve a target independently of the current display-layer selection."""
    if isinstance(identity, str) and ":" in identity:
        identifier, _ = identity.split(":", 1)
        table = installed_catalogue(identifier) if identifier in {"1lhaaso", *BUILTIN_CATALOGUES} else temporary_catalogues.get(identifier)
        return CatalogCollection([table]).get(identity)
    index = int(identity)
    if 0 <= index < CATALOG_EXPECTED_ROWS:
        return catalog.get(index)
    for identifier, (_, offset, count) in BUILTIN_CATALOGUES.items():
        if count is not None and offset <= index < offset + count:
            return installed_catalogue(identifier).get(index)
    temporary_catalogues._purge()
    for table in list(temporary_catalogues._catalogues.values()):
        try:
            return table.get(index)
        except KeyError:
            pass
    raise KeyError(f"Unknown source identity: {identity}")


catalog = JSONCatalog(CATALOG_PATH, "1lhaaso", 0, CATALOG_EXPECTED_ROWS)
temporary_catalogues = TemporaryCatalogStore()
enrichment_store = EnrichmentStore()
