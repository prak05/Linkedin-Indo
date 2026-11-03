"""Your persona: who you are and how you write, learned from your own LinkedIn posts.

Nothing here logs in to LinkedIn. linkedin.py can read your public profile page once,
when you press Scan.
Posts come from LinkedIn's own data export ("Get a copy of your data": the ZIP has
Shares.csv with every post and Profile.csv) or from text you paste.

- import_export() / import_text(): read posts.
- build(): "train" on them: length, structure, openers, closers, hashtags, emoji,
  I/we, favourite phrases, topic mix; merged with your own answers.
- similar_posts(): your past posts closest to a new topic (TF-IDF), as style examples.
- Inspiration: structure() reads the *shape* of a post you liked (hook, layout,
  lists, call to action) and originality() checks a draft did not copy its words.

Files live in persona/ (INDO_PERSONA_DIR): profile.json, posts.json, persona.json,
inspirations.json. They stay on this machine.
"""

import csv
import hashlib
import io
import json
import math
import os
import re
import statistics
import uuid
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import ml
from .validation import MAX_TEXT_CHARS, ValidationError, _text, http_url

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "persona"
MAX_POSTS = 2000
MAX_POST_CHARS = 6000
MAX_CSV_BYTES = 20 * 1024 * 1024
MAX_INSPIRATIONS = 50
SHOWCASE = 5

TONES = ("friendly", "professional", "humble", "bold", "storytelling", "technical", "witty", "inspiring")
EMOJI_CHOICES = ("never", "sometimes", "often")
LENGTH_CHOICES = ("short", "medium", "long")
TAG_REASONS = ("mentor", "teammate", "organiser", "judge", "speaker", "sponsor", "colleague", "friend")

BULLET_RE = re.compile(r"^\s*(?:[•▪◦‣\-*→➡✅✔️👉🔹🔸]|\d+[.)])\s+", re.M)
HASHTAG_RE = re.compile(r"(?<![\w#])#(\w{2,})")
MENTION_RE = re.compile(r"(?<!\w)@\w")
WORD_RE = re.compile(r"[A-Za-z']+")
OPENER_RE = re.compile(r"(excited|happy|thrilled|proud|delighted|glad|honou?red) to (share|announce)")


# ---------- Storage ----------

def folder(directory=None):
    return Path(directory or os.environ.get("INDO_PERSONA_DIR") or DEFAULT_DIR)


