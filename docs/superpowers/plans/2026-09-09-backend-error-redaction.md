# Backend error redaction (A3)

The authorized suite includes error sanitization. Implement this before adding
more diagnostic surfaces: exceptions currently enter fallback logs and transcript
gap markers as well as CLI envelopes.

- Shared sanitizer removes URL userinfo/query/fragment and recognizable credential
  assignments, authorization headers, and common provider-token prefixes.
- Sanitize before truncating an exception and before writing logs, CLI errors,
  aggregate failures, or synthetic transcript-gap markers. Source transcripts and
  successfully read article/chat content remain unchanged.
- Do not inspect environment values to build a redaction list. Keys remain env-only.
- Omit raw HTTP rejection bodies entirely; providers may echo credentials in arbitrary
  prose that pattern matching cannot reliably recognize. Keep HTTP status and backend.
- Gemini SDK failures expose a bounded exception type, not the provider's raw message.
- Preserve exit classification, retry policy, backend choices, and consent behavior.
- Table-driven synthetic tests cover URLs, headers, JSON/key-value text, provider
  prefixes, fallback/chunk logs, legacy/structured/guided CLI output, and HTTP-body omission.

No source code is copied from the research project. No network request or real
credential is needed for verification. Generic sanitization is defensive pattern
matching, not a promise to detect arbitrary secrets in arbitrary prose.
