from datetime import datetime, timezone
import io
import ssl
import xml.etree.ElementTree as ET

import pytest
from astropy.coordinates import SkyCoord
from pathlib import Path
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


def test_sky_map_uses_catalogue_stars_and_gaia_crosses():
    ordinary = _source(0, "ordinary")
    gaia = Source(1, "123", 0.0, None, 11.0, 21.0, 0.0, 0.0, None, "Gaia DR3", "gaia", 12.3,
                  catalogue_id="gaia-dr3", original_id="123")
    svg, snapshot = render_all_sky_svg([ordinary, gaia], datetime(2026, 12, 15, 16, tzinfo=timezone.utc), ConstraintSet())
    assert 'source-type-catalogue' in svg and 'source-star' in svg
    assert 'source-type-gaia' in svg and 'gaia-cross' in svg
    assert '<path class="source-symbol gaia-cross"' in svg
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


def test_gaia_sync_error_preserves_bounded_service_diagnostic(monkeypatch):
    import app.gaia as gaia
    from urllib.error import HTTPError

    error = HTTPError(
        gaia.GAIA_TAP_URL, 400, "Bad Request", {},
        io.BytesIO(b"ADQL syntax error: unexpected token"),
    )

    def reject(request, timeout, context):
        assert request.get_method() == "POST"
        raise error

    monkeypatch.setattr(gaia, "urlopen", reject)
    with pytest.raises(HTTPError, match="ADQL syntax error: unexpected token") as caught:
        gaia._read_gaia_payload(
            SkyCoord(ra=10, dec=20, unit="deg", frame="icrs"),
            1.0, 10, 10.0, 1.0,
        )
    assert gaia._should_retry(caught.value) is False


def test_gaia_query_success_and_network_failure_are_bounded(monkeypatch):
    import app.gaia as gaia
    gaia._CACHE.clear()
    calls = []
    payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n456,10.0,20.0,2,0.2,1,0.1,2,0.1,14.1,14.5,13.7,0.8,1.1,12\n"

    def online(request, timeout, context):
        assert request.get_method() == "POST"
        assert request.full_url == gaia.GAIA_TAP_URL
        assert request.headers["Content-type"] == "application/x-www-form-urlencoded"
        assert b"QUERY=" in request.data
        assert timeout == QUERY_TIMEOUT_SECONDS == 30
        assert context.verify_mode == ssl.CERT_REQUIRED
        assert context.check_hostname
        calls.append(request)
        return io.BytesIO(payload)

    monkeypatch.setattr(gaia, "urlopen", online)
    moment = datetime(2026, 12, 15, 16, tzinfo=timezone.utc)
    sources, meta = gaia.query_gaia_stars(moment, LACT_TELESCOPE, radius_deg=0.11, limit=3, max_mag=10)
    assert sources[0].gaia_mag == 14.1
    assert sources[0].notes["query_context"]["map_query_boundary"].startswith("bounded cone")
    assert meta["cached"] is False
    assert meta["bytes"] == len(payload) and meta["count"] == 1
    assert meta["truncated"] is False and meta["zero"] is False
    assert meta["selection"] == "nearest_by_angular_distance"
    assert meta["ordering"] == "angular_distance_asc" and meta["brightest_n"] is False
    from urllib.parse import parse_qs
    adql = parse_qs(calls[0].data.decode("ascii"))["QUERY"][0]
    assert calls[0].get_method() == "POST"
    assert "ORDER BY ANGULAR_DISTANCE ASC" in adql.upper()
    assert "SELECT TOP 4 " in adql
    assert "phot_g_mean_mag <= 10.000" in adql and "0.110000" in adql
    assert gaia.query_gaia_stars(moment, LACT_TELESCOPE, radius_deg=0.11, limit=3, max_mag=10)[1]["cached"] is True
    assert len(calls) == 1

    def offline(request, timeout, context):
        raise OSError("offline")

    monkeypatch.setattr(gaia, "urlopen", offline)
    with pytest.raises(GaiaQueryError, match="online query failed"):
        gaia.query_gaia_stars(moment, LACT_TELESCOPE, radius_deg=0.12, limit=3, max_mag=10)
    # Failed requests release the bounded concurrent-query permit.
    assert gaia._QUERY_SLOTS.acquire(blocking=False)
    gaia._QUERY_SLOTS.release()
    gaia._CACHE.clear()



