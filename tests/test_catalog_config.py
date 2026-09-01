from pathlib import Path

import pytest

from app.catalog import Catalog, CatalogError, catalog, enrichment_store
from app.config import (
    CATALOG_EXPECTED_ROWS,
    FOV_DIAMETER_DEG,
    FOV_RADIUS_DEG,
    SITE_ALTITUDE_M,
    SITE_LATITUDE_DEG,
    SITE_LONGITUDE_DEG,
)

EXPECTED_SHA256 = "83bbd6bf48c9f5d95b94db6495688471dfbe644d3047f39d4baf12dfcab69842"


def test_confirmed_site_and_fov_constants():
    assert SITE_LONGITUDE_DEG == pytest.approx(100 + 1 / 60 + 36 / 3600)
    assert SITE_LATITUDE_DEG == pytest.approx(29 + 21 / 60 + 27 / 3600)
    assert SITE_ALTITUDE_M == 4410
    assert FOV_DIAMETER_DEG == 8.3
    assert FOV_RADIUS_DEG == 4.15


def test_catalogue_loads_all_rows_and_known_sources():
    assert len(catalog.sources) == CATALOG_EXPECTED_ROWS == 190
    assert [source.index for source in catalog.sources] == list(range(190))
    assert catalog.sha256 == EXPECTED_SHA256
    crab = catalog.get(11)
    assert crab.display_name == "2LHAASO J0534+2200"
    assert (crab.ra, crab.dec, crab.ext, crab.p_err_95) == pytest.approx(
        (83.630, 22.011, 0.010, 0.010)
    )
    assert catalog.get(168).name == "Geminga"
    assert catalog.get(168).ext == 8.0


def test_catalogue_search_understands_prefix_and_name():
    assert catalog.search("2LHAASO Geminga")[0].index == 168
    assert catalog.search("J0534")[0].index == 11
    assert len(catalog.search("", limit=2)) == 2


def test_catalogue_rejects_tampered_schema(tmp_path: Path):
    broken = tmp_path / "broken.csv"
    broken.write_text("index,name\n0,a\n", encoding="utf-8")
    with pytest.raises(CatalogError, match="Unexpected catalogue columns"):
        Catalog(broken)


def test_missing_enrichment_is_explicitly_unverified():
    data = enrichment_store.get(11)
    assert data["spectral_model"] is None
    assert data["associated_sources"] == []
    assert data["verification_status"] == "unverified"
