from datetime import datetime, timezone
import io
import ssl

import pytest
from fastapi.testclient import TestClient

from app.catalog import CatalogCollection, Source, catalog
from app.config import LACT_TELESCOPE
from app.gaia import GaiaQueryError, QUERY_TIMEOUT_SECONDS, _parse_csv
from app.main import app
from app.schemas import ConstraintSet
from app.sky_map import render_all_sky_svg


client = TestClient(app)


def _source(index, name, ra=10.0, dec=20.0, label="Test"):
    return Source(index, name, 0.5, None, ra, dec, 0.0, 0.0, None, label, "catalogue",
                  catalogue_id=label.lower(), original_id=name)


def test_catalogue_collection_search_is_sorted_and_preserves_identity():
    first = type("Catalogue", (), {"sources": (_source(7, "zeta", label="A"), _source(8, "Alpha", label="A")), "label": "A", "identifier": "a", "sha256": "a"})()
    second = type("Catalogue", (), {"sources": (_source(0, "beta", label="B"),), "label": "B", "identifier": "b", "sha256": "b"})()
    selected = CatalogCollection([first, second])
    assert [item.index for item in selected.sources] == [7, 8, 0]
    assert [item.name for item in selected.search()] == ["Alpha", "beta", "zeta"]
    assert selected.get(0).source_key == "b:beta"
    for tables in ([second, first], [second], [second, first, second]):
        reordered = CatalogCollection(tables)
        assert reordered.get("b:beta") == selected.get(0)
    assert len(CatalogCollection([first, first, second]).sources) == 3


def test_sky_map_uses_catalogue_stars_and_gaia_solid_dots():
    ordinary = _source(0, "ordinary")
    gaia = Source(1, "123", 0.0, None, 11.0, 21.0, 0.0, 0.0, None, "Gaia DR3", "gaia", 12.3,
                  catalogue_id="gaia-dr3", original_id="123")
    svg, snapshot = render_all_sky_svg([ordinary, gaia], datetime(2026, 12, 15, 16, tzinfo=timezone.utc), ConstraintSet())
    assert 'source-type-catalogue' in svg and 'source-star' in svg
    assert 'source-type-gaia' in svg and 'gaia-dot' in svg
    assert 'data-source-key="gaia-dr3:123"' in svg
    assert snapshot["display_frame"] == "altaz"


def test_gaia_csv_parser_keeps_magnitude_and_rejects_bad_schema():
    payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n3403822609273809792,10.0,20.0,2,0.2,1,0.1,2,0.1,13.2,13.6,12.8,0.8,1.1,12\n"
    rows = _parse_csv(payload, 10)
    assert rows[0].is_calibration_star is True
    assert rows[0].gaia_mag == 13.2
    assert rows[0].source_key == "gaia-dr3:3403822609273809792"
    assert rows[0].to_dict()["source_id"] == "3403822609273809792"
    assert rows[0].notes["proper_motion_applied"] is False
    assert rows[0].notes["query_fields"]["parallax_mas"] == 2
    assert rows[0].notes["distance"]["inverse_parallax_distance_pc"] == 500
    with pytest.raises(GaiaQueryError, match="missing source_id/ra/dec"):
        _parse_csv(b"source_id,ra\n123,10\n", 10)


def test_gaia_query_success_and_network_failure_are_bounded(monkeypatch):
    import app.gaia as gaia
    gaia._CACHE.clear()
    calls = []
    payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n456,10.0,20.0,2,0.2,1,0.1,2,0.1,14.1,14.5,13.7,0.8,1.1,12\n"

    def online(request, timeout, context):
        assert timeout == QUERY_TIMEOUT_SECONDS == 20
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        calls.append(request.full_url)
        return io.BytesIO(payload)

    monkeypatch.setattr(gaia, "urlopen", online)
    moment = datetime(2026, 12, 15, 16, tzinfo=timezone.utc)
    sources, meta = gaia.query_gaia_stars(moment, LACT_TELESCOPE, radius_deg=0.11, limit=3, max_mag=17)
    assert sources[0].gaia_mag == 14.1
    assert sources[0].notes["query_context"]["map_query_boundary"].startswith("bounded cone")
    assert meta["cached"] is False
    assert meta["bytes"] == len(payload) and meta["count"] == 1
    assert meta["truncated"] is False and meta["zero"] is False
    assert meta["selection"] == "bounded_unordered_subset"
    assert meta["ordering"] == "unspecified" and meta["brightest_n"] is False
    from urllib.parse import parse_qs, urlparse
    adql = parse_qs(urlparse(calls[0]).query)["QUERY"][0]
    assert "ORDER BY" not in adql.upper()
    assert "SELECT TOP 4 " in adql
    assert "phot_g_mean_mag <= 17.000" in adql and "0.110000" in adql
    assert gaia.query_gaia_stars(moment, LACT_TELESCOPE, radius_deg=0.11, limit=3, max_mag=17)[1]["cached"] is True
    assert len(calls) == 1

    def offline(request, timeout, context):
        raise OSError("offline")

    monkeypatch.setattr(gaia, "urlopen", offline)
    with pytest.raises(GaiaQueryError, match="online query failed"):
        gaia.query_gaia_stars(moment, LACT_TELESCOPE, radius_deg=0.12, limit=3, max_mag=17)
    # Failed requests release the bounded concurrent-query permit.
    assert gaia._QUERY_SLOTS.acquire(blocking=False)
    gaia._QUERY_SLOTS.release()
    gaia._CACHE.clear()


def test_multiple_catalogues_are_combined_by_sources_api():
    upload = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("extra.csv", b"name,ra,dec,ext\nExtra,10,20,0.2\n", "text/csv")},
    )
    assert upload.status_code == 200
    token = upload.json()["token"]
    original = upload.json()["sources"][0]
    assert original["source_key"] == token + ":Extra"
    for tokens in ("2lhaaso," + token, token + ",2lhaaso", token):
        response = client.get("/api/v1/sources", params={"catalog_tokens": tokens, "limit": 500})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == data["total"] == (191 if "2lhaaso" in tokens else 1)
        extra = next(item for item in data["sources"] if item["name"] == "Extra")
        assert extra["index"] == original["index"]
        assert extra["source_key"] == original["source_key"]
        if "2lhaaso" in tokens:
            first = next(item for item in data["sources"] if item["source_key"] == catalog.get(0).source_key)
            assert first["index"] == 0


def test_gaia_original_ids_that_collided_under_modulo_have_unique_presentation_indexes():
    # These two original IDs share their final 15 digits. No numeric hash or
    # truncation may merge the markers; cross-query identity stays string-only.
    payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n3403822609273809792,10,20,,,,,,,,12,,,,,\n3404822609273809792,11,21,,,,,,,,13,,,,,\n"
    rows = _parse_csv(payload, 10)
    assert len({row.index for row in rows}) == 2
    assert all(row.index < 2 ** 53 for row in rows)
    assert len({row.source_key for row in rows}) == 2
    assert [row.to_dict()["source_id"] for row in rows] == ["3403822609273809792", "3404822609273809792"]
    reversed_payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n3404822609273809792,11,21,,,,,,,,13,,,,,\n3403822609273809792,10,20,,,,,,,,12,,,,,\n"
    reversed_rows = _parse_csv(reversed_payload, 10)
    assert reversed_rows[1].source_key == rows[0].source_key
    assert reversed_rows[1].index != rows[0].index  # query-local presentation only
