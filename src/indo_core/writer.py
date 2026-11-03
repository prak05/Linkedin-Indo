"""Compose posts and comments from the local analysis (ml.py). No model calls.

Every fact in a draft comes from the user's answers or is copied from the event
material. Where a post needs a fact that was not found, the draft leaves an
[ADD: ...] placeholder instead of guessing (PRD accuracy rule).
"""

import re

EMOJI = {"hackathon_win": "🏆", "hackathon": "💻", "workshop": "🛠️", "talk": "🎤", "conference": "🤝",
         "certification": "🎓", "new_role": "🚀", "project": "🚀", "general": "✨"}

HOOKS = {
    "hackathon_win": ["{topic}!", "Some good news: {topic_lc}.", "{rank_cap} at {event}!", "Proud moment: {topic_lc}."],
    "hackathon": ["{topic}.", "What a build weekend: {topic_lc}.", "Back from {event}, and I learned a lot."],
    "workshop": ["{topic}.", "Learning update: {topic_lc}.", "Spent some time at {event}, and it was worth it."],
    "talk": ["{topic}.", "Speaking update: {topic_lc}.", "Thank you for having me at {event}."],
    "conference": ["{topic}.", "Back from {event} with a full notebook.", "Event recap: {topic_lc}."],
    "certification": ["{topic}!", "Milestone unlocked: {topic_lc}.", "New certification: {topic_lc}."],
    "new_role": ["{topic}!", "Some personal news: {topic_lc}.", "New chapter: {topic_lc}."],
    "project": ["{topic}.", "Something I built: {topic_lc}.", "Shipping update: {topic_lc}."],
    "general": ["{topic}.", "A quick note: {topic_lc}.", "{topic}, and a few thoughts on it."],
}

# Hooks for each opening style the persona or an inspiration asks for. None of them adds facts.
STYLE_HOOKS = {
    "question": {
        "hackathon_win": "What happens when a team builds against the clock?",
        "hackathon": "What does a hackathon really teach you?",
        "workshop": "What is the fastest way to learn a new tool?",
        "talk": "What do you learn by teaching a topic?",
        "conference": "Are events like this worth the time?",
        "certification": "Is a certification worth the effort?",
        "new_role": "Ready for a new chapter?",
        "project": "Why build this?",
        "general": "Have you thought about this?",
    },
    "story": "Here is a quick story: {topic_lc}.",
    "announcement": "Happy to share: {topic_lc}.",
    "number": "A few takeaways from this one: {topic_lc}.",
}

CTA_QUESTIONS = {
    "hackathon_win": "What would you have built?",
    "hackathon": "Have you done a hackathon? What did you build?",
    "workshop": "What is the best workshop you have attended?",
    "talk": "What topic should I speak about next?",
    "conference": "Were you there? What was your favourite session?",
    "certification": "Are you preparing for it too? Happy to share notes.",
    "new_role": "Any advice for the first few weeks?",
    "project": "What would you add to it?",
    "general": "What do you think?",
}

REASON_PHRASES = {
    "mentor": "for the mentoring and guidance",
    "teammate": None,  # teammates get their own line
    "organiser": "for organising it",
    "organizer": "for organising it",
    "judge": "for judging and the feedback",
    "speaker": "for a great session",
    "sponsor": "for supporting the event",
    "colleague": "for the support",
    "friend": "for cheering me on",
}

PLACEHOLDERS = {
    "hackathon_win": "[ADD: what your team built and what made it stand out]",
    "hackathon": "[ADD: what your team built and one thing you learned]",
    "workshop": "[ADD: the most useful thing you learned]",
    "talk": "[ADD: what your talk covered and one question from the audience]",
    "conference": "[ADD: a session or conversation that stood out]",
    "certification": "[ADD: what you studied and how you prepared]",
    "new_role": "[ADD: what you will be working on]",
    "project": "[ADD: what it does and who it is for]",
    "general": "[ADD: the main point you want to make]",
}

