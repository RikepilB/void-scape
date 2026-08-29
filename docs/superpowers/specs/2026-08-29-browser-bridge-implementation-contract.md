# Browser bridge implementation contract

**Date:** 2026-08-29

**Status:** Design review complete for a disposable spike; production implementation not authorized

**Issue:** GitHub #25
**Builds on:** [Harness-neutral browser bridge and security contract](2026-08-28-harness-neutral-browser-bridge-design.md)

## Decision summary

If a bridge is pursued, create a dedicated `voidscape-bridge` repository. Publish any native host,
extension, or adapter packages from that repository. Keep only the Voidscape CLI envelope, discovery
manifest, reference contracts, and per-harness evidence in `void-scape`.

The bridge exposes two separate surfaces:

```text
browser bridge tools                         Voidscape CLI tools
snapshot / screenshot / navigate             probe / estimate / run
        |                                              |
harness-owned permitted tab                  local reader subprocess argv
        |                                              |
        +----------- no shared secrets ---------------+
```

Browser tools never become aliases for CLI tools. A browser observation may produce a public URL or
local screenshot path, but that value must enter a new `probe -> estimate -> run` sequence. The
bridge never reads browser credentials, cookies, storage, or secrets.

## Repository and package boundary

| Option | Decision | Reason |
| --- | --- | --- |
| Code in `void-scape` | Reject | Couples an extension/host attack surface and release cadence to a local media reader. |
| Package only | Reject as the source of truth | Distribution is useful, but policy, adapters, tests, and advisories need their own repository. |
| Dedicated repository with published packages | Choose if authorized | Gives the bridge independent releases, security ownership, harness fixtures, and a kill switch without changing the CLI. |

No production extension, host, MCP server, package manifest, or installer belongs in this repository
under this decision. Issue #27 may build and delete a disposable prototype outside the production
tree; its report may be committed here.

## Permission policy YAML v1

The future bridge repository should validate a single user-owned YAML policy before registering any
tool. Unknown keys, duplicate keys, malformed origins, and unavailable enforcement capabilities are
fatal policy errors. An absent policy denies every browser action.

```yaml
version: 1
policy_id: research-readonly
profile_id: Default

sites:
  - origin: https://www.youtube.com
    paths:
      - /watch*
    actions:
      - snapshot
      - screenshot
      - navigate
    navigate_to:
      - https://www.youtube.com/watch*
      - https://support.google.com/youtube/*

schedule:
  timezone: America/Santiago
  windows:
    - days: [Mon, Tue, Wed, Thu, Fri]
      start: "08:00"
      end: "20:00"

deny_apps:
  - 1Password
  - Signal
  - KeePass

limits:
  snapshot_max_chars: 30000
  screenshots_per_minute: 6
  navigations_per_minute: 12
  session_minutes: 30
```

### Schema

| Field | Type | Required | Validation and meaning |
| --- | --- | --- | --- |
| `version` | integer | yes | Exactly `1`. |
| `policy_id` | string | yes | `^[a-z0-9][a-z0-9_-]{0,63}$`; appears in audit records, never as authority by itself. |
| `profile_id` | string | yes | Exact harness-reported browser profile binding. A mismatch denies the request. No profile enumeration. |
| `sites` | non-empty list | yes | Ordered entries do not widen one another; the request must match one complete entry. |
| `sites[].origin` | URL origin | yes | Exact `https` scheme, host, and effective port. No userinfo, path, query, fragment, wildcard host, loopback site, `file:`, `data:`, or `javascript:`. |
| `sites[].paths` | non-empty list | yes | Anchored path globs. `*` matches within the path only; it cannot match an origin. Query values grant no extra authority. |
| `sites[].actions` | enum list | yes | Any of `snapshot`, `screenshot`, `navigate`; default deny for missing actions. |
| `sites[].navigate_to` | URL-pattern list | for `navigate` | Every requested URL and redirect hop must match one entry and an allowed site origin. |
| `schedule.timezone` | IANA zone | yes | Invalid or unavailable zones fail closed. Do not silently use host local time. |
| `schedule.windows[]` | day/start/end | yes | Request start and every navigation redirect are checked. Midnight wrap is explicit when `end < start`. |
| `deny_apps` | string list | no | Exact normalized app identifiers for desktop-wide capture adapters. If configured but the adapter cannot enforce app filtering, policy load fails. Tab-only screenshots do not claim app filtering. |
| `limits` | positive integers | yes | Hard upper bounds; adapter defaults may be stricter. Limits reset only with a new user-authorized session. |

