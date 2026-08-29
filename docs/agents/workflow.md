# Workflow and protocol

Voidscape exposes a guided product flow and a lower-level reader protocol.

[Back to agent docs](index.md) · Canonical sources: [workflow](../workflow.md),
[architecture](../architecture.md), and [CLI reference](../cli-reference.md)

## Guided flow

| Step | Command | Agent responsibility |
| --- | --- | --- |
| 1 | `voidscape.py inspect <input>` | Read source facts and recommended scope; do not process media |
| 2 | `voidscape.py preview <input>` | Inspect cost, dependency, cloud, and model-download decisions |
| 3 | approval gate | Stop when the preview requires a current approval or dependency action |
| 4 | `voidscape.py read <input>` | Pass only approvals granted for this previewed input and scope |
| 5 | read evidence | Use the manifest and exact citation labels in the answer |

The order is mandatory: `inspect -> preview -> read`. `customize` manages local preferences only;
`doctor` reports readiness without installing or changing anything.

## Approval fields

After preview, an agent must independently check:

- `requires_cloud_approval`
- `needs_model_download`
- `needs_install`
- `free`

`--allow-cloud` and `--allow-model-download` apply only after a current explicit yes for the
previewed job. An API key, configured backend, or previous run is not consent.

## Raw reader protocol

`video.py`, `image.py`, and `article.py` are focused siblings. Each exposes:

```text
manifest -> probe -> estimate -> run
```

The optional agent envelope is:

```json
{"ok": true, "data": {}, "error": null, "meta": {"protocol_version": "1.0"}}
```

Use `--envelope --compact` for deterministic single-line JSON. The shared exit codes are:

| Exit | Classification |
| --- | --- |
| 0 | success |
| 1 | unexpected error |
| 2 | usage error |
| 3 | input error |
| 4 | approval required |
| 5 | dependency error |
| 6 | operation failed |

An error envelope includes `code`, `message`, `retryable`, and `exit_code`. Do not treat every
non-zero result as retryable.

## Evidence contracts

| Reader | Evidence | Citation |
| --- | --- | --- |
| Image/carousel | `manifest.json`, ordered `images/` | `[image N]` |
| Video/audio | `manifest.json`, optional `frames/`, optional `transcript.txt` | `[MM:SS]` |
| Article | `manifest.json`, ordered `entries/` | `[article N]` |
| RSS/Atom | `manifest.json`, ordered `entries/` | `[entry N]` |

The agent cites only evidence actually prepared. A focused rerun is preferable to inventing details
outside the selected range.
