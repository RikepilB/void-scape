# Agent documentation

Turn a source you are allowed to use into local, ordered evidence an agent can cite. These guides
cover the complete path from installing Voidscape to handling a failed or approval-gated read.

## Start with a source

If Voidscape is not installed, follow [Install](install.md). Then complete the
[Quick start](quick-start.md) with one source you are allowed to use:

```powershell
voidscape inspect "meeting.mp4"
voidscape preview "meeting.mp4"
voidscape read "meeting.mp4" --workdir voidscape-output
```

The sequence is the product contract: inspect facts, preview cost and permission boundaries, then
read only the approved evidence. An agent answers from the resulting manifest and artifacts rather
than guessing from a filename, URL, title, or thumbnail.

## Pick your path

| I need to… | Start here | Result |
| --- | --- | --- |
| Complete a first local read | [Quick start](quick-start.md) | Frames, transcript, manifest, and one grounded answer |
| Understand the safety model | [Concepts](concepts.md) | Sources, evidence bundles, gates, citations, and status labels |
| Drive Voidscape from an agent | [Workflow and protocol](workflow.md) | Guided commands, raw envelopes, and deterministic errors |
| Choose the right source reader | [Video and audio](readers/video-audio.md), [Images](readers/images.md), or [Articles and RSS](readers/articles-rss.md) | Source-specific inputs, outputs, limits, and citations |
| Capture a visible browser state | [Observe and capture](observe-and-capture.md) | One explicit local screenshot or short clip, followed by a normal read |
| Diagnose a failure | [Troubleshooting](troubleshooting.md) | Safe checks that never add approval flags automatically |

## What an agent may do

An agent may inspect a selected source, show a preview, explain a gate, run an approved read, open
the evidence bundle, and answer with its exact citation labels. Non-interactive callers may use the
stable JSON envelope documented in [Agent automation](automation.md).

An agent may not infer consent from a key, previous run, browser session, or configured backend. It
may not read browser credentials, cookies, storage, or secrets. Browser interaction belongs to the
user-approved harness; Voidscape runs on the host and owns evidence preparation.

A vendor feature is not automatically a Voidscape capability. Confirm its status in the roadmap
and support matrix before promising that an agent can use it.

## Reader engines

| Reader | Typical sources | Evidence contract |
| --- | --- | --- |
| Video/audio | recordings, voice memos, supported public media URLs | `frames/`, `transcript.txt`, `manifest.json`, cited as `[MM:SS]` |
| Images | one image or a local non-recursive carousel | ordered byte-preserving `images/`, cited as `[image N]` |
| Articles/RSS | local text, Markdown, HTML, feeds, or an approved public article fetch | ordered `entries/`, cited as `[article N]` or `[entry N]` |

## Know what is actually available

Read [Roadmap status](roadmap-status.md) before composing integrations. `shipped` means merged,
tested, and available through a supported entry point. `release-candidate` means locally implemented
and verified but not yet merged, installed, or published. `dev-only` helpers exist in a repository
but are not installed commands. `planned` and `parked` items are not callable capabilities.

For machine discovery, open [manifest.json](manifest.json), then inspect the selected reader's own
`manifest` command. The discovery document describes capabilities and gates; it never grants an
approval. The manifest never grants approvals.

## Canonical contracts

The installed agent contract is [`skill/SKILL.md`](../../skill/SKILL.md). Architecture and backend
behavior live in [`docs/architecture.md`](../architecture.md). If prose conflicts with executable
behavior, code and tests on `main` win and the documentation must be corrected.
