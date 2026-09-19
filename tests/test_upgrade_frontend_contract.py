"""Frontend invariants plus optional genuine Chromium UI acceptance.

Run browser coverage with SKYWARD_UI_URL pointing at a dedicated loopback test
instance and a Python environment with Playwright. Never requires a production
JavaScript or Python dependency. Gaia network responses are explicitly mocked.
"""
import json
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / 'app/static/app.js').read_text()


def test_shared_layers_are_checkboxes_with_explicit_empty_semantics():
    panel = (ROOT / 'app/templates/_catalogue_panel.html').read_text()
    for identifier in ('2lhaaso', 'fermi-fl16y', 'fermi-3fhl', 'tevcat', 'gaia-dr3'):
        assert identifier in panel
    for name in ('index.html', 'result.html'):
        assert '{% include "_catalogue_panel.html" %}' in (ROOT / 'app/templates' / name).read_text()
    assert 'data-catalogue-id' in panel
    assert 'include-gaia' not in JS
    assert "params.set('catalog_tokens', selectedCatalogueTokens().filter" in JS


def test_search_transport_is_separate_from_popup_and_uses_paging_and_keys():
    template = (ROOT / 'app/templates/index.html').read_text()
    assert 'role="combobox"' in template and 'role="listbox"' in template
    assert template.index('id="source-search"') < template.index('id="source-options"')
    assert 'limit:\'100\',offset:' in JS
    assert 'data.next_offset' in JS
    assert 'encodeURIComponent(sourceIndex)' in JS
    assert "comparison_source_key" in JS
    assert 'source-key-input' in template


def test_camera_is_bounded_and_repaints_backend_grid():
    assert "input.max = '1000'" in JS
    assert "d.svg.setAttribute('viewBox'" in JS
    assert "skyward:camera-change" in JS
    assert "params.set('bounds'" in JS
    assert "image.style.width = (zoom * 100)" not in JS
    assert 'AbortController' in JS
    assert "skyward:coordinate-change', () => { refresh(); refreshLocal(); }" in JS


def test_submission_feedback_and_safe_notes_contract():
    assert 'requestAnimationFrame(()=>requestAnimationFrame(resolve))' in JS
    assert "window.addEventListener('pageshow',restore)" in JS
    assert 'form.reportValidity()' in JS
    assert 'JSON.stringify(data, null, 2)' in JS
    assert 'safeExternalUrl' in JS
    assert "gaiaCandidateWarning" in JS


@pytest.fixture
def browser_page():
    url = os.environ.get('SKYWARD_UI_URL')
    if not url:
        pytest.skip('Set SKYWARD_UI_URL for genuine browser coverage')
    sync_api = pytest.importorskip('playwright.sync_api')
    with sync_api.sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(url, wait_until='networkidle')
        yield page
        assert errors == []
        browser.close()


def test_browser_search_stability_and_failed_submission(browser_page):
    page = browser_page
    page.locator('#catalogue-picker-toggle').click()
    page.locator('[data-catalogue-id="fermi-fl16y"]').check()
    page.locator('#catalogue-confirm').click()
    page.locator('#source-picker-toggle').click()
    page.locator('#source-search').fill('J2359')
    page.wait_for_function("document.querySelector('#source-options').textContent.includes('J2359') && document.querySelector('#source-search-status').textContent.includes('/')")
    page.locator('#source-options [role=option]').nth(1).click()
    key = page.locator('#source-key-input').input_value()
    assert key.startswith('fermi-fl16y:')
    page.locator('#source-picker-toggle').click()
    page.locator('#source-search').fill('no_match_xyz')
    page.wait_for_timeout(500)
    assert page.locator('#source-key-input').input_value() == key
    page.locator('#source-search').press('Escape')
    page.route('**/result', lambda route: route.fulfill(status=500, content_type='application/json', body='{}'))
    page.locator('#planner-form button[type=submit]').click()
    page.wait_for_function("!document.querySelector('#calculation-error').hidden")
    assert page.locator('#calculation-dialog').is_visible()
    page.locator('#calculation-cancel').click()
    assert page.locator('#planner-form button[type=submit]').is_enabled()


