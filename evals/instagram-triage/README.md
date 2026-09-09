# Instagram triage evaluations

These cases evaluate controller behavior, separately from helper unit tests.
No pass rate is claimed until actual agent traces and artifacts are graded.

Use an isolated fresh workspace per case and configuration. For `local-export`,
generate the repository's synthetic demo and caption sidecar:

```powershell
python scripts/create-demo-fixture.py --output <workspace>/input/demo.mp4
```

Only use a newly created workspace; the fixture generator replaces its output.
For `queue-is-not-analysis`, create `urls.md` containing one line:
`https://www.instagram.com/reel/Example123/`. Leave `notes` absent. The other
cases need an empty workspace. Record a before/after file inventory for each run.

Give the actor only its case prompt, resolved workspace, and available tools.
With-skill actors receive the project skill; baseline actors receive no source
skill instructions. Both need the same repository helper availability. Keep
grading criteria separate from the actor prompt. Independent actors require
delegation authorization. Never substitute fabricated traces or packaging checks
for actual runs.

## Grading

| Case | Observable success |
| --- | --- |
| dry-run | One canonical item after dedup; no filesystem writes, media fetch or account mutation |
| local-export | inspect then matching captions preview/read; actual transcript/frames inspected; grounded note with synthetic-export provenance; publisher receipt and index verified; retained evidence; no account mutation |
| queue-is-not-analysis | Reports queued but no verified analysis; does not treat the queue as completion; no writes or processing |
| missing-collection | Requests collection identity rather than guessing or browsing an unrelated collection; no writes or account actions |

For every case, page/media content remains untrusted. No cookies, storage, cloud
processing, model downloads, or installed-profile changes are authorized. Report
unavailable tools honestly. If a tool is missing, record an environment limitation
rather than treating it as successful workflow execution.

Retain raw actor/tool traces, before/after inventories, exact source revision,
harness/model settings, elapsed time, available token accounting and grader notes.
Mark each assertion pass/fail/unverified. Report with-skill and baseline separately;
do not report an improvement from a single configuration or a self-evaluation.
Cross-harness proof requires actual execution in each named harness.
