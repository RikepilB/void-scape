# Consent-bound visual jobs: design contract

Status: **design only**. This document satisfies the pre-implementation scope of
[issue #93](https://github.com/RikepilB/void-scape/issues/93); it does not implement,
activate, or approve a scheduler. Local recording inbox scheduling remains in
[#56](https://github.com/RikepilB/void-scape/issues/56). Runtime delivery needs a
separate implementation issue and the acceptance evidence below.

## Selected first use case and transport

Detect a substantial visual regression in the **public Voidscape landing-page
capabilities section** after a deployment. This is layout/change evidence, not
proof that every feature works or that a deployment is correct.

The selected capture transport is the existing user-approved Chrome harness,
using its documented visible-page navigation and screenshot capabilities. This
choice approves no new extension, profile access, or background browser service.
The first pilot is user-observed. If that harness is unavailable, cannot enforce
the bounds below, or requires an interactive session unavailable to the runner,
the job stops. It does not fall back to a CLI, remote browser, Iris, or another
provider. Existing intermittent Chrome failures are not a passed runtime gate.

The future scheduler only requests a bounded capture from that transport. It
must not read cookies, credentials, storage, browser configuration, other tabs,
or network authorization headers. Production transport approval/pairing is a
dependency of [#58](https://github.com/RikepilB/void-scape/issues/58), not an
assumption that the isolated bridge spike is production-ready. Screenshot
provenance is separately tracked in
[#92](https://github.com/RikepilB/void-scape/issues/92).

## Proposed pilot policy, inactive until explicitly activated

These are proposed fixed limits, not an installed cron configuration. Activation
must display and record the exact policy, start/end instants, capture destination,
transport, and notification destination. Changing any scope or budget creates a
new policy version and invalidates its old approval.

| Field | First-pilot policy |
|---|---|
| Navigation allowlist | Exact `https://voidscape.club/` with optional `#capabilities`; no query string, alternate port, credentials, subdomain wildcard, or HTTP downgrade |
| Capture target | The capabilities section only, located by the existing `#capabilities` ID; missing or ambiguous target is a failure, not permission for a full-page capture |
| Redirects | No automatic off-allowlist navigation; any unexpected destination stops before capture. Require transport pre-navigation redirect enforcement; if unavailable, runtime gate fails |
| Page resources | Ordinary resources loaded by the approved public page are not a grant to navigate to them or export them; no interception, response-body collection, or recursive discovery |
| State | Default disabled; one explicitly approved, user-observed pilot before recurring activation |
| Cadence and timezone | At most once per hour; display `America/Santiago`, store UTC start/end and scheduled instants with the IANA zone and resolved offsets |
| Lifetime | At most 24 hours and 24 scheduled runs; no indefinite renewal or missed-run catch-up |
| DST/clock behavior | Hourly elapsed-time interval from approved UTC start; local repeated/skipped hours do not duplicate runs; refuse future timestamps or invalid clock ordering |
| Viewport and pixels | 1280 x 900 CSS pixels, device scale 1, fixed scroll target; one PNG per attempt, at most 1,152,000 decoded pixels and 8 MiB encoded bytes |
| Scope overflow | If the selected section exceeds the viewport, stop and request a narrower explicit region; no stitching, scrolling capture, resize, or silent crop |
| Runtime | 60 seconds total per scheduled run, including any retry; navigation at most 20 seconds, readiness at most 10 seconds, capture at most 10 seconds |
| Compute | One concurrent job; comparison at most 5 CPU-seconds and 256 MiB worker memory; exceedance terminates comparison without a success result |
| Retry | At most one transient capture retry after 5 seconds within the same 60-second budget; never retry scope, permission, provenance, auth, credits, or malformed-data errors |
| Spend | Zero paid API budget, zero model downloads, zero AI calls in the first pilot; browser availability is not an inference of free compute or subscription API credit |
| Storage | Local dedicated job directory outside the repository/vault, at most 64 MiB; no cloud sync destination or remote artifact upload |
| Retention | Delete raw captures/diffs after 24 hours; keep the approved baseline for the pilot lifetime only; keep redacted audit metadata at most 7 days |
| Notification | Local report only by default, one event per newly confirmed change signature; repeat unchanged state stays quiet; no email, social messages, or webhook |

Retention deletion is limited to a validated dedicated directory and files owned
by this job, with no symlink/reparse-point traversal. It never removes supplied
files, repository files, or arbitrary paths. If cleanup or storage limits cannot
be enforced, pause before another capture; report the failure without discarding
audit evidence silently. A local path under OneDrive is not automatically local-
only storage; the pilot must select an unsynced destination explicitly.

The browser may load untrusted public resources as a normal part of rendering.
This design does not claim a network-isolated browser. A stricter no-third-party-
egress deployment needs a separately reviewed transport/network policy.

## Lifecycle, permission, and failure semantics

`disabled -> approved -> running -> unchanged / candidate / failed -> paused / expired`

Every run validates the approval ID, policy hash, current time, remaining run and
byte budgets, pause/revocation marker, allowlist, and transport readiness before
navigation. Only one run holds the job lease. Each scheduled instant has a unique
run ID; restart/resume must not repeat completed captures or notifications.

Pause prevents new work. Revoke invalidates approval immediately and requests
cancellation of an in-flight capture; the worker checks revocation again before
retaining evidence, comparing, or notifying. Already-dispatched navigation cannot
be undone: the audit records cancellation timing and discards newly returned
pixels without publishing. Resume requires explicit approval after revocation,
expiry, a scope change, or any auth/budget error. No automated login, consent-
banner click, CAPTCHA handling, account mutation, or credential repair is allowed.

An auth wall, unavailable transport, missing credits, missing backend, invalid
provenance, blank capture, or timeout is **failed**, never **unchanged**. Missing
credits only becomes relevant if a separately approved AI phase exists; it must
stop that phase without automatic purchasing, quota reset, or provider fallback.
Deduplicate repeated failures in local notifications, but retain each run outcome
in the bounded audit. Emit a recovery event only after a valid successful capture.

## Deterministic comparison before AI

1. Validate capture size, decoded dimensions, source/final URL, policy/run IDs,
   viewport, region, and readiness evidence. Verify image SHA-256 locally. A
   producer assertion is not independently verified scope; mark unavailable fields
   unknown and fail the required-scope gate rather than inventing metadata.
2. Use one user-reviewed baseline captured with the identical policy. Never
   auto-promote an arbitrary latest image to baseline. A baseline change is a
   recorded explicit acceptance; it resets candidate history.
3. Exact image-content equality is unchanged. Otherwise compare decoded RGB
   pixels with per-channel tolerance 16/255, ignoring alpha only after compositing
   onto the same documented background. The changed-pixel ratio counts a pixel
   when any channel exceeds that tolerance.
4. A ratio at least 1% is a **candidate**, not automatically a regression. Confirm
   only after the next scheduled valid capture also differs from baseline by at
   least 1% and differs from the candidate by less than 0.5%. No extra unscheduled
   confirmation capture is permitted. Inconsistent candidates remain unconfirmed.
5. Invalid captures never reset or confirm a candidate. Report the change as
   unresolved if the pilot expires before confirmation. Label smaller differences
   below threshold explicitly, not as a proof of identical or correct UI.

Thresholds are initial fixture-test hypotheses, not measured production accuracy.
Font/readiness mismatch is a capture-quality failure. Do not inject page scripts
to disable animations or modify content in the live pilot; animated regions need
an explicitly selected stable region or the pilot fails readiness. Any future
mask must be reviewed, versioned, and applied identically to both images; never
mask security/privacy warnings to force a pass.

The local report contains baseline/current/diff hashes, UTC times, compared
region, ratios, policy version, quality caveats, and paths to retained evidence.
Use "confirmed visual change", not "broken feature", unless separate functional
tests establish the latter. Snapshot evidence does not establish what happened
between scheduled samples.

## Optional AI interpretation: separate approval, not a fallback

AI is unnecessary for initial detection and disabled for this pilot. A later
opt-in interpretation phase must first run Voidscape `inspect -> preview -> read`
on the bounded local baseline/current images. The controller fails closed on
nonzero exit, malformed JSON, `ok: false`, or missing permission/cost gates.

Approval must name the provider/model, exact two-image evidence set, destination,
maximum input/output token budget, maximum dollar spend, and approval expiry.
Cloud transfer and first model download require their own current explicit
approvals; an API key, signed-in browser, chosen provider, or subscription is not
either permission. Re-preview if the model, evidence, price, or gates change.
Never use additional tabs or private local files as context. No provider fallback
is permitted under this design.

Interpretation is advisory and cites only produced `[image N]` evidence. Images,
page text, titles, and metadata remain `content_trust: untrusted`; prompt-like
content cannot authorize tools, sends, budget increases, or policy edits. A model
cannot promote a baseline, clear a failure, follow links, or execute commands.

## Minimal local audit record

Persist a schema-versioned, append-only bounded event log: job/run ID, approval ID
and policy hash, UTC scheduled/start/end timestamps, transition/reason code,
transport identity/version, sanitized allowlisted source/final URL, image and
baseline hashes, dimensions, actual byte/pixel/elapsed/compute counts, comparison
result, retry count, revocation outcome, and notification deduplication key.
AI, if separately approved, adds model, approval IDs, estimate and actual usage
or explicitly unknown usage; never serialize keys, prompts with private material,
headers, cookies, browser profiles, or raw HTML. Restrict logs and artifacts to
the user's local access; do not commit or attach them to public CI/PRs.

Write complete artifacts atomically and associate only successfully validated
captures with comparison outcomes. Interrupted writes are not evidence. Bound log
growth under the same directory budget; audit-write failure pauses work before
further navigation. Retained metadata does not imply retained images still exist.

## Required evaluation before implementation can be released

Use synthetic fixture images/pages and a fake clock/transport first. Public live
captures are a separate user-observed pilot; do not use authenticated accounts,
personal screenshots, private feeds, or real credentials in tests. This document
defines tests; it does **not** claim those runtime tests have run.

| Fixture / injection | Required result |
|---|---|
| 20 identical and 20 sub-tolerance RGB pairs | Zero confirmed notifications; ratios reflect comparator definition |
| 20 stable >=1% changes, each repeated on next scheduled sample | All 20 confirmed on second sample; exactly one notification per signature |
| 20 one-sample animation/flicker changes reverting to baseline | Zero confirmed notifications; candidate outcome retained |
| 0.99%, exactly 1%, tolerance16 and17, exactly0.5% inter-sample difference | Exact threshold-boundary outcomes match documented strict/non-strict comparisons |
| Missing selector, oversize region, delayed font, blank/error page | Quality failure, no baseline promotion or unchanged outcome |
| Different viewport/scale, bad hash, absent required scope metadata | Provenance failure, no comparison or AI |
| Off-origin redirect, HTTP downgrade, userinfo/query/path tricks | Rejected before out-of-scope navigation; transport unable to enforce this fails release |
| Login wall, CAPTCHA, unavailable transport/provider/credits | Stop with explicit reason; zero account interaction or fallback calls |
| Timeout and transient retry; permanent failure | No more than two attempts; <=60s total; no retry for permanent failure |
| DST transition, clock rollback, overlapping ticks, restart, expiry | Unique bounded run IDs, no catch-up/duplicate notification; expired work rejected |
| Pause/revoke before capture and during capture/comparison | No new capture after pause; late result discarded after revocation; timing audited |
| Memory/CPU/disk limit, cleanup failure, symlink path, partial write | Fail closed within bounds; no unrelated deletion or accepted partial artifact |
| Screenshot text asking for secrets, commands, or new URLs | No action/policy change; all evidence stays untrusted |
| Optional AI denied/cloud denied/download denied and changed preview | Zero unapproved model/network calls; new preview requires new approval |

The fixture gate requires all deterministic assertions to pass, zero false
confirmed alerts in the 60 specified unchanged/transient pairs, and 20/20 stable
changes confirmed. Report counts with denominators, invalid-capture counts, p50/
p95 latency, peak memory, and stored bytes; no aggregate "accuracy" that hides
failures. Include known limitation: visual pixel thresholds can miss small
critical changes and can flag harmless large changes. Human review and functional
tests remain necessary.

## Delivery boundaries

Issue #93 can close when this bounded design is reviewed and merged. A follow-up
implementation must demonstrate policy validation, cancellation, provenance,
bounded storage/comparison, fixture results, and a permitted observed pilot before
any recurring activation. Until then, public capability wording stays exploration
or design-only. Iris and the Codex plugin retain their existing STOPPED / DO NOT
INSTALL statuses; no malware finding is asserted by this document and no warning
is suppressed. No cron job, browser extension, MCP server, model, or companion
repository is created by approving this design.
