# Concepts

Voidscape is an evidence-preparation boundary between a source and an agent answer. Understanding
five concepts prevents most unsafe retries, unsupported claims, and integration mistakes.

## Source

A source is the exact local file, local folder, or supported public URL selected for one job. The
browser page around a source, a saved collection, and the agent prompt are not automatically part of
that source. Account access in a browser is not CLI authentication.

## Evidence bundle

`read` writes a new local work folder containing a manifest and the selected evidence. The bundle
shape depends on the reader:

| Reader | Bundle |
| --- | --- |
| Video/audio | `manifest.json`, optional `frames/`, optional `transcript.txt` |
| Images | `manifest.json`, ordered `images/` |
| Article/RSS | `manifest.json`, ordered `entries/` |

The source remains unchanged. The bundle is inspectable input for an agent, not a finished semantic
note or a claim that every detail was captured.

## Guided sequence

```text
inspect -> preview -> approval or dependency decision -> read -> answer with citations
```

`inspect` discovers facts. `preview` exposes scope, cost, dependencies, cloud transfer, and model
acquisition. `read` prepares only the selected evidence. If the source, scope, tier, or backend
changes, preview again.

## Permission boundary

The harness owns user-approved browser interaction and approval presentation. The operating system
owns screen-recording permission. Voidscape owns evidence preparation and its per-job gates.

These permissions do not substitute for one another. Browser approval does not authorize cloud
transcription. A configured key does not authorize an upload. A previous model download approval
does not authorize a different cloud job.

## Citation contract

The manifest defines what an agent may cite:

- video or audio moments: `[MM:SS]` on the original source timeline;
- ordered images: `[image N]`;
- article entries: `[article N]`;
- RSS or Atom entries: `[entry N]`.

An agent should narrow or rerun the evidence when the answer falls outside the prepared bundle. It
should not invent timestamps, pages, OCR, hidden motion, or missing publication metadata.

## Capability status

- `shipped`: supported entry point on current `main`, backed by tests;
- `release-candidate`: implemented and locally verified, but not merged, installed, or published;
- `dev-only`: working repository helper, not an installed command;
- `planned`: approved direction without a shipped implementation;
- `parked`: explicitly deferred behind a product, security, legal, or distribution gate.

Harness claims use a separate evidence scale: `personally-tested`, `vendor-documented`, or
`unverified`. A vendor feature never becomes a shipped Voidscape capability through prose alone.

## Guided CLI and raw protocol

Use `voidscape.py inspect|preview|read` when an agent can explain decisions to a user. Use focused
reader commands `manifest -> probe -> estimate -> run` for deterministic integrations. Both paths
preserve the same gates and evidence contracts; the raw protocol does not provide a bypass.

Continue with [Workflow and protocol](workflow.md) for commands, envelopes, and exit handling.
