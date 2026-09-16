"""Scientific normalization and public fact-minimization acceptance tests.

Run: PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -p no:cacheprovider
     tests/test_tevcat_normalization.py
The reproducibility test uses TEVCAT_STAGING or the September 16 snapshot path.
"""
import importlib.util
import json
import math
import os
from pathlib import Path

import pytest
from astropy import units as u
from astropy.coordinates import SkyCoord

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('build_tevcat_catalogue', ROOT/'scripts/build_tevcat_catalogue.py')
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


@pytest.fixture(scope='module')
def catalogue():
    return mod.load(ROOT/'data/catalogues/tevcat.json')


@pytest.fixture(scope='module')
def by_id(catalogue):
    return {s['original_id']: s for s in catalogue['sources']}


def test_shared_schema_and_identity(catalogue):
    assert catalogue['schema_version'] == 1
    assert catalogue['catalogue_id'] == 'tevcat'
    assert catalogue['label'] == 'TeVCat (截止到2026年09月16日)'
    assert len(catalogue['sources']) == 361
    assert len({s['original_id'] for s in catalogue['sources']}) == 361
    assert [s['original_row'] for s in catalogue['sources']] == list(range(361))
    for s in catalogue['sources']:
        assert isinstance(s['original_id'], str) and s['name']
        assert isinstance(s['notes'], dict)
        assert 0 <= s['ra_deg'] < 360 and -90 <= s['dec_deg'] <= 90
        assert 0 <= s['l_deg'] < 360 and -90 <= s['b_deg'] <= 90
        assert all(math.isfinite(s[k]) for k in ('ra_deg','dec_deg','l_deg','b_deg'))


def test_authority_and_fk5_roundtrip(catalogue):
    counts = {'Galactic': 0, 'RA/Dec': 0}
    for s in catalogue['sources']:
        p = s['notes']['position']['original']
        counts[p['authority']] += 1
        c = SkyCoord(s['ra_deg']*u.deg, s['dec_deg']*u.deg, frame=mod.FRAME)
        if p['authority'] == 'Galactic':
            reference = SkyCoord(p['glon']*u.deg, p['glat']*u.deg, frame='galactic')
            assert c.galactic.separation(reference).arcsec < 1e-6
        else:
            reference = SkyCoord(p['ra'], p['dec'], unit=(u.hourangle,u.deg), frame=mod.FRAME)
            assert c.separation(reference).arcsec < 1e-6
        assert s['notes']['position']['frame'] == 'FK5'
        assert s['notes']['position']['equinox'] == 'J2000'
    assert counts == {'Galactic':20, 'RA/Dec':341}


def test_missing_epoch_is_evidence_based(by_id):
    s = by_id['WpcNUy']
    assert s['ra_deg'] == pytest.approx(292.25)
    assert s['dec_deg'] == pytest.approx(17.75)
    p = s['notes']['position']
    assert p['original']['epoch'] is None
    assert 's41586-021-03498-z' in p['epoch_evidence']['reference_url']
    with pytest.raises(ValueError, match='Unestablished'):
        mod.coordinates({'_id':'WpcNUy','position':{'epoch':None,'comment':'J2000'}})


def test_unknown_footprints_never_become_zero_radius(catalogue):
    assert any(s['notes']['morphology']['parameters']['is_extended']['value'] for s in catalogue['sources'])
    for s in catalogue['sources']:
        assert s['planning_radius_deg'] is None
        assert s['footprint_known'] is False
        assert s['footprint_kind'] == 'unknown_hard_boundary'


