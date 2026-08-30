# Voidscape MCP host spike

**Date:** 2026-08-29

**Status:** Complete — no-go for a production MCP host in the current repository

**Issue:** GitHub #26

## Recommendation

Do not add an MCP server, SDK dependency, package metadata, or host configuration to `void-scape`
now. The shell CLI remains canonical. Its three readers already expose the needed non-interactive
`manifest`, `probe`, `estimate`, and `run` commands with the same `{ok,data,error,meta}` envelope.

The official Python MCP SDK is the best implementation choice if evidence later justifies a host,
but it should live in an optional sibling `voidscape-mcp` repository/package and use local stdio
only. It must never be copied by the existing skill installer or become a dependency of media reads.

This is a product/distribution no-go, not a claim that MCP is technically unsuitable. The marginal
tool-discovery benefit does not currently repay a second runtime contract, a young fast-moving SDK,
a broad dependency tree, host-specific consent behavior, and a second support surface.

No production server merged as part of this spike.

## Evidence snapshot

Research was refreshed on 2026-08-29 against primary sources:

- The official Python SDK's current stable release is `v2.1.1` (2026-08-25), requires Python 3.10+,
  and supports stdio, Streamable HTTP, and SSE.
- Its base package declares `anyio`, `httpx2`, `mcp-types`, `pydantic`, `starlette`,
  `python-multipart`, `sse-starlette`, `uvicorn`, `jsonschema`, `pyjwt[crypto]`, typing helpers,
  OpenTelemetry, and Windows `pywin32` among its direct runtime requirements. The optional CLI adds
  Typer and dotenv.
- The official TypeScript SDK supports a focused stdio server package, but would add Node, npm,
  TypeScript/build output, and another supply chain to a Python-standard-library project.
- The 2026-07-28 protocol revision changed lifecycle and consent-related mechanics: it removed the
  old handshake/session model, introduced discovery and multi-round-trip input, and moved identity
  into request metadata. A hand-written JSON-RPC subset would have to track that evolution.
- MCP tool execution errors belong in a tool result with `isError: true`; malformed protocol/tool
  invocation is a JSON-RPC error. Stdio reserves stdout for protocol messages and permits logs only
  on stderr.

Voidscape has no `pyproject.toml`, `setup.py`, or requirements file. Its installer copies the skill
tree directly and its cloud calls intentionally use the standard library. Adding the SDK is not a
small internal import; it changes installation, upgrades, vulnerability handling, and judge setup.

## Options considered

| Option | Protocol fit | Repository fit | Decision |
| --- | --- | --- | --- |
| Official Python MCP SDK v2, stdio | Best: official Tier 1 SDK, Python 3.10+, schemas/transports handled | Poor in current skill; acceptable as optional sibling package | Preferred only if revisit gates pass |
| Official TypeScript SDK v2, stdio | Strong official implementation and focused server package | Poor: adds Node/npm/build and splits implementation language | Reject for Voidscape |
| Hand-written stdlib JSON-RPC/MCP subset | Keeps zero third-party Python dependencies | Unsafe maintenance burden during protocol churn; easy to mishandle lifecycle and errors | Reject |
| Thin HTTP/loopback server | Works across processes | Adds bind/auth/CORS/port lifecycle without a need for remote service | Reject; local stdio only if revisited |
| Existing shell CLI | Already shipped, tested, inspectable, scriptable, and envelope-stable | Exact project fit | Keep canonical |

## Why no-go now

1. **No demonstrated gap.** Agents with shell access already discover reader manifests and receive
   structured envelopes. No issue contains evidence that manual subprocess invocation blocks a real
   workflow.
2. **Consent remains host-specific.** MCP can carry structured results, but only the harness owns a
   trustworthy user-confirmation UI. A server cannot infer consent from a retry, API key, previous
   job, or generic tool authorization.
3. **Distribution cost is disproportionate.** The official Python SDK is the correct SDK but would
   turn a copied stdlib skill into a packaged dependency graph. Installing `[cli]` would add still
   more development-only dependencies.
4. **A custom protocol implementation is worse.** Recent lifecycle changes demonstrate why a
   hand-rolled subset would become a compatibility and security liability.
5. **No universal-host result is possible.** A passing Codex, Claude, VS Code, or Cursor integration
   proves only that host/version. Support, prompts, result rendering, and approval UX differ.

## Minimal future contract

If the revisit criteria are met, the first optional host exposes exactly three tools from the #25
manifest draft:

| MCP tool | Reader command | Purpose |
| --- | --- | --- |
| `voidscape_probe` | selected reader `probe --envelope --compact` | Free source facts; no processing |
| `voidscape_estimate` | selected reader `estimate --envelope --compact` | Cost, dependency, and approval fields |
| `voidscape_run` | selected reader `run --envelope --compact` | Exact preflighted job only |

Reader selection is an enum mapped to fixed `video.py`, `image.py`, or `article.py` paths. The host
uses an argv list with `shell=False`, a sanitized environment allowlist, bounded stdout/stderr, and a
timeout. It returns the CLI envelope as MCP `structuredContent` and a short equivalent text content
block. It does not expose browser, shell, cookie, storage, arbitrary-path browsing, or approval tools.

