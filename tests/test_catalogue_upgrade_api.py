"""Upgrade acceptance: original identity, table scope, pagination and Gaia bounds."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from urllib.parse import quote
import io

import pytest
from fastapi.testclient import TestClient

from app.catalog import CatalogCollection, catalog, installed_catalogue, resolve_source
from app.config import LACT_TELESCOPE
from app.main import app
from app.schemas import ConstraintSet, WindowRequest
from app.status import source_status
from app.windows import calculate_windows

client = TestClient(app)
MOMENT = datetime(2026, 9, 16, 16, tzinfo=timezone.utc)
ALL = "1lhaaso,fermi-fl16y,fermi-3fhl,tevcat"


def test_installed_counts_and_original_identity_stable_under_selection():
    options = client.get("/api/v1/catalogues").json()["catalogues"]
    assert {r["identifier"]: r.get("count") for r in options if not r.get("online")} == {
        "1lhaaso": 90, "fermi-fl16y": 7224, "fermi-3fhl": 1556, "tevcat": 363}
    gaia = next(row for row in options if row["identifier"] == "gaia-dr3")
    assert gaia["selection_scope"] == "result_local_fov_only"
    fl = installed_catalogue("fermi-fl16y")
    tv = installed_catalogue("tevcat")
    source = fl.sources[7223]
    for tables in ([fl], [tv, fl, catalog], [catalog, fl, tv]):
        row = CatalogCollection(tables).get(source.source_key)
        assert row.index == source.index
        assert row.source_key == "fermi-fl16y:" + source.original_id
    assert resolve_source(0) == catalog.get(0)
    assert resolve_source(source.source_key) == source


def test_complete_pagination_and_search_not_first_page_only():
    keys = []
    offset = 0
    while offset is not None:
        data = client.get("/api/v1/sources", params={"catalog_tokens": ALL, "limit": 2000, "offset": offset}).json()
        assert data["total"] == 9233
        assert data["offset"] == offset
        keys.extend(row["source_key"] for row in data["sources"])
        offset = data["next_offset"]
    assert len(keys) == len(set(keys)) == 9233
    late = installed_catalogue("fermi-fl16y").sources[-1]
    result = client.get("/api/v1/sources", params={"catalog_tokens": ALL, "q": late.original_id, "limit": 1}).json()
    assert result["sources"][0]["source_key"] == late.source_key


def test_explicit_empty_is_not_default_and_duplicate_tables_not_duplicate_sources():
    assert client.get("/api/v1/sources").json()["total"] == 90
    for params in ({"catalog_tokens": ""}, {"catalog_token": ""}, {"catalog_tokens": "gaia-dr3"}):
        assert client.get("/api/v1/sources", params=params).json()["total"] == 0
    assert client.get("/api/v1/sources", params={"catalog_tokens": "1lhaaso,1lhaaso"}).json()["total"] == 90


def test_detail_notes_resolved_from_original_table_even_when_overlay_excludes_target():
    row = installed_catalogue("fermi-3fhl").sources[-1]
    result = client.get("/api/v1/sources/" + quote(row.source_key, safe=""), params={"at_time": MOMENT.isoformat(), "catalog_tokens": "tevcat"})
    assert result.status_code == 200
    data = result.json()
    assert data["source_key"] == row.source_key
    assert data["notes"] == row.notes
    assert data["enrichment"] == row.notes
    numeric = client.get("/api/v1/sources/0", params={"at_time": MOMENT.isoformat(), "catalog_tokens": ""}).json()
    assert numeric["source_key"] == catalog.get(0).source_key


def test_source_detail_exposes_catalogue_units_for_frontend_rendering():
    tevcat = installed_catalogue("tevcat")
    tev_detail = client.get(
        "/api/v1/sources/" + quote(tevcat.sources[0].source_key, safe=""),
        params={"at_time": MOMENT.isoformat()},
    )
    assert tev_detail.status_code == 200
    assert tev_detail.json()["catalogue_units"]["reported_flux"] == "Crab"
    assert tev_detail.json()["catalogue_units"]["distance_mode_kpc"] == "kpc"
    fermi = installed_catalogue("fermi-3fhl")
    fermi_detail = client.get(
        "/api/v1/sources/" + quote(fermi.sources[0].source_key, safe=""),
        params={"at_time": MOMENT.isoformat()},
    )
    assert fermi_detail.status_code == 200
    assert fermi_detail.json()["catalogue_units"] == fermi.units


def test_target_local_comparison_and_windows_do_not_follow_overlay_selection():
    target = installed_catalogue("fermi-3fhl").sources[0]
    comparison = installed_catalogue("fermi-fl16y").sources[0]
    local = client.get("/api/v1/sky/local-fov", params={"target_source_key": target.source_key, "catalog_tokens": "", "at_time": MOMENT.isoformat()})
    assert local.status_code == 200
    assert local.json()["source"]["source_key"] == target.source_key
    overlay = client.get("/api/v1/windows/plot-overlay", params={"target_source_key": target.source_key, "comparison_source_key": comparison.source_key, "catalog_tokens": "", "start_time": MOMENT.isoformat(), "end_time": (MOMENT + timedelta(seconds=2)).isoformat()})
    assert overlay.status_code == 200
    assert overlay.json()["comparison_sources"][0]["source_key"] == comparison.source_key
    result = client.post("/api/v1/windows/calculate", json={"source_key": target.source_key, "catalog_tokens": "", "start_time": MOMENT.isoformat(), "end_time": (MOMENT + timedelta(seconds=2)).isoformat()})
    assert result.status_code == 200
    assert result.json()["source"]["source_key"] == target.source_key


def test_unknown_footprint_uses_point_source_fallback_without_promoting_provenance():
    unknown = next(s for s in installed_catalogue("fermi-fl16y").sources if not s.footprint_known)
    assert unknown.to_dict()["planning_radius_deg"] is None
    assert unknown.to_dict()["ext"] is None
    assert unknown.to_dict()["footprint_known"] is False
    assert unknown.to_dict()["warnings"] == ["point_source_fallback"]
    status = source_status(unknown, MOMENT, ConstraintSet())
    assert status.footprint_pass == status.center_pass
    assert "point_source_fallback" in status.reasons
    assert status.to_dict()["warnings"] == ["point_source_fallback"]
    result = calculate_windows(unknown, MOMENT, MOMENT + timedelta(seconds=2), ConstraintSet())
    payload = result.to_dict()
    assert payload["full_footprint_evaluated"] is False
    assert payload["footprint_assessment"] == "point_source_fallback"
    assert "point_source_fallback" in payload["warnings"]
    request = {"source_key": unknown.source_key, "start_time": MOMENT.isoformat(), "end_time": (MOMENT + timedelta(seconds=2)).isoformat()}
    data = client.post("/api/v1/windows/calculate", json=request).json()
    assert data["source"]["footprint_known"] is False
    assert data["source"]["planning_radius_deg"] is None
    assert "point_source_fallback" in data["warnings"]
    assert data["footprint_assessment"] == "point_source_fallback"
    detail = client.get("/api/v1/sources/" + quote(unknown.source_key, safe=""), params={"at_time": MOMENT.isoformat()}).json()
    assert "point_source_fallback" in detail["warnings"]
    assert "point_source_fallback" in detail["status"]["warnings"]


def test_basic_sky_never_queries_gaia(monkeypatch):
    import app.main as main
    monkeypatch.setattr(main, "query_gaia_stars", lambda *a, **k: pytest.fail("base sky must not call TAP"))
    response = client.get("/api/v1/sky/current", params={"at_time": MOMENT.isoformat(), "catalog_tokens": "gaia-dr3", "include_gaia": True})
    assert response.status_code == 200
    assert response.json()["gaia"]["deferred"] is True
    assert response.json()["sources"] == []
    zoomed = client.get("/api/v1/sky/current", params={"at_time": MOMENT.isoformat(), "catalog_tokens": "", "zoom": 1000, "bounds": "349,334,0.76,0.7", "display_frame": "j2000"})
    assert zoomed.status_code == 200
    assert zoomed.json()["grid_step_deg"] < response.json()["grid_step_deg"]
    assert client.get("/api/v1/sky/current", params={"at_time": MOMENT.isoformat(), "catalog_tokens": "", "bounds": "0,0,-1,2"}).status_code == 422


def test_single_xlsx_upload_numeric_identity_is_preserved_across_routes(xlsx_bytes):
    upload = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("legacy.xlsx", xlsx_bytes(["name", "ra", "dec"], [["OnlyRow", 83.633, 22.014], ["SecondRow", 84, 22]]), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    ).json()
    token = upload["token"]
    first, second = upload["sources"]
    detail = client.get("/api/v1/sources/0", params={"catalog_token": token, "at_time": MOMENT.isoformat()})
    assert detail.status_code == 200
    assert detail.json()["source_key"] == first["source_key"]
    assert detail.json()["ext_err"] is None and detail.json()["p_err(95%)"] is None
    assert client.get("/api/v1/sources/5", params={"catalog_token": token, "at_time": MOMENT.isoformat()}).status_code == 404
    # Plural explicit display selection never reinterprets the numeric target.
    plural = client.get("/api/v1/sources/0", params={"catalog_token": token, "catalog_tokens": "", "at_time": MOMENT.isoformat()}).json()
    assert plural["source_key"] == catalog.get(0).source_key
    keyed = client.get("/api/v1/sources/" + quote(catalog.get(0).source_key, safe=""), params={"catalog_token": token, "at_time": MOMENT.isoformat()}).json()
    assert keyed["source_key"] == catalog.get(0).source_key
    local = client.get("/api/v1/sky/local-fov", params={"catalog_token": token, "target_source_index": 0, "at_time": MOMENT.isoformat()})
    assert local.status_code == 200 and local.json()["source"]["source_key"] == first["source_key"]
    times = {"start_time": MOMENT.isoformat(), "end_time": (MOMENT + timedelta(seconds=2)).isoformat()}
    zenith = client.get("/api/v1/windows/zenith-overlay", params={**times, "catalog_token": token, "source_index": 0})
    assert zenith.status_code == 200 and zenith.json()["source"]["source_key"] == first["source_key"]
    plot = client.get("/api/v1/windows/plot-overlay", params={**times, "catalog_token": token, "target_source_index": 0, "comparison_source_index": 1})
    assert plot.status_code == 200 and plot.json()["comparison_sources"][0]["source_key"] == second["source_key"]
    windows = client.post("/api/v1/windows/calculate", json={**times, "catalog_token": token, "source_index": 0})
    assert windows.status_code == 200 and windows.json()["source"]["source_key"] == first["source_key"]
    form = client.post("/result", data={**times, "catalog_token": token, "source_index": "0", "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "0", "target_min_zenith_deg": "0", "target_max_zenith_deg": "90", "minimum_window_seconds": "0"})
    assert form.status_code == 200
    assert f'data-result-source-key="{first["source_key"]}"' in form.text


def test_nominal_override_survives_result_and_all_display_refreshes(monkeypatch):
    import app.main as main
    import xml.etree.ElementTree as ET
    target = next(source for source in installed_catalogue("tevcat").sources if not source.footprint_known and source_status(source, MOMENT, ConstraintSet()).center_pass)
    common = {"catalog_tokens": "tevcat", "nominal_radius_deg": 0.7}
    times = {"start_time": MOMENT.isoformat(), "end_time": (MOMENT + timedelta(seconds=2)).isoformat()}
    detail = client.get("/api/v1/sources/" + quote(target.source_key, safe=""), params={**common, "at_time": MOMENT.isoformat()}).json()
    assert detail["ext"] == 0.7 and detail["status"]["full_footprint_evaluated"]
    sky = client.get("/api/v1/sky/current", params={**common, "selected_source_key": target.source_key, "at_time": MOMENT.isoformat()}).json()
    selected = next(row for row in sky["sources"] if row["source_key"] == target.source_key)
    assert selected["ext"] == 0.7 and selected["footprint_kind"] == "operator_nominal_radius"
    local = client.get("/api/v1/sky/local-fov", params={**common, "target_source_key": target.source_key, "at_time": MOMENT.isoformat()}).json()
    root = ET.fromstring(local["svg"])
    marker = next(node for node in root.iter() if node.attrib.get("data-source-key") == target.source_key)
    assert any(node.attrib.get("data-angular-radius-deg") == "0.700000000" for node in marker.iter())
    seen = []
    calculate = main.calculate_windows
    def capture(source, *args, **kwargs):
        seen.append(source)
        return calculate(source, *args, **kwargs)
    monkeypatch.setattr(main, "calculate_windows", capture)
    plot = client.get("/api/v1/windows/plot-overlay", params={**times, **common, "target_source_key": target.source_key})
    assert plot.status_code == 200 and seen[-1].ext == 0.7
    contexts = []
    template_response = main.templates.TemplateResponse
    def capture_template(request, name, context, **kwargs):
        contexts.append(context)
        return template_response(request, name, context, **kwargs)
    monkeypatch.setattr(main.templates, "TemplateResponse", capture_template)
    form = client.post("/result", data={**times, **common, "source_key": target.source_key, "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "0", "target_min_zenith_deg": "0", "target_max_zenith_deg": "90", "minimum_window_seconds": "0"})
    assert form.status_code == 200
    assert contexts[-1]["source_detail"]["ext"] == 0.7
    snapshot_source = next(row for row in contexts[-1]["snapshot"]["sources"] if row["source_key"] == target.source_key)
    assert snapshot_source["ext"] == 0.7
    assert target.planning_radius_deg is None  # override never mutates original table


def test_unknown_footprint_point_source_fallback_does_not_claim_extension_duration():
    target = next(source for source in installed_catalogue("tevcat").sources if not source.footprint_known and source_status(source, MOMENT, ConstraintSet()).center_pass)
    for duration in (0, 120):
        status = source_status(target, MOMENT, ConstraintSet(minimum_window_seconds=duration))
        assert "point_source_fallback" in status.reasons
        assert status.footprint_pass == status.center_pass
        assert not any(reason.startswith("extension_") for reason in status.reasons)


def test_windows_provenance_hash_follows_target_or_bulk_selection():
    table = installed_catalogue("fermi-3fhl")
    times = {"start_time": MOMENT.isoformat(), "end_time": (MOMENT + timedelta(seconds=1)).isoformat()}
    single = client.post("/api/v1/windows/calculate", json={**times, "source_key": table.sources[0].source_key, "catalog_tokens": "1lhaaso"}).json()
    assert single["catalogue_sha256"] == table.sha256
    assert single["catalogue_sha256"] != catalog.sha256
    bulk = client.post("/api/v1/windows/calculate", json={**times, "all_sources": True, "catalog_tokens": ""}).json()
    assert bulk["catalogue_sha256"] == CatalogCollection([]).sha256
    assert bulk["catalogues"] == []
    custom = client.post("/api/v1/windows/calculate", json={**times, "region_ra_deg": 10, "region_dec_deg": 20, "region_radius_deg": 0.1}).json()
    assert custom["catalogue_sha256"] is None


def test_unpublished_2lhaaso_name_is_reserved_for_temporary_uploads(xlsx_bytes):
    payload = xlsx_bytes(["name", "ra", "dec"], [["JTEST", 10, 20]])
    for filename in ("2LHAASO.xlsx", "2-LHAASO private.xlsx", "2_lhaaso-copy.xlsx"):
        response = client.post(
            "/api/v1/catalogues/upload",
            files={"file": (filename, payload, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 422
        assert "reserved unpublished 2LHAASO name" in response.json()["detail"]


def test_uploaded_slash_identity_details_and_name_length_validation(xlsx_bytes):
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("slash.xlsx", xlsx_bytes(["name", "ra", "dec"], [["A/B", 10, 20]]), mime)},
    )
    assert response.status_code == 200
    key = response.json()["sources"][0]["source_key"]
    detail = client.get("/api/v1/sources/" + quote(key, safe=""), params={"at_time": MOMENT.isoformat()})
    assert detail.status_code == 200 and detail.json()["source_key"] == key
    for length, expected in ((80, 200), (81, 422)):
        upload = client.post(
            "/api/v1/catalogues/upload",
            files={"file": ("length.xlsx", xlsx_bytes(["name", "ra", "dec"], [["N" * length, 10, 20]]), mime)},
        )
        assert upload.status_code == expected


def test_upload_rejects_non_xlsx_and_invalid_workbook():
    not_xlsx = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("legacy.csv", b"name,ra,dec\nA,10,20\n", "text/csv")},
    )
    assert not_xlsx.status_code == 422
    assert ".xlsx" in not_xlsx.json()["detail"]
    invalid = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("broken.xlsx", b"not-a-workbook", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert invalid.status_code == 422
    assert "valid .xlsx workbook" in invalid.json()["detail"]


def test_target_list_xlsx_requires_extension_and_preserves_row_constraints(xlsx_bytes):
    mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    missing = client.post(
        "/api/v1/target-lists/upload",
        files={"file": ("missing.xlsx", xlsx_bytes(["name", "ra", "dec", "ext"], [["No radius", 10, 20, None]]), mime)},
    )
    assert missing.status_code == 422
    assert "provide ext" in missing.json()["detail"]
    valid = client.post(
        "/api/v1/target-lists/upload",
        files={"file": ("targets.xlsx", xlsx_bytes(
            ["name", "ra", "dec", "ext", "target_max_zenith_deg", "minimum_window_seconds"],
            [["Target A", 10, 20, 0.3, 55, 1200], ["Target B", 11, 21, 0.0, None, None]],
        ), mime)},
    )
    assert valid.status_code == 200
    payload = valid.json()
    assert payload["target_list"] is True and payload["count"] == 2
    assert payload["sources"][0]["planner_constraints"] == {"target_max_zenith_deg": 55.0, "minimum_window_seconds": 1200.0}
    assert payload["sources"][1]["planner_constraints"] is None


def test_gaia_api_error_is_not_zero(monkeypatch):
    import app.main as main
    from app.gaia import GaiaQueryError
    def fail(*args, **kwargs):
        raise GaiaQueryError("offline")
    monkeypatch.setattr(main, "query_gaia_stars", fail)
    data = client.get("/api/v1/gaia", params={"target_ra_deg": 20, "target_dec_deg": 30}).json()
    assert data["error"] == "offline" and data["zero"] is False and data["count"] == 0
    assert data["gaia"]["status"] == "error" and data["gaia"]["error_reason"] == "offline"
    assert client.get("/api/v1/gaia", params={"target_ra_deg": 20}).status_code == 422
    assert client.get("/api/v1/gaia", params={"limit": 2001}).status_code == 422


def test_gaia_limit_cache_byte_and_concurrency_bounds(monkeypatch):
    import app.gaia as gaia
    gaia._CACHE.clear()
    payload = b"source_id,ra,dec,parallax,parallax_error,pmra,pmra_error,pmdec,pmdec_error,phot_g_mean_mag,phot_bp_mean_mag,phot_rp_mean_mag,bp_rp,ruwe,visibility_periods_used\n3403822609273809792,10,20,2,0.1,1,0.1,2,0.1,12,12.5,11.5,1,1.1,12\n3403818623544184064,10.01,20.01,,,,,,,,13,,,,,\n"
    class Response(io.BytesIO):
        pass
    monkeypatch.setattr(gaia, "urlopen", lambda *a, **k: Response(payload))
    rows, meta = gaia.query_gaia_stars(MOMENT, LACT_TELESCOPE, .1, 1, 10, 10, 20)
    assert meta["truncated"] and not meta["cached"] and meta["bytes"] == len(payload)
    assert rows[0].original_id == "3403822609273809792"
    assert rows[0].notes["proper_motion_applied"] is False
    assert rows[0].notes["query_fields"]["parallax_mas"] == 2
    assert rows[0].notes["distance"]["inverse_parallax_distance_pc"] == 500
    assert gaia.query_gaia_stars(MOMENT, LACT_TELESCOPE, .1, 1, 10, 10, 20)[1]["cached"]
    monkeypatch.setattr(gaia, "MAX_CACHE_ENTRIES", 2)
    for ra in (11, 12, 13):
        gaia.query_gaia_stars(MOMENT, LACT_TELESCOPE, .1, 1, 10, ra, 20)
    assert len(gaia._CACHE) == 2
    monkeypatch.setattr(gaia, "MAX_RESPONSE_BYTES", 10)
    with pytest.raises(gaia.GaiaQueryError, match="byte limit"):
        gaia.query_gaia_stars(MOMENT, LACT_TELESCOPE, .1, 1, 10, 14, 20)
    assert gaia._QUERY_SLOTS.acquire(False)
    assert gaia._QUERY_SLOTS.acquire(False)
    try:
        with pytest.raises(gaia.GaiaQueryError, match="concurrency"):
            gaia.query_gaia_stars(MOMENT, LACT_TELESCOPE, .1, 1, 10, 15, 20)
    finally:
        gaia._QUERY_SLOTS.release()
        gaia._QUERY_SLOTS.release()
        gaia._CACHE.clear()
