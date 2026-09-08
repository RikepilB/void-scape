# Instagram follow audit adapter

A read-only relationship audit: diff a followers export against a following export and produce a
citable report for unfollow decisions. It never unfollows, follows, or messages anyone.

**Status:** `dev-only`

[Back to agent docs](../index.md) · Canonical sources:
[`ig_follow_audit_helper.py`](../../../scripts/ig_follow_audit_helper.py) and
[capture adapter contract](../../capture-adapters.md)

## Status board

| Capability | Status | Boundary |
| --- | --- | --- |
| Inspect two user-provided export files | `dev-only` | Repository script; local files only |
| Preview the diff plan | `dev-only` | Counts only; no writes |
| Write the local audit report | `dev-only` | New empty report dir; `report.md` + `report.json` |
| Execute unfollows | `parked` | Never implemented here; reading never implies account action |
| Installed audit command | `planned` | Not included by the skill installer |

## Commands

```powershell
python scripts/ig_follow_audit_helper.py inspect --followers followers.json --following following.json
python scripts/ig_follow_audit_helper.py preview --followers followers.json --following following.json
python scripts/ig_follow_audit_helper.py process --followers followers.json --following following.json --report-dir audit-report
```

Each side accepts an Instagram data-download JSON list or a plain text file with one handle per
line. The user exports both lists from Instagram's own settings or data download; the helper has no
network access and reads no browser state.

The report cites each suggested handle as `[user N]`. Acting on the list — unfollowing, keeping,
messaging — is a separate human decision with its own consent; this adapter only produces evidence.
