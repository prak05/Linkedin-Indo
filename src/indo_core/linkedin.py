"""Read your public LinkedIn profile: name, headline, about and recent posts.

One request to the public profile page (the one anyone sees without signing in),
made only when you press Scan. No login, no cookies, no crawling: LinkedIn embeds
a schema.org JSON-LD block in that page, with a Person record and your most
recent public posts (DiscussionForumPosting). That is what gets read. LinkedIn
shows only a handful of posts there; the data export reads all of them.
"""

import html
import json
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse

from .sources import FetchError, MAX_FETCH_BYTES, _check_public_host, _opener
from .validation import ValidationError

FETCH_TIMEOUT = 15
# LinkedIn answers non-browser clients with HTTP 999 or a sign-in wall.
BROWSER_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/141.0.0.0 Safari/537.36")
PROFILE_RE = re.compile(r"^/in/([^/?#]+)/?")
LDJSON_RE = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
META_RE = re.compile(r'<meta[^>]+(?:property|name)="(og:title|og:description|description)"[^>]+content="([^"]*)"')


def profile_url(url):
    """Normalise a LinkedIn profile URL to https://www.linkedin.com/in/<slug>. Raises ValidationError."""
    url = (url or "").strip()
    if url and "://" not in url:
        url = f"https://{url}"
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    match = PROFILE_RE.match(parsed.path or "")
    if not (host == "linkedin.com" or host.endswith(".linkedin.com")) or not match:
        raise ValidationError("Enter your LinkedIn profile URL, like https://www.linkedin.com/in/your-name")
    return f"https://www.linkedin.com/in/{match.group(1)}"


def fetch_profile_html(url, opener=None):
    _check_public_host(url)
    request = urllib.request.Request(url, headers={
        "User-Agent": BROWSER_UA, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9"})
    try:
        with (opener or _opener).open(request, timeout=FETCH_TIMEOUT) as resp:
            final = resp.geturl()
            body = resp.read(MAX_FETCH_BYTES + 1)[:MAX_FETCH_BYTES]
            charset = resp.headers.get_content_charset() or "utf-8"
    except FetchError:
        raise
    except urllib.error.HTTPError as e:
        if e.code == 999:
            raise FetchError("LinkedIn is limiting requests from this network right now (HTTP 999). "
                             "Try again later, or use the data export below") from None
        if e.code == 404:
            raise FetchError("LinkedIn has no public profile at that URL") from None
        raise FetchError(f"LinkedIn answered HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise FetchError(f"could not connect to LinkedIn ({getattr(e, 'reason', e)}). Check the internet connection") from None
    if "/authwall" in final or "/login" in final or "/signup" in final:
        raise FetchError("LinkedIn asked for a sign-in instead of showing the public profile. Make sure your "
                         "profile's public visibility is on (Settings, Visibility, Edit your public profile), "
                         "or use the data export below")
    return body.decode(charset, errors="replace")


def _graph(page):
    nodes = []
    for raw in LDJSON_RE.findall(page):
        try:
            data = json.loads(raw)
        except ValueError:
            continue
        for item in data if isinstance(data, list) else [data]:
            if isinstance(item, dict):
                nodes.extend(item["@graph"] if isinstance(item.get("@graph"), list) else [item])
    return [n for n in nodes if isinstance(n, dict)]


def _names(value):
    items = value if isinstance(value, list) else [value] if value else []
    return [i["name"] if isinstance(i, dict) else str(i) for i in items if (i.get("name") if isinstance(i, dict) else i)]


def _clean(text):
    return html.unescape(re.sub(r"[ \t]+", " ", str(text or ""))).strip()


def parse_profile(page, url):
    """Pull the profile and recent public posts out of a profile page. Returns a dict."""
    graph = _graph(page)
    meta = {k: _clean(v) for k, v in META_RE.findall(page)}
    person = next((n for n in graph if n.get("@type") == "Person"), {})
    title = meta.get("og:title", "").removesuffix("| LinkedIn").strip()
    name = _clean(person.get("name")) or title.split(" - ", 1)[0].strip()
    # The page title carries the headline as written ("Name - Headline"); jobTitle is only a list of roles.
    headline = (title.split(" - ", 1)[1].strip() if " - " in title else "") or (
        _clean(person.get("jobTitle")) if isinstance(person.get("jobTitle"), str) else ", ".join(_names(person.get("jobTitle"))))
    about = _clean(person.get("description"))
    if not about and (desc := meta.get("og:description") or meta.get("description")):
        # "Headline · About · Experience: … · Education: …": the second part is the About text.
        parts = [p.strip() for p in desc.split(" · ")]
        about = next((p for p in parts[1:] if not re.match(r"^(Experience|Education|Location|\d+ connections)", p)), "")
    slug = url.rstrip("/").rsplit("/", 1)[-1]

    def mine(node):
        author = node.get("author") or {}
        author_url = author.get("url", "") if isinstance(author, dict) else ""
        return not author_url or f"/in/{slug}" in author_url

    posts, articles = [], []
    for n in graph:
        kind = n.get("@type")
        if kind == "DiscussionForumPosting" and mine(n) and _clean(n.get("text")):
            posts.append({"text": _clean(n.get("text")), "url": n.get("url") or n.get("mainEntityOfPage"),
                          "date": n.get("datePublished")})
        elif kind == "Article" and mine(n) and _clean(n.get("headline")):
            articles.append({"title": _clean(n.get("headline")), "url": n.get("url"), "date": n.get("datePublished")})
    location = person.get("address", {}).get("addressLocality") if isinstance(person.get("address"), dict) else None
    return {
        "url": url, "name": name, "headline": headline, "about": about, "location": location,
        "works_for": _names(person.get("worksFor")), "education": _names(person.get("alumniOf")),
        "posts": posts, "articles": articles,
    }


def scan(url, fetch=fetch_profile_html):
    """Scan a public profile. Returns the parse_profile() dict plus "notes". Raises FetchError or ValidationError."""
    url = profile_url(url)
    found = parse_profile(fetch(url), url)
    if not found["name"]:
        raise FetchError("LinkedIn sent a page without profile details. Check the URL, or use the data export below")
    notes = [f"Read {found['name']}'s public profile."]
    if found["posts"]:
        notes.append(f"Found {len(found['posts'])} recent public post{'s' if len(found['posts']) != 1 else ''}. "
                     "LinkedIn shows only recent ones publicly; the data export has every post.")
    else:
        notes.append("No public posts were visible. Import the data export to train on your posts.")
    return {**found, "notes": notes}
