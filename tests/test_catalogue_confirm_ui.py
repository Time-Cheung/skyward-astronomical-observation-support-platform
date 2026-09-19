"""Confirmation semantics for the catalogue picker, with optional real Chromium coverage."""
import json
from pathlib import Path
import os
from urllib.parse import parse_qs, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "app/static/app.js").read_text()
PANEL = (ROOT / "app/templates/_catalogue_panel.html").read_text()
INDEX = (ROOT / "app/templates/index.html").read_text()
RESULT = (ROOT / "app/templates/result.html").read_text()


def test_catalogue_picker_is_inside_each_all_sky_panel_and_has_explicit_actions():
    assert INDEX.index('<section class="sky-panel"') < INDEX.index('{% include "_catalogue_panel.html" %}')
    assert RESULT.index('<div class="result-map-grid">') < RESULT.index('{% include "_catalogue_panel.html" %}')
    assert "catalogue-map-layout" not in RESULT
    assert 'id="catalogue-picker-toggle"' in PANEL
    assert 'id="catalogue-picker-popup"' in PANEL
    assert 'id="catalogue-confirm"' in PANEL
    assert "data-catalogue-cancel" in PANEL
    assert "Currently imported: the 2LHAASO source catalogue." not in INDEX


def test_catalogue_draft_and_stable_key_contracts_are_explicit():
    assert "let appliedCatalogueTokens = null" in JS
    assert "appliedCatalogueTokens = draftCatalogueTokens()" in JS
    assert "confirm?.addEventListener('click', applySelection)" in JS
    assert "panel.addEventListener('change'" in JS
    assert "document.dispatchEvent(new Event('skyward:catalogues-change')); load();" in JS
    assert "item.dataset.sourceKey === sourceKey" in JS
    assert "option = new Option('', sourceKey)" in JS
    assert "params.set('catalog_tokens', selectedCatalogueTokens().filter" in JS
    assert "params.set('include_gaia', 'false')" in JS


@pytest.fixture
def browser_page():
    url = os.environ.get("SKYWARD_UI_URL")
    if not url:
        pytest.skip("Set SKYWARD_UI_URL for real Chromium coverage")
    sync_api = pytest.importorskip("playwright.sync_api")
    with sync_api.sync_playwright() as runtime:
        executable = os.environ.get("SKYWARD_CHROMIUM_EXECUTABLE")
        browser = runtime.chromium.launch(headless=True, executable_path=executable)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="networkidle")
        yield page
        assert errors == []
        browser.close()


def test_browser_draft_cancel_confirm_empty_and_real_source_identity(browser_page):
    page = browser_page
    target_key = page.locator("#source-key-input").input_value()
    initial_marker_count = page.locator("[data-map-frame] .source-marker").count()
    requests = []
    page.on("request", lambda request: requests.append(request.url))

    page.locator("#catalogue-picker-toggle").click()
    request_count = len(requests)
    page.locator('[data-catalogue-id="fermi-3fhl"]').check()
    page.wait_for_timeout(350)
    assert len(requests) == request_count
    assert page.locator("[data-map-frame] .source-marker").count() == initial_marker_count
    assert page.locator("#source-key-input").input_value() == target_key

    page.locator("[data-catalogue-cancel]").last.click()
    assert not page.locator('[data-catalogue-id="fermi-3fhl"]').is_checked()
    assert page.locator("#catalogue-picker-summary").inner_text() == "2LHAASO"

    page.locator("#catalogue-picker-toggle").click()
    page.locator('[data-catalogue-id="2lhaaso"]').uncheck()
    page.locator('[data-catalogue-id="fermi-3fhl"]').check()
    with page.expect_response(lambda response: "/api/v1/sky/current?" in response.url) as sky_info:
        with page.expect_response(lambda response: "/api/v1/sources?" in response.url) as search_info:
            page.locator("#catalogue-confirm").click()
    sky_response = sky_info.value
    search_response = search_info.value
    sky_query = parse_qs(urlsplit(sky_response.url).query, keep_blank_values=True)
    assert sky_query["catalog_tokens"] == ["fermi-3fhl"]
    assert sky_query["include_gaia"] == ["false"]
    sky_payload = sky_response.json()
    search_payload = search_response.json()
    assert len(sky_payload["sources"]) == search_payload["total"] == 1556
    page.wait_for_function("document.querySelectorAll('[data-map-frame] .source-marker').length > 0 && [...document.querySelectorAll('[data-map-frame] .source-marker')].every(marker => marker.dataset.sourceKey.startsWith('fermi-3fhl:'))")
    assert page.locator("[data-map-frame] .source-marker").count() == sky_payload["svg"].count('class="source-marker')
    assert page.locator("#source-key-input").input_value() == target_key

    page.locator("#source-picker-toggle").click()
    page.wait_for_function("document.querySelector('#source-search-status').textContent.includes('1556')")
    page.locator("#source-options [role=option]").nth(1).click()
    assert page.locator("#source-key-input").input_value().startswith("fermi-3fhl:")

    page.locator("#catalogue-picker-toggle").click()
    page.locator('[data-catalogue-id="fermi-3fhl"]').uncheck()
    with page.expect_response(lambda response: "/api/v1/sky/current?" in response.url) as empty_info:
        page.locator("#catalogue-confirm").click()
    empty_query = parse_qs(urlsplit(empty_info.value.url).query, keep_blank_values=True)
    assert empty_query["catalog_tokens"] == [""]
    assert empty_info.value.json()["sources"] == []
    page.wait_for_function("document.querySelectorAll('[data-map-frame] .source-marker').length === 0")
    assert page.locator("#catalogue-picker-summary").inner_text() in {"未选择源表", "No catalogues selected"}
    assert page.locator("#catalog-tokens-input").input_value() == ""


