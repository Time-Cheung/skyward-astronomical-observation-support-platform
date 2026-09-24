#!/usr/bin/env python3
"""Build the fact-only TeVCat snapshot; never fetch network data.

Schema v1 (shared catalogue interface): catalogue_id/label/provenance/sources.
Sources: original_id:str, original_row:int (zero-based official listing), name:str,
ra_deg/dec_deg:float (FK5 J2000), l_deg/b_deg:float (Galactic),
planning_radius_deg:null, footprint_known:false, footprint_kind:str, notes:object.
notes contains aliases, all classifications, discovery, coordinates, parameters,
measurements, references and provenance. Measurement values may be *expressions*
with uncertainties/limits; they are not silently coerced to scalar best values.
Citation IDs resolve through the top-level references mapping. Brief fact rows
have local source URLs and reference context; unparsed prose remains in staging.

No Gaussian, containment or analysis template is a hard source boundary. Even an
upstream is_extended=false is not proof of a zero-radius physical footprint.
No name/position matching may create a verified cross-catalogue association.

Usage: python scripts/build_tevcat_catalogue.py --staging PATH
       [--output-dir data/catalogues] [--lhaaso data/catalogues/1lhaaso.json]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

from astropy import __version__ as astropy_version
from astropy import units as u
from astropy.coordinates import FK5, SkyCoord
from astropy.time import Time

FRAME = FK5(equinox=Time('J2000'))
BASE = 'https://tevcat2.tevcat.org'
LABEL = 'TeVCat (截止到2026年09月16日)'
NUMBER = re.compile(r'(?<!\w)[+−-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+−-]?\d+)?')
UNITS = re.compile(r'(?<![A-Za-z])(?:[kMGTPE]?eV(?:-1)?|[kM]?pc|deg|arcmin|arcsec|mas|cm-2|s-1|erg|photons?|ph|Crab|CU|sigma|kyr|yr|days?|hours?|hr|%)(?![A-Za-z])', re.I)
# Only an entire physical-parameter label can qualify; never search prose for RA.
PARAMETER = re.compile(
    r'^(?:(?:R\.?A\.?|Dec\.?|declination|longitude|latitude|l|b)(?:\s*\([^)]*\))?'
    r'|(?:(?:intrinsic|observed|differential|integral|VHE|photon|best-fit|mean|fiducial|source|major|minor|Gaussian)\s+)*'
    r'(?:spectral (?:index|indices|parameter)|specral index|photon index|index|flux(?: normalis[ae]tion| normalization)?|normalis[ae]tion|normalization|'
    r'diff\. flux|differential photon flux|energy|pivot energy|decorrelation energy|cut-?off energy|E_max|E_iso|'
    r'significance|detection significance|test statistic|TS|sqrt\(TS\)|size|extension|extent|width|diameter|radius|'
    r'semi-major axis|semi-minor axis|Gaussian width|position(?:al)? (?:angle|uncertainty)|statistical (?:error|uncertainty)|'
    r'systematic uncertainty|syst\. uncertainty|uncertainty|exposure|on-source events/off-source events|distance(?: d)?|'
    r'redshift(?:,? z)?|alpha(?:_HESS|_LAT)?|beta|z|T0|T90)'
    r'(?:\s*(?:\([^)]*\)|\[[^]]*\]|(?:at|above|during|for|of|in|along)\s+[^:;]+|[>,]\s*[^:;]+|range|threshold|upper limit at 95% confidence level))*'
    r'|(?:higher|lower) significance component \(TS\)'
    r'|\d+% containment radius'
    r'|(?:Period [AB]|\d{4} Data|(?:H\.E\.S\.S\.|MAGIC|VERITAS)(?: [\d/–-]+(?: data)?)?(?: \([^)]*\))?|'
    r'(?:All orbital phases|Orbital phase [\d.-]+)(?: \([^)]*\))?)[, ]+spectral index(?: \([^)]*\))?'
    r'|(?:power law(?: with exponential cut off)?|log parabola) spectral index)$', re.I)
UNIT_SOURCE = {'url': BASE + '/dist/bundle.js',
               'sha256': 'bda437217b34a886f98d1ee7338261e33b13b94c94491c3771ea527696a7c086',
               'checked_date': '2026-09-16', 'method': 'official UI field labels and form help'}


def reference_lookup(references):
    """Build exact URL/bibcode indexes once; no fuzzy publication association."""
    index = {'urls': {}, 'bibcodes': {}}
    for rid, ref in references.items():
        if ref.get('url'):
            index['urls'].setdefault(normalized_reference_url(ref['url']), []).append(rid)
        if ref.get('bibcode'):
            index['bibcodes'].setdefault(ref['bibcode'], []).append(rid)
    return index


def normalized_reference_url(url):
    p = urlsplit(unquote(url or ''))
    return (p.netloc.lower(), p.path.rstrip('/').removesuffix('/abstract'), p.query)


def matched_references(urls, references):
    """Resolve only explicit URL/bibcode equality, never the source bibliography."""
    index = references if references and 'urls' in references else reference_lookup(references or {})
    found = set()
    for url in urls:
        found.update(index['urls'].get(normalized_reference_url(url), []))
        decoded = unquote(url)
        # ADS bibcodes are exactly 19 characters; punctuation including '&' stays.
        for token in re.findall(r'(?<![A-Za-z0-9])(\d{4}[^/\s?&#=]{15})(?![A-Za-z0-9])', decoded):
            found.update(index['bibcodes'].get(token, []))
        for segment in re.split(r'[/=?#]', decoded):
            found.update(index['bibcodes'].get(segment, []))
    return sorted(found)


def citation_evidence(urls, context_urls, references):
    selected = urls or context_urls
    scope = 'inline_reference_url' if urls else ('preceding_explicit_reference_header' if context_urls else 'unresolved_source_link_only')
    return {'citation_ids': matched_references(selected, references),
            'reference_urls': list(dict.fromkeys(selected)), 'citation_scope': scope}


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe_url(value):
    return value if isinstance(value, str) and urlsplit(value).scheme in ('http', 'https') else None


class FactHTML(HTMLParser):
    """HTML-to-lines with links, without executing HTML or publishing raw prose."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self.parts, self.links = [], [], []
        self.suppressed = 0

    def flush(self):
        text = re.sub(r'\s+', ' ', ''.join(self.parts)).strip()
        if text:
            self.lines.append((text, list(dict.fromkeys(self.links))))
        self.parts, self.links = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.suppressed += 1
        if self.suppressed:
            return
        if tag in ('br', 'tr', 'p', 'blockquote', 'hr', 'li'):
            self.flush()
        if tag == 'td':
            self.parts.append(' ')
        if tag == 'a':
            url = safe_url(dict(attrs).get('href'))
            if url:
                self.links.append(url)

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.suppressed = max(0, self.suppressed - 1)
        if not self.suppressed and tag in ('tr', 'p', 'blockquote', 'li'):
            self.flush()

    def handle_data(self, data):
        if not self.suppressed:
            self.parts.append(data)


