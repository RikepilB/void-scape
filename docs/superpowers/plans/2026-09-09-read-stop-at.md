# Explicit read stage stopping

Implement B1 from the media research under the active suite implementation request.
The default full read stays unchanged. This plan resolves the stage contract before
implementation; source research remains reference material, not shipped behavior.

- Video/audio `read` and raw `run` accept `--stop-at probe|frames`.
- A probe stop retains source metadata and a manifest, with no downloaded media,
  frames, transcript, model access, or transcription request. Remote probing keeps
  its existing URL validation and network behavior.
- A frames stop follows the existing visual acquisition/extraction path and does
  not transcribe. Reject frames stopping with an audio-only tier before probing.
- Reject this option for image/article/chat readers before reading their contents
  or creating outputs. Reject unknown stages before effects.
- Retain requested tier and backend separately from the executed backend. Record
  `status: stopped`, `stopped_by: user`, `stop_at`, and completed stages. Successful
  stopping exits zero; envelopes add `meta.stopped_at`. Failures remain failures.
- Recovery pointers for deliberate stops say `status: stopped`; partial failures
  still cannot receive a success pointer. A stop is not a resumable checkpoint.
- Matching preview/estimate selectors describe the planned read extent. This is
  an intentional extension of the research's preview non-goal: preview itself
  does not acquire frames, but must price the exact read the user will authorize.
- Unexecuted transcription has zero transcription cost, no credential access,
  no installation/download requirement, and no cloud approval request. Every
  operation actually executed retains its normal permission checks. No consent
  is granted by selecting a stop point.

Implement shared scope validation, result/pointer state, raw/guided CLI arguments,
and human output. Test no downstream effects, preview/read agreement, full-read
gates, invalid reader/tier combinations, stopped pointers, and failure behavior.
Then update CLI and agent documentation, regenerate packaged mirrors, run focused
and full tests plus generated-file checks, review, push, and merge passing CI.

No background execution, auto-resume, publishing, new provider, or browser
credential access is included. B3/C1/D1 and production Bridge work stay separate.

Validation before review: 583 full-suite tests passed on Windows. Four additional
CLI/permission cases then passed in the 23-test stop-at suite. Ruff, generated
agent docs, packaged mirror checks, and whitespace checks passed. Real local
ffmpeg QA generated a two-second clip: probe produced no media; frames produced
two images; both manifests/pointers said stopped and neither produced a transcript.
No provider request, model download, or plugin installation was performed.
