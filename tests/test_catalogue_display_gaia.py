from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.catalog import CatalogCollection, Source, catalog
from app.config import LACT_TELESCOPE
from app.gaia import GaiaQueryError, _parse_csv
from app.main import app
from app.schemas import ConstraintSet
from app.sky_map import render_all_sky_svg


client = TestClient(app)


def _source(index, name, ra=10.0, dec=20.0, label="Test"):
    return Source(index, name, 0.5, None, ra, dec, 0.0, 0.0, None, label, "catalogue")


def test_catalogue_collection_search_is_sorted_and_remaps_indexes():
    first = type("Catalogue", (), {"sources": (_source(7, "zeta", label="A"), _source(8, "Alpha", label="A")), "label": "A", "identifier": "a", "sha256": "a"})()
    second = type("Catalogue", (), {"sources": (_source(0, "beta", label="B"),), "label": "B", "identifier": "b", "sha256": "b"})()
    selected = CatalogCollection([first, second])
    assert [item.index for item in selected.sources] == [0, 1, 2]
    assert [item.name for item in selected.search()] == ["Alpha", "beta", "zeta"]
    assert selected.get(2).source_key == "B:2"


def test_sky_map_uses_hollow_circles_and_gaia_stars():
    ordinary = _source(0, "ordinary")
    gaia = Source(1, "123", 0.0, None, 11.0, 21.0, 0.0, 0.0, None, "Gaia DR3", "gaia", 12.3)
    svg, snapshot = render_all_sky_svg([ordinary, gaia], datetime(2026, 12, 15, 16, tzinfo=timezone.utc), ConstraintSet())
    assert 'source-type-catalogue' in svg and '<circle cx=' in svg
    assert 'source-type-gaia' in svg and '<polygon points=' in svg
    assert snapshot["display_frame"] == "altaz"


def test_gaia_csv_parser_keeps_magnitude_and_rejects_bad_schema():
    payload = b"source_id,ra,dec,phot_g_mean_mag\n123,10.0,20.0,13.2\n"
    rows = _parse_csv(payload, 10)
    assert rows[0].is_calibration_star is True
    assert rows[0].gaia_mag == 13.2
    try:
        _parse_csv(b"source_id,ra\n123,10\n", 10)
    except GaiaQueryError as exc:
        assert "source_id, ra and dec" in str(exc)
    else:
        raise AssertionError("bad Gaia schema should fail")


def test_gaia_query_success_and_network_failure_are_bounded(monkeypatch):
    import app.gaia as gaia

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, size=-1):
            return b"source_id,ra,dec,phot_g_mean_mag\n456,10.0,20.0,14.1\n"

    monkeypatch.setattr(gaia, "urlopen", lambda request, timeout: Response())
    sources, meta = gaia.query_gaia_stars(datetime(2026, 12, 15, 16, tzinfo=timezone.utc), LACT_TELESCOPE, radius_deg=0.11, limit=3, max_mag=17)
    assert sources[0].gaia_mag == 14.1
    assert meta["cached"] is False

    monkeypatch.setattr(gaia, "urlopen", lambda request, timeout: (_ for _ in ()).throw(OSError("offline")))
    try:
        gaia.query_gaia_stars(datetime(2026, 12, 15, 16, tzinfo=timezone.utc), LACT_TELESCOPE, radius_deg=0.12, limit=3, max_mag=17)
    except GaiaQueryError as exc:
        assert "online query failed" in str(exc)
    else:
        raise AssertionError("offline Gaia query should fail clearly")


def test_multiple_catalogues_are_combined_by_sources_api():
    upload = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("extra.csv", b"name,ra,dec,ext\nExtra,10,20,0.2\n", "text/csv")},
    )
    assert upload.status_code == 200
    token = upload.json()["token"]
    response = client.get("/api/v1/sources", params={"catalog_tokens": "2lhaaso," + token, "limit": 500})
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 191
    assert any(item["name"] == "Extra" for item in data["sources"])
    assert next(item["index"] for item in data["sources"] if item["name"] == "Extra") == 190
