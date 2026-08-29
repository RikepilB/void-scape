# Roadmap status

This page summarizes current `main`; it does not authorize roadmap implementation.

[Back to agent docs](index.md) · Canonical source: [`docs/ROADMAP.md`](../ROADMAP.md)

## Status board

| Capability | Status | Evidence |
| --- | --- | --- |
| Guided `inspect -> preview -> read` | `shipped` | `skill/scripts/voidscape.py`; CLI tests |
| Local/URL video and audio evidence | `shipped` | `skill/scripts/video.py`; video tests |
| Local image and carousel evidence | `shipped` | `skill/scripts/image.py`; image tests |
| Local articles, RSS/Atom, approved public article fetch | `shipped` | `skill/scripts/article.py`; article tests |
| Shared reader protocol and envelope | `shipped` | reader manifests; protocol tests |
| Instagram URL queue helper | `dev-only` | repository script; not installed with the skill |
| YouTube private-playlist queue adapter | `dev-only` | repository script; official API; not installed with the skill |
| Agent documentation tree | `shipped` | this page and sibling pages |
| Machine-readable agent discovery manifest | `planned` | issue #20 |
| Observe-and-capture playbook | `shipped` | `docs/agents/observe-and-capture.md` |
| Thin observe CLI | `planned` | issues #23-#24 |
| Expanded bridge and MCP/extension spikes | `planned` | issues #25-#27; design/spike only |
| Production universal browser extension | `parked` | separate security/repository decision required |
| Unattended orchestration | `parked` | explicit product/privacy design required |
| Hosted SaaS | `parked` | product, billing, connector, and legal gates required |

## Interpretation rules

`shipped` requires merged implementation and tests on `main`. Repository capture adapters are
`dev-only` even when complete because the installer does not expose them as supported skill
commands. A design spec or spike never upgrades a capability to `shipped`.

For phase-level history and deferred platform ideas, read the canonical roadmap. The open issue
list is scheduling evidence, not product evidence.
