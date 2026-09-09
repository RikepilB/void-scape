# Instagram triage project skill

The [canonical skill](../.agents/skills/instagram-triage/SKILL.md) coordinates
user-selected Instagram items using repository helpers. It requires this checkout;
the standalone media-reader installer does not install it.

- Discovery workers return scoped URLs and never change accounts or queues.
- `instagram_capture_helper.py inspect` validates a URL without writing.
- `preview <url> <queue-file>` reports append/duplicate without creating a queue.
- The controller reads approved items through inspect, preview and read, then
  publishes evidence-grounded drafts through [triage_store](triage-store.md).
- A verified receipt does not authorize an unsave. Account changes require the
  exact current user confirmation and an available approved browser harness.

Example: ask for a dry-run of three supplied Reel URLs and a specified notes root.
The skill reports canonical URLs and verified existing work without reading media
or creating files. A subsequent request to read and file those items supplies the
local scope; model-download and cloud gates still apply to each item.

## Maintain the harness files

Edit `.agents/skills/instagram-triage` first. Its `roles.json` points at the capture
and analysis role references. Generate only the project files with:

```powershell
python scripts/sync_instagram_roles.py --write
python scripts/sync_instagram_roles.py
python -m pytest tests/test_instagram_skill_packaging.py tests/test_instagram_capture_helper.py tests/test_triage_store.py -q -p no:cacheprovider
```

Without `--write`, synchronization only reports drift and exits nonzero. With
`--write`, it updates the named Claude skill mirror and Claude/Agents/Codex role
files. Review the Git diff; it does not install runtimes or modify global settings.
The Codex entry point is the canonical `.agents/skills` directory, avoiding a
second competing skill under `.codex/skills`.

## Verification limits

Helper execution and generated-file equality are deterministic tests. They are
not a behavioral evaluation of an AI agent, signed-in browser discovery, or proof
of equivalent operation in Codex, Claude and OpenCode. Those runtime evaluations
and separately approved live mutation proof remain
required before declaring the source workflow complete under issue #54.

Keep synthetic fixtures distinct from fetched source evidence. Never present a
fixture note as a real Instagram analysis or use it to authorize an account change.

The [evaluation workspace](https://github.com/RikepilB/void-scape/tree/main/evals/instagram-triage) contains scoped
cases and separate grading criteria. The first real local CLI exercise exposed
and corrected a success-schema mismatch: guided `voidscape --json` commands return
flat success objects, while `triage_store` returns an `ok`/`data` envelope. See
[observed results and remaining limits](https://github.com/RikepilB/void-scape/blob/main/evals/instagram-triage/RESULTS.md).
