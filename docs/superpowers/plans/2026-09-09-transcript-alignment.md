# Optional transcript reference alignment

Implement B3 as a local post-processing step under the active suite request.
Default reads retain existing transcription behavior and output. Similarity is
not factual verification: automatic captions and scripts remain untrusted evidence.

## Contract

- Add `--align-reference PATH` and `--alignment-threshold FLOAT` (default 0.8,
  range 0..1) to video/audio preview and read, and raw estimate/run.
- Accept explicit local UTF-8 TXT/SRT/VTT references, bounded to 2 MiB. No new
  fetch, provider request, model acquisition, or reference discovery occurs.
- Active alignment with a non-caption backend deliberately uses that backend,
  instead of the existing automatic sidecar shortcut. Preview and read both
  suppress the shortcut, so cloud/model/install gates reflect the real work.
  Caption baselines can use the existing sidecar or URL captions path. Reject
  using the exact same sidecar as both baseline and reference.
- Visual-only reads reject active alignment. Explicit probe/frames stops skip
  alignment and do not open a reference. Full reads without alignment are unchanged.
- Require a baseline with valid, monotonic `[MM:SS]` or `[HH:MM:SS]` start labels.
  Preserve each label verbatim. Existing backend output has no segment endings;
  report end time as unavailable, never invent it or imply millisecond precision.
- Match reference units in order with bounded lookahead and grouping. Replace
  baseline text only when similarity meets the threshold; preserve low-scoring
  baseline text and emit mismatch warnings. Never drop baseline segments.
- Retain original transcript, exact reference snapshot, and per-segment provenance
  beside the final transcript. Include source labels, reference indices, similarity,
  threshold, mismatch count, timing source, and explicit unavailable end times.
  Keep all artifact paths inside the workdir and include them in recovery metadata.
- Invalid references fail before media processing. An alignment failure after
  transcription remains a failed read with the original transcript available as
  partial evidence. Preserve the completed transcript if the post-pass cannot finish.

## Implementation and verification

Use a small standard-library alignment module with bounded file/parser inputs.
Integrate it as an explicit stage after transcription. Record which baseline
backend actually succeeded, including fallbacks and sidecars, rather than tagging
a requested chain as Whisper output. Update manifests, gates, CLI/help, skill,
agent workflow, README, and landing copy; regenerate docs and mirrors.

Tests cover high/low similarity, reference grouping, nonmonotonic/untimed input,
unchanged timestamp labels and scope offsets, exact original/reference retention,
actual backend provenance, sidecar/gate parity, stop-at no-effects, confinement,
failed post-pass evidence, defaults, and synthetic demo round-trip. Run focused/full
tests, real local fixture QA, generated checks, review, CI, and merge.

No audio forced alignment, translation, timing correction, silent second read,
automatic caption trust, background execution, or new optional dependency is added.

Validation before review: local full suite612 passed after package/legacy import
fixes. A subsequent relative-workdir recovery regression was reproduced and fixed
by resolving the video output directory;67 focused alignment/recovery/stage/stop
checks then passed. Real demo and packaged-module round-trips retained all three
start labels, original bytes, reference snapshot, and provenance. Ruff, generated
docs/mirror checks passed. Final hosted CI must include the last path fix.

Observed implementation limits: matching preserves existing rendered start labels;
end times are explicitly unavailable. The runtime demo used its synthetic caption
sidecar, not a newly downloaded Whisper model. Backend/consent/fallback behavior
uses synthetic unit fixtures; no provider request or model download was made.
