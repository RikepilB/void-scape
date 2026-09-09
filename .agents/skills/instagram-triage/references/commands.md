# Controller commands

Run these from the selected Voidscape checkout. Paths and URLs are data: pass
arguments through structured tools or proper shell quoting, never interpolate
source text into executable shell code.

## Read-only preparation

```powershell
python scripts/instagram_capture_helper.py inspect "<url>"
python scripts/instagram_capture_helper.py preview "<url>" "<queue-file>"
python scripts/triage_store.py lookup "<notes-root>" instagram "instagram:<shortcode>"
```

Capture inspect/preview emit flat JSON with canonical `url`, `shortcode`, and
false mutation flags. Preview also returns duplicate/action. Neither writes a
queue. The separate `process <url> <queue-file>` command appends a verified URL;
use it only when queue capture itself was requested. Queue readiness is not a note.

## Evidence

```powershell
python -m skill.scripts.voidscape inspect "<input>" --json
python -m skill.scripts.voidscape preview "<input>" --tier both --backend faster-whisper --json
python -m skill.scripts.voidscape read "<input>" --tier both --backend faster-whisper --workdir "<fresh-evidence-dir>" --json
```

These examples use local transcription. Match preview/read options to the chosen
backend and requested scope. A supplied local caption sidecar may use `captions`
when appropriate; inspect and preview it first. Never run read after a failed or
malformed preview or with missing permission flags. These guided commands return
flat success objects, not `ok`/`data` envelopes. Require exit zero and a JSON object
with the command's expected fields: source inspection, explicit preview gate flags,
and read `status: complete` plus actual artifact paths. A nonzero exit or structured
`error` is a failure; preserve its sanitized `error.message`. The separate raw
reader `--envelope` interface and `triage_store` use envelopes; do not mix contracts.
Required approval flags are not shown above intentionally:
add one only when the user granted that exact current gate.

For a retained completed bundle, inspect the actual manifest and referenced files.
Do not treat filenames, a raw transcript pasted in tool output, or `status` alone
as proof of source identity or completeness. Preserve citations exactly as the
reader defines them.

## Publication

```powershell
python scripts/triage_store.py publish "<notes-root>" instagram "instagram:<shortcode>" "<category>" "<draft.md>" --evidence "<manifest.json>" --evidence "<transcript.txt>"
python scripts/triage_store.py inspect "<notes-root>" "<returned-receipt-id>"
```

Add the actual selected frame/evidence files with repeated `--evidence`, up to the
store's limit. The draft needs scalar source frontmatter, exact Source key, title,
priority/reason, Synopsis, Action Items, Instagram Excerpt, Links and Evidence.
The publisher writes links to the selected retained files and verifies their hashes.

For an explicit skip record, use category `_Skipped`, a draft with source
frontmatter and `## Reason`, and `--skipped`. Do not claim skipped or pending items
as analyzed. Both store commands return envelopes; `source_action_authorized`
always remains false. Publication never supplies account permission.
