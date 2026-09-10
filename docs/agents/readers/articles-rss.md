# Articles and RSS/Atom

For repeated intake, the repository-only [RSS helper](../../rss-intake.md) adds
bounded public-feed capture and revalidated entry dedup. It stores untrusted
evidence, not analyzed notes. The project-scoped
[substack-ingest skill](../../../.agents/skills/substack-ingest/SKILL.md) coordinates
retained-entry resume and verified note publication; independent harness checks remain pending.

The article reader prepares deterministic text evidence from local documents, feeds, and explicitly
approved public article fetches.

**Status:** `shipped`

[Back to agent docs](../index.md) · Entry points:
[`voidscape.py`](../../../skill/scripts/voidscape.py), [`article.py`](../../../skill/scripts/article.py)

## Inputs

- Local Markdown, plain-text, or HTML documents.
- Local RSS or Atom files, up to 100 entries.
- Non-video `http`/`https` article URLs after preview and explicit fetch approval.

Video-host URLs remain on the video reader. Complex publisher templates, subscriber-only pages, and
browser-authenticated article extraction are not promised.

## Approval boundary

Local documents and feeds require no network. Fetching an article URL transfers the URL/request to
the remote server and is blocked until the previewed job is approved (`--allow-cloud` in the guided
CLI or `--allow-fetch` in `article.py`). The reader does not reuse browser login state.

## Guided use

```powershell
voidscape inspect "feed.xml"
voidscape preview "feed.xml"
voidscape read "feed.xml" --workdir article-evidence
```

Raw commands follow `manifest -> probe -> estimate -> run`; `run` writes `manifest.json` and ordered
text files under `entries/`.

## Citation contract

- A single article uses `[article N]`, normally `[article 1]`.
- RSS/Atom items use `[entry N]` in manifest order.

Do not invent page numbers, timestamps, publication metadata, or text the extraction did not
produce. Canonical details: [article and RSS reader](../../article-rss-reader.md).
