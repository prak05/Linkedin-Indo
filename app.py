"""LinkedIn Indo, command-line flow (PRD section 6).

Run:  python3.13 app.py            (add --persona to set up or update your persona)
"""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

import indo_core  # noqa: E402
from indo_core import persona  # noqa: E402
from indo_core.validation import MAX_FILE_BYTES, http_url  # noqa: E402

IMAGE_EXT = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif", ".webp": "image/webp"}
DOC_EXT = {".txt": "text/plain", ".md": "text/markdown", ".pdf": "application/pdf"}


def ask(prompt, *, required=True):
    while True:
        value = input(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("  Please enter a value.")


def choose(prompt, options):
    """options: {key: label}. Returns the chosen key (FR-10)."""
    keys = list(options)
    for i, key in enumerate(keys, 1):
        print(f"  {i}. {options[key]}")
    while True:
        raw = input(f"{prompt} [1-{len(keys)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(keys):
            return keys[int(raw) - 1]
        print(f"  Enter a number from 1 to {len(keys)}.")


def ask_file(kind):
    allowed = IMAGE_EXT if kind == "image" else DOC_EXT
    while True:
        raw = ask(f"Path to the {kind} (blank to skip)", required=False)
        if not raw:
            return None
        path = Path(raw).expanduser()
        if not path.is_file():
            print(f"  No file at {path}.")
        elif path.suffix.lower() not in allowed:
            print(f"  Use one of: {', '.join(sorted(allowed))}.")
        elif path.stat().st_size > MAX_FILE_BYTES:
            print("  That file is larger than 4 MB.")
        else:
            media_type = allowed[path.suffix.lower()]
            if media_type.startswith("text/"):
                return {"type": "file", "name": path.name, "media_type": media_type,
                        "text": path.read_text(encoding="utf-8", errors="replace")}
            data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
            return {"type": kind, "name": path.name, "media_type": media_type, "data": data}


def ask_source():
    print("\nEvent details:")
    kind = choose("Source", {"file": "Upload a .txt, .md or .pdf file", "image": "Upload an image",
                             "url": "Give a URL", "skip": "Skip"})
    if kind in ("file", "image"):
        return ask_file(kind) or {"type": "skip"}
    if kind == "url":
        while True:
            raw = ask("Event URL (blank to skip)", required=False)
            if not raw:
                return {"type": "skip"}
            try:
                return {"type": "url", "url": http_url(raw, "URL")}
            except indo_core.ValidationError as e:
                print(f"  {e}")
    return {"type": "skip"}


def ask_people():
    people = []
    print("\nPeople to thank (blank name to finish). You add the @tags yourself in LinkedIn.")
    while True:
        name = ask(f"Person {len(people) + 1} name", required=False)
        if not name:
            return people
        url = ask("  LinkedIn URL (optional)", required=False)
        reason = ask(f"  Why are you tagging {name}? (mentor, teammate, organiser, judge, speaker, sponsor, or your own words)")
        print("  Paste their headline or About text (optional). Finish with an empty line:")
        bio_lines = []
        while line := input("  > "):
            bio_lines.append(line)
        people.append({"name": name, "url": url or None, "bio": "\n".join(bio_lines) or None, "reason": reason})


def collect():
    print("\nWhat are you writing?")
    activity = choose("Activity", {"post": "Post", "comment": "Comment"})
    req = {"activity": activity}
    if activity == "comment":
        print("Paste the post you are replying to. Finish with an empty line:")
        lines = []
        while line := input("> "):
            lines.append(line)
        req["post_text"] = "\n".join(lines)
    req["topic"] = ask("What is it about")
    req["when"] = ask("When did it happen")
    req["source"] = ask_source()
    req["people"] = ask_people()
    return req


def show(result):
    for note in result.get("notes", []):
        print(f"  note: {note}")
    print("\n" + "-" * 60 + f"\n{result['draft']}\n" + "-" * 60)


def choose_engine():
    """Pick the drafting engine once per run (local model, or an LLM provider and model)."""
    print("\nDrafting engine:")
    if choose("Engine", {"local": "Local model (offline, no AI service)", "llm": "LLM via API"}) == "local":
        return {"engine": "local"}
    providers = indo_core.status()["providers"]
    print("\nProvider:")
    provider = choose("Provider", {k: f"{p['label']}{'' if p['ready'] else ' (credentials not set)'}"
                                   for k, p in providers.items()})
    p = providers[provider]
    print(f"Suggested models: {', '.join(p['models'])}")
    model = ask(f"Model (blank for {p['default']})", required=False) or p["default"]
    return {"engine": "llm", "provider": provider, "model": model}


def session(engine):
    req = {**collect(), **engine}
    print("\nWriting the draft...")
    built = persona.load()
    posts = persona.load_posts() if built else None
    if built:
        print(f"Writing as {built['answers']['name']} (persona trained on {built['stats'].get('posts', 0)} posts).")
    inspiration = ask_inspiration()
    if inspiration:
        req["inspiration"] = inspiration
    result = indo_core.generate(req, persona=built, posts=posts)
    while True:
        show(result)
        action = choose("Next", {"revise": "Request changes", "save": "Save the draft", "quit": "Quit without saving"})
        if action == "revise":
            feedback = ask("What should change")
            print("Revising...")
            try:
                result = indo_core.revise({"history": result["history"], "feedback": feedback, **engine},
                                          persona=built, posts=posts)
            except indo_core.DraftError as e:
                print(f"  {e}")
        elif action == "save":
            saved = indo_core.save_post({"topic": req["topic"], "when": req["when"], "draft": result["draft"]})
            print(f"Saved to {saved['path']}")
            return
        else:
            return


def ask_inspiration():
    """Optionally borrow the format of a saved post you liked."""
    items = persona.list_inspirations()
    if not items:
        return None
    options = {"none": "No, use my usual format"} | {i["id"]: f"{i.get('author') or 'Saved post'}: {', '.join(i['description'][:2])}"
                                                      for i in items}
    print("\nBorrow the format of a post you liked?")
    choice = choose("Format", options)
    if choice == "none":
        return None
    item = next(i for i in items if i["id"] == choice)
    credit = bool(item.get("author")) and choose(f"Credit {item['author']} in the post?", {"no": "No", "yes": "Yes"}) == "yes"
    return {"text": item["text"], "author": item.get("author"), "credit": credit}


def setup_persona():
    """Ask who you are and how you write, load your posts, and train the persona."""
    print("\nYour persona: the app learns how you write from your answers and your own posts.")
    old = persona.load_profile()

    def keep(key, prompt, required=False):
        hint = f" (blank keeps: {old[key]})" if old.get(key) else ""
        return ask(prompt + hint, required=required and not old.get(key)) or old.get(key)

    answers = {
        "name": keep("name", "Your name", required=True),
        "linkedin_url": keep("linkedin_url", "Your LinkedIn URL"),
        "headline": keep("headline", "Your headline"),
        "tone": ask(f"Your tone, up to 4 of: {', '.join(persona.TONES)}", required=False) or old.get("tone"),
        "emoji": ask("Emoji: never, sometimes or often (blank: learn from my posts)", required=False) or old.get("emoji"),
        "length": ask("Length: short, medium or long (blank: learn from my posts)", required=False) or old.get("length"),
        "audience": keep("audience", "Who reads your posts"),
        "avoid": ask("Words you never use (comma separated)", required=False) or old.get("avoid"),
        "signature": keep("signature", "Your usual sign-off line"),
        "hashtags": ask("Hashtags you always use (comma separated)", required=False) or old.get("hashtags"),
    }
    try:
        answers = persona.validate_answers({k: v for k, v in answers.items() if v})
    except indo_core.ValidationError as e:
        print(f"  {e}")
        return setup_persona()
    persona.save_profile(answers)
    print("\nLoad your posts. Download them from LinkedIn: Settings > Data privacy > Get a copy of your data")
    print("(https://www.linkedin.com/mypreferences/d/download-my-data), tick Posts, and LinkedIn emails a ZIP.")
    while raw := ask("Path to the export ZIP, or a .txt of posts separated by --- (blank to skip)", required=False):
        path = Path(raw).expanduser()
        try:
            if path.suffix.lower() == ".zip":
                data = persona.import_export(path.read_bytes())
                for note in data["notes"]:
                    print(f"  {note}")
                total = persona.add_posts(data["posts"])
                persona.save_comments(data["comments"])
            else:
                total = persona.add_posts(persona.import_text(path.read_text(encoding="utf-8", errors="replace")))
            print(f"  {total} posts stored.")
            break
        except (OSError, indo_core.ValidationError) as e:
            print(f"  {e}")
    built = persona.retrain()
    print("\nWhat the app learned:")
    for line in built["summary"]:
        print(f"  - {line}")
    return built


def main():
    print("LinkedIn Indo: drafts LinkedIn posts in your voice. Nothing is posted automatically.")
    print("The local engine runs offline. An LLM engine sends your answers, event material and pasted bios to the chosen provider.")
    try:
        if "--persona" in sys.argv or (persona.load() is None and choose(
                "\nNo persona yet. Set it up now so drafts sound like you?", {"yes": "Yes (recommended)", "no": "Not now"}) == "yes"):
            setup_persona()
        engine = choose_engine()
        while True:
            try:
                session(engine)
            except (indo_core.ValidationError, indo_core.DraftError) as e:
                print(f"\n  {e}")
            if choose("\nStart another post?", {"yes": "Yes", "no": "No"}) == "no":
                return 0
    except indo_core.DraftError as e:
        print(e, file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nBye.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