REFLECTIONS = {
    "hackathon_win": ["Seeing the work recognised means a lot, and the credit goes to the whole team.",
                      "Building something real against the clock is hard, which makes this one special."],
    "hackathon": ["Building against the clock is a fast way to learn what matters in a project.",
                  "Win or not, I came away with new skills and new friends."],
    "workshop": ["Hands-on sessions like this make new tools click much faster than reading docs alone.",
                 "I left with ideas I can use right away."],
    "talk": ["Preparing a talk is one of the best ways to really understand a topic.",
             "Sharing what I know with others is something I want to keep doing."],
    "conference": ["The hallway conversations were as valuable as the sessions.",
                   "Events like this are a reminder of how generous the tech community is."],
    "certification": ["Preparing for it filled in gaps I did not know I had.",
                      "It was a lot of study, and it was worth it."],
    "new_role": ["I am grateful to everyone who helped me get here.",
                 "This is a big step for me, and I cannot wait to get started."],
    "project": ["Building it taught me more than I expected.",
                "It started as a small idea, and shipping it felt great."],
    "general": ["Writing it down helps me think it through.",
                "Sharing in case it helps someone else."],
}

CLOSINGS = {
    "hackathon_win": ["On to the next one.", "Looking forward to building more."],
    "hackathon": ["Already looking forward to the next hackathon.", "On to the next build."],
    "workshop": ["Looking forward to putting this into practice.", "Now to go build something with it."],
    "talk": ["Questions are welcome in the comments.", "If you were there, I would love your feedback."],
    "conference": ["Already looking forward to the next one.", "If you were there too, let's connect."],
    "certification": ["On to the next goal.", "Happy to help anyone preparing for it."],
    "new_role": ["Excited for what's ahead.", "Looking forward to learning a lot."],
    "project": ["Feedback is very welcome.", "Would love to hear what you think."],
    "general": ["Would love to hear your thoughts.", "Thanks for reading."],
}

COMMENT_OPENERS = {
    "hackathon_win": ["Congratulations, well deserved!", "Huge congratulations to you and the team!"],
    "hackathon": ["Great effort, building something in that time is no small feat.", "Love seeing what came out of this."],
    "workshop": ["Sounds like a really useful session.", "Great takeaways from this one."],
    "talk": ["Great session, thanks for sharing it.", "Really enjoyed this topic."],
    "conference": ["Looks like a great event.", "Thanks for the recap."],
    "certification": ["Congratulations on the certification!", "Well done, that one takes real effort."],
    "new_role": ["Congratulations on the new role!", "Congrats, exciting news!"],
    "project": ["Really nice work on this.", "Cool project, well done."],
    "general": ["Thanks for sharing this.", "Well said."],
}

CATEGORY_TAGS = {"hackathon_win": "Hackathon", "hackathon": "Hackathon", "workshop": "Learning",
                 "talk": "PublicSpeaking", "conference": "Community", "certification": "Certification",
                 "new_role": "NewBeginnings", "project": "BuildInPublic", "general": None}
EVENT_CATEGORIES = {"hackathon_win", "hackathon", "workshop", "talk", "conference"}
LEADING_LOWER = set("won win attended gave completed got joined started built launched presented spoke participated "
                    "earned finished passed cleared spent took made received my our the a an we i'm".split())
FORMAL = [(r"\bI'm\b", "I am"), (r"\blet's\b", "let us"), (r"\bwhat's\b", "what is"), (r"\bcan't\b", "cannot"),
          (r"\bdon't\b", "do not"), (r"!", ".")]

FEEDBACK_HELP = ("Try: shorter, longer, more formal, more casual, add or remove emoji, add or remove hashtags, "
                 "#YourTag, thank <Name>, remove <Name>, as a list, end with a question, or another version.")


def _cap(text):
    return text[:1].upper() + text[1:]


def _topic_forms(topic):
    topic = topic.strip().rstrip(".!")
    first = topic.split(" ", 1)[0]
    lc = topic[:1].lower() + topic[1:] if first.lower() in LEADING_LOWER and first != "I" else topic
    return _cap(topic), lc


