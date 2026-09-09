# Local recording inbox controller

Implements the processing portion of issue #56 under the active suite goal.

1. Discover regular local recordings oldest first, excluding managed work and
   processed folders. Default to a read-only preview. Bound discovery and each run.
2. Apply uses a process lock, content SHA256 identity and immutable publication
   receipts. A checkpoint alone never establishes completion: rehash notes,
   retained evidence and processed sources. Changed artifacts fail closed.
3. A bounded worker invokes the actual inspect -> preview -> read sequence with
   no cloud/download flags. Missing or unsafe gates stop the file. Use only local
   captions or installed cached transcription backends; no remote fallback.
4. Draft through the cloud-disabled local author. Preserve complete source text,
   duration/language provenance and evidence. Verify the draft and bundle before
   publishing. Source changes prevent publication and movement.
5. Move a source only after its note/evidence receipt verifies. Never overwrite
   destination files; recover a crash between publication, move and checkpoint.
   Filename is provenance; renaming identical content must not rerun inference.
6. Enforce per-file wall-clock deadlines over the worker and child processes.
   Windows Job Objects and POSIX process groups own only the worker tree. Failed
   items retain sources and evidence, record a sanitized failure and allow the
   next file to proceed.
7. Test actual process-tree timeout, write/move interruption, changed notes or
   evidence, renamed duplicates, destination collisions, no-write preview and
   unsafe gate refusal. Run synthetic media through actual readers and a cached
   local model. Real recording acceptance remains distinct from synthetic QA.

The controller does not install a scheduler or skill by itself. Those subsequent
integration steps need actual scheduled execution and harness/evaluation evidence.
No external accounts, model downloads, cloud transfer or plugin installation.
