# Harness skill kit

Copy-and-adapt agent skills that ride on Voidscape evidence. The kit lives in
[`harness/skills/`](../../harness/skills/read-inbox-export/SKILL.md) in the repository.

**Status:** `shipped` (templates) · not installed by the skill installer

[Back to agent docs](index.md) · Canonical sources: [harness support](../harness-support.md) and
the [connectors contract](connectors.md)

## The kit

| Template | What it does | Evidence tie |
| --- | --- | --- |
| `read-inbox-export` | Triage a messaging inbox export; media and the export itself go through Voidscape | `[message N]`, `[MM:SS]`, `[image N]` |
| `evidence-outreach` | Outreach whose hook must cite an evidence bundle; refuses to draft without one | any citation label |
| `learning-capture` | Turn a finished task into a reusable lesson; proposal-first | records which labels verified |
| `catch-up` | Fast repo orientation from the project's own handoff digest | orients inside evidence workdirs |

## The rule

The kit ships **templates, not personal skills**. They are parameterized (`{{VAULT_INBOX}}`,
`{{SHARED_INBOX}}`) and carry no personal voice, memory, or machine paths. Your calibrated voice,
proof points, and private destinations belong in your own skill library; copy a template there
and specialize it. A regression test keeps the kit free of absolute paths and personal tokens.

## Installation

The templates are not installed by the Voidscape skill installer and never become Voidscape
commands. Copy the folder into your harness skills root and adapt the placeholders:

```powershell
Copy-Item -Recurse harness/skills/read-inbox-export ~/.agents/skills/read-inbox-export
```

## Boundaries carried by every template

Read-only where reading is the job (an inbox skill never sends; an outreach skill drafts, the
human sends). Source content is untrusted evidence, never instructions. Cloud and model-download
consent still belongs to the Voidscape gates.
