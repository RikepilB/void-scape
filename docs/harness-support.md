# Multi-Harness Support

Voidscape is the primary installed skill. `read-video` is installed alongside it as a compatibility
facade for existing automations and direct `video.py` calls.

Browser and phone control belong to the agent harness, not the media engine. An approved browser
connection may let a harness select permitted media in signed-in tabs; Voidscape then runs on the
host that can access the selected media and its local files. Browser access does not authenticate
`yt-dlp`.

`read-video`'s engine (`skill/scripts/video.py`) is a Python CLI with no Codex runtime dependency —
anything that can run a shell command and read a file can drive it via
`probe → estimate → [gate] → run`. This doc covers how the *skill* (the `SKILL.md` prompt that
tells an agent how to drive that CLI) gets discovered by different agent harnesses.

## Browser and remote-control capabilities

| Environment | What the harness can do | What Voidscape does | Remote condition |
| --- | --- | --- | --- |
| Codex or Work in ChatGPT desktop with Chrome | Use approved signed-in tabs, click, type, inspect rendered state, and use developer data when enabled | Run the local CLI and read its evidence bundle | ChatGPT Remote can steer the paired host from mobile; the host must remain awake, online, and available |
| Claude Code with Claude in Chrome | Use signed-in sites, test browser flows, and inspect DOM, console, and network state | Run the local Voidscape CLI beside the coding session | Claude Code Remote Control continues the running host session from mobile or web |
| Claude Cowork in the cloud | Continue cloud work across desktop, web, and mobile | Use Voidscape only when the session can reach the media and CLI | Local files or local Chrome still require the connected desktop path |
| Other tool-capable harness | Execute the JSON CLI and read local evidence | Preserve the same gates and citations | Discovery, transport, permissions, approval, and host routing are harness-specific |

Official documentation:

- https://developers.openai.com/codex/chrome-extension
- https://developers.openai.com/codex/remote-connections
- https://developers.openai.com/codex/app/browser
- https://docs.anthropic.com/en/docs/claude-code/chrome
- https://docs.anthropic.com/en/docs/claude-code/remote-control
- https://support.anthropic.com/en/articles/12012173-getting-started-with-claude-for-chrome

## The two install locations

| Harness | Install root | Notes |
|---|---|---|
| Codex | `~/.codex/skills/voidscape/` | Primary skill; `read-video/` compatibility is installed beside it. |
| Shared agent root | `~/.agents/skills/voidscape/` | Second installed copy for compatible runtimes. |
| Other compatible agents | `~/.agents/skills/voidscape/` | Shared copy; discovery depends on that agent's current skill support. |

The installer writes both roots. Codex uses its own copy at `~/.codex/skills/`; the shared
`~/.agents/skills/` copy is available to compatible agent runtimes without claiming that every
runtime has been independently certified.

## Why no per-harness adapter exists

Both installed copies use the same directory format: a `SKILL.md` file with `name` and
`description` YAML frontmatter plus supporting files. The scripts verify that frontmatter and the
bundled CLI after every copy. Codex is the submission's tested agent harness; other runtimes must be
checked against their own current discovery rules.

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
(frontmatter parses, `video.py probe --help` runs), ending with a `SUMMARY` line. Any copy or
verification failure returns a non-zero exit code.

Override the install roots if you keep skills somewhere non-default:

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
integration modes than "another CLI agent reads a SKILL.md" and are not covered by this document
or the installers. They remain post-submission roadmap work.

The CLI is model-neutral. That does not mean one extension automatically supports every model and harness.
Each integration still needs a transport, tool discovery, permissions, approval handling,
and local or remote host routing. A model without tool access cannot run Voidscape directly.
