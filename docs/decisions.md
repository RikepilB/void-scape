# read-video — Decision Log

Append-only ADR log. Newest entries at the bottom. One entry per real decision (not per
confirmed-the-obvious question) — see `grill-with-docs` skill for how entries land here.

---

### 2026-07-09 — Platform-expansion ideation scopes to the consumption pipeline, not publishing

**Context:** User asked to "ideate process to improve and workflows to use: instagram, substack,
facebook, x, linkedin, youtube" — ambiguous between two unrelated problems: (a) extending
read-video's existing capture→analyze pipeline (`/ig-pipeline`'s shape: save something → get it
read/transcribed/noted into the vault) to more platforms, or (b) the user's own content-creation/
publishing/growth workflow across those platforms.

**Decision:** This ideation track is (a) — consumption-pipeline expansion, extending
`docs/ROADMAP.md` Phase 2 (platform expansion, capture side). Own-content publishing workflows are
explicitly out of scope for this track.

**Alternatives considered:** (b) publishing workflow — rejected for this track, unrelated to
read-video's read/consume engine; could be its own separate initiative later. (c) both in
parallel — rejected, needs sequencing not simultaneous design.

**Consequences:** Facebook and YouTube are new platforms not yet in ROADMAP Phase 2 (which only
listed X, TikTok, LinkedIn, Substack) — need their own capture-adapter feasibility check (API vs.
browser-automation vs. ToS fit) before joining that phase's milestone list.

---

### 2026-07-09 — YouTube is the first new capture-adapter; uses the official Data API, not browser automation

**Context:** Of the platform-expansion candidates, YouTube's "read" axis already works today
(`video.py`/`yt-dlp` take a YouTube URL directly) — only the "capture" axis (playlist → queue) is
missing. That makes it the lowest-new-build-effort next milestone, unlike every other capture
adapter shipped so far (Instagram), which needed browser automation because IG has no official
saved-collection API.

**Decision:** YouTube capture-adapter is next. It uses the official **YouTube Data API v3**
(OAuth/API-key via Google Cloud Console), not `Codex Chrome control` browser automation.

**Alternatives considered:** Browser automation mirroring `instagram_capture_helper.py` — rejected;
YouTube has a real, stable, ToS-clean API for playlist access, so there's no reason to inherit
browser automation's known fragility (selector breaks, live-watch-first-run requirement) here.

**Consequences:** This is read-video's first capture-adapter that isn't `Codex Chrome control`-based —
Phase 0's "capture-adapter interface" (ROADMAP.md) needs to abstract over *both* mechanisms, not
just browser automation. New one-time setup cost: Google Cloud Console project + OAuth consent
screen, documented wherever this ships (likely `skill/references/` alongside `backends.md`).

---

### 2026-07-09 — YouTube adapter sources Watch Later and removes items after capture

