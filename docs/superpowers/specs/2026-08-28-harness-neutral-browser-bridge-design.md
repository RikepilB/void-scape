# Harness-neutral browser bridge and security contract

**Date:** 2026-08-28  
**Status:** Design approved for review — implementation not authorized  
**Issue:** GitHub #14  
**Branch:** `chore/post-merge-verification`

## Goal

Design a portable browser bridge that lets different agent harnesses invoke Voidscape while media and
browser state remain on the user's desktop host. The protocol may be model-neutral, but compatibility
must be claimed per verified harness adapter.

This document is a design and security contract only. It does not authorize building a universal
browser extension, native-messaging host, loopback daemon, or MCP server.

## Non-goals

- Implementing a browser extension, MCP server, or native-messaging host
- Automatic cookie or credential transfer from the browser to `yt-dlp` or the Voidscape CLI
- Unattended orchestration, cron, or background capture
- Universal compatibility claims across every model and harness
- Replacing harness-owned browser control (Codex Chrome, Claude in Chrome)

## Repository placement decision

**Recommendation: dedicated repository, not in-tree.**

| Option | Fit | Rationale |
| --- | --- | --- |
| **Dedicated repo** (`voidscape-bridge` or similar) | **Recommended** | The bridge is a different product shape than the CLI-first Voidscape skill. It carries its own security surface, release cadence, per-harness adapters, and platform ToS review. Keeping it out of `void-scape` preserves the submission's local-first CLI discipline and avoids coupling bridge CVEs to media-engine releases. |
| In-tree package under `void-scape/` | Not recommended | Blurs the "next-project candidate" boundary in `docs/ROADMAP.md`. Bridge adapters would ship beside `video.py` even though most Voidscape users never install a browser bridge. Security review and versioning would entangle unrelated artifacts. |
| Published PyPI/npm package only | Partial | A distributable package is useful inside the dedicated repo, but the contract, adapters, and threat model still deserve their own home and issue tracker. |

**What stays in `void-scape`:**

- The CLI manifest and `{ok,data,error,meta}` envelope (`video.py manifest`, `image.py manifest`)
- Harness-support documentation (`docs/harness-support.md`, `docs/chrome-use-case-matrix.md`)
- This design spec and its security contract (reference copy or link from the bridge repo README)

**What moves to the dedicated repo when implementation is authorized:**

- Harness-specific adapters (Codex/ChatGPT, Claude)
- Transport hosts (native messaging, loopback service, MCP server)
- Bridge tool schemas and capability negotiation registry
- Adapter verification fixtures and evidence labels

## Architectural boundary

Voidscape remains the media engine. The harness owns browser control. The bridge is a thin,
auditable shim that:

1. receives **user-permitted, page-scoped observations** from the harness browser integration;
2. normalizes them into bridge tool results using the Voidscape envelope;
3. invokes the **local Voidscape CLI** on the host that can reach the selected media;
4. returns evidence paths and structured errors — never browser secrets.

```text
Phone (remote UI) ──► Harness remote control ──► Desktop host session
                                                      │
                         Harness browser tools ◄──────┤ (signed-in tab, DOM, network *when enabled*)
                                                      │
                         Bridge adapter (future) ──────┤ URL selection, capability negotiation
                                                      │
                         Voidscape CLI (local) ────────┘ inspect → preview → read
```

Browser access does not authenticate `yt-dlp`. When account-scoped CLI access is required, the user
must provide an explicit, site-scoped Netscape `cookies.txt` via `READ_VIDEO_YTDLP_COOKIES` — a
path the bridge must not populate automatically.

## Transport comparison

All transports must speak the same logical tool contract (schemas + envelope). Physical transport is
a harness adapter concern.

