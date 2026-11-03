# LinkedIn Indo

Drafts LinkedIn posts and comments in your voice from the facts you give it. Nothing is posted automatically. See `PRD.md` for the product spec.

Three ways to run the same flow:

| Target | What runs | Drafts saved to |
|---|---|---|
| **MOCK** | `index.html` alone, with an in-browser stub (no network) | memory |
| **LOCAL** | `local_server.py` on this machine | `posts/*.md` |
| **CLOUD** | API Gateway HTTP API + Lambda + DynamoDB + Cognito (Terraform, Python 3.13 on arm64) | DynamoDB |

Switch targets with the `TARGET` toggle in the page header. The CLI (`python3.13 app.py`) uses the local code directly.

## Your persona

The app learns how you write and drafts every post as you. Open **Persona** in the header (it opens by itself the first time), or run `linkedin-indo --persona`.

0. **Scan your profile (quick start):** paste your LinkedIn URL and press **Scan profile**. The app reads your public profile page once, the way a signed-out visitor sees it: name, headline, about and your most recent public posts (LinkedIn embeds them as schema.org data). No login and nothing is posted. Your profile's public visibility must be on. Answers you typed are kept unless you tick "Replace". LinkedIn's terms restrict automated access, so the scan only runs when you press the button.
1. **About you:** name, LinkedIn URL, headline, tone, emoji, length, audience, words you never use, sign-off, hashtags.
2. **Your posts:** upload LinkedIn's own data export (Settings, Data privacy, [Get a copy of your data](https://www.linkedin.com/mypreferences/d/download-my-data), tick Posts). The app reads every post in `Shares.csv`, plus `Profile.csv` and `Comments.csv`, or posts you paste. It never logs in to LinkedIn or scrapes it.
3. **Training:** it learns your length, structure, hook and ending style, I or we, emoji and hashtag habits, reused phrases and topics. The Local ML engine writes with those patterns; the LLM engine gets the persona plus your most similar past posts.

**Tagging:** each person you tag gets a reason (mentor, teammate, organiser, judge, speaker, sponsor, or your own words), and the post thanks them for exactly that.

**Posts you liked:** paste someone's post under Persona. Only its structure is kept (hook type, layout, lists, ending). Pick it in Review and your draft uses that shape with your own facts and voice. An originality check flags any run of 6+ words copied from it, and you can credit the author. The LLM never sees the liked post's text, only its described shape.

Persona files (`profile.json`, `posts.json`, `persona.json`, `inspirations.json`) live in `persona/` (`~/.local/share/linkedin-indo/persona` for the .deb) and stay on your computer. CLOUD drafts carry only the trained summary, not your post archive.

## Engines

Switch with the `ENGINE` toggle in the page header, or at the start of the CLI. Requests carry `engine`, `provider` and `model`; `INDO_ENGINE` and `INDO_PROVIDER` set the defaults.

| Engine | What writes the draft | Needs |
|---|---|---|
| **Local ML** (default) | Offline model in `src/indo_core/` (`ml.py`, `writer.py`): Naive Bayes post-type classifier, rule-based fact extraction, and graph message passing (fixed weights) to pick key sentences. Templates use only facts it found and leave `[ADD: ...]` for the rest. Revisions are commands: shorter, longer, formal, casual, emoji, hashtags, `#Tag`, thank Name, remove Name, another version. | Nothing. `pdftotext` and `tesseract` let it read PDFs and images. |
| **LLM** | A hosted model through `llm.py` | The provider's credentials |

LLM providers (pick a model per request, or set `INDO_<PROVIDER>_MODEL`):

| Provider | Credentials | Default model |
|---|---|---|
| `anthropic` (Claude) | `ANTHROPIC_API_KEY` | `claude-opus-5-5` |
| `bedrock` (Claude on Amazon Bedrock) | AWS keys or a profile (Settings), else the normal AWS chain | `us.anthropic.claude-opus-5-5` (the region's inference profile; `global.` also listed) |
| `openai` | `OPENAI_API_KEY` | `gpt-5` |
| `gemini` | `GEMINI_API_KEY` | `gemini-2.5-flash` |
| `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile` |
| `openrouter` | `OPENROUTER_API_KEY` | `openrouter/auto` |
| `ollama` | none (runs on this machine) | `llama3.2` |

Bedrock serves current Claude models only through cross-region inference profiles (`us.`, `eu.`, `apac.`, `global.`), so a bare `anthropic.claude-*` ID is upgraded to the region's profile. If AWS answers *Operation not allowed* for every model, the AWS account itself is blocked from Bedrock (common on new accounts): fix it in the AWS console, or use other credentials.

Override an OpenAI-compatible endpoint with `INDO_<PROVIDER>_BASE_URL`.

## Settings

**Settings** in the header stores API keys, Amazon Bedrock credentials (region, profile or access keys) and the agent workspace in `settings.json` next to the persona folder (`~/.local/share/linkedin-indo/settings.json` for the .deb, mode 0600). Apps-menu launches have no exported variables, so this is how the LLM engine gets credentials there. A saved key wins over the same environment variable. **Import from Claude Code** copies the AWS (or Anthropic) credentials from `~/.claude/settings.json` when you press it; temporary AWS keys need importing again when they expire. **Test connection** sends one tiny request to the chosen provider.

## Agent

**Agent** in the header opens a chat assistant on Claude (Anthropic API or Amazon Bedrock), a small local Claude Code. It decides which tools to use:

| Tool | Does | Approval |
|---|---|---|
| `web_search`, `fetch_url` | search the web (Bing results page), read pages | no |
| `linkedin_profile` | read a public LinkedIn profile (yours by default) | no |
| `get_persona`, `save_draft` | your persona; save a finished draft to your drafts | no |
| `list_files`, `read_file` | read the workspace folder | no |
| `write_file`, `run_command` | write files, run `bash` commands (120 s limit) in the workspace | **every time** |

File tools cannot leave the workspace (default `~/.local/share/linkedin-indo/workspace`; change it in Settings). Commands run without the app's API keys in their environment. The conversation lives in the page (and the tab's session storage); the backend is stateless, one step per `POST /agent`. Current Claude models on the Anthropic API use server-side refusal fallbacks (`fallbacks: "default"`). A draft is always revised by the engine that wrote it.

