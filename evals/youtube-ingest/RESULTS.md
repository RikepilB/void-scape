# Evidence and remaining evaluation

Implementation tests cover URL scope, bounded subprocesses, capture integrity,
selected-snapshot resume, reader gates, cookie-binding exclusion, timestamp-bound
publication and note dedup. Real subprocess failures/timeouts are tested separately
from mocked metadata and synthetic media records.

A real public playlist linked by blender.org returned two canonical video IDs
with a limit of two. A131-second public video then completed visual extraction and
cached local Whisper. Seven retained frames and the one-word transcript were
inspected; the QA note explicitly limited its semantic coverage. Verified
publication succeeded and retained lookup returned one analyzed item, zero pending.
This is implementation evidence, not an independent skill benchmark.

The named prompts still need independent with-skill/baseline runs, recorded outputs,
grades and representative target-harness execution. Generated mirrors and helper
tests do not establish those outcomes. Do not mark issue57 acceptance complete.