### Evaluation order

1. Authenticate the harness session and bind `session_id`, `profile_id`, extension ID, and host ID.
2. Parse and canonicalize the active tab URL; reject opaque or non-HTTPS origins.
3. Check the exact profile, current time window, site entry, path, and action.
4. For `navigate`, validate the requested URL before dispatch and every redirect before following it.
5. Apply deny-app enforcement when a desktop-wide capture adapter declares that capability.
6. Apply rate/session limits. Any missing fact or enforcement capability denies the action.

Deny always wins. The policy has no `admin`, `allow_all`, secret, cookie, storage, raw-header, shell,
or `eval` field. Policy changes invalidate active sessions and require a new user confirmation.

This borrows the useful shape of screenpipe's allow/deny, app, content, and time restrictions, but
changes the unsafe upstream default: the bridge is default-deny and never grants full access merely
because a permission block is absent.

## Browser bridge tool contract

All results use `{ok,data,error,meta}` with protocol version `1.0`. `meta` also includes
`bridge_version`, `tool`, `policy_id`, `adapter_id`, `session_id`, and an evidence label. Audit logs
record those identifiers, origin, action, decision, and timestamps; they exclude page text, image
bytes, URLs with query strings, headers, tokens, and local file contents.

### `browser.snapshot`

Input:

```json
{
  "session_id": "opaque-session-id",
  "profile_id": "Default",
  "tab_id": "harness-tab-id",
  "max_chars": 12000
}
```

Returns the active URL without query/fragment, title, viewport, and a bounded accessibility-first
tree of visible nodes (`node_id`, role, safe name, state, bounds). Visible text may be included within
the character cap. Password fields, input values, hidden DOM, script/style, headers, storage, raw
HTML, and cross-origin frame contents are excluded. Node IDs are session-scoped and expire after
navigation or the next snapshot.

### `browser.screenshot`

Input:

```json
{
  "session_id": "opaque-session-id",
  "profile_id": "Default",
  "tab_id": "harness-tab-id",
  "out": "C:\\captures\\task-17.png"
}
```

Captures only the permitted tab viewport through the harness API. The output must be a new absolute
`.png` path under a user-selected capture root. Refuse an existing file, symlink escape, cross-host
path, full-desktop fallback, or capture when the tab is no longer permitted. Return the local path,
byte count, SHA-256, viewport, and redacted origin. Never return base64 image data through logs.

### `browser.navigate`

Input:

```json
{
  "session_id": "opaque-session-id",
  "profile_id": "Default",
  "tab_id": "harness-tab-id",
  "url": "https://www.youtube.com/watch?v=example"
}
```

Performs a top-level GET navigation only. Validate the source tab, destination, and every redirect
against the same policy. Reject downloads, POST/resubmission, popups, new tabs, credentials in URLs,
non-HTTPS schemes, and cross-profile targets. Return `final_origin`, `redirect_count`, and a fresh
bounded snapshot. The raw URL remains in process memory only and is not written to audit logs.

### Explicitly absent tools

There is no raw `eval`, arbitrary JavaScript, click/type, network-body, request-header, cookie,
storage, download, upload, clipboard, credential, DevTools, or filesystem-browse tool in v1. Adding
any mutation action requires a new threat review and schema version.

## MCP manifest draft for Voidscape CLI tools

This manifest is a design artifact, separate from browser control tools. The MCP host delegates only
to fixed Python argv arrays for installed readers and returns their envelope unchanged. It never
accepts a command string.

```json
{
  "name": "voidscape-cli",
  "protocol_version": "1.0",
  "transport": "stdio",
  "tools": [
    {
      "name": "voidscape_probe",
      "description": "Inspect one local source or supported public URL without processing it.",
      "inputSchema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["reader", "input"],
        "properties": {
          "reader": {"enum": ["video_audio", "image", "article"]},
          "input": {"type": "string", "minLength": 1}
        }
      },
      "result": "{ok,data,error,meta}"
    },
    {
      "name": "voidscape_estimate",
      "description": "Price and surface approval or dependency gates before a read.",
      "inputSchema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["reader", "input"],
        "properties": {
          "reader": {"enum": ["video_audio", "image", "article"]},
          "input": {"type": "string", "minLength": 1},
          "tier": {"enum": ["visual", "audio", "both"]},
          "backend": {"type": "string"},
          "frames": {"type": "integer", "minimum": 1, "maximum": 240}
        }
      },
      "result": "{ok,data,error,meta} plus a session-bound preflight_id"
    },
    {
      "name": "voidscape_run",
      "description": "Run the exact preflighted read; approval flags remain explicit and job-scoped.",
      "inputSchema": {
        "type": "object",
        "additionalProperties": false,
        "required": ["reader", "input", "workdir", "preflight_id"],
        "properties": {
          "reader": {"enum": ["video_audio", "image", "article"]},
          "input": {"type": "string", "minLength": 1},
          "workdir": {"type": "string", "minLength": 1},
          "preflight_id": {"type": "string", "minLength": 32},
          "allow_cloud": {"type": "boolean", "default": false},
          "allow_model_download": {"type": "boolean", "default": false}
        }
      },
      "result": "{ok,data,error,meta}"
    }
  ],
  "forbidden_tools": [
    "browser.*",
    "shell",
    "eval",
    "cookies",
    "storage",
    "credentials"
  ]
}
```

