from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import MAX_CALCULATION_DAYS
from app.main import _parse_form_datetime, app

client = TestClient(app)


def test_planner_duration_limit_matches_second_resolution_capacity():
    assert MAX_CALCULATION_DAYS == 30
    home = client.get("/")
    assert 'Maximum 30 days' in home.text
    too_long = client.post(
        "/api/v1/windows/calculate",
        json={
            "source_index": 11,
            "start_time": "2026-12-15T10:00:00Z",
            "end_time": "2027-01-14T10:00:01Z",
            "constraints": {"minimum_window_seconds": 0},
        },
    )
    assert too_long.status_code == 422
    assert "cannot exceed 30 days" in too_long.text


def test_health_and_config_expose_provenance_and_scope_boundaries():
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    data = health.json()
    assert data["status"] == "ok"
    assert data["catalogue"]["rows"] == 90
    assert data["iers"]["covers_current_time"] is True

    config = client.get("/api/v1/config").json()
    assert config["fov_diameter_deg"] == 8.3
    assert config["fov_radius_deg"] == 4.15
    assert config["geometry_only"] is True
    assert config["joint_observation_evaluated"] is False
    assert config["weather_evaluated"] is False
    assert config["telemetry_evaluated"] is False


def test_source_list_search_and_detail_contract():
    response = client.get("/api/v1/sources", params={"q": "J0634+1741u"})
    assert response.status_code == 200
    assert response.json()["sources"][0]["display_name"] == "1LHAASO J0634+1741u"

    detail = client.get(
        "/api/v1/sources/11", params={"at_time": "2026-12-15T16:00:00Z"}
    )
    assert detail.status_code == 200
    data = detail.json()
    assert data["coordinate_frame"] == "FK5 J2000"
    assert data["display_name"].startswith("1LHAASO ")
    assert "p_err(95%)" in data
    assert data["enrichment"]["published_name"].startswith("1LHAASO ")
    assert len(data["enrichment"]["components"]) == 2
    assert "r39" in data["enrichment"]["scientific_boundary"]
    assert data["geometry_only"] is True


def test_unknown_source_and_invalid_query_are_clean_errors():
    assert client.get("/api/v1/sources/999").status_code == 404
    assert client.get("/api/v1/sources/90").status_code == 404
    assert client.get("/api/v1/sources", params={"limit": 2001}).status_code == 422
    invalid_range = {"target_min_zenith_deg": 70, "target_max_zenith_deg": 20}
    assert client.get("/api/v1/sources/11", params=invalid_range).status_code == 422
    assert client.get("/api/v1/sky/current", params=invalid_range).status_code == 422


def test_sky_api_has_clickable_stable_source_ids_and_counts():
    response = client.get(
        "/api/v1/sky/current",
        params={"at_time": "2026-12-15T16:00:00Z", "selected_source_index": 11},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["sources"]) == 90
    assert data["visible_source_count"] + data["below_horizon_source_count"] == 90
    assert 'data-source-index="11"' in data["svg"]
    # English is the documented API default. Labels are selected explicitly
    # through language=zh for the Chinese UI, not inferred from the browser.
    assert "Horizon" in data["svg"]
    # Bodies below the horizon are deliberately omitted from the map.
    assert "sun" not in data["svg"].lower() and "moon" not in data["svg"].lower()


