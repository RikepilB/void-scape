# Local inbox note authoring

Implementation dependency for issue #56. The requested scheduled inbox cannot
claim local processing if transcript analysis still uses an online agent.

1. Add a repository-only local note author using an existing Ollama service.
   Fixed IPv4 loopback transport, no proxy or redirect support; no installation,
   model pulling, authentication, web tools or remote provider fallback.
2. Before sending transcript text, require `/api/status` to explicitly report
   cloud disabled, a matching cached model in `/api/tags`, and local completion
   metadata from `/api/show`. Missing or unexpected fields fail closed.
3. Accept a completed local reader bundle. Generate structured note fields from
   its timestamped transcript; require source quotes and valid timestamps for
   action items/key moments. Preserve the full transcript in the draft. Do not
   claim visual analysis or semantic certainty from structural validation.
4. Write a new draft exclusively. No publication receipts, source movement,
   checkpoints, index updates or scheduling in this dependency. The subsequent
   inbox controller must verify the note and evidence before moving a source.
5. Test that failed preflight sends no transcript, redirects/oversized responses
   are rejected, fabricated citations fail, and existing output survives. Exercise
   the real cached model with a synthetic completed reader bundle.

Remaining issue #56 scope is unchanged: bounded oldest-first discovery, SHA256
identity across renames, immutable publication/recovery, per-file hard time caps,
verified source moves, local scheduling, skills/evals/harness proof and real
recording acceptance. This helper alone does not close the issue.

API evidence: [Ollama generate](https://docs.ollama.com/api/generate),
[cloud-disable configuration](https://docs.ollama.com/faq), and upstream
[API types](https://github.com/ollama/ollama/blob/main/api/types.go) /
[status route](https://github.com/ollama/ollama/blob/main/api/client.go).
Integration is written independently using the Python standard library.
