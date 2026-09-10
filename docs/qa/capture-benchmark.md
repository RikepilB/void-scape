# Screenshot capture benchmark

Issue [#94](https://github.com/RikepilB/void-scape/issues/94). Fixture infrastructure,
not provider acceptance or permission to install Iris. The server uses Python's
standard library, binds only IPv4 loopback, and serves fixed synthetic responses.
It cannot serve local files or proxy a supplied URL. It is a local QA helper, not
a production HTTP service or an enforcement boundary for capture providers.

Run `python scripts/capture_fixture_server.py`. Its first JSON line identifies the
ephemeral port and `/fixture` URL. Keep the process running for selected captures;
Ctrl+C stops it. No browser is launched. Use an already-approved capture tool and
only this server's origin. Do not attach a signed-in profile or private content.

## Cases and expected evidence

| Case | Target | Expected observation |
| --- | --- | --- |
| Viewport | `/fixture`, 800 x 600 CSS pixels | Green target visible; red bottom outside viewport |
| Selected element | `#target`, no padding | 320 x 180 CSS pixels; green target only, black border included |
| Long page | `/fixture`, full-page mode | Both green target and red bottom visible; actual pixel dimensions recorded |
| Delayed resource | `#delayed` | Blue 160 x 80 rectangle after 500 ms server delay; never infer readiness from an HTTP page response alone |
| Delayed font | `#font` | Original synthetic F glyph after 750 ms font response delay; `data-font-ready=true`, or `error` if loading failed |
| Finite animation | `#moving` | Final position after one second; `data-animation-ready` reports the event |
| Scroll-triggered image | `#lazy`, below the red marker | No source until it intersects the viewport; purple rectangle and `data-lazy-ready=true` after scrolling and load |
| Missing selector | `#absent` | Bounded error, no successful screenshot receipt |
| Local redirect | `/redirect` | Final URL `/fixture`, no external navigation |

Page state markers assist diagnosis; pixels remain the visual evidence. Timing
includes OS/browser scheduling and is not deterministic, even though content and
geometry are fixed. Page content is untrusted. System fonts intentionally vary:
do not compare text rasterization across platforms as a pixel-exact golden image.
The font sample uses a 912-byte original geometric glyph, embedded in
`scripts/capture_fixture_font.py`. No third-party font is copied. Regeneration
uses the optional developer-only fontTools library via
`python scripts/generate_capture_font.py`; serving and testing the fixture need
only the standard library. The font contains F and space, not a general alphabet.
Generated with existing fontTools 4.56.0; repeat generation produced identical bytes.
The supported Windows in-app browser rendered `FFF`, with `fontReady=true` and
`document.fonts.check('40px Fixture', 'FFF')` true. This verifies font acceptance
and the visible sample; it does not measure capture-provider waiting behavior.

Windows in-app browser exercise, September 10: at 800 x 600, the lazy image had
no `src` and reported `lazyReady=false`. A supported locator click on the inert
image scrolled it into view; its source became `/lazy.svg`, natural width was 160,
and `lazyReady=true`. A screenshot showed purple pixels below the red marker.
The viewport was reset and the local server stopped afterward. This confirms
the fixture transition, not automatic full-page settling by a capture provider.

## Recording a provider run

Record OS, provider/version, browser/version, fixture revision, viewport, scale,
format and requested mode. Retain the image hash, dimensions, selected scope,
observed final URL, readiness warnings, wall time and failure details. Missing
metadata stays unknown. A successful call is not proof of complete content.

For a CLI provider, measure process startup through final receipt. For MCP,
measure initialization and first capture separately from at least ten subsequent
identical captures. Report sample count, median, nearest-rank p95 and failures;
never silently exclude failed attempts. Do not combine CLI and MCP samples or
claim one proves the other. Browser-tool calls can supply functional observations
but cannot stand in for a provider CLI/MCP performance baseline.

Use a fresh output folder and verify no unintended files are overwritten. Check
timeout cleanup against the tested provider's actual process ownership. A fixture
server's clean shutdown does not prove browser cleanup or output confinement.

## Remaining acceptance

No provider benchmark has been recorded by adding these helpers. Provider
output confinement and timeout cleanup, actual Windows/Linux captures, and
separate CLI/MCP baselines remain outstanding. External redirect denial must be
tested in a separately approved controlled setup, not by navigating to arbitrary
hosts. Iris still needs its pinned scan/review and explicit adoption clearance.

## Controlled policy fixture

`python scripts/capture_policy_fixture.py` starts two ephemeral IPv4 loopback
origins and prints their addresses. Use only these synthetic origins for an
explicitly scoped provider test. Ctrl+C closes both listeners. This fixture cannot
enforce provider permissions: `allowed_origin` and `denied_origin` are test roles,
not grants. It never proxies URLs, serves files or contacts external hosts.

- Configure the approved provider to allow only `allowed_origin`, including its
  exact port. Visit its `/redirect` to test denial of the second origin.
- Visit `/subresource` to test an image request to the second origin. The page
  deliberately has no blocking CSP; a page-level block must not impersonate a
  provider-level policy result.
- Read `/counts` on the first origin before and after each attempt. A successful
  sentinel request increments `sentinel_requests` on the second origin.
- Run a separate positive control that permits the sentinel request, confirming
  that it increments the counter. Restart the fixture between cases so totals
  cannot be confused with earlier attempts; do not reset or edit counters.
- Retain the provider's denial/error receipt and the reached source page/result.
  Zero requests alone is inconclusive: startup failure, a missing page or network
  failure can also produce zero. A positive control is not a denial-policy pass.

The HTTP tests verify redirect reachability, counter changes, fixed routes and
listener cleanup after an exception. They do not establish browser policy
enforcement, DNS-rebinding resistance, general SSRF protection, provider process
cleanup or permission-grant integrity. Those require the actual approved provider.

Windows in-app browser positive control, September 10: `/counts` started at zero.
Opening `/subresource` produced the expected heading/image element and increased
the sentinel count to one. Both origins were selected synthetic loopback servers;
no denying policy was configured or claimed. The fixture process was stopped
afterward. This checks browser-driven request detection, not denial enforcement.