def test_window_api_returns_center_and_full_windows_with_traceability():
    payload = {
        "source_index": 11,
        "start_time": "2026-12-15T10:00:00Z",
        "end_time": "2026-12-16T10:00:00Z",
        "constraints": {
            "sun_max_altitude_deg": -18,
            "target_max_zenith_deg": 50,
            "minimum_window_seconds": 1800,
        },
    }
    response = client.post("/api/v1/windows/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["center_windows"]) == 1
    assert len(data["full_footprint_windows"]) == 1
    assert data["catalogue_sha256"]
    assert data["geometry_only"] is True
    assert data["fov_diameter_deg"] == 8.3


def test_window_api_validates_time_order_and_extra_fields():
    bad = {
        "source_index": 11,
        "start_time": "2026-12-16T10:00:00Z",
        "end_time": "2026-12-15T10:00:00Z",
        "constraints": {},
    }
    assert client.post("/api/v1/windows/calculate", json=bad).status_code == 422
    bad["end_time"] = "2026-12-17T10:00:00Z"
    bad["unexpected"] = True
    assert client.post("/api/v1/windows/calculate", json=bad).status_code == 422


def test_out_of_range_IERS_times_are_rejected_consistently():
    future = "2030-01-01T00:00:00Z"
    assert client.get("/api/v1/sources/11", params={"at_time": future}).status_code == 422
    assert client.get("/api/v1/sky/current", params={"at_time": future}).status_code == 422
    payload = {
        "source_index": 11,
        "start_time": future,
        "end_time": "2030-01-01T01:00:00Z",
        "constraints": {},
    }
    assert client.post("/api/v1/windows/calculate", json=payload).status_code == 422

def test_skyward_display_controls_and_bilingual_assets_are_local():
    """Branding, translations and theme preferences must not need a CDN."""
    root = client.get("/")
    assert root.status_code == 200
    assert "SKYWARD" in root.text
    assert 'id="language-select"' in root.text
    assert 'id="theme-toggle"' in root.text
    assert 'data-i18n="homeTitle"' in root.text
    assert "https://" not in root.text

    about = client.get("/about")
    api_reference = client.get("/api/v1")
    assert 'data-i18n="aboutTitle"' in about.text
    assert 'data-i18n="apiTitle"' in api_reference.text

    project_root = Path(__file__).resolve().parents[1]
    script = (project_root / "app" / "static" / "app.js").read_text(encoding="utf-8")
    stylesheet = (project_root / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    assert 'skyward.theme' in script and 'skyward.language' in script
    assert 'translations' in script and 'theme-toggle' in script
    assert '#3333FF' in stylesheet
    assert '[data-theme="dark"]' in stylesheet


    home = client.get("/")
    assert home.status_code == 200
    assert "/static/styles.css" in home.text
    assert "https://" not in home.text
    assert "SKYWARD" in home.text
    assert "LACT all-sky view" in home.text
    assert 'id="language-select"' in home.text
    assert 'id="theme-toggle"' in home.text

    api_reference = client.get("/api/v1")
    assert api_reference.status_code == 200
    assert "/openapi.json" in api_reference.text
    assert "https://" not in api_reference.text
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 200

    about = client.get("/about")
    assert about.status_code == 200
    assert "8.3°" in about.text
    assert "Data, coordinates and geometry" in about.text
    assert 'data-i18n="aboutTitle"' in about.text

    result = client.post(
        "/result",
        data={
            "source_index": "11",
            "start_time": "2026-12-15T18:00",
            "end_time": "2026-12-16T18:00",
            "sun_max_altitude_deg": "-18",
            "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "50",
            "minimum_window_seconds": "1800",
        },
    )
    assert result.status_code == 200
    assert "10°" in result.text
    assert "LACT FoV 8.30°" in result.text
    assert 'data-i18n="localFovTitle"' in result.text
    assert 'id="local-fov-gaia-toggle"' not in result.text
    assert 'id="local-gaia-filter-apply"' in result.text
    assert 'value="10"' in result.text
    assert "Full-footprint windows" in result.text
    assert 'data-i18n="fullWindows"' in result.text
    assert "extension-ring" in result.text
    assert 'id="detail-query-context"' in result.text
    assert 'data-at-time="2026-12-15T10:00:00Z"' in result.text
    assert 'data-sun-max-altitude-deg="-18.0"' in result.text
    assert 'data-target-max-zenith-deg="50.0"' in result.text
    assert 'data-minimum-window-seconds="1800"' in result.text

def test_html_planner_rejects_blank_required_constraints():
    """The UI says every planning field is required; server validation agrees."""
    response = client.post(
        "/result",
        data={
            "source_index": "11",
            "start_time": "2026-12-15T18:00",
            "end_time": "2026-12-15T19:00",
            "sun_max_altitude_deg": "-18",
            "moon_min_separation_deg": "",
            "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "60",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 422
    assert "all planning constraints must be supplied" in response.text


def test_result_page_uses_moon_separation_for_both_window_columns():
    response = client.post(
        "/result",
        data={
            "source_index": "11", "start_time": "2026-12-15T18:00", "end_time": "2026-12-16T18:00",
            "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30", "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "60", "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    assert response.text.count('data-i18n="minimumMoonSeparation"') == 2
    assert 'data-i18n="maximumSunAltitude"' not in response.text



def test_sky_map_exposes_fixed_zenith_realtime_fov_and_body_panel_data():
    response = client.get(
        "/api/v1/sky/current", params={"at_time": "2026-12-15T16:00:00Z"}
    )
    assert response.status_code == 200
    data = response.json()
    assert 'class="realtime-fov-ring"' in data["svg"]
    assert "LACT FoV 8.3°" not in data["svg"]
    assert 'class="telescope-label"' not in data["svg"]
    assert 'class="realtime-fov-label"' in data["svg"]
    assert data["lact_pointing"]["mode"] == "fixed_zenith_pending_telemetry"
    assert data["lact_pointing"]["altitude_deg"] == 90.0
    assert set(data["sun"]) == {"altitude_deg", "azimuth_deg"}
    assert set(data["moon"]) == {"altitude_deg", "azimuth_deg"}
    assert "Horizon" in data["svg"]
    chinese = client.get("/api/v1/sky/current", params={"at_time": "2026-12-15T16:00:00Z", "language": "zh"}).json()
    assert "地平线" in chinese["svg"]


def test_planner_defaults_constraints_and_supports_region_and_legacy_current_fov_api():
    home = client.get("/")
    assert home.status_code == 200
    for expected in ('value="-18"', 'value="30"', 'value="0"', 'value="60"', 'value="0"', 'max="-15"'):
        assert expected in home.text
    assert 'value="none"' not in home.text
    assert 'value="region"' in home.text
    assert 'data-i18n="addTargetOption"' in home.text
    assert 'id="region_name"' in home.text
    assert 'id="sky-mode"' in home.text
    assert 'id="sun-coordinates"' in home.text

    region = client.post(
        "/result",
        data={
            "source_index": "region", "region_name": "", "region_ra_deg": "83.633", "region_dec_deg": "22.014", "region_radius_deg": "1.0",
            "start_time": "2026-12-15T18:00", "end_time": "2026-12-16T18:00",
            "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30", "target_min_zenith_deg": "0", "target_max_zenith_deg": "60", "minimum_window_seconds": "0",
        },
    )
    assert region.status_code == 200
    assert "TMP J0534+2200" in region.text
    assert 'data-plan-source-name="TMP J0534+2200"' in region.text

    current_fov = client.post(
        "/api/v1/windows/calculate",
        json={
            "all_sources": True, "start_time": "2026-12-15T10:00:00Z", "end_time": "2026-12-15T11:00:00Z",
            "constraints": {"sun_max_altitude_deg": -18, "moon_min_separation_deg": 30, "target_min_zenith_deg": 0, "target_max_zenith_deg": 60, "minimum_window_seconds": 0},
        },
    )
    assert current_fov.status_code == 200
    payload = current_fov.json()
    assert payload["target_mode"] == "current_lact_fov_fixed_zenith"
    assert payload["pointing"]["altitude_deg"] == 90.0




def test_custom_target_name_and_result_ui_contract():
    """Transient targets retain a chosen name and expose local-only plan controls."""
    response = client.post(
        "/result",
        data={
            "source_index": "region", "region_name": "TMP Crab follow-up",
            "region_ra_deg": "83.633", "region_dec_deg": "22.014", "region_radius_deg": "0.6",
            "start_time": "2026-12-15T18:00", "end_time": "2026-12-16T18:00",
            "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0", "target_max_zenith_deg": "60", "minimum_window_seconds": "0",
            "display_theme": "light", "display_timezone": "local", "planner_start_utc": "", "planner_end_utc": "",
        },
    )
    assert response.status_code == 200
    assert "TMP Crab follow-up" in response.text
    assert 'data-plan-source-name="TMP Crab follow-up"' in response.text
    assert 'id="observation-plan-dialog"' in response.text
    assert 'data-plan-window' in response.text
    assert 'id="timezone-select"' in response.text
    assert 'id="result-display-preferences"' in response.text


def test_result_markup_only_offers_plan_button_for_physically_valid_seconds():
    response = client.post(
        "/result",
        data={
            "source_index": "region",
            "region_name": "TMP boundary",
            "region_ra_deg": "34.485",
            "region_dec_deg": "29.230",
            "region_radius_deg": "0.001",
            "start_time": "2026-12-15T22:00:00",
            "end_time": "2026-12-15T22:03:00",
            "display_timezone": "local",
            "sun_max_altitude_deg": "-18",
            "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "0.5",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    # Any offered planner payload must carry non-empty, explicit valid bounds.
    if "data-plan-window" in response.text:
        assert 'data-plan-start=""' not in response.text
        assert 'data-plan-end=""' not in response.text


def test_legacy_bulk_result_keeps_explicit_utc_range_for_source_replacement():
    response = client.post(
        "/result",
        data={
            "source_index": "none",
            "start_time": "2026-12-15T18:00",
            "end_time": "2026-12-15T19:00",
            "display_timezone": "local",
            "sun_max_altitude_deg": "-18",
            "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "60",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    # Replacement requests must use these canonical instants even after the
    # browser switches its display preference from Beijing time to UTC.
    assert 'data-result-time-context' in response.text
    assert 'data-start-utc="2026-12-15T10:00:00Z"' in response.text
    assert 'data-end-utc="2026-12-15T11:00:00Z"' in response.text
    assert 'data-time-display="range"' in response.text


def test_result_form_handles_utc_z_refresh_and_preserves_display_preference():
    """A result refresh must be valid on Python 3.9 and keep ``auto`` intact."""
    response = client.post(
        "/result",
        data={
            "source_index": "11",
            "start_time": "2026-12-15T10:00:00Z",
            "end_time": "2026-12-16T10:00:00Z",
            "display_theme": "auto",
            "plot_theme": "dark",
            "display_timezone": "utc",
            "sun_max_altitude_deg": "-18",
            "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "60",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    assert 'data-theme="auto"' in response.text
    assert 'data-plot-theme="dark"' in response.text
    assert 'name="plot_theme" value="dark"' in response.text
    assert "#0c1117" in response.text.lower()


def test_form_datetime_accepts_z_on_python_39_and_honours_selected_zone():
    assert _parse_form_datetime("2026-12-15T10:00:00Z", "utc") == datetime(2026, 12, 15, 10, tzinfo=timezone.utc)
    assert _parse_form_datetime("2026-12-15T18:00", "local").astimezone(timezone.utc) == datetime(2026, 12, 15, 10, tzinfo=timezone.utc)
    assert _parse_form_datetime("2026-12-15T10:00", "utc") == datetime(2026, 12, 15, 10, tzinfo=timezone.utc)


def test_planner_validation_rerender_preserves_canonical_utc_and_custom_name():
    response = client.post(
        "/result",
        data={
            "source_index": "region",
            "region_name": "TMP operator chosen name",
            "region_ra_deg": "83.633",
            "region_dec_deg": "22.014",
            "region_radius_deg": "0.6",
            "start_time": "2026-12-15T10:00",
            "end_time": "2026-12-16T10:00",
            "display_theme": "auto",
            "display_timezone": "utc",
            "sun_max_altitude_deg": "-18",
            "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "70",
            "target_max_zenith_deg": "20",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 422
    assert 'id="planner-start-utc" value="2026-12-15T10:00:00Z"' in response.text
    assert 'id="planner-end-utc" value="2026-12-16T10:00:00Z"' in response.text
    assert 'value="TMP operator chosen name"' in response.text


def test_frontend_timezone_and_observation_plan_regressions_are_guarded():
    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    base = (Path(__file__).resolve().parents[1] / "app" / "templates" / "base.html").read_text(encoding="utf-8")
    assert "skyward:timezone-will-change" in script
    assert "planner-start-utc" in script and "planner-end-utc" in script
    assert "localDatetimeValue(new Date(iso), displayTimezone(), true)" in script
    assert 'id="plan-window-editor"' in base
    assert 'start.step = "1"' in script and 'endInput.step = "1"' in script
    theme_block = script[script.index("const initialiseResultThemePlot"):script.index("const initialiseSourceDialog")]
    assert "recolourPlot" in theme_block
    assert "requestSubmit" not in theme_block and "fetch(" not in theme_block


    from app.catalog import catalog
    from app.plotting import render_window_plot
    from app.schemas import ConstraintSet
    from app.targets import temporary_target_name
    from app.windows import calculate_windows

    assert temporary_target_name(83.633, 22.014) == "TMP J0534+2200"
    result = calculate_windows(
        catalog.get(11),
        datetime(2026, 12, 15, 10, tzinfo=timezone.utc),
        datetime(2026, 12, 15, 12, tzinfo=timezone.utc),
        ConstraintSet(sun_max_altitude_deg=-18, target_max_zenith_deg=60),
    )
    light = render_window_plot(result, theme="light", timezone_label="UTC")
    dark = render_window_plot(result, theme="dark", timezone_label="Beijing UTC+8")
    assert "#ffffff" in light.lower()
    assert "#0c1117" in dark.lower()
    overlay = render_window_plot(result, timezone_label="UTC", zenith_overlays=[(999, "Comparison source", result.series.target_zenith_deg, "#ff0000", "dashdot")])
    assert "Comparison source" in overlay and "Target zenith" in overlay
    assert "matplotlib.org" not in light

    too_bright = {
        "source_index": 11, "start_time": "2026-12-15T10:00:00Z", "end_time": "2026-12-15T11:00:00Z",
        "constraints": {"sun_max_altitude_deg": -14},
    }
    assert client.post("/api/v1/windows/calculate", json=too_bright).status_code == 422
    no_target = {"start_time": "2026-12-15T10:00:00Z", "end_time": "2026-12-15T11:00:00Z", "constraints": {}}
    assert client.post("/api/v1/windows/calculate", json=no_target).status_code == 422

    response = client.post(
        "/result",
        data={
            "source_index": "11",
            "start_time": "2026-12-15T18:00",
            "end_time": "2026-12-16T18:00",
            "target_min_zenith_deg": "70",
            "target_max_zenith_deg": "20",
        },
    )
    assert response.status_code == 422
    assert "target_min_zenith_deg" in response.text


def test_telescope_controls_and_current_fov_contract_are_rendered_and_local():
    """The homepage keeps telescope settings request-local and sky-aware."""
    home = client.get("/")
    assert home.status_code == 200
    assert 'id="telescope_mode"' in home.text
    assert 'id="custom-telescope-fields"' in home.text
    assert 'id="custom_longitude_deg"' in home.text
    assert 'id="sky-zoom-in"' in home.text
    assert 'id="sky-zoom-out"' in home.text
    assert 'data-i18n="allFieldsRequired"' not in home.text
    assert 'data-i18n="blankDisables"' not in home.text
    assert 'V2.2: geometry assessment only' not in home.text
    assert 'data-i18n="homeTitle"' in home.text

    custom = {
        "telescope_mode": "custom",
        "custom_longitude_deg": "0",
        "custom_latitude_deg": "30",
        "custom_altitude_m": "100",
        "custom_timezone_offset_hours": "0",
        "custom_fov_diameter_deg": "12",
    }
    sky = client.get("/api/v1/sky/current", params={
        "at_time": "2026-12-15T16:00:00Z",
        "sun_max_altitude_deg": -18, "moon_min_separation_deg": 30,
        "target_min_zenith_deg": 0, "target_max_zenith_deg": 60,
        **custom,
    })
    assert sky.status_code == 200
    payload = sky.json()
    assert payload["telescope"]["name"] == "Custom telescope"
    assert payload["telescope"]["fov_radius_deg"] == 6.0
    assert 'class="realtime-fov-ring"' in payload["svg"]
    assert 'fill="none"' not in payload["svg"]  # CSS, never a filled SVG FoV region


def test_result_keeps_custom_telescope_context_and_human_reason_markup():
    response = client.post(
        "/result",
        data={
            "source_index": "11", "start_time": "2026-12-15T10:00", "end_time": "2026-12-15T11:00",
            "telescope_mode": "custom", "custom_longitude_deg": "0", "custom_latitude_deg": "30",
            "custom_altitude_m": "100", "custom_timezone_offset_hours": "0", "custom_fov_diameter_deg": "12",
            "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30", "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "60", "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    assert 'data-telescope-mode="custom"' in response.text
    assert 'name="custom_fov_diameter_deg" value="12"' in response.text
    # Replacement remains only through the shared source-detail dialog; no
    # result-header replacement button is rendered.
    assert 'data-replace-source' not in response.text
    assert 'id="replace-source-form"' in response.text
    assert 'data-reason-codes=' in response.text
    # Machine codes remain in a data attribute for the bilingual client, while
    # the visible server fallback is already readable before JavaScript runs.
    assert 'Target centre:' in response.text or 'All enabled geometry conditions pass' in response.text

    stylesheet = (Path(__file__).resolve().parents[1] / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    assert '.fov-ring { fill: none;' in stylesheet

    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "appendTelescopeParameters" in script
    assert "initialiseTelescopeControls" in script
    assert "skyQueryParameters" in script
    assert "Math.min(1000" in script
    assert "setAttribute('viewBox'" in script
    assert "image.style.width = (zoom * 100)" not in script
    assert "formatReason" in script


def test_uploaded_catalogue_is_request_scoped_and_supports_map_display_routes():
    upload = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("operator.csv", b"name,ra,dec,ext\nDemoA,83.633,22.014,0.4\nDemoB,84.0,22.3,0\n", "text/csv")},
    )
    assert upload.status_code == 200
    payload = upload.json()
    assert payload["temporary"] is True and payload["count"] == 2
    token = payload["token"]
    listed = client.get("/api/v1/sources", params={"catalog_token": token, "limit": 190})
    assert listed.status_code == 200 and listed.json()["count"] == 2
    sky = client.get("/api/v1/sky/current", params={"catalog_token": token, "at_time": "2026-12-15T16:00:00Z", "language": "zh"})
    assert sky.status_code == 200 and len(sky.json()["sources"]) == 2
    assert "地平线" in sky.json()["svg"]
    trajectory = client.get("/api/v1/sky/current", params={"catalog_token": token, "at_time": "2026-12-15T16:00:00Z", "trajectory_end": "2026-12-15T17:00:00Z", "status_mode": "trajectory"})
    assert trajectory.status_code == 200 and trajectory.json()["status_mode"] == "trajectory"
    local = client.get("/api/v1/sky/local-fov", params={"catalog_token": token, "target_source_index": 0, "at_time": "2026-12-15T16:00:00Z", "language": "zh"})
    assert local.status_code == 200 and "局部" not in local.text  # SVG stays data-only, no external asset.


def test_plot_overlay_is_display_only_and_preserves_target_curve():
    response = client.get(
        "/api/v1/windows/plot-overlay",
        params={
            "comparison_source_index": 12, "target_source_index": 11,
            "start_time": "2026-12-15T10:00:00Z", "end_time": "2026-12-15T11:00:00Z",
            "sun_max_altitude_deg": -18, "moon_min_separation_deg": 30,
            "target_min_zenith_deg": 0, "target_max_zenith_deg": 60,
            "minimum_window_seconds": 0, "theme": "light", "timezone_label": "UTC",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["comparison_source"]["index"] == 12
    assert 'stroke-dasharray' in data["svg"]



def test_trajectory_mode_validates_direction_and_respects_minimum_duration():
    """Trajectory colours must describe a forward interval and enabled duration."""
    base = {
        "at_time": "2026-12-15T16:00:00Z",
        "trajectory_end": "2026-12-15T17:00:00Z",
        "status_mode": "trajectory",
        "minimum_window_seconds": 86400,
    }
    response = client.get("/api/v1/sky/current", params=base)
    assert response.status_code == 200
    assert not any(item["status"] in {"GREEN", "YELLOW"} for item in response.json()["sources"])
    for end in ("2026-12-15T16:00:00Z", "2026-12-15T15:59:59Z"):
        invalid = client.get("/api/v1/sky/current", params={**base, "trajectory_end": end})
        assert invalid.status_code == 422
        assert "trajectory_end must be later" in invalid.text


def test_observation_window_mode_uses_explicit_full_ranges_without_pointing():
    """Result-map status can be limited to target full windows and ignore pointing."""
    ranges = '[["2026-12-15T16:10:00Z","2026-12-15T16:20:00Z"]]'
    response = client.get(
        "/api/v1/sky/current",
        params={
            "at_time": "2026-12-15T16:00:00Z",
            "trajectory_end": "2026-12-15T17:00:00Z",
            "status_mode": "trajectory",
            "trajectory_enforce_current_pointing": "false",
            "trajectory_ranges": ranges,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status_mode"] == "trajectory"
    assert payload["enforce_current_pointing"] is False
    invalid = client.get(
        "/api/v1/sky/current",
        params={
            "at_time": "2026-12-15T16:00:00Z",
            "trajectory_end": "2026-12-15T17:00:00Z",
            "status_mode": "trajectory",
            "trajectory_ranges": '[["2026-12-15T16:20:00Z","2026-12-15T16:10:00Z"]]',
        },
    )
    assert invalid.status_code == 422


def test_empty_full_window_ranges_classify_every_source_red():
    response = client.get(
        "/api/v1/sky/current",
        params={
            "at_time": "2026-12-15T16:00:00Z",
            "trajectory_end": "2026-12-15T17:00:00Z",
            "status_mode": "trajectory",
            "trajectory_ranges": "[]",
            "highlight_indexes": "11",
            "selected_source_index": 11,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["sources"]) == 90
    assert all(item["status"] == "RED" for item in payload["sources"])
    assert payload["svg"].count('class="source-marker ') == 90
    import xml.etree.ElementTree as ET
    assert not any("trajectory-highlight" in node.get("class", "").split()
                   for node in ET.fromstring(payload["svg"]).iter())  # no highlighted marker; CSS rules are allowed
    instant = client.get(
        "/api/v1/sky/current",
        params={"at_time": "2026-12-15T16:00:00Z", "highlight_indexes": "11"},
    )
    assert instant.status_code == 200
    assert not any("trajectory-highlight" in node.get("class", "").split()
                   for node in ET.fromstring(instant.json()["svg"]).iter())


def test_result_map_exposes_full_windows_and_fixed_size_symbol_controls():
    response = client.post(
        "/result",
        data={
            "source_index": "11", "start_time": "2026-12-15T10:00",
            "end_time": "2026-12-16T10:00", "display_timezone": "utc",
            "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0", "target_max_zenith_deg": "60",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    assert "data-full-window-ranges='[" in response.text
    assert 'data-i18n="trajectoryStatusExplanation"' not in response.text
    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    stylesheet = (Path(__file__).resolve().parents[1] / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    assert "trajectory_enforce_current_pointing" in script
    assert "trajectory_ranges" in script
    assert "--map-icon-scale" in script and "--map-icon-scale" in stylesheet
    assert ".trajectory-highlight .source-symbol" in stylesheet and "#8b5cf6" in stylesheet
    assert 'data-i18n="legendGreenMeaning"' in response.text
    assert 'data-i18n="legendYellowMeaning"' in response.text
    assert 'data-i18n="legendRedMeaning"' in response.text
    assert 'id="tracked-fov-legend" hidden' in response.text


def test_source_detail_ignores_legacy_current_pointing_flag():
    """Detail and map status share geometry-only observability without telemetry."""
    moment = "2026-12-15T16:00:00Z"
    sky = client.get("/api/v1/sky/current", params={"at_time": moment}).json()
    marker = next(item for item in sky["sources"] if item["index"] == 1)
    detail = client.get("/api/v1/sources/1", params={"at_time": moment, "enforce_current_pointing": "true"})
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"]["status"] == marker["status"]
    assert payload["status"]["current_pointing_enforced"] is False


def test_minimal_uploaded_catalogue_derives_coordinates_without_fake_uncertainties():
    upload = client.post(
        "/api/v1/catalogues/upload",
        files={"file": ("minimal.csv", b"name,ra,dec\nOnlyRow,83.633,22.014\n", "text/csv")},
    )
    assert upload.status_code == 200
    token = upload.json()["token"]
    source = client.get("/api/v1/sources/0", params={"catalog_token": token, "at_time": "2026-12-15T16:00:00Z"})
    assert source.status_code == 200
    payload = source.json()
    assert payload["l"] != 0.0 or payload["b"] != 0.0
    assert payload["ext_err"] is None
    assert payload["p_err(95%)"] is None


def test_custom_offset_plot_uses_physical_local_clock_and_client_passes_label():
    from app.catalog import catalog
    from app.config import custom_telescope
    from app.plotting import render_window_plot
    from app.schemas import ConstraintSet
    from app.windows import calculate_windows

    telescope = custom_telescope(0, 30, 100, 5.5, 12)
    result = calculate_windows(
        catalog.get(11), datetime(2026, 12, 15, 12, tzinfo=timezone.utc),
        datetime(2026, 12, 15, 13, tzinfo=timezone.utc), ConstraintSet(), telescope=telescope,
    )
    svg = render_window_plot(result, timezone_label="UTC+05:30", timezone_offset_hours=5.5)
    assert "17:30" in svg or "17:45" in svg
    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "observerTimezoneLabel()" in script
    assert "checkbox.dataset.catalogueId=data.token" in script
    assert "setCatalogueOpen(true); checkbox.checked=true" in script
    assert "confirm?.addEventListener('click', applySelection)" in script
    assert "replaceSourceOptions(rows)" in script


def test_conditional_fields_zoom_and_result_modes_have_explicit_client_contracts():
    home = client.get("/")
    assert home.status_code == 200
    assert 'id="custom-telescope-fields"' in home.text and ' hidden' in home.text
    assert 'id="sky-time-control" hidden' in home.text
    stylesheet = (Path(__file__).resolve().parents[1] / "app" / "static" / "styles.css").read_text(encoding="utf-8")
    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert '[hidden] { display: none !important; }' in stylesheet
    assert "Math.min(1000" in script
    assert "setAttribute('viewBox'" in script
    assert "image.style.width = (zoom * 100)" not in script
    assert "frame.getBoundingClientRect()" in script
    assert "getScreenCTM().inverse()" in script and "setPointerCapture" in script
    assert "skyward:map-replaced" in script

    result = client.post(
        "/result",
        data={
            "source_index": "11", "start_time": "2026-12-15T10:00:00Z", "end_time": "2026-12-15T11:00:00Z",
            "display_timezone": "utc", "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0", "target_max_zenith_deg": "60", "minimum_window_seconds": "0",
        },
    )
    assert result.status_code == 200
    assert '>Real-time</option>' in result.text
    assert '>Observation window</option>' in result.text
    assert '#8b5cf6' in stylesheet


def test_plot_overlay_supports_multiple_additions_and_empty_removal_state():
    base = [
        ("target_source_index", "11"), ("start_time", "2026-12-15T10:00:00Z"),
        ("end_time", "2026-12-15T11:00:00Z"), ("theme", "light"), ("timezone_label", "UTC"),
    ]
    multiple = client.get(
        "/api/v1/windows/plot-overlay",
        params=base + [("comparison_source_index", "12"), ("comparison_source_index", "13")],
    )
    assert multiple.status_code == 200
    payload = multiple.json()
    assert [item["index"] for item in payload["comparison_sources"]] == [12, 13]
    assert payload["comparison_source"] is None
    assert "#ff8c42" in payload["svg"] and "#8b5cf6" in payload["svg"]

    removed = client.get("/api/v1/windows/plot-overlay", params=base)
    assert removed.status_code == 200
    assert removed.json()["comparison_sources"] == []
    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "zenithOverlayIndexes = new Set()" in script
    assert "zenithOverlayIndexes.delete(sourceIndex)" in script
    assert "renderZenithCurveControls" in script
    assert "params.append('comparison_source_key'" in script


def test_latest_result_map_realtime_and_curve_controls_contracts():
    response = client.post(
        "/result",
        data={
            "source_index": "11", "start_time": "2026-12-15T10:00",
            "end_time": "2026-12-16T10:00", "display_timezone": "utc",
            "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30",
            "target_min_zenith_deg": "0", "target_max_zenith_deg": "60",
            "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    text = response.text
    assert 'class="result-source-title"' in text
    assert 'data-window-display-time=' in text
    assert text.count('data-zoom-max="1000"') >= 2
    assert 'id="local-fov-mode"' not in text and 'id="local-fov-time"' not in text
    assert 'id="specified-time-kind"' in text and 'id="specified-time-start"' in text
    assert 'id="zenith-curve-controls"' in text
    assert 'id="refresh-realtime"' in text
    assert 'id="sky-clock"' in text and 'id="sun-coordinates"' in text and 'id="moon-coordinates"' in text
    assert 'sky-live-panel' not in text
    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "trajectory_display_time" in script
    assert "comparison_colour" in script and "comparison_line_style" in script
    assert "Math.min(1000" in script
    assert "appendCameraParameters" in script
    assert "skyward:refresh-realtime" in script


def test_observation_window_positions_share_one_explicit_instant():
    params = {
        "at_time": "2026-12-15T10:00:00Z",
        "trajectory_end": "2026-12-15T12:00:00Z",
        "trajectory_display_time": "2026-12-15T10:30:00Z",
        "trajectory_ranges": '[["2026-12-15T10:15:00Z","2026-12-15T11:00:00Z"]]',
        "status_mode": "trajectory",
        "trajectory_enforce_current_pointing": "false",
        "selected_source_index": 11,
    }
    response = client.get("/api/v1/sky/current", params=params)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["sources"]) == 90
    assert 'selected-source' in payload["svg"]
    instant = client.get("/api/v1/sky/current", params={"at_time": "2026-12-15T10:30:00Z"}).json()
    by_index = {item["index"]: item for item in instant["sources"]}
    for item in payload["sources"][:10]:
        assert item["geometry"]["target_altitude_deg"] == pytest.approx(by_index[item["index"]]["geometry"]["target_altitude_deg"])
        assert item["geometry"]["sun_altitude_deg"] == pytest.approx(by_index[item["index"]]["geometry"]["sun_altitude_deg"])


def test_curve_styles_and_shared_body_endpoint():
    bodies = client.get("/api/v1/sky/bodies", params={"at_time": "2026-12-15T10:30:00Z"})
    assert bodies.status_code == 200
    assert set(bodies.json()) >= {"sun", "moon", "at_time", "telescope"}
    overlay = client.get(
        "/api/v1/windows/plot-overlay",
        params=[
            ("comparison_source_index", "12"), ("comparison_colour", "#8b5cf6"),
            ("comparison_line_style", "dotted"), ("target_source_index", "11"),
            ("start_time", "2026-12-15T10:00:00Z"), ("end_time", "2026-12-15T11:00:00Z"),
            ("theme", "light"), ("timezone_label", "UTC"),
        ],
    )
    assert overlay.status_code == 200
    assert "#8b5cf6" in overlay.json()["svg"].lower()


def test_review_edge_cases_empty_ranges_custom_context_and_temporary_marker():
    script = (Path(__file__).resolve().parents[1] / "app" / "static" / "app.js").read_text(encoding="utf-8")
    assert "params.set('trajectory_ranges', context.dataset.fullWindowRanges)" in script
    assert "resultTelescopeContext" in script
    assert "specifiedTimeLimit" in script
    assert "mapStatusParameters" in script
    response = client.post(
        "/result",
        data={
            "source_index": "region", "region_name": "TMP custom marker",
            "region_ra_deg": "83.633", "region_dec_deg": "22.014", "region_radius_deg": "0.2",
            "start_time": "2026-12-15T10:00", "end_time": "2026-12-15T11:00",
            "display_timezone": "utc", "sun_max_altitude_deg": "-18",
            "moon_min_separation_deg": "30", "target_min_zenith_deg": "0",
            "target_max_zenith_deg": "60", "minimum_window_seconds": "0",
        },
    )
    assert response.status_code == 200
    assert 'selected-source' in response.text
    assert 'data-source-index="-1"' in response.text


def test_latest_live_map_plan_and_fast_curve_contracts():
    base = (Path(__file__).parents[1] / "app" / "templates" / "base.html").read_text()
    result = (Path(__file__).parents[1] / "app" / "templates" / "result.html").read_text()
    index = (Path(__file__).parents[1] / "app" / "templates" / "index.html").read_text()
    js = (Path(__file__).parents[1] / "app" / "static" / "app.js").read_text()
    assert "window.setInterval(() => refresh(new Date()), 60_000)" not in js
    assert "data-live-option" in index and result.count("data-live-option") == 1
    assert "refreshLiveOptionLabels" in js and "liveTimestamp" in js
    assert "data-result-map-time" not in result
    assert result.count("heading-mode-control") == 1
    assert "data-download-observation-plan" in result
    assert 'id="plan-download"' not in base
    assert 'data-i18n="confirmAddPlan"' in base
    assert "duplicatePlanPrompt" in js and "window.confirm" not in js
    assert "chooseDuplicateAction" in js
    assert "plotSvg:" in js and "safeName(entry.source)" in js
    assert 'lineStyle: "dashdot"' in js
    assert "['dashed','--']" not in js
    assert "curveGroup()?.remove()" in js
    assert "applyVisualStyle()" in js
    assert "await refreshZenithOverlays();" not in js[js.index("const renderZenithCurveControls"):js.index("const initialiseResultMaps")]
    assert 'id="dialog-add-zenith"' in base


def test_overlay_svg_exposes_stable_curve_group_for_client_only_style_changes():
    response = client.get("/api/v1/windows/plot-overlay", params=[
        ("target_source_index", "11"), ("start_time", "2026-12-15T10:00:00Z"),
        ("end_time", "2026-12-15T11:00:00Z"), ("comparison_source_index", "12"),
    ])
    assert response.status_code == 200
    assert 'id="zenith-overlay-12"' in response.json()["svg"]


def test_display_only_theme_plan_zip_and_compact_controls_contracts():
    root = Path(__file__).parents[1]
    js = (root / "app/static/app.js").read_text()
    css = (root / "app/static/styles.css").read_text()
    base = (root / "app/templates/base.html").read_text()
    result = (root / "app/templates/result.html").read_text()
    plotting = (root / "app/plotting.py").read_text()
    assert 'id="theme-refresh-form"' not in result
    theme_block = js[js.index("const initialiseResultThemePlot"):js.index("const initialiseSourceDialog")]
    assert "requestSubmit" not in theme_block and "fetch(" not in theme_block
    assert "recolourPlot" in theme_block and "replaceAll" in theme_block
    assert '"svg.fonttype": "none"' in plotting
    assert "grey solid circle" in js and "blue dashed circle" in js and "cyan dashed circle" in js
    assert "青色虚线圆" in js and "可能被中央目标标记遮住" in js
    assert "height: 32px" in css and ".heading-mode-control select" in css
    assert ".plan-window-actions .secondary-button" in css
    assert 'id="duplicate-plan-dialog"' in base
    assert 'data-duplicate-choice="overwrite"' in base
    assert 'data-duplicate-choice="append"' in base
    assert 'data-duplicate-choice="cancel"' in base
    assert "window.confirm" not in js
    assert 'choice === "cancel"' in js and 'choice === "overwrite"' in js and 'choice === "append"' in js
    assert "application/zip" in js and "skyward-observing-plan.zip" in js
    assert "zipBytes(files)" in js
    assert "saveFile(" not in js
