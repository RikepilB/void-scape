# Article and RSS reader

Voidscape's article reader prepares deterministic text evidence from local documents and feed
files. It follows the same guided workflow as images and video: **inspect → preview → read**.

## Supported source types

| Input | Local now | Remote URL |
|---|---|---|
| `.md`, `.markdown` | Yes | Planned fetch with approval |
| `.txt` | Yes | Planned fetch with approval |
| `.html`, `.htm` | Yes | Planned fetch with approval |
| RSS / Atom (`.xml`, `.rss`, `.atom`, or feed-shaped XML) | Yes | Planned fetch with approval |
| Public article URLs (`https://…`) | — | Estimate + read require explicit approval |

Video-host URLs (YouTube, Vimeo, Instagram, TikTok, and similar) stay on the media engine.
They are never routed through the article reader.

## Privacy boundaries

- **Local files** are read from disk only. Originals are never modified.
- **Remote URLs** are not fetched during `inspect` or `preview`. `read` fetches only after
  explicit approval (`--allow-cloud` in `voidscape.py`, `--allow-fetch` in `article.py`).
- **Browser-authenticated content** (paywalls, subscriber feeds, saved-session pages) is a
  separate path. A browser-connected agent may read those pages after human approval; the CLI
  **never** reads browser credentials, cookies, or storage.
- **No generic interface extraction** in v1: this is a focused reader, not a universal web
  scraper.

## Evidence layout

`read` writes a workdir containing:

```
workdir/
  manifest.json
  entries/
    001-<slug>.txt
    002-<slug>.txt
```

Each entry file includes a header (`title`, `citation`, optional `link` / `published`) and the
extracted body text. `manifest.json` records deterministic order and citation semantics.

## Citation semantics

| Source shape | Citation form | Example |
|---|---|---|
| Single article / HTML / Markdown / TXT | `[article N]` | `[article 1]` |
| Feed entries (RSS / Atom) | `[entry N]` | `[entry 2]` |

Agents should cite the manifest citation labels exactly. Do not invent timestamps or page numbers
unless they appear in the source metadata.

## Command vocabulary

The engine exposes the same agent-facing commands as `image.py`:

```bash
python skill/scripts/article.py manifest
python skill/scripts/article.py probe path/to/post.md
python skill/scripts/article.py estimate path/to/feed.xml --out-words 600
python skill/scripts/article.py run path/to/feed.xml --workdir ./evidence
```

Guided entry points:

```bash
python skill/scripts/voidscape.py inspect path/to/post.md
python skill/scripts/voidscape.py preview path/to/feed.xml
python skill/scripts/voidscape.py read path/to/feed.xml --workdir ./evidence
```

For remote article URLs:

```bash
python skill/scripts/voidscape.py preview https://example.com/post
python skill/scripts/voidscape.py read https://example.com/post --allow-cloud
```

## Cost and approval gates

`preview` / `estimate` report:

- source availability (local vs remote fetch required)
- estimated text + output token cost
- whether explicit approval is required before network fetch
- that browser-assisted auth is out of scope for the CLI

Local reads are free (no out-of-pocket transcription). Remote fetch is gated separately from
cloud audio transcription, but uses the same `--allow-cloud` flag in the guided CLI for a single
consent vocabulary.

## Feed handling rules

- Entries keep feed document order.
- Duplicate items (same `guid` / `id`, else `link`, else `title|published`) are skipped and
  listed in `skipped`.
- Empty items (no title and no body) are skipped.
- More than 100 entries raises an input error; choose a narrower feed export.

## Manual verification checklist

1. `inspect` a local `.md` file and confirm title order and entry count.
2. `preview` the same file and confirm `requires_cloud_approval` is false.
3. `read` into a fresh workdir and open `entries/001-*.txt` plus `manifest.json`.
4. `inspect` an RSS file with duplicate `<item>` rows and confirm `skipped` lists duplicates.
5. `preview` a public article URL and confirm the next-step text mentions `--allow-cloud`.
6. Attempt `read` on a URL without approval and confirm a permission error.
7. For paywalled content, confirm the CLI reports browser-assisted reading as the alternative.

## Deferred work

- Robust article extraction for complex publisher templates (readability-style parsing).
- Subscriber / authenticated feed adapters beyond anonymous HTTP fetch.
- Redirect-chain reporting and content-type negotiation beyond basic HTML/feed detection.
- Scheduled or unattended feed ingestion (blocked until after 2026-07-21 submission).