def test_browser_gaia_cache_detail_and_uncheck(browser_page):
    page = browser_page
    payload = {'gaia': {'count': 1, 'drawn_count': 1, 'cached': True, 'radius_deg': 5, 'max_mag': 18, 'limit': 500, 'selection': 'bounded_unordered_subset', 'ordering': 'unspecified', 'brightest_n': False},
               'sources': [{'index': 80001, 'source_key': 'gaia-dr3:123', 'source_id': '123', 'display_name': 'Gaia DR3 123', 'notes': '<script>alert(1)</script>'}],
               'overlay_svg': '<svg xmlns="http://www.w3.org/2000/svg"><g class="source-marker source-type-gaia" data-source-index="80001" data-source-key="gaia-dr3:123" tabindex="0"><circle cx="380" cy="250" r="8" /></g></svg>'}
    page.route('**/api/v1/gaia?*', lambda route: route.fulfill(content_type='application/json', body=json.dumps(payload)))
    page.locator('#catalogue-picker-toggle').click()
    page.locator('[data-catalogue-id="gaia-dr3"]').check()
    page.locator('#catalogue-confirm').click()
    page.wait_for_selector('[data-gaia-layer] .source-marker')
    assert '1 / 1' in page.locator('[data-gaia-status]').inner_text()
    assert '不是最亮 N 颗' in page.locator('[data-gaia-selection-warning]').inner_text()
    assert '不是代表性抽样' in page.locator('[data-gaia-selection-warning]').inner_text()
    page.locator('#language-select').select_option('en')
    page.wait_for_function("document.querySelector('[data-gaia-selection-warning]')?.textContent.includes('not the brightest N')")
    assert 'not a representative sample' in page.locator('[data-gaia-selection-warning]').inner_text()
    page.locator('[data-gaia-layer] .source-marker').click(force=True)
    assert page.locator('#dialog-title').inner_text() == 'Gaia DR3 123'
    assert page.locator('#dialog-body script').count() == 0
    page.locator('[data-close-dialog]').click()
    page.locator('#catalogue-picker-toggle').click()
    page.locator('[data-catalogue-id="gaia-dr3"]').uncheck()
    page.locator('#catalogue-confirm').click()
    assert page.locator('[data-gaia-layer]').count() == 0


def test_browser_empty_layers_and_camera_layout(browser_page):
    page = browser_page
    frame = page.locator('.map-frame')
    selected_before = page.locator('#source-key-input').input_value()
    width = frame.bounding_box()['width']
    page.locator('.zoom-factor').fill('1000')
    page.locator('.zoom-factor').press('Tab')
    assert frame.get_attribute('data-zoom') == '1000'
    assert abs(frame.bounding_box()['width'] - width) < 1
    page.locator('#catalogue-picker-toggle').click()
    for checkbox in page.locator('[data-catalogue-id]:checked').all():
        checkbox.uncheck()
    page.locator('#catalogue-confirm').click()
    page.wait_for_function("document.querySelectorAll('.map-frame .source-marker').length === 0")
    assert page.locator('#source-key-input').input_value() == selected_before


def test_browser_deep_zoom_preserves_rendered_symbol_and_text_sizes(browser_page):
    """Measure CSS pixel glyph/hit/text bounds, not just the outer SVG layout."""
    from urllib.parse import parse_qs, urlsplit
    page = browser_page

    def mock_gaia(route):
        zoom = float(parse_qs(urlsplit(route.request.url).query).get('zoom', ['1'])[0])
        radius = 8 / zoom
        svg = ('<svg xmlns="http://www.w3.org/2000/svg"><g class="source-marker source-type-gaia" '
               'data-source-key="gaia-dr3:123" data-source-index="80001">'
               f'<polygon points="{380-radius},350 380,{350-radius} {380+radius},350 380,{350+radius}"/>'
               '</g></svg>')
        route.fulfill(content_type='application/json', body=json.dumps({
            'gaia': {'count': 1, 'drawn_count': 1, 'cached': True},
            'sources': [], 'overlay_svg': svg}))

    page.route('**/api/v1/gaia?*', mock_gaia)
    page.locator('#catalogue-picker-toggle').click()
    page.locator('[data-catalogue-id="gaia-dr3"]').check()
    page.locator('#catalogue-confirm').click()
    page.wait_for_selector('[data-gaia-layer] polygon')

    def dimensions():
        return page.locator('.map-frame svg').evaluate('''svg => {
          const box = selector => {
            const e = svg.querySelector(selector), rect = e.getBoundingClientRect();
            return {width:rect.width,height:rect.height};
          };
          return {symbol:box('.source-type-catalogue .source-symbol'),
            hit:box('.source-type-catalogue .source-hit-target'),
            text:box('.compass-label'),gaia:box('[data-gaia-layer] polygon')};
        }''')

    before = dimensions()
    page.locator('.zoom-factor').fill('1000')
    page.locator('.zoom-factor').press('Tab')
    page.wait_for_function("Number(document.querySelector('.map-frame svg').dataset.zoom) === 1000 && document.querySelector('[data-gaia-layer]')?.dataset.renderZoom === '1000'")
    after = dimensions()
    for name in before:
        assert after[name]['width'] > 2, (name, before, after)
        assert after[name]['height'] > 2, (name, before, after)
        assert after[name]['width'] == pytest.approx(before[name]['width'], rel=0.2), (name, before, after)
    assert page.locator('.map-frame svg').evaluate("e=>e.style.getPropertyValue('--map-icon-scale')") == '1'