def test_placeholder_flags_and_inactive_redshift(catalogue, by_id):
    p = by_id['00sLaj']['notes']['flux']['parameters']
    assert p['crab_fraction']['value'] is None
    assert p['crab_fraction']['upstream_value'] == 0
    assert p['spectral_index']['state'] == 'zero_placeholder_or_unconfirmed'
    for s in catalogue['sources']:
        for group in ('flux','distance','morphology'):
            for item in s['notes'][group]['parameters'].values():
                raw = item['upstream_value']
                if type(raw) in (int,float) and raw == 0:
                    assert item['value'] is None
        d = s['notes']['distance']['parameters']
        if not d['is_redshift']['value']:
            assert d['redshift']['value'] is None
        else:
            assert d['kpc']['value'] is None
    rs = next(s for s in catalogue['sources'] if s['name']=='RS Ophiuchi')
    assert rs['notes']['distance']['parameters']['redshift']['upstream_value'] == 4.2
    assert rs['notes']['distance']['parameters']['redshift']['value'] is None
    alternatives = {m['value_expression'] for m in rs['notes']['measurements'] + rs['notes']['unverified_excerpts']
                    if m['parameter'] == 'reported_distance_alternative'}
    assert {'1.4kpc', '2.3 kpc', '2.7 kpc', '4200 +/- 900 pc'} <= alternatives


def test_multi_class_discovery_and_measurements(catalogue, by_id):
    crab = by_id['06r8mb']['notes']
    assert len(crab['types']) >= 3
    assert crab['seen_by']
    hawc = by_id['00sLaj']['notes']
    assert hawc['discovery']['discovered_by'] is None
    assert hawc['seen_by'][0]['name'] == 'HAWC'
    facts = by_id['EDm9lI']['notes']['measurements']
    indices = [f for f in facts if f['parameter'] == 'Spectral Index']
    assert {f['value_expression'] for f in indices} >= {'2.21 +/- 0.11','2.70 +/- 0.22'}
    assert {f['component'].split()[0] for f in indices} == {'WCDA','KM2A'}
    fluxes = [f for f in facts if f['parameter'] == 'Diff. Flux, N0, at E0']
    assert len(fluxes) == 2
    assert all('TeV-1' in f['unit_tokens'] and 'Q08dSU' in f['citation_ids'] for f in fluxes)


def test_citation_closure_and_source_provenance(catalogue):
    refs = catalogue['references']
    assert len(refs) == 4005
    for s in catalogue['sources']:
        n = s['notes']
        assert not (set(n['citation_ids'])-refs.keys())
        assert n['source_url'] == n['source_api_url']
        assert n['source_url'].endswith('/api/sources/'+s['original_id'])
        assert len(n['detail_sha256']) == 64
        for m in n['measurements']:
            assert set(m['citation_ids']) <= refs.keys()
            assert all(url.startswith(('https://','http://')) for url in m['reference_urls'])


def test_publication_minimization(catalogue):
    serialized = json.dumps(catalogue, ensure_ascii=False)
    for forbidden in ('<script','<table','<blockquote','<br>','comment_public": "','A selection of information for each of the 90 sources'):
        assert forbidden not in serialized
    assert catalogue['provenance']['license'] is None
    for s in catalogue['sources']:
        for m in s['notes']['measurements']:
            assert len(m['parameter']) <= 100
            assert len(m['parameter']) + len(m['value_expression']) <= 220


def test_html_safety_and_no_boilerplate():
    html = '<script>alert(1)</script><br>From <a href="javascript:alert(1)">bad</a><br>Flux: 1 +/- 0.1 TeV<br>'
    assert mod.plain(html).find('alert') == -1
    f = mod.extract_facts(html,'flux',[], 'https://example.org')[0]
    assert f['value_expression'] == '1 +/- 0.1 TeV'
    assert f['reference_urls'] == []
    assert mod.extract_facts('<blockquote>"'+('Long copyrighted narrative '*30)+'Flux: 123</blockquote>','flux',[], 'https://example.org') == []


