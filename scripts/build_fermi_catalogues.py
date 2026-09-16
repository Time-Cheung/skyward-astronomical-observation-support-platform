#!/usr/bin/env python3
"""Complete source-field JSON extraction of supplied FL16Y/v41 and 3FHL/v13.

Run: .venv/bin/python -B scripts/build_fermi_catalogues.py
No downloads, input edits, time-dependent fields, unit conversion, or model fitting.
JSON arrays follow Astropy/FITS TDIM ordering (e.g. [band][error_component]);
error signs are preserved, not made absolute. All HDU cards are retained; models,
EnergyBounds and Hist_Start rows are embedded. Other ancillary rows are referenced
by input SHA256 and HDU index in the bundled FITS, not duplicated in JSON.
FITS undefined/TNULL/masked/nonfinite cells become JSON null.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
SPECS = {
    "fermi-fl16y": ("gll_psc_v41.fit", "Fermi FL16Y", 7224, 83, "v41"),
    "fermi-3fhl": ("gll_psch_v13.fit", "Fermi 3FHL", 1556, 55, "v13"),
}


def json_value(value):
    """Convert scalars/ND arrays without flattening or nonstandard JSON NaNs."""
    if value is None or value is np.ma.masked or isinstance(value, fits.card.Undefined):
        return None
    if isinstance(value, np.ma.MaskedArray):
        return json_value(value.tolist())
    if isinstance(value, np.ndarray):
        return json_value(value.tolist())
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, np.generic):
        return json_value(value.item())
    if isinstance(value, bytes):
        return value.decode("ascii").rstrip(" \x00")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported FITS value: {type(value)!r}")


def header_cards(header):
    return [{"keyword": c.keyword, "value": json_value(c.value), "comment": c.comment}
            for c in header.cards]


def columns_metadata(hdu):
    if not isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
        return {}
    output = {}
    for i, col in enumerate(hdu.columns, 1):
        related = [card for card in hdu.header.cards
                   if re.fullmatch(r"T[A-Z_]+" + str(i), card.keyword)]
        output[col.name] = {
            "unit": col.unit, "format": str(col.format), "dim": col.dim,
            "null": json_value(col.null),
            "array_shape": list(np.shape(hdu.data[col.name][0])) if len(hdu.data) else None,
            "header_cards": [{"keyword": c.keyword, "value": json_value(c.value),
                              "comment": c.comment} for c in related],
        }
    return output


def table_rows(hdu):
    """Explicitly honor integer TNULL, which fits.FITS_rec does not mask."""
    columns = hdu.columns
    result = []
    for row in hdu.data:
        output = {}
        for col in columns:
            value = row[col.name]
            if col.null is not None:
                # TNULL is expressed in stored units, before scaling.
                null = col.null * (col.bscale if col.bscale is not None else 1)
                null += col.bzero if col.bzero is not None else 0
                value = np.ma.masked_where(np.asarray(value) == null, value)
            output[col.name] = json_value(value)
        result.append(output)
    return result


def footprint(extended_name, model, center):
    """Finite disks only. Localization ellipses NEVER define source extent.

    A SpatialMap is not certified by its approximate Model_Form or semiaxes.
    Gaussian widths have infinite support and need an explicit containment rule.
    Planning radius is centred on the catalogue position; a model-centre offset
    is added to the model radius using the spherical triangle inequality.
    """
    if not extended_name:
        return {"planning_radius_deg": 0.0, "footprint_known": True,
                "footprint_kind": "point", "reason": "catalogue_point_source"}
    unknown = {"planning_radius_deg": None, "footprint_known": False,
               "footprint_kind": "unknown"}
    if model is None:
        return {**unknown, "reason": "unmatched_extended_source_name"}
    form = model["Model_Form"].strip().replace(" ", "").lower()
    spatial = model["Spatial_Function"].strip().lower()
    if form not in {"disk", "ellipticaldisk"} or spatial not in {"radialdisk", "ellipticaldisk"}:
        return {**unknown, "reason": "template_gaussian_or_ambiguous_support"}
    axes = [model["Model_SemiMajor"], model["Model_SemiMinor"]]
    if any(x is None or not math.isfinite(x) or x <= 0 for x in axes):
        return {**unknown, "reason": "invalid_disk_semiaxes"}
    model_center = [model["RAJ2000"], model["DEJ2000"]]
    if any(x is None for x in model_center + list(center)):
        return {**unknown, "reason": "unknown_model_center"}
    # Astropy is the authoritative spherical coordinate implementation.
    from astropy.coordinates import SkyCoord
    import astropy.units as u
    a = SkyCoord(center[0] * u.deg, center[1] * u.deg, frame="fk5", equinox="J2000")
    b = SkyCoord(model_center[0] * u.deg, model_center[1] * u.deg, frame="fk5", equinox="J2000")
    offset = float(a.separation(b).deg)
    radius = max(axes)
    return {"planning_radius_deg": radius + offset, "footprint_known": True,
            "footprint_kind": "circular_envelope", "reason": "finite_disk_envelope",
            "model_radius_deg": radius, "model_center_offset_deg": offset,
            "model_center_fk5_j2000_deg": model_center,
            "radius_semantics": "max(model semiaxes) + spherical centre offset; not a localization error"}


def energy_mapping(rows, flux_length, catalogue_id):
    """Do not assert a flux-band linkage from coincidental table dimensions."""
    pairs = list(dict.fromkeys((r["LowerEnergy"], r["UpperEnergy"]) for r in rows))
    result = {
        "status": "unknown", "flux_band_count": flux_length,
        "energy_bounds_row_count": len(rows), "flux_band_bounds": None,
        "candidate_unique_energy_bounds": [list(p) for p in pairs],
        "candidate_unit": "MeV" if catalogue_id == "fermi-fl16y" else "GeV",
        "evidence": {
            "local": "EnergyBounds and LAT_Point_Source_Catalog TTYPE/TFORM/TDIM/TUNIT cards retained verbatim",
            "column_comment_result": "No explicit band-index mapping in supplied TTYPE comments",
            "official_index": "https://fermi.gsfc.nasa.gov/ssc/data/access/",
            "official_3fhl": "https://fermi.gsfc.nasa.gov/ssc/data/access/lat/3FHL/",
            "verification": "Official 3FHL page confirms 10 GeV-2 TeV range, not array-index mapping. FL16Y exact mapping not independently verified.",
        },
        "warning": "Candidate bounds are unassigned, not flux-band labels. FL16Y has 23 event-component rows for 8 flux values; never zip these tables.",
    }
    if catalogue_id == "fermi-3fhl":
        expected = [(10.0, 20.0), (20.0, 50.0), (50.0, 150.0),
                    (150.0, 500.0), (500.0, 2000.0)]
        result["evidence"]["official_band_documentation"] = {
            "url": "https://heasarc.gsfc.nasa.gov/W3Browse/fermi/fermi3fhl.html",
            "bibcode": "2017ApJS..232...18A",
            "ordered_parameters": ["Flux_10_20_GeV", "Flux_20_50_GeV", "Flux_50_150_GeV",
                                   "Flux_150_500_GeV", "Flux_0p5_2_Tev"],
            "quotes": ["The integral photon flux from 10 GeV to 20 GeV, in photon/cm2/s.",
                       "The integral photon flux from 0.5 TeV to 2 TeV, in photon/cm2/s."],
            "scope": "Official HEASARC parameter definitions corroborate the five ordered FITS EnergyBounds intervals, not release-specific source counts.",
            "discrepancy": "HEASARC overview states 1558 objects; supplied v13 FITS has 1556 rows. Local source count remains authoritative.",
        }
        # Validate actual row order too: unique-pair counts cannot establish mapping.
        if flux_length == 5 and [(r["LowerEnergy"], r["UpperEnergy"]) for r in rows] == expected:
            result.update({"status": "verified", "flux_band_bounds": [list(p) for p in expected],
                           "unit": "GeV", "mapping_basis": "ordered FITS EnergyBounds corroborated by official HEASARC band parameter definitions",
                           "warning": None})
            result["evidence"]["verification"] = "Five documented bands match all five FITS EnergyBounds rows in ascending order; TFORM confirms five Flux_Band values. Differential units remain original TUNIT, not inferred from web text."
    return result


def extract_catalogue(input_path, catalogue_id):
    input_path = Path(input_path)
    _, label, expected_count, expected_models, version = SPECS[catalogue_id]
    digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    with fits.open(input_path, mode="readonly", memmap=False) as hdul:
        primary = hdul[0].header
        main = hdul["LAT_Point_Source_Catalog"]
        if primary.get("VERSION") != version or main.header.get("VERSION") != version:
            raise ValueError("Unexpected FITS release version")
        if main.header.get("RADECSYS") != "FK5" or main.header.get("EQUINOX") != 2000.0:
            raise ValueError("Expected FK5 J2000 source positions; no implicit frame conversion")
        rows = table_rows(main)
        extended = table_rows(hdul["ExtendedSources"])
        if len(rows) != expected_count or len(extended) != expected_models:
            raise ValueError(f"Unexpected row counts: sources={len(rows)}, models={len(extended)}")
        models = {r["Source_Name"]: r for r in extended}
        if len(models) != len(extended):
            raise ValueError("Duplicate ExtendedSources names")
        ids = [r["Source_Name"] for r in rows]
        if len(set(ids)) != len(ids) or any(not key for key in ids):
            raise ValueError("Empty or duplicate stable source identifier")
        metadata = columns_metadata(main)
        units = {name: col["unit"] for name, col in metadata.items()}
        sources = []
        linked = Counter()
        for index, raw in enumerate(rows):
            name = raw["Source_Name"]
            extended_name = raw["Extended_Source_Name"].strip()
            model = models.get(extended_name)
            if extended_name:
                linked[extended_name] += 1
            shape = footprint(extended_name, model, [raw["RAJ2000"], raw["DEJ2000"]])
            sources.append({
                "original_id": name, "original_row": index, "name": name,
                "source_key": f"{catalogue_id}:{name}",
                "ra_deg": raw["RAJ2000"], "dec_deg": raw["DEJ2000"],
                "l_deg": raw["GLON"], "b_deg": raw["GLAT"],
                "planning_radius_deg": shape["planning_radius_deg"],
                "footprint_known": shape["footprint_known"],
                "footprint_kind": shape["footprint_kind"],
                "p_err_95": raw["Conf_95_SemiMajor"],
                "extended_source_name": extended_name or None,
                "notes": {"raw": raw, "extended_model": model, "footprint": shape,
                          "units_reference": "#/units", "columns_reference": "#/columns",
                          "model_units_reference": "#/hdus/2/columns",
                          "position_error_semantics": "Conf_95_SemiMajor is localization uncertainty, never source extension",
                          "array_semantics": "Nested TDIM shape and signed error-component order retained; no symmetric reduction",
                          "coordinate_semantics": "Original FK5 J2000 RA/Dec and independently supplied Galactic l/b; no conversion"},
            })
        hdus = []
        for i, hdu in enumerate(hdul):
            entry = {"index": i, "name": hdu.name,
                     "version": hdu.header.get("VERSION"), "hduvers": hdu.header.get("HDUVERS"),
                     "row_count": len(hdu.data) if hdu.data is not None else 0,
                     "header_cards": header_cards(hdu.header), "columns": columns_metadata(hdu)}
            if isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                if hdu is main:
                    entry["rows_reference"] = "#/sources/*/notes/raw"
                elif hdu.name in {"ExtendedSources", "EnergyBounds", "Hist_Start"}:
                    entry["rows"] = table_rows(hdu)
                else:
                    entry["rows_reference"] = {
                        "format": "FITS", "repository_path": f"data/{input_path.name}",
                        "input_sha256": digest, "hdu_index": i, "hdu_name": hdu.name,
                        "reason": "Ancillary analysis table retained in bundled immutable FITS; not duplicated in normalized source JSON",
                    }
            hdus.append(entry)
        bounds = table_rows(hdul["EnergyBounds"])
        unmatched = sorted(set(linked) - set(models))
        if unmatched:
            raise ValueError(f"Unresolved extended-source links: {unmatched}")
        output = {
            "schema_version": 1, "catalogue_id": catalogue_id, "label": label,
            "source_count": len(sources),
            "provenance": {"input_filename": input_path.name, "input_sha256": digest,
                           "primary_version": primary.get("VERSION"),
                           "source_hdu_version": main.header.get("VERSION"),
                           "source_hduvers": main.header.get("HDUVERS"),
                           "fits_primary_date": primary.get("DATE"),
                           "fits_source_hdu_date": main.header.get("DATE"),
                           "official_release": ({
                               "version": "v13", "date": "2017-07-19", "change": "Updated redshifts",
                               "source_url": "https://fermi.gsfc.nasa.gov/ssc/data/access/lat/3FHL/",
                               "date_semantics": "FSSC release change-log date; distinct from original FITS DATE header values",
                           } if catalogue_id == "fermi-3fhl" else None),
                           "extractor": "scripts/build_fermi_catalogues.py", "extractor_schema_version": 1,
                           "original_row_base": 0,
                           "null_policy": "FITS undefined, TNULL, masked and nonfinite values => JSON null",
                           "unit_policy": "Original TUNIT strings and numerical values; no unit conversion",
                           "reproducibility": "Canonical sorted-key UTF-8 JSON; no runtime timestamp or absolute input path",
                           "catalogue_identity": "FL16Y preliminary 16-year source list, not a renamed 4FGL release" if catalogue_id == "fermi-fl16y" else "3FHL v13 high-energy catalogue"},
            "coordinate_system": {"equatorial_frame": "FK5", "equinox": 2000.0,
                                  "galactic_frame": "Galactic", "units": "deg"},
            "columns": metadata, "units": units, "sources": sources,
            "hdus": hdus, "energy_bounds": bounds,
            "spectral_band_mapping": energy_mapping(bounds, len(rows[0]["Flux_Band"]), catalogue_id),
            "validation": {"extended_model_count": len(extended), "linked_source_count": sum(linked.values()),
                           "linked_model_count": len(linked), "unmatched_extended_names": unmatched,
                           "unused_extended_models": sorted(set(models) - set(linked)),
                           "footprint_counts": dict(Counter(s["footprint_kind"] for s in sources))},
        }
    if hashlib.sha256(input_path.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Input changed during extraction")
    return output


def canonical_bytes(payload):
    return (json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "catalogues")
    parser.add_argument("--check", action="store_true", help="Compare deterministic bytes; write nothing")
    args = parser.parse_args()
    for catalogue_id, (filename, _, _, _, _) in SPECS.items():
        payload = extract_catalogue(args.input_dir / filename, catalogue_id)
        data = canonical_bytes(payload)
        destination = args.output_dir / f"{catalogue_id}.json"
        if args.check:
            if not destination.is_file() or destination.read_bytes() != data:
                raise SystemExit(f"Mismatch: {destination}")
        else:
            if destination.resolve() == (args.input_dir / filename).resolve():
                raise ValueError("Output must not overwrite source FITS")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        print(json.dumps({"catalogue_id": catalogue_id, "sources": payload["source_count"],
                          "input_sha256": payload["provenance"]["input_sha256"],
                          "output_sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                          "validation": payload["validation"], "check": args.check}, sort_keys=True))


if __name__ == "__main__":
    main()
