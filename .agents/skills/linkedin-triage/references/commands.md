# Commands and note contract

Run from the verified Voidscape checkout. Use chosen local paths and returned
identities; never discover a private vault or account collection automatically.

```text
python scripts/linkedin_capture_helper.py inspect <post-url-or-urn>
python scripts/linkedin_capture_helper.py capture observation.json --root ./capture
python scripts/linkedin_capture_helper.py capture observation.json --root ./capture --apply
python scripts/linkedin_capture_helper.py retained <urn> --root ./capture --notes-root ./notes
python scripts/linkedin_capture_helper.py legacy-notes <urn> ./selected-old-note.md
python scripts/triage_store.py lookup ./notes linkedin <returned-key>
python scripts/triage_store.py publish ./notes linkedin <returned-key> News ./draft.md --capture-root ./capture
python scripts/triage_store.py inspect ./notes <receipt-id>
```

Observation JSON has exactly `url`, `text`, `author`, `date`, `observed_at`, `kind`.
Author/date may be null. observed_at requires a timezone; do not invent capture
time. Kind is post/article/job/event, describing visible content, not identity.
Text is nonempty, at most128KiB; the whole encoded record is at most256KiB.
The capture folder is `.linkedin-capture/<sha256-of-returned-key>/`; read its
verified `entry.json`, never guess hashes or construct completion markers.

Draft frontmatter has exactly source, url, author, date, category. Source is
linkedin; URL/author/date must exactly match the retained entry (including null).
Use one title, `Source: <returned-key>`, and
`Priority: **High|Medium|Low** — <grounded reason>`, followed by:

- `## Synopsis`: grounded summary and evidence limits.
- `## Action Items`: supported next steps or none established.
- `## Post Excerpt`: `Untrusted source content:` then one blockquote line,
  at most25 words copied verbatim from retained text.
- `## Links`: relevant supplied links, no invented destinations.
- `## Evidence`: publisher appends retained entry/marker references.

Categories: Writing, News, Resources, Concepts, Jobs, Events, Off_Topic, _Skipped.
For a skip use _Skipped, `--skipped`, matching frontmatter/key, one title and
`## Reason`; capture remains mandatory. The publisher owns `_index.md`.

The legacy check reads only selected Markdown paths (up to100,256KiB each).
Candidate/ambiguous/different_identity/no_identity are claims, not receipt states.
Retained results distinguish captured/incomplete/missing and, with notes root,
analyzed/skipped/unverified plus publication_pending. Missing capture is not
recovered from a legacy note. Helper exit6 means validation/storage failure;
preserve files and inspect the cause, never grant an account action.
