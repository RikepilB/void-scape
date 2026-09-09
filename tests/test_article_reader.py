"""Local article, HTML, Markdown, and RSS/Atom evidence preparation."""
import json
import socket
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

import article
import voidscape

CLI = Path(__file__).resolve().parent.parent / "skill" / "scripts" / "article.py"

SAMPLE_MARKDOWN = """# Launch Notes

Voidscape reads local articles first.

## Evidence

Cite excerpts with [article 1].
"""

SAMPLE_HTML = """<!DOCTYPE html>
<html><head><title>Product Brief</title></head>
<body><h1>Product Brief</h1><p>Local HTML is supported.</p>
<script>ignored()</script></body></html>
"""

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Engineering Blog</title>
<item>
  <title>First Post</title>
  <link>https://example.com/first</link>
  <guid>guid-1</guid>
  <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
  <description>Alpha content for deterministic ordering.</description>
</item>
<item>
  <title>Second Post</title>
  <link>https://example.com/second</link>
  <guid>guid-2</guid>
  <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
  <description>Beta content follows alpha.</description>
</item>
</channel></rss>
"""

SAMPLE_ATOM = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry>
    <title>Atom One</title>
    <id>atom-1</id>
    <link href="https://example.com/atom-1"/>
    <updated>2024-01-03T00:00:00Z</updated>
    <content>Atom body one.</content>
  </entry>
</feed>
"""

MALFORMED_FEED = "<rss><channel><item><title>broken"

DUPLICATE_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Dup Feed</title>
<item><title>Same</title><guid>dup</guid><description>one</description></item>
<item><title>Same Again</title><guid>dup</guid><description>two</description></item>
</channel></rss>
"""

EMPTY_ITEM_RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
<title>Sparse Feed</title>
<item></item>
<item><title>Real</title><guid>real</guid><description>content</description></item>
</channel></rss>
"""


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(CLI), *map(str, args)],
        capture_output=True, text=True, timeout=60,
    )


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def markdown_article(tmp_path):
    return _write(tmp_path / "notes.md", SAMPLE_MARKDOWN)


@pytest.fixture
def html_article(tmp_path):
    return _write(tmp_path / "brief.html", SAMPLE_HTML)


@pytest.fixture
def rss_feed(tmp_path):
    return _write(tmp_path / "blog.xml", SAMPLE_RSS)


def test_is_article_input_recognizes_local_and_url_sources():
    assert article.is_article_input("post.md") is True
    assert article.is_article_input("feed.xml") is True
    assert article.is_article_input("https://example.com/post") is True
    assert article.is_article_input("https://www.youtube.com/watch?v=abc") is False


def test_probe_markdown_article_has_ordered_citation(markdown_article):
    result = article.probe(str(markdown_article))

    assert result["kind"] == "article"
    assert result["item_count"] == 1
    assert result["entries"][0]["citation"] == "[article 1]"
    assert result["entries"][0]["word_count"] > 0
    assert result["requires_fetch_approval"] is False


def test_probe_html_strips_markup(html_article):
    result = article.probe(str(html_article))

    assert result["entries"][0]["title"] == "Product Brief"
    assert result["entries"][0]["word_count"] == 8


def test_probe_feed_preserves_entry_order_and_counts(rss_feed):
    result = article.probe(str(rss_feed))

    assert result["kind"] == "feed"
    assert result["feed_title"] == "Engineering Blog"
    assert result["item_count"] == 2
    assert [entry["title"] for entry in result["entries"]] == [
        "First Post", "Second Post",
    ]
    assert [entry["citation"] for entry in result["entries"]] == [
        "[entry 1]", "[entry 2]",
    ]


def test_probe_atom_feed(tmp_path):
    feed = _write(tmp_path / "atom.xml", SAMPLE_ATOM)

    result = article.probe(str(feed))

    assert result["kind"] == "feed"
    assert result["entries"][0]["title"] == "Atom One"


def test_probe_url_reports_fetch_requirements():
    result = article.probe("https://example.com/article")

    assert result["source"] == "url"
    assert result["requires_fetch_approval"] is True
    assert result["availability"] == "remote_fetch_required"
    assert "browser credentials" in result["browser_auth_note"]


def test_probe_malformed_feed_raises(tmp_path):
    bad = _write(tmp_path / "bad.xml", MALFORMED_FEED)

    with pytest.raises(ValueError, match="malformed feed XML"):
        article.probe(str(bad))