The host selects `video.py`, `image.py`, or `article.py` from the `reader` enum. `estimate` generates
a short-lived `preflight_id` over the session, normalized input, reader, and cost-affecting arguments.
`run` rejects a missing, expired, already-used, or mismatched preflight. It adds `--allow-cloud` or
`--allow-model-download` only when the matching estimate field required it and the harness supplies a
fresh user approval for that exact job. Exit 4 remains `approval_required`, not a retry instruction.

Issue #26 decides whether an MCP runtime is worth adding. This draft does not choose an SDK or ship a
server.

## Transport security requirements

### Native messaging

- Pin the extension ID and native-host manifest path; reject messages without the bound profile and
  harness session.
- Use length-bounded JSON messages and strict schemas. No dynamic module, command, or path loading.
- Keep one user-authorized session per host process and destroy tokens on disconnect.

### Loopback HTTP

- Bind only `127.0.0.1` or `::1`; never `0.0.0.0`, LAN, or a public tunnel.
- Generate at least 128 bits of session entropy. Send it only as `Authorization: Bearer`; never in a
  URL, config committed to disk, page DOM, or log.
- Require authentication on every route, constant-time token comparison, bounded bodies, JSON-only
  content types, short timeouts, rate limits, and explicit allowed origins. CORS is not authentication.
- Reject browser requests whose `Origin` is absent or outside the registered extension/harness origin.
  Native/non-browser clients use a separate authenticated transport profile.
- Expose no health response beyond version/readiness before authentication and no debug/admin route.

### CLI execution

- Map enums to fixed script paths and flags. Invoke `subprocess` with an argv list and `shell=False`.
- Resolve local inputs and workdirs beneath user-approved roots; refuse existing/non-empty evidence
  workdirs according to reader behavior.
- Strip environment inheritance to an explicit allowlist. Never print `.env`, cookie paths, tokens,
  headers, or subprocess stderr that may contain page/session data.

## Updated threat model

| Threat | Required control | Verification |
| --- | --- | --- |
| Origin spoofing / DNS rebinding | Canonical exact origins, redirect revalidation, pinned extension origin, no wildcard hosts | Unit cases for userinfo, punycode, ports, redirects, and forbidden schemes |
| Localhost exposure | Loopback bind, per-session Bearer auth, no wildcard CORS, bounded unauthenticated surface | Connect without token/from disallowed origin and require denial |
| Command injection | Enum-to-fixed argv mapping, schema validation, `shell=False` | Metacharacter URL/path corpus never changes argv shape |
| Cross-profile access | Bind token to harness `profile_id`, `tab_id`, host, and session; never enumerate profiles | Request a tab from a second profile and require denial |
| Credential or storage leakage | No storage/header/network-body tools; redact password/input values; static forbidden-symbol audit | Search built artifacts and manifests for cookie/storage/credential APIs |
| Confused deputy | Site/action/time policy plus same-session preflight binding | Replay, expired, mismatched-input, and cross-host preflights fail |
| Sensitive screenshot | Tab-only capture, explicit new path, active permission recheck, no base64 logging | Permission revocation and overwrite tests |
| Redirect escape | Validate every hop before follow | Allowed URL redirecting to a denied origin fails closed |
| Token disclosure | Memory-only token, Authorization header, redacted logs, rotation on disconnect | Log snapshot contains no token; old token fails after disconnect |
| Capability overclaim | Per-adapter evidence labels and default-deny registration | Unverified tools absent from the harness-visible manifest |

## Per-harness verification plans

The protocol is harness-neutral; compatibility is not. Every row begins `unverified` and may change
only when its exact harness version, host, profile, policy, and evidence are recorded.