**Context:** Needed a "save something" source list (mirroring IG's "Cursos" collection) and a
dedup/marker convention (mirroring IG's "unsave = captured" pattern) for the YouTube adapter.

**Decision:** Source list is the built-in **Watch Later** playlist. After a video's URL is
successfully written to the capture queue, the adapter removes it from Watch Later via the Data
API — same low-blast-radius mutation-as-marker pattern IG's capture helper already uses. Content-
keyed dedup against the vault (matching `/ig-pipeline`'s analysis-phase dedup) still applies on
top, unchanged.

**Alternatives considered:** A dedicated custom playlist (rejected — more setup friction, no
real benefit over Watch Later for a single user). Liked videos as source (rejected — wrong
signal, conflates "liked" with "want this processed"). Leave-list-untouched/content-dedup-only
(rejected — loses the at-a-glance "still pending" signal Watch Later gives when items get
removed as they're processed).

**Consequences:** None — matches existing IG precedent exactly, no new risk class introduced.

---

### 2026-07-09 — YouTube adapter ships as a one-off; Phase 0's capture-adapter interface is extracted afterward

**Context:** ROADMAP.md's Phase 0 calls for a generic capture-adapter interface before more
platforms are added. With only one real implementation (Instagram) to generalize from, designing
that interface now risks guessing the wrong abstraction.

**Decision:** Build the YouTube capture-adapter as a second one-off (same discipline that shipped
Instagram's), not against a pre-built interface. Extract Phase 0's interface afterward, once two
real implementations (IG + YouTube) exist to compare.

**Alternatives considered:** Interface-first — rejected for this milestone; front-loads design
work against only one working example, the same anti-pattern this repo's own AGENTS.md rules
warn against ("no premature abstraction... three similar lines is better").

**Consequences:** Phase 0 (capture-adapter interface) explicitly deferred until after the YouTube
adapter ships — ROADMAP.md's phase ordering updated to reflect this.
---

### 2026-07-17 - Watch Later is not API-accessible; YouTube capture uses a dedicated private playlist

**Context:** The 2026-07-09 YouTube decision chose the official YouTube Data API v3 and the built-in Watch Later playlist as the source queue. Current Google docs contradict the Watch Later part: `playlistItems.list` documents `watchLaterNotAccessible` and `playlistOperationUnsupported` errors for Watch Later, and `playlists.list` says the API cannot list the Watch Later playlist. Official API remains the right mechanism, but Watch Later is not a workable source.

**Decision:** Supersede only the source-list portion of the 2026-07-09 decision. The YouTube capture adapter should use a user-owned private playlist, default title `Read Video Queue`, configured by playlist ID or discovered with `playlists.list?mine=true`. After each URL is durably appended to `urls.md`, remove that playlist item with `playlistItems.delete` as the captured marker.

**Alternatives considered:** Keep Watch Later (rejected: official API docs say it is inaccessible). Browser automation for Watch Later (rejected for this adapter because the earlier decision explicitly chose the official API to avoid selector fragility). Leave the playlist untouched and rely only on content dedup (rejected: loses the visible pending queue signal that made the IG unsave marker useful).

**Consequences:** One-time setup changes from "use Watch Later" to "create or choose a private queue playlist." The implementation plan must document OAuth, playlist ID/title configuration, quota cost (`playlistItems.list` is 1 unit; `playlistItems.delete` is 50 units), and the fact that `youtube.readonly` is insufficient for deletion.

---

### 2026-08-28 — Media-reader interface: protocol yes, generic implementation no (issue #15)

**Context:** Milestone 0.2 deferred a generic reader interface until a third concrete shape existed.
`article.py` (local HTML/Markdown, RSS/Atom, non-video URLs) shipped alongside `image.py` and
`video.py`. GitHub issue #15 asked to compare discovery, probe, estimate, approvals, evidence, and
errors across all three before extracting anything.

**Decision:** Document a **small shared protocol** — each reader exposes `manifest` / `probe` /
`estimate` / `run` with the same exit-code map and optional `{ok,data,error,meta}` envelope;
`voidscape.py` maps `inspect → preview → read`. **Do not** add a shared reader implementation
layer or base class. Keep `video.py`, `image.py`, and `article.py` as focused siblings; image and
article continue importing envelope, pricing, and error helpers from `video.py`.

**Alternatives considered:** No documented interface (rejected — agents already depend on manifest/
envelope parity). Shared implementation / base class (rejected — probe fields, cost drivers,
approval gates, and evidence layouts differ materially; a generic layer would hide real differences
or leak video knobs into text readers).

**Consequences:** ROADMAP milestone 0.2 closed by spec, not refactor. New readers follow the
protocol checklist in `docs/superpowers/specs/2026-08-28-media-reader-interface-reassessment.md`.
Revisit extraction only after a fourth reader duplicates substantial CLI boilerplate without
masking behavioral differences. Regression tests in `tests/test_media_reader_protocol.py`.

---

### 2026-08-29 — Agent documentation uses a canonical Markdown tree with evidence and status labels

**Context:** Issues #18-#28 expand Voidscape's agent documentation and autonomy guidance. Existing
facts were spread across the skill contract, architecture, harness notes, roadmap, reader docs, and
design specs. Browser-vendor capabilities and local Voidscape behavior also used different evidence
standards, which made overclaiming easy.

**Decision:** Add `docs/agents/` as the canonical agent-facing documentation tree. Keep Markdown as
the source format and link it from the existing README and hand-written HTML site. Harness claims use
`personally-tested`, `vendor-documented`, or `unverified`; product capabilities use `shipped`,
`dev-only`, `planned`, or `parked`, tied to code and tests on `main`. The harness owns permitted
browser interaction, while Voidscape keeps `inspect -> preview -> read` and its per-job gates.

**Alternatives considered:** Expand only the existing flat documents (rejected because agents still
lack one discoverable entry point). Build a generator before the content (rejected because issue #28
owns that decision and Markdown delivery must not wait). Treat vendor documentation as Voidscape
verification (rejected because it obscures the host, permission, and test boundary).

**Consequences:** Issue #19 implements the tree and minimal navigation; issue #21 enforces truth in
tests. Voidscape does not gain browser automation, cookie access, or unattended execution from this
documentation change.

---

### 2026-08-29 — Observe capture ships as a focused sibling CLI, not a guided subcommand

**Context:** Issue #23 needed an on-demand screenshot/short-clip contract without rebuilding
screenpipe or expanding the guided media-selection interface. The user chose an installed sibling
script over `voidscape.py observe ...` or a repository-only developer helper.

**Decision:** Implement `skill/scripts/observe.py` with `doctor`, `screenshot`, `clip`, and `status`.
Capture delegates to ffmpeg, supports Windows and Linux X11, records no audio, refuses overwrites,
and returns local files. `voidscape doctor` reports optional readiness only. Every captured file
still enters the separate `inspect -> preview -> read` flow.

**Alternatives considered:** Nested `voidscape observe` commands (rejected because capture is a
companion concern, not a media-reader dispatch mode). `scripts/observe_helper.py` (rejected because
the selected capability should install with the skill). Embed or manage screenpipe (rejected because
it creates a separate service, retention, permission, and dependency surface).

**Consequences:** The installer gains the script automatically by copying `skill/`; #24 must add
mocked platform/error tests and update discovery status. macOS, Wayland, audio, ambient capture,
browser automation, and automatic evidence reads remain out of scope.

---

### 2026-08-29 — A future browser bridge belongs in a dedicated repository

**Context:** Issue #25 expands the closed #14 browser-bridge design into an implementation-ready
permission, tool, and threat contract. A browser extension or native host has a materially different
attack surface, release cadence, dependency stack, and per-harness test matrix from Voidscape's
standard-library media readers.

**Decision:** If production work is later authorized, create a dedicated `voidscape-bridge`
repository and publish any extension/native-host packages from there. Keep the CLI envelope,
discovery references, design contracts, and verified harness evidence in `void-scape`. Issue #27 may
run a disposable prototype outside the production tree and commit only its report here.

**Alternatives considered:** Implement inside `void-scape` (rejected because it couples browser and
localhost security advisories to the media CLI). Treat a package registry as the source of truth
(rejected because policy, adapters, threat tests, and issue history need repository ownership). Do
nothing beyond harness-owned integrations (retained as the default if the spike cannot prove a
distinct safe benefit).

**Consequences:** The implementation contract can align schemas without shipping bridge code. Any
production issue needs explicit maintainer authorization, an independent security review, and
separate Codex/ChatGPT and Claude verification; one harness never proves universal compatibility.

---

### 2026-08-29 — Keep the shell CLI canonical; park a production MCP host

**Context:** Issue #26 evaluated a thin MCP wrapper for the existing reader envelope. The official
Python MCP SDK is the closest language/runtime fit, but its required dependency and package surface
conflicts with Voidscape's copied, standard-library-first skill. The current shell commands already
provide stable manifest/probe/estimate/run discovery and structured results, while consent display
and MCP behavior still require per-harness verification.

**Decision:** Do not ship an MCP server in `void-scape`. Keep the shell CLI canonical and mark the
production MCP host `parked`. If explicit revisit gates are later met, use the official Python SDK
over local stdio in an optional sibling `voidscape-mcp` repository/package; do not hand-roll the MCP
wire protocol or expose HTTP/browser tools.

**Alternatives considered:** Add the Python SDK here (rejected due dependency, packaging, upgrade,
and vulnerability ownership). Use the TypeScript SDK (rejected because it adds Node/npm and a second
implementation language). Hand-write a stdlib MCP subset (rejected because recent lifecycle changes
make protocol drift and error handling a material risk).

**Consequences:** Issue #26 closes with a no-go report and no server code. Future evidence must show
two host workflows that shell invocation cannot satisfy, preserve separate estimate/run approvals,
and pass a new security/distribution review before an implementation issue is opened.
