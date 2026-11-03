import base64
import json

import pytest

from indo_core import ValidationError, local_engine, ml, writer
from indo_core.validation import validate_history

MATERIAL = """Kochi GenAI Hackathon 2026
The Kochi GenAI Hackathon was organised by KeralaAI Community and AWS User Group Kochi.
Over 200 teams built generative AI applications in 36 hours using AWS Lambda and Python.
Team Indo placed second with an assistant that drafts LinkedIn posts from event material.
Register now at https://example.com to get updates.
Judges praised the serverless design and the focus on accuracy over hype.
Lunch was provided on both days."""


@pytest.fixture
def with_material(draft_request):
    draft_request["source"] = {"type": "file", "name": "notes.md", "media_type": "text/markdown", "text": MATERIAL}
    return draft_request


@pytest.mark.parametrize("text, label", [
    ("Won second place at the Kochi GenAI hackathon", "hackathon_win"),
    ("Passed the AWS Solutions Architect exam", "certification"),
    ("Attended AWS Community Day Kochi", "conference"),
    ("Attended a hands-on Terraform workshop", "workshop"),
    ("Excited to start my internship at a startup", "new_role"),
    ("Released version 2 of my open source tool", "project"),
])
def test_classifier_detects_post_type(text, label):
    assert ml.classify(text)[0] == label


def test_unclear_text_falls_back_to_general():
    assert ml.classify("zzz qqq")[0] == "general"


def test_extracts_facts_from_answers_and_material():
    facts = ml.extract_facts("Won second place at the Kochi GenAI hackathon", MATERIAL)
    assert facts["event"] == "Kochi GenAI hackathon"
    assert facts["rank"] == "second place"
    assert facts["organiser"] == "KeralaAI Community and AWS User Group Kochi"
    assert facts["team"] == "Indo"
    assert {"AWS", "Lambda", "Python", "GenAI"} <= set(facts["tech"])
    assert "Generative AI" not in facts["tech"]


def test_prize_amounts_are_found():
    assert ml.extract_facts("Won the hackathon and ₹50,000", None)["prize"] == "₹50,000"


