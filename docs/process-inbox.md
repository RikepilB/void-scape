# Process a local recording inbox

Repository-only controller for issue #56. It reads selected local recordings,
authors transcript notes through an existing cloud-disabled local model, verifies
the files, then moves each successfully processed recording. The project-scoped
[process-inbox skill](https://github.com/RikepilB/void-scape/blob/main/.agents/skills/process-inbox/SKILL.md)
coordinates this helper. It depends on the checkout; the base installed media
skill does not bundle the controller. No scheduler is installed by these commands.

Start with a preview from the repository root:

```powershell
python scripts/process_inbox.py --root "C:/Recordings/Inbox" --notes-root "C:/Knowledge" --model gemma3:4b
```

The default is read-only: no output folders, checkpoints, model calls or source
moves. After reviewing the selected files and destination, apply the same scope:

```powershell
python scripts/process_inbox.py --root "C:/Recordings/Inbox" --notes-root "C:/Knowledge" --model gemma3:4b --limit 10 --timeout 1800 --apply
```

Omitting `--root` uses configured `inbox_dir`, then `~/Documents/Voidscape/Inbox`.
`--notes-root` and the cached model name are explicit. Notes go beneath
`03_Media/Transcripts/` for files directly in the inbox; a named subfolder routes
to `Conference/<first-subfolder>/`. Notes are named by source SHA256. A model service
must already be running with cloud disabled; see [local note drafts](local-note-drafts.md).
No service or model is installed, started or downloaded automatically.

## Processing and recovery

- Discover up to 100 recordings oldest-first, with at most 10,000 directory entries scanned.
  A recording and its sidecars must be unchanged for `--min-age` seconds (default
  60). The worker checks again before processing and reports a recently changed
  input as deferred. A quiet period reduces partial-copy reads but cannot prove
  a remote sync is complete; source/evidence hash checks still apply. Use
  `--min-age 0` only for deliberately selected complete files.
  Managed, hidden and `processed/` folders are excluded. Links/reparse points fail
  closed. Video files use both modalities; audio files use audio. Notes currently
  analyze transcripts only, even when frame evidence is retained.
- Each worker calls `inspect`, `preview`, then `read`. Missing gate fields,
  cloud transfer, model download or installation requirements refuse that file.
  `auto` selects sidecar captions when available, otherwise `faster-whisper`.
  Explicit `captions`, `faster-whisper` and `whisper-cpp` are also available.
- A completed reader bundle and input/evidence hashes allow authoring to resume
  without repeating extraction. Model chunk checkpoints reuse validated work.
  Notes retain full transcripts, supported actions and timestamped moments.
  Duration comes from the probe; unavailable language is labeled `unknown`.
- Immutable receipts record source identity, original filename, note and evidence
  hashes. `.processed.json` is a managed index, not permission or proof by itself.
  Receipts and retained files are checked again before duplicate reuse or recovery.
- A verified note precedes the source move to `processed/<original-relative-path>`.
  Existing different destination bytes are never overwritten. A renamed duplicate
  is reported as skipped without transcription or model use, then moved under
  its own relative name so it no longer occupies future batch slots.
  Sidecar originals remain in place. Interrupted publication/moves are recoverable;
  changed completed artifacts stop processing for local review.
- Failures before the source move retain the recording and local work, record a
  sanitized failure and continue with the next file. Interruption after a verified
  move is recovered through its receipt. Windows Job Objects and POSIX process groups
  bound the worker and descendants to `--timeout` seconds (default 1,800). Recovery
  has a separate bounded worker. The existing model service is not forcibly stopped.
- If another process holds the inbox lock, return `status: busy`, zero counts and
  exit 0 without starting a worker. Permission and filesystem errors remain
  failures. Busy, empty and deferred-only runs do not require repeated alerts.

Run state, logs, original transcripts, frames and derived text live under
`<inbox>/.inbox/`; these are private data. The helper neither uploads them nor
applies automatic expiration. Deleting retained evidence invalidates verification.
Never publish this folder as diagnostic evidence without reviewing its contents.

The move uses same-filesystem hard links followed by unlink, with verification
before removal. A filesystem that cannot provide hard links fails safely with
the source retained. Model summaries remain reviewable: valid quotations do not
guarantee semantic completeness. Scheduled execution must preserve these same
local-only gates and needs separate operational verification.

## Verification and remaining work

Tests exercise process-tree deadlines, unsafe gate refusal, resumed authoring,
publication/move interruption, source changes, collisions and renamed duplicates.
An actual synthetic clip plus sidecar passed reader -> cached local model ->
verified note -> processed file. An unreadable preceding file stayed intact while
the valid file completed. With the model server stopped, an empty rerun and a
renamed duplicate succeeded without changing the checkpoint.

The skill has generated Claude/Agents/Codex controller mirrors. Check them with
`python scripts/sync_inbox_skill.py`; `--write` regenerates only those project
files. Behavioral evidence and unexecuted harness cases are recorded in
[the evaluation record](https://github.com/RikepilB/void-scape/blob/main/evals/process-inbox/RESULTS.md).
Matching files are not proof of runtime parity.

Still pending: real user-recording acceptance,
independent skill/harness evaluation, scheduled laptop
execution, and suite release packaging. These commands do not establish those
requirements as complete.
