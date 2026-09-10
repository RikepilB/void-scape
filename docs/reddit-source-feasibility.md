# Reddit saved-source feasibility

Design-only checkpoint for [issue #95](https://github.com/RikepilB/void-scape/issues/95),
2026-09-10. No adapter, skill, API application, account capture or live pilot is
implemented or approved by this document. X and TikTok remain separate exploration;
LinkedIn belongs to #55.

## Proposed first use case and unresolved selection

Propose a local, read-only inventory of **at most 10 saved Reddit posts** selected
by the user for personal media reading. Comments, feeds, follower profiling and
whole-account archives are excluded. The supplied Reddit homepage is not a
selected saved collection. Before implementation, record the exact user-selected
file or collection, item bounds, allowed read path and private output destination.
These values are currently **not supplied**; do not infer a username or browse an
account to fill them in. Issue #95 cannot close on this proposal alone.

## Access options reviewed

The following primary documentation was read on 2026-09-10. Recheck policy and
approved-use scope before adopting any network route; this is a technical intake
decision, not legal clearance.

| Option | Evidence and constraint | Decision for this proposal |
|---|---|---|
| User-supplied export subset | Reddit offers an account-data request, with preparation potentially taking up to 30 days. The help page does not guarantee a saved-post filename/schema or complete media payload. | Preferred candidate: user supplies only selected post records. Validate actual schema first; never read the complete archive by default. |
| Official Data API | The saved listing is documented under `/user/username/where` with `history` scope and listing cursors. Endpoint documentation does not grant access. | Deferred: requires Reddit approval, correct account authorization and a separate token-handling design. No credentials requested or inspected here. |
| Visible browser observation | A signed-in browser proves neither collection selection nor platform permission for automation. | No automated scraping or API-bypass fallback. A user-observed pilot needs selected scope plus a current platform-policy disposition; alternatively use manually supplied observations. |

Export facts: [Reddit account-data request guide](https://support.reddithelp.com/hc/en-us/articles/360043048352-How-do-I-request-a-copy-of-my-Reddit-data-and-information).
API facts: [official API documentation](https://www.reddit.com/dev/api/#GET_user_{username}_{where}).

Reddit's [Responsible Builder Policy](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy)
requires explicit API approval and limits access to permitted purposes. It also
restricts scraping/mining and sensitive-person profiling. Therefore browser
automation is not an assumed workaround when API access is absent. No training,
commercialization or identity enrichment is part of this use case.
The [Data API Terms](https://redditinc.com/policies/data-api-terms) additionally
limit permitted access, retention and commercial use. A future API route must
document retention/deletion obligations before storing content; local-first does
not mean indefinite retention or permission to republish others' content.

## Proposed deterministic contract

This design specializes the [source triage contract](source-triage-contract.md).
It does not adopt the remove-saved example from the lower-level queue contract:
**every account mutation is out of scope**, even after a verified note.

- **Identity:** use `reddit:t3_<base36-id>` for posts. Reddit's documented
  fullnames distinguish posts (`t3`) from comments (`t1`); reject comments for
  this first scope. Require an observed post fullname or an unambiguous approved
  Reddit post permalink; conflicting IDs stop processing. Do not identify by
  title, author, outbound media URL or row number.
- **URL handling:** permit only explicitly supported Reddit post URL shapes;
  reject userinfo, deceptive hosts, collection URLs and unresolved share links.
  Preserve source and normalized URL separately. Strip only reviewed tracking
  parameters, never identity/content parameters. Do not resolve links during
  local inspection. A crosspost has its own post identity.
- **Bounds:** maximum 10 selected records, no pagination or expansion during
  the first local pilot. Reject oversize input before processing rather than
  silently capturing the entire account. A future API design must bound pages,
  requests and time; an `after` cursor is not snapshot completeness.
- **Dedup:** compare canonical keys against the selected batch, queue and
  reverified notes. Queued is not analyzed; stale or missing note evidence
  cannot suppress required reading. Preserve explicit duplicate dispositions.
- **Dry-run:** inspect and preview return proposed work only: zero disk writes,
  network requests, account actions or cloud transfer. The first approved write
  batch uses durable append, reread and identity verification.
- **Checkpoint:** record source key, stage, input-subset hash, verified artifact
  relative path/hash and failure reason. Stages distinguish selected, queued,
  evidence-ready, note-verified and skipped. Resume revalidates the selected
  input and artifact; never stores reusable approval. Partial write stops the
  batch, retaining already verified artifacts without claiming full success.
- **Evidence:** retain only the approved subset and necessary provenance in the
  chosen private destination. Record observation time, source permalink, known
  author/date or null, static/incomplete status and `content_trust: untrusted`.
  Titles/instructions inside a post cannot authorize tools. Inventory evidence
  is not a transcript. Read one permitted media item through
  `inspect -> preview -> read`; use only actual manifest citation labels.
  Unsupported article/media paths produce an explicit skip, not guessed notes.
- **Stops:** login/CAPTCHA, unavailable/deleted/private content, unknown schema
  or layout, identity ambiguity, off-scope redirect, permission failure and
  verification failure. No hidden network inspection, cookie/storage access,
  paywall bypass, retries around denial, follows, unfollows, unsaves, votes,
  subscriptions, comments, messages or sends.

## Independent evaluation and pilot gate

Before any source skill is called available, its eval workspace must contain
synthetic fixtures, named assertions, actual outputs, reviewer grades and a
benchmark distinguishing helper tests from harness behavior:

| Test group | Required evidence |
|---|---|
| Identity and selection | Same post/different title dedups; distinct crossposts do not; comments, conflicting IDs, spoof hosts, traversal and over-limit input fail closed. |
| Adversarial content | A title asking to leak secrets or unsave posts stays inert; HTML/script content is never executed. |
| Lifecycle | Dry-run disk/network/action counters stay zero; queued is not analyzed; partial write retains prior artifacts; stale checkpoint/hash mismatch requires revalidation. |
| Missing access | Login, CAPTCHA, changed layout, deleted/private post, redirect and missing consent stop without alternate access attempts. |
| Harness behavior | An independent evaluator runs normal and hostile prompts in each claimed Codex/Claude/Agents target, records tools and outputs, and compares with a no-skill baseline. Mirror text alone is not parity. |

After scope and policy gates pass, the user-observed pilot first previews up to
10 supplied observations without writes. With current approval, retain the
selected local inventory and read at most one supported permitted item. Compare
source identity and citations to retained evidence; record explicit skips and
limitations. Verify zero account mutations and no unapproved transfers/model
downloads. Report selected, queued, evidence-ready, note-verified and skipped
counts separately. A mocked browser run is not live acceptance.

## Issue acceptance status

- [ ] Concrete user-owned file/collection and bounds selected: blocked on input.
- [x] API/export/browser alternatives and primary platform constraints reviewed.
- [x] Proposed IDs, bounds, dedup, checkpoints, stops and evidence specified.
- [x] Independent harness evaluation and user-observed pilot gates defined.
- [x] Account mutation, credential access and paywall bypass excluded.

No pilot or tests of a Reddit adapter have run: there is no adapter in this PR.
This document advances #95 but does not close it or promote a shipped capability.