`manifest` is not a fourth model-facing tool: MCP's tool listing is the discovery surface. The host
may call reader `manifest` internally at startup to verify protocol `1.0` and fail closed on drift.

## Approval and error mapping

The future host must preserve a visible two-call boundary:

```text
voidscape_estimate
  -> ok: true
  -> data.requires_cloud_approval / data.needs_model_download
  -> host shows the exact job and obtains current user consent
  -> voidscape_run with only the approved boolean(s)
```

- `estimate` is a successful tool call even when approval is required; the approval fields are data,
  not an exception.
- `run` without required consent executes the unchanged CLI without approval flags. Exit 4 becomes an
  MCP tool result with `isError: true` and the exact sanitized `approval_required` envelope in
  `structuredContent`.
- CLI exits 3, 5, and 6 are also tool execution errors with `isError: true`. They remain visible to
  the model for correction but never include raw secret-bearing stderr.
- Unknown tools, malformed JSON-RPC, and arguments rejected before CLI dispatch are protocol errors.
- Exit 1 returns a generic tool execution error; internal exceptions and command lines are not shown.
- The first version does not use MCP multi-round-trip input/elicitation to block inside `run`.
  Separate estimate and run calls work across more hosts and keep consent explicit and auditable.
- A tool-call permission granted by the host is not cloud or model-download consent. No retry may
  auto-add `allow_cloud` or `allow_model_download`.

The #25 `preflight_id` remains a future host requirement: it binds reader, normalized input,
cost-affecting arguments, host identity, and a short expiry. It is single-use for `run`; mismatch,
replay, expiration, or cross-host use fails before subprocess execution.

## Placement if revisited

Use a sibling repository and optional distribution:

```text
voidscape-mcp/
  pyproject.toml          # pinned official Python MCP SDK major
  src/voidscape_mcp/      # stdio host and fixed CLI adapter
  tests/                  # subprocess contract and host fixtures
  SECURITY.md             # reporting, supported versions, threat boundary
```

The package accepts an explicit path to an installed Voidscape skill. It does not vendor or modify
the reader scripts, install models, configure API keys, expose HTTP, or ship browser control. The
`void-scape` repository would keep only a link and per-version compatibility evidence.

## Revisit gates

Open a new implementation proposal only when all are true:

1. Two named MCP-capable harnesses have a documented need that shell invocation cannot meet.
2. A disposable adapter proves tool listing, structured envelope round-trips, cancellation/timeouts,
   and stdout isolation on Windows plus one Unix target.
3. Each target harness proves its own estimate-to-user-confirmation-to-run flow for both approval
   fields; one host's evidence is not reused for another.
4. The maintainer accepts a sibling package, dependency lock/update policy, vulnerability ownership,
   and separate release cadence.
5. Security review approves fixed argv dispatch, environment/path boundaries, preflight replay
   protection, output sanitization, and the absence of browser/credential tools.

Until then, no follow-up implementation issues should be opened. The alternative is the supported
shell flow documented in `docs/agents/automation.md` and each reader's `manifest` command.

## Verification plan for a future proposal

- Contract-test all three readers with fake subprocesses and exact argv assertions.
- Exercise CLI exits 0 through 6 and verify MCP protocol error versus tool `isError` mapping.
- Corrupt stdout deliberately and require fail-closed parsing; ensure host logs use stderr only.
- Prove approval flags are absent until the matching estimate and current user confirmation.
- Reject reused, mismatched, expired, or cross-host `preflight_id` values.
- Verify installed-skill upgrades that change protocol version prevent host startup.
- Run the official MCP inspector only from a pinned development environment; never make `npx` part
  of the user runtime.
- Record separate Codex/ChatGPT, Claude, and any other host/version results without universal claims.

## Acceptance mapping

| Issue #26 question | Spike answer |
| --- | --- |
| Which SDK/runtime fits? | Official Python MCP SDK v2 over stdio, but only in an optional sibling package if revisited |
| How do approvals surface? | Estimate data first; missing run consent is `isError: true` with the exact exit-4 envelope; never a blocking hidden retry |
| Repo, package, or sibling? | Sibling repository/package; current repo keeps CLI and reference evidence |
| Minimal v1 tools? | `voidscape_probe`, `voidscape_estimate`, `voidscape_run` |
| Go/no-go? | No-go now; shell CLI remains canonical |
| Production server merged? | No |

## Primary sources

- [Python SDK v2.1.1 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.1.1).
- [Python SDK runtime metadata at reviewed commit](https://github.com/modelcontextprotocol/python-sdk/blob/d2290ca3434731b68ea3e2270bc06a6e6575931b/pyproject.toml).
- [Python SDK documentation](https://github.com/modelcontextprotocol/python-sdk/blob/d2290ca3434731b68ea3e2270bc06a6e6575931b/docs/index.md).
- [TypeScript stdio server documentation at reviewed commit](https://github.com/modelcontextprotocol/typescript-sdk/blob/70de0c8b569b0d664a56b90be2f141d1d1645880/docs/serving/stdio.md).
- [Official 2026-07-28 protocol revision summary](https://blog.modelcontextprotocol.io/posts/2026-07-28/).
- [MCP tool error and security contract](https://modelcontextprotocol.io/specification/2025-06-18/server/tools).
