# Voidscape for agents

Voidscape turns selected media and documents into local, ordered evidence an agent can cite.

**Current boundary:** the harness may browse or interact with user-permitted pages; Voidscape runs
on the host and governs evidence preparation through `inspect -> preview -> read`.

## Start here

```powershell
python skill/scripts/voidscape.py inspect "meeting.mp4"
python skill/scripts/voidscape.py preview "meeting.mp4"
python skill/scripts/voidscape.py read "meeting.mp4" --workdir evidence
```

`inspect` discovers source facts. `preview` surfaces cost, dependencies, cloud transfer, and model
downloads. `read` prepares artifacts only after the applicable approvals exist. The agent then reads
the manifest and evidence, answering with citations rather than guesses.

## Three-layer model

| Layer | Owner | Responsibility |
| --- | --- | --- |
| Harness | Codex/ChatGPT, Claude, or another tool-capable agent | Permitted browser interaction, shell execution, approval UI, host routing |
| Observe companion | Optional ffmpeg or screenpipe tooling | Screenshots, short clips, or separately managed desktop memory |
| Voidscape | This repository and installed skill | Local-first evidence preparation, cost/privacy gates, manifests, citations |

Browser access is not CLI authentication. Voidscape never reads browser credentials, cookies,
storage, or secrets. See [constraints](constraints.md).

## Documentation map

### Operate Voidscape

- [Harness support](harnesses.md) — verified scope for Codex, Claude, and generic agents.
- [Workflow and protocol](workflow.md) — guided commands, raw reader commands, envelope, and errors.
- [Constraints and permissions](constraints.md) — gates, authentication, privacy, and citations.
- [Agent automation](automation.md) — safely coordinate the non-interactive CLI.
- Observe and capture — planned documentation in
  [issue #22](https://github.com/RikepilB/void-scape/issues/22).

### Readers

- [Images and carousels](readers/images.md)
- [Video and audio](readers/video-audio.md)
- [Articles and RSS/Atom](readers/articles-rss.md)

### Capture adapters

- [Instagram](capture-adapters/instagram.md)
- [YouTube](capture-adapters/youtube.md)

### Truth and direction

- [Roadmap status](roadmap-status.md) — shipped, dev-only, planned, and parked.
- [References](references.md) — canonical local sources, vendor docs, and pattern sources.
- Machine-readable discovery manifest — planned in
  [issue #20](https://github.com/RikepilB/void-scape/issues/20).

## Status vocabulary

- `shipped`: merged, tested, and available through the supported installed/public entry point.
- `dev-only`: repository tooling that is not installed as a supported skill capability.
- `planned`: approved issue or roadmap work without merged implementation.
- `parked`: explicitly deferred behind a design, security, legal, or product gate.

Harness claims use `personally-tested`, `vendor-documented`, or `unverified`. A vendor feature is
not automatically a Voidscape capability.

## Canonical contracts

The installed agent contract is [`skill/SKILL.md`](../../skill/SKILL.md). Architecture and backend
behavior live in [`docs/architecture.md`](../architecture.md). If documentation conflicts with
executable behavior, code and tests on `main` win and the documentation must be corrected.
