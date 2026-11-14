"""Bounded, one-page HTTPS fetch with pinned, publicly routable IP.

This is only a defense-in-depth baseline; public scanning is disabled by default.
Real internet-facing deployment additionally needs egress firewall policy, queues,
per-account auth/CAPTCHA, monitoring and legal/abuse review.
"""
from dataclasses import dataclass
import http.client
import ipaddress
import socket
import ssl
import time
from urllib.parse import urlsplit, urljoin, urlunsplit

MAX_HTML_BYTES = 750_000
MAX_REDIRECTS = 2
USER_AGENT = "ClientMagnetPro/0.1 (+https://github.com/rajachanna/ClientMagnet-Pro)"


class FetchError(ValueError):
    pass


@dataclass(frozen=True)
class FetchedPage:
    url: str
    html: str
    status_code: int
    elapsed_ms: int
    size_bytes: int


def validate_url(url: str) -> str:
    if not isinstance(url, str) or len(url) > 750 or any(ord(c) < 33 for c in url):
        raise FetchError("Expected a single unspaced HTTPS URL of at most 750 characters")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise FetchError("Invalid URL") from exc
    if (parsed.scheme.lower() != "https" or parsed.username is not None or
        parsed.password is not None or parsed.fragment or not hostname or
        port not in (None, 443) or len(parsed.path) > 450 or len(parsed.query) > 250):
        raise FetchError("Only standard-port HTTPS URLs with no credentials or fragments are allowed")
    try:
        ascii_host = hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise FetchError("Invalid international domain") from exc
    if (not ascii_host or len(ascii_host) > 253 or
        ascii_host.endswith((".local", ".localhost", ".internal", ".test", ".example")) or
        ascii_host in {"localhost", "metadata.google.internal"} or
        "." not in ascii_host or
        any(not label or len(label)>63 or label.startswith("-") or label.endswith("-")
            for label in ascii_host.split("."))):
        raise FetchError("A public domain name is required")
    # Reject bare IP addresses, even public ones: only DNS names that resolve to
    # all-global addresses are eligible. This simplifies TLS, abuse and URL rules.
    try:
        ipaddress.ip_address(ascii_host)
    except ValueError:
        pass
    else:
        raise FetchError("IP-literal URLs are not supported")
    netloc = ascii_host if port is None else ascii_host + ":443"
    return urlunsplit(("https", netloc, parsed.path or "/", parsed.query, ""))


def resolve_global_ips(hostname: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except (OSError, ValueError) as exc:
        raise FetchError("Could not resolve public domain") from exc
    ips = list(dict.fromkeys(info[4][0] for info in infos))
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise FetchError("Domain resolves to an unsafe IP address")
    return ips


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, ip: str, timeout: int = 5):
        super().__init__(host, port=443, timeout=timeout, context=ssl.create_default_context())
        self.pinned_ip = ip

    def connect(self):
        # TLS checks and SNI use the *validated hostname*, while the socket
        # connects only to the resolved, already checked public IP.
        sock = socket.create_connection((self.pinned_ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


def fetch_html(url: str) -> FetchedPage:
    current = validate_url(url)
    begun = time.monotonic()
    for attempt in range(MAX_REDIRECTS + 1):
        parsed = urlsplit(current)
        ips = resolve_global_ips(parsed.hostname)
        connection = PinnedHTTPSConnection(parsed.hostname, ips[0])
        try:
            path = parsed.path or "/"
            if parsed.query:
                path += "?" + parsed.query
            connection.request("GET", path, headers={
                "Host": parsed.hostname,
                "User-Agent": USER_AGENT,
                "Accept": "text/html",
                "Accept-Encoding": "identity",
                "Connection": "close",
            })
            result = connection.getresponse()
            status = result.status
            if status in (301, 302, 303, 307, 308):
                location = result.getheader("Location", "")
                if not location or attempt >= MAX_REDIRECTS:
                    raise FetchError("Redirect missing target or exceeds two hops")
                current = validate_url(urljoin(current, location))
                continue
            if status != 200:
                raise FetchError(f"Website returned HTTP {status}")
            content_type = result.getheader("Content-Type", "").lower()
            if "text/html" not in content_type:
                raise FetchError("Target is not an HTML web page")
            if result.getheader("Content-Encoding", "identity").lower() != "identity":
                raise FetchError("Compressed or encoded response not supported by safe fetch")
            raw = result.read(MAX_HTML_BYTES + 1)
            if len(raw) > MAX_HTML_BYTES:
                raise FetchError("HTML exceeds safe 750 KB limit")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=", 1)[1].split(";", 1)[0].strip(' \"')
            if charset not in {"utf-8", "utf8", "iso-8859-1", "latin-1", "windows-1252"}:
                raise FetchError("Unsupported page character encoding")
            return FetchedPage(
                url=current, html=raw.decode(charset, errors="replace"),
                status_code=status, elapsed_ms=int((time.monotonic() - begun) * 1000),
                size_bytes=len(raw),
            )
        except (ssl.SSLError, socket.timeout, OSError, http.client.HTTPException) as exc:
            raise FetchError("TLS or network error while requesting page") from exc
        finally:
            connection.close()
    raise FetchError("Redirect loop")