The CLOUD backend offers the local engine and the `anthropic` provider (key in SSM).

## Desktop app

`linkedin-indo-desktop` (or **LinkedIn Indo** in the apps menu once the .deb is installed) starts the local backend and opens the UI in its own window: Chromium, Chrome or Brave in app mode, with a separate profile in `~/.local/share/linkedin-indo/window`. Closing the window stops the backend. Without a Chromium-based browser it opens in the default browser instead. Pick a browser with `INDO_BROWSER`. From a checkout: `python3.13 desktop.py`.

## Install as a .deb

```sh
sh packaging/build-deb.sh                     # -> dist/linkedin-indo_<version>_amd64.deb
sudo apt install ./dist/linkedin-indo_*.deb
linkedin-indo-desktop                         # desktop app (also in the apps menu)
linkedin-indo                                 # CLI
linkedin-indo-server                          # web UI on http://localhost:8787/
```

Drafts and style samples live in `~/.local/share/linkedin-indo/`.

## Run locally

```sh
python3.13 -m pip install --user -r requirements.txt
export ANTHROPIC_API_KEY=...       # only for the LLM engine
python3.13 local_server.py        # open http://localhost:8787/ and choose LOCAL
```

Put a few of your own past posts in `samples/` so drafts match your voice.

On this workstation Python 3.13 is managed by `uv`, which refuses plain `pip install --user`; add `--break-system-packages` (with `--user` it only writes to `~/.local/lib/python3.13`).

## Deploy to AWS

The easy way: sign in and let the wizard set everything up.

```sh
linkedin-indo-aws connect        # or: python3.13 aws_connect.py connect
```

It runs `aws login` (your AWS Console sign-in, in the browser; needs AWS CLI v2.32+), shows the account, and asks before deploying. It then runs Terraform (plan, summary, your confirmation, apply), optionally stores your Anthropic API key in SSM, and creates your Cognito sign-in. Afterwards choose TARGET Cloud in the page and sign in. `linkedin-indo-aws status` shows what is connected; `linkedin-indo-aws disconnect` removes every resource. Credentials already in the shell (`AWS_ACCESS_KEY_ID`, ...) are ignored, so it only ever deploys to the account you signed in to.

By hand:

```sh
cd infrastructure
terraform init
terraform plan -out=tfplan        # review, then:
terraform apply tfplan
```

Then follow the `next_steps` output: store the API key in SSM, create your Cognito user, and open http://localhost:8787/ with `local_server.py` running. Choose CLOUD and sign in. Terraform writes `config.cloud.js` for the page.

Remove everything with `terraform destroy`.

## API

The same routes on both backends. On CLOUD, every route except `/health` requires a Cognito ID token in the `Authorization` header, checked by a Lambda authorizer.

- `GET /health`: backend status
- `POST /drafts`: generate a draft (JSON: activity, topic, when, source, people; post_text for comments). Returns draft, history, notes
- `POST /drafts/revise`: revise a draft (JSON: history, feedback)
- `POST /posts`: save a draft (JSON: topic, when, draft)
- `GET /posts`: list the caller's drafts

LOCAL only: `GET`/`POST /settings`, `POST /settings/test` (provider, model), `POST /settings/import-claude-code`, `POST /persona/scan` (url, overwrite), `POST /agent` (messages, provider, model, approvals; returns messages and next: continue, approve or done) and `GET /net` (internet check).

## Tests

```sh
python3.13 -m pip install --user -r requirements-dev.txt
python3.13 -m pytest
```

`index.html?audit` runs the motion checks from PRD section 16.5 (`verify-motion.js`).

## Portfolio brief

A professional-networking product concept localized for Indian users, with profile, discovery, and career-oriented interaction flows.

### Visual system

Editorial professional identity: warm neutrals, strong typographic hierarchy, restrained saffron/indigo signals, and content-led layouts.

### Architecture

The repository contains the product interface and supporting application assets; keep deployment configuration and credentials outside source control.

### Run and output

Follow the project-specific setup instructions. Generated packages and local build artifacts are intentionally excluded from the showcase source.

