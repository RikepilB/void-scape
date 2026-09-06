# read-video → Universal Save-and-Read Pipeline — Long-Term Roadmap

**Status: planning only.** No implementation authorized by this document. Each milestone below
still needs its own `brainstorming → writing-plans → subagent-driven-development` cycle when work
actually starts on it — same process used for every thread shipped so far in this repo. This doc
exists so the vision isn't lost, not as a green light to start building.

## Vision

Turn `read-video` from a personal Instagram-reel tool into an open-source, multi-platform,
multi-media "save something anywhere → get it read and organized" pipeline — usable by
developers, by AI agents, and by non-technical people, not just by one person's own workflow.

## Guiding principles (carried over from what already exists here)

- **Cost-gate before spend, always** — every new capture-adapter or media-reader inherits
  `SKILL.md`'s existing philosophy: estimate first, ask before any paid/cloud spend.
- **Local-first / privacy-first** — never send captured content to any cloud service without an
  explicit gate the user approves.
- **Harness-neutral where feasible** — reuse Thread C's multi-harness packaging pattern
  (`SKILL.md` + `scripts/install-skill.*`) so new pieces install the same way on Codex and
  compatible runtimes.
- **Small, independently spec'd modules** — one platform or one media type per cycle, never a
  big-bang rewrite. This is the same discipline that kept Threads A/C/D/E reviewable.
- **Compose with specialist tools** — accept durable sidecars and exported evidence instead of
  rebuilding mature transcription, editing, translation, or live-dictation products. Voidscape's
  responsibility is the governed, multimodal handoff to an agent.
- **Legal/ToS risk is a first-class constraint** — each platform's automation gets its own
  terms-of-service and rate-limit review before it ships past "just for me," and especially
  before any hosted/SaaS use.

## The three audience tracks

This is why it's not one project — three genuinely different deliverables, built on the same
core:

1. **Technical people** — the open-source repo itself: code, docs, self-serve.
2. **AI agents** — the pipeline packaged so an *agent*, not a human, can discover and drive it
   (skill manifests, MCP-style tool surfaces, machine-readable guides).
3. **Non-technical people** — no code at all: demo videos, one-line installers, eventually a
   hosted website/SaaS product.

## Phase 0 — Foundation: generalize the two axes this repo currently hard-codes

The project began hard-wired to "Instagram" (capture) and "video" (read). Both axes now have
concrete, tested contracts:

- **Capture axis** — bookmark / saved-collection / folder → queue file. Today:
  `capture_adapter.py` shares queue/dedup/process semantics across the dev-only Instagram and
  YouTube helpers. Platform discovery/auth/mutation stays adapter-specific.
- **Read axis** — media to ordered evidence. `video.py` handles video and audio URLs/files.
  `image.py` handles local images and carousels. `article.py` handles local HTML/Markdown and
  RSS/Atom plus non-video article URLs. The guided CLI dispatches between these focused readers.

**Milestone 0.1 — Capture-adapter interface (closed 2026-08-29).** The second concrete adapter
(YouTube) shipped first, then the shared queue, dedup, preview, durable-write, and partial-failure
contract was extracted into `scripts/capture_adapter.py`. Instagram and YouTube remain dev-only;
the interface is shipped development infrastructure, not proof of live account compatibility.

