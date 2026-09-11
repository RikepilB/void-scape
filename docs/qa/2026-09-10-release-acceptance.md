# Release acceptance checkpoint — 2026-09-10

Progress for [#91](https://github.com/RikepilB/void-scape/issues/91), not a release
certificate. Tested base: `42b3496` (merged LinkedIn skill PR #101). Preserve the
distinction between implemented helpers, generated wrappers, actual skill behavior,
live source access and complete media evidence. This document does not close #91.

> A later checkpoint for current main is available in
> [2026-09-11-release-acceptance.md](2026-09-11-release-acceptance.md). The historical
> measurements below remain scoped to this file's exact tested base.

## Executed checks

| Check | Observed outcome | Scope limit |
| --- | --- | --- |
| Full Windows suite | `python -m pytest -q -p no:cacheprovider`: **1102 passed in 108.06s** | Exact tested base above; future commits need their own tests. |
| Installer/demo coverage | Full suite includes `test_install_skill.py` and `test_demo_fixture.py` | Isolated fixture roots, not an upgrade of the user's global installation. |
| Inbox, RSS, YouTube, LinkedIn mirror checks | Each `scripts/sync_*_skill.py` returned `changed: []`, `written: false` | Packaging consistency, not cross-harness runtime parity. |
| Agent Docs generation | `python scripts/build-agent-docs.py --check`: 21 pages current | Generated consistency, not visual/mobile acceptance. |
| Additional actual demo walkthrough | Generated the repository's 12-second fixture; guided inspect, preview and read succeeded with `--tier both --backend captions --frames 3` | Synthetic local fixture; no arbitrary-user-recording claim. |
| Demo consent | Preview reported `requires_cloud_approval: false`, `needs_model_download: false`, transcription cost zero and local sidecar | No cloud/model-download flags passed; API-equivalent agent estimate is not actual billing. |
| Demo artifacts | Complete manifest, three frames at `[00:01]`, `[00:05]`, `[00:09]`, 203-character transcript, no warnings | Frame sampling is not continuous viewing. |
| Independent frame inspection | Viewed the actual three retained JPEGs: red, green, blue in manifest order | The local sidecar says tones rise; images alone do not establish audio content. |
| Fresh supported Chrome | Public landing DOM/disclosure and desktop screenshot succeeded; archive and Reddit accessible | Later responsive check failed; see #42 record. |

Reproduce the demo in a new disposable directory using
`python scripts/create-demo-fixture.py --output <new-dir>/demo.mp4`, then:

```text
python skill/scripts/voidscape.py inspect <new-dir>/demo.mp4 --json
python skill/scripts/voidscape.py preview <new-dir>/demo.mp4 --tier both --backend captions --frames 3 --json
python skill/scripts/voidscape.py read <new-dir>/demo.mp4 --tier both --backend captions --frames 3 --workdir <new-dir>/evidence
```

Read the preview before the final command; fail on missing or unexpected permission
gates. Inspect manifest/transcript/frames after reading. Use a new output path: the
fixture generator overwrites its named synthetic output. No private recordings,
profile information, generated personal notes or account-page screenshots are
committed with this report.

## Measured helper coverage, not claimed 100%

Executed Coverage.py branch measurement on this base:

```text
python -m coverage run --data-file=<private-temp>/helper.coverage --branch -m pytest -q -p no:cacheprovider tests/test_instagram_capture_helper.py tests/test_instagram_cli_workflow.py tests/test_triage_store.py
python -m coverage report --data-file=<private-temp>/helper.coverage --include="*/instagram_capture_helper.py,*/triage_store.py"
```

81 tests passed in 6.70s. This selected measurement reported Instagram helper
**88%** (67 statements, 6 missed, 17 branches, 4 partial) and triage store **67%**
(363 statements, 118 missed, 198 branches, 22 partial). Combined coverage was 70%.
This is coverage of the named test selection, not the complete suite. Child CLI
process execution is not traced by this configuration. It neither proves missing
lines are untested elsewhere nor supports claiming 100% helper coverage for #54.
Coverage data remains local; no extra dependency was installed.

## Source and harness acceptance still open

The existing `evals/{instagram-triage,process-inbox,substack-ingest,youtube-ingest,
linkedin-triage}/RESULTS.md` records correctly distinguish implementation exercises
from independent with-skill/baseline evaluation. This pass did not produce those
independent behavioral grades or execute every claimed target harness. Note hashes
establish artifact integrity, not that a summary is semantically accurate.

- **#54:** independent source-contract/Instagram evaluation and representative
  target-harness evidence remain. The selected coverage measurement above is now
  explicit; do not promote the entire contract to complete.
- **#55:** observation capture, verified notes, legacy-note assessment and project
  skill are merged through #97/#99/#100/#101. Selected real-source acquisition,
  independent behavioral evaluation and permitted harness acceptance remain.
- **#56:** controller and skill exist; no selected real-recording acceptance or
  activated bounded cloud-disabled schedule is certified here. Do not activate an
  indefinite job against an unspecified folder from this issue alone.
- **#57:** public RSS/YouTube implementations and exercises exist; independent skill
  evaluation, representative harness runs and complete-source/access limits remain.

## Other issue gates, kept separate

| Issue | Next verifiable gate |
| --- | --- |
| #42 | Stable supported Chrome connection after the repeated responsive timeout; mobile/reset verification. Source-access success alone is insufficient. |
| #44 | User-selected follower/following export files, then an offline report. No guessing paths or live follow/unfollow actions. |
| #58 | Production transport design/security and isolated client proof in the sibling agent-bridge project. No production promotion of the three-verb spike. |
| #92 | Optional screenshot provenance implementation, reviewed tests and original/crop evidence in its own PR. No Iris prerequisite. |
| #93 | Review the bounded visual-job design in its own PR; design closure is not a running scheduler. |
| #94 | Approved provider plus actual fixture captures/timing/cleanup evidence on each claimed platform. No invented median/p95 or blocked-provider installation. |
| #95 | Reviewed source feasibility plus exact selected collection/export and platform-permitted pilot. Reddit homepage alone is not a saved-content selection. |
| #96 | Review the separate job-search companion boundary/design; closure does not create or ship that application. |

Iris static warnings are not evidence of malware. The repository still explicitly
requires a fresh scan, line-level disposition and Richard's go-ahead before changing
its STOPPED status; the Codex plugin remains DO NOT INSTALL. This acceptance pass
does not install either or suppress a finding.

## Release disposition

**Not fully accepted.** Public desktop layout was readable in the captured state,
but Chrome timed out during the 390 x 844 responsive request and subsequent
selection returned `Browser is not available: chrome`. The attempted viewport
reset could not be confirmed. The detailed chronology belongs to
[the source QA record](2026-09-05-live-source-targets.md).

Do not reuse an older mobile pass as evidence for this run. A final release needs
the chosen merged commit's tests, installer/demo, hosted checks and fresh live
desktop/mobile/interaction evidence. CI checks and deployment are independently
reported on each issue's PR; a rate-limited automated review is not code review.
No version bump, final release tag, global installation or all-issues-complete
claim is made here.
