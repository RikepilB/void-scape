# Read stage results (B2)

Implement the authorized suite track with additive metadata and unchanged exit codes.
The requested tier remains mandatory: missing audio on `both` is a failed read,
not success silently downgraded to visual.

## Contract

- Every reader records completed stages and identifies the failing stage.
- Successful manifests gain `status: complete`, `stages_completed`, and `warnings`.
- If a later operation fails after usable artifacts were written, preserve those
  artifacts and write `manifest.json` with `status: partial`, `failed_stage`, completed
  stages, and a warning. Return the original nonzero exit and `ok: false`.
- The failure envelope includes this partial result in `data`; `meta` contains
  warnings and failed_stage. Only explicitly listed completed artifacts are evidence.
- No success recovery pointer is written for a partial run. Permission refusals
  remain hard failures, never converted into partial-result warnings.
- If manifest persistence itself fails, keep the original failure and add a bounded
  persistence warning. Never claim that a manifest exists when writing failed.
- Per-reader stages: probe/validate/workdir; video acquire/scope/frames/transcribe;
  image copy; article fetch/write_entries; chat write_transcript; then manifest/recovery.
- Preserve exception types and exit classification. Diagnostic metadata comes only
  from the owned progress object, not arbitrary provider exception attributes.

## Implementation

1. Shared execution/progress helpers; reader-specific operations remain in their modules.
2. Instrument each reader's actual stage boundaries and artifact checkpoints.
3. Extend raw and guided error envelopes and success metadata; keep legacy error text.
4. Test later transcription failure, partial image/article output, manifest failure,
   approval-before-work, probe errors, confinement, and no false success pointer.
5. Update skill/CLI/Agent Docs; run full tests, generated checks, CI, review and merge.

No retry, new provider, implicit consent, automatic downgrade, background execution,
or new account/cloud/model action is authorized by this implementation.
