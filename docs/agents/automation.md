# Agent automation

Agents may coordinate Voidscape non-interactively, but automation does not weaken consent gates.

[Back to agent docs](index.md) · Canonical sources: [workflow](../workflow.md),
[CLI reference](../cli-reference.md), and the [reader protocol decision](../superpowers/specs/2026-08-28-media-reader-interface-reassessment.md)

## Guided coordination

Use the guided CLI when an agent can present approvals to a user:

```powershell
python skill/scripts/voidscape.py inspect "clip.mp4" --json
python skill/scripts/voidscape.py preview "clip.mp4" --tier both --backend captions
python skill/scripts/voidscape.py read "clip.mp4" --tier both --backend captions --workdir evidence
```

The agent records the preview decision, stops when required, and adds only the approval flags the
user granted for that invocation.

## Raw coordination

Use focused readers for integrations that need stable envelopes:

```powershell
python skill/scripts/video.py manifest --envelope --compact
python skill/scripts/video.py probe "clip.mp4" --envelope --compact
python skill/scripts/video.py estimate "clip.mp4" --tier both --envelope --compact
python skill/scripts/video.py run "clip.mp4" --tier both --workdir evidence --envelope --compact
```

Dispatch order in the guided CLI is image, then article, then video/audio. Integrators should use
reader manifests rather than duplicating command flags from memory.

## Safe state machine

```text
new -> inspected -> previewed -> approval_required
                         |             |
                         |             +-> wait for current user decision
                         +-> ready -> read -> evidence_ready -> answer_with_citations
```

Bind the decision to the input, scope, tier, backend, and preview. If those change, preview again.
Never auto-retry exit 4 with approval flags.

## Failure handling

- Exit 2 or 3: correct invocation/input before retrying.
- Exit 4: stop for the named approval.
- Exit 5: explain the missing dependency; installation is a separate action.
- Exit 6: surface the sanitized operation error and whether a narrower/public/local path exists.
- Exit 1: preserve the error and investigate; do not assume the run is safe to repeat.

Voidscape ships no scheduler, background worker, or production MCP host. A calling system remains
responsible for queue durability, concurrency, cancellation, and human approval presentation.

