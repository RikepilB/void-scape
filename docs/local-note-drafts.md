# Local transcript note drafts

Repository-only dependency for the inbox workflow in issue #56. This helper
authors a draft from a completed local transcript using an already installed,
cached Ollama model. It does not move recordings or install a scheduler.

```powershell
python scripts/local_notes.py <completed-evidence-folder> <new-draft.md> --model gemma3:4b
```

Use your chosen cached model name. The model service must be listening on IPv4
loopback (default port 11434) with cloud features disabled. Follow
[Ollama's local-only configuration](https://docs.ollama.com/faq); the helper
checks the live status rather than trusting an environment variable supplied to
the client. It never starts a service, downloads a model or requests credentials.

Before sending transcript content, the helper verifies cloud-disabled status,
an exact cached-model match and local completion metadata. Remote aliases and
missing status fields are refused. The HTTP client connects directly to
`127.0.0.1`, without proxy handling or redirect following. No web-search or model
pull endpoint is exposed.

The output contains title, priority, synopsis, actions, timestamped key moments
and the full input transcript. Actions and moments must include exact transcript
quotes at valid source timestamps. The model receives transcript text only;
visual analysis is not claimed. Structural grounding does not prove that every
paraphrase or prioritization is correct; generated text remains untrusted and
reviewable. A draft never authorizes source mutation.

## Current bounds

- Completed `captions`, `faster-whisper` or `whisper-cpp` bundle required.
- Transcript must be inside the evidence folder; links/reparse points are rejected.
- Maximum 4,000 UTF-8 bytes of transcript. Longer recordings require the pending
  chunking/reduction stage; the helper rejects them rather than silently truncating.
- Bounded response size and socket timeout. This is not yet the inbox worker's
  hard wall-clock limit for a whole file.
- Exclusive draft creation; existing drafts remain intact. Transcript changes
  during generation stop publication.
- The local service is a trusted machine component. These checks are not an OS
  network sandbox or a defense against a hostile process impersonating localhost.

Verified with Ollama 0.30.9, cached Gemma 3 4B, a synthetic completed caption bundle,
and cloud-disabled runtime status. The generated note preserved the complete
transcript and grounded moments. No recording moved. Tests also cover refusals
before any transcript is sent, invalid citations, redirects and oversized replies.

Remaining inbox work: long-transcript chunking, oldest-first file processing,
stable content identity across renames, verified publication/checkpoint recovery,
source moves, per-file cancellation, scheduler and real recording/harness evidence.