def test_associations_are_candidate_only_and_many_to_many():
    a = mod.load(ROOT/'data/catalogues/tevcat-associations.json')
    assert a['verified_associations'] == []
    assert a['provenance']['official_2lhaaso_textual_mentions'] == 0
    assert a['provenance']['target_sha256'] == mod.sha256(ROOT/'data/2LHAASO.txt')
    assert len(a['candidates']) == 186
    assert any(e['ambiguous'] for e in a['candidates'])
    assert any(e['tevcat_candidate_degree']>1 for e in a['candidates'])
    assert any(e['lhaaso_candidate_degree']>1 for e in a['candidates'])
    assert all(e['evidence']==[] and e['status']=='candidate_only' for e in a['candidates'])
    assert all(e['separation_deg']<=0.5 for e in a['candidates'])


def test_strict_physical_parameter_whitelist(by_id):
    bad = ('From VERITAS Collaboration: (2018):',
           'From MAGIC Collaboration: (2018):',
           'divided into: <15% in energy scale, 11-18% in flux normalization',
           'TS of 6.1, and the elliptical Gaussian with TS: 8.2',
           '03: 10 UTC observations', 'The authors note: flux 3.2',
           'This is the position reported in TeVCat. - R.A. (J2000): 12 deg')
    for text in bad:
        assert mod.extract_facts(text, 'comment_public', ['fake'], 'https://example.org') == []
    txs = by_id['HpuBf6']['notes']['measurements']
    assert any(m['parameter'] == 'spectral index' and '4.8' in m['value_expression'] for m in txs)
    assert not any(m['parameter'].startswith('From') or m['parameter']=='divided into' for m in txs)


def test_line_reference_resolution_and_no_source_bibliography_leak(catalogue, by_id):
    references = {'a': {'bibcode':'2018ApJ...861L..20A', 'url':'https://ui.adsabs.harvard.edu/abs/2018ApJ...861L..20A'},
                  'b': {'bibcode':'2020ApJ...905...76A', 'url':'https://ui.adsabs.harvard.edu/abs/2020ApJ...905...76A'}}
    html = ('From <a href="https://ui.adsabs.harvard.edu/abs/2018ApJ...861L..20A/abstract">VERITAS</a> (2018):<br>'
            'Spectral index: 4.8 +/- 1.3<br>From unlinked author (2020):<br>Spectral index: 3.0')
    facts = mod.extract_facts(html, 'comment_public', ['a','b'], 'https://example.org', references)
    assert facts[0]['citation_ids'] == ['a']
    assert facts[1]['citation_ids'] == []
    assert facts[1]['citation_scope'] == 'unresolved_source_link_only'
    assert mod.matched_references(['https://ui.adsabs.harvard.edu/abs/UNKNOWN'], references) == []
    crab = by_id['06r8mb']['notes']
    assert len(crab['references']['citation_ids']) > 50
    spectral = [m for m in crab['measurements'] if 'spectral index' in m['parameter'].lower()]
    assert spectral
    assert all(len(m['citation_ids']) <= len(m['reference_urls']) for m in spectral)
    for source in catalogue['sources']:
        for m in source['notes']['measurements']:
            # Every ID independently resolves from only this fact's retained URLs.
            subset = {rid:catalogue['references'][rid] for rid in m['citation_ids']}
            assert mod.matched_references(m['reference_urls'], subset) == m['citation_ids']
            if not m['reference_urls']:
                assert m['citation_ids'] == []


def test_verified_structured_units_and_unknown_unit_state(catalogue, by_id):
    assert by_id['06r8mb']['notes']['flux']['parameters']['crab_fractionE']['unit'] == 'GeV'
    angular = {'semi_maj_68','semi_min_68','semi_maj_68_err','semi_min_68_err','angle_68','angle_68_err'}
    for source in catalogue['sources']:
        for key in angular:
            item = source['notes']['morphology']['parameters'][key]
            assert item['unit'] == 'deg'
            assert item['unit_source']['url'].endswith('/dist/bundle.js')
            assert len(item['unit_source']['sha256']) == 64
        for group in ('distance','flux','morphology'):
            for item in source['notes'][group]['parameters'].values():
                if item['state']=='reported' and type(item['value']) in (float,int):
                    assert item['unit'] is not None
    result = mod.clean_parameters({'mystery_numeric': 12.3}, 'flux')['parameters']['mystery_numeric']
    assert result['value'] == 12.3
    assert result['unit'] is None and result['state']=='unit_unverified'


