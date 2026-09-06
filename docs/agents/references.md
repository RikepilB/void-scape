# References

These sources inform the agent documentation and autonomy boundary; they are not bundled dependencies.

[Back to agent docs](index.md)

## Canonical Voidscape sources

- [`skill/SKILL.md`](../../skill/SKILL.md) — installed agent behavior and approval workflow.
- [`docs/architecture.md`](../architecture.md) — data flow, pricing, backends, and security posture.
- [`docs/workflow.md`](../workflow.md) — guided decision flow.
- [`docs/source-capabilities.md`](../source-capabilities.md) — platform routing and capture truth.
- [Upgrade verification matrix](../verification/2026-09-04-upgrade-matrix.md) — complete issue,
  backlog, platform, test, and security disposition for the current local candidate.
- [`docs/harness-support.md`](../harness-support.md) — browser, remote-host, and install boundaries.
- [`docs/ROADMAP.md`](../ROADMAP.md) — planning and parked work.
- [SkillSpector static review](../security/2026-09-04-skillspector-review.md) — current plugin
  install stop, manual disposition, and raw-report hash.
- [Agent-docs information architecture](../superpowers/specs/2026-08-29-agent-docs-information-architecture.md).
- [Browser-bridge security contract](../superpowers/specs/2026-08-28-harness-neutral-browser-bridge-design.md).
- [Browser-bridge implementation contract](../superpowers/specs/2026-08-29-browser-bridge-implementation-contract.md).
- [MCP host spike and no-go recommendation](../superpowers/specs/2026-08-29-voidscape-mcp-host-spike.md).

## Official harness documentation

- [Codex Chrome extension](https://developers.openai.com/codex/chrome-extension/)
- [Codex remote connections](https://developers.openai.com/codex/remote-connections/)
- [Codex app browser](https://developers.openai.com/codex/app/browser/)
- [Claude Code with Chrome](https://docs.anthropic.com/en/docs/claude-code/chrome)
- [Claude Code Remote Control](https://docs.anthropic.com/en/docs/claude-code/remote-control)

Vendor documentation supports `vendor-documented` labels only. Voidscape verification requires its
own scoped test evidence.

## Official provider documentation

- [Groq Speech to Text](https://console.groq.com/docs/speech-to-text) — model speed factors, file
  limits, and transcription endpoint behavior.
- [Groq Batch API](https://console.groq.com/docs/batch) — asynchronous audio batch availability,
  cost model, retention, and processing windows.

Provider performance numbers describe provider-side behavior, not a Voidscape end-to-end SLA.

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
