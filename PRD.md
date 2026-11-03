# PRD: LinkedIn Indo

**Version:** 0.1 (draft)
**Owner:** Prak
**Status:** Working prototype (CLI)
**Last updated:** 2026-10-24

---

## 1. Summary

LinkedIn Indo is a guided command-line assistant that drafts LinkedIn posts and comments. The user answers a short set of questions, supplies event details (document, image, or URL), optionally tags people to thank, and receives a draft written in their own voice. The user refines the draft in conversation and saves the final version locally.

## 2. Problem

Writing a good LinkedIn post after an event takes effort. The user has the raw facts (what happened, when, who helped) but struggles to turn them into a clear, well-structured post that sounds like them. Event pages, brochures, and notes are scattered across formats. Thank-you posts often miss people or sound generic.

## 3. Goals

- Produce a publish-ready draft in under 5 minutes of user effort.
- Match the user's writing voice, using their own past posts as reference.
- Pull facts from whatever event material the user has (text, PDF, image, or web page) without inventing details.
- Make thank-you and tagging steps easy and complete.
- Keep the user in control: nothing is posted automatically.

## 4. Non-goals (v0.1)

- Posting directly to LinkedIn or any API integration.
- Scraping LinkedIn profiles or posts (LinkedIn blocks automated access and prohibits it in its terms).
- Automatic @tag resolution. The user adds tags in LinkedIn's own editor.
- Image or graphic generation.
- Multi-user accounts or cloud hosting. (A web UI is planned for M4; see section 16.)
- Scheduling or analytics.

## 5. Target user

**Primary:** the developer or student who attends events, workshops, or competitions and wants to share them on LinkedIn. Comfortable with a terminal and Python.

**Secondary (future):** anyone who posts about events and wants a faster, more consistent workflow.

## 6. User flow

1. Launch with `python3.13 app.py`.
2. Choose **Post** or **Comment**.
3. Answer: what the post is about, and when it happened.
4. Provide event details: upload `.txt`/`.md`/`.pdf`, upload an image, give a URL, or skip.
5. Optionally add people to thank: name, LinkedIn URL, and pasted headline/About text.
6. Review the generated draft.
7. Either request changes (repeat step 6), save the draft, or quit.
8. Choose whether to start another post.

## 7. Functional requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Offer Post and Comment as the activity types. | Must |
| FR-2 | Ask for the topic and the date or period of the event. | Must |
| FR-3 | Accept event details as text, Markdown, PDF, image, or URL. | Must |
| FR-4 | Fetch and clean text from a URL. If the fetch fails, continue without it and say so. | Must |
| FR-5 | Collect zero or more people, each with name, optional LinkedIn URL, and optional bio text. | Must |
| FR-6 | Load past posts from `samples/` as style references. | Must |
| FR-7 | Generate a draft using the system prompt rules: hook, 2 to 4 short paragraphs, closing line, at most 4 hashtags. | Must |
| FR-8 | Allow iterative revision through free-text feedback, keeping prior context. | Must |
| FR-9 | Save the final draft as a timestamped `.md` file in `posts/`. | Must |
| FR-10 | Validate menu choices and file paths, with clear messages on bad input. | Should |
| FR-11 | Allow a Comment flow that drafts a reply to a pasted post. | Should |
| FR-12 | Support a `--style-only` mode that learns voice from samples without event input. | Could |
| FR-13 | Export drafts to a clipboard-ready format. | Could |

## 8. Non-functional requirements

- **Accuracy:** no invented facts, names, dates, or numbers. Missing information is flagged, not filled in.
- **Privacy:** all data stays local except what is sent to the Anthropic API. Users are told which content is sent. Bio text and URLs are only sent when the user provides them.
- **Security:** the API key is read from `ANTHROPIC_API_KEY` and never written to files or logs.
- **Performance:** a draft returns in under 15 seconds for typical inputs (under 20,000 characters of context).
- **Reliability:** network or file errors do not crash the session.
- **Portability:** runs on Linux and macOS with Python 3.13.
- **Cost:** a typical session uses a single generation call plus one per revision.

## 9. Technical design

- **Language:** Python 3.13.
- **Model:** `claude-sonnet-4-6` through the Anthropic SDK.
- **Dependencies:** `anthropic`, `requests`.
- **Input handling:** text files as text, images as base64 image blocks, PDFs as base64 document blocks, URLs fetched and stripped of HTML.
- **State:** conversation history is kept in memory for the current draft only.
- **Storage:** `samples/` (input), `posts/` (output). No database.

## 10. Quality and success metrics

| Metric | Target |
|------|--------|
| Drafts accepted with 0 to 2 revision rounds | 70% or more |
| Time from launch to saved draft | Under 5 minutes |
| Facts in draft not present in source material | 0 in spot checks |
| Drafts judged "sounds like me" by the user | 4 out of 5 or more |
| Session crashes per 20 sessions | 0 |

## 11. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Model invents event details | High (credibility) | Strict system prompt; spot-check before posting; user reviews every draft. |
| URL fetch returns mostly navigation or JavaScript-rendered content | Medium | Tell the user when little text was extracted; suggest uploading a file instead. |
| LinkedIn terms or blocking | High | No scraping. Users paste their own content. |
| Sensitive data sent to the API | Medium | Warn the user at startup; document what is sent. |
| Generic, repetitive output | Medium | Style samples; revision loop; future prompt tuning. |
| Large PDFs exceed context limits | Low | Truncate text and warn; cap document size. |