def lines(html):
    parser = FactHTML()
    parser.feed(html or '')
    parser.flush()
    return parser.lines


def plain(value):
    if value is None:
        return None
    return ' '.join(text for text, _ in lines(str(value)))


def collect_ids(value):
    found = set()
    if isinstance(value, dict):
        found.update(x for x in value.get('citation_ids', []) if x is not None)
        for item in value.values():
            found.update(collect_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(collect_ids(item))
    return found


def extract_facts(html, field, citation_ids, source_url, references=None):
    """Retain short parameter rows, not paragraphs or entire comment_public.

    Values and units stay expressions: no interpretation of alternate fits,
    +/- errors, limits, confidence levels or power-law exponents is invented.
    Multi-row components have an explicit component context. Citation scope is
    stated rather than pretending a field-level citation proves each value.
    """
    facts, context_urls, component = [], [], None
    for text, urls in lines(html):
        text = text.strip(' -•').removeprefix('...').strip()
        if re.match(r'^(From|Reference|First LHAASO Catalog)\b', text, re.I):
            context_urls, component = urls, None
            continue
        if re.match(r'^(Source Notes|Possible Origin)', text, re.I):
            context_urls, component = [], None
            continue
        if re.search(r'(?:higher|lower) significance component', text, re.I):
            component = plain(text.split(':', 1)[-1])
        # Long prose, direct quotations and boilerplate are deliberately omitted.
        if not (1 <= len(text) <= 220 and NUMBER.search(text)):
            continue
        if text.startswith(('"', '“')) or len(text.split()) > 32:
            continue
        if ':' not in text and '=' not in text:
            continue
        if re.search(r'\b(?:source lies|nearest|association|potentially|copyright|provided in TeVCat|et al\.|Table \d|Figure \d)\b', text, re.I):
            continue
        split = re.split(r':|(?<![<>])=', text, maxsplit=1)
        if len(split) != 2 or not NUMBER.search(split[1]):
            continue
        parameter, expression = [x.strip() for x in split]
        if not PARAMETER.fullmatch(parameter) or len(parameter) > 100 or len(parameter.split()) > 12:
            continue
        if re.search(r'\b(?:and the|gives|yielding|yields|was |were |is |are |updated|reported|authors|found|leading)\b', parameter, re.I):
            continue
        # A value must begin like a measurement, not a narrative with a later year.
        if not re.match(r'^(?:[<>=~≈+−\-()\s]*\d|[<>=~≈+−\-()\s]*\.\d|(?:WCDA|KM2A)\s*\()', expression, re.I):
            continue
        if re.search(r'\b(?:we |in two|under partial|circular|consecutive|estimated|cloud coverage)\b', expression, re.I):
            continue
        facts.append({
            'field': field, 'parameter': parameter, 'value_expression': expression,
            'unit_tokens': list(dict.fromkeys(UNITS.findall(parameter + ' ' + expression))),
            'component': component, **citation_evidence(urls, context_urls, references),
            'source_url': source_url, 'interpretation': 'reported_fact_not_planning_boundary',
        })
    return facts


def extract_distance_alternatives(html, citation_ids, source_url, references=None):
    """Extract numerical pc/kpc expressions, not the surrounding quoted prose.

    These remain reported alternatives, never a preferred distance or redshift.
    Local reference links and uncertainty qualifiers are retained separately.
    """
    result, context_urls = [], []
    pattern = re.compile(r'(?<![\w.])(?:[<>~≈]\s*)?\(?\d+(?:\.\d+)?(?:\s*(?:\+/-|±|[+−-])\s*\d+(?:\.\d+)?)*\)?\s*(?:kpc|Mpc|pc)\b')
    for text, urls in lines(html):
        if text.startswith('From '):
            context_urls = urls
            continue
        for match in pattern.finditer(text):
            result.append({'field': 'distance', 'parameter': 'reported_distance_alternative',
                           'value_expression': match.group(),
                           'unit_tokens': UNITS.findall(match.group()), 'component': None,
                           **citation_evidence(urls, context_urls, references),
                           'source_url': source_url,
                           'interpretation': 'reported_alternative_not_adopted_distance',
                           'qualifiers': [word for word in ('uncertain', 'questionable', 'limit', 'canonical', 'approximately', 'suggests') if word in text.lower()]})
    return result


def expression_rendering_issue(expression):
    """Fail closed on unparsed TeX/MathML residuals, including dual rendering.

    An explicit citation does not validate HTML rendering. Do not guess how to
    remove a concatenated presentation+annotation value or which errors belong
    to it. Keep the exact short excerpt and its references for manual checking.
    """
    if re.search(r'[{}\\\\]|(?:\^|_)\s*(?:[+−-]?\d|\{)|</?(?:math|annotation)\b', expression):
        return 'unparsed_mathml_or_tex_possible_duplicate_representation'
    return None


def classify_measurements(measurements):
    supported, unverified = [], []
    for original in measurements:
        measurement = dict(original)
        issue = expression_rendering_issue(measurement['value_expression'])
        if measurement['citation_ids'] and issue is None:
            measurement['evidence_status'] = 'reference_link_resolved_not_independently_remeasured'
            supported.append(measurement)
        else:
            measurement['evidence_status'] = 'unverified_excerpt'
            measurement['interpretation'] = 'unverified_excerpt_not_adopted_scientific_measurement'
            if issue:
                measurement['expression_rendering_status'] = 'unverified'
                measurement['expression_rendering_issue'] = issue
                measurement['unverified_reason'] = 'Expression rendering not validated; citation resolution does not establish an intact numerical expression.'
            else:
                measurement['unverified_reason'] = 'No fact-level reference resolved.'
            unverified.append(measurement)
    return supported, unverified


def clean_parameters(block, group):
    """Preserve every structured scalar, with null/zero states made explicit."""
    result = {}
    units = {'kpc': 'kpc', 'kpc_err': 'kpc', 'redshift': '1', 'redshift_err': '1',
             'crab_fraction': 'Crab', 'crab_fractionE': 'GeV',
             'spectral_index': '1', 'spectral_index_err': '1',
             **{name: 'deg' for name in ('semi_maj_68', 'semi_min_68', 'angle_68',
                                        'semi_maj_68_err', 'semi_min_68_err', 'angle_68_err')}}
    for key, value in block.items():
        if key in ('comment', '_id', 'created_at', 'updated_at', 'citation_ids'):
            continue
        if isinstance(value, bool):
            normalized, state = value, 'reported_flag'
        elif value is None or value == '':
            normalized, state = None, 'missing'
        elif isinstance(value, (int, float)) and value == 0:
            normalized, state = None, 'zero_placeholder_or_unconfirmed'
        else:
            normalized, state = plain(value) if isinstance(value, str) else value, 'reported'
        if group == 'distance' and key.startswith('redshift') and not block.get('is_redshift'):
            normalized, state = None, 'inactive_redshift_field'
        if group == 'distance' and key.startswith('kpc') and block.get('is_redshift'):
            normalized, state = None, 'inactive_distance_field'
        if state == 'reported' and type(normalized) in (int, float) and key not in units:
            state = 'unit_unverified'
        result[key] = {'value': normalized, 'state': state,
                       'unit': units.get(key),
                       'unit_source': (dict(UNIT_SOURCE, field=key) if key in units else None),
                       'upstream_value': plain(value) if isinstance(value, str) else value}
    return {'parameters': result, 'citation_ids': sorted(x for x in block.get('citation_ids', []) if x),
            'unit_policy': 'null means not established from this field; see measurement expressions',
            'semantic_warning': ('Upstream *_68 names are not validated containment definitions; comments may describe Gaussian sigma, 39% containment or templates. No hard boundary follows.'
                                 if group == 'morphology' else None)}


def coordinates(detail):
    p = detail['position']
    epoch = p['epoch']
    evidence = None
    if epoch is None:
        text = plain(p.get('comment')) or ''
        if not (detail['_id'] == 'WpcNUy' and 'J2000' in text and '292.25' in text
                and '+17.75' in text and '2021' in text
                and 's41586-021-03498-z' in (p.get('comment') or '')):
            raise ValueError(f"Unestablished coordinate epoch: {detail['_id']}")
        epoch = 'J2000'
        evidence = {'reason': 'position.comment explicitly labels both coordinates J2000',
                    'reference_url': 'https://www.nature.com/articles/s41586-021-03498-z',
                    'citation_ids': p['citation_ids'], 'ra_deg': 292.25, 'dec_deg': 17.75}
    if epoch != 'J2000':
        raise ValueError(f'Unsupported equinox {epoch}')
    if p['authority'] == 'Galactic':
        c = SkyCoord(l=p['glon'] * u.deg, b=p['glat'] * u.deg, frame='galactic').transform_to(FRAME)
    elif p['authority'] == 'RA/Dec':
        c = SkyCoord(p['ra'], p['dec'], unit=(u.hourangle, u.deg), frame=FRAME)
    else:
        raise ValueError(f"Unknown coordinate authority {p['authority']}")
    g = c.galactic
    original = {k: v for k, v in p.items() if k not in ('comment', '_id', 'created_at', 'updated_at')}
    return c, g, {'frame': 'FK5', 'equinox': epoch, 'original': original,
                  'epoch_evidence': evidence,
                  'sexagesimal_warning': ('Upstream seconds=60 normalized by Astropy to next minute; original retained'
                                          if any(str(p.get(k, '')).split()[-1:] == ['60'] for k in ('ra', 'dec')) else None),
                  'coordinate_policy': 'transform the authoritative pair only',
                  'uncertainty_policy': 'original error values are unvalidated; zero is not exact position'}


def reference_record(ref):
    return {k: (safe_url(v) if k == 'url' else plain(v)) for k, v in ref.items()
            if k in ('_id', 'author', 'bibcode', 'date', 'journal', 'title', 'type', 'url')}


def build(staging):
    staging = Path(staging)
    manifest, audit = load(staging/'manifest.json'), load(staging/'audit_report.json')
    if not (manifest['complete'] and audit['acquisition_validated'] and not audit['failures']):
        raise ValueError('Acquisition is not complete and validated')
    listing = load(staging/'sources.json')['data']
    if len(listing) != 361 or len({x['_id'] for x in listing}) != 361:
        raise ValueError('Expected 361 unique official sources')
    for dirname, expected in (('details', 361), ('citations', 361), ('references', 67)):
        if len(list((staging/dirname).glob('*.json'))) != expected:
            raise ValueError(f'Unexpected {dirname} file count')
    if load(staging/'sources_at_finish.json')['data'] != listing:
        raise ValueError('Official listing changed during acquisition')
    refs, hashes = {}, {}
    paths = [staging/x for x in ('manifest.json', 'audit_report.json', 'sources.json',
             'sources_at_finish.json', 'catalogs.json', 'types.json', 'observatories.json')]
    paths += sorted((staging/'details').glob('*.json')) + sorted((staging/'citations').glob('*.json'))
    paths += sorted((staging/'references').glob('*.json'))
    for path in paths:
        hashes[path.relative_to(staging).as_posix()] = sha256(path)
        envelope = load(path)
        if path.parent.name in ('citations', 'references'):
            records = envelope['data'] if isinstance(envelope['data'], list) else [envelope['data']]
            for ref in records:
                refs[ref['_id']] = reference_record(ref)
    if len(refs) != 4005:
        raise ValueError(f'Expected 4005 unique references, got {len(refs)}')
    instruments = {r['_id']: plain(r['name']) for r in load(staging/'observatories.json')['data']}
    ref_index = reference_lookup(refs)
    sources, authorities = [], Counter()
    for row, item in enumerate(listing):
        sid = item['_id']
        envelope = load(staging/'details'/f'{sid}.json')
        load(staging/'citations'/f'{sid}.json')  # Per-source citation response must exist.
        d = envelope['data']
        if d['_id'] != sid:
            raise ValueError('Detail/listing identity mismatch')
        ids = collect_ids(d)
        if ids - refs.keys():
            raise ValueError(f'Unresolved citations for {sid}: {ids - refs.keys()}')
        c, g, position = coordinates(d)
        authorities[d['position']['authority']] += 1
        source_url = envelope['url']
        fields = {k: d[k].get('comment') for k in ('position', 'distance', 'flux', 'morphology')}
        fields['comment_public'] = d.get('comment_public')
        measurements = []
        for field, html in fields.items():
            field_ids = d.get('citation_ids', []) if field == 'comment_public' else d[field].get('citation_ids', [])
            measurements.extend(extract_facts(html, field, field_ids, source_url, ref_index))
            if field == 'distance':
                measurements.extend(extract_distance_alternatives(html, field_ids, source_url, ref_index))
        measurements, unverified_excerpts = classify_measurements(measurements)
        sources.append({
            'original_id': sid, 'original_row': row, 'name': plain(d['names']['common'] or d['name']),
            'ra_deg': float(c.ra.deg), 'dec_deg': float(c.dec.deg),
            'l_deg': float(g.l.deg), 'b_deg': float(g.b.deg),
            'planning_radius_deg': None, 'footprint_known': False, 'footprint_kind': 'unknown_hard_boundary',
            'notes': {
                'tev_name': plain(d['name']), 'aliases': [plain(a) for a in d['names']['other']],
                'catalogue_group': plain(d['catalog_id_data']['name']),
                'primary_type': plain((d.get('source_type_id_data') or {}).get('name')),
                'types': [{'name': plain(t.get('name')), 'nickname': plain(t.get('nickname'))} for t in d['type_tags_data']],
                'type_ids': d['type_tag_ids'], 'position': position,
                'discovery': {'date': d['discovery_date'], 'discovered_by_id': d['discovered_by_id'],
                              'discovered_by': instruments.get(d['discovered_by_id'])},
                'seen_by': [{'id': i, 'name': instruments.get(i)} for i in d['seen_by_ids']],
                'distance': clean_parameters(d['distance'], 'distance'),
                'flux': clean_parameters(d['flux'], 'flux'),
                'morphology': clean_parameters(d['morphology'], 'morphology'),
                'measurements': measurements, 'unverified_excerpts': unverified_excerpts, 'citation_ids': sorted(ids),
                'references': {'citation_ids': sorted(ids), 'scope': 'source_bibliography_not_per_measurement_evidence'},
                'other_catalogs': {k: plain(v) for k,v in d['other_catalogs'].items()},
                'source_url': source_url, 'source_api_url': envelope['url'],
                'retrieved_at': envelope['retrieved_at'], 'detail_sha256': hashes[f'details/{sid}.json'],
                'normalization_notes': [
                    'No hard footprint is established; centre-only planning is not full-source coverage.',
                    'Unknown/zero placeholders are not physical zero; upstream values are retained for audit.',
                    'Only short parameter facts are extracted; prose and unparsed results remain in staging.',
                    'Measurement expressions preserve alternate fits and limits; no preferred fit is inferred.',
                ],
            },
        })
    if authorities != {'Galactic': 20, 'RA/Dec': 341}:
        raise ValueError(f'Coordinate authority distribution changed: {authorities}')
    return {
        'schema_version': 1, 'catalogue_id': 'tevcat', 'label': LABEL,
        'units': {'ra_deg': 'deg', 'dec_deg': 'deg', 'l_deg': 'deg', 'b_deg': 'deg', 'planning_radius_deg': 'deg'},
        'provenance': {
            'catalogue_url': BASE, 'snapshot_date': '2026-09-16',
            'attribution': manifest['attribution'], 'license': None,
            'redistribution_policy': 'No explicit reuse license established; structured facts, short parameter extracts and bibliography only. Full original prose stays in private staging.',
            'coordinate_frame': 'FK5', 'equinox': 'J2000', 'astropy_version': astropy_version,
            'normalization_version': 4, 'unit_definition_provenance': UNIT_SOURCE, 'acquisition_counts': {'sources': 361, 'citations_responses': 361, 'supplements': 67, 'references': 4005},
            'authority_counts': dict(authorities), 'input_sha256': hashes,
            'measurement_policy': 'Conservative short-row extraction, not exhaustive prose interpretation. All structured upstream parameter fields retained with validity states; source URLs locate omitted material.',
        },
        'references': dict(sorted(refs.items())), 'sources': sources,
    }


def association_audit(catalogue, lhaaso_path, max_separation_deg=0.5):
    """All candidate edges, never nearest-only or verified identity claims."""
    target_payload = load(lhaaso_path)
    if target_payload.get('catalogue_id') != '1lhaaso':
        raise ValueError('association target must be the public 1LHAASO normalization')
    targets = target_payload['sources']
    candidate_edges = []
    target_coords = SkyCoord([float(x['ra_deg']) for x in targets] * u.deg,
                             [float(x['dec_deg']) for x in targets] * u.deg, frame=FRAME)
    for source in catalogue['sources']:
        c = SkyCoord(source['ra_deg'] * u.deg, source['dec_deg'] * u.deg, frame=FRAME)
        for index, separation in enumerate(c.separation(target_coords).deg):
            if separation <= max_separation_deg:
                target = targets[index]
                candidate_edges.append({'tevcat_id': source['original_id'], 'lhaaso_original_id': target['original_id'],
                                        'lhaaso_name': target['name'], 'separation_deg': float(separation),
                                        'status': 'candidate_only', 'evidence': [],
                                        'reason': 'position_nearby_is_not_identity_evidence'})
    by_tevcat = Counter(e['tevcat_id'] for e in candidate_edges)
    by_lhaaso = Counter(e['lhaaso_original_id'] for e in candidate_edges)
    for edge in candidate_edges:
        edge['tevcat_candidate_degree'] = by_tevcat[edge['tevcat_id']]
        edge['lhaaso_candidate_degree'] = by_lhaaso[edge['lhaaso_original_id']]
        edge['ambiguous'] = edge['tevcat_candidate_degree'] > 1 or edge['lhaaso_candidate_degree'] > 1
    return {'schema_version': 1, 'catalogue_id': 'tevcat', 'target_catalogue_id': '1lhaaso',
            'verified_associations': [], 'candidates': candidate_edges,
            'provenance': {'target_sha256': sha256(lhaaso_path), 'candidate_radius_deg': max_separation_deg,
                           'target_coordinate_assumption': 'FK5 J2000 for candidate audit only; not source identity evidence',
                           'method': 'all pairs within fixed angular separation; no one-to-one assignment',
                           'unpublished_2lhaaso_data_used': False,
                           'manual_enrichment_status': 'inspected existing source_enrichment.json; empty sources mapping',
                           'policy': 'Public 1LHAASO Table 2 coordinates are used only for candidate proximity. Positional coincidence does not establish identity and no unpublished 2LHAASO data are used.'}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staging', required=True, type=Path)
    parser.add_argument('--output-dir', type=Path, default=Path('data/catalogues'))
    parser.add_argument('--lhaaso', type=Path, default=Path('data/catalogues/1lhaaso.json'))
    args = parser.parse_args()
    catalogue = build(args.staging)
    associations = association_audit(catalogue, args.lhaaso)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, obj in [('tevcat.json', catalogue), ('tevcat-associations.json', associations)]:
        path = args.output_dir / name
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        assert load(path) == obj
    print(json.dumps({'sources': len(catalogue['sources']), 'references': len(catalogue['references']),
                      'measurements': sum(len(x['notes']['measurements']) for x in catalogue['sources']),
                      'candidate_edges': len(associations['candidates']), 'verified_associations': 0}))


if __name__ == '__main__':
    main()
