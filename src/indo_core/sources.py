"""Turn event material (text, PDF, image, URL) into model input (FR-3, FR-4)."""

import base64
import ipaddress
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

from .validation import MAX_TEXT_CHARS

FETCH_TIMEOUT = 8
MAX_FETCH_BYTES = 2 * 1024 * 1024
LOW_TEXT_CHARS = 300
USER_AGENT = "LinkedIn-Indo/0.1 (+event page reader)"
EXTRACT_TIMEOUT = 30
# Local tools that read PDFs and images. The draft continues without them.
EXTRACTORS = {
    "document": ("pdftotext", ["pdftotext", "-q", "-l", "20", "-", "-"], "poppler-utils"),
    "image": ("tesseract", ["tesseract", "stdin", "stdout"], "tesseract-ocr"),
}


class FetchError(Exception):
    """The URL could not be read. The draft continues without it."""


def _check_public_host(url):
    """Refuse addresses on the local machine or a private network."""
    host = urlparse(url).hostname
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise FetchError(f"could not resolve {host}") from None
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if not addr.is_global:
            raise FetchError(f"{host} points to a private or local address")


class _PublicOnlyRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlparse(newurl).scheme not in ("http", "https"):
            raise FetchError("redirected to a non-web address")
        _check_public_host(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_PublicOnlyRedirects)


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "nav", "footer", "header", "form", "template"}
    BLOCK = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "tr", "td", "th"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.title, self._skip, self._in_title = [], "", 0, False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag == "title":
            self._in_title = True
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag == "title":
            self._in_title = False
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            # Source newlines are just whitespace in HTML; line breaks come from block tags.
            self.parts.append(data.replace("\r", " ").replace("\n", " "))


def html_to_text(html):
    parser = _TextExtractor()
    parser.feed(html)
    lines = (" ".join(line.split()) for line in "".join(parser.parts).splitlines())
    text = "\n".join(line for line in lines if line)
    title = " ".join(parser.title.split())
    return f"{title}\n\n{text}" if title else text


def fetch_url_text(url, opener=None, user_agent=USER_AGENT):
    """Fetch a page and return its readable text. Raises FetchError."""
    _check_public_host(url)
    request = urllib.request.Request(url, headers={"User-Agent": user_agent, "Accept": "text/html,text/plain;q=0.9"})
    try:
        with (opener or _opener).open(request, timeout=FETCH_TIMEOUT) as resp:
            ctype = resp.headers.get_content_type()
            if ctype not in ("text/html", "text/plain", "application/xhtml+xml"):
                raise FetchError(f"the page is {ctype}, not a web page")
            body = resp.read(MAX_FETCH_BYTES + 1)
            charset = resp.headers.get_content_charset() or "utf-8"
    except FetchError:
        raise
    except urllib.error.HTTPError as e:
        raise FetchError(f"the site answered HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise FetchError(f"could not connect ({reason})") from None
    text = body[:MAX_FETCH_BYTES].decode(charset, errors="replace")
    return html_to_text(text) if ctype != "text/plain" else text


def _clip(text, label, notes):
    if len(text) > MAX_TEXT_CHARS:
        notes.append(f"{label} was long, so only the first {MAX_TEXT_CHARS:,} characters were used.")
        return text[:MAX_TEXT_CHARS]
    return text


def extract_text(kind, data):
    """Read text from a PDF ("document") or an image with a local tool. Returns (text, note)."""
    tool, cmd, package = EXTRACTORS[kind]
    if not shutil.which(tool):
        return None, f"{tool} is not installed (apt install {package})"
    try:
        result = subprocess.run(cmd, input=base64.b64decode(data), capture_output=True, timeout=EXTRACT_TIMEOUT, check=False)
    except (subprocess.TimeoutExpired, OSError):
        return None, f"{tool} could not read it in time"
    text = result.stdout.decode("utf-8", errors="replace").strip()
    return (text, None) if result.returncode == 0 and text else (None, "no readable text was found")


def build_source(source, fetch=fetch_url_text):
    """Return (content_blocks, event_text, notes) for a validated source.

    content_blocks go before the prompt text (PDF/image); event_text is inlined
    as untrusted material; notes are shown to the user.
    """
    notes = []
    kind = source["type"]
    if kind == "skip":
        return [], None, notes
    if kind == "url":
        host = urlparse(source["url"]).hostname
        try:
            text = fetch(source["url"])
        except FetchError as e:
            notes.append(f"Could not read {host}: {e}. The draft uses only your answers.")
            return [], None, notes
        if len(text) < LOW_TEXT_CHARS:
            notes.append(f"Only {len(text)} characters came back from {host}. "
                         "The page may need a login or JavaScript; uploading a file usually works better.")
        else:
            notes.append(f"Read {len(text):,} characters from {host}.")
        return [], _clip(text, f"The page at {host}", notes), notes
    if kind == "file" and "text" in source:
        return [], _clip(source["text"], source["name"], notes), notes
    block_type = "image" if kind == "image" else "document"
    block = {"type": block_type, "source": {"type": "base64", "media_type": source["media_type"], "data": source["data"]}}
    return [block], None, notes
