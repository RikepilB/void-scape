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
python scripts/instagram_capture_helper.py process <url-or-shortcode> --queue <urls.md>
```

The helper does not log in, enumerate collections, read browser state, or control Chrome. A harness
may perform a user-approved, read-only collection workflow and pass a confirmed URL to the helper.
The helper validates only the queue operation; it does not prove media access.

Reading the captured URL remains a separate Voidscape `inspect -> preview -> read` job. A URL visible
in an authenticated tab may still fail in an anonymous CLI. Voidscape never extracts cookies from
the browser; see [authenticated sources](../../authenticated-sources.md).