| Transport | How it works | Pros | Cons | Evidence |
| --- | --- | --- | --- | --- |
| **Native messaging** | Browser extension ↔ OS-launched host process over stdin/stdout JSON messages | Tight coupling to one browser profile; no open TCP port by default; matches Chrome extension patterns | Platform-specific installers; one host per browser profile; harder to debug; message size limits | **Vendor-documented** for Codex Chrome and Claude in Chrome extension models |
| **Loopback HTTP/WebSocket service** | Local daemon on `127.0.0.1` (or UDS) accepts authenticated JSON-RPC from harness and bridge | Easy to test; language-agnostic clients; supports multiple concurrent harness sessions with session tokens | **Local port exposure** risk if misbound; requires origin/session binding; another process to lifecycle-manage | **Unverified** for Voidscape — reasonable for a future MCP-adjacent host |
| **MCP-style tool calls** | Harness exposes or consumes tools over MCP (or MCP-like JSON schema) | Schema-first discovery; aligns with `manifest` introspection; portable across agents that already speak MCP | Not universal across harnesses; still needs a local executor for Voidscape CLI; spec drift across MCP versions | **Vendor-documented** that some agents support MCP; **unverified** as the Voidscape bridge transport |

**Recommendation:** define transport-agnostic tool schemas first. Implement adapters per harness:

- **Codex / ChatGPT:** prefer the harness's existing browser integration for observation; use native
  messaging or harness-native tool forwarding only if required to reach the local CLI host.
- **Claude Code:** same split — Claude in Chrome for observation; local CLI execution beside the
  coding session.
- **Other MCP-capable harnesses:** optional MCP adapter wrapping the same schemas.

Do not pick one transport in the design and force every harness through it. Pick one **contract** and
allow multiple transports behind adapter modules.

## Tool schemas (CLI manifest + envelope)

The bridge reuses Voidscape's existing machine-readable CLI contract. Adapters call the local CLI with
`--envelope` (and usually `--compact`) and wrap results in bridge-level tools.

### Layer 1 — Voidscape CLI (authoritative)

```bash
video.py manifest --envelope --compact
video.py probe <url-or-path> --envelope --compact
video.py estimate <url-or-path> ... --envelope --compact
video.py run <url-or-path> ... --envelope --compact
```

Manifest excerpt (from `skill/scripts/video.py`):

```json
{
  "protocol_version": "1.0",
  "interactive": false,
  "default_output": "legacy_json",
  "agent_output": "standard envelope: {ok,data,error,meta}",
  "commands": {
    "manifest": { "description": "describe commands, flags, output protocol, and exit codes" },
    "probe": { "description": "inspect a local file or URL without media processing" },
    "estimate": { "description": "price tokens/transcription and surface approval requirements" },
    "run": { "description": "extract frames and an optional transcript into a workdir" }
  },
  "exit_codes": {
    "0": "success",
    "1": "unexpected_error",
    "2": "usage_error",
    "3": "input_error",
    "4": "approval_required",
    "5": "dependency_error",
    "6": "operation_failed"
  }
}
```

Envelope shape (all `--envelope` responses):

```json
{
  "ok": true,
  "data": { },
  "error": null,
  "meta": { "command": "probe", "protocol_version": "1.0" }
}
```

Error object fields: `code`, `message`, `retryable`, `exit_code`.

### Layer 2 — Bridge tools (harness-facing)

Bridge tools are a stable, versioned surface. Each tool:

- accepts only JSON-schema-validated inputs;
- maps 1:1 to a Voidscape CLI command or a read-only browser observation the harness already permits;
- returns `{ok,data,error,meta}` plus bridge `meta` extensions (`adapter`, `capability_id`, `evidence_label`).

| Bridge tool | CLI mapping | Purpose |
| --- | --- | --- |
| `voidscape.manifest` | `video.py manifest` / `image.py manifest` | Introspection for agents |
| `voidscape.probe` | `probe` | Inspect URL or path without processing |
| `voidscape.estimate` | `estimate` | Cost and approval surfacing |
| `voidscape.run` | `run` | Execute read after gates pass |
| `browser.get_active_media_url` | *(harness browser API)* | User-selected or agent-visible media URL from permitted tab |
| `browser.get_page_metadata` | *(harness browser API)* | Title, visible player duration, caption presence — **no storage reads** |

`browser.*` tools are implemented by the harness adapter, not by reading cookies or `chrome.storage`.
They return only what the harness already exposes through its approved browser integration.

Example bridge response:

