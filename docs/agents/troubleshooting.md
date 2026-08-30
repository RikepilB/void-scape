# Troubleshooting

Start with evidence, not retries. Preserve the original error, run the narrowest read-only check,
and never add an approval flag merely to make a command pass.

## Run doctor first

```powershell
python skill/scripts/voidscape.py doctor
```

Doctor reports readiness without installing packages, downloading a model, changing preferences,
or starting a service.

## A command returns exit 4

Exit 4 means approval is required. Read the named preview field and present that exact decision to
the user. Do not automatically retry with `--allow-cloud` or `--allow-model-download`.

If the input, scope, tier, or backend changed since approval, preview again.

## A command returns exit 5

Exit 5 means a local dependency is unavailable. Run doctor, explain which selected path needs the
tool, and install it only as a separate approved action. A narrower path may be valid—for example,
existing captions instead of speech transcription—but it must remain honest to the task.

## A URL works in the browser but not the CLI

The browser may have account state that the CLI does not. Start anonymously and treat browser and
CLI authentication as separate. Voidscape never discovers or exports browser cookies.

For media the user is permitted to access, they may separately provide a site-scoped Netscape cookie
file through `READ_VIDEO_YTDLP_COOKIES`. Never print, inspect, commit, or copy that file into an
evidence bundle. See [Constraints and permissions](constraints.md).

## There are no captions

Preview a local transcription backend or a cloud backend. A first local model download requires
`--allow-model-download`; cloud transcription requires `--allow-cloud` for the current job. If
neither path is approved, report that transcript evidence is unavailable.

## The workdir is rejected

Use a new empty workdir for each run. Do not delete or overwrite an unfamiliar folder. If you need
to rerun, choose a new path or explicitly review and remove your own prior evidence outside the CLI.

## Article fetch is blocked

Local Markdown, text, HTML, RSS, and Atom inputs need no fetch approval. A public article URL is not
fetched during inspect or preview; read requires explicit approval for the remote request. Paywalled
or browser-authenticated extraction is a separate path and is not promised by the article reader.

## Observe cannot capture the screen

Run the companion diagnostic:

```powershell
python skill/scripts/observe.py doctor
```

Confirm the supported host/display path and operating-system permission. Observe does not grant a
screen-recording permission, install FFmpeg, overwrite a destination, record audio, or call read.

## The evidence does not answer the question

Say what is missing. Preview a narrower time window, another tier, more explicit timestamps, or the
correct reader, then create a new bundle. Do not infer motion from near-identical frames or claim
text outside a prepared article/feed entry.

## Report a reproducible defect

Record the command shape, sanitized error, exit code, platform, and whether the source is local or
public. Do not attach private media, tokens, cookie files, absolute personal paths, or raw browser
state. Link to the relevant manifest or a harmless fixture when possible.

For deterministic error fields and retryability, see [Workflow and protocol](workflow.md).
