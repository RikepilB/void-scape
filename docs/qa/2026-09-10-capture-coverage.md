# Capture helper coverage audit

Baseline: `c497b86`, Windows, existing coverage.py 7.5.0. The full test suite passed
with branch instrumentation limited to four capture helpers. Child Python
processes were instrumented through a temporary `sitecustomize.py` calling
`coverage.process_startup()`, scoped environment variables and parallel data files.
Environment values were restored afterward; no global Python configuration or
package installation changed. Synthetic tests used no live account credentials.

| Helper | Combined statement/branch coverage |
| --- | --- |
| Instagram | 98% |
| LinkedIn | 100% |
| RSS | 100% |
| Private YouTube API adapter | 78% |
| Total | 93% |

These are rounded coverage.py percentages, not semantic accuracy or live harness
grades. The measured modules contain 652 statements and 271 branch opportunities;
35 statements and 17 partial branches remained uncovered. Initial parent-only
and dedicated-test-only measurements understated coverage and were superseded by
the full-suite subprocess-aware run. The table is a baseline, not a claim about
later commits. Issue #54's complete branch acceptance remains unmet.

## Concrete finding

On the baseline code, `_parse_api_error(403, '[]')` raised
`AttributeError: 'list' object has no attribute 'get'`. The error path assumed a
JSON object and correctly shaped nested `error`, `errors` and `reason` fields.
Unexpected JSON from an API/proxy could therefore escape normal classification.

The correction accepts only object-shaped error metadata, list-shaped error
entries and string messages/reasons. Malformed metadata keeps the HTTP status
classification; valid quota reasons remain recognizable after malformed entries.
Regression cases use null, arrays, scalars and invalid nested field types. This
is synthetic failure-path verification, not evidence of a live provider outage.

At this baseline, remaining coverage work included YouTube network failures, malformed successful
responses, pagination and CLI failure branches, plus an Instagram invalid-shortcode
guard. Review their existing tests and contracts before adding cases; percentage
gains alone do not establish correct behavior.

## Follow-up: reachable paths and queue confirmation

After PR119–PR121 and the title-resolution/queue-confirmation regression tests,
a fresh full-suite subprocess-aware run passed 1,314 tests. Runtime helper source
was unchanged from `d046df1`; the additional changes are tests. The exact result
was 683 of 684 statements and 287 of 288 branches covered (99.7942% combined),
with no exclusions. Instagram, LinkedIn and RSS had no missing lines or branches.

The remaining YouTube path is the fallback `return 1` after handling the three
CLI commands. Argparse restricts command selection to inspect, preview and process;
an unsupported-command test verifies exit 2 before transport starts. The fallback
was retained, not excluded or forced through a fabricated parser result. This is
not a literal 100% coverage claim.

New tests also verify default/custom playlist-title resolution and the failure
when an existing queued URL disappears before confirmation. The latter stops
before any playlist deletion. All transport and race inputs are synthetic; no
account mutation or private credentials are used. Independent skill/harness and
semantic acceptance remain outstanding even with these reachable paths exercised.
