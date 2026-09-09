# Long transcript note drafting

Issue #56 dependency, within the requested suite upgrades. Extend the existing
local draft helper without changing source acquisition or consent boundaries.

1. Validate the entire timestamped input before generation. Bound the document
   at 1 MiB and 512 segments; each model request stays within 4,000 UTF-8 bytes.
2. Preserve all source text, Unicode characters and original timestamps. Keep
   validated actions and moments from every segment; reduce only synopses.
3. Cache validated generations by content, model name and schema. Verify cached
   integrity and citations before reuse, preserve changed entries, and resume
   interrupted generation. Cache reuse is not approval or model-freshness proof.
4. Keep cloud-disabled local model checks before each new generation. Source
   modification during processing must still prevent draft publication.
5. Verify late-segment retention, Unicode boundaries, bounded reduction, altered
   input/cache handling and interrupted recovery. Exercise the installed cached
   model on synthetic long input and prove a complete replay needs no model call.

No source moves, scheduler or installed skill are added by this dependency.
Structural citation checks do not establish semantic correctness; the generated
overview is derived from summaries and remains reviewable. The inbox controller
still needs a hard per-file deadline and real recording acceptance.
