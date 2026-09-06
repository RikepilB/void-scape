# Landing capability release checks

Scope: landing copy and regression tests only. No CLI/skill upgrade, plugin, browser extension,
Iris installation, account mutation or scheduled job is included in this release.

The approved design brief remains in force: reuse the existing FAQ disclosure styles, preserve
the six-use-case evidence reel and installation flow, and avoid a second card inventory.

## Landing audit

| Check | Result | Follow-up |
| --- | --- | --- |
| robots.txt | Missing in repository | Optional crawl-policy follow-up |
| Description | Present, under 160 characters on landing (code) | Cross-page uniqueness not audited here |
| Title | Present on landing (code) | Cross-page uniqueness not audited here |
| Favicons | SVG, PNG and Apple references present (code) | Live asset requests after deploy |
| Social cards | Missing OG/Twitter tags (code) | Optional sharing-metadata follow-up |
| Privacy / terms | Both linked (code) | Presence does not establish legal sufficiency |
| Contact | Source repository and security link available (code) | Dedicated contact clarity can improve |
| HTTPS | Post-deploy check required | Verify certificate and status through normal HTTPS request |
| Primary CTA | Existing installation action unchanged (code) | Above-fold appearance not newly verified |
| Product proof | Existing evidence examples and source links (code) | No invented customer claims |
| FAQ | Existing FAQ plus status disclosures (code) | Native keyboard interaction; render check pending |
| Domain | Existing voidscape.club unchanged | No action |
| Responsive layout | Existing responsive styles reused (code) | New mobile/desktop rendering unverified |
| Sticky navigation | Existing implementation unchanged (code) | Live scroll behavior unverified |
| Analytics | No analytics script identified (code) | Do not add tracking without a separate decision |

## Anti-slop review

Copy/code review: no new visual system, invented proof, or unsupported installed capabilities.
The new section separates available readers, designed capture/visual jobs, and exploration.
Full visual verdict remains unverified: isolated browser startup timed out and the supported
Chrome connection was unavailable. Do not present this report as a screenshot/render pass.

## Production-readiness advisory

| Item | Status | Recommendation |
| --- | --- | --- |
| Analytics | Missing | Deliberately leave tracking unchanged; not blocking |
| Public forms / CAPTCHA | N/A for this change | No new submission surface |
| Privacy / terms | Present | No new data collection; legal sufficiency not assessed |
| Rollback | GitHub Pages serves main /docs | Revert the landing release commit through a normal reviewed commit, then verify Pages |

Advisory gaps are not blocking; user retains the decision. Automated test results, merge SHA,
and deployment evidence are recorded in the release handoff, not inferred from this checklist.
