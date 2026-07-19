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

After `estimate`, Codex reads two flags:

- **`free: true` and `needs_install: false`** → no out-of-pocket spend, dependencies present → **proceed**
  (still mention it if the *token* job is large, e.g. a long URL with 100 frames).
- **`free: false`** (a provider gets billed) **or** **`needs_install: true`** → **stop.** Show the `--human`
  estimate: the total, the dominant driver, the backend. Then ask the user to **run as-is / pick a cheaper
  backend / skip.** Don't spend on an API, and don't install anything, until the user says yes.

The principle: **audio is never silently sent to a cloud API**, and money/installs are never spent without an
explicit yes. This is the behavior that separates the skill from an agent improvising `ffmpeg` commands.

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
