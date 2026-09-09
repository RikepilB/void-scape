# Recording inbox skill and watched-file safeguards

Advance issue56 using the merged controller, preserving its actual scope.

1. Add a configurable quiet period (default60seconds) for recordings and sidecars.
   Filter discovery and recheck inside the worker before hashing or inference.
   Report deferred files without creating a false completed result.
2. Distinguish real OS lock contention from filesystem errors. Overlapping runs
   return busy with no new worker; permission errors remain failures.
3. Author the project-scoped process-inbox skill using skill-creator guidance.
   Generate Claude/Agents/Codex controller mirrors from a single source and check
   drift. Keep explicit roots/model/bounds, local-only gates, scoped authorization,
   integrity checks and sanitized scheduled summaries.
4. Register the skill in the private skills-lab with a versioned project-owned
   snapshot. Preserve unrelated dirty changes and never copy it globally.
5. Record behavioral evaluation cases and actual evidence without inventing an
   independent benchmark or installed-harness acceptance. Test actual lock
   contention, recently changed sidecars, worker rechecks and no-write previews.

Actual scheduled execution, real recording acceptance and independent harness
evaluation remain required for overall issue completion. No cloud/model download,
account action, scheduler installation or private-content upload is added here.