## 12. Dependencies and constraints

- Requires an Anthropic API key and internet access.
- Requires Python 3.13 installed as `python3.13`.
- Depends on the public availability of event pages for URL input.

## 13. Milestones

| Milestone | Scope | Status |
|-----------|-------|--------|
| M0 | Core CLI: Post flow, file/image/URL input, draft, revise, save | Done (untested) |
| M1 | Test on real events; tune system prompt; add input validation (FR-10) | Planned |
| M2 | Comment flow (FR-11); style-only mode (FR-12) | Planned |
| M3 | Clipboard export (FR-13); packaging with a `requirements.txt` | Planned |
| M4 | Web UI with the motion system in section 16 (CLI remains supported) | Planned |

## 14. Open questions

1. Should the app remember past events and people across sessions, or start fresh each time?
2. Is a lightweight web UI worth building later, or does the CLI meet the need?
3. Should drafts include an emoji or tone setting, or stay with one fixed voice?
4. What is the right length target: short (under 150 words) or long-form (up to 300)?
5. Should the app warn when an event page is likely to be behind a login?

## 15. Glossary

- **Draft:** a generated post or comment not yet saved as final.
- **Style samples:** past posts placed in `samples/` to guide voice.
- **Tagging:** mentioning a LinkedIn user with @name. Done manually in LinkedIn.

---

## 16. Web UI and motion design (M4)

**Scope:** a browser front-end for the same flow in section 6. It targets the feel of a high-end product launch page: fluid, cinematic, and deliberate. Functionality, data handling, and the API contract stay identical to the CLI. The CLI is not replaced.

**Visual reference:** product launch pages from premium consumer software, such as the Launchly page on the Apple App Store. Reference is for mood and pacing only, not for copying layout or assets.

**Implementation constraint:** native CSS or lightweight animation utilities only. No heavy animation frameworks unless a later review approves one.

### 16.1 Cinematic choreography (staggering)

- **No simultaneous fades.** Elements never all fade in at once on load.
- **Reveal sequence:**
  1. Structural layout container.
  2. Main editorial typography (headline, then supporting copy).
  3. Supporting interface: buttons, navigation, cards.
- **Stagger increments:** 50 to 80 ms per element group, applied through sequential delays (for example `delay-100`, `delay-200`, and so on).

### 16.2 Easing and timing

- **Banned:** `linear`, `ease`, `ease-in`, `ease-out`.
- **Structural entries and slides:** `cubic-bezier(0.16, 1, 0.3, 1)`.
- **Micro-interactions and hovers:** `cubic-bezier(0.25, 1, 0.5, 1)`.
- **Duration:**
  - Structural macro-transitions: 400 to 600 ms.
  - Micro-interactions (button hovers, active states): under 200 ms.

### 16.3 Spatial continuity (transitions as camera moves)

- **No static spawning.** Entering elements always travel.
- **Entry motion:** a subtle `translateY` or scale change paired with an opacity fade. Headings glide up 8 to 12 px into place.
- **Component morphing:** when a card expands or a modal opens, the bounding box animates smoothly. Inner content clips cleanly during the transition. Layouts never pop into existence.

### 16.4 Micro-interactions

- **Magnetic hover states:** buttons and links use crisp, transformative hovers. Example: an arrow link moves 4 px right on hover. Border colors interpolate smoothly rather than snapping.
- **Contextual masks:** CSS `clip-path` or gradient masks create structural reveals, such as a video wipe or a shutter opening (for example, when the draft panel appears).
- **Hardware acceleration:** animate only `transform` and `opacity` where possible. Target a steady 60 fps, and 120 fps on capable displays.

### 16.5 Acceptance criteria

| ID | Criterion | Check |
|----|-----------|-------|
| MO-1 | No element group fades in simultaneously on initial load. | Manual review of load sequence. |
| MO-2 | Stagger gaps fall between 50 and 80 ms. | Inspect CSS delays. |
| MO-3 | No `linear`, `ease`, `ease-in`, or `ease-out` appears in the stylesheet. | Grep the stylesheet. |
| MO-4 | Structural transitions run 400 to 600 ms; micro-interactions run under 200 ms. | Inspect CSS durations. |
| MO-5 | Headings travel 8 to 12 px on entry while fading in. | Inspect CSS transforms. |
| MO-6 | Card and modal expansions animate bounding box size with clipped overflow. | Manual test in browser. |
| MO-7 | Animated properties are limited to `transform` and `opacity` (plus `clip-path` for masks). | Performance panel shows no layout or paint thrash. |
| MO-8 | Animations hold steady frame rate on a mid-range laptop. | Browser performance trace. |
| MO-9 | Users who set `prefers-reduced-motion` get the same content with minimal motion. | Toggle OS setting and verify. |

### 16.6 Accessibility note

Reduced-motion support (MO-9) is required, not optional. Animations must never hide content or block interaction. Every reveal completes within the timing limits above so content is usable on screen within about one second.

### 16.7 Open questions for the web UI

1. Is a single-page layout enough, or does the flow need separate screens for each step?
2. Should the draft panel use the clip-path shutter, or a simpler slide?
3. Which browsers are in scope for the 120 fps target?
