# Evaluation

`read-video` was built and validated with Codex's **skill-creator** eval loop. The idea: run the same
realistic prompts twice — once **with** the skill, once with **no skill** (baseline) — grade both against
objective assertions, and compare. If the skill doesn't beat a capable general-purpose agent, it isn't
pulling its weight.

## Method

For each test case, two subagents run the same prompt in the same turn:
- **with_skill** — has the `read-video` skill loaded.
- **without_skill** — plain agent, must improvise (it *can* DIY `ffmpeg` + `faster-whisper`).

Each run's outputs are graded against named, objectively-checkable assertions; results aggregate into a
benchmark with pass-rate, time, and token usage per configuration.

## Test cases (`skill/evals/evals.json`)

| id | name | prompt gist | what it probes |
|---|---|---|---|
| 0 | `visual-summary` | "What's happening in this screen recording?" (short clip) | probe → estimate → visual run → Read → grounded TL;DR + `[MM:SS]`, no spend |
| 1 | `audio-doc` | "Transcribe this meeting and save me notes" (short clip) | recognizes audio is the value; local faster-whisper ($0, no upload); writes a durable note |
| 2 | `cost-gate-skip` | "Estimate what it'd cost before doing anything" (~13-min clip) | probe + estimate **only**; presents the gate; does **not** extract/transcribe |

To reproduce: drop a short and a long clip into `samples/` as `short-screen-recording.mp4` /
`long-screen-recording.mp4` (gitignored), then run the loop with the skill-creator plugin.

## Iteration-1 results

| configuration | pass rate |
|---|---|
| **with skill** | **93.3%** (14/15 assertions) |
| baseline (no skill) | 66.7% (10/15) |
| **delta** | **+0.27** |

### Where the skill won
The baselines were surprisingly capable — a general-purpose agent can write its own `ffmpeg` + faster-whisper
pipeline. So the skill's edge concentrated in behaviors a bare agent doesn't reliably do:

- **Cost-gate-before-run** — pricing the job and *waiting*, instead of just doing it.
- **`[MM:SS]` grounding** — citing specific timestamps from the frame manifest.
- **Vault persistence** — saving a durable note to the workspace.
- **Privacy-correct backend choice** — the skill recommended **free local** transcription; a baseline
  recommended a **paid API that uploads the audio**. Same task, very different data-handling — a qualitative
  win the raw pass-count doesn't fully capture.

### What iteration-1 surfaced (and the fix)
The biggest finding wasn't a pass/fail — it was a robustness gap. `faster-whisper` originally hardcoded the
`base` model. In a locked-down network it couldn't complete the model download, and both configs silently
fell back to the `tiny` model → poor non-English (Spanish) accuracy.

The fix (now in `scripts/video.py`):
- **Model size is configurable** (`whisper_model` / `READ_VIDEO_WHISPER_MODEL`), default **`small`**.
- **Offline-first load** (`local_files_only=True`) so a cached model loads without the network revision check
  that was failing even when the files were on disk.
- **Loud fallback** — if it has to drop to a smaller cached size, it prints a stderr `WARNING` instead of
  degrading silently.

This is the kind of thing the eval loop is for: the benchmark number was fine, but reading *how* the runs
behaved exposed a real defect that mattered for the actual use case.

## Takeaways for contributors

- **Non-discriminating assertions** (both configs pass — "no out-of-pocket spend", "used visual path") are
  fine as guardrails but don't measure the skill's value; the discriminating ones (cost-gate, grounding,
  persistence) are what to protect when editing the prompt.
- **Watch the transcripts, not just the pass-rate.** The model-size defect and the privacy-correctness win
  both came from reading run behavior, not the aggregate.
- A good next iteration: relax the "≥3 `[MM:SS]` cites" assertion for near-static screens (honestly sparse),
  or segment frames by **visual-change events** instead of a fixed budget.
