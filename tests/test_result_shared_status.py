"""Result map shared-status and specified-time regression tests."""
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

from fastapi.testclient import TestClient

from app.catalog import catalog
from app.main import app


client = TestClient(app)
AT = "2026-09-16T16:00:00Z"
KEY = catalog.get(0).source_key


def _marker_class(svg: str, source_key: str) -> str:
    root = ET.fromstring(svg)
    for node in root.iter():
        if node.attrib.get("data-source-key") == source_key:
            return node.attrib.get("class", "")
    raise AssertionError(f"marker not found: {source_key}")


def test_result_template_has_one_shared_mode_and_specified_controls():
    response = client.post(
        "/result",
        data={
            "source_key": KEY, "source_index": KEY,
            "start_time": "2026-09-16T16:00:00Z", "end_time": "2026-09-16T17:00:00Z",
            "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0", "target_max_zenith_deg": "60",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    assert 'id="result-status-mode"' in response.text
    assert 'value="specified"' in response.text
    assert 'id="specified-time-kind"' in response.text
    assert 'id="specified-time-start"' in response.text
    assert 'id="specified-time-end"' in response.text
    assert 'id="local-fov-mode"' not in response.text
    assert 'id="local-fov-time"' not in response.text


def test_frontend_shares_trajectory_highlights_preserves_mode_and_reports_map_actions():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    result = (root / "app/templates/result.html").read_text(encoding="utf-8")
    css = (root / "app/static/styles.css").read_text(encoding="utf-8")
    local_refresh = js[js.index("const refreshLocal = async"):js.index("allSky.addEventListener('skyward:camera-change'")]
    assert "context.dataset.highlightIndexes" in local_refresh
    assert "params.set('highlight_indexes', context.dataset.highlightIndexes)" in local_refresh
    assert "skyward.pending-result-map-state" in js
    assert "sessionStorage.removeItem('skyward.pending-result-map-state')" in js
    assert "markerMapKind" in js and "setMapActionStatus(mapKind" in js
    assert result.count('data-map-action-status=') == 2
    assert "dialog-head-actions .secondary-button" in css and "white-space: nowrap" in css


def test_specified_point_and_range_contracts_apply_to_both_map_endpoints():
    common = {
        "at_time": AT, "catalog_tokens": "", "status_mode": "specified",
        "specified_kind": "point",
    }
    all_point = client.get("/api/v1/sky/current", params={**common, "selected_source_key": KEY})
    local_point = client.get("/api/v1/sky/local-fov", params={**common, "target_source_key": KEY})
    assert all_point.status_code == local_point.status_code == 200
    assert all_point.json()["status_mode"] == local_point.json()["status_mode"] == "specified"
    assert all_point.json()["specified_kind"] == local_point.json()["specified_kind"] == "point"

    end = "2026-09-17T16:00:00Z"
    range_params = {**common, "specified_kind": "range", "specified_end": end}
    all_range = client.get("/api/v1/sky/current", params={**range_params, "selected_source_key": KEY})
    local_range = client.get("/api/v1/sky/local-fov", params={**range_params, "target_source_key": KEY})
    assert all_range.status_code == local_range.status_code == 200
    assert all_range.json()["specified_end"] == end
    assert local_range.json()["display_time"] == AT

    too_long = {**range_params, "specified_end": "2026-09-17T16:00:01Z"}
    assert client.get("/api/v1/sky/current", params={**too_long, "selected_source_key": KEY}).status_code == 422
    assert client.get("/api/v1/sky/local-fov", params={**too_long, "target_source_key": KEY}).status_code == 422
    mixed = {**range_params, "trajectory_ranges": "[]"}
    assert client.get("/api/v1/sky/current", params={**mixed, "selected_source_key": KEY}).status_code == 422
    assert client.get("/api/v1/sky/local-fov", params={**mixed, "target_source_key": KEY}).status_code == 422


def test_instant_target_status_and_symbol_match_between_maps():
    all_sky = client.get("/api/v1/sky/current", params={
        "at_time": AT, "catalog_tokens": "1lhaaso", "selected_source_key": KEY,
    })
    local = client.get("/api/v1/sky/local-fov", params={
        "at_time": AT, "catalog_tokens": "1lhaaso", "target_source_key": KEY,
    })
    assert all_sky.status_code == local.status_code == 200
    all_class = _marker_class(all_sky.json()["svg"], KEY)
    local_class = _marker_class(local.json()["svg"], KEY)
    assert "selected-source" in all_class and "selected-source" in local_class
    for status in ("status-green", "status-yellow", "status-red"):
        assert (status in all_class) == (status in local_class)


def test_result_navigation_uses_snapshot_restore_and_read_only_source_dialog():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    js = (root / "app/static/app.js").read_text(encoding="utf-8")
    result = (root / "app/templates/result.html").read_text(encoding="utf-8")
    assert "skyward.result-page-cache.v1" in js
    assert "snapshotResultPage" in js
    assert "restoreCachedResultPage" in js
    assert "document.write(record.html)" in js
    assert "if (!restoredFromPageCache)" in js
    assert "gaiaSources" in js and "restoreCachedDynamicState" in js
    assert "apply(zoom,false);" in js
    assert "apply(1,false);" not in js
    assert "!resultPage && document.getElementById('planner-form')" in js
    assert "const isResultTarget = isResultTargetIdentity(sourceKey) || isResultTargetIdentity(data.index)" in js
    assert "dialogUseSource.hidden = isResultTarget ||" in js
    assert "dialogAddZenith.dataset.overlayAdded" in js
    assert "removeZenithOverlay" in js
    assert "local-map-heading-actions" in result
    assert 'class="local-fov-time-controls"' not in result
