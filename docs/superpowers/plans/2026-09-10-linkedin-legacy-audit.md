# Selected legacy-note assessment

Issue55 needs old-note dedup without promoting unaudited notes to verified analysis.
Add a read-only helper command over explicitly selected Markdown paths, bounded
to100 files and256KiB each. Reuse typed identity parsing and safe-path checks.
Report matching candidates, conflicting/invalid claims, other identities and
missing identity. Preserve file hashes for review; never create receipts or
unsave permission. No recursive vault discovery, source fetch or automatic migration.
Test typed collisions, malformed claims, bounds, CLI failure and unchanged files.
