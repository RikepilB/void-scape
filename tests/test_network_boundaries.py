"""Short responses and loopback redirects must not widen or truncate reads."""
import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

import pytest

import article
import observe
import voidscape
import video


def test_guided_dispatch_receives_normalized_url(monkeypatch, capsys):
    seen = []
    def probe(value):
        seen.append(value)
        return {"source": "url", "input": value}
    monkeypatch.setattr(voidscape.article_engine, "probe", probe)
    assert voidscape.main(["inspect", "  https://example.com/article  ", "--json"]) == 0
    assert seen == ["https://example.com/article"]


def test_pricing_fallback_matches_reviewed_snapshot():
    snapshot = json.loads(video.PRICING_PATH.read_text(encoding="utf-8"))
    assert snapshot["transcription_per_min"] == video.DEFAULT_PRICING["transcription_per_min"]
    assert snapshot["model_per_mtok"] == video.DEFAULT_PRICING["model_per_mtok"]
    assert snapshot["transcription_per_min"]["groq"] * 60 == pytest.approx(0.111)


@pytest.mark.parametrize("oversized", [False, True])
def test_article_reads_short_chunks_and_enforces_limit(monkeypatch, oversized):
    body = b"<p>complete article</p>"
    class ShortResponse(io.BytesIO):
        headers = {"Content-Type": "text/html; charset=utf-8"}
        def read(self, size=-1):
            return super().read(min(size, 3))
    monkeypatch.setattr(article, "MAX_REMOTE_BYTES", len(body) - 1 if oversized else len(body))
    monkeypatch.setattr(article, "_validate_remote_url", lambda url: url)
    monkeypatch.setattr(article, "_open_url", lambda request, timeout: ShortResponse(body))
    if oversized:
        with pytest.raises(ValueError, match="response limit"):
            article._fetch_url("https://example.com/article")
    else:
        assert article._fetch_url("https://example.com/article") == body.decode()


@pytest.mark.parametrize("redirect", [False, True])
def test_health_stays_on_loopback_ignoring_proxy_and_redirect(monkeypatch, redirect):
    requests = []
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(302 if redirect else 200)
            if redirect:
                self.send_header("Location", "http://127.0.0.1:1/forbidden")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
    monkeypatch.setenv("NO_PROXY", "")
    try:
        result = observe._fetch_health(f"http://localhost:{server.server_port}")
        assert result == (None if redirect else {"status": "healthy"})
        assert requests == ["/health"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
