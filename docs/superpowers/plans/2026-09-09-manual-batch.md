# Manual batch preview and read

Implement C1 under the active suite request, with a privacy review in this plan.
This is a foreground evidence command, not the scheduled note-authoring workflow
in issue56. Existing individual commands retain their behavior.

## Input and execution contract

- `voidscape batch-preview manifest.jsonl --json` and `batch-read manifest.jsonl
  --workdir NEW_ROOT --json` accept at most100 JSON objects/1MiB of UTF-8 JSONL.
  Each row has `input`, optional unique `id`, and supported per-read options using
  snake_case keys. Reject unknown/duplicate keys and invalid types/values.
- No per-row permissions, config paths, workdirs, arbitrary commands, or output
  paths. Relative local inputs/references resolve against the manifest directory.
  Input paths may intentionally refer outside that directory, but observed links
  and reparse points are rejected. Output IDs cannot express paths or traversal.
- Route and validate every item, then preview all items before media processing.
  Include aggregate cost, per-item estimates, and aggregate gates. Normal remote
  video probing can use the network; preview does not fetch article bodies,
  transcribe, download models, or create read output.
- Batch read checks every required cloud/model approval and missing dependency
  before creating the output root. Flags apply only to this invocation and are
  never persisted. Each actual reader still rechecks its own gates at run time.
- Use a new output root and deterministic numbered item subdirectories. Reject
  preexisting roots, links/reparse points, and observed root replacement. Output
  traversal is impossible through IDs; recheck output boundaries around each item.
- Run sequentially, without retries. Independent execution failures are recorded
  with their original typed error and available partial data; other authorized
  items continue. Count completed, deliberately stopped, and failed separately.
- Persist private `batch-summary.json` after each item using a staged replacement.
  Record manifest SHA-256 and row IDs, not a second raw manifest or prompt archive.
  The JSON CLI result uses the existing envelope. Any failed item exits6; invalid
  preflight uses input-error3, missing permission uses approval4. Stops are not
  failures and never masquerade as complete reads. A successful batch containing
  stops has status `completed_with_stops`; stop stages remain per item.
  No resumable checkpoint claim.

## Privacy and threat boundaries

The user selects the manifest and one invocation's permissions. Manifest content
cannot grant permission. Raw initial prompts and signed source URLs are not copied
into batch metadata; reader results retain their existing private-evidence policy.
No account discovery/mutation, source move, vault publication, scheduler, daemon,
approval persistence, automatic retry, or new provider is introduced.

Path checks prevent traversal and reject observed links/root changes. This local
workflow assumes a user-controlled filesystem; it is not a sandbox against a
hostile process racing every filesystem operation. A detected output-boundary
change aborts the batch rather than continuing to write elsewhere.

## Validation

Extract shared structured preview/read helpers without changing individual CLI
results. Test all-validation-before-run, all-gates-before-output, schema bounds,
reader-option compatibility, path confinement, source-relative paths, mixed
success/failure/stops, summary recovery, no persisted prompts/permissions, gate
revalidation, and no approval reuse on the next invocation. Run local multi-reader
fixture QA, focused/full tests, generated checks, CI/review, then merge. Update
README, skill, CLI, agent workflow, and landing copy without claiming issue56 done.
