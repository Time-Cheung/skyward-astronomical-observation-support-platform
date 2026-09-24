#!/usr/bin/env python3
"""Build the public normalized 1LHAASO catalogue from Table 2 data.

The input is a CSV mirror of the published Table 2 machine-readable table.
The output keeps one stable source row per published 1LHAASO name and preserves
all WCDA/KM2A component measurements in notes.  The Table 2 r39 values are
39% containment radii of fitted two-dimensional Gaussians, not a verified hard
planning footprint, so the normalized rows intentionally use an unknown
footprint and never turn r39 into a geometry radius.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import OrderedDict
from pathlib import Path

from astropy import __version__ as astropy_version
from astropy import units as u
from astropy.coordinates import FK5, SkyCoord
from astropy.time import Time

CATALOGUE_ID = "1lhaaso"
LABEL = "1LHAASO"
PAPER_DOI = "10.3847/1538-4355/acfd29"
PAPER_HASH = "4b41467c795de459c9484b51d8a4c157350dcac8d4106508297043fdda1f9c21"
TABLE_URL = "https://casdc.china-vo.org/archive/LHAASO-Gamma-Ray-sources/table.csv"
PUBLISHED_COLUMNS = (
    "Source name", "components", "Ra", "Dec", "positional error", "r39",
    "r39 error", "TS", "N0", "N0 error", "index", "index error", "TS100",
    "Assoc.(Sep.)",
)
FRAME = FK5(equinox=Time("J2000"))


def clean(value: object) -> str:
    return str(value or "").strip()


def optional_float(value: object) -> float | None:
    text = clean(value)
    if not text:
        return None
    return float(text)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measurement(value: object, error: object) -> dict:
    """Preserve zero-coded upper limits without treating them as measurements."""
    raw_value, raw_error = clean(value), clean(error)
    numeric = optional_float(raw_value)
    uncertainty = optional_float(raw_error)
    if numeric == 0.0 and uncertainty is not None:
        return {
            "value": None,
            "error": None,
            "upper_limit": uncertainty,
            "kind": "upper_limit",
            "raw_value": raw_value,
            "raw_error": raw_error,
        }
    return {
        "value": numeric,
        "error": uncertainty,
        "upper_limit": None,
        "kind": "measurement" if numeric is not None else "missing",
        "raw_value": raw_value or None,
        "raw_error": raw_error or None,
    }


def plain_measurement(value: object, error: object) -> dict:
    """Handle fields whose machine table uses blank, not zero, for absence."""
    raw_value, raw_error = clean(value), clean(error)
    return {
        "value": optional_float(value),
        "error": optional_float(error),
        "raw_value": raw_value or None,
        "raw_error": raw_error or None,
    }


def component(row: dict, ordinal: int) -> dict:
    name = clean(row["Source name"])
    component_name = clean(row["components"])
    ra, dec = optional_float(row["Ra"]), optional_float(row["Dec"])
    r39 = measurement(row["r39"], row["r39 error"])
    n0 = measurement(row["N0"], row["N0 error"])
    spectral_index = plain_measurement(row["index"], row["index error"])
    return {
        "row_number": ordinal,
        "component": component_name or None,
        "ra_deg": ra,
        "dec_deg": dec,
        "positional_error_deg": optional_float(row["positional error"]),
        "r39_deg": r39["value"],
        "r39_error_deg": r39["error"],
        "r39_upper_limit_deg": r39["upper_limit"],
        "r39_kind": r39["kind"],
        "r39_statistical_interpretation": (
            "95_percent_confidence_upper_limit" if r39["kind"] == "upper_limit"
            else "1_sigma_statistical_uncertainty" if r39["value"] is not None and r39["error"] is not None
            else None
        ),
        "ts": optional_float(row["TS"]),
        "n0_value": n0["value"],
        "n0_error": n0["error"],
        "n0_upper_limit": n0["upper_limit"],
        "n0_kind": n0["kind"],
        "n0_units": (
            "10^-13 cm^-2 s^-1 TeV^-1" if component_name.startswith("WCDA")
            else "10^-16 cm^-2 s^-1 TeV^-1" if component_name.startswith("KM2A")
            else None
        ),
        "reference_energy_tev": 3 if component_name.startswith("WCDA") else 50 if component_name.startswith("KM2A") else None,
        "photon_index": spectral_index["value"],
        "photon_index_error": spectral_index["error"],
        "photon_index_raw_value": spectral_index["raw_value"],
        "photon_index_raw_error": spectral_index["raw_error"],
        "ts100": optional_float(row["TS100"]),
        "association": clean(row["Assoc.(Sep.)"]) or None,
        "association_scope": (
            "preliminary_positional_counterpart_from_table2"
            if clean(row["Assoc.(Sep.)"]) else None
        ),
        "raw_fields": {key: clean(row[key]) or None for key in PUBLISHED_COLUMNS},
    }


def build(table: Path) -> dict:
    if sha256(table) != "ab90608c6e74a58a2f10a9edac1e691d3b88f0bb7ae17b44830aa4fb754299a8":
        raise ValueError("input table hash does not match the audited public Table 2 mirror")
    with table.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = tuple(clean(field) for field in (reader.fieldnames or ()))
        if fields != PUBLISHED_COLUMNS:
            raise ValueError(f"unexpected machine-table columns: {fields}")
        grouped: OrderedDict[str, list[dict]] = OrderedDict()
        for ordinal, raw in enumerate(reader, start=2):
            row = {clean(key): clean(value) for key, value in raw.items()}
            grouped.setdefault(clean(row["Source name"]), []).append(component(row, ordinal))
    if len(grouped) != 90 or sum(len(rows) for rows in grouped.values()) != 180:
        raise ValueError("Table 2 mirror must contain exactly 90 sources and 180 component rows")
    sources = []
    for ordinal, (published_name, components) in enumerate(grouped.items()):
        with_coordinates = [row for row in components if row["ra_deg"] is not None and row["dec_deg"] is not None]
        if not with_coordinates:
            raise ValueError(f"no coordinate component for {published_name}")
        representative = max(
            with_coordinates,
            key=lambda row: (row["ts"] is not None, row["ts"] if row["ts"] is not None else -math.inf),
        )
        ra, dec = representative["ra_deg"], representative["dec_deg"]
        skycoord = SkyCoord(ra * u.deg, dec * u.deg, frame=FRAME).galactic
        source_name = re.sub(r"^1LHAASO\s+", "", published_name)
        source_id = source_name
        sources.append({
            "original_id": source_id,
            "original_row": ordinal,
            "name": source_name,
            "ra_deg": ra,
            "dec_deg": dec,
            "l_deg": float(skycoord.l.deg),
            "b_deg": float(skycoord.b.deg),
            "p_err_95": representative["positional_error_deg"],
            "planning_radius_deg": None,
            "footprint_known": False,
            "footprint_kind": "unknown_table2_gaussian_containment",
            "notes": {
                "published_name": published_name,
                "representative_component": representative["component"],
                "representative_rule": "component with the highest TS among components with published coordinates",
                "components": components,
                "scientific_boundary": (
                    "Table 2 r39 is a 39% containment radius of a fitted 2D Gaussian; "
                    "measured-extension errors are 1-sigma statistical uncertainties and pointlike-source "
                    "upper limits are at 95% confidence. It is retained as provenance and is not used as "
                    "a hard planning footprint. Table 2 associations are preliminary positional counterparts, "
                    "not Skyward-verified source identities."
                ),
            },
        })
    return {
        "schema_version": 2,
        "catalogue_id": CATALOGUE_ID,
        "label": LABEL,
        "display": {
            "zh": "1LHAASO（论文 Table 2）",
            "en": "1LHAASO (paper Table 2)",
        },
        "units": {
            "ra_deg": "deg", "dec_deg": "deg", "l_deg": "deg", "b_deg": "deg",
            "p_err_95": "deg", "r39": "deg",
            "n0_wcda": "10^-13 cm^-2 s^-1 TeV^-1",
            "n0_km2a": "10^-16 cm^-2 s^-1 TeV^-1",
            "reference_energy_wcda": "3 TeV", "reference_energy_km2a": "50 TeV",
        },
        "provenance": {
            "paper_title": "The First LHAASO Catalog of Gamma-Ray Sources",
            "paper_doi": PAPER_DOI,
            "paper_table": "Table 2",
            "paper_sha256": PAPER_HASH,
            "table_url": TABLE_URL,
            "table_sha256": sha256(table),
            "component_rows": 180,
            "source_count": 90,
            "retrieval_note": "Public machine-readable Table 2 mirror audited against the supplied paper. Blank fields remain null.",
            "coordinate_policy": "For sources with two components, use the position of the component with higher TS, following the Table 2 note.",
            "r39_policy": "r39 is a 39% containment radius of a fitted two-dimensional Gaussian. Measured-extension errors are 1-sigma statistical uncertainties; pointlike-source upper limits are at 95% confidence. r39 is not used as a hard planning boundary.",
            "association_policy": "Table 2 association entries are preliminary closest known-TeV counterparts found by a positional search; they are not treated as verified source identities.",
            "n0_policy": "N0 units are detector-specific: WCDA 10^-13 and KM2A 10^-16 cm^-2 s^-1 TeV^-1, with reference energies 3 and 50 TeV. Zero-coded non-detections are stored as upper limits, not scientific zeroes.",
            "redistribution_policy": "Normalized fields derived from the public paper Table 2; no unpublished second-catalogue source file is included.",
            "astropy_version": astropy_version,
        },
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--table", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/catalogues/1lhaaso.json"))
    args = parser.parse_args()
    payload = build(args.table)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(payload["sources"]), "components": payload["provenance"]["component_rows"], "sha256": sha256(args.output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