def _when_phrase(when):
    if re.match(r"(?i)(on|in|at|last|this|next|yesterday|today|during|over|from|between|earlier|recently|early|late|mid)\b", when):
        return when
    if re.fullmatch(r"(?i)(\d{4}|[a-z]+\s+\d{4})", when):
        return f"in {when}"
    return f"on {when}"


def _pick(options, index, slots):
    """Choose a template whose slots are all known, rotating by index."""
    usable = [o for o in options if all(slots.get(k) for k in re.findall(r"{(\w+)}", o))]
    return usable[index % len(usable)].format(**slots)


def _role(person):
    bio = (person.get("bio") or "").strip()
    if not bio:
        return None
    role = re.split(r"\s[|·•]\s|\n", bio, maxsplit=1)[0].strip()
    return role if len(role) <= 60 else None


def _join(names):
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _thanks(people, we=False):
    if not people:
        return None
    if any(p.get("reason") for p in people):
        return _thanks_by_reason(people, we)
    names = [f"@{p['name']}" + (f" ({r})" if (r := _role(p)) else "") for p in people]
    guiding = any(re.search(r"(?i)mentor|lead|professor|teacher|coach|organi[sz]er|judge", _role(p) or "") for p in people)
    reason = "for the guidance and support" if guiding else "for all the support"
    if len(names) > 3:
        return f"Thank you {reason} to:\n" + "\n".join(names)
    joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
    return f"Thank you to {joined} {reason}."


def _thanks_by_reason(people, we):
    """One line per reason: teammates are credited, everyone else is thanked for what they did."""
    groups = {}
    for p in people:
        reason = (p.get("reason") or "").strip()
        key = reason.lower()
        groups.setdefault(key, (reason, []))[1].append(f"@{p['name']}")
    lines = []
    for key, (reason, names) in groups.items():
        if key in ("teammate", "teammates", "team"):
            mates = "teammate" if len(names) == 1 else "teammates"
            lines.append(f"{'We' if we else 'I'} could not have done it without my {mates} {_join(names)}.")
        elif key in REASON_PHRASES:
            lines.append(f"Thank you {_join(names)} {REASON_PHRASES[key]}.")
        elif key:
            what = reason if re.match(r"(?i)for\b", reason) else f"for {reason[:1].lower() + reason[1:]}"
            lines.append(f"Thank you {_join(names)} {what.rstrip('.')}.")
        else:
            lines.append(f"Thank you {_join(names)} for all the support.")
    return "\n".join(lines)


def _camel(text):
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "".join(w if w.isupper() or not w.islower() else w.capitalize() for w in words)


def hashtags(category, facts, count, extra=()):
    tags = list(extra)
    if facts.get("event"):
        event_tag = _camel(re.sub(r"\b\d{4}\b", "", facts["event"]))
        if 3 <= len(event_tag) <= 30:
            tags.append(event_tag)
    if CATEGORY_TAGS[category]:
        tags.append(CATEGORY_TAGS[category])
    tags += [_camel(t) for t in facts.get("tech", [])]
    seen, out = set(), []
    for tag in tags:
        tag = tag.lstrip("#")
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            out.append(f"#{tag}")
    return out[:max(count, len(extra))]