def test_graph_propagation_spreads_relevance_to_neighbours():
    # Node 0 is relevant; node 1 is linked to it; node 2 is isolated.
    adjacency = ml._normalised_adjacency([[0, 1, 0], [1, 0, 0], [0, 0, 0]])
    final = ml.propagate(adjacency, [[1, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
    assert final[1][0] > 0 and final[2] == [0, 0, 0, 0]


def test_key_sentences_are_copied_skip_boilerplate_and_restated_facts():
    topic = "Won second place at the Kochi GenAI hackathon"
    facts = ml.extract_facts(topic, MATERIAL)
    entities = [facts["event"], facts["organiser"], facts["team"], *facts["tech"]]
    picked = ml.key_sentences(topic, MATERIAL, entities=entities)
    assert picked and all(s in MATERIAL for s in picked)
    assert not any("Register now" in s or "organised by" in s for s in picked)
    assert any("Team Indo placed second" in s for s in picked)


def test_voice_profile_reads_emoji_hashtags_and_length():
    voice = ml.voice_profile(["Shipped it 🚀 #AWS #Python", "Short one 🎉 #AWS"])
    assert voice == {"emoji": True, "hashtags": 2, "length": -1, "exclaim": False}


def test_generate_uses_only_found_facts_and_tags_people(with_material):
    result = local_engine.generate(with_material, samples=[])
    draft = result["draft"]
    assert "12-14 Oct 2026" in draft and "@Asha Menon (Mentor)" in draft
    assert "KeralaAI Community and AWS User Group Kochi" in draft
    assert draft.splitlines()[-1].startswith("#")
    assert "Hackathon or competition win" in result["notes"][0]
    assert any("No persona" in n for n in result["notes"])


def test_missing_material_leaves_a_placeholder(draft_request):
    draft = local_engine.generate(draft_request, samples=[])["draft"]
    assert "[ADD:" in draft


def test_history_is_json_and_valid_for_the_api(with_material):
    history = json.loads(json.dumps(local_engine.generate(with_material, samples=[])["history"]))
    validate_history(history)
    assert all(isinstance(m["content"], str) for m in history)
    assert json.loads(history[0]["content"])["engine"] == "local"


def test_revise_replays_every_request(with_material):
    first = local_engine.generate(with_material, samples=[])
    second = local_engine.revise({"history": first["history"], "feedback": "No hashtags and thank Rahul Nair"}, samples=[])
    assert "#" not in second["draft"] and "@Rahul Nair" in second["draft"]
    third = local_engine.revise({"history": second["history"], "feedback": "more formal, add emoji"}, samples=[])
    assert "#" not in third["draft"] and "@Rahul Nair" in third["draft"]
    assert "!" not in third["draft"] and "🏆" in third["draft"]
    assert third["notes"] == ["Applied: more formal, emoji."]
    assert [m["role"] for m in third["history"]] == ["user", "assistant"] * 3


def test_shorter_drops_paragraphs(with_material):
    first = local_engine.generate(with_material, samples=[])
    shorter = local_engine.revise({"history": first["history"], "feedback": "shorter"}, samples=[])
    assert len(shorter["draft"]) < len(first["draft"])


def test_unknown_feedback_explains_what_works(with_material):
    first = local_engine.generate(with_material, samples=[])
    result = local_engine.revise({"history": first["history"], "feedback": "make it sing"}, samples=[])
    assert result["draft"] == first["draft"]
    assert "Did not recognise" in result["notes"][0]


def test_revise_rejects_history_from_another_engine():
    history = [{"role": "user", "content": "Write a post"}, {"role": "assistant", "content": "A draft."}]
    with pytest.raises(ValidationError, match="local engine"):
        local_engine.revise({"history": history, "feedback": "shorter"})


def test_comment_replies_without_hashtags():
    req = {"activity": "comment", "topic": "loved the demo", "when": "today", "people": [],
           "post_text": "Excited to start my internship at AWS as a cloud engineer!"}
    result = local_engine.generate(req, samples=[])
    assert result["draft"].startswith("Congrat") and "Loved the demo." in result["draft"]
    assert "#" not in result["draft"]


def test_pdf_is_read_with_a_local_tool(monkeypatch, draft_request):
    seen = {}

    def extract(kind, data):
        seen["args"] = (kind, base64.b64decode(data))
        return "Team Indo placed second out of two hundred teams at the hackathon finale.", None

    monkeypatch.setattr(local_engine, "extract_text", extract)
    draft_request["source"] = {"type": "file", "name": "b.pdf", "media_type": "application/pdf", "data": "JVBERg=="}
    result = local_engine.generate(draft_request, samples=[])
    assert seen["args"] == ("document", b"%PDF")
    assert "two hundred teams" in result["draft"]
    assert "Read 73 characters from b.pdf." in result["notes"]


def test_missing_ocr_tool_is_noted(monkeypatch, draft_request):
    monkeypatch.setattr("indo_core.sources.shutil.which", lambda tool: None)
    draft_request["source"] = {"type": "image", "name": "p.png", "media_type": "image/png", "data": "iVBORw=="}
    result = local_engine.generate(draft_request, samples=[])
    assert any("tesseract is not installed" in n for n in result["notes"])


def test_feedback_settings_parse_names_and_tags():
    s, applied = writer.settings({"length": 0, "emoji": False, "hashtags": 3, "exclaim": True},
                                 ["Remove Asha Menon, #AWSCommunity, another version"])
    assert s["remove"] == ["asha menon"] and s["tags"] == ["AWSCommunity"] and s["variant"] == 1
    assert applied == ["hashtags #AWSCommunity", "another version", "removed Asha Menon"]