def test_gaia_large_query_uses_async_tap_polling_result_and_cleanup(monkeypatch):
    import app.gaia as gaia

    gaia._CACHE.clear()
    payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n789,10,20,,,,,,,,13,,,,,\n"

    class Response(io.BytesIO):
        def __init__(self, body=b"", headers=None):
            super().__init__(body)
            self.headers = headers or {}

    responses = iter([
        Response(headers={"Location": "https://gea.example/tap-server/tap/async/42"}),
        Response(b"EXECUTING"),
        Response(b"COMPLETED"),
        Response(payload),
        Response(),
    ])
    calls = []

    def fake_urlopen(request, timeout, context):
        calls.append((request, timeout, context))
        assert timeout <= gaia.ASYNC_TOTAL_BUDGET_SECONDS
        assert context.verify_mode == ssl.CERT_REQUIRED
        return next(responses)

    monkeypatch.setattr(gaia, "urlopen", fake_urlopen)
    monkeypatch.setattr(gaia.time, "sleep", lambda seconds: None)
    rows, meta = gaia.query_gaia_stars(
        datetime(2026, 12, 15, 16, tzinfo=timezone.utc), LACT_TELESCOPE,
        radius_deg=1.1, limit=100, max_mag=10, target_ra_deg=10, target_dec_deg=20,
    )

    assert [row.original_id for row in rows] == ["789"]
    assert meta["query_strategy"] == "async_tap"
    assert meta["query_strategy_metadata"]["large_query"] is True
    assert meta["total_query_budget_seconds"] == gaia.ASYNC_TOTAL_BUDGET_SECONDS == 30
    assert meta["async_cleanup_attempted"] is True
    assert [request.get_method() for request, _, _ in calls] == ["POST", "GET", "GET", "GET", "DELETE"]
    assert calls[0][0].full_url.endswith("/tap-server/tap/async")
    assert b"PHASE=RUN" in calls[0][0].data
    assert calls[1][0].full_url.endswith("/async/42/phase")
    assert calls[3][0].full_url.endswith("/async/42/results/result")
    assert calls[4][0].full_url.endswith("/async/42")
    assert meta["bytes"] == sum(len(body) for body in (b"", b"EXECUTING", b"COMPLETED", payload))
    gaia._CACHE.clear()


def test_gaia_async_failure_reports_reason_and_attempts_cleanup(monkeypatch):
    import app.gaia as gaia

    gaia._CACHE.clear()

    class Response(io.BytesIO):
        def __init__(self, body=b"", headers=None):
            super().__init__(body)
            self.headers = headers or {}

    responses = iter([
        Response(headers={"Location": "https://gea.example/tap-server/tap/async/99"}),
        Response(b"ERROR: quota exceeded"),
        Response(),
    ])
    methods = []

    def fake_urlopen(request, timeout, context):
        methods.append(request.get_method())
        return next(responses)

    monkeypatch.setattr(gaia, "urlopen", fake_urlopen)
    with pytest.raises(GaiaQueryError, match="quota exceeded") as caught:
        gaia.query_gaia_stars(
            datetime(2026, 12, 15, 16, tzinfo=timezone.utc), LACT_TELESCOPE,
            radius_deg=1.1, limit=100, max_mag=10, target_ra_deg=10, target_dec_deg=21,
        )
    assert methods == ["POST", "GET", "DELETE"]
    assert caught.value.metadata["actual_failure_reason"].endswith("quota exceeded")
    assert caught.value.metadata["async_cleanup_attempted"] is True
    gaia._CACHE.clear()


def test_gaia_async_invalid_result_preserves_lifecycle_metadata(monkeypatch):
    import app.gaia as gaia

    gaia._CACHE.clear()

    class Response(io.BytesIO):
        def __init__(self, body=b"", headers=None):
            super().__init__(body)
            self.headers = headers or {}

    responses = iter([
        Response(headers={"Location": "https://gea.example/tap-server/tap/async/invalid"}),
        Response(b"COMPLETED"),
        Response(b"not,a,gaia,csv\n1,2,3,4\n"),
        Response(),
    ])
    methods = []

    def fake_urlopen(request, timeout, context):
        methods.append(request.get_method())
        return next(responses)

    monkeypatch.setattr(gaia, "urlopen", fake_urlopen)
    with pytest.raises(GaiaQueryError, match="missing source_id/ra/dec") as caught:
        gaia.query_gaia_stars(
            datetime(2026, 12, 15, 16, tzinfo=timezone.utc), LACT_TELESCOPE,
            radius_deg=1.1, limit=100, max_mag=10, target_ra_deg=10, target_dec_deg=22,
        )

    assert methods == ["POST", "GET", "GET", "DELETE"]
    assert caught.value.metadata["async_job_url"].endswith("/async/invalid")
    assert caught.value.metadata["async_poll_attempts"] == 1
    assert caught.value.metadata["async_cleanup_attempted"] is True
    assert caught.value.metadata["async_cleanup_error"] is None
    gaia._CACHE.clear()


