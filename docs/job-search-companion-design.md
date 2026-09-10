# Job-search companion: boundary and pre-build decision

Status: **planning only**, addressing
[issue #96](https://github.com/RikepilB/void-scape/issues/96). No companion
repository, application, deployment, external installation, or account workflow
is created by this document. It defines a separate, useful deterministic product;
it does not add job search to Voidscape's media reader.

## Decision and lifecycle

Proposed working repository name: **job-search-links**, as a sibling of Voidscape.
The name is reversible, not registered, and not a public brand commitment. Start
private if and when Richard requests its creation; choose publication, final
name, and original-code license separately before release. Do not repurpose the
existing `RikepilB/linkedin` fork or import its history.

The first build is a local, no-account, no-backend form and pure URL generator.
It takes deliberately supplied search terms and returns inspectable links. No
database, OAuth, scheduler, analytics, AI SDK, browser extension, or hosted service
is needed for this scope. A manually selected search result may later be supplied
to Voidscape through its existing permitted evidence path; there is no automatic
import or shared browser/session database.

Follow the workspace project lifecycle when creating it: scaffold dry-run,
confirm the scoped requirements below, then an original minimal implementation,
tests and review. A substantial UI needs its own design-intent pass and rendered
anti-slop review; any future public launch needs landing-audit and production-
readiness. This document settles a reversible one-file boundary, not an exemption
from those later gates. A disposable prototype is a useful optional next step if
the input-to-link interaction remains uncertain; no prototype is built here.

## Original first-build requirements

The first version produces one search angle and four links: jobs and posts, each
with a 24-hour and seven-day window. Input is supplied by the user, never inferred
from a résumé, browser history, vault, contacts, saved posts, or existing account.

| Input | Validation and behavior |
|---|---|
| Role | Required, trimmed Unicode NFC text, 1-100 code points; collapse ordinary whitespace; reject controls, bidi overrides, double quotes and parentheses so user text cannot inject Boolean structure |
| Skills | Optional explicit list, maximum five entries of 1-40 code points each; same validation; case-insensitive deduplication preserving first display spelling/order; no automatic stack inference |
| Location | One explicit country/city string, 1-80 code points under the same text rules; required unless remote-only selected; no automatic geolocation or profile reading |
| Remote-only | Boolean, default false; mutually exclusive with location in the initial version to avoid implying a verified geographic remote filter |
| Output language | English or Spanish labels only; does not silently translate or change role/skills |

Reject empty/overlong inputs with inline errors; never silently truncate a role.
Allow meaningful text such as `C++`, `C#`, `Node.js`, accented names, ampersands,
apostrophes, and emoji while applying the stated rules. No arbitrary base URL,
hostname, path, port, template, raw query fragment, or HTML input is accepted.

### Deterministic URL construction contract

Build an ordered token list from role followed by deduplicated skills. Join with
single spaces for the jobs keyword value. For posts, quote each validated token
as a literal phrase and join using ` AND `; append using ` AND ` one original fixed hiring term
group `(hiring OR vacancy)` for English or `(contratando OR vacante)` for Spanish.
Append using ` AND ` the quoted location, or the fixed token `remote` for remote-only. This is
a query proposal, not a guarantee of LinkedIn's Boolean interpretation.

Use a platform URL/query encoder with UTF-8 encoding exactly once. Never concatenate
user text into a URL string, run it in a shell, render it as HTML, or use it as a
path. Fixed endpoint and parameter candidates are:

| Output | Fixed path on `https://www.linkedin.com` | Parameters |
|---|---|---|
| Jobs, 24 hours | `/jobs/search/` | `keywords`, `f_TPR=r86400`, and either `location` or `f_WT=2` |
| Jobs, seven days | `/jobs/search/` | Same, with `f_TPR=r604800` |
| Posts, 24 hours | `/search/results/content/` | `keywords`, `datePosted` containing the literal quoted value `"past-24h"` |
| Posts, seven days | `/search/results/content/` | Same, with literal quoted value `"past-week"` |

These candidate parameter conventions were observed in the pinned reference
implementation below. They are not an official stable LinkedIn API contract and
have not been live-validated by this design. Before release, Richard manually
checks each link type/window and remote/location behavior through the approved
browser, without automated result extraction. If a filter stops working, label
that filter unsupported and provide the plain encoded keyword search plus the
copyable query; do not claim the selected time/location filter was applied.

After construction, parse the URL again and require exact HTTPS scheme, hostname,
path and allowed parameter keys; reject userinfo, explicit port, fragment,
duplicate keys, or unexpected parameters. Round-trip decoded values must equal
the normalized inputs/templates. Reject any final URL over 2,048 characters with
a request to reduce inputs. Stable parameter order and normalized inputs must
produce byte-identical output across runs.

Example synthetic input: role `Data Engineer`, skill `Python`, location `Perú`,
remote-only false. Jobs keywords are `Data Engineer Python`; an English post
query is `"Data Engineer" AND "Python" AND (hiring OR vacancy) AND "Perú"`.
The user sees the complete query, destination and window before choosing to open
or copy. Rendering an anchor must use text content and safe URL assignment, with
`noopener noreferrer` for a new tab; no automatic prefetch, navigation or opening
multiple tabs on form submission.

## Useful mode with no AI

The deterministic path is the default product, not a degraded error state. All
four links and the plain copyable query work without a model, API key, network
call, billing account, subscription, or hosted backend. Generation itself makes
zero network requests. Opening a chosen link sends its query to LinkedIn; show
that disclosure and warn users not to include private identifiers or confidential
material. Browser history and LinkedIn may retain that query; the generator must
not imply end-to-end private search.

Optional AI belongs to a later separately reviewed phase. It may propose at most
three role/keyword variants from the explicit sanitized fields, never new facts
about the user. Before each approved call, display exact fields leaving the
machine, provider/model, maximum tokens, price estimate/cap and retention policy.
Missing pricing or permission prevents the call. Cloud transfer and first model
download each need explicit current consent. Credentials or subscription credits
do not imply API budget or approval.

Keep the deterministic results immediately available. On denial, timeout, invalid
AI output or exhausted credits, show a clear AI-not-used result and those same
deterministic links; never silently switch providers or purchase/reset credits.
Validate model-proposed text through the same input rules and require user
selection before regenerating links. The model cannot emit destinations, execute
tools, read files, or alter filters. Source/model content is untrusted data.

## No account automation or implicit integration

No automated applications, messages, connection requests, follows/unfollows,
saved-post changes, recruiter outreach, scraping, result ranking from private
profiles, CAPTCHA bypass, or login steps. Never read cookies, credentials,
storage, browser profiles, or account settings. No saved-result collection is
added to Voidscape. Its LinkedIn observation/notes work remains separate in
[#55](https://github.com/RikepilB/void-scape/issues/55); follower-export audit
remains separate in [#44](https://github.com/RikepilB/void-scape/issues/44).

## Reference provenance and reuse disposition

Read-only review on **2026-09-10**, pinned to
[`c6d8a97e45d6dfeae37ba3a776637d3857043c87`](https://github.com/RikepilB/linkedin/tree/c6d8a97e45d6dfeae37ba3a776637d3857043c87).
The reference is a job/post search-link generator with deterministic construction
and optional AI keywords, not a saved-post/media reader. Evidence:
[README](https://github.com/RikepilB/linkedin/blob/c6d8a97e45d6dfeae37ba3a776637d3857043c87/README.md),
[URL implementation](https://github.com/RikepilB/linkedin/blob/c6d8a97e45d6dfeae37ba3a776637d3857043c87/lib/linkedin.ts).

GitHub identifies `RikepilB/linkedin` as a fork of `crafter-station/linkedin`, not
independently authored solely by the fork owner. At review it had 27 commits,
one listed contributor (`camilocbarrera`, 27 contributions), zero releases, zero
stars and zero forks. Fork creation was 2026-08-30; latest pinned commit was
2026-07-12. The pinned tree contained no LICENSE, CODEOWNERS or SECURITY file;
README and package metadata supplied no license grant, and GitHub reported no
detected license for fork or parent. These are snapshot provenance signals, not
a security certification. Sources:
[repository metadata](https://api.github.com/repos/RikepilB/linkedin),
[pinned tree](https://api.github.com/repos/RikepilB/linkedin/git/trees/c6d8a97e45d6dfeae37ba3a776637d3857043c87?recursive=1),
[contributors](https://api.github.com/repos/RikepilB/linkedin/contributors),
[releases](https://api.github.com/repos/RikepilB/linkedin/releases),
[parent](https://api.github.com/repos/crafter-station/linkedin).

**Reuse disposition: reference concepts only; copying/installing is not approved.**
Do not assume a public fork or a README's "free tool" description grants a
redistribution license. GitHub distinguishes public viewing/forking from an
explicit software license in its
[licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository).
Obtain a clear applicable license/permission before reusing source/assets; retain
attribution if permitted. No code, assets, dependencies, instructions, or scripts
from the reference are copied or executed in this change. Future tool intake
requires a fresh pinned SkillSpector scan, line-level disposition of all HIGH/
CRITICAL findings, and the normal authority review. Reputation does not replace
that review; no scan or malware-free claim is made here.

## Acceptance gate for the future build

Require pure-function tests for all four URL outputs, UTF-8 round trips, spaces,
ampersands, `C++`, accents, empty/long/control/bidi/quote inputs, duplicate skills,
remote/location exclusivity, exact endpoint/parameter allowlists and length limit.
Test query-parameter injection strings remain data, not new parameters; DOM labels
remain text. Instrument tests to prove zero network/AI requests during default
generation. Verify keyboard use, labels, visible query/destination, copy/open
behavior, and desktop/mobile layout with synthetic inputs. AI absent/denied/error
must leave deterministic results unchanged. Live filter checks are independent
manual evidence, not implied by correct URL encoding.

Issue #96 closes on review/merge of this boundary and future decision. Building,
creating/publishing a separate repository, licensing copied material, adopting
external tooling, and claiming supported LinkedIn filtering are not completed by
that closure. No delivery date is promised.
