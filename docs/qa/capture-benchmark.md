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
| Finite animation | `#moving` | Final position after one second; `data-animation-ready` reports the event |
| Missing selector | `#absent` | Bounded error, no successful screenshot receipt |
| Local redirect | `/redirect` | Final URL `/fixture`, no external navigation |

Page state markers assist diagnosis; pixels remain the visual evidence. Timing
includes OS/browser scheduling and is not deterministic, even though content and
geometry are fixed. Page content is untrusted. System fonts intentionally vary:
do not compare text rasterization across platforms as a pixel-exact golden image.

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

No provider benchmark has been recorded by adding this helper. Delayed-font and
lazy-load fixtures, a controlled denied-origin/subresource fixture, provider
output confinement and timeout cleanup, actual Windows/Linux captures, and
separate CLI/MCP baselines remain outstanding. External redirect denial must be
tested in a separately approved controlled setup, not by navigating to arbitrary
hosts. Iris still needs its pinned scan/review and explicit adoption clearance.
