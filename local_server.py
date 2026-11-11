"""Local backend for index.html: the LOCAL target.

Run:  python3.13 local_server.py      then open http://localhost:8787/

Serves the page and the same API as the AWS deployment, on this machine only:
  GET  /health         POST /drafts        POST /drafts/revise
  GET  /posts          POST /posts         (drafts saved to posts/*.md)
plus what only runs here:
  GET  /settings       POST /settings      POST /settings/test     POST /settings/import-claude-code
  POST /persona/scan   (your public LinkedIn profile)
  POST /agent          (chat agent with tools)                     GET  /net (internet check)
"""

import base64
import binascii
import json
import os
import socket
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import indo_core  # noqa: E402
from indo_core import agent, linkedin, llm, persona, settings  # noqa: E402
from indo_core.sources import FetchError  # noqa: E402

HOST = "127.0.0.1"
PORT = int(os.environ.get("INDO_PORT", "8787"))
MAX_BODY = 8 * 1024 * 1024
# A LinkedIn data export ZIP (base64) can be larger than a normal request.
MAX_IMPORT_BODY = 60 * 1024 * 1024
# Written by Terraform when the CLOUD stack is deployed (aws_connect.py).
CLOUD_CONFIG = Path(os.environ.get("INDO_CLOUD_CONFIG") or ROOT / "config.cloud.js")
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/config.js": ("config.js", "text/javascript; charset=utf-8"),
    "/verify-motion.js": ("verify-motion.js", "text/javascript; charset=utf-8"),
    "/config.cloud.js": ("config.cloud.js", "text/javascript; charset=utf-8"),
    "/vendor/tailwindcss-browser-4.3.3.js": ("vendor/tailwindcss-browser-4.3.3.js", "text/javascript; charset=utf-8"),
    "/icon.svg": ("packaging/linkedin-indo.svg", "image/svg+xml"),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "LinkedInIndo/0.1"
    # Swapped out in tests.
    client = None
    samples = None
    fetch = None
    posts_dir = None
    persona_dir = None

    def _allowed_hosts(self):
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _origin(self):
        origin = self.headers.get("Origin")
        return origin if origin in {f"http://{h}" for h in self._allowed_hosts()} else None

    def _send(self, status, body=b"", ctype="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if origin := self._origin():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, data):
        self._send(status, json.dumps(data).encode("utf-8"))

    def _guard(self):
        # Reject other Host headers so a malicious page cannot reach this server via DNS rebinding.
        if self.headers.get("Host") not in self._allowed_hosts():
            self._json(HTTPStatus.FORBIDDEN, {"error": "Unexpected Host header."})
            return False
        return True

    def _body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        limit = MAX_IMPORT_BODY if self.path.split("?", 1)[0] == "/persona/import" else MAX_BODY
        if length < 0 or length > limit:
            raise indo_core.ValidationError(f"Request body is too large (limit {limit // (1024 * 1024)} MB).")
        if "application/json" not in (self.headers.get("Content-Type") or ""):
            raise indo_core.ValidationError("Send JSON with Content-Type: application/json.")
        try:
            return json.loads(self.rfile.read(length) or b"null")
        except json.JSONDecodeError:
            raise indo_core.ValidationError("Request body is not valid JSON.") from None

    def do_OPTIONS(self):
        if not self._guard():
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        if origin := self._origin():
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Max-Age", "600")
            self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._guard():
            return
        path = self.path.split("?", 1)[0]
        if path in STATIC:
            name, ctype = STATIC[path]
            file = CLOUD_CONFIG if name == "config.cloud.js" else ROOT / name
            # config.cloud.js exists only while the AWS stack is deployed.
            body = file.read_bytes() if file.exists() else b"// CLOUD not deployed\n"
            self._send(HTTPStatus.OK, body, ctype)
        elif path == "/health":
            self._json(HTTPStatus.OK, {"target": "local", "ok": True, **indo_core.status()})
        elif path == "/persona":
            self._json(HTTPStatus.OK, self._persona_view())
        elif path == "/inspirations":
            self._json(HTTPStatus.OK, persona.list_inspirations(self.persona_dir))
        elif path == "/posts":
            self._json(HTTPStatus.OK, indo_core.list_posts(self.posts_dir))
        elif path == "/settings":
            self._json(HTTPStatus.OK, settings.view())
        elif path == "/rag/stats":
            from indo_core.vector_db.query import stats as rag_stats
            self._json(HTTPStatus.OK, rag_stats())
        elif path == "/net":
            self._json(HTTPStatus.OK, {"online": internet_ok()})
        else:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})

    do_HEAD = do_GET

    def do_POST(self):
        if not self._guard():
            return
        path = self.path.split("?", 1)[0]
        routes = {
            "/drafts": lambda body: indo_core.generate(self._with_inspiration(body), client=self.client, samples=self.samples,
                                                       fetch=self.fetch, **self._persona_args()),
            "/drafts/revise": lambda body: indo_core.revise(body, client=self.client, samples=self.samples,
                                                            **self._persona_args()),
            "/persona": self._save_answers,
            "/persona/import": self._import_posts,
            "/inspirations": lambda body: persona.add_inspiration(body, self.persona_dir),
            "/inspirations/delete": self._delete_inspiration,
            "/posts": lambda body: indo_core.save_post(body, directory=self.posts_dir),
            "/cover-letters": lambda body: self._cover_letter(body),
            "/cover-letters/revise": lambda body: self._cover_letter_revise(body),
            "/cover-letters/save": lambda body: indo_core.cover_letters.save(body),
            "/persona/scan": self._scan_profile,
            "/settings": settings.save,
            "/settings/test": lambda body: llm.test_connection((body or {}).get("provider"), (body or {}).get("model"),
                                                               client=self.client),
            "/settings/import-claude-code": lambda body: settings.import_claude_code(),
            "/agent": lambda body: agent.step(body, client=self.client, persona_dir=self.persona_dir,
                                              posts_dir=self.posts_dir),
            "/rag/search": self._rag_search,
            "/rag/ingest": self._rag_ingest,
        }
        if path not in routes:
            self._json(HTTPStatus.NOT_FOUND, {"error": "Not found."})
            return
        try:
            result = routes[path](self._body())
        except indo_core.ValidationError as e:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(e)})
        except indo_core.DraftError as e:
            self._json(e.status, {"error": str(e)})
        except FetchError as e:
            self._json(HTTPStatus.BAD_GATEWAY, {"error": f"{str(e)[:1].upper()}{str(e)[1:]}."})
        except Exception:  # noqa: BLE001 - never leak internals to the page
            self.log_error("Unhandled error on %s", path)
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Something went wrong on the local backend."})
        else:
            self._json(HTTPStatus.CREATED if path == "/posts" else HTTPStatus.OK, result)

    def _cover_letter(self, body):
        built = persona.load(self.persona_dir)
        req = indo_core.cover_letters.validate_request(body)
        return {"draft": indo_core.cover_letters.generate(req, built),
                "track": req["track"], "engine": "local"}

    def _cover_letter_revise(self, body):
        built = persona.load(self.persona_dir)
        return {**indo_core.cover_letters.revise(body, built), "engine": "local"}

    def _rag_search(self, body):
        from indo_core.vector_db.query import search as rag_search
        query = (body or {}).get("query", "").strip()
        if not query:
            raise indo_core.ValidationError("Query is required.")
        n = min(int((body or {}).get("n_results", 8)), 25)
        category = (body or {}).get("category") or None
        results = rag_search(query, n_results=n, category_filter=category)
        return {"query": query, "results": results}

    def _rag_ingest(self, body):
        from indo_core.vector_db.ingest import build_index
        force = bool((body or {}).get("force", False))
        return build_index(force=force)

    # ---------- Persona (stays on this machine) ----------

    def _persona_args(self):
        built = persona.load(self.persona_dir)
        return {"persona": built, "posts": persona.load_posts(self.persona_dir) if built else None}

    def _persona_view(self):
        return {"persona": persona.load(self.persona_dir), "profile": persona.load_profile(self.persona_dir),
                "post_count": len(persona.load_posts(self.persona_dir)),
                "inspirations": persona.list_inspirations(self.persona_dir),
                "choices": {"tone": persona.TONES, "emoji": persona.EMOJI_CHOICES, "length": persona.LENGTH_CHOICES,
                            "reasons": persona.TAG_REASONS}}

    def _save_answers(self, body):
        answers = persona.validate_answers(body)
        persona.save_profile(answers, self.persona_dir)
        persona.retrain(self.persona_dir)
        return self._persona_view()

    def _import_posts(self, body):
        if not isinstance(body, dict):
            raise indo_core.ValidationError("Send {\"zip\": base64} or {\"text\": pasted posts}.")
        notes, comments = [], []
        if body.get("zip"):
            try:
                data = base64.b64decode(body["zip"], validate=True)
            except (binascii.Error, TypeError, ValueError):
                raise indo_core.ValidationError("The uploaded ZIP is not valid base64.") from None
            result = persona.import_export(data)
            posts, notes, comments = result["posts"], result["notes"], result["comments"]
            profile = persona.load_profile(self.persona_dir)
            if result["profile"].get("name") and not profile:
                # First import: start the persona from the export's profile; answers can refine it later.
                persona.save_profile(persona.validate_answers({k: v for k, v in result["profile"].items() if v}),
                                     self.persona_dir)
        elif body.get("text"):
            posts = persona.import_text(body["text"])
            notes = [f"Read {len(posts)} pasted posts."]
        else:
            raise indo_core.ValidationError("Upload your LinkedIn export ZIP or paste some posts.")
        total = persona.add_posts(posts, self.persona_dir, replace=bool(body.get("replace")))
        if comments:
            persona.save_comments(comments, self.persona_dir)
        if persona.load_profile(self.persona_dir):
            persona.retrain(self.persona_dir)
            notes.append(f"Persona retrained on {total} posts.")
        else:
            notes.append("Answer the persona questions to finish training.")
        return {**self._persona_view(), "notes": notes}

    def _scan_profile(self, body):
        """Read the public LinkedIn profile, fill in the persona answers and add the visible posts."""
        body = body if isinstance(body, dict) else {}
        profile = persona.load_profile(self.persona_dir)
        found = linkedin.scan(body.get("url") or profile.get("linkedin_url") or "")
        # Scanned facts fill empty answers; answers you typed stay unless you ask to overwrite them.
        overwrite = bool(body.get("overwrite"))
        merged = dict(profile)
        merged["linkedin_url"] = found["url"]
        for key, limit in (("name", 200), ("headline", 300), ("about", 2000)):
            if found[key] and (overwrite or not merged.get(key)):
                merged[key] = found[key][:limit]
        persona.save_profile(persona.validate_answers(merged), self.persona_dir)
        notes = list(found["notes"])
        if found["posts"]:
            total = persona.add_posts([{"text": p["text"][:persona.MAX_POST_CHARS], "date": (p.get("date") or "")[:40],
                                        "url": (p.get("url") or "")[:500]} for p in found["posts"]], self.persona_dir)
            notes.append(f"{total} posts in your persona now.")
        persona.retrain(self.persona_dir)
        notes.append("Persona retrained.")
        scanned = {k: found[k] for k in ("url", "name", "headline", "about", "location", "works_for", "education")}
        return {**self._persona_view(), "scan": {**scanned, "post_count": len(found["posts"])}, "notes": notes}

    def _delete_inspiration(self, body):
        persona.delete_inspiration((body or {}).get("id"), self.persona_dir)
        return persona.list_inspirations(self.persona_dir)

    def _with_inspiration(self, body):
        """Resolve a saved inspiration by id, so the page need not resend its text."""
        if isinstance(body, dict) and body.get("inspiration_id") and not body.get("inspiration"):
            item = next((i for i in persona.list_inspirations(self.persona_dir) if i["id"] == body["inspiration_id"]), None)
            if item is None:
                raise indo_core.ValidationError("That inspiration no longer exists.")
            body = {**body, "inspiration": {k: item.get(k) for k in ("text", "author")}
                    | {"credit": bool(body.get("credit", item.get("credit")))}}
        return body

    def log_message(self, fmt, *args):
        # Log method and path only; bodies hold user content.
        sys.stderr.write(f"{self.log_date_time_string()} {fmt % args}\n")


def internet_ok(host="1.1.1.1", port=443, timeout=3):
    """True if this machine can open a connection to the internet."""
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def make_server(port=PORT):
    # API keys saved in Settings, so the LLM engine works without exported variables.
    settings.apply()
    return ThreadingHTTPServer((HOST, port), Handler)


def main():
    server = make_server()
    print(f"LinkedIn Indo local backend on http://localhost:{server.server_address[1]}/  (Ctrl-C to stop)")
    print("Engine LOCAL runs offline. Engine LLM sends your answers, event material and pasted bios to the chosen provider.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