```json
{
  "ok": true,
  "data": { "input": "https://example.com/video", "source": "youtube", "duration": 125.0 },
  "error": null,
  "meta": {
    "command": "voidscape.probe",
    "protocol_version": "1.0",
    "bridge_version": "0.1.0",
    "adapter": "codex-chrome",
    "capability_id": "media.probe.public_url",
    "evidence_label": "richard-tested"
  }
}
```

Image inputs follow the same pattern via `image.py` when dispatch detects a local image or carousel
directory.

## Capability negotiation

Models and harnesses must only see **verified** operations. Adapters publish a capability manifest at
handshake time.

### Capability manifest (adapter → harness)

```json
{
  "bridge_version": "0.1.0",
  "adapter_id": "claude-chrome",
  "evidence_label": "vendor-documented",
  "capabilities": [
    {
      "id": "media.probe.public_url",
      "tools": ["voidscape.probe", "browser.get_active_media_url"],
      "verified": true,
      "evidence_label": "richard-tested"
    },
    {
      "id": "media.read.local_with_gates",
      "tools": ["voidscape.estimate", "voidscape.run"],
      "verified": true,
      "evidence_label": "richard-tested",
      "requires": ["inspect_preview_read_sequence", "approval_gates"]
    },
    {
      "id": "media.read.authenticated_cli",
      "tools": ["voidscape.probe", "voidscape.run"],
      "verified": false,
      "evidence_label": "unverified",
      "notes": "Requires user-supplied READ_VIDEO_YTDLP_COOKIES; bridge does not export browser cookies"
    },
    {
      "id": "browser.storage.read",
      "tools": [],
      "verified": false,
      "evidence_label": "unverified",
      "forbidden": true
    }
  ]
}
```

### Negotiation rules

1. **Default deny:** if a capability is not listed with `verified: true`, the harness must not expose
   it to the model as a reliable operation.
2. **Forbidden capabilities** (`forbidden: true`) must never be registered, even as experimental tools.
3. **Sequence lock:** `media.read.*` capabilities require the `inspect → preview → read` workflow;
   adapters must not expose a single-shot "read anything" tool that skips `estimate` approval surfacing.
4. **Per-adapter claims:** compatibility is `adapter_id + capability_id`, not "Voidscape works everywhere."
5. **Evidence propagation:** every tool result carries `evidence_label` so agents do not over-trust
   vendor-only paths.

## Host routing and lifecycle (phone → desktop)

Remote control continues an existing **desktop host session**; it does not relocate files, browser
profiles, or CLI credentials to the phone.

| Phase | Requirement | Evidence |
| --- | --- | --- |
| **Pairing** | User explicitly pairs phone to a named desktop host through the harness vendor flow | **Vendor-documented** (ChatGPT Remote, Claude Code Remote Control) |
| **Host availability** | Desktop must remain awake, online, and session-unlocked per harness rules | **Vendor-documented** |
| **Browser state** | Signed-in tabs and site approvals remain on the desktop browser profile | **Richard-tested** for read-only observation flows |
| **CLI execution** | Voidscape runs on the paired desktop host, not on the phone | **Richard-tested** |
| **Continuation** | Remote UI sends intents; host executes tools and returns envelope results | **Vendor-documented** |
| **Disconnect** | On host sleep or disconnect, bridge returns `retryable: true` with `host_unavailable`; no queued unattended runs | **Unverified** — design requirement |

Lifecycle rules for adapters:

1. Resolve `host_id` from the harness session before any `voidscape.*` call.
2. Refuse cross-host routing (phone cannot target a different machine than the paired host).
3. Propagate harness session expiry — do not cache host credentials beyond the vendor session.
4. Surface explicit "host asleep" errors instead of silently failing or switching to cloud processing.

## Permission, approval, cloud-spend, and model-download gates

The bridge **must not bypass** Voidscape gates. Adapters are thin forwards.

| Gate | CLI mechanism | Bridge behavior |
| --- | --- | --- |
| **Site / tab permission** | Harness browser approval UI | Adapter only calls `browser.*` after harness reports permitted tab |
| **Cloud spend** | `estimate` → `requires_cloud_approval`; `run --allow-cloud` | Bridge exposes `voidscape.estimate` first; `voidscape.run` without allowance returns envelope `approval_required` (exit 4) |
| **Model download** | `estimate` → `needs_model_download`; `run --allow-model-download` | Same pass-through; never auto-add flags |
| **User confirmation** | Skill workflow `inspect → preview → read` | Bridge tools remain separate; adapters document that models must not skip preview |
| **Cookie auth** | `READ_VIDEO_YTDLP_COOKIES` env path | User configures explicitly; bridge never writes this path from browser state |

