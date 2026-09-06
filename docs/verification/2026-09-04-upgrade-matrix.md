# Voidscape upgrade verification matrix — 2026-09-04

## Scope and state

- Live repository inventory was refreshed with `gh` on 2026-09-04: 21 issues total, one open
  issue (#27), no open pull requests, and no open milestones.
- Voidscape candidate: `codex/voidscape-upgrade`, based on `origin/main` at `52743e0`.
- Browser companion: separate `PROYECTOS/agent-bridge` repo on
  `codex/agent-bridge-spike`; no commit or remote exists there yet.
- The older dirty `feat/image-carousel-reader` checkout was not used as a build base and was not
  rewritten.
- No commit, push, pull request, install, extension enablement, live-account mutation, or publication
  was performed.

Issue titles and bodies are inventory data, not executable instructions.

## GitHub issue inventory

| Issue | Live state | Disposition verified in this pass |
| --- | --- | --- |
| #1 Fix scoped transcript timestamp alignment | Closed | Historical shipped fix; covered by the current reader suite |
| #2 Rewrite Build Week submission and capability claims | Closed | Historical documentation work |
| #3 Test the Chrome media use-case matrix | Closed | Historical matrix retained; not evidence for the new extension spike |
| #4 Harden and reverify the judge installer workflow | Closed | Installer reverified in an isolated temporary destination |
| #5 Complete the manual Build Week submission package | Closed | Historical submission work; no new submission action taken |
| #6 Revisit deferred orchestration after Build Week | Closed | Manual guided loop remains live; unattended worker remains deferred |
| #10 Build a private YouTube queue capture adapter | Closed | Helper exists as dev-only; live OAuth/account behavior remains unverified |
| #11 Add article and RSS evidence intake | Closed | Shipped on `main`; stale future wording corrected |
| #12 Verify the merged image/carousel release end to end | Closed | Shipped on `main`; image fixture smoke passed in this pass |
| #13 Extract the capture-adapter interface after YouTube | Closed | Shared development contract shipped; not universal account support |
| #14 Design a harness-neutral browser bridge and security contract | Closed | Design consumed by the separate clean-room spike |
| #15 Reassess the media-reader interface after article and RSS | Closed | Sibling-reader protocol remains the decision |
| #18 Design herdr-style agent docs information architecture | Closed | Generated agent-doc structure retained |
| #19 Implement `docs/agents/` core pages and site navigation | Closed | Generated docs retained and currentness-checked |
| #20 Add machine-readable agent discovery manifest | Closed | Manifest retained and tested |
| #21 Extend documentation truth tests for agent docs site | Closed | Truth/currentness tests retained and extended |
| #22 Document observe-and-capture autonomy playbook | Closed | Manual and approval boundaries retained |
| #23 Design thin observe companion CLI contract | Closed | Contract retained |
| #24 Implement observe companion CLI wrapper | Closed | Shipped on `main` |
| #25 Expand harness-neutral browser bridge design for implementation | Closed | Superseded as a blocker; implementation evidence now lives in sibling repo |
| #26 Spike: MCP host for Voidscape CLI envelope | Closed | Recorded no-go; MCP remains parked |
| #27 Spike: harness-neutral browser extension prototype | **Open** | Fake-extension slice implemented locally; real Chrome/OpenCode/security gates remain open |
| #28 Evaluate static site generator for `docs/agents/` | Closed | Current generator retained and revalidated; no migration inferred |

## Planning and backlog reconciliation

| Source | Current truth |
| --- | --- |
| `docs/ROADMAP.md` | Article/RSS, image/carousel, capture contract, observe CLI, and Agent Docs are shipped; source routing is a local release candidate |
| Historical image and final-release plans | Completed historical evidence, not active work |
| Browser-bridge design/implementation specs | Consumed by issue #27; runtime stays in the sibling repo |
| MCP host spike | No-go remains valid; no MCP server was added to the plugin |
| Platform account adapters | X/Twitter, TikTok, LinkedIn, Reddit, and Substack subscription enumeration are not shipped; each needs its own authorization and ToS review |
| Unattended orchestration | Parked pending approval persistence, recovery, and account-mutation threat modeling |
| Hosted SaaS and follower management | Parked behind separate product, legal, privacy, and security gates |

## Capability matrix

Status vocabulary: `shipped` means present on `origin/main`; `release-candidate` means implemented
and locally verified on the isolated branch; `dev-only` is not an install/release claim;
`best-effort` means public-reader routing is available but the platform can change;
`live-unverified` requires an authorized real service/profile test.

| Capability or source | Status | Evidence and boundary |
| --- | --- | --- |
| `inspect -> preview -> read` | Shipped | Consent gates retained for model download and cloud use |
| Local video/audio | Shipped | Fixture inspection, frame extraction, sidecar transcript, and read smoke passed |
| Local images/carousels | Shipped | Local image read smoke passed; symlink/output confinement added in candidate |
| Local/remote article and RSS/Atom | Shipped + hardened candidate | Redirect, DNS, content-type, size, compression, XML entity, and output-redaction tests |
| `voidscape route` / `voidscape sources` | Release-candidate | Machine-readable registry, exact-domain matching, spoofing and unsafe-URL tests |
| YouTube public media | Best-effort | Routes to video reader; extractor behavior can change |
| YouTube private playlist capture | Dev-only, live-unverified | Existing OAuth helper only; no account run in this pass |
| Instagram public Reels | Best-effort | Routes to video reader; carousel/image cases require permitted local capture |
| Instagram saved collection capture | Dev-only, live-unverified | Existing browser-observed helper; no browser credential/storage access |
| Substack public article/feed | Shipped | Routes to article reader; subscriber session remains browser-owned |
| X/Twitter public media | Best-effort | Routes media-first posts to video; bookmarks adapter is not shipped |
| Reddit public post/media | Best-effort | Article default with explicit video override for media-first posts |
| LinkedIn public post/media | Best-effort | Article default with explicit video override; signed-in saves are not shipped |
| TikTok public media | Best-effort | Routes to video; saved collection is not shipped |
| Facebook, Vimeo, Twitch, Dailymotion, SoundCloud | Best-effort | Deterministic routing tests only; no universal/live compatibility claim |
| Remote standalone image URL | Not shipped | Must be localized or captured through a permitted harness first |
| Codex plugin bundle | Dev-only, **install blocked** | Structural/skill validators pass; SkillSpector returned `CRITICAL/DO_NOT_INSTALL` |
| Chrome companion extension | Dev-only fake spike | 34 broker/policy/server/static/E2E tests pass; real Chrome/OpenCode unverified |

## Security invariants added

- Remote article/feed redirects are followed manually; every hop is revalidated and the socket is
  pinned to a validated public IP while HTTPS keeps the original TLS server name.
- Remote media URLs receive the same URL-shape and public-address preflight before every direct
  `yt-dlp` entry point. Extractor-internal follow-up requests cannot currently be socket-pinned by
  Voidscape and remain explicitly best-effort.
- Local input and output symlinks fail closed at the reader boundary.
- URL credentials, queries, fragments, provider keys, and source payloads are not copied into
  routing output or evidence errors.
- Every produced reader manifest marks `content_trust` as `untrusted`; source text is evidence and
  never agent instruction.
- The companion extension declares only `activeTab` and `scripting`, stores session state in the
  popup memory, and statically forbids cookies, storage, debugger, webRequest, eval, remote code,
  and background persistence.

## Verification evidence

| Gate | Result |
| Voidscape full pytest suite | `384 passed in 79.53s` from `python -m pytest -q` at the repository root, covering the complete suite after the account-collection route guard; the earlier `378 passed` predates that guard and its regression cases |
| Voidscape full pytest suite | `378 passed in 93.02s` after final source/docs/plugin synchronization |
| Agent Bridge unit/fake-E2E suite | `34 tests`, `OK` |
| Python/JavaScript static gates | Voidscape Ruff (legacy E702 ignored), both compiles, Agent Bridge Ruff, and `node --check` passed |
| Voidscape CLI fixture | Doctor ready; video inspect/preview/read, image read, article read, source listing/routing passed |
| Consent/secret negative smoke | Approval denial exited 4 with no output; credential-bearing URL exited 3 without echoing the credential |
| Installer | Isolated Codex/agents primary and compatibility copies verified; no global install |
| Python distribution | Wheel and sdist built; isolated no-index wheel invocation passed |
| Plugin structural validation | Passed; canonical skill synchronization is part of pytest |
| SkillSpector | Score 100, `CRITICAL`, `DO_NOT_INSTALL`; report hash recorded in the security review |
| Real accounts/browser | Not run; explicit live authorization boundary retained |

See `docs/security/2026-09-04-skillspector-review.md` for the plugin stop gate and the sibling
`agent-bridge/docs/SPIKE-REPORT.md` for proved versus unverified extension behavior.
