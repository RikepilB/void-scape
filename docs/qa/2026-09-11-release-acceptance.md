# Release acceptance checkpoint — 2026-09-11

Current evidence for [#91](https://github.com/RikepilB/void-scape/issues/91),
not a release certificate. Tested base:
[`65deac1`](https://github.com/RikepilB/void-scape/commit/65deac148d9a2aee56f2ed96d1ebf95c18afae79)
(`docs: record Chrome transport interruption (#127)`). This checkpoint replaces
neither the historical [2026-09-10 record](2026-09-10-release-acceptance.md) nor
the distinct source, harness, browser, and external-review gates.

## Executed checks

| Check | Observed outcome | Scope limit |
| --- | --- | --- |
| Full Windows suite | `python -m pytest -q -p no:cacheprovider`: **1316 passed in 115.67s** | Exact tested base above; this does not exercise personal accounts or remote sources. |
| Installer and demo coverage | The full suite includes `test_install_skill.py` and `test_demo_fixture.py` | Isolated fixture roots, not an upgrade of the user's global installation. |
| Agent Docs generation | `python scripts/build-agent-docs.py --check`: **21 pages current** | Generated consistency, not visual/mobile acceptance. |
| Hosted validation | [Tests](https://github.com/RikepilB/void-scape/actions/runs/34563542518) and [Pages deployment](https://github.com/RikepilB/void-scape/actions/runs/34563542145) succeeded for `65deac1` | Hosted checks are separate from source and harness acceptance. |
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
  require their stated real input and harness evidence. No LinkedIn unsave or
  unattended schedule is authorized or claimed here.
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
