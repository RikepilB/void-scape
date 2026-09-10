import threading
import time
import urllib.error
import urllib.request

import pytest

from capture_fixture_server import make_server


@pytest.fixture
def fixture_url():
    with make_server() as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        yield f"http://127.0.0.1:{server.server_port}"
        server.shutdown()
        thread.join(timeout=3)
        assert not thread.is_alive()


def fetch(url):
    # Avoid workstation proxy configuration even for this synthetic loopback test.
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=3)


def test_fixture_and_local_redirect(fixture_url):
    with fetch(fixture_url + "/redirect") as response:
        assert response.url == fixture_url + "/fixture"
        body = response.read()
        assert b"GREEN TARGET ONLY" in body
        assert b"RED BOTTOM MARKER" in body
        assert b'id="absent"' not in body
        assert response.headers["Cache-Control"] == "no-store"
        assert "connect-src 'none'" in response.headers["Content-Security-Policy"]


@pytest.mark.parametrize("path", ["/", "/../AGENTS.md", "/%2e%2e/AGENTS.md",
                                  "/fixture?url=https://example.com", "/favicon.ico"])
def test_unknown_paths_never_serve_files(fixture_url, path):
    with pytest.raises(urllib.error.HTTPError) as error:
        fetch(fixture_url + path)
    assert error.value.code == 404


def test_delayed_resource_does_not_block_other_requests(fixture_url):
    result = []

    def delayed():
        with fetch(fixture_url + "/delayed.svg") as response:
            result.append(response.read())

    start = time.monotonic()
    thread = threading.Thread(target=delayed)
    thread.start()
    with fetch(fixture_url + "/fixture") as response:
        assert response.status == 200
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert time.monotonic() - start >= 0.5
    assert result and b'fill="blue"' in result[0]


def test_lazy_image_requires_page_trigger(fixture_url):
    with fetch(fixture_url + "/fixture") as response:
        body = response.read()
    assert b'<img id="lazy" width="160" height="80"' in body
    assert b'<img id="lazy" src=' not in body
    with fetch(fixture_url + "/lazy.svg") as response:
        assert response.headers["Content-Type"] == "image/svg+xml"
        assert b'fill="purple"' in response.read()