Approval forwarding:

```text
estimate → data.requires_cloud_approval == true
        → harness shows vendor approval UI
        → user consents
        → run with --allow-cloud
```

If the harness has no approval UI, the bridge returns `ok: false`, `error.code: approval_required`,
and does not retry with flags.

## Threat model

This threat model covers **origin validation**, **local port exposure**, **command injection**,
**cross-profile access**, and **credential leakage**.

### Assets

- User media URLs and local file paths
- Voidscape evidence bundles on disk
- User cloud API keys (environment / workspace config — out of bridge scope but must not be exfiltrated)
- Browser sessions (must remain harness-isolated; bridge must not read them)

### Threats and mitigations

| Threat | Description | Mitigation |
| --- | --- | --- |
| **Origin validation failure** | Malicious web page or extension impersonates the bridge | Bind native messaging to extension ID; loopback services accept only `127.0.0.1` with per-session HMAC/token; reject wildcard `0.0.0.0` binds |
| **Local port exposure** | Loopback service reachable from other local users or containers | Default deny; bind localhost only; optional UDS; auth on every request; no admin ports in docs |
| **Command injection** | Untrusted URL or path fragments passed to shell | Adapters invoke `video.py` via `subprocess` argv list (no shell); validate URLs/paths against schema; reject metacharacters in paths |
| **Cross-profile access** | Bridge in one browser profile reaches another profile's tabs | Adapter scopes to harness-reported `tab_id` / `profile_id`; no cross-profile tab enumeration |
| **Credential leakage** | Bridge reads cookies, `localStorage`, passwords, or exports Netscape cookies | **Hard rule:** forbidden capability; code review gate; automated test that bridge manifest excludes storage tools |
| **Confused deputy** | Remote phone triggers desktop CLI on unintended paths | Host routing ties to paired session; `voidscape.run` requires prior `probe`/`estimate` on same `input` hash in session |
| **Silent cloud spend** | Auto-adding `--allow-cloud` on retry | Pass-through exit 4; no flag injection |
| **Over-claiming** | Docs imply universal harness support | Evidence labels on every capability; default deny in negotiation |

### Hard rule — no browser credential access

The bridge never reads browser credentials, cookies, storage, or secrets. The bridge and all adapters **never**:

- read browser credentials, cookies, `localStorage`, `sessionStorage`, IndexedDB, or extension storage;
- export or write Netscape cookie files;
- call `document.cookie` or DevTools storage APIs for authentication purposes;
- pass harness network HAR entries containing `Cookie` or `Authorization` headers to the CLI.

Allowed browser observations (harness-mediated only):

- visible URL in an approved tab;
- DOM text/metadata the user could see;
- player duration / caption track presence when exposed by the harness developer-data APIs;
- screenshots only when the harness already permits them for the same task.

This matches `AGENTS.md`, `docs/chrome-use-case-matrix.md`, and `docs/authenticated-sources.md`.

## Adapter and verification plans

Compatibility is per adapter. Do not publish a single "works with all agents" claim.

### ChatGPT / Codex adapter

| Item | Plan | Evidence |
| --- | --- | --- |
| Browser observation | Use Codex Chrome / ChatGPT browser tools for tab selection and read-only inspection | **Vendor-documented** |
| Remote continuation | ChatGPT Remote steers paired desktop host | **Vendor-documented** |
| CLI execution | Run `video.py` / `voidscape.py` on paired host via existing shell tool | **Richard-tested** |
| URL handoff | User or agent copies permitted media URL from browser → `voidscape.probe` | **Richard-tested** |
| Authenticated CLI | User supplies `READ_VIDEO_YTDLP_COOKIES`; no automatic transfer | **Richard-tested** (failure path); cookie success **pending** |
| Bridge transport | Defer native messaging until harness documents a stable host protocol | **Unverified** |

Verification checklist before `verified: true`:

