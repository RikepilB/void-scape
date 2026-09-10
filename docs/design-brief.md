# Voidscape landing design brief

## Product and audience

Voidscape is a local-first CLI and agent skill for turning user-approved video, audio, images,
articles, and feeds into inspectable evidence. The landing page serves technical users and agent
builders who need to understand the trust boundary before they install anything.

The primary job is to make the result and the `inspect -> preview -> read` mechanism legible fast.
The conversion is a jump to the honest source-install section, followed by a guide or Agent Docs
visit when the reader needs detail—not an ungrounded signup claim. Proof comes from shipped
commands, manifests, tests, and concrete use cases. Do not invent usage numbers, testimonials, or
customer logos.

## Story and hierarchy

1. Show the outcome: media becomes local evidence an agent can cite.
2. Explain the mechanism once: inspect, preview, then read.
3. Demonstrate breadth through one focused use-case carousel, not an inventory wall.
4. Make the no-clone CLI install the obvious action and explain its present-day shape honestly.
5. Route command detail, capability status, and long reference material to Guide and Agent Docs.

## Art direction

Treat the page as a nocturnal evidence instrument, not a generic space-themed SaaS site. The
orb-in-orbit mark represents a source crossing a visible consent boundary; terminal surfaces and
protocol labels come directly from the CLI. Blue-to-lilac gradients belong to the orb, signal, and
primary action—not every surface.

Preserve the existing nocturnal evidence-instrument identity, display/mono typography pairing, and
compact evidence labels in both dark and light modes. Use the shipped orb-in-orbit asset as the
header logo. The memorable product-derived visual is one evidence reel: a single large use case at
a time, moving automatically until the reader chooses a slide. Avoid inventory walls, stock space
art, fake dashboards, decorative glass layers, gratuitous glow, or repository-unsupported claims.

## Page architecture

1. Sticky identity/navigation bar with the real logo, Download action, and theme control.
2. Direct hero: outcome, one-line mechanism, Download primary action, Guide secondary action.
3. Three-step workflow: inspect, preview, read—no duplicate five-command reference.
4. One-frame use-case reel: six shipped scenarios, manual controls, and restrained autoplay.
5. Compact consent/cost proof.
6. Honest CLI installation: install from the GitHub source archive, initialize the bundled skill,
   and run one readiness check.
7. Three essential FAQs and the full FAQ link.

The Guide owns the five-command explanation and fuller workflow context. Agent Docs owns capability
status, reader contracts, adapters, automation, and troubleshooting.

## Interaction and accessibility

- Keep one visually dominant workflow action while leaving the guide and source available.
- Keep the header sticky after scroll and provide a quiet back-to-top control on long pages.
- Start from the operating-system color preference; theme changes do not use cookies or browser
  storage, preserving the public privacy contract.
- Advance the use-case reel automatically, pause while hovered or focused, and stop permanently
  after manual navigation so the selected use case stays put.
- Use product-derived line icons; they remain decorative and hidden from assistive technology.
- Keep terminal examples horizontally scrollable inside their cards instead of widening the page.
- Preserve visible focus states, semantic headings, reduced-motion handling, and sufficient contrast.
- Support 1280 px desktop and 375 px mobile without horizontal document overflow.

## Release checks

- Confirm every capability and roadmap label against current `main`.
- Run the full Python suite and the site wording tests.
- Verify all five HTML pages reference SVG, 32 px PNG, and Apple touch favicons.
- Inspect desktop and mobile rendering locally, then repeat against `https://voidscape.club/` after
  the production deployment is ready.
- Verify both themes, sticky navigation, logo rendering, use-case autoplay/manual-stop behavior,
  Download anchors, and the back-to-top threshold/action.

## 2026-09-10 acceptance review

Reviewed the live capabilities section against this brief using the approved Chrome
harness. The available/in-progress/next/later disclosures preserve a readable hierarchy,
concrete mechanism and honest boundaries. Keep the existing restrained dark treatment
and native disclosure interaction; no visual redesign is indicated by this state.

Visual verdict: **partial / mobile unverified**. The desktop screenshot and opening
the in-progress disclosure succeeded. A subsequent 390 x 844 responsive request timed
out, reset the connection, and Chrome could not be reselected. Therefore this pass does
not establish mobile overflow, focus/keyboard, light-theme or reduced-motion acceptance.
Recheck those states after supported connection recovery (#42), rather than treating
passing Python/site tests as visual proof. No public UI files were changed in this pass.
