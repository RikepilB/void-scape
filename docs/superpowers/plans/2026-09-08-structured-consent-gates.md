# Structured consent gates (A2)

The suite implementation request authorizes this bounded track. Research is a
pattern reference; implementation is written against the current reader code.

## Contract

- Preserve exit codes: approval failures remain 4, missing credentials remain 5.
- Add `error.gate` with `type`, `backend`, and (for credentials) `env_var` names.
  Never serialize key values. Existing error code/message fields remain available.
- Preview reports approval/download requirements without inspecting API keys.
- Cloud approval and model-download approval remain separate and ordered before
  credential lookup. Sidecars and visual-only reads still avoid unused backends.
- Explicit backend fallback chains keep their behavior. If every backend fails,
  preserve the individual structured gates in `error.gates`; mixed failures must
  not be represented as a single missing-credentials problem.
- Article fetching reports its existing approval gate through the same schema.
- CLI stays noninteractive. Agents ask once for the missing action, never ask users
  to paste key values in conversation, and never treat configured keys as approval.

## Implementation and verification

1. Add typed gate exceptions and shared error serialization in the video helpers.
2. Annotate current approval and missing-key failures; retain fallback metadata.
3. Use shared serialization in guided and raw reader error envelopes.
4. Add preview metadata and document field/exit compatibility in CLI and skill docs.
5. Test all three gate types, raw/guided parity, consent-before-credentials,
   multi-backend failures, no value disclosure, and existing sidecar behavior.
6. Regenerate the repository mirror and Agent Docs, run full tests and CI.

No key storage, OAuth, automatic retry, cloud transfer, model download, or new
authorization is part of this change.
