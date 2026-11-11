import base64
import csv
import io
import json
import zipfile

import pytest

from indo_core import ValidationError, generate, persona, revise

MY_POSTS = [
    "Excited to share that our team won the Kochi GenAI Hackathon! 🚀\n\nWe built a voice assistant for farmers.\n\n"
    "Huge thanks to everyone who helped.\n\nWhat would you have built?\n\n#GenAI #BuildInPublic #Kochi",
    "Excited to share my AWS Cloud Practitioner certification! 🚀\n\nIt took six weeks of evening study.\n\n"
    "• Practice exams helped most\n• The free tier labs were great\n\nWhat should I learn next?\n\n#AWS #BuildInPublic",
    "Excited to share that I spoke at PyCon India about serverless Python. 🚀\n\nThe questions were brilliant.\n\n"
    "Slides are linked below.\n\nWhat topic should I cover next?\n\n#Python #BuildInPublic",
]


def export_zip(posts=MY_POSTS, comments=("Congrats, well deserved!",)):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        s = io.StringIO()
        w = csv.writer(s)
        w.writerow(["Date", "ShareLink", "ShareCommentary", "SharedUrl", "MediaUrl", "Visibility"])
        for i, p in enumerate(posts):
            w.writerow([f"2026-0{i + 1}-01 10:00:00", f"https://www.linkedin.com/feed/update/{i}", p, "", "", "MEMBER_NETWORK"])
        w.writerow(["2026-05-01", "https://www.linkedin.com/feed/update/9", "", "https://example.com", "", "PUBLIC"])
        zf.writestr("Basic_LinkedInDataExport/Shares.csv", s.getvalue())
        s = io.StringIO()
        w = csv.writer(s)
        w.writerow(["First Name", "Last Name", "Maiden Name", "Headline", "Summary"])
        w.writerow(["Prakhar", "Sharma", "", "Cloud and AI builder", "I build things on AWS."])
        zf.writestr("Basic_LinkedInDataExport/Profile.csv", s.getvalue())
        s = io.StringIO()
        w = csv.writer(s)
        w.writerow(["Date", "Link", "Message"])
        for c in comments:
            w.writerow(["2026-01-02", "https://x", c])
        zf.writestr("Basic_LinkedInDataExport/Comments.csv", s.getvalue())
    return buf.getvalue()


LIKED = ("Most people think hackathons are about code.\n\nThey are not.\n\nThey are about people.\n\n"
         "Here is what I learned after ten of them:\n\n• Sleep matters more than you think\n"
         "• The demo is half the work\n• Talk to the judges early\n\nWhat is your best hackathon lesson?")


@pytest.fixture
def pdir(tmp_path, monkeypatch):
    monkeypatch.setenv("INDO_PERSONA_DIR", str(tmp_path))
    monkeypatch.delenv("INDO_ENGINE", raising=False)
    return tmp_path


def trained(pdir, **answers):
    data = persona.import_export(export_zip())
    persona.add_posts(data["posts"], pdir)
    a = persona.validate_answers({"name": "Prakhar Sharma", "linkedin_url": "https://www.linkedin.com/in/prak05", **answers})
    persona.save_profile(a, pdir)
    return persona.build(a, persona.load_posts(pdir), data["comments"], data["profile"], directory=pdir)


# ---------- Import ----------

def test_export_zip_gives_every_post_profile_and_comments():
    data = persona.import_export(export_zip())
    assert [p["text"] for p in data["posts"]] == MY_POSTS  # the empty repost row is skipped
    assert data["posts"][0]["url"].endswith("/0")
    assert data["profile"] == {"name": "Prakhar Sharma", "headline": "Cloud and AI builder", "about": "I build things on AWS."}
    assert data["comments"] == ["Congrats, well deserved!"]
    assert any("3 posts" in n for n in data["notes"])


def test_bad_zip_and_missing_shares_are_explained():
    with pytest.raises(ValidationError, match="not a ZIP"):
        persona.import_export(b"nope")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Connections.csv", "a,b\n")
    assert any("No Shares.csv" in n for n in persona.import_export(buf.getvalue())["notes"])


def test_pasted_posts_split_on_dashes_and_dedupe(pdir):
    posts = persona.import_text(MY_POSTS[0] + "\n---\n" + MY_POSTS[1] + "\n---\ntoo short")
    assert len(posts) == 2
    assert persona.add_posts(posts, pdir) == 2
    assert persona.add_posts(posts, pdir) == 2


# ---------- Training ----------

def test_training_learns_how_you_write(pdir):
    p = trained(pdir)
    st = p["stats"]
    assert st["posts"] == 3 and st["openers"] == ["excited to share"] and st["hooks"][0] == "announcement"
    assert st["ctas"] == "question" and st["emoji_rate"] == 1.0 and st["top_emoji"] == ["🚀"]
    assert st["top_hashtags"][0] == "BuildInPublic"
    v = p["voice"]
    assert v["emoji"] is True and v["hook"] == "announcement" and v["cta"] == "question" and "BuildInPublic" in v["fixed_tags"]
    assert p["answers"]["headline"] == "Cloud and AI builder"  # filled from Profile.csv
    assert any("Learned from 3 of your posts" in line for line in p["summary"])
    assert persona.load(pdir) == p


