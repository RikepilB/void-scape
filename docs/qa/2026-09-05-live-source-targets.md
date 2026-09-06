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