def _load_result(page):
    form = {
        "source_key": "2lhaaso:J0534+2200", "source_index": "region", "catalog_tokens": "2lhaaso",
        "start_time": "2026-09-16T19:00", "end_time": "2026-09-16T19:01",
        "sun_max_altitude_deg": "-18", "moon_min_separation_deg": "30",
        "target_min_zenith_deg": "0", "target_max_zenith_deg": "60", "minimum_window_seconds": "0",
    }
    response = page.request.post(page.url.rstrip("/") + "/result", form=form)
    assert response.status == 200
    page.set_content(response.text(), wait_until="networkidle")


def test_browser_result_picker_is_inside_map_and_never_replaces_result_target(browser_page):
    page = browser_page
    _load_result(page)
    context = page.locator("#detail-query-context")
    target_key = context.get_attribute("data-result-source-key")
    target_title = page.locator(".result-source-title").inner_text()
    assert page.locator(".result-map-grid .sky-panel").first.locator("[data-catalogue-panel]").count() == 1

    calls = []
    page.on("request", lambda request: calls.append(request.url) if "/api/v1/sky/" in request.url else None)
    page.locator("#catalogue-picker-toggle").click()
    request_count = len(calls)
    page.locator('[data-catalogue-id="fermi-3fhl"]').check()
    page.wait_for_timeout(350)
    assert len(calls) == request_count
    page.locator("[data-catalogue-cancel]").last.click()
    assert not page.locator('[data-catalogue-id="fermi-3fhl"]').is_checked()

    page.locator("#catalogue-picker-toggle").click()
    page.locator('[data-catalogue-id="2lhaaso"]').uncheck()
    page.locator('[data-catalogue-id="fermi-3fhl"]').check()
    with page.expect_response(lambda response: "/api/v1/sky/current?" in response.url) as sky_info:
        page.locator("#catalogue-confirm").click()
    query = parse_qs(urlsplit(sky_info.value.url).query, keep_blank_values=True)
    assert query["catalog_tokens"] == ["fermi-3fhl"]
    payload = sky_info.value.json()
    assert len(payload["sources"]) == 1557
    page.wait_for_function("target => document.querySelectorAll('[data-result-sky-map] .source-marker').length > 0 && [...document.querySelectorAll('[data-result-sky-map] .source-marker')].every(marker => marker.dataset.sourceKey.startsWith('fermi-3fhl:') || marker.dataset.sourceKey === target)", arg=target_key)
    marker_keys = page.locator("[data-result-sky-map] .source-marker").evaluate_all("markers => markers.map(marker => marker.dataset.sourceKey)")
    assert target_key in marker_keys
    assert any(key.startswith("fermi-3fhl:") for key in marker_keys)
    assert context.get_attribute("data-result-source-key") == target_key
    assert page.locator(".result-source-title").inner_text() == target_title
    assert page.locator('#replace-source-form [name="catalog_tokens"]').input_value() == "fermi-3fhl"
    assert context.get_attribute("data-catalog-tokens") == "fermi-3fhl"


def test_browser_gaia_remains_a_separate_confirmed_layer(browser_page):
    page = browser_page
    payload = {
        "gaia": {"count": 1, "drawn_count": 1, "cached": True},
        "sources": [{"index": 80001, "source_key": "gaia-dr3:123", "source_id": "123", "display_name": "Gaia DR3 123"}],
        "overlay_svg": '<svg xmlns="http://www.w3.org/2000/svg"><g class="source-marker source-type-gaia" data-gaia-source-id="123" data-source-key="gaia-dr3:123"><circle cx="380" cy="250" r="8" /></g></svg>',
    }
    gaia_calls = []
    page.route("**/api/v1/gaia?*", lambda route: (gaia_calls.append(route.request.url), route.fulfill(content_type="application/json", body=json.dumps(payload))))
    page.locator("#catalogue-picker-toggle").click()
    page.locator('[data-catalogue-id="gaia-dr3"]').check()
    page.wait_for_timeout(250)
    assert gaia_calls == []
    with page.expect_response(lambda response: "/api/v1/sky/current?" in response.url) as sky_info:
        page.locator("#catalogue-confirm").click()
    query = parse_qs(urlsplit(sky_info.value.url).query, keep_blank_values=True)
    assert query["catalog_tokens"] == ["2lhaaso"]
    assert query["include_gaia"] == ["false"]
    page.wait_for_selector("[data-gaia-layer] [data-gaia-source-id]")
    assert len(gaia_calls) == 1
    gaia_query = parse_qs(urlsplit(gaia_calls[0]).query, keep_blank_values=True)
    assert gaia_query["map_kind"] == ["current"]


@pytest.mark.parametrize("language,theme", [("zh", "light"), ("en", "dark")])
def test_browser_catalogue_popup_fits_mobile_themes(browser_page, language, theme):
    page = browser_page
    page.set_viewport_size({"width": 375, "height": 812})
    page.locator("#language-select").select_option(language)
    for _ in range(3):
        if page.locator("html").get_attribute("data-theme") == theme:
            break
        page.locator("#theme-toggle").click()
    page.locator("#catalogue-picker-toggle").click()
    popup = page.locator("#catalogue-picker-popup")
    box = popup.bounding_box()
    assert popup.is_visible() and box
    assert box["x"] >= 0 and box["x"] + box["width"] <= 375
    assert page.locator("#catalogue-confirm").is_visible()
    assert page.locator("[data-catalogue-cancel]").last.is_visible()
    assert page.evaluate("document.documentElement.scrollWidth") == 375