def test_your_answers_override_what_was_learned(pdir):
    p = trained(pdir, emoji="never", length="long", tone=["professional"], avoid="synergy, game changer",
                signature="Keep building.")
    v = p["voice"]
    assert v["emoji"] is False and v["length"] == 1 and v["tone"] == "formal" and v["exclaim"] is False
    assert v["avoid"] == ["synergy", "game changer"] and v["signature"] == "Keep building."


def test_answers_are_validated():
    with pytest.raises(ValidationError, match="name"):
        persona.validate_answers({})
    with pytest.raises(ValidationError, match="tone"):
        persona.validate_answers({"name": "P", "tone": ["sarcastic"]})
    with pytest.raises(ValidationError, match="Emoji"):
        persona.validate_answers({"name": "P", "emoji": "lots"})
    assert persona.validate_answers({"name": "P", "hashtags": "#AWS, GenAI"})["hashtags"] == ["AWS", "GenAI"]


def test_similar_posts_retrieves_by_topic():
    posts = [{"text": t} for t in MY_POSTS]
    assert persona.similar_posts("Passed the AWS certification exam", posts, k=1) == [MY_POSTS[1]]


# ---------- Drafting with the persona ----------

def test_local_draft_follows_the_persona(pdir, draft_request):
    p = trained(pdir, signature="Keep building.", avoid="journey")
    result = generate({**draft_request, "engine": "local"}, persona=p)
    draft = result["draft"]
    assert draft.startswith("🚀 Excited to share: ")  # your emoji and your own opener
    assert "Keep building." in draft and "#BuildInPublic" in draft
    assert result["notes"][0] == "Written as Prakhar Sharma (persona)."


def test_tag_reasons_shape_the_thank_you_lines(draft_request):
    draft_request["people"] = [
        {"name": "Asha Menon", "reason": "mentor"},
        {"name": "Ravi", "reason": "teammate"}, {"name": "Meera", "reason": "teammate"},
        {"name": "GDG Kochi", "reason": "organiser"},
        {"name": "Sam", "reason": "lending me a laptop at 3 am"},
    ]
    draft = generate({**draft_request, "engine": "local"}, samples=[])["draft"]
    assert "Thank you @Asha Menon for the mentoring and guidance." in draft
    assert "without my teammates @Ravi and @Meera." in draft
    assert "Thank you @GDG Kochi for organising it." in draft
    assert "Thank you @Sam for lending me a laptop at 3 am." in draft


def test_llm_prompt_gets_persona_similar_posts_and_reasons(pdir, fake_client, llm_request):
    p = trained(pdir)
    llm_request["people"][0]["reason"] = "mentor"
    client = fake_client("Draft")
    generate(llm_request, client=client, persona=p, posts=persona.load_posts(pdir))
    call = client.messages.calls[0]
    assert "<persona>" in call["system"] and "Name: Prakhar Sharma" in call["system"]
    assert "most similar to this one" in call["system"] and "Kochi GenAI Hackathon" in call["system"]
    assert 'why_tagged="mentor"' in call["messages"][0]["content"][-1]["text"]


def test_cloud_requests_can_carry_a_trimmed_persona(pdir, fake_client, llm_request):
    p = trained(pdir)
    inline = {k: p[k] for k in ("answers", "voice", "summary", "showcase")}
    client = fake_client("Draft")
    generate({**llm_request, "persona": inline}, client=client)
    assert "Name: Prakhar Sharma" in client.messages.calls[0]["system"]
    cleaned = persona.clean_inline(inline)
    assert cleaned["voice"]["opener"] == "excited to share" and cleaned["voice"]["fixed_tags"] == p["voice"]["fixed_tags"]
    with pytest.raises(ValidationError):
        generate({**llm_request, "persona": {"answers": {"name": "x" * 500}}}, client=client)


# ---------- Inspiration ----------

def test_structure_reads_the_shape_not_the_words():
    shape = persona.structure(LIKED)
    assert shape["pattern"] == {"hook": "bold", "list": True, "short_lines": True, "cta": "question",
                                "length": "short", "emoji": False, "hashtags": 0}
    assert "opens with a short punchy line" in shape["description"]
    assert "uses a list for the key points" in shape["description"]


def test_originality_flags_copied_runs():
    assert persona.originality("My own words about a hackathon.", LIKED)["ok"]
    bad = persona.originality("Honestly, sleep matters more than you think at events.", LIKED)
    assert not bad["ok"] and bad["phrase"] == "sleep matters more than you think"