def _post_result(page, **overrides):
    form = {'source_key': '2lhaaso:J0534+2200', 'source_index': 'region',
            'catalog_tokens': '2lhaaso', 'start_time': '2026-09-16T19:00',
            'end_time': '2026-09-16T19:01', 'sun_max_altitude_deg': '-18',
            'moon_min_separation_deg': '30', 'target_min_zenith_deg': '0',
            'target_max_zenith_deg': '60', 'minimum_window_seconds': '0'}
    form.update(overrides)
    response = page.request.post(page.url.rstrip('/') + '/result', form=form)
    page.set_content(response.text(), wait_until='networkidle')
    return response


def test_browser_validation_rerender_retains_stable_source_key(browser_page):
    page = browser_page
    response = _post_result(page, target_min_zenith_deg='80', target_max_zenith_deg='20')
    assert response.status == 422
    assert page.locator('#source-key-input').input_value() == '2lhaaso:J0534+2200'
    assert 'J0534+2200' in page.locator('#source-picker-value').inner_text()
    assert not page.locator('#region-fields').is_visible()


def test_browser_explicit_override_propagates_without_promoting_unknown(browser_page):
    from urllib.parse import parse_qs, urlsplit
    page = browser_page
    calls = []
    page.on('request', lambda req: calls.append(req.url))
    response = _post_result(page, nominal_radius_deg='0.42')
    assert response.status == 200
    assert page.locator('#detail-query-context').get_attribute('data-nominal-radius-deg') == '0.42'
    assert page.locator('#replace-source-form [name=nominal_radius_deg]').input_value() == '0.42'
    assert page.locator('[data-i18n=operatorNominalAssumption]').is_visible()
    page.wait_for_function("document.querySelector('[data-local-fov-map] svg') !== null")
    page.locator('#refresh-realtime').click()
    page.wait_for_timeout(500)
    for endpoint in ('/sky/current?', '/sky/local-fov?'):
        matching = [url for url in calls if endpoint in url]
        assert matching and all(parse_qs(urlsplit(url).query).get('nominal_radius_deg') == ['0.42'] for url in matching)


def test_browser_unknown_footprint_is_not_displayed_as_zero(browser_page):
    page = browser_page
    data = page.request.get(page.url.rstrip('/') + '/api/v1/sources?catalog_tokens=fermi-fl16y&q=J0058.0-7245e&limit=100').json()
    source = next(row for row in data['sources'] if not row['footprint_known'])
    response = _post_result(page, source_key=source['source_key'], catalog_tokens='fermi-fl16y')
    assert response.status == 200
    assert page.locator('[data-i18n=unknownFootprint]').is_visible()
    assert page.locator('[data-i18n=operatorNominalAssumption]').count() == 0
    assert page.locator('#detail-query-context').get_attribute('data-nominal-radius-deg') == ''
    assert page.locator('#detail-query-context').get_attribute('data-result-source-radius') == ''
    assert '0.000°' not in page.locator('.result-heading p').all_inner_texts()[-1]


