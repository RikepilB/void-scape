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