def settings(voice, feedback):
    """Replay every revision request on top of the voice profile.

    Returns (settings, applied) where applied lists what the last request changed.
    """
    s = {"length": voice["length"], "emoji": voice["emoji"], "hashtags": voice["hashtags"],
         "exclaim": voice["exclaim"], "tone": voice.get("tone", "neutral"), "variant": 0, "tags": [], "add": [], "remove": [],
         # From your persona (or the structure of a post you liked).
         "hook": voice.get("hook"), "bullets": voice.get("bullets", False), "short_lines": voice.get("short_lines", False),
         "cta": voice.get("cta", "none"), "signature": voice.get("signature"), "fixed_tags": voice.get("fixed_tags", []),
         "avoid": voice.get("avoid", []), "we": voice.get("we", False), "emoji_set": voice.get("emoji_set", []),
         "opener": voice.get("opener")}
    applied = []
    for text in feedback:
        applied = []
        low = text.lower()

        def did(label):
            applied.append(label)

        if re.search(r"\b(shorter|short|concise|trim|brief|tighter)\b", low):
            s["length"] = max(-2, s["length"] - 1); did("shorter")
        if re.search(r"\b(longer|expand|more detail|elaborate|detailed)\b", low):
            s["length"] = min(1, s["length"] + 1); did("longer")
        if re.search(r"\b(formal|professional)\b", low):
            s["tone"] = "formal"; did("more formal")
        if re.search(r"\b(casual|friendly|fun|relaxed|informal)\b", low):
            s["tone"] = "casual"; did("more casual")
        if re.search(r"\b(no|remove|without|drop|less|fewer)\s+(the\s+)?emojis?\b", low):
            s["emoji"] = False; did("no emoji")
        elif re.search(r"\bemojis?\b", low):
            s["emoji"] = True; did("emoji")
        if re.search(r"\b(no|remove|without|drop)\s+(the\s+)?hash ?tags?\b", low):
            s["hashtags"] = 0; s["tags"] = []; did("no hashtags")
        elif re.search(r"\b(more|add)\s+hash ?tags?\b", low):
            s["hashtags"] = min(6, s["hashtags"] + 2); did("more hashtags")
        if tags := re.findall(r"(?<!\w)#(\w+)", text):
            s["tags"] += [t for t in tags if t not in s["tags"]]; did("hashtags " + " ".join(f"#{t}" for t in tags))
        if re.search(r"\b(as a list|use a list|bullets?|bullet points)\b", low):
            s["bullets"] = True; did("as a list")
        elif re.search(r"\b(no list|no bullets|as prose|paragraphs)\b", low):
            s["bullets"] = False; did("no list")
        if re.search(r"\b(end with a question|ask a question|question at the end)\b", low):
            s["cta"] = "question"; did("ends with a question")
        if re.search(r"\b(no sign[- ]?off|without (the )?sign[- ]?off)\b", low):
            s["signature"] = None; did("no sign-off")
        if re.search(r"\b(no exclamation|calmer|tone (it )?down|less excited)\b", low):
            s["exclaim"] = False; did("calmer")
        if re.search(r"\b(another|different|new|alternative)\s+(version|take|one|draft|opening|hook|wording)\b"
                     r"|\b(rewrite|rephrase|variation|again)\b", low):
            s["variant"] += 1; did("another version")
        name = r"@?([A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*){0,3})"
        for m in re.finditer(r"(?i:\b(?:remove|untag|drop|don't mention|do not mention))\s+" + name, text):
            s["remove"].append(m.group(1).lower()); did(f"removed {m.group(1)}")
        for m in re.finditer(r"(?i:\b(?:thanks to|thank|mention|tag|credit))\s+" + name, text):
            s["add"].append(m.group(1)); did(f"thanked {m.group(1)}")
    return s, applied


def _people(state, s):
    people = [p for p in state["people"] if p["name"].lower() not in s["remove"]]
    known = {p["name"].lower() for p in people}
    people += [{"name": n, "url": None, "bio": None} for n in s["add"]
               if n.lower() not in known and n.lower() not in s["remove"]]
    return people


def _style(text, s):
    if s["tone"] == "formal" or not s["exclaim"]:
        for pattern, repl in FORMAL if s["tone"] == "formal" else FORMAL[-1:]:
            text = re.sub(pattern, repl, text)
    return text