def test_local_draft_borrows_structure_and_credits_on_request(draft_request):
    inspiration = {"text": LIKED, "author": "Jane Doe", "credit": True}
    result = generate({**draft_request, "engine": "local", "inspiration": inspiration}, samples=[])
    draft = result["draft"]
    assert draft.rstrip().endswith("#Hackathon") or "#" in draft.splitlines()[-1]
    assert "What would you have built?" in draft  # the liked post ended with a question
    assert "(Format inspired by a post from @Jane Doe.)" in draft
    assert any("originality check passed" in n for n in result["notes"])
    # The credit survives revisions.
    again = revise({"history": result["history"], "feedback": "shorter"})
    assert "(Format inspired by a post from @Jane Doe.)" in again["draft"]


def test_llm_gets_the_described_shape_never_the_liked_text(fake_client, llm_request):
    client = fake_client("Sleep matters more than you think, says my new draft.")
    result = generate({**llm_request, "inspiration": {"text": LIKED}}, client=client, samples=[])
    text = client.messages.calls[0]["messages"][0]["content"][-1]["text"]
    assert "<structure_to_borrow>" in text and "uses a list" in text
    assert "The demo is half the work" not in text and "The demo is half the work" not in client.messages.calls[0]["system"]
    assert any("Originality check" in n and "repeats" in n for n in result["notes"])


def test_inspiration_library(pdir):
    item = persona.add_inspiration({"text": LIKED, "author": "Jane"}, pdir)
    assert item["pattern"]["list"] and persona.list_inspirations(pdir)[0]["id"] == item["id"]
    with pytest.raises(ValidationError, match="at least 15 words"):
        persona.add_inspiration({"text": "Too short to learn from."}, pdir)
    persona.delete_inspiration(item["id"], pdir)
    assert persona.list_inspirations(pdir) == []


# ---------- Local server endpoints ----------

def test_server_onboarding_import_and_inspiration_flow(tmp_path, monkeypatch):
    import local_server
    from test_local_server import request

    monkeypatch.setattr(local_server.Handler, "persona_dir", tmp_path)
    monkeypatch.setattr(local_server.Handler, "samples", [])
    monkeypatch.setattr(local_server.Handler, "log_message", lambda *a: None)
    srv = local_server.make_server(port=0)
    import threading
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        status, _, view = request(srv, "GET", "/persona")
        assert status == 200 and view["persona"] is None and "mentor" in view["choices"]["reasons"]

        status, _, view = request(srv, "POST", "/persona/import", {"zip": base64.b64encode(export_zip()).decode()})
        assert status == 200 and view["post_count"] == 3 and view["persona"]["answers"]["name"] == "Prakhar Sharma"

        status, _, view = request(srv, "POST", "/persona", {"name": "Prakhar Sharma", "tone": ["friendly"],
                                                            "linkedin_url": "https://www.linkedin.com/in/prak05"})
        assert status == 200 and view["persona"]["answers"]["linkedin_url"].endswith("/prak05")

        status, _, item = request(srv, "POST", "/inspirations", {"text": LIKED, "author": "Jane"})
        status, _, gen = request(srv, "POST", "/drafts", {
            "engine": "local", "activity": "post", "topic": "Won the Kochi GenAI hackathon", "when": "Oct 2026",
            "source": {"type": "skip"}, "people": [], "inspiration_id": item["id"]})
        assert status == 200 and gen["notes"][0] == "Written as Prakhar Sharma (persona)."
        assert any("originality" in n for n in gen["notes"])

        status, _, items = request(srv, "POST", "/inspirations/delete", {"id": item["id"]})
        assert status == 200 and items == []
    finally:
        srv.shutdown()
        srv.server_close()


def test_import_html_connector():
    sample_html = """<!doctype html>
    <html>
    <head><title>Activity | Prakhar Sharma | LinkedIn</title></head>
    <body>
      <p class="ignore">short</p>
      <p>Drove operations on the ground for the September edition of the HR Evolve Monthly Session, hosted in exclusive association with LinkedIn. It was a masterclass in execution and community scaling across Trivandrum.</p>
      <p>Looking back at the intense momentum of September, the 4th Edition of the AI Evolve Meetup at the Floor of Madness, FAYA, stands out as a defining milestone in our tech ecosystem with state-wide engineering teams.</p>
    </body>
    </html>
    """
    res = persona.import_html(sample_html)
    assert res["profile"]["name"] == "Prakhar Sharma"
    assert len(res["posts"]) == 2
    assert "HR Evolve" in res["posts"][0]["text"]
    assert "AI Evolve" in res["posts"][1]["text"]


def test_auto_detect_saved_html(tmp_path):
    f1 = tmp_path / "Activity _ Prakhar _ LinkedIn.html"
    f1.write_text("<html></html>", encoding="utf-8")
    f2 = tmp_path / "random.txt"
    f2.write_text("hello", encoding="utf-8")
    detected = persona.auto_detect_saved_html([tmp_path])
    assert len(detected) == 1
    assert detected[0].name == f1.name

