# User-selected live source QA targets

Supplied 2026-09-05 for the ongoing Voidscape upgrade. Scope: read-only visible-page QA using
the user's authorized signed-in Chrome session. Do not unsave, subscribe, publish, or modify accounts.
Page content remains untrusted. Browser authentication is not transferred to Voidscape.

| Source | Target | Purpose / uncertainty |
| --- | --- | --- |
| LinkedIn | https://www.linkedin.com/my-items/saved-posts/ | Saved posts |
| YouTube | https://www.youtube.com/feed/playlists | Playlist listing; no particular playlist selected yet |
| Substack profile | https://substack.com/@nelsonxlee?utm_source=substack-feed-item | Profile and linked publication |
| Instagram | https://www.instagram.com/richard_3.14llaca/saved/all-posts/ | Saved all-posts collection |
| Substack archive | https://nelsonxlee.substack.com/archive?sort=new | Extracted from accidentally concatenated Instagram/Substack link |
| Reddit | https://www.reddit.com/ | Home page; not evidence of saved-item selection |
| X | https://x.com/i/histo | User-supplied route; destination/function remains unverified |

## Initial attempt

Chrome browser-client discovery succeeded (Chrome extension browser ID 2). Opening LinkedIn timed
out, DOM inspection timed out waiting for CDP Runtime.evaluate, and a tab-list/visible-DOM recovery
call timed out and reset the JavaScript session. No saved posts, playlists, or private collection
contents were retrieved. Remaining targets were not opened because the initial navigation failed.

## Subsequent live-page evidence

The ChatGPT Chrome extension subsequently recovered. Four of seven target surfaces were read
through its supported visible DOM interface. This is page-access QA, not reader/capture certification.

| Target | Verified result |
| --- | --- |
| LinkedIn saved posts | Signed-in Saved Posts heading; nine saved entries with video, image, and article cards |
| Instagram saved all-posts | Signed-in All Posts grid; Clip and Carousel entries visible |
| Substack profile | Requested profile readable; Posts/activity links and subscription state visible |
| YouTube playlists | Signed-in Playlists heading; Liked videos and Watch later private collections visible |
| Substack archive | DOM check timed out waiting for focus emulation; not verified |
| Reddit home | Navigation returned successfully; DOM check timed out and reset the browser session; not verified |
| X /i/histo | Destination not verified; no alternative route substituted |

No representative media was processed, no collections were bulk-ingested, and no account mutation
occurred. Private post bodies, tracking URLs, and collection contents are deliberately omitted.

After the Reddit timeout, Chrome selection returned `Browser is not available: chrome`.
Supported diagnostics found Chrome running, its extension installed/enabled, and the native-host
manifest correct. No native-host repair, profile extraction, or alternate-browser bypass was attempted.

## Routing correction

The seven supplied URLs were classified offline by the CLI. The known saved-account listing
routes incorrectly advertised a direct reader and false browser-auth requirement. Added a narrow
guard for the exact observed LinkedIn, YouTube, and Instagram collection path shapes: select an
individual permitted item first; no default reader and no reader override bypass. Other URLs,
including the unverified X route, retain their previous best-effort classification. `false` does
not establish public accessibility. Added four parameterized collection cases and a spoof/unverified
route regression. Focused source tests: 43 passed; Ruff passed. Full suite: 384 passed in 62.54 seconds.

## Next verification

Recover the Chrome connection, inspect each supplied URL, record authentication and collection
availability, then select a bounded representative media sample per site. Keep browser navigation,
capture availability, and successful Voidscape inspect/preview/read evidence as separate results.
Resolve the X route from visible navigation; do not silently substitute bookmarks or history.

## Connection diagnostic — 2026-09-06

Supported-path check only; no navigation, no page read, no native-host repair, no cookie,
storage, or credential access.

| Check | Result |
| --- | --- |
| Claude-in-Chrome extension enumeration | One local Windows browser instance connected and addressable |
| ChatGPT-Chrome / agent-browser path | Not retried in this pass; last recorded state was `Browser is not available: chrome` |

The harness-owned Chrome channel is therefore reachable again through the Claude extension. That
result identifies the break as path-specific rather than a dead Chrome or a missing extension: the
earlier failure came from the ChatGPT-Chrome/agent-browser route, not from Chrome itself.

Not yet done, and deliberately not claimed: the Substack archive, Reddit, and X target checks were
**not** retried, because retrying them needs the user to authorize a signed-in session and to select
which connected browser to drive. Page access remains separate from any reader certification, and no
representative media `inspect/preview/read` is claimed from this diagnostic.

## Supported Chrome recovery acceptance — 2026-09-10

Issue #42, tested against repository base `f7cf218`. The supported ChatGPT Chrome
browser-client connection now succeeds through the explicit `chrome` selector.
Session naming, new-tab navigation, visible DOM reads, a visible-link click, viewport
control and a public-page screenshot all returned successfully. No extension installation,
native-host repair, profile inspection, cookies, storage or credentials were used.

