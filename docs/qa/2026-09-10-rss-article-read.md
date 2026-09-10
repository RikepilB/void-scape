# RSS article read verification

Implementation branch: `codex/rss-followup-read`. Related issue #57 stays open.

- Synthetic retained feed entry selected the public IANA example-domain page.
- Actual guided inspect/preview exposed the article-fetch gate; approved helper
  read fetched 188 words through the existing public fetcher.
- Inspected actual `[article 1]` text, including its navigation boilerplate.
- Authored a local note with a nine-word verbatim excerpt and supported findings.
  Publication and subsequent receipt inspection both reported artifact_verified.
- Repeated helper read verified existing evidence without refetching the article.

Source: [IANA example domains](https://www.iana.org/help/example-domains).
This is a real public article fetch plus synthetic feed selection, not proof of
an IANA RSS feed, Substack access, media enclosure handling or independent agent
evaluation. No model download, AI upload, browser account or external note copy.

The initial CLI run failed before networking because the wrapper passed the raw
engine's `--allow-fetch` to the guided CLI. Corrected to the guided `--allow-cloud`
flag only after verifying the article-fetch gate and forcing `--reader article`.
Earlier tests also caught Windows newline handling in verbatim quote extraction.
Both corrected before the successful run. Failed diagnostics were preserved.

Tests exercise the real article parser/manifest with synthetic network payloads,
gate refusal, changed evidence, wrong resource type, malformed manifests, deadline
bounds, no-consent behavior, typed enclosure selection and article note binding.
They establish these mechanisms, not semantic accuracy across arbitrary websites.
