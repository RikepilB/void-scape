# References

These sources inform the agent documentation and autonomy boundary; they are not bundled dependencies.

[Back to agent docs](index.md)

## Canonical Voidscape sources

- [`skill/SKILL.md`](../../skill/SKILL.md) — installed agent behavior and approval workflow.
- [`docs/architecture.md`](../architecture.md) — data flow, pricing, backends, and security posture.
- [`docs/workflow.md`](../workflow.md) — guided decision flow.
- [`docs/harness-support.md`](../harness-support.md) — browser, remote-host, and install boundaries.
- [`docs/ROADMAP.md`](../ROADMAP.md) — planning and parked work.
- [Agent-docs information architecture](../superpowers/specs/2026-08-29-agent-docs-information-architecture.md).
- [Browser-bridge security contract](../superpowers/specs/2026-08-28-harness-neutral-browser-bridge-design.md).

## Official harness documentation

- [Codex Chrome extension](https://developers.openai.com/codex/chrome-extension/)
- [Codex remote connections](https://developers.openai.com/codex/remote-connections/)
- [Codex app browser](https://developers.openai.com/codex/app/browser/)
- [Claude Code with Chrome](https://docs.anthropic.com/en/docs/claude-code/chrome)
- [Claude Code Remote Control](https://docs.anthropic.com/en/docs/claude-code/remote-control)

Vendor documentation supports `vendor-documented` labels only. Voidscape verification requires its
own scoped test evidence.

## Pattern sources

- [Herdr agent docs](https://herdr.dev/docs/agents/) — information-architecture inspiration:
  separate harness support, authority, workflow, explanation, and automation.
- [screenpipe](https://github.com/screenpipe/screenpipe) — optional companion patterns for local
  desktop capture, health/freshness reporting, and authenticated localhost services.
- [automated_browser](https://github.com/deaspo/automated_browser/tree/devel) — learn-from-only
  patterns for structured browser actions and replayable session evidence.

Voidscape does not copy upstream code or adopt screenpipe's always-on recording as its core. It does
not adopt an autonomous browser loop, full-page cloud uploads, raw `eval`, or cookie scraping from
automated_browser. Review each upstream license and current design before any future code reuse.
