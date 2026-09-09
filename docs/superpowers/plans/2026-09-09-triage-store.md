# Verified Instagram note publication

Implement the deterministic publication/checkpoint part of issue54. Start with
the Instagram adapter and its existing fixed categories; reject unsupported
sources until their canonicalization and category contracts are implemented.

The controller supplies a locally authored Markdown note and explicitly selected
retained evidence. Validate scalar source frontmatter, canonical URL/key, category,
required sections and bounded inputs. This helper does not generate an analysis or
judge whether its prose is grounded; the source skill and evaluations own that.

Publish using an OS process lock, immutable receipt, exclusive note write,
hash verification, managed index update, and completion marker, in that order.
Retain note/evidence hashes and no approvals. Every lookup revalidates artifacts.
Use separate immutable attempt IDs so transient skips cannot block later analysis.
An identical retry may reconcile an interrupted publication without overwriting
different content. Changed notes, evidence or an unmanaged index fail closed.

The orchestrator alone calls publish and therefore owns index updates. Analysis
workers return drafts and evidence paths. No account action, source deletion,
cloud transfer, background job, or implicit approval occurs in this helper.

Filesystem checks reject observed links/reparse points and confined receipt paths.
The local filesystem is user-controlled; this is not a sandbox against a hostile
process able to replace arbitrary files between checks. fsync is an OS request,
not a universal filesystem/power-loss guarantee. Staging leftovers are preserved.

Verification must cover CLI round trips, duplicate/revision/skip semantics,
interrupted receipt/note/index/marker writes, lock contention and crash release,
edited artifacts/receipts/index, traversal/links, invalid provenance, size limits,
and typed sanitized failures. Then run the full suite and hosted checks.
Connect the actual source workflow only after publication semantics pass.
