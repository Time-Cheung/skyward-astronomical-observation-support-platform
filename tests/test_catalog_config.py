from pathlib import Path

import pytest

from app.catalog import Catalog, CatalogError, catalog, enrichment_store, installed_catalogue
from app.config import (
    CATALOG_EXPECTED_ROWS,
    FOV_DIAMETER_DEG,
    FOV_RADIUS_DEG,
    SITE_ALTITUDE_M,
    SITE_LATITUDE_DEG,
    SITE_LONGITUDE_DEG,
)

EXPECTED_SHA256 = "ae1712c892af21d33ed4b75a8d513a28070add4109c2a06b2c2f8d9df7acff25"


def test_confirmed_site_and_fov_constants():
    assert SITE_LONGITUDE_DEG == pytest.approx(100 + 1 / 60 + 36 / 3600)
    assert SITE_LATITUDE_DEG == pytest.approx(29 + 21 / 60 + 27 / 3600)
    assert SITE_ALTITUDE_M == 4410
    assert FOV_DIAMETER_DEG == 8.3
    assert FOV_RADIUS_DEG == 4.15


def test_public_1lhaaso_catalogue_loads_all_sources_and_components():
    assert catalog.identifier == "1lhaaso"
    assert catalog.label == "1LHAASO"
    assert len(catalog.sources) == CATALOG_EXPECTED_ROWS == 90
    assert [source.index for source in catalog.sources] == list(range(90))
    assert catalog.sha256 == EXPECTED_SHA256
    assert catalog.provenance["paper_doi"] == "10.3847/1538-4355/acfd29"
    assert catalog.provenance["source_count"] == 90
    assert catalog.provenance["component_rows"] == 180
    assert sum(len(source.notes["components"]) for source in catalog.sources) == 180

    crab = catalog.get(13)
    assert crab.display_name == "1LHAASO J0534+2200u"
    assert (crab.ra, crab.dec, crab.p_err_95) == pytest.approx((83.62, 22.01, 0.004))
    assert crab.planning_radius_deg is None
    assert crab.footprint_known is False
    assert crab.footprint_kind == "unknown_table2_gaussian_containment"
    assert crab.notes["representative_component"] == "WCDA"


def test_table2_upper_limits_units_and_r39_boundary_are_preserved():
    first = catalog.get(0)
    km2a, wcda = first.notes["components"]
    assert km2a["r39_kind"] == "upper_limit"
    assert km2a["r39_upper_limit_deg"] == pytest.approx(0.18)
    assert km2a["r39_statistical_interpretation"] == "95_percent_confidence_upper_limit"
    assert km2a["n0_units"] == "10^-16 cm^-2 s^-1 TeV^-1"
    assert km2a["reference_energy_tev"] == 50
    assert wcda["n0_kind"] == "upper_limit"
    assert wcda["n0_upper_limit"] == pytest.approx(0.27)
    assert wcda["n0_value"] is None
    assert wcda["n0_units"] == "10^-13 cm^-2 s^-1 TeV^-1"
    assert wcda["reference_energy_tev"] == 3
    measured = next(
        component
        for source in catalog.sources
        for component in source.notes["components"]
        if component["r39_kind"] == "measurement"
    )
    assert measured["r39_statistical_interpretation"] == "1_sigma_statistical_uncertainty"
    associated = next(
        component
        for source in catalog.sources
        for component in source.notes["components"]
        if component["association"]
    )
    assert associated["association_scope"] == "preliminary_positional_counterpart_from_table2"
    assert all(source.planning_radius_deg is None for source in catalog.sources)


def test_unpublished_2lhaaso_is_not_installed_or_served():
    with pytest.raises(KeyError):
        installed_catalogue("2lhaaso")
    assert not (Path(__file__).resolve().parents[1] / "data" / "2LHAASO.txt").exists()


def test_fermi_display_names_normalize_survey_prefix_without_changing_identity():
    for identifier, prefix in (("fermi-3fhl", "3FHL"), ("fermi-fl16y", "FL16Y")):
        row = installed_catalogue(identifier).sources[0]
        assert row.display_name.startswith(prefix + " ")
        assert (prefix + " " + prefix) not in row.display_name
        assert row.source_key.endswith(row.name)


def test_catalogue_search_understands_prefix_and_name():
    assert catalog.search("1LHAASO J0634+1741u")[0].index == 18
    assert catalog.search("J0534+2200")[0].index == 13
    assert len(catalog.search("", limit=2)) == 2


def test_legacy_csv_loader_requires_an_explicit_path():
    with pytest.raises(TypeError):
        Catalog()


def test_legacy_csv_loader_rejects_tampered_schema(tmp_path: Path):
    broken = tmp_path / "broken.csv"
    broken.write_text("index,name\n0,a\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="Unexpected catalogue columns"):
        Catalog(broken)


def test_missing_enrichment_is_explicitly_unverified():
    data = enrichment_store.get(13)
    assert data["spectral_model"] is None
    assert data["associated_sources"] == []
    assert data["verification_status"] == "unverified"
