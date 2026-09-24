"""Acceptance tests for persistent XLSX plans, alternatives, and safe result URLs."""
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.alternatives import metric_sort_key, window_metrics
from app.main import app


ROOT = Path(__file__).resolve().parents[1]
CLIENT = TestClient(app)


def test_window_ranking_prefers_overlap_then_gap_duration_and_stable_key():
    target_start = datetime(2026, 9, 22, 1, tzinfo=timezone.utc)
    target_end = datetime(2026, 9, 22, 2, tzinfo=timezone.utc)
    overlap = window_metrics(target_start, target_end, target_start, target_end)
    near = window_metrics(
        target_start, target_end,
        datetime(2026, 9, 22, 2, 10, tzinfo=timezone.utc),
        datetime(2026, 9, 22, 3, 10, tzinfo=timezone.utc),
    )
    far = window_metrics(
        target_start, target_end,
        datetime(2026, 9, 22, 3, tzinfo=timezone.utc),
        datetime(2026, 9, 22, 4, tzinfo=timezone.utc),
    )
    assert overlap["overlap_seconds"] == 3600
    assert near["gap_seconds"] == 600
    assert metric_sort_key(overlap, "z") < metric_sort_key(near, "a") < metric_sort_key(far, "a")
    assert metric_sort_key(overlap, "a") < metric_sort_key(overlap, "z")


