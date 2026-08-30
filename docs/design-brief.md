# Voidscape landing design brief

## Product and audience

Voidscape is a local-first CLI and agent skill for turning user-approved video, audio, images,
articles, and feeds into inspectable evidence. The landing page serves technical users and agent
builders who need to understand the trust boundary before they install anything.

The primary job is to make the `inspect -> preview -> read` sequence legible. The conversion is an
informed visit to the guide, install instructions, or source—not an ungrounded signup claim.
Proof comes from shipped commands, manifests, tests, and explicit capability status. Do not invent
usage numbers, testimonials, or customer logos.

## Story and hierarchy

1. A source is opaque until it is inspected.
2. Preview exposes cost, network, and model-download boundaries before work begins.
3. Read produces local, citable evidence through one stable sequence.
4. Command, protocol, capability, and use-case sections show how the product earns that promise.
5. Installation ends with a key-free fixture so the first proof is reproducible.

## Art direction

Treat the page as a nocturnal evidence instrument, not a generic space-themed SaaS site. The
orb-in-orbit mark represents a source crossing a visible consent boundary; terminal surfaces and
protocol labels come directly from the CLI. Blue-to-lilac gradients belong to the orb, signal, and
primary action—not every surface.

Preserve the existing ink background, light capability board, display/mono typography pairing,
and compact evidence labels. Avoid stock space art, fake dashboards, decorative glass layers,
gratuitous glow, or claims that are not present in the repository.

## Interaction and accessibility

- Keep one visually dominant workflow action while leaving the guide and source available.
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
