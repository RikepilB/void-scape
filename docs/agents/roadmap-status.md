# Roadmap status

This page distinguishes current `main` from the explicitly labeled local upgrade candidates; it
does not authorize install, publication, or roadmap expansion.

[Back to agent docs](index.md) · Canonical source: [`docs/ROADMAP.md`](../ROADMAP.md)

## Status board

| Capability | Status | Evidence |
| --- | --- | --- |
| Guided `inspect -> preview -> read` | `shipped` | `skill/scripts/voidscape.py`; CLI tests |
| Local/URL video and audio evidence | `shipped` | `skill/scripts/video.py`; video tests |
| Local image and carousel evidence | `shipped` | `skill/scripts/image.py`; image tests |
| Local articles, RSS/Atom, approved public article fetch | `shipped` | `skill/scripts/article.py`; article tests |
| Shared reader protocol and envelope | `shipped` | reader manifests; protocol tests |
| Source capability registry and reader override | `release-candidate` | `voidscape route`, `voidscape sources`; source tests |
| Instagram URL queue helper | `dev-only` | repository script; not installed with the skill |
| YouTube private-playlist queue adapter | `dev-only` | repository script; official API; not installed with the skill |
| Agent documentation tree | `shipped` | this page and sibling pages |
| Machine-readable agent discovery manifest | `shipped` | `docs/agents/manifest.json` |
| Observe-and-capture playbook | `shipped` | `docs/agents/observe-and-capture.md` |
| Thin observe CLI | `shipped` | `skill/scripts/observe.py`; issue #24 |
| Browser bridge implementation contract | `dev-only` | design only; issues #14 and #25 |
| MCP host spike / decision | `shipped` | no-go report; issue #26 |
| Production MCP host | `parked` | revisit gates in the #26 spike report |
| Browser extension spike | `dev-only` | sibling `agent-bridge` fake protocol proof; real Chrome/OpenCode unverified |
| Codex plugin bundle | `dev-only` | validates locally; SkillSpector `CRITICAL/DO_NOT_INSTALL` gate remains open |
| Production universal browser extension | `parked` | separate security/repository decision required |
| Unattended orchestration | `parked` | explicit product/privacy design required |
| Hosted SaaS | `parked` | product, billing, connector, and legal gates required |

## Interpretation rules

`shipped` requires merged implementation and tests on `main`. `release-candidate` means the local
upgrade is implemented and verified but is not merged, installed, or published. Repository capture
adapters and the fake browser spike are `dev-only` because no supported installer exposes them.
A design spec or fake spike never upgrades a capability to `shipped`.

For phase-level history and deferred platform ideas, read the canonical roadmap. The open issue
list is scheduling evidence, not product evidence.

## Incoming — what exploration could unlock

The long-term direction is one idea: every piece of media you already keep becomes inspectable,
citable evidence through the same gates. None of the directions below is shipped, installed, or
promised; each is listed with what it would take to become real.

| Direction | What it would give you | Standing gates |
| --- | --- | --- |
| X bookmarks, TikTok favorites, LinkedIn saves | one evidence library across every platform you save to | per-platform permission review; signed-in capture is never implied by public reading |
| Newsletter collections | inbox reading with sender and issue order preserved | delivery-platform review; no mailbox credentials, ever |
| Browser bridge (live pages) | read what a page shows at read time, with the page state recorded | site-by-site approval; no credentials, cookies, or storage access |
| Screenshot CLI/MCP integrations (Iris-style) | turn a visible screen region into citable frames | capture-scope consent; same inspect -> preview -> read discipline |
| Agent plugins and multi-model reading | choose per-task models for transcription and vision | model-download and cloud approvals stay per-run, never global settings |
| Hosted edition | Voidscape without local setup | product, billing, connector, and legal gates; local-first stays the default |

Two boundaries hold across every row. First, Voidscape is a reader: follower audits, creator
performance dashboards, and job-search tooling are separate companion projects, and permission to
read never implies following, unfollowing, messaging, or publishing. Second, security review gates
apply before any exploration becomes an installed capability — a working prototype is not a release.
