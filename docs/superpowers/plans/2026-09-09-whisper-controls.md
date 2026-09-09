# Opt-in Whisper word timing and vocabulary

Implement research track D1 under the active suite request. Upstream contract
verified against the official [faster-whisper transcribe implementation](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py)
on September 9: `word_timestamps` and `initial_prompt` are transcribe options;
returned word objects expose start, end, word, and probability. These are model
estimates, not a guarantee of acoustic accuracy. No upstream code is copied.

- Add `--word-timestamps` and `--initial-prompt TEXT` to matching video preview/read
  and raw estimate/run options. No prompt file, environment, or persistent setting.
- Active controls require only local/faster-whisper backends, and bypass automatic
  sidecar reuse. Preview and read agree on actual model/download/install needs.
  Reject incompatible readers/visual tiers/backend chains before output creation.
- Explicit probe/frames stops skip these controls. No STT work or consent occurs
  for an unexecuted stage. No change to cached-small, profile, or download gates.
- Pass requested controls intact. Never silently retry without them when an old
  backend rejects options; fail clearly. Preserve legacy VAD fallback only when
  neither new control is requested.
- Validate actual word start/end values; nonempty speech without word timing fails
  rather than receiving fabricated precision. Render segment labels from their
  first actual word start as `[MM:SS.mmm]`. Preserve raw word start/end/probability
  and source-time clipping offsets in a separate confined `words.json` artifact.
- Keep original word evidence intact when reference alignment changes transcript
  wording. The manifest explains its relationship to the baseline, and recovery
  pointers include it. Alignment does not manufacture word timings for new wording.
- Do not save the vocabulary prompt in manifests or output logs. Metadata only
  indicates whether one was supplied. Command-line text may remain in shell history;
  documentation must make that choice clear without adding a new storage mechanism.

Test unchanged default kwargs, opt-in plumbing, precise labels and clipping offsets,
word validation, legacy incompatibility, warm-cache no-network, model consent,
sidecar/preview parity, stop no-effects, alignment interoperability, and recovery.
Update help, CLI/skill/agent docs, README and landing; regenerate mirrors/docs.
Run focused/full tests, inspect packaged entry points, then CI and merge. A real
model download is not authorized by this implementation plan; distinguish fake
model contract tests from runtime accuracy evidence in the final report.

Validation before review:636 local tests passed. Real cached-small Whisper QA
ran via the packaged module with HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1,
using offline-generated speech. Preview required no cloud/model permission;
read returned14 words with valid ordered timing and the expected local-test text.
No model download/provider call occurred. Focused tests also verify clipped source
offsets and alignment interoperability. Ruff and generated docs/mirror checks passed.
