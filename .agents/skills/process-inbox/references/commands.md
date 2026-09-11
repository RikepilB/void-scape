# Controller commands

Run from the verified Voidscape checkout. Substitute only the authorized values.

```powershell
python scripts/process_inbox.py --root "C:/Recordings/Inbox" --notes-root "C:/Knowledge" --model gemma3:4b --limit 3 --timeout 600 --min-age 60
```

After scope is authorized, repeat with `--apply`. These example bounds permit
three ten-minute workers plus a ten-minute recovery worker, below a two-hour
interval. They are defaults to adapt to actual recordings, not scheduling proof.
`--min-age 0` is for deliberately selected complete files, not a way to bypass
changing-file safeguards in a watched folder.

The model service must already be cloud-disabled and the named model cached.
Backend `auto` selects local sidecars or installed cached faster-whisper; other
supported selections are `captions`, `faster-whisper` and `whisper-cpp`.

For an optional Windows schedule, first render a no-write plan with fixed existing
roots and local-only settings:

```powershell
python scripts/process_inbox_schedule.py --root "C:/Recordings/Inbox" --notes-root "C:/Knowledge" --model gemma3:4b --limit 3 --timeout 600 --interval-minutes 120 --config "C:/Voidscape/process-inbox-schedule.json"
```

`--write-config` persists the reviewed configuration only. The returned
`schtasks.exe` command is not executed by the helper; task registration is a
separate current user action. A later task uses only the fixed configuration and
writes sanitized counts to its adjacent JSONL log. Do not present a written config,
task definition or empty result as proof of a scheduled execution.

Success: `{"ok":true,"data":{"mode":"apply","processed":1,"skipped":0,"failed":0,"deferred":0,"results":[...]},"error":null}`.
Busy: `data.status` is `busy`, all counts zero, exit 0. A worker can return a
`deferred` result when recording or sidecar modification is too recent.

Root recordings use `03_Media/Transcripts/<sha256>.md`; event subfolders use
`Conference/<first-subfolder>/<sha256>.md`. The helper owns checkpoint validation
and verified moves to `processed/<original-relative-path>`. Never recreate those
transitions with shell renames or direct JSON edits.
