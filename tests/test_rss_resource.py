import json
from pathlib import Path

import pytest

import rss_capture_helper as capture
import rss_resource as resource


def fixture(tmp_path, link='https://example.com/post', mime='audio/mpeg'):
    source = tmp_path / 'feed.xml'
    source.write_text(f'<rss><channel><item><guid>1</guid><title>Example</title>'
                      f'<link>{link}</link><enclosure url="https://example.com/media" '
                      f'type="{mime}"/></item></channel></rss>', encoding='utf-8')
    root = tmp_path / 'capture'
    item = capture.capture(str(source), root, identity_url='https://example.com/feed', apply=True)['results'][0]
    return root, item['key'], Path(item['evidence'])


def test_selection_is_read_only_and_does_not_fetch(tmp_path, monkeypatch):
    root, key, _ = fixture(tmp_path)
    monkeypatch.setattr(resource.article, '_fetch_url', lambda *a, **k: pytest.fail('unexpected fetch'))
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    result = resource.select(root, key)
    assert result['reader'] == 'article' and result['url'] == 'https://example.com/post'
    assert not result['changes'] and not result['read_authorized'] and not result['source_action_authorized']
    assert result['network_validation'] == 'required_at_read'
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('mime,tier', [('audio/mpeg', 'audio'), ('video/mp4', 'both'), ('Audio/Ogg; codecs=opus', 'audio')])
def test_explicit_enclosure_routes(tmp_path, mime, tier):
    root, key, _ = fixture(tmp_path, mime=mime)
    result = resource.select(root, key, 'enclosure', 1)
    assert result['reader'] == 'video' and result['tier'] == tier


@pytest.mark.parametrize('options', [{'key': 'wrong'}, {'resource': 'other'}, {'enclosure': 1},
    {'resource': 'enclosure'}, {'resource': 'enclosure', 'enclosure': 0},
    {'resource': 'enclosure', 'enclosure': 2}, {'resource': 'enclosure', 'enclosure': True}])
def test_bad_selection_rejected(tmp_path, options):
    root, key, _ = fixture(tmp_path)
    with pytest.raises(ValueError):
        resource.select(**{'root': root, 'key': key, **options})


@pytest.mark.parametrize('url', ['https://example.com/post?token=secret', 'http://127.0.0.1/private', 'file:///private'])
def test_unsafe_or_redacted_article_rejected(tmp_path, url):
    root, key, _ = fixture(tmp_path, link=url)
    with pytest.raises(ValueError):
        resource.select(root, key)


@pytest.mark.parametrize('mime', ['application/octet-stream', 'audio/', 'video/*'])
def test_unknown_mime_does_not_guess(tmp_path, mime):
    root, key, _ = fixture(tmp_path, mime=mime)
    with pytest.raises(ValueError):
        resource.select(root, key, 'enclosure', 1)


def test_missing_legacy_flag_is_unknown(tmp_path):
    root, key, path = fixture(tmp_path)
    data = json.loads(path.read_bytes())
    data['entry'].pop('link_redacted')
    raw = capture.encoded(data)
    path.write_bytes(raw)
    path.with_name('captured.json').write_bytes(capture.encoded({'schema': 1, 'key': key, 'sha256': capture.digest(raw)}))
    with pytest.raises(ValueError, match='provenance unknown'):
        resource.select(root, key)


def test_corruption_and_cli_failure(tmp_path, capsys):
    root, key, path = fixture(tmp_path)
    assert resource.main([str(root), key]) == 0
    assert json.loads(capsys.readouterr().out)['ok']
    path.write_bytes(path.read_bytes() + b'changed')
    assert resource.main([str(root), key]) == 6
    assert not json.loads(capsys.readouterr().out)['ok']
