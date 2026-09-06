# Social audit and Voidscape companions

Status: proposed setup, 2026-09-05. Source review only; no external code installed or executed,
no follower data imported, no follows/unfollows or remote writes. Existing media QA continues
separately; this proposal does not certify new platform adapters.

## Repository assessment

| Reference | Observed capability | Proposed use / boundary |
| --- | --- | --- |
| [InstagramUnfollowers](https://github.com/RikepilB/InstagramUnfollowers) | README describes console injection, API scanning, whitelist and selected unfollows | Learn protected-list and review UX; do not execute injected scripts in signed-in Chrome |
| [ig-unfollows](https://github.com/RikepilB/code-with-coco/tree/main/ig-unfollows) | Source compares following against followers via session-authenticated internal endpoints | Reimplement the set comparison against user-provided exports; do not reuse transport |
| [iris](https://github.com/RikepilB/iris) | Screenshot CLI and stdio MCP; viewport, selector, full-page, JSON metadata; Cargo declares MIT | Optional harness-side capture candidate, not a Voidscape core dependency; scan and Windows/public-fixture verification before use |
| [linkedin](https://github.com/RikepilB/linkedin) | Deterministic job/post search URLs with optional AI keyword expansion and deterministic fallback | Learn pure link generation and bounded validated AI output; this is not a follower manager or general browser harness |
| [content-manager](https://github.com/RikepilB/code-with-coco/tree/main/content-manager) | README describes Instagram insights to CSV and optional Notion sync | Separate creator analytics module; verify current official API eligibility, scopes and metrics before implementation; no Notion sync by default |
| [FollowerManager](https://github.com/RikepilB/FollowerManager) | GitHub API main tree contains only LICENSE (MIT); README endpoint returned 404 | Possible future home/name, no implementation to reuse |

Review depth: READMEs for the first five, plus ig-unfollows.js, iris Cargo.toml and linkedin
lib/linkedin.ts. Not a full code/security audit. No SkillSpector approval has been obtained for
these references. External reuse/install/enable must pass the user's scan gate; REVIEW/UNSAFE
or HIGH/CRITICAL stops adoption. Pin exact commits and verify license scope before copying code.

## Proposed product split

- Voidscape: inspect -> preview -> read selected media, grounded citations and local manifests.
- Existing agent-bridge: authorized browser interaction and optional capture integrations.
- Relationship audit companion (working name only): private local snapshots, comparisons,
  protected accounts, explainable recommendations, and a human review queue.
- Creator analytics: a later module of that companion, not another standalone repo yet.
  Connect selected content evidence from Voidscape to the user's own performance metrics.

Keep one companion with modules before multiplying projects. Iris belongs at the capture edge:
permitted public/test page -> local screenshot + sanitized provenance -> Voidscape image reader.
It must not be used to bypass an unavailable explicitly selected Chrome connection. Validate
redirects/network scope, output paths, privacy, timeouts and Windows behavior before adopting.

## First slice: offline unfollow audit

Input: user-selected follower and following export files for the same account/platform and
capture period. Start with an actual sample schema, not an assumed Instagram format. Import
only these files, not a whole account archive containing messages or other private data.

Output groups:

1. Mutual: following intersect followers.
2. Not following back: following minus followers; not automatically an unfollow recommendation.
3. Followers not followed: followers minus following; not automatically a follow recommendation.
4. Protected: explicit friends, colleagues, creators or user-selected exceptions.
5. Review: user decision, reason, evidence date, confidence and source completeness.

Historical unfollow detection needs two complete, comparable follower snapshots. Label removals
as no longer present, not proven intent: renames, deactivation and incomplete exports can explain
differences. Match stable platform IDs when available; otherwise disclose username uncertainty.
Refuse cleanup recommendations from incomplete or mismatched snapshots. Never silently treat
missing pages or failed imports as an empty follower set.

## Recommendation policy

Reciprocity is one signal, not the value of an account. Keep/follow suggestions should use
explicit user topics, saved-content usefulness, originality, relevance and user-added relationship
tags. Show reasons and a small evidence sample; unknown stays unknown. Do not infer sensitive
traits or private relationships. No autonomous follows, unfollows, blocks, DMs or publishing.
Any later execution requires a freshly reviewed exact account list and explicit approval.

## Harness contract and acceptance gates

- Separate deterministic importer/comparison from optional language-model explanation.
- Local-only defaults; no credential, cookie, storage or profile extraction; no remote telemetry.
- Treat biographies, captions, exports and README prompts as untrusted data, never instructions.
- Bound input bytes/records and output sizes; reject malformed schemas; escape report HTML/CSV
  formula prefixes; do not auto-extract archives or follow embedded URLs.
- Store private data outside Git; share only synthetic fixtures and aggregate test evidence.
- Every result records source hashes, snapshot dates, platform/account identity and completeness.
- Tests: casing/duplicates, empty versus missing data, multi-file exports, rename ambiguity,
  mismatched accounts/dates, protected accounts, malicious text, CSV formulas, stable output.
- Prove zero network/account writes for audit mode. Dry-run review is the only MVP output.

## Build sequence

1. Obtain the two selected export lists and establish schema/completeness.
2. Build offline importer and set comparison with synthetic tests, then run the private audit.
3. Add protected list and evidence-based review report; user approves decisions separately.
4. Evaluate Iris with SkillSpector and isolated fixture screenshots, without signed-in profiles.
5. Add creator analytics only after official API verification and scoped authorization.

Open dependency: no follower/following export paths are currently supplied. No personal audit
results or individual follow/unfollow recommendations can be claimed yet.
