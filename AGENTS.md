# Voidscape repository instructions

## Role

Maintain Voidscape as a local-first Codex skill and CLI for grounded video/audio reading.

## Style

Match the existing Python standard-library style. Keep user-facing approval text direct.

## Constraints

- Preserve `inspect -> preview -> read`; never bypass cloud or model-download consent gates.
- Never read browser credentials, cookies, storage, or secrets.
- Keep `read-video` aliases only as documented backward compatibility.
- Preserve upstream license attribution in `CREDITS.md`.
- Do not build unattended orchestration before the 2026-07-21 submission.

## Workflow

Read `docs/architecture.md`, `docs/BUILD_WEEK_PROVENANCE.md`, and the current handoff before
changing behavior. Update tests with each behavior change.

## Quality

Run `python -m pytest -q -p no:cacheprovider`. Verify the installer and demo fixture for
submission-critical changes.
