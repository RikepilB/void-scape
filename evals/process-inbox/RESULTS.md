# Evaluation evidence

This is a coverage record, not an independent with-skill/baseline benchmark.

| Scenario | Available evidence | Limit |
| --- | --- | --- |
| Preview and recent files | Actual helper tests prove no writes and default quiet-period filtering | Harness decision quality not independently evaluated |
| Input changes after discovery | Worker test refuses processing before hashing/generation | Quiet periods cannot prove a remote sync has finished |
| Active run | Actual separate CLI process sees the OS lock and returns busy | Scheduled dispatch still needs runtime proof |
| Partial batch and verified moves | PR83 actual synthetic clip, local cached model, failure continuation and durable receipts | Not real user-recording acceptance |
| Renamed duplicate | PR83 model-off replay plus starvation/collision regressions | Live three-harness skill invocation pending |
| Missing local readiness | Local author preflight and controller gate refusals are tested | No claim of OS-level network isolation |

`tests/test_inbox_operations.py` covers the new quiet-period and lock behavior;
`tests/test_process_inbox.py`, `tests/test_process_deadline.py` and
`tests/test_local_notes.py` cover processing, recovery, deadlines and local gates.
`python scripts/sync_inbox_skill.py` checks generated role/mirror drift.

Independent forward-testing requires authorized delegation and isolated synthetic
fixtures. Cases are in `cases.json`; no grades or performance claims have been
invented. Agent-role files and byte-identical mirrors are packaging evidence,
not proof that Codex, Claude and other harnesses executed the skill correctly.
