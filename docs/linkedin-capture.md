# LinkedIn observed-post capture

Development helper for issue55, not a complete saved-posts triage skill. It accepts
synthetic or user-supplied permitted observations. Any future service acquisition
must satisfy the [source-scope gate](linkedin-source-scope.md); a signed-in browser
alone does not establish permission. It does not open LinkedIn, enumerate saved items, read credentials, or unsave
anything. The separate [verified publisher](triage-store.md) can now bind a draft
note to the retained observation and update the managed index.

## Identity and scope

`scripts/linkedin_capture_helper.py` recognizes explicit `activity`, `share`, and
`ugcPost` URNs, corresponding HTTPS feed/update URLs, and post URLs with an
explicit activity marker. Those identity types remain distinct. Event/job page
IDs, shorteners, collection pages and unsupported URL shapes are rejected without
following links. Tracking parameters `utm_*` and `rcm` are removed; unknown query
parameters and fragments are rejected rather than silently broadening scope.

Different post identity types are not assumed to be aliases. A future verified
mapping may relate them; this helper deliberately does not invent that mapping.

## Observation and commands

The input is a bounded local JSON file with exactly these fields. This example is
synthetic, not evidence of a real post:

```json
{
  "url": "https://www.linkedin.com/feed/update/urn:li:activity:7341234567890123456/",
  "text": "Synthetic visible post text.",
  "author": null,
  "date": null,
  "observed_at": "2026-09-10T03:00:00Z",
  "kind": "post"
}
```

`text` is nonempty visible text, at most128 KiB UTF-8. `author` and `date` are
observed strings or null, not inferred values. `observed_at` requires a timezone
and is caller-reported capture time, not an authenticated timestamp. `kind` is
post/article/job/event content attached to the validated post identity; it cannot
turn an event URL into an activity URL. Total encoded record size is bounded to
256 KiB. Page text and metadata always remain untrusted.

```powershell
python scripts/linkedin_capture_helper.py inspect 'urn:li:activity:7341234567890123456'
python scripts/linkedin_capture_helper.py capture observation.json --root captures
python scripts/linkedin_capture_helper.py capture observation.json --root captures --apply
python scripts/linkedin_capture_helper.py retained 'urn:li:activity:7341234567890123456' --root captures
```

The default capture command is a preview and writes nothing. `--apply` explicitly
selects local writes; the calling agent must still establish authorization for the
observed content and destination. No input field or stored artifact grants approval.

## Durable state and recovery

Each canonical typed identity has a hashed directory under `.linkedin-capture`.
The helper writes `entry.json` exclusively, flushes/syncs through the shared store
primitive, reads it back and verifies its hash, then writes `captured.json` and
revalidates both files. The immutable marker is the per-item capture checkpoint.
The shared root lock serializes applied captures; paths reject symlink traversal.

`retained` checks only the supplied 1..100 unique identities. It distinguishes
`captured`, `incomplete` and `missing`, with no capture-directory or account enumeration
and no writes. Captured means a verified local observation, never analyzed.

A retry with identical data can finish an interrupted capture. A conflicting
partial entry stops; a completed duplicate keeps the original and reports changed
observation metadata/text without overwriting. Source edits and deletions are not
tracked remotely. Hash verification detects file changes; it does not prove the
truth of caller-supplied text or capture time. Results never authorize unsaving.

## Verification and remaining acceptance

The initial 47 synthetic tests cover aliases, typed identities, rejected scope,
schema/size bounds, dry-run, complete/partial duplicates, corruption, failed
read-back, selected resume, symlink rejection, and CLI behavior. Measured helper
statement/branch coverage is 100%; this is not browser or independent agent QA.

For selected old Markdown notes, run:

```text
python scripts/linkedin_capture_helper.py legacy-notes <post-url-or-urn> <note.md> [more.md]
```

This read-only assessment checks up to100 explicitly selected files,256KiB each.
Exact `Source:` and `Activity-ID:` lines are untrusted identity claims. Typed keys,
URNs and supported post URLs are accepted; a numeric `Activity-ID` explicitly
means activity, never share/event/job. Conflicting or invalid claims are ambiguous.
Matching files are candidates with hashes, not verified analysis or permission
to unsave. Quoted lines are ignored; the parser is not a Markdown authenticity
checker. It never scans other files, rewrites notes or creates receipts. Review
candidates before a new publication; re-author and verify against retained source
evidence if migration is needed. Automatic legacy migration remains unimplemented.

The project [linkedin-triage skill](../.agents/skills/linkedin-triage/SKILL.md)
and generated harness entries coordinate this supplied-observation workflow.
Run `python scripts/sync_linkedin_skill.py` to check mirror consistency; this
does not prove runtime parity. Evaluation state is in
[the evaluation record](../evals/linkedin-triage/RESULTS.md).

Still required by issue55: independent skill/harness acceptance, legacy migration policy, batch progress
presentation, representative browser reads, approved unsave verification, auth-wall
abort evidence and independent skill benchmarks. Do not mark the issue complete.

## Publish a verified note

Use `source: linkedin`, the exact canonical URL and observed author/date in scalar
frontmatter. Categories are `Writing`, `News`, `Resources`, `Concepts`, `Jobs`,
`Events`, `Off_Topic`, and `_Skipped`. Include one title and exact typed `Source:`
key, a reasoned priority, `## Synopsis`, `## Action Items`, `## Post Excerpt`,
`## Links` and `## Evidence`.

The excerpt section contains exactly the line `Untrusted source content:` and one
blockquote line of at most 25 words copied verbatim from captured visible text.
The publisher retains and hashes the capture entry and marker automatically.
Unknown authors/dates stay null. It checks excerpt provenance and artifact
integrity, not the truth or quality of the summary and proposed actions. Analyze
the actually retained text before drafting; linked articles/media are not included
unless separately read through their supported gates and cited as evidence.

```powershell
python scripts/triage_store.py publish notes linkedin linkedin:activity:7341234567890123456 Events draft.md --capture-root captures
python scripts/triage_store.py inspect notes RECEIPT_ID
python scripts/linkedin_capture_helper.py retained 'urn:li:activity:7341234567890123456' --root captures --notes-root notes
```

Publication is an explicit local write, not a dry-run command. A previously
verified analysis for the same typed key is returned without overwriting its note.
The serialized publisher alone updates `_index.md`; a receipt left before an
interruption remains pending until the note, evidence and index reference verify.
Skips use `_Skipped`, `--skipped` and `## Reason`; a skipped item may be analyzed
later and is not considered completed analysis.

With `--notes-root`, retained lookup remains read-only and adds `analysis`,
`analyzed` and `publication_pending` fields. Missing/incomplete capture never
becomes analyzed based on an unrelated note. Legacy Markdown files without
verified publication receipts are not counted as analyzed; migration/dedup review
of those files remains a separate acceptance gap. Completion and skip records
never authorize unsaving or other account changes.

Note lookup scans metadata in the supplied notes root's `.triage` receipt store
and verifies the matching selected items; it does not enumerate the LinkedIn account.
