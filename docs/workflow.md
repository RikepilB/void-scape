# Workflow — how Codex drives the skill

This is the decision flow encoded in [`skill/SKILL.md`](../skill/SKILL.md). It's what turns the three CLI
commands into a safe, predictable behavior when Codex reads a video for you.

## The loop

```
                      ┌──────────────────────────────────────────────────────────┐
   user asks about    │  1. probe     →  is it a file/URL? duration? audio?       │
   a video/URL  ─────►│                  captions/sidecar already available?      │
                      └───────────────────────────┬──────────────────────────────┘
                                                  ▼
                      ┌──────────────────────────────────────────────────────────┐
                      │  2. choose tier  →  static screen + talking = AUDIO;      │
                      │                     slides/UI/charts = VISUAL; else BOTH  │
                      └───────────────────────────┬──────────────────────────────┘
                                                  ▼
                      ┌──────────────────────────────────────────────────────────┐
                      │  3. estimate  →  price transcription $ + agent tokens $   │
                      └───────────────────────────┬──────────────────────────────┘
                                                  ▼
                      ┌──────────────────────────────────────────────────────────┐
                      │  4. COST GATE                                             │
                      │     free && !needs_install  →  proceed                    │
                      │     out-of-pocket $ OR needs install  →  STOP, show the   │
                      │     --human estimate, ask: run / cheaper backend / skip   │
                      └───────────────────────────┬──────────────────────────────┘
                                                  ▼ (only after go)
                      ┌──────────────────────────────────────────────────────────┐
                      │  5. run  →  frames + transcript into a workdir            │
                      └───────────────────────────┬──────────────────────────────┘
                                                  ▼
                      ┌──────────────────────────────────────────────────────────┐
                      │  6. Read the frames + transcript  →  grounded answer      │
                      │     TL;DR + [MM:SS] beats; save to out_dir if configured  │
                      └──────────────────────────────────────────────────────────┘
```

## The cost-gate rule (the differentiator)

After `estimate`, Codex reads four independent decisions:

- **`requires_cloud_approval: true`** → **stop.** Audio could leave the machine. Add
  `--allow-cloud` only after a current explicit yes for that previewed scope and backend chain.
- **`needs_model_download: true`** → **stop separately.** Add `--allow-model-download` only after
  the user approves that model acquisition.
- **`needs_install: true`** → **stop.** Explain the missing local dependency before installing it.
- **`free: false`** → **stop.** Show the `--human` estimate, including transcription dollars,
  API-equivalent agent cost, dominant driver, and backend. Ask: run / cheaper backend / skip.

Proceed only when none of those fields requires action, or when the matching action was approved
for this invocation. Still mention unusually large agent-token estimates even when transcription is
free.

The principle: **audio is never silently sent to a cloud API**, and money, installs, or first model
downloads never happen without the matching explicit yes. An API key or a previous approval is not
consent for the current invocation.

## Output contract

When Codex answers, it uses a consistent shape so the result is groundable and skimmable:

```markdown
## TL;DR
<2–3 sentences: what the video is and the takeaway>

## Key points
- **[MM:SS]** <a specific, grounded moment — cite the timestamp from the frame manifest / transcript>
- ...
```

Rules that keep it honest:
- **Cite `[MM:SS]`** from the manifest/transcript rather than inventing structure.
- If frames are near-identical (a static screen), **say so** instead of narrating imaginary motion.
- If transcription fell back to a smaller model (the stderr `WARNING`), note that accuracy may be reduced.
- Don't claim to have watched parts you didn't extract — offer a focused `--start/--end` re-run instead.

## Workspace integration (optional)

If `skill/workspace.json` exists:

- **Inputs** — the user can pass a **bare filename** (resolved against `inbox_dir`) or a line from
  `inbox_dir/urls.md`, instead of a full path.
- **Outputs** — after answering, Codex **saves the finished note to `out_dir/<source-stem>.md`** (same
  TL;DR + `[MM:SS]` format) and reports the path. The frame/transcript workdir is throwaway; the `.md` is the
  durable artifact.

With no `workspace.json`, the skill behaves exactly the same minus those conveniences — pass full paths, get
the answer in chat.