def test_browser_plot_latest_response_wins_and_override_is_preserved(browser_page):
    page = browser_page
    assert _post_result(page, nominal_radius_deg='0.42').status == 200
    # Deliberately ignore AbortSignal in the mock to prove the generation guard,
    # rather than merely relying on a cooperative transport cancellation.
    page.evaluate('''() => {
      const original=window.fetch.bind(window); window.pendingPlots=[];
      window.fetch=(url,options)=>{
        if(String(url).includes('/windows/plot-overlay?'))return new Promise(resolve=>window.pendingPlots.push({url:String(url),resolve}));
        return original(url,options);
      };
    }''')
    for index, key in enumerate(('2lhaaso:Geminga', '2lhaaso:J0534+2221')):
        page.evaluate('''key=>{const button=document.createElement('button');button.id='test-detail';button.dataset.openSource=key;document.body.append(button);button.click();button.remove();}''', key)
        page.wait_for_function("!document.querySelector('#dialog-add-zenith').hidden")
        page.locator('#dialog-add-zenith').click()
        page.wait_for_function(f'window.pendingPlots.length === {index + 1}')
        page.locator('[data-close-dialog]').click()
    assert page.evaluate("window.pendingPlots.every(p=>new URL(p.url,location.href).searchParams.get('nominal_radius_deg')==='0.42')")
    page.evaluate('''()=>window.pendingPlots[1].resolve({ok:true,json:async()=>({svg:'<svg data-test-result="latest"/>',comparison_sources:[]})})''')
    page.wait_for_selector('.scientific-plot [data-test-result=latest]', state='attached')
    page.evaluate('''()=>window.pendingPlots[0].resolve({ok:true,json:async()=>({svg:'<svg data-test-result="stale"/>',comparison_sources:[]})})''')
    page.wait_for_timeout(100)
    assert page.locator('.scientific-plot [data-test-result=latest]').count() == 1
    assert page.locator('.scientific-plot [data-test-result=stale]').count() == 0


def test_browser_nominal_override_is_scoped_to_result_target(browser_page):
    from urllib.parse import parse_qs, unquote, urlsplit
    page = browser_page
    assert _post_result(page, nominal_radius_deg='0.42').status == 200
    detail_calls = []
    page.on('request', lambda req: detail_calls.append(req.url) if '/api/v1/sources/' in req.url else None)
    # Stop before network submission to inspect exactly what each replacement
    # would submit, including switching back after a cancelled different target.
    page.evaluate("document.querySelector('#replace-source-form').requestSubmit=()=>{}")
    for key, expected in [('2lhaaso:Geminga', ''), ('2lhaaso:J0534+2200', '0.42'), ('2lhaaso:J0534+2221', '')]:
        page.evaluate('''key=>{const button=document.createElement('button');button.dataset.openSource=key;document.body.append(button);button.click();button.remove();}''', key)
        page.wait_for_function("!document.querySelector('#dialog-use-source').hidden")
        url = next(url for url in reversed(detail_calls) if unquote(urlsplit(url).path).endswith(key))
        query = parse_qs(urlsplit(url).query)
        assert query.get('nominal_radius_deg', [''])[0] == expected
        if not expected:
            raw = page.locator('#dialog-body > .raw-fields pre').text_content()
            assert json.loads(raw)['footprint_kind'] != 'operator_nominal_radius'
        page.locator('#dialog-use-source').click()
        assert page.locator('#replace-source-form [name=nominal_radius_deg]').input_value() == expected
        page.locator('[data-close-dialog]').click()


@pytest.mark.parametrize('language,theme', [('en', 'dark'), ('zh', 'light')])
def test_browser_mobile_header_controls_fit_without_clipping(browser_page, language, theme):
    page = browser_page
    page.set_viewport_size({'width': 375, 'height': 812})
    page.locator('#language-select').select_option(language)
    for _ in range(3):
        if page.locator('html').get_attribute('data-theme') == theme:
            break
        page.locator('#theme-toggle').click()
    assert page.locator('html').get_attribute('data-theme') == theme
    assert page.evaluate('document.documentElement.scrollWidth') == 375
    for selector in ('#language-select', '#timezone-select', '#coordinate-select', '#theme-toggle'):
        control = page.locator(selector)
        box = control.bounding_box()
        assert box and box['x'] >= 0 and box['x'] + box['width'] <= 375
        assert control.is_visible() and control.is_enabled()
        control.focus()
        assert control.evaluate('e=>document.activeElement===e')
    page.locator('#timezone-select').select_option('utc')
    page.locator('#coordinate-select').select_option('galactic')
    page.locator('#theme-toggle').click()
    assert page.evaluate('document.documentElement.scrollWidth') == 375