### Codex / ChatGPT

1. Register only `snapshot`, `screenshot`, and `navigate` through the supported Codex/ChatGPT browser
   surface; record the product version and permission UI used.
2. Prove denied origin, path, action, time window, redirect, profile, expired token, and revoked-site
   cases before a permitted snapshot.
3. Capture one harmless tab screenshot to a new local path, then run separate Voidscape `probe`,
   `estimate`, and `run`; confirm cloud/model approval still stops at exit 4 without consent.
4. Continue the same host session remotely, then sleep/disconnect the host and require a retryable
   host-unavailable result rather than cloud fallback.
5. Inspect extension/host manifests and built artifacts for forbidden credential/storage APIs.

### Claude Code / Claude in Chrome

1. Repeat the policy-denial matrix using Claude's current site-approval surface and record its
   product/extension version independently of Codex results.
2. Verify snapshot node IDs and tab IDs cannot cross profiles or survive navigation.
3. Run the local CLI tools beside the Claude Code session and verify the same preflight and approval
   binding; do not infer this from MCP support documentation.
4. Exercise Remote Control host disconnect and permission revocation without queued execution.
5. Publish a separate adapter capability manifest. Any divergence remains in `notes` and does not
   weaken the common policy.

Passing one plan says nothing about the other harness. No page may claim universal compatibility.

## Completed design security review checklist

Completed 2026-08-29 against the baseline contract and current issue #25 scope:

- [x] Default-deny permission policy covers exact sites, paths, actions, time ranges, profiles, and
  deny-app enforcement capability.
- [x] Browser tools are snapshot-first and omit raw `eval`, cookie, storage, header, and credential
  surfaces.
- [x] Navigation validates the initial URL and every redirect; screenshot is tab-only and refuses
  overwrite/path escape.
- [x] MCP CLI tools are a separate manifest and preserve `probe -> estimate -> run`, exit 4, and both
  approval fields.
- [x] Loopback transport requires Bearer authentication, exact origin validation, bounded input, and
  loopback-only binding.
- [x] CLI execution uses fixed argv, `shell=False`, approved roots, and sanitized output.
- [x] Cross-profile, cross-host, replayed-preflight, disconnect, and policy-revocation cases have
  explicit tests in the future verification plan.
- [x] Dedicated-repository placement and independent security ownership are recorded in the ADR.
- [x] Codex/ChatGPT and Claude have separate verification plans and start as `unverified`.
- [x] This review authorizes only issue #27's disposable spike/report, not a production merge.

**Review result:** complete enough to run the bounded disposable spike in issue #27. A production
implementation issue must repeat this checklist against concrete code, receive independent security
review, record per-harness evidence, and obtain explicit maintainer authorization. No such production
issue is authorized by this document.

## Acceptance mapping

| Issue #25 criterion | Evidence in this spec |
| --- | --- |
| Permission YAML with site/action/time/deny-app rules | Permission policy YAML v1 |
| MCP probe/estimate/run manifest and envelope | MCP manifest draft for Voidscape CLI tools |
| Snapshot/screenshot/navigate; no raw eval | Browser bridge tool contract |
| Repo/package/dedicated-repo ADR | Repository and package boundary; `docs/decisions.md` |
| Origin/localhost/injection/cross-profile threat model | Transport requirements and updated threat model |
| Never read credentials/cookies/storage/secrets | Decision summary, absent tools, checklist |
| Per-harness verification | Codex/ChatGPT and Claude plans |
| Security checklist complete before production issue | Completed design security review checklist |

## Pattern sources

- [screenpipe pipe permissions at reviewed commit](https://github.com/screenpipe/screenpipe/blob/31491984c8d162acd3521d9cf9d7b2f885db858b/docs/mintlify/docs-mintlify-mig-tmp/pipe-permissions.mdx): learn-from-only patterns for allow/deny rules, app/content filters, time windows, and session Bearer tokens. Voidscape does not adopt its permissive missing-policy default.
- [automated_browser `devel` recorder at reviewed commit](https://github.com/deaspo/automated_browser/blob/143434c93bdfe468d3bbc9979e782cb5aad2364b/src/classes/AIAgentBrowserRecorder.ts): learn-from-only session metadata and replay evidence. Voidscape does not adopt injected remote scripts, raw event archives, autonomous loops, or cloud page analysis.
- [Baseline Voidscape bridge contract](2026-08-28-harness-neutral-browser-bridge-design.md).