def _read(name, default, directory=None):
    try:
        return json.loads((folder(directory) / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(name, data, directory=None):
    path = folder(directory)
    path.mkdir(parents=True, exist_ok=True)
    tmp = path / f".{name}.tmp"
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path / name)


def load(directory=None):
    """The built persona, or None before onboarding."""
    return _read("persona.json", None, directory)


def load_posts(directory=None):
    return _read("posts.json", [], directory)


# ---------- Answers (the questions the app asks you) ----------

def _choice(value, field, options, required=False):
    if value in (None, ""):
        if required:
            raise ValidationError(f"{field} is required.")
        return None
    if value not in options:
        raise ValidationError(f"{field} must be one of: {', '.join(options)}.")
    return value


def _list(value, field, max_items, max_len=60):
    if value in (None, ""):
        return []
    if isinstance(value, str):
        value = [v for v in re.split(r"[,\n]", value)]
    if not isinstance(value, list) or len(value) > max_items:
        raise ValidationError(f"{field} must be a list of at most {max_items} items.")
    return [v for v in (_text(x, field, required=False, max_len=max_len) for x in value) if v]


def validate_answers(payload):
    if not isinstance(payload, dict):
        raise ValidationError("Send your answers as a JSON object.")
    url = payload.get("linkedin_url")
    tones = _list(payload.get("tone"), "Tone", 4, 20)
    if bad := [t for t in tones if t not in TONES]:
        raise ValidationError(f"Unknown tone '{bad[0]}'. Use: {', '.join(TONES)}.")
    tags = [t.lstrip("#") for t in _list(payload.get("hashtags"), "Hashtags", 8, 40)]
    if bad := [t for t in tags if not re.fullmatch(r"\w{2,40}", t)]:
        raise ValidationError(f"'{bad[0]}' is not a valid hashtag.")
    return {
        "name": _text(payload.get("name"), "Your name", max_len=200),
        "linkedin_url": http_url(url, "LinkedIn URL") if url else None,
        "headline": _text(payload.get("headline"), "Headline", required=False, max_len=300),
        "about": _text(payload.get("about"), "About you", required=False, max_len=2000),
        "tone": tones,
        "emoji": _choice(payload.get("emoji"), "Emoji", EMOJI_CHOICES),
        "length": _choice(payload.get("length"), "Length", LENGTH_CHOICES),
        "audience": _text(payload.get("audience"), "Audience", required=False, max_len=300),
        "goals": _text(payload.get("goals"), "Goals", required=False, max_len=500),
        "avoid": _list(payload.get("avoid"), "Words to avoid", 20, 60),
        "signature": _text(payload.get("signature"), "Sign-off", required=False, max_len=200),
        "hashtags": tags,
    }


# ---------- Import ----------

def _clean_post(text):
    text = (text or "").replace("\r\n", "\n").strip()
    # The export sometimes wraps commentary in extra quotes.
    if len(text) > 1 and text[0] == text[-1] == '"':
        text = text[1:-1].replace('""', '"').strip()
    return text[:MAX_POST_CHARS]


def _csv_rows(zf, member):
    info = zf.getinfo(member)
    if info.file_size > MAX_CSV_BYTES:
        raise ValidationError(f"{member} is too large to import.")
    with zf.open(member) as raw:
        data = raw.read(MAX_CSV_BYTES + 1)
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig", errors="replace"))))


def _column(row, *needles):
    for key in row:
        low = (key or "").lower().replace(" ", "")
        if any(n in low for n in needles):
            return key
    return None


def import_export(zip_bytes):
    """Read a LinkedIn data export ZIP. Returns {"posts", "profile", "comments", "notes"}."""
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    except zipfile.BadZipFile:
        raise ValidationError("That is not a ZIP file. Upload the archive LinkedIn emailed you.") from None
    names = {Path(n).name.lower(): n for n in zf.namelist()}
    notes, posts, comments, profile = [], [], [], {}
    if "shares.csv" in names:
        rows = _csv_rows(zf, names["shares.csv"])
        for row in rows:
            text_key = _column(row, "commentary")
            text = _clean_post(row.get(text_key) if text_key else "")
            if text:
                date_key, link_key = _column(row, "date"), _column(row, "sharelink", "link")
                posts.append({"text": text, "date": (row.get(date_key) or "")[:40] if date_key else "",
                              "url": (row.get(link_key) or "")[:500] if link_key else ""})
        notes.append(f"Shares.csv: {len(posts)} posts with text (of {len(rows)} rows).")
    else:
        notes.append("No Shares.csv in this archive. Request the export with 'Posts' (or the full archive).")
    if "comments.csv" in names:
        for row in _csv_rows(zf, names["comments.csv"]):
            key = _column(row, "message", "comment")
            if key and (text := _clean_post(row.get(key))):
                comments.append(text)
        notes.append(f"Comments.csv: {len(comments)} comments.")
    if "profile.csv" in names:
        rows = _csv_rows(zf, names["profile.csv"])
        if rows:
            row = rows[0]
            first, last = row.get(_column(row, "firstname") or "", ""), row.get(_column(row, "lastname") or "", "")
            profile = {"name": f"{first} {last}".strip(), "headline": row.get(_column(row, "headline") or "", ""),
                       "about": row.get(_column(row, "summary") or "", "")}
            notes.append("Profile.csv: read your name, headline and summary.")
    return {"posts": posts[:MAX_POSTS], "comments": comments[:MAX_POSTS], "profile": profile, "notes": notes}


def import_text(text):
    """Pasted posts, separated by a line of --- (or two blank lines)."""
    chunks = re.split(r"\n\s*-{3,}\s*\n|\n\s*\n\s*\n+", (text or "").replace("\r\n", "\n"))
    return [{"text": t, "date": "", "url": ""} for t in (_clean_post(c) for c in chunks) if len(t.split()) >= 5]


def _key(text):
    return hashlib.sha256(" ".join(text.lower().split()).encode()).hexdigest()[:16]


def add_posts(posts, directory=None, replace=False):
    """Merge posts into posts.json without duplicates. Returns the total count."""
    existing = [] if replace else load_posts(directory)
    seen = {_key(p["text"]) for p in existing}
    for p in posts:
        if (k := _key(p["text"])) not in seen:
            seen.add(k)
            existing.append(p)
    _write("posts.json", existing[:MAX_POSTS], directory)
    return len(existing[:MAX_POSTS])


# ---------- Training ----------

def _paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def _body(text):
    """Text without the trailing hashtag block."""
    lines = text.strip().splitlines()
    while lines and (not lines[-1].strip() or all(w.startswith("#") for w in lines[-1].split())):
        lines.pop()
    return "\n".join(lines)


def _lines(text):
    return [ln for ln in _body(text).splitlines() if ln.strip()]


def hook_style(first_line):
    line = first_line.strip()
    low = line.lower()
    if line.endswith("?"):
        return "question"
    if re.match(r"^[\"“']", line):
        return "quote"
    if re.match(r"^(\d|one|two|three|five|ten)\b", low) or re.search(r"\b\d+\s+(things|lessons|tips|ways|reasons)\b", low):
        return "number"
    if re.match(r"^(i'm|i am|we're|we are)\s+(thrilled|excited|happy|delighted|proud|honou?red)|^(excited|thrilled|happy|delighted|proud)\b", low):
        return "announcement"
    if re.match(r"^(last|a few|this|two|three) (week|month|year|day|weekend)s?\b|^when i\b|^yesterday\b", low):
        return "story"
    if line.endswith("!") or len(line.split()) <= 8:
        return "bold"
    return "statement"


def cta_style(text):
    last = _lines(text)[-1:] or [""]
    low = last[0].lower()
    if last[0].rstrip().endswith("?"):
        return "question"
    if re.search(r"\b(comment|let me know|share your|dm me|reach out|connect|follow)\b", low):
        return "invite"
    return "none"


def _first_words(line, n=3):
    words = WORD_RE.findall(line.lower())
    return " ".join(words[:n])


def _phrases(texts, top=12):
    """Phrases you reuse: 2-3 word runs found in at least two posts."""
    stop = ml.STOPWORDS
    per_post = Counter()
    for t in texts:
        words = WORD_RE.findall(t.lower())
        grams = set()
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                g = words[i:i + n]
                if g[0] not in stop and g[-1] not in stop:
                    grams.add(" ".join(g))
        per_post.update(grams)
    need = 2 if len(texts) < 20 else 3
    return [g for g, c in per_post.most_common(top * 3) if c >= need][:top]


def _vectors(texts):
    docs = [Counter(ml.tokens(t)) for t in texts]
    df = Counter(t for d in docs for t in d)
    n = len(docs)
    idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
    vecs = []
    for d in docs:
        v = {t: c * idf[t] for t, c in d.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vecs.append({t: x / norm for t, x in v.items()})
    return vecs, idf


def _cos(a, b):
    if len(a) > len(b):
        a, b = b, a
    return sum(x * b.get(t, 0.0) for t, x in a.items())


def _showcase(texts):
    """The posts most typical of you (closest to the average of all of them)."""
    if len(texts) <= SHOWCASE:
        return texts
    vecs, _ = _vectors(texts)
    centroid = Counter()
    for v in vecs:
        centroid.update(v)
    ranked = sorted(range(len(texts)), key=lambda i: -_cos(vecs[i], centroid))
    return [texts[i] for i in ranked[:SHOWCASE]]


def similar_posts(topic, posts, k=3):
    """Your past posts most similar to a new topic, as style examples for the LLM engine."""
    texts = [p["text"] if isinstance(p, dict) else p for p in posts]
    if not texts:
        return []
    vecs, idf = _vectors(texts)
    q = Counter(ml.tokens(topic))
    qv = {t: c * idf.get(t, 1.0) for t, c in q.items()}
    ranked = sorted(range(len(texts)), key=lambda i: -_cos(vecs[i], qv))
    return [texts[i] for i in ranked[:k]]


def learn(texts):
    """Writing statistics from your posts."""
    if not texts:
        return {}
    words = [len(_body(t).split()) for t in texts]
    paras = [len(_paragraphs(_body(t))) for t in texts]
    sentences = [len(s.split()) for t in texts for s in re.split(r"(?<=[.!?])\s+", _body(t)) if s.strip()]
    first_lines = [_lines(t)[0] for t in texts if _lines(t)]
    last_lines = [_lines(t)[-1] for t in texts if _lines(t)]
    emoji = Counter(e for t in texts for e in ml.EMOJI_RE.findall(t))
    tags = Counter(h for t in texts for h in HASHTAG_RE.findall(t))
    i_count = sum(len(re.findall(r"\b(I|I'm|I've|my|me)\b", t)) for t in texts)
    we_count = sum(len(re.findall(r"\b(we|we're|we've|our|us)\b", t, re.I)) for t in texts)
    topics = Counter(ml.classify(t)[0] for t in texts)
    n = len(texts)
    return {
        "posts": n,
        "words_median": int(statistics.median(words)),
        "words_range": [int(min(words)), int(max(words))],
        "paragraphs_median": int(statistics.median(paras)),
        "sentence_words": round(statistics.mean(sentences), 1) if sentences else 0,
        "emoji_rate": round(sum(bool(ml.EMOJI_RE.search(t)) for t in texts) / n, 2),
        "top_emoji": [e for e, _ in emoji.most_common(5)],
        "hashtags_per_post": round(sum(len(HASHTAG_RE.findall(t)) for t in texts) / n, 1),
        "top_hashtags": [h for h, _ in tags.most_common(10)],
        "mentions_per_post": round(sum(len(MENTION_RE.findall(t)) for t in texts) / n, 1),
        "exclaim_rate": round(sum("!" in t for t in texts) / n, 2),
        "bullet_rate": round(sum(bool(BULLET_RE.search(t)) for t in texts) / n, 2),
        "voice": "we" if we_count > i_count * 1.2 else "I",
        "hooks": [s for s, _ in Counter(hook_style(f) for f in first_lines).most_common()],
        "openers": [o for o, c in Counter(_first_words(f) for f in first_lines).most_common(5) if c >= 2 and o],
        "ctas": Counter(cta_style(t) for t in texts).most_common(1)[0][0],
        "closers": [c for c, k in Counter(last_lines).most_common(3) if k >= 2],
        "phrases": _phrases(texts),
        "topics": [ml.label_name(t) for t, _ in topics.most_common(4)],
    }


def _voice(answers, stats):
    """What the local engine uses: your answers win over what was learned."""
    rate = stats.get("emoji_rate", 0.0)
    emoji = {"never": False, "often": True}.get(answers.get("emoji"), rate >= 0.3)
    words = stats.get("words_median", 120)
    length = {"short": -1, "medium": 0, "long": 1}.get(answers.get("length"),
                                                      -1 if words < 60 else (1 if words > 180 else 0))
    hashtags = round(stats["hashtags_per_post"]) if stats else 3
    return {
        "emoji": emoji, "emoji_set": stats.get("top_emoji", [])[:3],
        "hashtags": max(0, min(6, hashtags)), "fixed_tags": answers.get("hashtags", [])
        + [t for t in stats.get("top_hashtags", [])[:2] if t not in answers.get("hashtags", [])],
        "length": length,
        "exclaim": stats.get("exclaim_rate", 0.5) >= 0.2 and "professional" not in answers.get("tone", []),
        "bullets": stats.get("bullet_rate", 0.0) >= 0.3,
        "we": stats.get("voice") == "we",
        "hook": (stats.get("hooks") or ["statement"])[0],
        # Your own announcement opener ("excited to share"), reused word for word: it is yours.
        "opener": next((o for o in stats.get("openers", []) if OPENER_RE.fullmatch(o)), None),
        "cta": stats.get("ctas", "none"),
        "signature": answers.get("signature") or (stats.get("closers") or [None])[0],
        "avoid": [a.lower() for a in answers.get("avoid", [])],
        "tone": "formal" if "professional" in answers.get("tone", []) else
                ("casual" if {"friendly", "witty"} & set(answers.get("tone", [])) else "neutral"),
    }


def _summary(answers, stats):
    out = []
    if stats:
        out.append(f"Learned from {stats['posts']} of your posts: about {stats['words_median']} words, "
                   f"{stats['paragraphs_median']} short paragraphs, sentences of ~{stats['sentence_words']:.0f} words.")
        hook = stats["hooks"][0]
        out.append(f"You usually open with {'an' if hook[0] in 'aeiou' else 'a'} {hook} hook"
                   + (f" (often \"{stats['openers'][0]}…\")" if stats["openers"] else "")
                   + f", write as \"{stats['voice']}\", and "
                   + {"question": "end with a question.", "invite": "end by inviting replies.",
                      "none": "end without a call to action."}[stats["ctas"]])
        out.append(f"Emoji in {stats['emoji_rate']:.0%} of posts"
                   + (f" ({' '.join(stats['top_emoji'][:3])})" if stats["top_emoji"] else "")
                   + f"; ~{stats['hashtags_per_post']:.0f} hashtags"
                   + (f" (#{', #'.join(stats['top_hashtags'][:4])})" if stats["top_hashtags"] else "") + ".")
        if stats["bullet_rate"] >= 0.3:
            out.append("You often use lists.")
        if stats["phrases"]:
            out.append(f"Phrases you reuse: {', '.join(stats['phrases'][:6])}.")
        if stats["topics"]:
            out.append(f"You mostly post about: {', '.join(stats['topics'])}.")
    else:
        out.append("No posts imported yet, so the persona uses only your answers.")
    if answers.get("tone"):
        out.append(f"Tone you asked for: {', '.join(answers['tone'])}.")
    if answers.get("audience"):
        out.append(f"Audience: {answers['audience']}.")
    if answers.get("avoid"):
        out.append(f"Never use: {', '.join(answers['avoid'])}.")
    return out


def build(answers, posts, comments=(), profile=None, directory=None, now=None):
    """Train the persona on your posts and answers, and save it. Returns the persona."""
    profile = profile or {}
    answers = {**answers, "headline": answers.get("headline") or profile.get("headline"),
               "about": answers.get("about") or profile.get("about")}
    texts = [p["text"] for p in posts]
    stats = learn(texts)
    persona = {
        "version": 1,
        "trained_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "answers": answers,
        "stats": stats,
        "comment_stats": learn(list(comments)) if comments else {},
        "voice": _voice(answers, stats),
        "summary": _summary(answers, stats),
        "showcase": [t[:4000] for t in _showcase(texts)],
    }
    _write("persona.json", persona, directory)
    return persona


def save_profile(answers, directory=None):
    _write("profile.json", answers, directory)


def load_profile(directory=None):
    return _read("profile.json", {}, directory)


def retrain(directory=None):
    """Rebuild persona.json from the saved answers and posts."""
    answers = load_profile(directory)
    if not answers:
        raise ValidationError("Answer the persona questions first.")
    return build(answers, load_posts(directory), _read("comments.json", [], directory), directory=directory)


def save_comments(comments, directory=None):
    _write("comments.json", list(comments)[:MAX_POSTS], directory)


def clean_inline(persona):
    """A persona sent with a request (CLOUD has no local files). Keeps known, bounded fields only."""
    if persona is None:
        return None
    if not isinstance(persona, dict) or len(json.dumps(persona)) > 64_000:
        raise ValidationError("persona must be an object under 64 KB.")
    answers = validate_answers(persona.get("answers") or {"name": "You"})
    voice = persona.get("voice") if isinstance(persona.get("voice"), dict) else {}
    showcase = [s[:4000] for s in persona.get("showcase", []) if isinstance(s, str)][:SHOWCASE]
    summary = [s[:500] for s in persona.get("summary", []) if isinstance(s, str)][:12]
    clean_voice = _voice(answers, {})
    for k, default in clean_voice.items():
        value = voice.get(k)
        if isinstance(value, str) and (default is None or isinstance(default, str)):
            clean_voice[k] = value[:200]
        elif value is not None and default is not None and isinstance(value, type(default)):
            clean_voice[k] = value[:20] if isinstance(value, list) else value
    return {"answers": answers, "voice": clean_voice, "summary": summary, "showcase": showcase, "stats": {}}


# ---------- Prompt block for the LLM engine ----------

def prompt_block(persona):
    a = persona["answers"]
    lines = [f"Name: {a['name']}"]
    for key, label in (("headline", "Headline"), ("about", "About"), ("audience", "Audience"), ("goals", "Goals")):
        if a.get(key):
            lines.append(f"{label}: {a[key][:600]}")
    lines += persona.get("summary", [])
    if a.get("signature"):
        lines.append(f"Their usual sign-off: {a['signature']}")
    if a.get("hashtags"):
        lines.append(f"Hashtags they like: {' '.join('#' + t for t in a['hashtags'])}")
    return "\n".join(lines)


# ---------- Inspiration: borrow a structure, never the words ----------

def structure(text):
    """The shape of a post you liked. Returns {"pattern", "description"}."""
    body = _body(text)
    first = (_lines(text) or [""])[0]
    paras = _paragraphs(body)
    one_liners = sum(len(p.splitlines()) == 1 and len(p.split()) <= 14 for p in paras)
    words = len(body.split())
    pattern = {
        "hook": hook_style(first),
        "list": bool(BULLET_RE.search(body)),
        "short_lines": bool(paras) and one_liners / len(paras) >= 0.5,
        "cta": cta_style(text),
        "length": "short" if words < 60 else ("long" if words > 180 else "medium"),
        "emoji": bool(ml.EMOJI_RE.search(text)),
        "hashtags": len(HASHTAG_RE.findall(text)),
    }
    hooks = {"question": "opens with a question", "quote": "opens with a quote", "number": "opens with a number or list promise",
             "announcement": "opens with an announcement", "story": "opens with a short story moment",
             "bold": "opens with a short punchy line", "statement": "opens with a plain statement"}
    desc = [hooks[pattern["hook"]], f"{pattern['length']} ({words} words)"]
    if pattern["short_lines"]:
        desc.append("one idea per line, lots of white space")
    if pattern["list"]:
        desc.append("uses a list for the key points")
    desc.append({"question": "ends with a question to the reader", "invite": "ends by inviting comments",
                 "none": "ends without a call to action"}[pattern["cta"]])
    return {"pattern": pattern, "description": desc}


def originality(draft, source, n=6):
    """Longest run of words the draft shares with the source. Flagged when it is n words or more."""
    a = WORD_RE.findall((draft or "").lower())
    b = WORD_RE.findall((source or "").lower())
    if not a or not b:
        return {"copied_words": 0, "phrase": None, "ok": True}
    best, end = 0, 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, end = cur[j], i
        prev = cur
    return {"copied_words": best, "phrase": " ".join(a[end - best:end]) if best >= n else None, "ok": best < n}


def credit_line(inspiration):
    """Optional credit for the author whose post you borrowed the format from."""
    if not inspiration or not inspiration.get("credit") or not inspiration.get("author"):
        return None
    return f"(Format inspired by a post from @{inspiration['author'].lstrip('@')}.)"


def with_credit(draft, line):
    """Put the credit line above the closing hashtags."""
    if not line or line in draft:
        return draft
    parts = draft.rstrip().split("\n\n")
    if parts and parts[-1].split() and all(w.startswith("#") for w in parts[-1].split()):
        return "\n\n".join(parts[:-1] + [line, parts[-1]])
    return f"{draft.rstrip()}\n\n{line}"


def validate_inspiration(payload):
    if payload is None:
        return None
    if not isinstance(payload, dict):
        raise ValidationError("inspiration must be an object.")
    text = _text(payload.get("text"), "The post you liked", max_len=MAX_TEXT_CHARS)
    if len(text.split()) < 15:
        raise ValidationError("Paste the whole post you liked (at least 15 words).")
    return {"text": text, "author": _text(payload.get("author"), "Author", required=False, max_len=200),
            "credit": bool(payload.get("credit"))}


def list_inspirations(directory=None):
    return _read("inspirations.json", [], directory)


def add_inspiration(payload, directory=None, now=None):
    item = validate_inspiration(payload)
    items = list_inspirations(directory)
    if len(items) >= MAX_INSPIRATIONS:
        raise ValidationError(f"You can keep up to {MAX_INSPIRATIONS} inspirations. Delete one first.")
    item = {"id": uuid.uuid4().hex[:12], **item, **structure(item["text"]),
            "added_at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")}
    _write("inspirations.json", items + [item], directory)
    return item


def delete_inspiration(item_id, directory=None):
    items = list_inspirations(directory)
    kept = [i for i in items if i["id"] != item_id]
    if len(kept) == len(items):
        raise ValidationError("No inspiration with that id.")
    _write("inspirations.json", kept, directory)