1. Public YouTube URL: `probe → estimate → run` without cookies.
2. Instagram saved collection: browser visible, anonymous CLI fails with actionable exit 6.
3. Remote session: phone intent returns host error when desktop sleeps.
4. `estimate` with cloud backend refuses `run` without `--allow-cloud`.
5. Confirm no storage APIs in adapter code paths (static allowlist audit).

Official docs:

- https://developers.openai.com/codex/chrome-extension
- https://developers.openai.com/codex/remote-connections
- https://developers.openai.com/codex/app/browser

### Claude adapter (Claude Code + Claude in Chrome)

| Item | Plan | Evidence |
| --- | --- | --- |
| Browser observation | Claude in Chrome for signed-in sites, DOM, console, network **when enabled** | **Vendor-documented** |
| Remote continuation | Claude Code Remote Control continues desktop session | **Vendor-documented** |
| CLI execution | Local Voidscape CLI beside coding session | **Unverified** as Voidscape product test |
| Cowork cloud | Voidscape only when session reaches local media + CLI | **Vendor-documented** boundary |
| MCP exposure | Optional future `voidscape.*` MCP tools mirroring bridge schema | **Unverified** |

Verification checklist before `verified: true`:

1. Repeat public YouTube path on Richard's Windows setup.
2. Confirm Claude site approvals required before `browser.get_active_media_url`.
3. Confirm Remote Control session cannot invoke CLI on an unpaired machine.
4. Run static audit forbidding cookie/storage reads.
5. Document divergence from Codex adapter in capability manifest `notes`.

Official docs:

- https://docs.anthropic.com/en/docs/claude-code/chrome
- https://docs.anthropic.com/en/docs/claude-code/remote-control
- https://support.anthropic.com/en/articles/12012173-getting-started-with-claude-for-chrome

## Evidence labels

All capabilities, adapter claims, and matrix rows use exactly one label:

| Label | Meaning | May publish as product capability? |
| --- | --- | --- |
| **Richard-tested** | Observed on Richard's connected Windows setup with signed-in accounts where noted | Yes, with scope notes |
| **Vendor-documented** | Supported in current OpenAI or Anthropic docs, not reproduced as Voidscape bridge test | Yes, as harness capability — not as Voidscape-verified |
| **Unverified** | Design intent or plausible path without product test | **No** — do not market |

Examples (from `docs/chrome-use-case-matrix.md`):

- Browser selection → host CLI `inspect → preview → read`: **Richard-tested**
- Mobile continuation: **Vendor-documented**
- Automatic cookie transfer to `yt-dlp`: **Unverified and unsupported**
- Universal model/harness support: **Unverified and unsupported**

## Security review gate (pre-implementation)

Implementation must not start until:

1. This design is reviewed against `AGENTS.md` constraints.
2. A security reviewer signs off on the threat model and forbidden-capability list.
3. Repository placement (dedicated repo) is accepted.
4. Per-adapter verification checklists exist as tracked issues in the bridge repo.
5. A regression test asserts the bridge contract excludes credential/storage tools.

## Acceptance criteria mapping

| Criterion | Section |
| --- | --- |
| Repo placement | Repository placement decision |
| Transport comparison | Transport comparison |
| Tool schemas | Tool schemas (CLI manifest + envelope) |
| Capability negotiation | Capability negotiation |
| Host routing / lifecycle | Host routing and lifecycle |
| Permission and approval gates | Permission, approval, cloud-spend, and model-download gates |
| Threat model | Threat model |
| No credential reads | Hard rule — no browser credential access |
| ChatGPT/Codex and Claude plans | Adapter and verification plans |
| Evidence labels | Evidence labels |
| Security review before build | Security review gate |

## References

- `docs/harness-support.md` — multi-harness matrix and host boundary
- `docs/chrome-use-case-matrix.md` — Richard-tested vs vendor-documented evidence
- `docs/authenticated-sources.md` — CLI cookie path vs browser auth
- `docs/ROADMAP.md` — next-project candidate (universal browser-extension reader)
- `skill/scripts/video.py` — `manifest`, `_envelope`, exit codes
- `AGENTS.md` — inspect → preview → read; no credential reads; no unattended orchestration
