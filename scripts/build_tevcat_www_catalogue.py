#!/usr/bin/env python3
"""Build a minimal, auditable TeVCat catalogue from a public www snapshot."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
from collections import Counter
from pathlib import Path

from astropy import __version__ as astropy_version
from astropy import units as u
from astropy.coordinates import FK5, SkyCoord
from astropy.time import Time

FRAME = FK5(equinox=Time("J2000"))
CATALOGUE_ID = "tevcat"
DISPLAY_LABEL = "TeVCat"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def text(value) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def coordinate(row: dict) -> tuple[float, float, float, float]:
    ra, dec = text(row.get("coord_ra")), text(row.get("coord_dec"))
    if not ra or not dec:
        raise ValueError(f"source {row.get('id')} has no RA/Dec")
    source = SkyCoord(ra, dec, unit=(u.hourangle, u.deg), frame=FRAME)
    if not (math.isfinite(source.ra.deg) and math.isfinite(source.dec.deg)):
        raise ValueError(f"source {row.get('id')} has invalid RA/Dec")
    galactic = source.galactic
    return float(source.ra.deg), float(source.dec.deg), float(galactic.l.deg), float(galactic.b.deg)


def state(value):
    return {"value": value, "state": "reported" if value not in (None, "") else "missing"}


def source_note(row: dict, groups: dict, source_url: str) -> dict:
    aliases = text(row.get("other_names"))
    if aliases:
        aliases = re.sub(r"<[^>]+>", " ", aliases)
    note = text(row.get("notes"))
    note_summary = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", note or ""))).strip()
    if len(note_summary) > 480:
        note_summary = note_summary[:477].rstrip() + "..."
    return {
        "catalogue_group": text((groups.get(str(row.get("catalog_id"))) or {}).get("name")),
        "catalogue_group_description": text((groups.get(str(row.get("catalog_id"))) or {}).get("description")),
        "catalogue_source_id": str(row["id"]),
        "canonical_name": text(row.get("canonical_name")),
        "catalogue_name": text(row.get("catalog_name")),
        "aliases": [item.strip() for item in (aliases or "").replace(";", ",").split(",") if item.strip()],
        "classification": {"source_type": state(row.get("source_type")), "source_type_name": state(text(row.get("source_type_name")))},
        "coordinates": {"input_ra": text(row.get("coord_ra")), "input_dec": text(row.get("coord_dec")), "input_type": text(row.get("coord_type")), "frame": "FK5", "equinox": "J2000"},
        "discovery": {"date": state(text(row.get("discovery_date"))), "discoverer_id": state(row.get("discoverer")), "observatory": state(text(row.get("observatory_name")))},
        "physical_fields": {
            "reported_extent": state(row.get("ext")),
            "reported_size_x": state(row.get("size_x")),
            "reported_size_y": state(row.get("size_y")),
            "reported_flux": state(row.get("flux")),
            "energy_threshold": state(row.get("eth")),
            "spectral_index": state(row.get("spec_idx")),
            "distance_or_redshift": state(row.get("distance")),
            "distance_mode": state(text(row.get("distance_mod"))),
            "variability": state(text(row.get("variability"))),
        },
        "public_notes": {"available": bool(note), "summary": note_summary or None, "sha256": hashlib.sha256((note or "").encode("utf-8")).hexdigest() if note else None, "rendering": "short sanitized public summary; raw HTML not redistributed"},
        "source_url": source_url,
        "normalization_notes": [
            "Public www.tevcat.org record normalized from embedded data.",
            "Raw public notes HTML is not redistributed; only availability and digest are retained.",
            ("The upstream Extended: No flag is normalized as a zero-radius point source for planning."
             if row.get("ext") in (0, "0", False) else
             "The upstream Extended: Yes flag does not define a verified angular hard boundary; planning footprint remains unknown."),
        ],
    }


def build(staging: Path) -> dict:
    manifest = load(staging / "manifest.json")
    public = load(staging / "public-sources.json")
    if not manifest.get("complete") or manifest.get("source_url") != "https://www.tevcat.org/":
        raise ValueError("staging is not a complete public www TeVCat snapshot")
    groups, rows = public.get("catalogs"), public.get("sources")
    if not isinstance(groups, dict) or not isinstance(rows, list) or len(rows) != manifest.get("source_count"):
        raise ValueError("staging manifest and public payload disagree")
    sources, seen = [], set()
    for ordinal, row in enumerate(rows):
        if not isinstance(row, dict) or row.get("public") != 1:
            raise ValueError("non-public row supplied to normalizer")
        identifier = str(row.get("id"))
        if not identifier.isdecimal() or identifier in seen:
            raise ValueError("invalid or duplicate TeVCat source id")
        seen.add(identifier)
        ra, dec, l, b = coordinate(row)
        name = text(row.get("canonical_name"))
        if not name:
            raise ValueError(f"source {identifier} has no canonical name")
        source_url = f"https://www.tevcat.org/?id={identifier}"
        is_point_source = row.get("ext") in (0, "0", False)
        sources.append({
            "original_id": identifier, "original_row": ordinal, "name": name,
            "ra_deg": ra, "dec_deg": dec, "l_deg": l, "b_deg": b,
            "planning_radius_deg": 0.0 if is_point_source else None,
            "footprint_known": is_point_source,
            "footprint_kind": "point_source" if is_point_source else "unknown_hard_boundary",
            "notes": source_note(row, groups, source_url),
        })
    group_counts = Counter(str(row["catalog_id"]) for row in rows)
    if dict(sorted(group_counts.items())) != manifest.get("catalogue_group_counts"):
        raise ValueError("catalogue group count mismatch")
    return {
        "schema_version": 2,
        "catalogue_id": CATALOGUE_ID,
        "label": DISPLAY_LABEL,
        "display": {"zh": f"TeVCat（截止到{manifest['snapshot_date_shanghai'].replace('-', '年', 1).replace('-', '月', 1)}日）", "en": f"TeVCat (as of {manifest['snapshot_date_shanghai']})"},
        "units": {"ra_deg": "deg", "dec_deg": "deg", "l_deg": "deg", "b_deg": "deg", "planning_radius_deg": "deg"},
        "provenance": {
            "catalogue_url": manifest["source_url"], "snapshot_date": manifest["snapshot_date_shanghai"],
            "retrieved_at_start": manifest["retrieved_at_start"], "retrieved_at_finish": manifest["retrieved_at_finish"],
            "source_count": len(sources), "catalogue_group_counts": dict(sorted(group_counts.items())),
            "source_ids_sha256": manifest["source_ids_sha256"], "public_payload_sha256": manifest["public_payload_sha256"],
            "response_sha256": manifest["response_sha256"], "final_response_sha256": manifest["final_response_sha256"],
            "public_field_policy": "Private and operator-only fields are excluded before normalization.", "astropy_version": astropy_version,
            "redistribution_policy": "Normalized public structured fields only; raw notes HTML and private fields are excluded.",
            "measurement_policy": "Extended: No is interpreted as a point source with zero planning radius; Extended: Yes remains an unknown hard boundary unless a verified angular size is available. Other website fields are catalogue facts, not independently verified measurements.",
        },
        "sources": sources,
    }


def association_audit(catalogue: dict, lhaaso_path: Path) -> dict:
    target_payload = load(lhaaso_path)
    if target_payload.get("catalogue_id") != "1lhaaso":
        raise ValueError("association target must be the public 1LHAASO normalization")
    targets = target_payload["sources"]
    target_coords = SkyCoord([float(row["ra_deg"]) for row in targets] * u.deg, [float(row["dec_deg"]) for row in targets] * u.deg, frame=FRAME)
    candidates = []
    for source in catalogue["sources"]:
        coord = SkyCoord(source["ra_deg"] * u.deg, source["dec_deg"] * u.deg, frame=FRAME)
        for index, separation in enumerate(coord.separation(target_coords).deg):
            if separation <= 0.5:
                target = targets[index]
                candidates.append({"tevcat_id": source["original_id"], "lhaaso_original_id": target["original_id"], "lhaaso_name": target["name"], "separation_deg": float(separation), "status": "candidate_only", "evidence": [], "reason": "position_nearby_is_not_identity_evidence"})
    return {"schema_version": 2, "catalogue_id": CATALOGUE_ID, "target_catalogue_id": "1lhaaso", "verified_associations": [], "candidates": candidates, "provenance": {"target_sha256": sha256(lhaaso_path), "candidate_radius_deg": 0.5, "method": "all pairs within fixed angular separation; no one-to-one assignment", "policy": "Position proximity alone is not source identity evidence. Public 1LHAASO Table 2 coordinates are the target catalogue; no unpublished 2LHAASO data are used."}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", required=True, type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/catalogues"))
    parser.add_argument("--lhaaso", type=Path, default=Path("data/catalogues/1lhaaso.json"))
    args = parser.parse_args()
    catalogue = build(args.staging)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "tevcat.json").write_text(json.dumps(catalogue, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    associations = association_audit(catalogue, args.lhaaso)
    (args.output_dir / "tevcat-associations.json").write_text(json.dumps(associations, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(catalogue["sources"]), "groups": catalogue["provenance"]["catalogue_group_counts"], "candidates": len(associations["candidates"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