**Milestone 0.2 — Media-reader interface (closed 2026-08-28, issue #15).** Compared
`video.py`, `image.py`, and `article.py` after article/RSS intake shipped. **Decision: document a
small shared protocol (`manifest` / `probe` / `estimate` / `run`, standard exit codes, optional
`{ok,data,error,meta}` envelope, `inspect → preview → read` via `voidscape.py`); do not extract a
generic implementation layer.** Readers stay sibling modules; shared envelope/pricing/error helpers
remain imported from `video.py`. See
`docs/superpowers/specs/2026-08-28-media-reader-interface-reassessment.md`. Revisit a shared
implementation only if a fourth reader duplicates substantial CLI boilerplate without hiding real
behavioral differences.

## Phase 1 — Media-type expansion (the "read" side)

- **1.1 Local images and carousels** — shipped in PR #9 (merged 2026-08-28).
- **1.2 Audio-only reader — shipped.** Podcasts and voice memos use the existing video/audio reader
  with `--tier audio`. X Spaces and LinkedIn audio still need platform acquisition evidence.
- **1.3 Blog / post / text reader — shipped 2026-08-28.** `article.py` reads local HTML/Markdown,
  RSS/Atom, and approved public article/feed URLs. Subscriber/account capture remains separate.

## Phase 2 — Platform expansion (the "capture" side)

One milestone per platform, each its own spec/plan/implementation cycle, each gated on: does the
platform have a bookmark/saved-collection concept; what does its ToS say about automation; is
there a Codex Chrome control-drivable UI or a real API alternative.

- **2.1 X (Twitter) bookmarks — not started**
- **2.2 TikTok favorites/saved — not started**
- **2.3 LinkedIn saved posts — not started**
- **2.4 Reddit saved posts — not started**
- **2.5 Substack saved/subscribed posts — partial.** Public article/RSS reading is shipped; account
  subscription capture is not. Prefer public feeds over browser automation where possible;
  Substack has no bookmark-grid UI to drive the way IG/TikTok do.
- **2.6 YouTube private-playlist capture — dev-only implementation complete, live OAuth unverified
  (sharpened 2026-07-09, corrected 2026-07-17;
  see `docs/decisions.md`).** Read axis already works (`video.py`/`yt-dlp` take a YouTube URL
  directly) - this milestone is capture only. Official **YouTube Data API v3** (OAuth, not browser
  automation), source = a user-owned private queue playlist such as `Read Video Queue` because
  current Data API docs report Watch Later playlist items as inaccessible; captured videos are
  removed from that queue playlist as the "captured" marker (mirrors IG's unsave pattern), with
  content-keyed dedup against the vault on top (unchanged from `/ig-pipeline`). Ships as a second
  one-off adapter. The shared capture contract was extracted only after this second adapter existed.
- **2.7 Facebook** — raised 2026-07-09, not yet scoped. Facebook's saved-items API is limited/
  largely deprecated and its automation ToS is stricter than IG/YouTube — needs its own
  feasibility+ToS pass before it can even get a milestone number that means anything.

## Phase 3 — Technical-audience packaging

**Status: substantially shipped.** The Agent Docs tree, reader/capture extension guides, static
site, no-clone CLI distribution, and contributor docs now describe multiple readers and two
capture adapters. Continue updating them from the capability registry rather than prose memory.

- **3.1** Generalize "how to use" docs (SKILL.md/README/CONTRIBUTING already exist in miniature
  for read-video alone) to cover N platforms × M media types.
- **3.2** Write the "how to build your own adapter/reader" meta-guide — walks a contributor
  through Phase 0's interfaces so they can add platform #5 or media-type #4 without reading this
  whole roadmap.
- **3.3** Public-launch documentation polish — revisit once the Phase 0 interfaces have actually
  stabilized; don't announce a public API surface that's about to be redesigned.

## Phase 4 — AI-agent-consumable packaging

Can start any time after Phase 0 — doesn't block on Phase 1/2/3.

- **4.1 — in progress.** The primary self-contained skill and a local Codex plugin bundle package
  all readers together. The bundle validates structurally but remains dev-only because its
  SkillSpector static scan is `CRITICAL/DO_NOT_INSTALL`; no installation or publication is approved.
  Split adapter skills only after their account flows are verified.
- **4.2 — shipped / expanding.** Agent-facing discovery docs and `docs/agents/manifest.json` exist;
  `voidscape sources --json` adds runtime source capability discovery without relying on prose
  memory or claiming unverified account capture.
- **4.3 — parked by completed no-go spike.** The shell CLI remains canonical. Revisit an optional
  sibling MCP package only after two named harness workflows prove shell invocation insufficient.

## Phase 5 — Non-technical distribution

- **5.1** Demo videos per platform/media-type combo (screen recordings of the full
  capture→read→note flow) — a genuinely good use of read-video on itself.
- **5.2** One-line installers / packaged downloads for non-developers (no git clone, no Python
  setup) — needs its own design pass (binary bundling? Docker? hosted installer script?).
- **5.3** A plain marketing/docs website hosting the demo videos, guides, and downloads from
  5.1/5.2 — static site, not the SaaS product yet.

## Phase 6 — Hosted SaaS ("as a service")

The biggest, riskiest, most separate piece of this whole roadmap — likely its own product/repo,
not a feature bolted onto this one.

- **6.1** Product design pass: what "as a service" concretely means — connect-your-account and
  auto-process saved items, a paste-a-link one-off tool, or both.
- **6.2** Auth, multi-tenancy, billing — replace the current user-exported cookie bridge with
  provider connections that show requested scopes, ask permission, store credentials safely, and
  support revocation. None of this exists today; it is genuinely new infrastructure, not a
  generalization of the CLI.
- **6.3** LLM SDK integration layer (OpenAI SDK or a provider-neutral adapter) — replaces this
  project's own agent-token cost *estimate* with real per-user billing/usage metering.
- **6.4** **Legal review — a hard gate before any public launch.** Automating captures from other
  people's accounts at SaaS scale is a materially different ToS/rate-limit/abuse-risk situation
  than one person's personal tool (today's scope). This alone could be a go/no-go for the entire
  SaaS track, independent of whether it's technically buildable.

## Suggested sequencing (a sane default, not a commitment)

1. **Phase 0 first, except Milestone 0.1** — refined 2026-07-09: the capture-adapter interface
   (0.1) is extracted *after* a second real adapter (YouTube, Phase 2.5) exists to compare against
   Instagram's, not designed upfront from one example. Milestone 0.2 (media-reader protocol) closed
   2026-08-28 — see the milestone entry above.
2. **Phase 1 + Phase 2 in parallel**, one milestone at a time — whichever platform or media type
   you personally want next, proving the Phase 0 interfaces actually generalize.
3. **Phase 3** once ≥2 platforms and ≥2 media types exist, so the docs reflect a real pattern.
4. **Phase 4** any time after Phase 0 — independent of Phase 1-3's progress.
5. **Phase 5** after Phase 3 — needs stable docs to build videos/guides from.
6. **Phase 6 last**, and only after its own dedicated product + legal design pass — a different
   kind of project, not a natural extension of the CLI.

## Parked idea — Instagram follower-management assistant

**Not authorized for implementation. Next-endeavors only, raised 2026-07-09.** Vision: extend
read-video into a social-media assistant that helps manage who follows/doesn't follow back, tracks
interaction frequency per follower, and offers commands to unfollow, message, follow-back, block,
or restrict based on that data.

- **Reference repos (learn-from-only, do not copy code or transcribe their implementation —
  clean-room this from the feature list above, not from reading their source):**
  - https://github.com/cocohernandez/code-with-coco/tree/main/ig-unfollows
  - https://github.com/haidityara/tools-ig
  - https://github.com/GiovanniCasini/IG_unfollow
- **Gate:** this is exactly the class of feature Phase 6.4 already flags — mass follow/unfollow/
  block automation risks Instagram ToS violation and account suspension. Same legal-review gate
  applies before this starts, regardless of which phase it's filed under.

## Active spike — harness-neutral browser extension (issue #27)

**A bounded disposable spike is now authorized in the separate sibling `PROYECTOS/agent-bridge`;
production implementation remains unauthorized.** The existing CLI
manifest and `{ok,data,error,meta}` envelope are the portable core. A universal browser bridge
still needs a transport, tool schemas, permission and approval handling, host routing, and a
per-platform policy review. It requires a separate design and security review.

- **Why separate:** this is a different shape of project than the CLI-first, one-adapter-at-a-time
  discipline every phase above follows. The ideation and repo decision are complete; the security
  boundary requires its own implementation and release lifecycle outside Voidscape.
  Also every platform named here inherits the same per-platform ToS/legal gate Phase 6.4 and the
  follower-management idea above already flag — none of that changes just because the access
  method is a browser extension instead of an API.
  - **Current slice:** Chrome + OpenCode-shaped fake-harness proof for `snapshot`, `screenshot`, and
    `navigate` is implemented and locally verified in the sibling repo. It uses an authenticated
    loopback broker and popup-only MV3 source with no eval/cookies/storage/credentials. No real
    extension enablement, profile access, or OpenCode integration has been run or approved.

## Orchestration — reassessed 2026-08-28 (was: parked until after the submission)

Parked during Build Week, revisited after the 2026-07-21 submission shipped. The three scoped
options are preserved below; the decision is which one is live now and what the other two are
waiting on. GitHub issue #6 tracked this reassessment and is closed by it.

**The three options, unchanged:**

1. **Full background-job system** — scheduled unattended capture and read, with a queue, failure
   recovery, and durable state.
2. **Thin demo slice** — a single scripted end-to-end run, enough to show the shape without the
   supporting infrastructure.
3. **Zero-code operating workflow** — a documented manual loop over the CLI that already ships,
   adding no code and no new privacy surface.

**Decision: option 3 remains live. Options 1 and 2 are still deferred for product/privacy reasons,
not because the capture-adapter interface is missing.**

- **Live now — the zero-code operating loop.** Operate the existing CLI by hand:
  `inspect → preview → read`, with the cost gate answered per run and the output filed by the
  user. No scheduler, no worker, no new credential handling. This is what "orchestration" means
  in this repo today.
- **Deferred — background job execution (option 1) and the demo slice (option 2).** The capture
  contract, YouTube helper, and article/RSS reader now exist. The remaining blockers are approval
  persistence, cancellation/recovery, live-account evidence, and a threat model for unattended
  account mutation—not missing foundation code.
- **Release candidate — source discovery routing.** `voidscape route` and `voidscape sources`
  classify readers and capability status. Automated destination routing for unattended queues
  remains deferred with the worker itself.
- **Deferred — scheduling/headless worker and its privacy gates.** Windows Task Scheduler or
  equivalent, a headless Codex worker, and failure recovery stay unscoped. The privacy and
  approval gates are the load-bearing part and get designed *with* the adapter interface, not
  bolted onto it afterward — an unattended worker is the first thing in this project that would
  act on the user's accounts without a human in the loop, so it inherits the same explicit-gate
  rule as every cloud spend (see Guiding principles).

## Open questions (flagged, not decided here)

- **Naming/identity** — "read-video" undersells a multi-platform, multi-media,
  capture-and-read pipeline. Rename the whole thing, or keep `read-video` as the "reader" half
  and give capture-adapters their own umbrella name?
- **One repo or many — partially resolved.** The browser bridge is a separate sibling repo.
  Voidscape readers and current capture helpers stay here; a platform adapter splits only when its
  independent credential, release, or policy boundary justifies it.
- **Per-platform ToS ownership** — who actually reads and signs off on each platform's terms
  before an adapter ships, even at "developers self-host it" scope, let alone SaaS scope?
