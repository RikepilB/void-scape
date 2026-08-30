# Design brief — Voidscape agent documentation

## Product and conversion

- **Audience and context:** agents, agent builders, and technical users arriving with a source they
  want to read safely. They may be scanning during an active task, not browsing marketing copy.
- **Job to be done:** find the correct command or boundary, run a first evidence read, and know what
  the resulting artifacts authorize an agent to claim.
- **Primary action:** complete the Quick start through `inspect -> preview -> read`.
- **Proof available:** executable commands, reader manifests, tests, citation contracts, and status
  labels tied to current `main`. Do not add testimonials, adoption metrics, or universal support claims.

## Story

Opaque source -> inspect facts -> preview cost and permission boundaries -> read approved evidence
-> answer with exact citations. Navigation should move from onboarding to operation, focused readers,
agent environments, repository-only adapters, reference, and troubleshooting in that order.

## Art direction

- **Register:** product documentation, not a second marketing page.
- **Physical scene:** a quiet operator's manual beside an evidence console: dense enough to scan,
  restrained enough to read for twenty minutes.
- **Lane:** dark technical editorial with ink surfaces, thin structural rules, and a blue signal
  color. The orb mark identifies the product; protocol labels and code are the memorable visual idea.
- **Guardrails:** learn from Herdr's hierarchy, not its brand. Do not clone its logo, wording, exact
  colors, typography, or component code. Avoid glass cards, gradient text, decorative space art,
  oversized marketing headlines, fake version/language controls, and unexplained status badges.

## System

- **Identity:** reuse the shipped orb-in-orbit favicon and Voidscape wordmark.
- **Color:** ink page, slightly raised navigation surfaces, paper text, muted explanatory text,
  blue for links/focus/current location, lilac only for secondary protocol signals.
- **Type:** existing Aptos display/body with Cascadia Mono for commands and machine contracts.
- **Layout:** sticky header; persistent left information architecture; readable article column;
  sticky on-page outline. At mobile widths, the left navigation becomes a drawer and the page outline
  becomes a compact disclosure above the article.
- **Interaction:** local search via Ctrl/Cmd+K, copy buttons, anchor links, previous/next pages, and a
  non-persistent light/dark toggle. No analytics, cookies, external fonts, or browser storage.

## Content architecture

1. **Start here:** Overview routes readers by intent; Install verifies readiness; Quick start is a
   complete runnable path; Concepts explains the mental model.
2. **Operate:** Workflow, Automation, and Observe/capture are imperative how-to guides.
3. **Readers:** focused source support, gates, outputs, and citation contracts.
4. **Agent environments:** harness evidence and non-negotiable permission boundaries.
5. **Capture adapters:** clearly dev-only repository helpers, never confused with installed commands.
6. **Reference:** current status, discovery manifest, canonical architecture, and sources.
7. **Help:** symptom -> likely cause -> safe next command; never bypass a gate as a fix.

Every article starts with what the page helps accomplish. Commands sit next to the decision they
support. Reference tables are exhaustive; tutorials stay linear; status pages separate shipped,
dev-only, planned, and parked work.

## Verification

- Inspect 1440x900 and 375x812 on Overview, Quick start, one long how-to, and one dense table page.
- Verify keyboard search, Escape close, menu open/close, copy feedback, theme toggle, active page,
  anchor navigation, previous/next links, and zero horizontal document overflow.
- Require semantic landmarks, skip link, visible focus, reduced motion, readable line length, and
  no external runtime requests.
- Run the renderer drift check, full pytest suite, local-link check, and anti-slop review before any
  release is proposed.
