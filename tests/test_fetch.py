from unittest.mock import Mock
import socket
import pytest
from clientmagnet.fetch import validate_url, resolve_global_ips, fetch_html, FetchError


@pytest.mark.parametrize('url', [
    'http://example.org/',
    'file:///etc/passwd',
    'https://user:pass@example.org',
    'https://localhost',
    'https://127.0.0.1',
    'https://[::1]/',
    'https://10.5.7.3/',
    'https://example.local',
    'https://metadata.google.internal',
    'https://example.org:8080/',
    'https://example.org/#fragment',
    'https://example.org/bad\npath',
    'https://example.org?' + 'a'*260,
])
def test_untrusted_urls_rejected(url):
    with pytest.raises(FetchError):
        validate_url(url)


def test_https_url_normalized():
    assert validate_url('https://EXAMPLE.ORG?x=y') == 'https://example.org/?x=y'


def test_domain_with_private_dns_is_rejected(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *args, **kwargs: [
        (socket.AF_INET,socket.SOCK_STREAM,0,'',('93.184.216.34',443)),
        (socket.AF_INET,socket.SOCK_STREAM,0,'',('127.0.0.1',443)),
    ])
    with pytest.raises(FetchError, match='unsafe'):
        resolve_global_ips('example.org')


def test_domain_with_public_dns_accepted(monkeypatch):
    monkeypatch.setattr(socket, 'getaddrinfo', lambda *args, **kwargs: [
        (socket.AF_INET,socket.SOCK_STREAM,0,'',('93.184.216.34',443)),
    ])
    assert resolve_global_ips('example.org') == ['93.184.216.34']


def fake_connection(status=200, html=b'<html><title>Sample</title></html>', content_type='text/html', location=None):
    result = Mock()
    result.status = status
    result.read.return_value = html
    def header(key, default=None):
        return {'Content-Type':content_type, 'Location':location}.get(key, default)
    result.getheader.side_effect = header
    conn = Mock()
    conn.getresponse.return_value = result
    return conn


def test_fetch_one_html_page_without_real_network(monkeypatch):
    monkeypatch.setattr('clientmagnet.fetch.resolve_global_ips', lambda host:['93.184.216.34'])
    monkeypatch.setattr('clientmagnet.fetch.PinnedHTTPSConnection', lambda host,ip:fake_connection())
    r = fetch_html('https://example.org/')
    assert r.status_code == 200
    assert r.size_bytes > 0
    assert 'Sample' in r.html


def test_redirect_back_to_private_host_rejected(monkeypatch):
    monkeypatch.setattr('clientmagnet.fetch.resolve_global_ips', lambda host:['93.184.216.34'])
    monkeypatch.setattr('clientmagnet.fetch.PinnedHTTPSConnection',
                        lambda host,ip:fake_connection(status=302,location='http://127.0.0.1/private'))
    with pytest.raises(FetchError):
        fetch_html('https://example.org/')


def test_fetch_rejects_non_html(monkeypatch):
    monkeypatch.setattr('clientmagnet.fetch.resolve_global_ips', lambda host:['93.184.216.34'])
    monkeypatch.setattr('clientmagnet.fetch.PinnedHTTPSConnection',lambda host,ip:fake_connection(content_type='application/pdf'))
    with pytest.raises(FetchError, match='not an HTML'):
        fetch_html('https://example.org/')


def test_fetch_rejects_huge_pages(monkeypatch):
    monkeypatch.setattr('clientmagnet.fetch.resolve_global_ips', lambda host:['93.184.216.34'])
    monkeypatch.setattr('clientmagnet.fetch.PinnedHTTPSConnection',lambda host,ip:fake_connection(html=b'a'*750001))
    with pytest.raises(FetchError, match='750 KB'):
        fetch_html('https://example.org/')