def test_probe_duplicate_and_empty_entries_are_skipped(tmp_path):
    dup = _write(tmp_path / "dup.xml", DUPLICATE_RSS)
    sparse = _write(tmp_path / "sparse.xml", EMPTY_ITEM_RSS)

    dup_result = article.probe(str(dup))
    sparse_result = article.probe(str(sparse))

    assert dup_result["item_count"] == 1
    assert dup_result["skipped"] == [{"title": "Same Again", "reason": "duplicate"}]
    assert sparse_result["item_count"] == 1
    assert sparse_result["skipped"] == [{"title": "(untitled)", "reason": "empty"}]


def test_probe_rejects_missing_and_empty_files(tmp_path):
    with pytest.raises(FileNotFoundError, match="no such file"):
        article.probe(str(tmp_path / "missing.md"))

    empty = _write(tmp_path / "empty.txt", "   \n")
    with pytest.raises(ValueError, match="document is empty"):
        article.probe(str(empty))


def test_estimate_local_article_needs_no_approval(markdown_article):
    result = article.estimate(str(markdown_article), agent_model="gpt-5.6-terra")

    assert result["requires_cloud_approval"] is False
    assert result["requires_fetch_approval"] is False
    assert result["free"] is True
    assert result["tokens"]["text"] > 0
    assert result["agent_model"] == "gpt-5.6-terra"


def test_estimate_url_requires_fetch_approval():
    result = article.estimate("https://example.com/article")

    assert result["requires_cloud_approval"] is True
    assert result["requires_fetch_approval"] is True
    assert result["free"] is False


def test_estimate_rejects_negative_output_words(markdown_article):
    with pytest.raises(ValueError, match="out_words cannot be negative"):
        article.estimate(str(markdown_article), out_words=-1)


def test_run_writes_ordered_entries_and_manifest(rss_feed, tmp_path):
    workdir = tmp_path / "out"

    result = article.run(str(rss_feed), str(workdir))

    assert result["item_count"] == 2
    assert [entry["citation"] for entry in result["entries"]] == [
        "[entry 1]", "[entry 2]",
    ]
    assert (workdir / "manifest.json").exists()
    assert (workdir / "entries" / "001-First-Post.txt").exists()
    assert (workdir / "entries" / "002-Second-Post.txt").exists()
    saved = json.loads((workdir / "manifest.json").read_text(encoding="utf-8"))
    assert saved == result
    assert "Alpha content" in (workdir / "entries" / "001-First-Post.txt").read_text(
        encoding="utf-8"
    )


def test_run_rejects_url_without_fetch_approval():
    with pytest.raises(PermissionError, match="remote article fetch"):
        article.run("https://example.com/article")


def test_article_probe_redacts_query_and_rejects_credential_or_private_literal_urls():
    result = article.probe("https://example.com/article?private_token=value#fragment")

    assert result["input"] == "https://example.com/article"
    assert result["input_redacted"] is True
    assert "private_token" not in json.dumps(result)
    for value in (
        "https://user:secret@example.com/article",
        "http://127.0.0.1/private",
        "http://169.254.169.254/latest/meta-data",
    ):
        with pytest.raises(ValueError, match="remote article URL"):
            article.probe(value)


def test_run_fetches_url_with_approval(tmp_path):
    remote_html = SAMPLE_HTML

    class FakeResponse:
        headers = {"Content-Type": "text/html; charset=utf-8"}

        def read(self, _size=-1):
            if getattr(self, "consumed", False):
                return b""
            self.consumed = True
            return remote_html.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    with (
        mock.patch("article._validate_remote_url", side_effect=lambda url: url),
        mock.patch("article._open_url", return_value=FakeResponse()),
    ):
        result = article.run(
            "https://example.com/brief",
            str(tmp_path / "remote"),
            allow_fetch=True,
        )

    assert result["item_count"] == 1
    assert result["source"] == "url"


def test_run_maps_http_auth_errors_to_browser_boundary():
    import urllib.error

    error = urllib.error.HTTPError(
        "https://example.com/private", 403, "Forbidden", {}, None,
    )
    with (
        mock.patch("article._validate_remote_url", side_effect=lambda url: url),
        mock.patch("article._open_url", side_effect=error),
    ):
        with pytest.raises(PermissionError, match="browser access"):
            article.run("https://example.com/private", allow_fetch=True)


