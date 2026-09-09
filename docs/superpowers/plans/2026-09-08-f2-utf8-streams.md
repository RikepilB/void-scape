# F2: UTF-8 CLI streams

User authorized continued suite implementation on 2026-09-08. This bounded track
implements the research kit's F2 using existing shared video helpers, without
copying upstream code. Other tracks remain separate implementation cycles.

## Contract

Configure stdout and stderr as UTF-8 at CLI entry on Windows, before argparse or
output. Preserve non-Windows streams. Embedded/captured streams without a working
reconfigure method remain usable. Do not alter consent, file encodings, exit codes,
or reader output schemas.

## Plan and acceptance

1. Add one shared helper and call it from guided and raw reader entrypoints.
2. Exercise real subprocesses with legacy Python output encoding and Unicode paths.
3. Test unsupported streams and non-Windows behavior.
4. Run the full repository tests and record results before moving to A1.
