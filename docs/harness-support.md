# Multi-Harness Support

Voidscape is the primary installed skill. `read-video` is installed alongside it as a compatibility
facade for existing automations and direct `video.py` calls.

`read-video`'s engine (`skill/scripts/video.py`) is a plain stdlib Python CLI with no Codex
dependency — anything that can run a shell command and read a file can drive it via
`probe → estimate → [gate] → run`. This doc covers how the *skill* (the `SKILL.md` prompt that
tells an agent how to drive that CLI) gets discovered by different agent harnesses.

## The two install locations

| Harness | Install root | Notes |
|---|---|---|
| Codex | `~/.codex/skills/voidscape/` | Primary skill; `read-video/` compatibility is installed beside it. |
| Codex | `~/.agents/skills/voidscape/` | Primary skill; shared cross-runtime directory. |
| Gemini CLI | `~/.agents/skills/voidscape/` | Same shared directory as Codex/Copilot CLI. |
| Copilot CLI | `~/.agents/skills/voidscape/` | Same shared directory as Codex/Gemini CLI. |

Codex, Gemini CLI, and Copilot CLI all read **the same** `~/.agents/skills/` directory — installing
there once covers all three. Codex needs its own separate copy at `~/.codex/skills/`.

## Why no per-harness adapter exists

All four harnesses use the identical skill format: a subdirectory containing a `SKILL.md` file with
`name` and `description` YAML frontmatter, plus supporting files. There's no prompt-syntax or
schema difference to translate between them — `read-video`'s `skill/` directory is valid, as-is,
at both install roots. The only harness-specific work was removing Codex-specific wording
from `SKILL.md`'s prose (e.g. naming Codex's `Read` tool specifically) so the same file reads
naturally regardless of which agent is following it.

## Installing

From the repo root:

```powershell
# Windows / PowerShell (primary)
.\scripts\install-skill.ps1
```

```bash
# macOS / Linux / Git Bash (parity)
bash scripts/install-skill.sh
```

Both scripts install canonical `voidscape` and legacy `read-video` compatibility skills at both
roots. They print a per-target `RESULT` line for each copy and two verification checks
(frontmatter parses, `video.py probe --help` runs), ending with a
`SUMMARY` line. Exit code is non-zero only if **every** target's copy failed — a machine with only
Codex installed still succeeds overall (the `~/.agents/skills/` copy just sits there ready
for whichever of Codex/Gemini CLI/Copilot CLI gets installed later).

Override the install roots (the PS1 flags below are exercised by the test suite; the Bash env vars
are parity-only and manually verified). Use either if you keep skills somewhere non-default:

```powershell
.\scripts\install-skill.ps1 -CodexSkillsRoot "D:\custom\codex\skills" -AgentsSkillsRoot "D:\custom\agents\skills"
```

```bash
CODEX_SKILLS_ROOT=/custom/codex/skills AGENTS_SKILLS_ROOT=/custom/agents/skills bash scripts/install-skill.sh
```

## Re-syncing after edits

There is no live-sync watcher. After editing anything under `skill/` or `compat/`, re-run the
install script to push the change to both installed copies. Local config files (`workspace.json`, `.env`,
`load-env.ps1`) at either destination are never touched by the install — the repo's `skill/`
directory never contains those filenames (they're gitignored, generated at the destination only),
so a plain overlay copy leaves them alone automatically.

## Out of scope

Agent SDK / custom-bot integration and non-interactive automation (cron, n8n, etc.) are different
integration modes than "another CLI agent reads a SKILL.md" and aren't covered by this doc or the
install scripts — see `docs/superpowers/specs/2026-07-02-agent-harness-packaging-design.md` for the
full scope decision.