def test_unverified_excerpts_are_not_structured_measurements(catalogue):
    assert catalogue['provenance']['normalization_version'] == 4
    all_records = 0
    for source in catalogue['sources']:
        notes = source['notes']
        for measurement in notes['measurements']:
            assert measurement['citation_ids']
            assert measurement['evidence_status'] == 'reference_link_resolved_not_independently_remeasured'
        for excerpt in notes['unverified_excerpts']:
            assert not excerpt['citation_ids'] or excerpt.get('expression_rendering_status') == 'unverified'
            assert excerpt['evidence_status'] == 'unverified_excerpt'
            assert excerpt['interpretation'] == 'unverified_excerpt_not_adopted_scientific_measurement'
            assert excerpt['source_url'].startswith('https://tevcat2.tevcat.org/')
        all_records += len(notes['measurements']) + len(notes['unverified_excerpts'])
    assert all_records == 4090  # Downgrade, not deletion of uncertain records.


@pytest.mark.parametrize('expression', [
    '278.6−0.03+0.03278.6^{+0.03}_{-0.03}',
    '2.314−0.015+0.0162.314^{+0.016}_{-0.015}',
])
def test_mathml_tex_dual_representation_never_supported(expression):
    record = {'value_expression': expression, 'citation_ids': ['real_reference'],
              'source_url': 'https://tevcat2.tevcat.org/api/sources/test'}
    supported, unverified = mod.classify_measurements([record])
    assert supported == []
    assert unverified[0]['value_expression'] == expression
    assert unverified[0]['citation_ids'] == ['real_reference']
    assert unverified[0]['expression_rendering_status'] == 'unverified'
    assert record.get('evidence_status') is None  # Classifier does not mutate input.


def test_whole_catalogue_expression_rendering_gate(catalogue, by_id):
    affected_sources = set()
    cited_downgrades = 0
    for source in catalogue['sources']:
        for measurement in source['notes']['measurements']:
            assert mod.expression_rendering_issue(measurement['value_expression']) is None
            assert not any(ch in measurement['value_expression'] for ch in '{}\\\\')
        for excerpt in source['notes']['unverified_excerpts']:
            if mod.expression_rendering_issue(excerpt['value_expression']):
                assert excerpt['expression_rendering_status'] == 'unverified'
                assert excerpt['evidence_status'] == 'unverified_excerpt'
                if excerpt['citation_ids']:
                    affected_sources.add(source['original_id'])
                    cited_downgrades += 1
    assert len(affected_sources) == 33
    assert cited_downgrades == 187
    for sid, expression in [('4xiQfb', '278.6−0.03+0.03278.6^{+0.03}_{-0.03}'),
                            ('66DvGb', '2.314−0.015+0.0162.314^{+0.016}_{-0.015}')]:
        assert any(x['value_expression'] == expression for x in by_id[sid]['notes']['unverified_excerpts'])
    assert mod.expression_rendering_issue('2.314 +0.016 -0.015') is None
    assert mod.expression_rendering_issue('(0.34 +/- 0.06) e-13 cm-2 s-1 TeV-1') is None


def test_reproducible_from_staging(catalogue):
    staging = Path(os.environ.get('TEVCAT_STAGING','/data/lact/wz/skyward-data-staging/tevcat-20260916'))
    if not staging.is_dir():
        pytest.skip('Offline staging snapshot unavailable')
    assert mod.build(staging) == catalogue
    a = mod.association_audit(catalogue, ROOT/'data/2LHAASO.txt')
    assert a == mod.load(ROOT/'data/catalogues/tevcat-associations.json')
