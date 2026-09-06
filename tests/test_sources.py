"""Source capability registry and guided reader routing."""
import json

import pytest

import sources
import voidscape


def test_registry_covers_named_upgrade_platforms_without_universal_claim():
    manifest = sources.manifest()
    platform_ids = {profile["id"] for profile in manifest["platforms"]}

    assert {
        "instagram", "youtube", "substack", "linkedin", "x-twitter", "reddit", "tiktok",
    } <= platform_ids
    assert manifest["boundaries"]["platform_compatibility_is_not_universal"] is True
    assert manifest["boundaries"]["browser_credentials_cookies_storage_read"] is False


@pytest.mark.parametrize(
    ("url", "platform", "reader"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube", "video"),
        ("https://youtu.be/abc", "youtube", "video"),
        ("https://www.instagram.com/reel/abc", "instagram", "video"),
        ("https://www.tiktok.com/@creator/video/1", "tiktok", "video"),
        ("https://x.com/example/status/1", "x-twitter", "video"),
        ("https://twitter.com/example/status/1", "x-twitter", "video"),
        ("https://substack.com/@writer/post", "substack", "article"),
        ("https://www.linkedin.com/posts/example", "linkedin", "article"),
        ("https://www.reddit.com/r/videos/comments/abc/post", "reddit", "article"),
        ("https://v.redd.it/example/video.mp4", "reddit", "video"),
        ("https://www.facebook.com/watch/?v=1", "facebook", "video"),
        ("https://fb.watch/example", "facebook", "video"),
        ("https://vimeo.com/123", "vimeo", "video"),
        ("https://www.twitch.tv/videos/123", "twitch", "video"),
        ("https://www.dailymotion.com/video/123", "dailymotion", "video"),
        ("https://dai.ly/123", "dailymotion", "video"),
        ("https://soundcloud.com/example/track", "soundcloud", "video"),
        ("https://cdn.example.com/media/clip.webm?download=1", "generic-web", "video"),
        ("https://example.com/feed.rss", "generic-web", "article"),
    ],
)
def test_route_selects_platform_and_reader(url, platform, reader):
    result = sources.route(url)

    assert result["platform"] == platform
    assert result["default_reader"] == reader
    assert result["boundaries"]["source_content_trusted"] is False


def test_domain_matching_does_not_accept_suffix_spoofing():
    for url in (
        "https://evilinstagram.com/post",
        "https://instagram.com.evil.test/post",
        "https://youtube.com.evil.test/watch",
        "https://notreddit.com/post",
        "https://linkedin.com.evil.test/post",
    ):
        assert sources.route(url)["platform"] == "generic-web"


@pytest.mark.parametrize("url", [
    "https://www.linkedin.com/my-items/saved-posts/",
    "https://www.youtube.com/feed/playlists",
    "https://www.youtube.com/feed/playlists/?view=grid",
    "https://www.instagram.com/example/saved/all-posts/",
])
def test_account_collection_requires_item_selection(url):
    result = sources.route(url)

    assert result["default_reader"] is None
    assert result["reader_options"] == []
    assert result["requires_browser_auth"] is True
    assert result["public_read"] == "not_supported"
    with pytest.raises(ValueError, match="Account collection page"):
        voidscape._select_reader(url)
    for reader in ("video", "article", "image"):
        with pytest.raises(ValueError, match="not supported"):
            voidscape._select_reader(url, reader)


def test_collection_guard_does_not_classify_unverified_or_spoofed_routes():
    assert sources.route("https://x.com/i/histo")["requires_browser_auth"] is False
    spoof = sources.route("https://youtube.com.evil.test/feed/playlists")
    assert spoof["platform"] == "generic-web"
    assert spoof["default_reader"] == "article"


def test_remote_image_route_requires_localization_first():
    source = "https://cdn.example.com/image/photo.png"
    result = sources.route(source)

    assert result["default_reader"] is None
    assert "save" in result["note"].casefold()
    with pytest.raises(ValueError, match="Remote image fetch is not shipped"):
        voidscape._select_reader(source)


@pytest.mark.parametrize("value", ["file:///etc/passwd", "data:text/plain,hello", "javascript:alert(1)"])
def test_route_rejects_non_http_network_schemes(value):
    result = sources.route(value)

    assert result["source"] == "unsupported"
    assert result["default_reader"] is None
    assert result["input"] == "[rejected input]"
    assert result["input_redacted"] is True
    with pytest.raises(ValueError, match="must use http or https"):
        voidscape._select_reader(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https:///missing-host",
        "https://[invalid-host/post",
        "https://user:secret@example.com/post",
        "https://127.0.0.1/private",
        "http://169.254.169.254/latest/meta-data",
        "https://example.com:8080/post",
        "https://example.com/post#fragment",
    ],
)
def test_route_rejects_malformed_or_sensitive_web_targets(value):
    result = sources.route(value)

    assert result["source"] == "unsupported"
    with pytest.raises(ValueError):
        voidscape._select_reader(value, "video")


def test_reader_override_cannot_enable_an_unadvertised_remote_reader():
    with pytest.raises(ValueError, match="not supported"):
        voidscape._select_reader("https://youtube.com/watch?v=abc", "article")


def test_reader_override_handles_mixed_media_sites():
    reddit_post = "https://www.reddit.com/r/example/comments/abc/post"
    linkedin_post = "https://www.linkedin.com/posts/example"

    assert voidscape._select_reader(reddit_post) == "article"
    assert voidscape._select_reader(reddit_post, "video") == "video"
    assert voidscape._select_reader(linkedin_post, "video") == "video"


def test_local_route_is_offline_and_type_aware(tmp_path):
    carousel = tmp_path / "carousel"
    carousel.mkdir()
    article = tmp_path / "note.md"
    article.write_text("# Note\n", encoding="utf-8")

    assert sources.route(str(carousel))["default_reader"] == "image"
    assert sources.route(str(article))["default_reader"] == "article"
    assert sources.route(str(tmp_path / "clip.mp4"))["default_reader"] == "video"


def test_sources_and_route_commands_offer_json_contract(capsys):
    assert voidscape.main(["sources", "--json"]) == 0
    source_manifest = json.loads(capsys.readouterr().out)
    assert source_manifest["schema_version"] == "1.0"

    assert voidscape.main(["route", "https://x.com/example/status/1", "--json"]) == 0
    route = json.loads(capsys.readouterr().out)
    assert route["platform"] == "x-twitter"
    assert route["default_reader"] == "video"


def test_route_output_redacts_url_credentials_queries_and_fragments():
    result = sources.route("https://user:secret@example.com/post?token=private#section")

    assert result["source"] == "unsupported"
    assert result["input"] == "[rejected input]"
    assert result["input_redacted"] is True
    assert "user:secret" not in json.dumps(result)
    assert "private" not in json.dumps(result)

    youtube = sources.route("https://youtube.com/watch?v=private-id")
    assert youtube["input"] == "https://youtube.com/watch"
    assert youtube["input_redacted"] is True
