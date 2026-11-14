from clientmagnet.audit import audit_page
from clientmagnet.sample import SAMPLE_HTML, SAMPLE_URL
import pytest


def scores(report):
    return {x['key']: x['status'] for x in report['checks']}


def test_sample_audit_returns_real_rules():
    r = audit_page(SAMPLE_URL, SAMPLE_HTML, source="synthetic_sample")
    assert r['scores']['overall'] > 80
    assert r['summary']['total'] >= 14
    assert r['url'].startswith('https://')
    assert r['source'] == 'synthetic_sample'
    assert 'Lighthouse' in r['limitations']


def test_missing_basics_fail():
    r = audit_page("https://example.org", "<html><head></head><body>Hello</body></html>")
    for k in ('title', 'description', 'h1', 'lang', 'viewport', 'cta', 'contact'):
        assert scores(r)[k] == 'fail'
    assert r['scores']['overall'] < 55


def test_missing_alt_detected():
    r = audit_page("https://example.org", "<html><body><img src='x'></body></html>")
    assert scores(r)['alts'] == 'fail'
    assert '1 / 1' in next(x['evidence'] for x in r['checks'] if x['key'] == 'alts')


def test_empty_alt_is_valid_for_decorative_image():
    r = audit_page('https://example.org', '<html><img src="decorative.svg" alt=""></html>')
    assert scores(r)['alts'] == 'pass'


def test_multiple_h1_fails():
    r = audit_page('https://example.org', '<h1>One</h1><h1>Two</h1>')
    assert scores(r)['h1'] == 'fail'


def test_form_accessibility_pass_and_fail():
    okay = audit_page('https://example.org', '<form><label for="a">Email</label><input id="a"></form>')
    bad = audit_page('https://example.org', '<form><input type="text"></form>')
    assert scores(okay)['labels'] == 'pass'
    assert scores(bad)['labels'] == 'fail'


def test_accessible_aria_label_counts():
    r = audit_page('https://example.org', '<input aria-label="email address">')
    assert scores(r)['labels'] == 'pass'


def test_noindex_fails():
    r = audit_page('https://example.org', '<meta name="robots" content="noindex,follow">')
    assert scores(r)['robots'] == 'fail'


def test_heading_jump_warning():
    r = audit_page('https://example.org', '<h1>Hi</h1><h4>Too far</h4>')
    assert scores(r)['headings'] == 'warning'


def test_new_tab_noopener_warning():
    r = audit_page('https://example.org', '<a href="https://other.org" target="_blank">Go</a>')
    assert scores(r)['new_tabs'] == 'warning'
    good = audit_page('https://example.org', '<a href="https://other.org" rel="noopener" target="_blank">Go</a>')
    assert scores(good)['new_tabs'] == 'pass'


def test_cta_pattern_is_bounded():
    r = audit_page('https://example.org', '<a href="/book">Book a consultation</a>')
    assert scores(r)['cta'] == 'pass'


def test_priorities_include_evidence():
    r = audit_page('https://example.org', '<body/>')
    assert r['priority_recommendations']
    assert all(x['evidence'] and x['recommendation'] for x in r['priority_recommendations'])
    assert len(r['priority_recommendations']) <= 5


def test_html_size_limit():
    with pytest.raises(ValueError):
        audit_page('https://example.org', '<p>' + 'x'*751_000)


def test_fetch_timing_not_fabricated():
    r = audit_page('https://example.org', '<p>Test</p>')
    assert r['timing']['measured_fetch_ms'] is None
    timed = audit_page('https://example.org', '<p>Test</p>', fetch_ms=250)
    assert timed['timing']['measured_fetch_ms'] == 250


def test_valid_iso_url_and_id():
    r = audit_page('https://EXAMPLE.org', '<html></html>')
    assert r['url'] == 'https://example.org/'
    assert len(r['id']) == 32
