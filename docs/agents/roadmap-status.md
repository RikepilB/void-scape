# Roadmap status

Updated 2026-09-10. This page distinguishes supported reading from repository workflows still
under acceptance and future plans. Milestones are sequencing, not delivery-date promises;
they do not authorize installation or account actions.

[Back to agent docs](index.md) · Canonical source: [`docs/ROADMAP.md`](../ROADMAP.md)

## Work sequence

| Stage | Focus | Tracker |
| --- | --- | --- |
| Completed foundations | Readers, CLI, docs, hardening and scoped design/spike outcomes | [M0](https://github.com/RikepilB/void-scape/milestone/1) |
| Current verification | Implemented source skills, independent harness acceptance, browser QA and release checks | [M1](https://github.com/RikepilB/void-scape/milestone/2), #42 / #54 / #57 / #91 |
| Next | Inbox scheduling, LinkedIn triage, bridge pairing/permissions | [M2](https://github.com/RikepilB/void-scape/milestone/3), #55 / #56 / #58 |
| Later / exploration | Visual jobs, capture benchmarks, more saved sources and separate companions | [M3](https://github.com/RikepilB/void-scape/milestone/4), #44 / #93–#96 |

Closing a design or spike issue only completes that scope. It never ships a production integration.

## Capability evidence

| Capability | Status | Evidence |
| --- | --- | --- |
| Guided `inspect -> preview -> read` | `shipped` | `skill/scripts/voidscape.py`; CLI tests |
| Local/URL video and audio evidence | `shipped` | `skill/scripts/video.py`; video tests |
| Local image and carousel evidence | `shipped` | `skill/scripts/image.py`; image tests |
| Local articles, RSS/Atom, approved public article fetch | `shipped` | `skill/scripts/article.py`; article tests |
| Optional screenshot provenance | `shipped` | [Image sidecar contract](readers/images.md), merged PR #107; local hash/geometry verification, not browser capture or producer authentication |
| Public feed capture and notes | `dev-only` | [RSS intake helper](../rss-intake.md), selected article/enclosure reads (#109–#111), real podcast QA and [one public access-wall skip](../qa/2026-09-10-rss-access-wall.md); project skill and verified publication implemented; broader provider and independent harness acceptance pending |
| Local chat export (WhatsApp-style) evidence | `shipped` | `skill/scripts/chat.py`; chat reader tests |
| Connectors contract page | `shipped` | this tree: `connectors.md` |
| Harness skill kit (copy-and-adapt templates) | `shipped` | `harness/skills/`; template tests |
| Shared reader protocol and envelope | `shipped` | reader manifests; protocol tests |
| Private recovery pointers and Windows UTF-8 output | `shipped` | merged PR #65; recovery and Unicode subprocess tests |
| Bounded article responses and direct loopback health | `shipped` | merged PR #66; network boundary tests |
| Source capability registry and reader override | `shipped` | merged PR #45; supported `voidscape route`, `voidscape sources`; source tests |
| Instagram URL queue helper | `dev-only` | repository script; not installed with the skill |
| Instagram triage and verified notes | `dev-only` | merged project skill/controller and note store (#77–#80); independent behavior and live harness acceptance remain #54 |
| LinkedIn observed-post capture and notes | `dev-only` | [local workflow](../linkedin-capture.md): typed identities, verified notes/index, legacy assessment and project skill with selected resume; independent harness and permitted live acceptance remain #55 |
| Instagram follow-relationship audit (read-only) | `dev-only` | repository script; local exports only; never unfollows |
| YouTube private-playlist queue adapter | `dev-only` | repository script; official API; not installed with the skill |
| Public YouTube capture and notes | `dev-only` | [source workflow](../youtube-ingest.md); real local capture/read/note proof, independent skill/harness acceptance pending |
| Agent documentation tree | `shipped` | this page and sibling pages |
| Machine-readable agent discovery manifest | `shipped` | `docs/agents/manifest.json` |
| Observe-and-capture playbook | `shipped` | `docs/agents/observe-and-capture.md` |
| Thin observe CLI | `shipped` | `skill/scripts/observe.py`; issue #24 |
| Browser bridge production integration | `dev-only` | isolated spike complete; pairing, permission profiles and client acceptance are next in #58, separate agent-bridge repository |
| MCP host spike / decision | `shipped` | no-go report; issue #26 |
| Production MCP host | `parked` | revisit gates in the #26 spike report |
| Browser extension spike | `dev-only` | [spike report](../superpowers/specs/2026-09-08-browser-extension-spike-report.md): isolated Chrome three-command proof; real harnesses and signed-in profiles unverified |
| Codex plugin bundle | `dev-only` | validates locally; SkillSpector `CRITICAL/DO_NOT_INSTALL` gate remains open |
| Production universal browser extension | `parked` | separate security/repository decision required |
| Local recording inbox controller | `dev-only` | [repository helper](../process-inbox.md), project skill and local note author merged (#81–#84); real recording/harness acceptance and scheduler pending in #56 |
| Unattended orchestration | `parked` | general orchestration beyond the bounded local inbox work in issue #56 needs separate product/privacy design |
| Hosted SaaS | `parked` | product, billing, connector, and legal gates required |

## Interpretation rules

`shipped` requires merged implementation, tests on `main` and a supported entry point.
`release-candidate` means an implemented and verified change awaiting merge/release.
Repository source workflows and the browser spike remain `dev-only` while supported distribution
or independent end-to-end acceptance is incomplete. Project-local packaging is not live harness proof.
A design spec or fake spike never upgrades a capability to `shipped`.

Iris scan warnings are not evidence of malware. Richard assesses them as false positives;
the remaining gate is pinned capability/permission review and integration acceptance.
Iris is not installed by this roadmap; its existing STOP remains an adoption status.

For phase-level history and deferred platform ideas, read the canonical roadmap. The open issue
list is scheduling evidence, not product evidence.

## Incoming — what exploration could unlock

The long-term direction is one idea: every piece of media you already keep becomes inspectable,
citable evidence through the same gates. None of the directions below is shipped, installed, or
promised; each is listed with what it would take to become real.

| Direction | What it would give you | Standing gates |
| --- | --- | --- |
| X bookmarks, TikTok favorites, Reddit saves | one evidence library across more platforms you save to | per-platform permission review; signed-in capture is never implied by public reading |
| Newsletter collections | inbox reading with sender and issue order preserved | delivery-platform review; no mailbox credentials, ever |
| Browser bridge (live pages) | read what a page shows at read time, with the page state recorded | site-by-site approval; no credentials, cookies, or storage access |
| Screenshot CLI/MCP integrations (Iris-style) | turn a visible screen region into citable frames | capture-scope consent; same inspect -> preview -> read discipline |
| Agent plugins and multi-model reading | choose per-task models for transcription and vision | model-download and cloud approvals stay per-run, never global settings |
| Hosted edition | Voidscape without local setup | product, billing, connector, and legal gates; local-first stays the default |

Two boundaries hold across every row. First, Voidscape is a reader: follower audits, creator
performance dashboards, and job-search tooling are separate companion projects, and permission to
read never implies following, unfollowing, messaging, or publishing. Second, security review gates
apply before any exploration becomes an installed capability — a working prototype is not a release.
