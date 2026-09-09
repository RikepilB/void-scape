# Public feed intake and durable capture

Issue57 requires RSS/Substack discovery, notes, checkpoints and a source skill.
Implement the deterministic intake first, using the existing bounded public
article fetcher and local durable-write primitives. A captured entry is not an
analyzed note and must remain visible for downstream reading/publication.

- Correct RSS content:encoded and Atom alternate-link handling in the shared
  reader. Preserve GUID/ID identity, distinguish fallback identity, and expose
  available author/enclosure metadata without following enclosure URLs.
- Add rss_capture_helper.py with local-file or explicitly permitted public-feed
  fetching, publication-root /feed handling for Substack, since/limit bounds,
  read-only default, immutable per-entry evidence and revalidated capture dedup.
- Scope persistence to selected entries, serialize writers and verify bytes on
  every retry. Never use feed titles as paths, infer paywall status from a short
  excerpt, fetch an article/enclosure automatically or mark capture as analysis.
- Exercise RSS/Atom parsing, ambiguous IDs, dates, no-write preview, interrupted
  publication, edited evidence, lock contention and real public-feed capture.
- Document remaining note publication, source skill, media routing and harness
  evaluation work. Keep issue57 open until its full acceptance is verified.

Sources: RSS2 https://www.rssboard.org/rss-specification and Atom
https://www.rfc-editor.org/rfc/rfc4287. GUIDs/Atom IDs are opaque identifiers;
Atom enclosure links must not be confused with the human-readable alternate.
