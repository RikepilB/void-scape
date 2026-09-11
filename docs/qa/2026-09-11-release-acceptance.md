# Release acceptance checkpoint — 2026-09-11

Current evidence for [#91](https://github.com/RikepilB/void-scape/issues/91),
not a release certificate. Tested source base:
[`b9f577a`](https://github.com/RikepilB/void-scape/commit/b9f577a37f475e51156301c3c38c60f62b82320b)
(`docs: refresh release evidence (#130)`). This supersedes the earlier `3d1d46b`
and `65deac1` checkpoints for current-main evidence. It does not replace the historical
[2026-09-10 record](2026-09-10-release-acceptance.md) or any distinct source,
harness, browser, and external-review gate.

## Executed checks

| Check | Observed outcome | Scope limit |
| --- | --- | --- |
| Full Windows suite | `python -m pytest -q -p no:cacheprovider`: **1322 passed in 100.98s** | Exact tested base above; this does not exercise personal accounts or remote sources. |
| Installer and demo coverage | The full suite includes `test_install_skill.py` and `test_demo_fixture.py` | Isolated fixture roots, not an upgrade of the user's global installation. |
| Agent Docs generation | `python scripts/build-agent-docs.py --check`: **21 pages current** | Generated consistency, not visual/mobile acceptance. |
| Hosted validation | [Tests](https://github.com/RikepilB/void-scape/actions/runs/34567347860) and [Pages deployment](https://github.com/RikepilB/void-scape/actions/runs/34567347417) succeeded for `b9f577a` on Linux 3.10, Linux 3.12, and Windows 3.12 | Hosted checks are separate from source and harness acceptance. |
| Inbox scheduler plan | Preview validates fixed local-only settings; `--write-config` writes a reviewed configuration and prints a manual `schtasks.exe` command | It does not create or start a task, transfer content to cloud services, start/download a model, or prove a scheduled run. |
| Independent synthetic safety evaluation | Codex baseline and with-project-skills traces each passed **30/30** observable safety assertions | Deliberately no browser, account, network, media, model, cloud, publication, or source mutation. Claude's paired run was unavailable because its local OAuth session had expired. |
| Fresh supported Chrome tab | A new public Agent Docs tab exposed the responsive menu at 390 x 844 and returned to desktop navigation | Later source-tab creation returned `Browser is not available`; this is bounded recovery evidence, not durable transport acceptance. |

The independent safety traces in `evals/independent-safety/` show that the tested
skills did not weaken the five supplied safety decisions. They do not establish a
quality difference from the baseline, semantic note quality, cross-harness behavior,
or real source-workflow completion.

## Open acceptance gates

- **#42:** a basic Chrome installation and registration problem is not established,
  but the later transport interruption prevented the Archive, Reddit, and exact X
  retries. The public record is [the Chrome evidence brief](../design-brief.md).
- **#54 and #57:** source helpers and project workflows have implementation evidence.
  Independent, fixture-backed skill evaluation; representative harness runs; and
  selected real-source evidence remain distinct requirements.
- **#55 and #56:** LinkedIn's read-only capture pilot and the inbox controller still
  require their stated real input and harness evidence. The inbox now has a manual
  Windows scheduler-plan helper, but no task registration or unattended schedule is
  authorized or claimed here. LinkedIn unsave remains out of scope.
- **#58:** the separate agent-bridge repository now has a proposed
  [pairing and permission design](https://github.com/RikepilB/agent-bridge/pull/4).
  Independent security review and one isolated client proof remain before any
  production bridge claim.
- **#44, #94, and #95:** selected follower exports, an approved capture provider, and
  a selected saved-source use case respectively are required before work can move
  beyond their documented boundaries. Iris remains stopped and its plugin remains
  `DO NOT INSTALL`.

## Release disposition

**Not fully accepted.** The current main commit has local tests, generated-doc
consistency, installer/demo coverage, and hosted checks. It does not yet have a
stable supported Chrome transport, complete independent cross-harness evaluation,
or the real selected-source acceptance required for repository source workflows.

Do not create a version tag, change a global installation, or claim every issue is
complete from this checkpoint. Keep the current landing and agent documentation
labels: core readers are shipped; source workflows remain `dev-only` until their
separate evidence gates pass.