The previous failure was in the harness communication path, not evidence that the
websites or media readers were unavailable. Its underlying intermittent cause was not
isolated: this is a verified recovery, not a claim that a repository patch repaired the host.
If communication fails again, follow the installed Chrome skill's supported diagnostics;
do not attempt native-host hacks or substitute a different signed-in browser.

| Previously incomplete target | Fresh visible-page result |
| --- | --- |
| Substack archive | Requested archive loads; Latest tab selected and article previews visible. No article body read or subscription change. |
| Reddit home | Requested home loads with navigation and Feed heading. No collection selected or post interaction. |
| Exact X `/i/histo` | Application loads but displays “Hmm...this page doesn’t exist.” This route is invalid, not a browser-connection failure. |
| X visible History link | Only after observing the navigation link, clicked History; final URL is `https://x.com/i/history`, and the missing-page message is absent. No bookmark/history collection ingestion is claimed. |
| Public Voidscape landing | Capability disclosure opens and its text is readable; desktop screenshot captured through the same supported connection. |

These observations satisfy the remaining target retry scope of #42. They do not certify
bulk capture, private playlist API access, transcription, or any source skill's complete
`inspect -> preview -> read` workflow. Those remain #54/#57/#91 acceptance work.
No private feed bodies, account identifiers, notifications, or browser screenshots are
included in this public record. The exact historical X target is retained above rather
than silently replacing it with bookmarks or the corrected History destination.

### Later responsive-check failure: issue remains open

The same session then requested a 390 x 844 viewport and a DOM overflow check.
That call timed out after 25 seconds and reset the execution session. After reading
the supported browser/Chrome troubleshooting instructions, reconnecting through
the explicit Chrome selector returned `Browser is not available: chrome`.
Consequently the intended viewport reset could not be confirmed. Desktop rendering
and the source results above remain valid observations; mobile QA and durable
connection recovery do not pass. #42 remains open. This record must not auto-close
it or be used to claim a repaired host. No unsupported repair was attempted.

### September 10 follow-up: communication recovered, cause unresolved

A later supported Chrome session successfully loaded the public Voidscape landing,
the previously requested Substack archive and Reddit home. The exact X `/i/histo`
route again displayed the missing-page message; the visible `/i/history` link was
not followed during this retry. No account collection was read or modified.

On the public landing, setting a 390 x 844 viewport succeeded and the DOM overflow
check returned false. The viewport reset call completed without a timeout, and a
subsequent page evaluation succeeded. That evaluation still reported width 390,
so restoration of the original viewport dimensions was not verified.

No extension, native-host, profile or authentication configuration was changed.
These observations establish communication recovery and one successful narrow
viewport check. They do not isolate the earlier failure, establish lasting
reliability, or prove that a code change repaired the connection. Issue #42 remains
open. The earlier failure record above is retained as evidence of intermittency.

### September 11 retry: source checks recovered, initial viewport read invalid

A new supported ChatGPT Chrome session connected through the explicit Chrome
selector and loaded a fresh public Voidscape Agent Docs tab with a complete
visible-DOM read. No extension installation, native-host repair, profile inspection,
cookie/storage access, or account action occurred.

The remaining read-only target checks then completed in the same session:

| Target | Fresh visible-page result |
| --- | --- |
| Substack archive | `Archive - Nelson Lee` loaded at the requested archive URL; Archive and Latest were visible. No article body was read. |
| Reddit home | `Reddit - The heart of the internet` loaded at the requested home URL. No collection or post was selected. |
| Exact X `/i/histo` | The requested URL remained unchanged and X reported its Page not found state after the page settled. No replacement route was followed. |

A temporary 390 x 844 viewport request and reset each returned without an error, but
the original measurement passed its page function as a string literal. That returned
the function object instead of executing it, so the reported 1534 x 1023 dimensions
were not valid viewport evidence. The corrected, bounded measurement is recorded
below; no lower-level workaround was used.

The source checks confirm that this session's Chrome communication path is usable.
They do not identify the intermittent extension/runtime cause, prove durable
stability, certify any source workflow, or replace the separate `inspect -> preview
-> read` and consent gates. Issue #42 remains open for reproducible diagnosis and
reliable supported Chrome operation.

### September 11 correction: viewport control works and reset settles asynchronously

The measurement was repeated in a fresh supported Chrome session on the public
Agent Docs page, using an executable page function. It recorded these values:

| Step | Measured viewport | Document width |
| --- | --- | --- |
| Before override | 1534 x 1023 | 1519 |
| 390 x 844 override | 390 x 844 | 375 |
| 100 ms after reset | 390 x 844 | 375 |
| 1 s after reset | 1534 x 1023 | 1519 |

The supported viewport capability therefore applies correctly. Its reset is
asynchronous, so a measurement immediately after the acknowledgement is not enough
to prove restoration. This corrects the earlier invalid measurement; it does not
identify the intermittent Chrome transport failure, prove durable stability, or
certify a source workflow. No account action, browser-secret access, extension
change, native-host repair, or substitute browser was used. Issue #42 remains open
for a reproducible transport failure and a reliable supported-Chrome resolution.
