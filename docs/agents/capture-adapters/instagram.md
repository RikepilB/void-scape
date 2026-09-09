# Instagram capture adapter

The Instagram repository helper canonicalizes and deduplicates user-confirmed Reel/post URLs before
appending them to a queue.

**Status:** `dev-only`

[Back to agent docs](../index.md) · Canonical sources:
[`instagram_capture_helper.py`](../../../scripts/instagram_capture_helper.py) and
[capture adapters](../../capture-adapters.md)

## Status board

| Capability | Status | Boundary |
| --- | --- | --- |
| Canonicalize a confirmed Reel/post URL | `dev-only` | Repository helper only |
| Deduplicate and append to `urls.md` | `dev-only` | Local queue operation |
| Browse a saved collection | `dev-only` workflow | Harness browser task after site approval |
| Installed Instagram capture command | `planned` | Not included by the skill installer |
| Automatic private collection or cookie access | `parked` | Explicitly unsupported without separate security/ToS design |

## Helper use

```powershell
python scripts/instagram_capture_helper.py inspect <url-or-shortcode>
python scripts/instagram_capture_helper.py preview <url-or-shortcode> <urls.md>
python scripts/instagram_capture_helper.py process <url-or-shortcode> <urls.md>
```

`inspect` and `preview` do not write files. Both return flat JSON with canonical
URL/shortcode and false mutation flags; preview adds the duplicate/action result.
Only `process` writes the queue. All commands require a zero exit and valid JSON.

The project-local [Instagram triage skill](../../instagram-triage-skill.md)
connects scoped discovery, these helpers, gated media reads and note publication.
Its generated role files have packaging checks; live harness parity is still pending.

The helper does not log in, enumerate collections, read browser state, or control Chrome. A harness
may perform a user-approved, read-only collection workflow and pass a confirmed URL to the helper.
The helper validates only the queue operation; it does not prove media access.

For analyzed notes, the controller uses the repository-only
[verified note publisher](../../triage-store.md). Workers return drafts; the
publisher verifies source fields and evidence hashes before completing the receipt
and index. `lookup` distinguishes analyzed items from skips and pending attempts.
These mechanics do not establish an installed skill or live harness verification.

Reading the captured URL remains a separate Voidscape `inspect -> preview -> read` job. A URL visible
in an authenticated tab may still fail in an anonymous CLI. Voidscape never extracts cookies from
the browser; see [authenticated sources](../../authenticated-sources.md).
