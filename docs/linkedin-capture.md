# LinkedIn observed-post capture

Development helper for issue55, not a complete saved-posts triage skill. It accepts
local observations from a separately approved browser workflow or user-provided
text. It does not open LinkedIn, enumerate saved items, write analysis notes,
read credentials, or unsave anything.

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

`retained` checks only the supplied1..100 unique identities. It distinguishes
`captured`, `incomplete` and `missing`, with no directory-wide/account enumeration
and no writes. Captured means a verified local observation, never analyzed.

A retry with identical data can finish an interrupted capture. A conflicting
partial entry stops; a completed duplicate keeps the original and reports changed
observation metadata/text without overwriting. Source edits and deletions are not
tracked remotely. Hash verification detects file changes; it does not prove the
truth of caller-supplied text or capture time. Results never authorize unsaving.

## Verification and remaining acceptance

The initial47 synthetic tests cover aliases, typed identities, rejected scope,
schema/size bounds, dry-run, complete/partial duplicates, corruption, failed
read-back, selected resume, symlink rejection, and CLI behavior. Measured helper
statement/branch coverage is100%; this is not browser or independent agent QA.

Still required by issue55: verified note/excerpt publication and index integration,
the project skill and harness mirrors, legacy-note dedup assessment, batch progress
presentation, representative browser reads, approved unsave verification, auth-wall
abort evidence and independent skill benchmarks. Do not mark the issue complete.
