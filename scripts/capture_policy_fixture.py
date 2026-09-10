"""Two loopback origins for scoped capture-policy QA; no external URLs."""
import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

SENTINEL = b'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40"><rect width="40" height="40" fill="red"/></svg>'


class Handler(BaseHTTPRequestHandler):
    def reply(self, status, content_type, payload, location=None):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        if location:
            self.send_header("Location", location)
        self.end_headers()
        try:
            self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, format, *args):
        pass


class SinkHandler(Handler):
    def do_GET(self):
        if self.path != "/sentinel.svg":
            self.reply(404, "text/plain", b"Unknown route")
            return
        with self.server.hit_lock:
            self.server.hits += 1
        self.reply(200, "image/svg+xml", SENTINEL)


class SourceHandler(Handler):
    def do_GET(self):
        if self.path == "/redirect":
            self.reply(302, "text/plain", b"", self.server.sentinel_url)
        elif self.path == "/subresource":
            # No CSP blocks this image: the provider's policy must deny it.
            page = ('<!doctype html><html lang="en"><meta charset="utf-8">'
                    '<title>Synthetic policy fixture</title><h1>DENIED ORIGIN TEST</h1>'
                    f'<img src="{self.server.sentinel_url}" alt="Denied-origin sentinel" '
                    'width="40" height="40"></html>')
            self.reply(200, "text/html; charset=utf-8", page.encode("utf-8"))
        elif self.path == "/counts":
            with self.server.sink.hit_lock:
                payload = json.dumps({"sentinel_requests": self.server.sink.hits}).encode("ascii")
            self.reply(200, "application/json", payload)
        else:
            self.reply(404, "text/plain", b"Unknown route")


@contextlib.contextmanager
def fixture_pair():
    """Own and close both servers, including when a test raises or is interrupted."""
    with contextlib.ExitStack() as resources:
        sink = resources.enter_context(ThreadingHTTPServer(("127.0.0.1", 0), SinkHandler))
        source = resources.enter_context(ThreadingHTTPServer(("127.0.0.1", 0), SourceHandler))
        sink.hits = 0
        sink.hit_lock = threading.Lock()
        source.sink = sink
        source.sentinel_url = f"http://127.0.0.1:{sink.server_port}/sentinel.svg"
        for server in (sink, source):
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            resources.callback(thread.join, 3)
            resources.callback(server.shutdown)
        yield {"allowed_origin": f"http://127.0.0.1:{source.server_port}",
               "denied_origin": f"http://127.0.0.1:{sink.server_port}",
               "content_trust": "untrusted"}


def main():
    with fixture_pair() as origins:
        print(json.dumps(origins), flush=True)
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
