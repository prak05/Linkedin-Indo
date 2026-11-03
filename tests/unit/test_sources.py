import io
import socket
import urllib.error
from email.message import Message

import pytest

from indo_core import sources
from indo_core.sources import FetchError, build_source, fetch_url_text, html_to_text
from indo_core.validation import MAX_TEXT_CHARS


def test_html_to_text_drops_chrome_and_keeps_content():
    html = """<html><head><title>Kochi GenAI Hackathon</title><style>p{}</style></head>
    <body><nav>Home | About</nav><h1>Results</h1><p>Team  Indo
    placed <b>second</b>.</p><script>track()</script><footer>(c) 2026</footer></body></html>"""
    text = html_to_text(html)
    assert text.startswith("Kochi GenAI Hackathon")
    assert "Results" in text and "Team Indo placed second." in text
    for junk in ("Home | About", "track()", "(c) 2026", "p{}"):
        assert junk not in text


@pytest.fixture
def public_dns(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [(None, None, None, None, ("93.184.215.14", 0))])


class FakeResponse(io.BytesIO):
    def __init__(self, body, ctype="text/html; charset=utf-8"):
        super().__init__(body)
        self.headers = Message()
        self.headers["Content-Type"] = ctype

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    def __init__(self, result):
        self.result = result

    def open(self, request, timeout):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_fetch_reads_public_page(public_dns):
    page = FakeResponse(b"<p>Hello from the event</p>")
    assert fetch_url_text("https://example.com/e", opener=FakeOpener(page)) == "Hello from the event"


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "169.254.169.254", "::1", "192.168.1.1"])
def test_fetch_refuses_private_addresses(monkeypatch, address):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, port: [(None, None, None, None, (address, 0))])
    with pytest.raises(FetchError, match="private or local"):
        fetch_url_text("http://internal.example/", opener=FakeOpener(FakeResponse(b"secret")))


def test_redirect_to_private_address_is_refused(monkeypatch):
    def resolve(host, port):
        return [(None, None, None, None, ("10.0.0.1" if host == "internal" else "93.184.215.14", 0))]
    monkeypatch.setattr(socket, "getaddrinfo", resolve)
    handler = sources._PublicOnlyRedirects()
    with pytest.raises(FetchError, match="private"):
        handler.redirect_request(None, None, 302, "Found", {}, "http://internal/admin")


def test_fetch_rejects_non_html(public_dns):
    with pytest.raises(FetchError, match="application/pdf"):
        fetch_url_text("https://example.com/f.pdf", opener=FakeOpener(FakeResponse(b"%PDF", "application/pdf")))


def test_fetch_reports_http_errors(public_dns):
    err = urllib.error.HTTPError("https://example.com", 403, "Forbidden", {}, None)
    with pytest.raises(FetchError, match="HTTP 403"):
        fetch_url_text("https://example.com", opener=FakeOpener(err))


def test_failed_url_continues_without_it():
    def fail(url):
        raise FetchError("could not connect (timed out)")
    blocks, text, notes = build_source({"type": "url", "url": "https://example.com/e"}, fetch=fail)
    assert blocks == [] and text is None
    assert "Could not read example.com" in notes[0] and "only your answers" in notes[0]


def test_thin_page_warns_about_login_or_javascript():
    _, text, notes = build_source({"type": "url", "url": "https://example.com"}, fetch=lambda u: "Sign in")
    assert text == "Sign in"
    assert "login or JavaScript" in notes[0]


def test_long_text_is_clipped_with_a_note():
    src = {"type": "file", "name": "notes.md", "media_type": "text/markdown", "text": "x" * (MAX_TEXT_CHARS + 50)}
    _, text, notes = build_source(src)
    assert len(text) == MAX_TEXT_CHARS
    assert "notes.md was long" in notes[0]


def test_pdf_and_image_become_content_blocks():
    pdf = {"type": "file", "name": "b.pdf", "media_type": "application/pdf", "data": "JVBERg=="}
    blocks, text, _ = build_source(pdf)
    assert blocks == [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "JVBERg=="}}]
    assert text is None
    img = {"type": "image", "name": "p.png", "media_type": "image/png", "data": "iVBORw=="}
    assert build_source(img)[0][0]["type"] == "image"
