import json

import pytest

from indo_core import linkedin
from indo_core.sources import FetchError
from indo_core.validation import ValidationError

GRAPH = {"@context": "http://schema.org", "@graph": [
    {"@type": "Person", "name": "Asha Menon", "jobTitle": ["Engineer"], "description": "I build cloud things in Kochi.",
     "address": {"addressLocality": "Kochi, Kerala, India"}, "worksFor": [{"@type": "Organization", "name": "Acme"}],
     "alumniOf": [{"@type": "EducationalOrganization", "name": "CUSAT"}]},
    {"@type": "DiscussionForumPosting", "author": {"url": "https://www.linkedin.com/in/asha-menon"},
     "text": "Spoke at AWS Community Day Kochi &amp; met so many builders.", "datePublished": "2026-10-01T10:00:00Z",
     "url": "https://www.linkedin.com/posts/asha_1"},
    {"@type": "DiscussionForumPosting", "author": {"url": "https://www.linkedin.com/in/someone-else"},
     "text": "Not my post.", "url": "https://www.linkedin.com/posts/other"},
    {"@type": "Article", "author": {"url": "https://www.linkedin.com/in/asha-menon"}, "headline": "Serverless notes"},
]}
PAGE = f"""<html><head>
<meta property="og:title" content="Asha Menon - Cloud and AI builder · AWS Community Builder | LinkedIn">
<meta property="og:description" content="Cloud and AI builder · I build cloud things in Kochi. · Experience: Acme">
<script type="application/ld+json">{json.dumps(GRAPH)}</script></head><body></body></html>"""


def test_profile_url_is_normalised():
    assert linkedin.profile_url("linkedin.com/in/asha-menon/?trk=x") == "https://www.linkedin.com/in/asha-menon"
    assert linkedin.profile_url("https://in.linkedin.com/in/asha") == "https://www.linkedin.com/in/asha"
    for bad in ("", "https://example.com/in/asha", "https://www.linkedin.com/company/acme"):
        with pytest.raises(ValidationError):
            linkedin.profile_url(bad)


def test_parse_reads_person_and_only_own_posts():
    p = linkedin.parse_profile(PAGE, "https://www.linkedin.com/in/asha-menon")
    assert p["name"] == "Asha Menon"
    assert p["headline"] == "Cloud and AI builder · AWS Community Builder"
    assert p["about"] == "I build cloud things in Kochi."
    assert p["location"] == "Kochi, Kerala, India" and p["works_for"] == ["Acme"] and p["education"] == ["CUSAT"]
    assert [x["text"] for x in p["posts"]] == ["Spoke at AWS Community Day Kochi & met so many builders."]
    assert p["articles"][0]["title"] == "Serverless notes"


def test_scan_falls_back_to_meta_tags_and_reports():
    page = '<meta property="og:title" content="Ravi K - Student | LinkedIn"><meta name="description" content="Student · Loves robots. · Education: MIT">'
    r = linkedin.scan("https://www.linkedin.com/in/ravi", fetch=lambda url: page)
    assert (r["name"], r["headline"], r["about"]) == ("Ravi K", "Student", "Loves robots.")
    assert "No public posts" in r["notes"][-1]


def test_scan_without_profile_details_is_an_error():
    with pytest.raises(FetchError):
        linkedin.scan("https://www.linkedin.com/in/ravi", fetch=lambda url: "<html></html>")
