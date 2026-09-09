# Initial integration findings

2026-09-09. Method: manual integration exercise in the current Codex session,
using generated local media. This is not an independent with-skill/baseline
benchmark and does not establish cross-harness parity.

## Observed defect and correction

The real guided CLI returned flat success objects for `inspect`, `preview`, and
`read`. The source skill incorrectly described an `ok`/`data` envelope in two
places. That guidance could reject successful reads or look in the wrong place
for permission flags. Corrected the canonical references and regenerated roles.

`tests/test_instagram_cli_workflow.py` now executes all three commands against
the real generated clip and sidecar, verifies the flat schema, checks all three
false permission/dependency flags, and verifies the retained read artifacts.
It does not mock the CLI or substitute a fixture response for a tool call.

## Executed scenarios

| Scenario | Observed result |
| --- | --- |
| Dry-run two URL variants | One canonical item; empty verified lookup; before/after file inventory unchanged |
| Queue without a note | Preview reports duplicate; lookup reports no analysis; queue bytes unchanged |
| Generated local export | Real inspect/preview/read completed with captions backend; three retained frames and transcript inspected; synthetic-provenance draft published and receipt/index reverified |

The generated clip contains red, green and blue scenes at 0, 4 and 8 seconds.
The note identifies the synthetic URL association and distinguishes caption text
from independently heard audio. Seven local evidence files were retained: input,
sidecar, manifest, transcript and three frames. Publication returned
`source_action_authorized: false`; no account action or source fetch occurred.

The same exercise did not run an independent baseline or a separate Claude or
OpenCode actor. The missing-collection case remains unexecuted. No aggregate agent
pass rate, improvement, or full source-workflow completion is claimed.

## Remaining verification

The targeted store/helper coverage run improved the store's combined statement
and branch figure from 81% to 86%. This Windows parent-process measurement does
not include CLI child-process execution or POSIX lock branches. It does not meet
the full-coverage requirement. Follow actual missing paths rather than adding
tests that only repeat implementation details.

Next: independently execute the case matrix where authorized, retain actor traces
and inventories, and grade with-skill and baseline separately. Keep environmental
limitations and unverified assertions visible.
