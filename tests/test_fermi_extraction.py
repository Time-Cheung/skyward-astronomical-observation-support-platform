"""Scientific regression tests; real attached FITS are optional on other hosts.

Run: .venv/bin/python -B -m pytest -p no:cacheprovider tests/test_fermi_extraction.py
"""
from pathlib import Path
import hashlib
import json
import math

import numpy as np
import pytest
from astropy.io import fits

from scripts.build_fermi_catalogues import (
    ROOT, SPECS, canonical_bytes, energy_mapping, extract_catalogue, footprint,
    json_value, table_rows,
)


@pytest.fixture(scope="module", params=list(SPECS))
def catalogue(request):
    key = request.param
    path = ROOT / "data" / SPECS[key][0]
    if not path.is_file():
        path = ROOT.parent / SPECS[key][0]
    if not path.is_file():
        pytest.skip(f"Original attachment unavailable: {path}")
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    result = extract_catalogue(path, key)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    return key, path, result


def test_exact_counts_ids_versions_and_source_hash(catalogue):
    key, path, result = catalogue
    filename, _, count, models, version = SPECS[key]
    assert len(result["sources"]) == count
    assert len(set(s["original_id"] for s in result["sources"])) == count
    assert result["provenance"]["input_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["provenance"]["primary_version"] == version
    assert result["provenance"]["source_hdu_version"] == version
    assert result["validation"]["extended_model_count"] == models
    assert result["validation"]["unmatched_extended_names"] == []
    with fits.open(path) as hdul:
        for index, (source, row) in enumerate(zip(result["sources"], hdul[1].data)):
            assert source["original_id"] == row["Source_Name"]
            assert source["name"] == row["Source_Name"]
            assert source["original_row"] == index
            assert source["source_key"] == f"{key}:{row['Source_Name']}"


def test_every_source_field_array_unit_and_coordinate_preserved(catalogue):
    key, path, result = catalogue
    with fits.open(path) as hdul:
        table = hdul[1]
        assert set(result["columns"]) == set(table.columns.names)
        assert result["coordinate_system"] == {"equatorial_frame": "FK5", "equinox": 2000.0,
                                                "galactic_frame": "Galactic", "units": "deg"}
        for c in table.columns:
            assert result["units"][c.name] == c.unit
            assert result["columns"][c.name]["format"] == c.format
            assert result["columns"][c.name]["dim"] == c.dim
        for source, row in zip(result["sources"], table.data):
            raw = source["notes"]["raw"]
            assert set(raw) == set(table.columns.names)
            for c in table.columns:
                v = row[c.name]
                if c.null is not None and np.ndim(v) == 0 and v == c.null:
                    assert raw[c.name] is None
                else:
                    assert raw[c.name] == json_value(v)
            for target, original in [("ra_deg", "RAJ2000"), ("dec_deg", "DEJ2000"),
                                     ("l_deg", "GLON"), ("b_deg", "GLAT")]:
                assert source[target] == float(row[original])
            assert 0 <= source["ra_deg"] < 360 and -90 <= source["dec_deg"] <= 90
            bands = 8 if key == "fermi-fl16y" else 5
            assert len(raw["Flux_Band"]) == bands
            assert len(raw["Unc_Flux_Band"]) == bands
            assert all(len(pair) == 2 for pair in raw["Unc_Flux_Band"])
            if key == "fermi-fl16y":
                assert len(raw["Flux_History"]) == 16
                assert np.shape(raw["Unc_Flux_History"]) == (16, 2)


def test_hdu_headers_ancillary_fields_and_energy_bounds_preserved(catalogue):
    key, path, result = catalogue
    with fits.open(path) as hdul:
        assert len(result["hdus"]) == len(hdul)
        for stored, hdu in zip(result["hdus"], hdul):
            assert stored["name"] == hdu.name
            assert stored["version"] == hdu.header.get("VERSION")
            assert len(stored["header_cards"]) == len(hdu.header.cards)
            for output, original in zip(stored["header_cards"], hdu.header.cards):
                assert output == {"keyword": original.keyword, "value": json_value(original.value),
                                  "comment": original.comment}
            if hdu.data is not None:
                assert stored["row_count"] == len(hdu.data)
                if hdu.name in {"ExtendedSources", "EnergyBounds", "Hist_Start"}:
                    assert stored["rows"] == table_rows(hdu)
                else:
                    assert "rows" not in stored
                    if hdu.name == "LAT_Point_Source_Catalog":
                        assert stored["rows_reference"] == "#/sources/*/notes/raw"
                    else:
                        ref = stored["rows_reference"]
                        assert ref["hdu_index"] == hdul.index_of(hdu)
                        assert ref["hdu_name"] == hdu.name
                        assert ref["input_sha256"] == result["provenance"]["input_sha256"]
                        assert ref["repository_path"] == f"data/{path.name}"
        assert result["energy_bounds"] == table_rows(hdul["EnergyBounds"])
    mapping = result["spectral_band_mapping"]
    assert mapping["energy_bounds_row_count"] == (23 if key == "fermi-fl16y" else 5)
    if key == "fermi-fl16y":
        assert mapping["status"] == "unknown"
        assert mapping["flux_band_bounds"] is None
        assert len(mapping["candidate_unique_energy_bounds"]) == 8
        assert result["units"]["Pivot_Energy"] == "MeV"
    else:
        assert mapping["status"] == "verified"
        assert mapping["flux_band_bounds"] == [[10, 20], [20, 50], [50, 150], [150, 500], [500, 2000]]
        assert mapping["unit"] == "GeV"
        assert "heasarc.gsfc.nasa.gov" in mapping["evidence"]["official_band_documentation"]["url"]
        assert result["provenance"]["official_release"]["date"] == "2017-07-19"
        assert result["provenance"]["official_release"]["change"] == "Updated redshifts"
        assert result["provenance"]["fits_source_hdu_date"] == "2017-02-02T13:47:36"
        assert result["units"]["Pivot_Energy"] == "GeV"
        assert result["units"]["Flux_Density"] == "photon/cm**2/GeV/s"
        assert result["energy_bounds"][0]["LowerEnergy"] == 10.0
        assert result["energy_bounds"][-1]["UpperEnergy"] == 2000.0


def test_extended_joins_and_conservative_footprints(catalogue):
    _, _, result = catalogue
    models = {row["Source_Name"]: row for row in result["hdus"][2]["rows"]}
    for source in result["sources"]:
        notes = source["notes"]
        ext = source["extended_source_name"]
        if ext is None:
            assert source["footprint_kind"] == "point"
            assert source["planning_radius_deg"] == 0.0
            assert source["footprint_known"] is True
            assert notes["extended_model"] is None
        else:
            model = models[ext]
            assert notes["extended_model"] == model
            if model["Model_Form"] == "Disk" and model["Spatial_Function"] == "RadialDisk":
                assert source["footprint_kind"] == "circular_envelope"
                assert source["footprint_known"] is True
                assert source["planning_radius_deg"] >= max(model["Model_SemiMajor"], model["Model_SemiMinor"])
            else:
                assert source["planning_radius_deg"] is None
                assert source["footprint_known"] is False
                assert source["footprint_kind"] == "unknown"
        assert source["p_err_95"] == notes["raw"]["Conf_95_SemiMajor"]


def test_generated_file_is_exact_deterministic_strict_json(catalogue):
    key, _, result = catalogue
    output = ROOT / "data" / "catalogues" / f"{key}.json"
    assert output.is_file(), "Build catalogue output before running attachment integration tests"
    expected = canonical_bytes(result)
    assert output.read_bytes() == expected
    assert canonical_bytes(result) == expected
    decoded = json.loads(expected, parse_constant=lambda token: pytest.fail(f"Invalid JSON token {token}"))
    assert decoded == result


def test_null_policy_handles_masked_nan_infinity_and_integer_tnull():
    assert json_value(np.ma.array([1.0, 2.0], mask=[False, True])) == [1.0, None]
    assert json_value(np.ma.masked) is None
    assert json_value(np.array([[np.nan, np.inf], [-np.inf, 3.0]])) == [[None, None], [None, 3.0]]
    hdu = fits.BinTableHDU.from_columns([
        fits.Column(name="integer", format="I", null=-1, array=np.array([2, -1])),
        fits.Column(name="float", format="E", array=np.array([np.nan, 3.0])),
    ])
    assert table_rows(hdu) == [{"integer": 2, "float": None}, {"integer": None, "float": 3.0}]


@pytest.mark.parametrize("form,spatial", [("2D Gaussian", "RadialGauss"), ("Map", "SpatialMap"),
                                            ("Disk", "SpatialMap"), ("Ring", "SpatialMap"),
                                            ("unknown", "RadialDisk")])
def test_ambiguous_models_never_become_zero_radius(form, spatial):
    model = {"Model_Form": form, "Spatial_Function": spatial}
    result = footprint("extended", model, [10.0, 20.0])
    assert result["planning_radius_deg"] is None
    assert result["footprint_known"] is False


def test_explicit_elliptical_disk_envelope_includes_center_offset():
    model = {"Model_Form": "EllipticalDisk", "Spatial_Function": "EllipticalDisk",
             "Model_SemiMajor": 0.5, "Model_SemiMinor": 0.25, "RAJ2000": 11.0, "DEJ2000": 0.0}
    result = footprint("extended", model, [10.0, 0.0])
    assert result["planning_radius_deg"] == pytest.approx(1.5)
    assert result["model_center_offset_deg"] == pytest.approx(1.0)
    assert result["footprint_known"] is True
    model["Model_SemiMajor"] = None
    assert footprint("extended", model, [10.0, 0.0])["planning_radius_deg"] is None


def test_point_and_unmatched_models_have_distinct_semantics():
    assert footprint("", None, [0, 0])["footprint_kind"] == "point"
    assert footprint("absent", None, [0, 0])["planning_radius_deg"] is None


def test_error_arrays_not_flattened_or_absolutized():
    value = np.array([[-1.0, 3.0], [np.nan, 4.0]])
    assert json_value(value) == [[-1.0, 3.0], [None, 4.0]]


def test_equal_dimensions_alone_do_not_establish_band_mapping():
    rows = [{"LowerEnergy": 10.0, "UpperEnergy": 20.0}]
    result = energy_mapping(rows, 1, "fermi-3fhl")
    assert result["status"] == "unknown" and result["flux_band_bounds"] is None


def test_documented_band_mapping_requires_exact_order_and_values():
    rows = [{"LowerEnergy": a, "UpperEnergy": b} for a, b in
            [(10, 20), (20, 50), (50, 150), (150, 500), (500, 2000)]]
    assert energy_mapping(rows, 5, "fermi-3fhl")["status"] == "verified"
    assert energy_mapping(list(reversed(rows)), 5, "fermi-3fhl")["status"] == "unknown"
    assert energy_mapping(rows, 4, "fermi-3fhl")["status"] == "unknown"
    rows[0]["LowerEnergy"] = 9
    assert energy_mapping(rows, 5, "fermi-3fhl")["status"] == "unknown"


def test_no_large_ancillary_table_embedded(catalogue):
    key, _, result = catalogue
    for hdu in result["hdus"]:
        if hdu["name"] in {"GTI", "ROIs", "Components", "LAT_Point_Source_Catalog"}:
            assert "rows" not in hdu
            assert "rows_reference" in hdu
    if key == "fermi-fl16y":
        gti = next(h for h in result["hdus"] if h["name"] == "GTI")
        assert gti["row_count"] == 91340
        assert set(gti["columns"]) == {"START", "STOP"}
        assert len(canonical_bytes(result)) < 40_000_000