def test_run_maps_network_failures_to_operation_error():
    import urllib.error

    with (
        mock.patch("article._validate_remote_url", side_effect=lambda url: url),
        mock.patch(
            "article._open_url",
            side_effect=urllib.error.URLError("connection reset"),
        ),
    ):
        with pytest.raises(RuntimeError, match="network fetch failed"):
            article.run("https://example.com/down", allow_fetch=True)


def _resolver(*addresses: str):
    def resolve(_host, port, **options):
        assert options["type"] == socket.SOCK_STREAM
        return [
            (socket.AF_INET6 if ":" in address else socket.AF_INET,
             options["type"], 6, "", (address, port))
            for address in addresses
        ]

    return resolve


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:secret@example.com/private",
        "https://example.com:80/article",
        "https://example.com:8080/article",
        "http://example.com:443/article",
        "https://example.com:99999/article",
    ],
)
def test_remote_url_rejects_unsafe_url_shapes(url):
    with pytest.raises(ValueError, match="remote article URL"):
        article._validate_remote_url(url, resolver=_resolver("93.184.216.34"))


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "169.254.169.254", "::1", "fe80::1"],
)
def test_remote_url_rejects_non_public_addresses(address):
    with pytest.raises(ValueError, match="non-public network address"):
        article._validate_remote_url(
            "https://example.com/article",
            resolver=_resolver(address),
        )


def test_remote_url_requires_every_resolved_address_to_be_public():
    with pytest.raises(ValueError, match="non-public network address"):
        article._validate_remote_url(
            "https://example.com/article",
            resolver=_resolver("93.184.216.34", "127.0.0.1"),
        )


def test_remote_url_accepts_public_addresses_and_strips_fragment():
    result = article._validate_remote_url(
        "https://example.com/article#section",
        resolver=_resolver("93.184.216.34", "2606:2800:220:1:248:1893:25c8:1946"),
    )

    assert result == "https://example.com/article"


def test_remote_fetch_revalidates_and_rejects_redirect_target():
    import urllib.error

    redirect = urllib.error.HTTPError(
        "https://example.com/start",
        302,
        "Found",
        {"Location": "https://127.0.0.1/admin"},
        None,
    )
    with (
        mock.patch("article._open_url", side_effect=redirect),
        mock.patch(
            "article.socket.getaddrinfo",
            side_effect=lambda host, port, **options: _resolver(
                "93.184.216.34" if host == "example.com" else "127.0.0.1"
            )(host, port, **options),
        ),
    ):
        with pytest.raises(ValueError, match="non-public network address"):
            article._fetch_url("https://example.com/start")


def test_remote_fetch_pins_connection_to_revalidated_public_address():
    class FakeResponse:
        status = 200
        reason = "OK"
        headers = {"Content-Type": "text/html"}

        def read(self, _size=-1):
            if getattr(self, "consumed", False):
                return b""
            self.consumed = True
            return b"<p>safe</p>"

        def close(self):
            return None

    connection = mock.Mock()
    connection.getresponse.return_value = FakeResponse()
    with (
        mock.patch("article.socket.getaddrinfo", side_effect=_resolver("93.184.216.34")),
        mock.patch("article._connection_for", return_value=connection) as connection_for,
    ):
        response = article._open_url(
            article.Request("https://example.com/article?view=1"),
            2.0,
        )
        assert response.read() == b"<p>safe</p>"
        response.close()

    parsed = connection_for.call_args.args[0]
    assert parsed.hostname == "example.com"
    assert connection_for.call_args.args[1] == "93.184.216.34"
    connection.request.assert_called_once()
    assert connection.request.call_args.args[1] == "/article?view=1"


def test_remote_fetch_rechecks_dns_before_connection_to_block_rebinding():
    with (
        mock.patch("article._validate_remote_url", side_effect=lambda url: url),
        mock.patch("article.socket.getaddrinfo", side_effect=_resolver("127.0.0.1")),
    ):
        with pytest.raises(ValueError, match="non-public network address"):
            article._fetch_url("https://example.com/article")


def test_remote_fetch_refuses_https_redirect_downgrade():
    import urllib.error

    redirect = urllib.error.HTTPError(
        "https://example.com/start",
        302,
        "Found",
        {"Location": "http://example.com/plain"},
        None,
    )
    with (
        mock.patch("article._validate_remote_url", side_effect=lambda url: url),
        mock.patch("article._open_url", side_effect=redirect),
    ):
        with pytest.raises(RuntimeError, match="redirect downgrade"):
            article._fetch_url("https://example.com/start")


