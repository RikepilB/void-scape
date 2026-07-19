## Auto snapshot — 2026-07-19T01:13:31.845Z (auto compaction)
- Branch: chore/codex-only-migration
- Uncommitted (git status --short):
```
M docs/handoff/.current-session
 D docs/handoff/2026-07-03-wrapup-and-roadmap/.sid
 D docs/handoff/2026-07-03-wrapup-and-roadmap/HANDOFF.md
 D docs/handoff/2026-07-03-wrapup-and-roadmap/snapshot-005052.md
 D docs/handoff/2026-07-03-wrapup-and-roadmap/snapshot-214337.md
 D docs/handoff/2026-07-05-f409bd2c/.sid
 D docs/handoff/2026-07-05-f409bd2c/HANDOFF.md
 D docs/handoff/2026-07-05-f409bd2c/snapshot-021552.md
 D docs/handoff/2026-07-05-f409bd2c/snapshot-051016.md
 D docs/handoff/2026-07-09-mega-request-triage/.sid
 D docs/handoff/2026-07-09-mega-request-triage/HANDOFF.md
 D docs/handoff/2026-07-15-deep-catch-up/HANDOFF.md
 D docs/handoff/2026-07-17-devpost-draft/HANDOFF.md
 D docs/handoff/2026-07-17-openai-build-week/HANDOFF.md
 M docs/handoff/HANDOFF.md
 M docs/handoff/_meta/TEMPLATE.md
 D docs/superpowers/plans/2026-07-01-upstream-v020-port.md
 D docs/superpowers/plans/2026-07-02-agent-harness-packaging.md
 D docs/superpowers/plans/2026-07-02-instagram-capture-pipeline.md
 D docs/superpowers/plans/2026-07-17-youtube-private-playlist-capture-adapter.md
 D docs/superpowers/specs/2026-07-01-upstream-v020-port-design.md
 D docs/superpowers/specs/2026-07-02-agent-harness-packaging-design.md
 D docs/superpowers/specs/2026-07-02-instagram-capture-design.md
 D docs/superpowers/specs/2026-07-03-ig-capture-analysis-pipeline-design.md
 D docs/superpowers/specs/2026-07-03-transcription-thoroughness-tiers-design.md
 M scripts/install-skill.ps1
 M scripts/install-skill.sh
 M tests/test_agent_docs_gate_sync.py
 M tests/test_install_skill.py
 M tests/test_skill_md_wording.py
?? docs/handoff/2026-07-18-codex-migration/
```
- Diff stat:
```
docs/handoff/.current-session                      |    2 +-
 docs/handoff/2026-07-03-wrapup-and-roadmap/.sid    |    1 -
 .../2026-07-03-wrapup-and-roadmap/HANDOFF.md       |  260 ----
 .../snapshot-005052.md                             |   15 -
 .../snapshot-214337.md                             |   13 -
 docs/handoff/2026-07-05-f409bd2c/.sid              |    1 -
 docs/handoff/2026-07-05-f409bd2c/HANDOFF.md        |   92 --
 .../handoff/2026-07-05-f409bd2c/snapshot-021552.md |   16 -
 .../handoff/2026-07-05-f409bd2c/snapshot-051016.md |   15 -
 docs/handoff/2026-07-09-mega-request-triage/.sid   |    1 -
 .../2026-07-09-mega-request-triage/HANDOFF.md      |   77 --
 docs/handoff/2026-07-15-deep-catch-up/HANDOFF.md   |   44 -
 docs/handoff/2026-07-17-devpost-draft/HANDOFF.md   |  127 --
 .../2026-07-17-openai-build-week/HANDOFF.md        |  157 ---
 docs/handoff/HANDOFF.md                            |  171 +--
 docs/handoff/_meta/TEMPLATE.md                     |   10 +-
 .../plans/2026-07-01-upstream-v020-port.md         | 1390 --------------------
 .../plans/2026-07-02-agent-harness-packaging.md    |  812 ------------
 .../plans/2026-07-02-instagram-capture-pipeline.md |  524 --------
 ...-17-youtube-private-playlist-capture-adapter.md |  470 -------
 .../specs/2026-07-01-upstream-v020-port-design.md  |  164 ---
 .../2026-07-02-agent-harness-packaging-design.md   |  186 ---
 .../specs/2026-07-02-instagram-capture-design.md   |  196 ---
 ...26-07-03-ig-capture-analysis-pipeline-design.md |  213 ---
 ...7-03-transcription-thoroughness-tiers-design.md |  112 --
 scripts/install-skill.ps1                          |   56 +-
 scripts/install-skill.sh                           |   57 +-
 tests/test_agent_docs_gate_sync.py                 |   10 +-
 tests/test_install_skill.py                        |  120 +-
 tests/test_skill_md_wording.py                     |   16 +-
 30 files changed, 104 insertions(+), 5224 deletions(-)
```
