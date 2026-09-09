# A1: durable result recovery

Implement separately from F2. Each reader writes `.agent/latest-read.json` after
its manifest succeeds. Use a fresh subdirectory and exclusive file creation;
never follow an existing `.agent` destination. The payload contains relative evidence
paths, manifest SHA-256, UTC completion time, and a schema version, with no source
body content, URLs, credentials, or participant fields. Evidence filenames can contain
source titles; the pointer is private local metadata. The manifest remains authoritative.

Failure before manifest completion creates no pointer. Pointer write failure fails
the command and may leave partial artifacts; never treat an older pointer as success
for a failed command. Existing nonempty-workdir rejection prevents stale reuse.

Verify Unicode recovery, content minimization, path confinement, and failure paths.
Document one foreground invocation; recover the pointer once after successful exit
when output is truncated. Waiting on the command's process handle is supported.
Recovery does not replace reading evidence with blind trust in exit status.
