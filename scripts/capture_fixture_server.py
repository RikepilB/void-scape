"""Serve fixed synthetic screenshot fixtures on IPv4 loopback; never serve files."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time

from capture_fixture_font import FONT


PAGE = b"""<!doctype html><html lang="en"><meta charset="utf-8">
<title>Capture reliability fixture</title>
<style>
@font-face { font-family: Fixture; src: url('/delayed.ttf') format('truetype'); font-display: swap; }
#font { font: 40px Fixture, monospace; }
* { box-sizing: border-box; } body { margin: 0; font: 20px sans-serif; }
#target { width: 320px; height: 180px; background: #149646; color: white;
padding: 20px; border: 4px solid black; }
#moving { width: 120px; background: gold; animation: settle 1s linear forwards; }
@keyframes settle { from { transform: translateX(200px); }
to { transform: translateX(0); } }
.spacer { height: 2200px; background: #ddd; }
#bottom { height: 180px; background: #d02030; color: white; }
</style><h1>PUBLIC SYNTHETIC FIXTURE</h1>
<section id="target">GREEN TARGET ONLY</section>
<p id="font" aria-label="Synthetic font sample">FFF</p>
<p id="moving">ANIMATION END</p>
<img id="delayed" src="/delayed.svg" width="160" height="80"
alt="Delayed blue rectangle: pending">
<div class="spacer">Below-viewport content follows</div>
<section id="bottom">RED BOTTOM MARKER</section>
<img id="lazy" width="160" height="80" alt="Lazy purple rectangle: pending">
<script>
document.documentElement.dataset.fontReady = 'false';
document.fonts.load('40px Fixture', 'FFF').then(fonts => {
  document.documentElement.dataset.fontReady = String(fonts.length > 0);
}, () => { document.documentElement.dataset.fontReady = 'error'; });
const image = document.querySelector('#delayed');
function ready() {
  document.documentElement.dataset.imageReady = image.complete && image.naturalWidth > 0;
  if (image.complete && image.naturalWidth > 0) image.alt = 'Loaded blue rectangle';
}
image.addEventListener('load', ready); ready();
document.querySelector('#moving').addEventListener('animationend', () => {
  document.documentElement.dataset.animationReady = 'true';
});
const lazy = document.querySelector('#lazy');
document.documentElement.dataset.lazyReady = 'false';
lazy.addEventListener('load', () => {
  document.documentElement.dataset.lazyReady = 'true';
  lazy.alt = 'Loaded purple rectangle';
});
const observer = new IntersectionObserver(entries => {
  if (entries.some(entry => entry.isIntersecting)) {
    lazy.src = '/lazy.svg';
    observer.disconnect();
  }
}, {rootMargin: '0px', threshold: 0});
observer.observe(lazy);
</script></html>"""
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="160" height="80"><rect width="160" height="80" fill="blue"/></svg>'
LAZY_SVG = SVG.replace(b'fill="blue"', b'fill="purple"')


class FixtureHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Exact routes: no path decoding, disk access, proxying or query controls.
        if self.path == "/redirect":
            self.send_response(302)
            self.send_header("Location", "/fixture")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if self.path == "/fixture":
            payload, media_type = PAGE, "text/html; charset=utf-8"
        elif self.path == "/delayed.svg":
            time.sleep(0.5)
            payload, media_type = SVG, "image/svg+xml"
        elif self.path == "/lazy.svg":
            payload, media_type = LAZY_SVG, "image/svg+xml"
        elif self.path == "/delayed.ttf":
            time.sleep(0.75)
            payload, media_type = FONT, "font/ttf"
        else:
            self.send_error(404, "Unknown fixture route")
            return
        self.send_response(200)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; "
                         "font-src 'self'; "
                         "script-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; "
                         "form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A capture timeout can disconnect while the delayed image settles.

    def log_message(self, format, *args):
        pass  # Do not retain request paths supplied by a client.


def make_server(port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), FixtureHandler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be between 0 and 65535")
    with make_server(args.port) as server:
        print(json.dumps({"fixture_url": f"http://127.0.0.1:{server.server_port}/fixture",
                          "content_trust": "untrusted"}), flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