def compose_post(state, s):
    a, facts, cat = state["analysis"], state["analysis"]["facts"], state["analysis"]["category"]
    topic, topic_lc = _topic_forms(state["topic"])
    base = sum(map(ord, state["topic"])) + s["variant"]
    slots = {"topic": topic, "topic_lc": topic_lc, "event": facts.get("event"),
             "rank_cap": _cap(facts["rank"]) if facts.get("rank") else None}
    hook, lead = _hook(cat, s, base, slots, topic)
    if s["tone"] == "casual" and hook.endswith(".") and cat in ("hackathon_win", "certification", "new_role"):
        hook = hook[:-1] + "!"
    if s["emoji"]:
        hook = f"{(s['emoji_set'] or [EMOJI[cat]])[0]} {hook}"

    context = [f"It took place {_when_phrase(state['when'])}"]
    if facts.get("event") and facts["event"].lower() not in hook.lower():
        context[0] += f", at {facts['event']}"
    if facts.get("organiser"):
        context[0] += f", organised by {facts['organiser']}"
    context[0] += "."
    if facts.get("team") and cat in ("hackathon_win", "hackathon"):
        context.append(f"We competed as team {facts['team']}.")
    if facts.get("prize") and cat == "hackathon_win":
        context.append(f"The prize: {facts['prize']}.")
    if facts.get("tech") and s["length"] >= 0:
        tech = facts["tech"][:4]
        context.append("Tools and topics: " + (tech[0] if len(tech) == 1 else ", ".join(tech[:-1]) + " and " + tech[-1]) + ".")

    highlights = a["highlights"][:{-2: 0, -1: 1, 0: 2, 1: 3}[s["length"]]]
    if highlights and s["bullets"]:
        details = ("Highlights:" if cat in EVENT_CATEGORIES else "Key points:") + "\n" + "\n".join(f"• {h}" for h in highlights)
    elif highlights:
        details = ("About the event: " if cat in EVENT_CATEGORIES else "Some context: ") + " ".join(highlights)
    else:
        details = PLACEHOLDERS[cat] if s["length"] >= 0 else None

    parts = [hook, lead]
    if s["length"] >= -1:
        parts.append(("\n" if s["short_lines"] else " ").join(context))
    parts.append(details)
    if s["length"] >= 0:
        parts.append(_choose(REFLECTIONS[cat], base, s))
    parts.append(_thanks(_people(state, s), s["we"]))
    if s["cta"] == "question":
        parts.append(CTA_QUESTIONS[cat])
    elif s["length"] >= -1 and not s["signature"]:
        parts.append(_choose(CLOSINGS[cat], base, s))
    if s["signature"]:
        parts.append(s["signature"])
    tags = hashtags(cat, facts, s["hashtags"], s["tags"] + [t for t in s["fixed_tags"] if t not in s["tags"]])
    if tags:
        parts.append(" ".join(tags))
    return _style("\n\n".join(p for p in parts if p), s)


def _avoids(text, s):
    low = text.lower()
    return any(re.search(r"\b" + re.escape(w) + r"\b", low) for w in s["avoid"])


def _choose(options, base, s):
    """A template line, skipping any that use a word you asked to avoid."""
    usable = [o for o in options if not _avoids(o, s)] or [None]
    return usable[base % len(usable)]


def _hook(cat, s, base, slots, topic):
    """Opening line in the persona's (or inspiration's) style. Returns (hook, lead line or None)."""
    style = s["hook"]
    if style == "question":
        return STYLE_HOOKS["question"][cat], f"{topic}."
    if style in ("story", "announcement", "number"):
        hook = STYLE_HOOKS[style].format(**slots)
        if style == "announcement" and s.get("opener"):
            hook = f"{_cap(s['opener'])}: {slots['topic_lc']}."
        if style == "announcement" and s["exclaim"]:
            hook = hook[:-1] + "!"
        return hook, None
    return _pick(HOOKS[cat], base, slots), None


def compose_comment(state, s):
    cat = state["analysis"]["category"]
    base = sum(map(ord, state["topic"])) + s["variant"]
    opener = COMMENT_OPENERS[cat][base % len(COMMENT_OPENERS[cat])]
    if s["emoji"]:
        opener += f" {EMOJI[cat]}"
    topic, _ = _topic_forms(state["topic"])
    parts = [opener, f"{topic}."]
    if s["length"] >= 1:
        parts.append("Looking forward to seeing what comes next.")
    people = _people(state, s)
    if people:
        parts.append("Tagging " + ", ".join(f"@{p['name']}" for p in people) + ".")
    if s["tags"]:
        parts.append(" ".join(f"#{t}" for t in s["tags"]))
    return _style(" ".join(parts), s)


def compose(state, s):
    return compose_comment(state, s) if state["activity"] == "comment" else compose_post(state, s)