def test_gaia_endpoint_defaults_and_bounds(monkeypatch):
    import app.main as main

    captured = {}

    def fake_query(moment, telescope, radius, limit, max_mag, target_ra, target_dec):
        captured.update(radius=radius, limit=limit, max_mag=max_mag)
        return [], {"count": 0, "zero": True, "status": "zero", "cached": False, "cache_hit": False, "cache": {"hit": False}}

    monkeypatch.setattr(main, "query_gaia_stars", fake_query)
    response = client.get("/api/v1/gaia", params={"target_ra_deg": 10, "target_dec_deg": 20})
    assert response.status_code == 200
    assert captured == {"radius": 1.0, "limit": 10, "max_mag": 10.0}
    assert response.json()["status_counts"] == {"GREEN": 0, "RED": 0, "UNKNOWN": 0}
    assert response.json()["sources"] == []
    for name, value in (("radius_deg", 0.09), ("radius_deg", 5.01), ("limit", 0), ("limit", 501), ("max_mag", 4), ("max_mag", 23)):
        assert client.get("/api/v1/gaia", params={"target_ra_deg": 10, "target_dec_deg": 20, name: value}).status_code == 422


    import app.gaia as gaia
    gaia._CACHE.clear()
    payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n456,10.0,20.0,,,,,,,,14,,,,,\n457,10.01,20.01,,,,,,,,15,,,,,\n999,20.0,20.0,,,,,,,,16,,,,,\n"
    calls = []

    def bounded_read(center, radius, row_limit, max_mag, timeout, boundary_center=None, boundary_radius_deg=None, order_center=None):
        calls.append((center, radius, row_limit, timeout, boundary_center, boundary_radius_deg))
        if len(calls) == 1:
            raise TimeoutError("initial small-cone timeout")
        return payload

    monkeypatch.setattr(gaia, "_read_gaia_payload", bounded_read)
    rows, meta = gaia.query_gaia_stars(
        datetime(2026, 9, 16, 16, tzinfo=timezone.utc), LACT_TELESCOPE, radius_deg=0.5, limit=10, max_mag=10,
        target_ra_deg=10, target_dec_deg=20,
    )
    assert len(calls) == 1 + gaia.FALLBACK_SUBCONE_COUNT
    assert all(call[1] == 0.25 for call in calls[1:])
    assert all(call[5] == 0.5 for call in calls[1:])
    assert {row.original_id for row in rows} == {"456", "457"}
    assert len({row.source_key for row in rows}) == 2
    assert meta["fallback_used"] is True
    assert meta["attempts"] == 6
    assert meta["truncated"] is True and meta["incomplete"] is True
    assert "subcones inside the original cone" in meta["warning"]
    assert meta["fallback_reason"] == "Gaia response exceeded query timeout" or "initial small-cone timeout" in meta["fallback_reason"]
    gaia._CACHE.clear()
    upload = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("extra.csv", b"name,ra,dec,ext\nExtra,10,20,0.2\n", "text/csv")},
    )
    assert upload.status_code == 200
    token = upload.json()["token"]
    original = upload.json()["sources"][0]
    assert original["source_key"] == token + ":Extra"
    for tokens in ("1lhaaso," + token, token + ",1lhaaso", token):
        response = client.get("/api/v1/sources", params={"catalog_tokens": tokens, "limit": 500})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == data["total"] == (91 if "1lhaaso" in tokens else 1)
        extra = next(item for item in data["sources"] if item["name"] == "Extra")
        assert extra["index"] == original["index"]
        assert extra["source_key"] == original["source_key"]
        if "1lhaaso" in tokens:
            first = next(item for item in data["sources"] if item["source_key"] == catalog.get(0).source_key)
            assert first["index"] == 0


def test_gaia_endpoint_colours_each_cross_and_reports_matching_status_counts(monkeypatch):
    import app.main as main

    star = Source(10001, "Gaia DR3 123", 0.0, None, 10.0, 20.0, 0.0, 0.0, None,
                  "Gaia DR3", "gaia", catalogue_id="gaia-dr3", original_id="123")
    monkeypatch.setattr(
        main, "query_gaia_stars",
        lambda *args, **kwargs: ([star], {"count": 1, "zero": False, "status": "success", "cached": False}),
    )
    response = client.get("/api/v1/gaia", params={
        "map_kind": "local-fov", "target_ra_deg": 10, "target_dec_deg": 20,
        "at_time": "2026-09-22T00:00:00Z",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    status = payload["sources"][0]["status"]
    assert status in {"GREEN", "RED"}
    assert payload["status_counts"][status] == 1
    assert payload["status_counts"]["UNKNOWN"] == 0
    assert f"status-{status.lower()}" in payload["overlay_svg"]
    root = ET.fromstring(payload["overlay_svg"])
    cross = next(node for node in root.iter() if "gaia-cross" in node.attrib.get("class", "").split())
    assert cross.tag.endswith("path") and cross.attrib["d"].count("M") == 2
    css = (Path(__file__).resolve().parents[1] / "app/static/styles.css").read_text(encoding="utf-8")
    assert "source-type-gaia.status-green .gaia-cross { stroke: var(--green) !important; }" in css
    assert "source-type-gaia.status-red .gaia-cross { stroke: var(--red) !important; }" in css


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
