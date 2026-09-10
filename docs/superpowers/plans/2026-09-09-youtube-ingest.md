# Public YouTube ingestion

Issue57 requires a complete public video/channel/playlist workflow, separate from
the existing OAuth private-queue adapter. The user has authorized implementation,
testing and publication through the active full-suite goal.

1. Normalize exact supported YouTube hosts and video IDs. Reject ambiguous video
   plus playlist/time scope, credentials, fragments and unknown functional queries.
   Only remove known tracking parameters. Explicit channel tabs retain their scope;
   a channel root selects the videos tab, documented rather than silently all tabs.
2. Enumerate an explicit bounded playlist/channel window using installed yt-dlp
   flat metadata. Disable config/plugins/cache, cookies and media download; require
   public-fetch authorization. Bound deadline/output/retries and sanitize errors.
   Flat metadata is incomplete: never infer author/date/access from absent fields.
3. Retain canonical video-keyed captures with immutable hash markers, revalidate
   dedup across collections, and expose pending analysis separately from queued
   state. Resume must not depend on a mutable playlist position alone.
4. Read selected videos through the existing inspect/preview/read gates. Captions
   then permitted cached local Whisper; no implicit cloud or first model download.
   Preserve evidence manifests and actual timestamps; unavailable items are explicit.
5. Extend verified note publication for YouTube provenance and grounded media
   evidence; create project skill/harness mirrors and private library registration.
6. Verify failure/resume/no-write transitions, real public read, source skill evals,
   harness behavior, README/agent docs, hosted checks and merge. Packaging alone
   never proves independent skill or harness acceptance.

Primary option reference: https://github.com/yt-dlp/yt-dlp/blob/master/README.md
Installed CLI help confirms flat-playlist may omit metadata, playlist-items bounds,
ignore-config, no-cache-dir, dump-single-json and bounded extractor retries.
No claim of a completed YouTube source workflow until every required stage works.
