# Verified LinkedIn notes

Continue issue55 from merged capture PR97. Reuse the existing serialized note
publisher, immutable receipts and index ownership; do not add a second store.

1. Bind LinkedIn drafts to a verified typed capture identity and exact observed
   URL/author/date. Require the issue's fixed categories and note sections.
2. Verify a short, explicitly untrusted Post Excerpt against retained visible text.
   Hashes and verbatim text validate provenance, not summary accuracy.
3. Deduplicate verified analysis by typed source key; preserve skip/pending states.
4. Add optional notes-root lookup to selected capture resume, without writing or
   treating legacy notes/queue entries as verified analysis.
5. Test malformed drafts, provenance changes, forged/oversized excerpts, duplicate
   and interrupted publication, CLI use and read-only resume. Run existing source
   tests and full suite; document remaining skill/browser/unsave/evaluation gates.
