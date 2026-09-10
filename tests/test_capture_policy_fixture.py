import json
import urllib.error
import urllib.request

import pytest

from capture_policy_fixture import fixture_pair


def fetch(url):
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=3)


def counts(origin):
    with fetch(origin + "/counts") as response:
        return json.load(response)["sentinel_requests"]


def test_positive_control_redirect_detects_denied_origin_request():
    with fixture_pair() as pair:
        source, sink = pair["allowed_origin"], pair["denied_origin"]
        assert source != sink
        assert counts(source) == 0
        with fetch(source + "/redirect") as response:
            assert response.url == sink + "/sentinel.svg"
        assert counts(source) == 1


def test_subresource_page_is_not_its_own_policy_enforcer():
    with fixture_pair() as pair:
        source = pair["allowed_origin"]
        with fetch(source + "/subresource") as response:
            assert "Content-Security-Policy" not in response.headers
            assert (pair["denied_origin"] + "/sentinel.svg").encode() in response.read()
        assert counts(source) == 0
        with fetch(pair["denied_origin"] + "/sentinel.svg") as response:
            assert response.status == 200
        assert counts(source) == 1


@pytest.mark.parametrize("path", ["/../AGENTS.md", "/redirect?url=https://example.com"])
def test_routes_do_not_accept_files_or_arbitrary_targets(path):
    with fixture_pair() as pair:
        for origin in (pair["allowed_origin"], pair["denied_origin"]):
            with pytest.raises(urllib.error.HTTPError) as error:
                fetch(origin + path)
            assert error.value.code == 404


def test_both_listeners_close_on_exception():
    with pytest.raises(RuntimeError):
        with fixture_pair() as pair:
            raise RuntimeError("test cleanup")
    for origin in (pair["allowed_origin"], pair["denied_origin"]):
        with pytest.raises(urllib.error.URLError):
            fetch(origin + "/sentinel.svg")