def test_alternative_endpoint_returns_real_ranked_catalogue_sources_without_pointing_constraint():
    target = CLIENT.get(
        "/api/v1/sources", params={"catalog_tokens": "1lhaaso", "limit": 1}
    ).json()["sources"][0]
    response = CLIENT.post(
        "/api/v1/windows/alternatives",
        json={
            "source_key": target["source_key"],
            "catalog_tokens": "1lhaaso",
            "search_start": "2026-09-22T00:00:00Z",
            "search_end": "2026-09-22T03:00:00Z",
            "target_window_start": "2026-09-22T00:30:00Z",
            "target_window_end": "2026-09-22T01:30:00Z",
            "constraints": {},
            "max_alternatives": 3,
            "coarse_step_seconds": 900,
            "shortlist_limit": 8,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["pointing_constraint_applied"] is False
    assert len(data["alternatives"]) == 3
    assert [row["rank"] for row in data["alternatives"]] == [1, 2, 3]
    assert all(row["source"]["source_key"] != target["source_key"] for row in data["alternatives"])
    assert all(row["source"]["source_type"] != "gaia" for row in data["alternatives"])
    assert all(row["selection_stage"] == "coarse_then_exact_local" for row in data["alternatives"])
    assert all(row["pointing_constraint_applied"] is False for row in data["alternatives"])
    assert all("overlap_seconds" in row["metrics"] and "gap_seconds" in row["metrics"] for row in data["alternatives"])
    assert data["search_summary"]["shortlist_count"] <= 8
    assert data["search_summary"]["returned_count"] == 3


def test_uploaded_alternative_catalogue_is_exclusive_candidate_pool(monkeypatch):
    import app.main as main

    upload = CLIENT.post(
        "/api/v1/catalogues/upload",
        files={"file": ("dedicated.csv", b"name,ra,dec\nOnlyAlt,84,22\n", "text/csv")},
    )
    assert upload.status_code == 200, upload.text
    token = upload.json()["token"]
    target = CLIENT.get("/api/v1/sources", params={"catalog_tokens": "1lhaaso", "limit": 1}).json()["sources"][0]
    captured = {}

    def fake_find(candidates, target_source, *args, **kwargs):
        captured["candidates"] = list(candidates)
        return {
            "alternatives": [],
            "search_summary": {"shortlist_count": 0, "returned_count": 0},
            "pointing_constraint_applied": False,
        }

    monkeypatch.setattr(main, "find_alternatives", fake_find)
    response = CLIENT.post(
        "/api/v1/windows/alternatives",
        json={
            "source_key": target["source_key"],
            "catalog_tokens": "1lhaaso",
            "alternative_catalog_token": token,
            "search_start": "2026-09-22T00:00:00Z",
            "search_end": "2026-09-22T01:00:00Z",
            "target_window_start": "2026-09-22T00:10:00Z",
            "target_window_end": "2026-09-22T00:20:00Z",
            "constraints": {},
            "max_alternatives": 3,
            "coarse_step_seconds": 900,
            "shortlist_limit": 8,
        },
    )
    assert response.status_code == 200, response.text
    assert [source.name for source in captured["candidates"]] == ["OnlyAlt"]
    data = response.json()
    assert data["candidate_scope"] == "uploaded_alternative_catalogue"
    assert data["candidate_catalogues"][0]["token"] == token
    assert data["catalogues"][0]["identifier"] == "1lhaaso"


def _result_params(nominal_radius_deg):
    return {
        "source_index": "0",
        "nominal_radius_deg": nominal_radius_deg,
        "start_time": "2026-09-22T00:00:00Z",
        "end_time": "2026-09-22T00:00:02Z",
        "display_timezone": "utc",
        "sun_max_altitude_deg": "-18",
        "moon_min_separation_deg": "30",
        "target_min_zenith_deg": "0",
        "target_max_zenith_deg": "60",
        "minimum_window_seconds": "0",
        "telescope_mode": "lact",
    }


def test_result_get_accepts_empty_nominal_radius_but_rejects_invalid_nonempty_value():
    empty = CLIENT.get("/result", params=_result_params(""))
    assert empty.status_code == 200, empty.text
    assert 'id="detail-query-context"' in empty.text
    invalid = CLIENT.get("/result", params=_result_params("not-a-number"))
    assert invalid.status_code == 422
    detail = invalid.json()["detail"][0]
    assert detail["loc"] == ["query", "nominal_radius_deg"]
    assert detail["input"] == "not-a-number"


def test_frontend_persists_all_entries_previews_and_exports_xlsx_plus_both_saved_svgs():
    js = (ROOT / "app/static/app.js").read_text(encoding="utf-8")
    result = (ROOT / "app/templates/result.html").read_text(encoding="utf-8")
    base = (ROOT / "app/templates/base.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/styles.css").read_text(encoding="utf-8")
    assert 'const storageKey = "skyward.observation-plan.v3"' in js
    assert 'sessionStorage.removeItem("skyward.observation-plan.v2")' in js
    assert "stored?.version === 3" in js
    assert "JSON.stringify({ version: 3, entries: planEntries })" in js
    assert "data-plan-edit" in js and "data-plan-delete" in js
    assert "data-clear-observation-plan" in base
    assert "name: 'skyward-observing-plan.xlsx'" in js
    assert "skyward-observing-plan.csv" not in js
    assert "skyward-observing-plan.txt" not in js
    assert 'record_type", "plan_entry", "window_number", "target_source"' in js
    assert 'window_plot_file", "local_fov_file' in js
    assert '"alternative", index + 1, windowIndex + 1' in js
    assert 'entry.windows.forEach((window, windowIndex)' in js
    assert 'const buildXlsxFiles = () => {' in js
    assert "xl/worksheets/sheet1.xml" in js and "xl/styles.xml" in js
    assert "localFovSvg:" in js
    assert "export-background" in js and "export-source-id" in js and "export-source-legend" in js
    assert "data-source-name" in (ROOT / "app/sky_map.py").read_text(encoding="utf-8")
    assert '"-observing-window.svg"' in js and '"-local-fov.svg"' in js
    assert 'window.alternativeStatus === "pending"' in js
    assert "XLSX includes them" in js
    assert "/api/v1/windows/alternatives?" in js
    assert "coarse_step_seconds: 900" in js and "shortlist_limit: 8" in js
    assert "if (value.trim() === '') return;" in js
    navigation = js[js.index("const initialiseNavigationContext"):js.index("const initialiseCalculationSubmission")]
    assert "window.location.assign(parsed.href);" in navigation
    assert "window.location.assign(parsed.href); sessionStorage.removeItem(key)" not in navigation
    assert result.count("data-preview-observation-plan") == 1
    assert result.count("data-download-observation-plan") == 1
    assert result.count("data-plan-window data-i18n") == 1
    full_windows = result[result.index('class="windows-panel emphasized"'):result.index("{% if source_detail %}")]
    assert full_windows.index('class="full-windows-heading-actions"') < full_windows.index('class="window-list"')
    assert full_windows.count('class="plan-window-actions"') == 1
    assert "class=\"local-gaia-filter-controls compact-gaia-filter-controls\"" in result
    assert ".compact-gaia-filter-controls input, .compact-gaia-filter-controls .secondary-button { min-height: 34px; height: 34px; }" in css
    assert ".full-windows-heading-actions .plan-window-actions .plan-action-button { flex: 0 1 108px; width: 108px;" in css
    assert "data-plan-window-select" in result and "checked" in result
    assert "data-plan-alternative-status" in result
    assert 'id="observation-plan-preview-dialog"' in base
    assert 'id="plan-window-editor"' in base
    assert "data-close-plan-preview" in base
    assert ".gaia-cross" in css and "stroke-width: 2.8" in css
    assert ".plan-window-actions .plan-action-button { font-family: var(--font-sans); }" in css
    assert ".plan-window-actions [data-download-observation-plan]" not in css
    assert 'font: 800 12px/1.2 var(--font-sans)' in css
    assert '<fills count="5">' in js
    assert 'patternType="gray125"' in js
    assert 'fgColor rgb="FF000000"' in js and 'bgColor rgb="FF000000"' in js
    assert 'fgColor rgb="FFFFFF99"' in js and 'bgColor rgb="FFFFFF99"' in js
    assert 'fgColor rgb="FFC6EFCE"' in js and 'bgColor rgb="FFC6EFCE"' in js
    assert 'fontId="1" fillId="2"' in js
    assert 'fontId="0" fillId="3"' in js
    assert 'fontId="0" fillId="4"' in js
    assert "const rowStyle = rowIndex === 0 ? 1 : row[0] === 'target' ? 2 : row[0] === 'alternative' ? 3 : 0;" in js
    assert 'data-clear-observation-plan' in base
    assert 'data-plan-edit' in js and 'data-plan-delete' in js
