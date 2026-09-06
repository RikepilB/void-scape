# Browser QA report: Voidscape

| Field | Value |
|---|---|
| Date | 2026-09-04 |
| Public URL | `https://voidscape.club/` |
| Viewports | Mobile `375x812`; desktop `1280x900` |
| Scope | Public navigation, responsive rendering, interactive documentation controls, console/page errors, and homepage carousel behavior |
| Overall result | Pass; no reproducible product issues |

## Summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| **Total** | **0** |

## Route coverage

All 22 public HTML routes passed at `375x812`: exactly one `h1`, no document-level horizontal overflow, no broken images, no third-party runtime resources, and no page errors reported by agent-browser.

- Product: `/`, `/guide.html`, `/faq.html`, `/privacy.html`, `/terms.html`.
- Agent Docs: `/agents/`, `/agents/automation.html`, `/agents/concepts.html`, `/agents/constraints.html`, `/agents/harnesses.html`, `/agents/install.html`, `/agents/observe-and-capture.html`, `/agents/quick-start.html`, `/agents/references.html`, `/agents/roadmap-status.html`, `/agents/troubleshooting.html`, `/agents/workflow.html`.
- Capture adapters: `/agents/capture-adapters/instagram.html`, `/agents/capture-adapters/youtube.html`.
- Readers: `/agents/readers/articles-rss.html`, `/agents/readers/images.html`, `/agents/readers/video-audio.html`.

Desktop checks at `1280x900` also passed for all five product routes plus `/agents/`, `/agents/quick-start.html`, `/agents/observe-and-capture.html`, and `/agents/roadmap-status.html`.

## Interaction checks

- Theme toggle changed the active theme and accessible label.
- Agent Docs mobile menu opened and closed with the correct expanded state and overlay.
- Documentation search opened, filtered for `Instagram`, supported `ArrowDown` and `Enter` navigation, and returned focus to the search button after `Escape`.
- Guide code blocks scrolled inside their containers without causing document overflow.
- FAQ content and responsive layout rendered correctly.
- Homepage carousel passed an independent clean Chrome-for-Testing CDP check: selecting dot 3 changed the mode to `Manual`, live status to use case 3, and zero-based current index to `2`; the state remained unchanged after seven seconds.
- The deployed and local `landing.js` files were identical after normalization. No deployment drift was found.

## Evidence

Validated visual captures in `screenshots/`:

- `desktop-initial.png`
- `desktop-light-mode.png`
- `home-mobile.png`
- `faq-mobile.png`
- `guide-mobile.png`
- `agents-automation-mobile.png`
- `agents-mobile-menu-open.png`
- `agents-search-instagram-mobile.png`
- `agents-roadmap-desktop.png`
- `carousel-use-case-4-immediate.png` (visual state only; not persistence evidence)

Excluded exploratory artifacts:

- `issue-001-step-1-auto.png`
- `issue-001-step-2-selected-3.png`
- `issue-001-result-auto-advanced.png`
- `videos/issue-001-carousel-manual-stop.webm`

The excluded `issue-001` artifacts came from an invalid agent-browser interaction sequence and do not reproduce a product defect. The clean Chrome-for-Testing check above is the authoritative behavioral result.

## Tooling and access notes

- Agent-browser intermittently returned Windows socket error `10060`. Fresh isolated sessions completed the route and interaction checks, so this is recorded as tooling reliability, not a site defect.
- Signed-in Chrome control was unavailable at the ChatGPT extension/runtime handshake. No signed-in workflows, credentials, cookies, storage, sends, or publishing actions were performed.

## Issues

None reproduced.