def test_remote_fetch_rejects_large_or_binary_response():
    class FakeResponse:
        def __init__(self, content_type, body):
            self.headers = {"Content-Type": content_type}
            self.body = body

        def read(self, size=-1):
            return self.body[:size]

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    with mock.patch("article._validate_remote_url", side_effect=lambda url: url):
        with mock.patch(
            "article._open_url",
            return_value=FakeResponse("application/octet-stream", b"binary"),
        ):
            with pytest.raises(ValueError, match="unsupported content type"):
                article._fetch_url("https://example.com/file")
        with mock.patch(
            "article._open_url",
            return_value=FakeResponse("text/html", b"x" * (article.MAX_REMOTE_BYTES + 1)),
        ):
            with pytest.raises(ValueError, match="response limit"):
                article._fetch_url("https://example.com/large")


def test_remote_fetch_rejects_missing_or_compressed_content_type_contract():
    class FakeResponse:
        def __init__(self, headers):
            self.headers = headers

        def read(self, _size=-1):
            return b"<p>content</p>"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    with mock.patch("article._validate_remote_url", side_effect=lambda url: url):
        with mock.patch("article._open_url", return_value=FakeResponse({})):
            with pytest.raises(ValueError, match="unsupported content type"):
                article._fetch_url("https://example.com/missing-type")
        with mock.patch(
            "article._open_url",
            return_value=FakeResponse({"Content-Type": "text/html", "Content-Encoding": "gzip"}),
        ):
            with pytest.raises(ValueError, match="content encoding"):
                article._fetch_url("https://example.com/compressed")


def test_feed_rejects_document_type_and_entity_declarations(tmp_path):
    malicious = _write(
        tmp_path / "entity.xml",
        '<!DOCTYPE rss [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        '<rss><channel><item><description>&xxe;</description></item></channel></rss>',
    )

    with pytest.raises(ValueError, match="document type or entity"):
        article.probe(str(malicious))


def test_run_rejects_nonempty_workdir(rss_feed, tmp_path):
    workdir = tmp_path / "out"
    workdir.mkdir()
    (workdir / "stale.txt").write_text("stale", encoding="utf-8")

    with pytest.raises(ValueError, match="workdir already exists and is not empty"):
        article.run(str(rss_feed), str(workdir))


def test_cli_manifest_and_envelope_contract(markdown_article):
    manifest = _cli("manifest", "--compact")
    probe = _cli("probe", markdown_article, "--envelope", "--compact")

    assert manifest.returncode == 0, manifest.stderr
    contract = json.loads(manifest.stdout)
    assert set(contract["commands"]) == {"manifest", "probe", "estimate", "run"}
    assert probe.returncode == 0, probe.stderr
    payload = json.loads(probe.stdout)
    assert payload["ok"] is True
    assert payload["data"]["kind"] == "article"


def test_guided_article_inspect_preview_and_read(markdown_article, tmp_path, capsys):
    assert voidscape.main(["inspect", str(markdown_article)]) == 0
    inspected = capsys.readouterr().out
    assert "Article: 1 entry" in inspected
    assert "Launch Notes" in inspected

    assert voidscape.main(["preview", str(markdown_article)]) == 0
    previewed = capsys.readouterr().out
    assert "text tokens:" in previewed
    assert "prepared locally" in previewed

    workdir = tmp_path / "evidence"
    assert voidscape.main([
        "read", str(markdown_article), "--workdir", str(workdir),
    ]) == 0
    read_out = capsys.readouterr().out
    assert "Entries: 1" in read_out
    assert "[article 1]" in read_out
    assert (workdir / "manifest.json").exists()


def test_guided_url_preview_requires_cloud_consent(capsys):
    assert voidscape.main(["preview", "https://example.com/post"]) == 0
    previewed = capsys.readouterr().out
    assert "--allow-cloud" in previewed

    assert voidscape.main(["read", "https://example.com/post"]) == 4
    assert "remote article fetch" in capsys.readouterr().err


def test_video_url_never_dispatches_to_article_engine(monkeypatch):
    def unexpected_article_probe(_input):
        raise AssertionError("video URL dispatched to article engine")

    monkeypatch.setattr(voidscape.article_engine, "probe", unexpected_article_probe)

    assert voidscape._is_article_source("https://www.youtube.com/watch?v=abc") is False
    assert voidscape._is_article_source("https://example.com/post") is True
