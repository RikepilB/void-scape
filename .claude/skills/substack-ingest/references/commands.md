# Commands and note contract

Run from the verified repository. Replace example roots and IDs with the chosen
paths and returned values; do not discover a private vault automatically.

```powershell
python scripts/rss_capture_helper.py https://publication.substack.com --root ./capture --allow-fetch --limit 10
python scripts/rss_capture_helper.py https://publication.substack.com --root ./capture --allow-fetch --limit 10 --apply
python scripts/rss_capture_helper.py --list-retained --root ./capture --notes-root ./publication-notes --feed-url https://publication.substack.com --limit 10
python scripts/triage_store.py lookup ./publication-notes rss rss:<capture-id>
python scripts/triage_store.py publish ./publication-notes rss rss:<capture-id> Tech ./draft.md --capture-root ./capture
python scripts/triage_store.py inspect ./publication-notes <receipt-id>
```

Public fetch and local writes are separate flags. `--since YYYY-MM-DD` is an
inclusive UTC date filter for capture; unknown dates remain eligible and flagged.
Local UTF-8 feeds use `feed.xml --feed-url https://example.com/feed`. Retained
inventory uses no source, fetch, date filter or apply flag. Its `--feed-url`
filters the selected publication locally; omitting it selects the whole capture
folder. It changes no files.

Notes have scalar frontmatter: `source: rss`, exact retained `url`, `author`,
`date`, and selected `category`. Missing metadata is `null`; dates preserve the
retained string. If the entry has no usable URL, use the retained feed URL.
Use one title and `Source: rss:<capture-id>`, plus
`Priority: **High|Medium|Low** — <reason>` and these sections:

- `## Synopsis`: concise grounded summary with evidence limitations.
- `## Key points`: supported facts.
- `## Action Items`: supported actions, or state that none are established.
- `## RSS Excerpt`: exactly `Untrusted source content:` followed by one blockquote
  line of at most 25 words copied verbatim from the retained body.
- `## Links`: relevant retained links, without guessing removed query values.
- `## Evidence`: populated by the publisher with verified entry/marker links.

Categories: `AI`, `Design`, `Product`, `Jobs`, `Content`, `Startup`, `Hackathon`,
`Tech`, `Software_Developer`, `News`, `_Skipped`. For a skip use `_Skipped`,
`--skipped`, matching frontmatter/key, one title and `## Reason`. Capture evidence
remains mandatory. A skipped record is not an analyzed note.

Exit 4 on RSS capture is missing fetch approval. Exit 6 is a verification/operation
failure: preserve evidence and inspect locally. A publisher duplicate is the
existing verified note, not permission to replace it. No command grants an
account mutation or cloud transfer.
