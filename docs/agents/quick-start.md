# Quick start

Complete one read from source inspection to a citation-grounded answer. Run every command from any
terminal and keep each decision visible.

If Voidscape is not ready yet, see [Install](install.md).

## Choose one source

Use a local image, audio file, video, folder, or supported public URL you are allowed to process.
The examples below use `meeting.mp4`; replace that name with your path or URL.

## Inspect the source

```powershell
voidscape inspect "meeting.mp4"
```

Inspect reports source facts such as duration, dimensions, audio, and available caption or sidecar
paths. It does not extract frames, transcribe speech, or upload the source.

## Preview the decision

```powershell
voidscape preview "meeting.mp4"
```

Read the preview before continuing. Check the evidence scope, dependencies, estimated agent-reading
cost, and these independent fields:

| Field | Meaning |
| --- | --- |
| `requires_cloud_approval` | Audio would leave the host for this job |
| `needs_model_download` | A selected local model is not present yet |
| `needs_install` | A required local dependency is missing |
| `free` | The selected evidence-preparation path has no out-of-pocket backend cost |

If the preview requires a cloud or model-download approval, stop and make that decision for this
source. Do not copy approval flags from this guide.

## Read the evidence

Use a new work folder:

```powershell
voidscape read "meeting.mp4" --workdir voidscape-output
```

The read prepares `manifest.json`, selected `frames/`, and `transcript.txt`. It does not write the
final interpretation for the agent.

## Ask one grounded question

Give the work folder to your agent and ask:

> Summarize the recording in three bullets. Support each factual bullet with an exact `[MM:SS]` citation
> from the prepared evidence. Say when the evidence does not support a claim.

Open the cited transcript or frame and verify at least one statement yourself. The citation points
to source evidence; it is not a guarantee that transcription or interpretation is perfect.

## Try your own source

Replace the example path with another source you are allowed to use. Run `inspect` and `preview` again;
approvals belong to the current source, scope, tier, and backend. Use a fresh workdir for the read.

For images, articles, feeds, URLs, time windows, or raw JSON envelopes, continue with
[Workflow and protocol](workflow.md) and the focused reader pages.

## Where next

- [Concepts](concepts.md) explains why the three commands are separate.
- [Video and audio](readers/video-audio.md) covers tiers, backends, and source-time citations.
- [Troubleshooting](troubleshooting.md) starts with the safest check for common failures.
