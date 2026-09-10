# LinkedIn capture foundation

Authorized full-suite work, issue55. This slice establishes identity and durable
observed-post evidence before note publication and browser/account operations.
It does not complete the issue's live acceptance or independent skill evaluation.

1. Accept explicit activity/share/ugcPost URNs and observed post URLs carrying
   those identities. Never convert an event/job ID into an activity ID; reject
   unknown/share-shortener shapes without fetching them.
2. Validate a bounded local observation: text, optional author/date, capture time,
   content kind and canonical URL. Treat all fields as untrusted evidence.
3. Preview writes nothing. Applied capture writes an immutable entry, flushes and
   re-reads it, then writes a verified completion marker. That marker is a per-item
   checkpoint, not an analyzed note or authority to unsave.
4. Resume against explicit selected identities, verifying complete artifacts and
   distinguishing incomplete/captured/missing entries. Do not scan account data.
5. Test URL scope, redaction, bounds, missing/partial/conflicting writes,
   corruption, duplicates, symlinks and CLI envelopes with synthetic fixtures.

Follow-on work: bind notes/excerpts and index through triage_store, build the skill
and harness mirrors, then execute approved real browser/unsave and independent
evaluation acceptance. All capture, cloud/model and account gates remain separate.
