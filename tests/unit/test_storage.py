from datetime import datetime, timezone

from indo_core import list_posts, save_post


def test_save_writes_timestamped_markdown_and_lists_newest_first(tmp_path):
    t1 = datetime(2026, 10, 24, 9, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 24, 10, 0, 0, tzinfo=timezone.utc)
    a = save_post({"topic": "Kochi GenAI hackathon!", "when": "Oct 2026", "draft": "First"}, directory=tmp_path, now=t1)
    b = save_post({"topic": "Workshop\nnotes", "when": "Nov", "draft": "Second\n\nline"}, directory=tmp_path, now=t2)

    assert a == {"id": "20261024-090000-kochi-genai-hackathon", "path": "posts/20261024-090000-kochi-genai-hackathon.md"}
    text = (tmp_path / f"{a['id']}.md").read_text()
    assert text.startswith("---\ntopic: Kochi GenAI hackathon!\nwhen: Oct 2026\ncreated_at: 2026-10-24T09:00:00+00:00\n---\n\nFirst")

    posts = list_posts(tmp_path)
    assert [p["id"] for p in posts] == [b["id"], a["id"]]
    assert posts[0]["topic"] == "Workshop notes" and posts[0]["draft"] == "Second\n\nline"


def test_same_second_does_not_overwrite(tmp_path):
    t = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ids = {save_post({"topic": "Same", "when": "x", "draft": str(i)}, directory=tmp_path, now=t)["id"] for i in range(3)}
    assert len(ids) == 3


def test_list_of_missing_folder_is_empty(tmp_path):
    assert list_posts(tmp_path / "nope") == []
