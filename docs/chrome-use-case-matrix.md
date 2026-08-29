# Browser and CLI use-case matrix

This matrix separates what was verified on Richard's signed-in machine from the public baseline
other users should be able to reproduce. A personal account is useful test coverage, not proof of a
general capability.

## Browser and remote-control support matrix

- **Richard-tested:** observed on Richard's connected Windows setup.
- **Vendor-documented:** supported by current OpenAI or Anthropic documentation but not reproduced
  as a Voidscape product test.
- **Unverified:** do not publish as a capability claim.

| Capability | Evidence | Boundary |
| --- | --- | --- |
| Browser selection, then host CLI `inspect -> preview -> read` | Richard-tested | The user selects permitted media in a signed-in browser tab; Voidscape runs locally on the host and preserves its normal gates. |
| Mobile continuation and host availability | Vendor-documented | Remote control steers the connected host; it requires that the host remain available, and it does not move local files, browser sessions, or CLI credentials to the phone. |
| DOM, console, and network inspection | Vendor-documented | Availability depends on the documented browser integration and any enabled developer-data capability. |
| Automatic cookie transfer to `yt-dlp` | Unverified and unsupported | Browser access does not silently authenticate the CLI. |
| Automatic support for every model or harness | Unverified and unsupported | Each harness has its own transport, discovery, permission, approval, and host-routing requirements. |

## Verified on 2026-07-19

| Use case | Browser result | CLI result | Conclusion |
| --- | --- | --- | --- |
| Public YouTube video supplied for testing | Page and captions were visible | `inspect` and `preview` passed anonymously; a captions-only read of 02:00-03:00 passed with source-time timestamps | Shipped public path works without browser cookies |
| Unrelated NASA YouTube video with captions | Public result discovered through `yt-dlp` | Anonymous `inspect` and captions preview passed; 7m45s, 3840x2160, captions available | A second unrelated captions source passes without account state |
| Big Buck Bunny YouTube video without captions | Public Blender Foundation video | Anonymous `inspect` passed; captions preview now exits 6 with an actionable local/cloud alternative; local preview passed | No-caption sources no longer receive a false successful captions gate |
| Public OpenAI TikTok video | Public direct post | Anonymous `inspect` and local-backend preview passed; 10s, 720x1280, audio present | Best-effort public TikTok metadata path works for this sample |
| Public NASA Instagram Reel | Visible in Chrome from NASA's public Reels page | Anonymous `inspect` exits 6 with Instagram cookie guidance | A public page can still require platform authentication at the media endpoint |
| Instagram saved collection | Readable in the already authenticated Chrome session | Anonymous `inspect` failed | Saved collections require user-owned authentication; browser access does not automatically authenticate the CLI |
| Nelson Lee Substack | Public article feed readable in Chrome | Media `inspect` failed | Article intake is outside the shipped media CLI |
| AI in Public | Public article feed readable in Chrome | Media `inspect` failed | Article intake is outside the shipped media CLI |

The Chrome checks were read-only. No passwords, browser storage, or cookie contents were read.

## Public/guest regression matrix

Run these before claiming broad source support. Use content that is public, safe to demonstrate, and
permitted for testing.

| Case | Expected result | Status |
| --- | --- | --- |
| Local generated demo fixture | Full `inspect -> preview -> read` succeeds without an account or key | Passed in isolated working-tree copy; dual-root installer passed and the current full suite has 154 tests |
| Random public YouTube video with captions | Anonymous `inspect` and captions preview succeed | Passed with unrelated NASA sample |
| Random public YouTube video without captions | Inspect succeeds; captions-only preview rejects clearly and local/cloud alternatives remain explicit | Passed with Big Buck Bunny after regression fix |
| Direct public Instagram Reel | Either anonymous inspect succeeds or the CLI gives actionable authentication guidance | Passed as an actionable exit 6 on a public NASA Reel; cookie-authenticated retry remains pending |
| Direct public TikTok video | Either anonymous inspect succeeds or the CLI gives an actionable unsupported/auth/network error | Passed anonymously with an OpenAI public post; no dedicated adapter claimed |
| Logged-in Instagram saved folder | Agent can observe the collection after explicit Chrome site approval; selected URL then follows the CLI gate | Browser discovery verified; configured cookie path was stale/missing, so authenticated CLI pass remains pending |
| Logged-in YouTube private playlist or saved queue | User can select an accessible URL; no automatic queue connector is claimed | Planned |
| Public Substack post | Browser workflow can read it; media CLI rejects it honestly | Verified on two sites |
| Subscriber-only Substack post | Browser access requires the user's login and site approval; media CLI remains unsupported | Pending browser check; no CLI claim |
| VPN on/off comparison | Failure is diagnosed as network/region/session behavior rather than silently blamed on media | Pending |

Record the exact URL class, whether the browser was signed in, whether cookies were provided to the
CLI, VPN state, exit code, and sanitized error. Never publish private collection URLs or cookies.

See [Public and authenticated sources](authenticated-sources.md) for setup and troubleshooting.
