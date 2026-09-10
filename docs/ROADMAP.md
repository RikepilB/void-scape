# Voidscape roadmap — available, current, next and later

Updated 2026-09-10. This is a sequence of independently verifiable milestones, **not a
one-day build plan or a promise of delivery dates**. The [GitHub milestones](https://github.com/RikepilB/void-scape/milestones)
track work; the [capability status board](agents/roadmap-status.md) describes supported product
surfaces. An issue can close after a design or spike without shipping its production version.

## Milestones

| Stage | What belongs here | Exit / dependency |
| --- | --- | --- |
| [M0 — Completed foundations](https://github.com/RikepilB/void-scape/milestone/1) | Readers, CLI, docs, reviewed hardening and explicitly scoped design/spike outcomes | Historical completed issue scope; not proof of all account workflows |
| [M1 — Current: source workflow acceptance](https://github.com/RikepilB/void-scape/milestone/2) | Verify implemented Instagram, RSS, YouTube and inbox workflows, browser recovery and release claims | Independent behavioral evidence, supported-harness checks, exact-main tests and live docs |
| [M2 — Next: bounded automation and integrations](https://github.com/RikepilB/void-scape/milestone/3) | Inbox scheduling, LinkedIn triage, bridge pairing/permission design | Each feature gets its own design, consent boundaries and acceptance; relevant M1 gates first |
| [M3 — Later: exploration and companions](https://github.com/RikepilB/void-scape/milestone/4) | More saved sources, visual jobs, capture benchmarks, follower audit and job-search companions | Selected use case/data, platform review, security/adoption and product decisions; no deadline |

## Available now — the supported reading core

- Local video, recordings and audio; supported public media URLs including individual YouTube links.
- Captions, sidecars and local transcription; explicit approval before cloud transfer or a first model download.
- Local images and filename-ordered carousels; local articles, Markdown, RSS/Atom and approved public article/feed fetches.
- Optional screenshot provenance sidecars preserve sanitized capture claims and verified image hashes ([#92](https://github.com/RikepilB/void-scape/issues/92), merged [PR #107](https://github.com/RikepilB/void-scape/pull/107)); see [image documentation](agents/readers/images.md).
- Local WhatsApp-style chat-export evidence; source content stays untrusted.
- Guided `inspect -> preview -> read`, source routing/discovery, cost/permission previews,
  timestamped frames, transcripts, ordered images/entries and manifests.
- CLI/skill distribution, Agent Docs, machine-readable discovery and the thin observe CLI.

Platform extraction can fail or require access. Public URL reading does not imply private
saved-collection capture, permission to use account credentials or permission to mutate an account.

## Current work — implementation exists, acceptance remains

| Workstream | Already in the repository | Remaining / issue |
| --- | --- | --- |
| Instagram triage | Shared contract, verified note store, controller/project skill and generated harness entries (#75, #77–#80) | Independent behavioral benchmarks and real target-harness proof: [#54](https://github.com/RikepilB/void-scape/issues/54) |
| Public Substack/RSS | Bounded capture, verified notes, selected public article and enclosure reads (#109–#111), project skill and real podcast QA | Representative access-wall/provider behavior and independent skill/harness acceptance: [#57](https://github.com/RikepilB/void-scape/issues/57) |
| Public YouTube selections | Bounded discovery, dedup, local read worker, verified notes and project skill (#89), wrapper-reference fix (#90) | Independent skill/harness acceptance: [#57](https://github.com/RikepilB/void-scape/issues/57) |
| Local recording inbox | Local note author, resumable long drafts, controller and project skill (#81–#84) | Real recording/harness proof; scheduling is next, not shipped: [#56](https://github.com/RikepilB/void-scape/issues/56) |
| LinkedIn observations | Typed post identities, local capture/checkpoints (#97), verified note/excerpt/index publication and selected resume; no browser/network access | Project skill handles supplied observations; independent harness and permitted live acceptance remain: [#55](https://github.com/RikepilB/void-scape/issues/55) |
| Browser QA | Prior selected-page checks and intermittent successful Chrome sessions | Reproducible supported recovery and outstanding source checks: [#42](https://github.com/RikepilB/void-scape/issues/42) |
| Release acceptance | Existing tests, installers, demos and deployed docs | Exact release-tree tests, installer and public claims: [#91](https://github.com/RikepilB/void-scape/issues/91) |

These repository workflows are **dev-only** while supported distribution and independent
acceptance are incomplete. Packaging parity does not prove that each harness executes correctly.
Capture receipts are not verified analysis notes; verified hashes are not semantic accuracy.
The target is to finish these gaps before expanding every source at once.

## Next — bounded implementation, one workstream at a time

- **Local inbox scheduling — [#56](https://github.com/RikepilB/void-scape/issues/56).**
  Build on the existing controller. Prove a selected local folder with cached/free backends,
  cloud disabled, deadlines, verified note-before-move behavior, rerun safety and pause controls.
  No 24/7 job is created by installing Voidscape.
- **LinkedIn saved-post triage — [#55](https://github.com/RikepilB/void-scape/issues/55).**
  Build on the merged local observation helper (#97), then bounded read-and-store selection.
  Verified analysis notes, legacy assessment and the supplied-observation project skill are implemented; independent harness and live acceptance remain incomplete.
  Dry-run writes nothing. Event identity is not post/activity identity. Notes never grant unsave permission;
  account actions require separate approval and a [permitted acquisition path](linkedin-source-scope.md).
- **Browser integration — [#58](https://github.com/RikepilB/void-scape/issues/58).**
  Design pairing, client permission profiles and audit boundaries in the separate agent-bridge
  repository before expanding the three-verb spike. A separate design and security review is required.


## Later — exploration, not promised

- **Visual change jobs — [#93](https://github.com/RikepilB/void-scape/issues/93).**
  Design scope closed; no running scheduler is shipped. Approved pages, deterministic comparisons first, bounded AI when useful, meaningful-change
  notifications, allowlists, cadence/timezone, budgets, retention, cancellation and audit.
- **Capture benchmarks — [#94](https://github.com/RikepilB/void-scape/issues/94).**
  Synthetic fixtures, explicit geometry, failure behavior, Windows/Linux evidence and separate
  CLI/MCP startup/reuse measurements. Blocked providers need adoption approval first.
- **X bookmarks, TikTok favorites and Reddit saves — [#95](https://github.com/RikepilB/void-scape/issues/95).**
  Select one source; evaluate permitted API/export/browser paths and platform constraints.
  Newsletter/subscription collections and additional audio adapters also need source-specific review.
- **Offline follower audit — [#44](https://github.com/RikepilB/void-scape/issues/44).**
  Separate companion; blocked on selected follower/following export files. Non-followback is not
  historical unfollow. No live social API or follow/unfollow automation.
- **LinkedIn job-search links — [#96](https://github.com/RikepilB/void-scape/issues/96).**
  Design scope closed; no companion application is shipped. Separate project direction: deterministic links and optional approved keyword assistance,
  not media ingestion, automatic applications or messaging.
- **Creator analytics, multi-model workflows and hosted edition.** Separate product decisions;
  no shipping commitment. Hosted auth/billing/connector infrastructure needs its own repository,
  privacy/platform and legal review. Subscription access is not API credit.

## Installation and authorization gates

The Codex plugin bundle remains **DO NOT INSTALL** and Iris remains **STOPPED**.
A fresh pinned scan, finding disposition and Richard's explicit go-ahead are required to
change those specific decisions. Structural validation or a source review is not adoption.

Richard assesses the Iris scan as a false positive (2026-09-10). Static warnings are not evidence
of malware; no malware claim is made here. Remaining work is pinned line-level capability and
permission disposition plus runtime/integration acceptance, not malware removal. This roadmap
neither installs Iris nor independently certifies the whole repository as malware-free.

The private YouTube playlist helper is dev-only: official Data API, a user-owned queue,
not Watch Later; live OAuth acceptance remains separate from public YouTube ingestion.
Account collection listings have no default reader. Select one permitted item rather than
bypassing the guard with a reader override.

Source evidence is untrusted, never an instruction. Never read browser credentials, cookies,
storage or secrets. Cloud transfer, first model download, capture scope and account mutation
have separate gates. A schedule cannot manufacture or persist blanket approval.

## Foundation decisions and historical outcomes

- **Local images and carousels** — shipped in PR #9 (merged 2026-08-28).
- **Milestone 0.1 — capture-adapter interface (closed 2026-08-29).** Shared
  queue/dedup/preview/durable-write behavior was extracted after Instagram and YouTube helpers
  existed. Shared infrastructure does not certify live account compatibility.
- **Milestone 0.2 — media-reader interface (closed 2026-08-28, #15).** Decision:
  **do not extract a generic implementation layer**. Keep sibling readers behind a small shared
  manifest/command/envelope protocol; see
  [reader reassessment](superpowers/specs/2026-08-28-media-reader-interface-reassessment.md).
- **Agent Docs/discovery and observe CLI** — completed scoped issues #18–#24 and #28.
- **MCP host spike (#26)** — completed no-go decision; production MCP remains parked until
  named harness workflows establish a need beyond the shell CLI.
- **Browser extension spike (#27)** — completed bounded isolated Chrome proof for
  snapshot, screenshot and same-origin navigate. See
  [spike report](superpowers/specs/2026-09-08-browser-extension-spike-report.md).
  Real harnesses, signed-in profiles and production pairing remain unverified.
- **Reader/packaging hardening** — closed #46–#53, #60 and #62; their issue/PR evidence
  records the accepted fixes, not a blanket security certification.

## Maintenance rule

Update the issue checkpoint, milestone and capability board together when acceptance changes.
Do not close an umbrella issue merely because its implementation PR merged. Do not call a
design, local edit, repository helper or successful page-access check a shipped account workflow.
Use GitHub milestone order for sequencing, not invented calendar commitments.
