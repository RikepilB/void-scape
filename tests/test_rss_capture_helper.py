import json
from pathlib import Path
import runpy
import sys

import pytest

import article
import rss_capture_helper as rss

URL = 'https://example.com/feed'


def feed(tmp_path, items=None):
    path = tmp_path / 'feed.xml'
    path.write_text('<rss version="2.0"><channel><title>Publication</title>' +
                    (items or '<item><title>First</title><guid>opaque:1</guid><description>Body.</description></item>') +
                    '</channel></rss>', encoding='utf-8')
    return path


def invoke(path, root, **kwargs):
    return rss.capture(str(path), root, identity_url=URL, **kwargs)


def test_preview_does_not_create_destination(tmp_path):
    path, root = feed(tmp_path), tmp_path / 'notes'
    result = invoke(path, root)
    assert result['results'][0]['status'] == 'new'
    assert result['analyzed'] == 0 and not root.exists()


def test_capture_replay_and_integrity(tmp_path):
    path, root = feed(tmp_path), tmp_path / 'notes'
    result = invoke(path, root, apply=True)
    entry = result['results'][0]
    retained = rss.verify(root, entry['key'][4:])
    assert retained['entry']['guid'] == 'opaque:1'
    assert retained['content_trust'] == 'untrusted'
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    replay = invoke(path, root, apply=True, since='2026-01-01')
    assert replay['duplicates'] == 1 and replay['results'] == []
    assert before == {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    Path(entry['evidence']).write_text('{}')
    with pytest.raises(ValueError):
        invoke(path, root, apply=True)


def test_interrupted_capture_resumes_without_overwrite(tmp_path, monkeypatch):
    path, root = feed(tmp_path), tmp_path / 'notes'
    original = rss.exclusive
    def fail_marker(path, data):
        if path.name == 'captured.json':
            raise OSError('synthetic sync failure')
        original(path, data)
    monkeypatch.setattr(rss, 'exclusive', fail_marker)
    with pytest.raises(OSError):
        invoke(path, root, apply=True)
    assert len(list(root.rglob('entry.json'))) == 1
    assert not list(root.rglob('captured.json'))
    monkeypatch.setattr(rss, 'exclusive', original)
    assert invoke(path, root, apply=True)['results'][0]['status'] == 'captured'


def test_changed_entry_is_reported_preserving_original(tmp_path):
    path, root = feed(tmp_path), tmp_path / 'notes'
    first = invoke(path, root, apply=True)['results'][0]
    evidence = Path(first['evidence']).read_bytes()
    path.write_text(path.read_text().replace('Body.', 'Updated body.'))
    assert invoke(path, root, apply=True)['results'][0]['status'] == 'changed'
    assert Path(first['evidence']).read_bytes() == evidence


def test_limit_skips_retained_entries_without_starvation(tmp_path):
    path = feed(tmp_path, ''.join(f'<item><title>{i}</title><guid>{i}</guid></item>' for i in range(3)))
    root = tmp_path / 'notes'
    keys = [invoke(path, root, limit=1, apply=True)['results'][0]['key'] for _ in range(3)]
    assert len(set(keys)) == 3
    assert invoke(path, root, limit=1, apply=True)['results'] == []


def test_dates_keep_unknown_but_exclude_older(tmp_path):
    path = feed(tmp_path, '<item><guid>old</guid><title>Old</title><pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate></item>'
                '<item><guid>new</guid><title>New</title><pubDate>2026-09-01T00:00:00Z</pubDate></item>'
                '<item><guid>unknown</guid><title>Unknown</title></item>')
    result = invoke(path, tmp_path / 'notes', since='2026-01-01')
    assert [r['title'] for r in result['results']] == ['New', 'Unknown']
    assert [r['date_filter_uncertain'] for r in result['results']] == [False, True]


@pytest.mark.parametrize('options', [{'limit': 0}, {'limit': 101}, {'since': 'yesterday'}, {'since': '2026-02-30'}])
def test_invalid_bounds_precede_fetch(tmp_path, monkeypatch, options):
    monkeypatch.setattr(article, '_fetch_url', lambda *a: pytest.fail('must validate first'))
    with pytest.raises(ValueError):
        rss.capture(URL, tmp_path / 'notes', allow_fetch=True, apply=True, **options)
    assert not (tmp_path / 'notes').exists()


def test_fetch_gate_and_publication_root(tmp_path, monkeypatch):
    text = feed(tmp_path).read_text()
    seen = []
    monkeypatch.setattr(article, '_fetch_url', lambda url: seen.append(url) or text)
    with pytest.raises(PermissionError):
        rss.capture('https://publication.substack.com', tmp_path / 'notes')
    assert seen == []
    result = rss.capture('https://publication.substack.com', tmp_path / 'notes', allow_fetch=True)
    assert seen == ['https://publication.substack.com/feed']
    assert result['results'] and not (tmp_path / 'notes').exists()


@pytest.mark.parametrize('url', ['https://example.com/feed?token=secret', 'https://a:b@example.com/feed',
                              'http://127.0.0.1/feed', 'file:///tmp/feed', 'https://example.com/feed#section'])
def test_unsafe_or_noncanonical_feed_urls_refused(url):
    with pytest.raises(ValueError):
        rss.feed_url(url)


def test_busy_writer_preserves_state(tmp_path):
    path, root = feed(tmp_path), tmp_path / 'notes'
    with rss.locked(root / '.rss-capture'):
        with pytest.raises(OSError):
            invoke(path, root, apply=True)
    assert not list(root.rglob('entry.json'))


def test_cli_error_does_not_echo_secret(tmp_path, capsys):
    assert rss.main(['https://user:secret@example.com/feed', '--root', str(tmp_path)]) == 6
    raw = capsys.readouterr().out
    assert 'secret' not in raw and json.loads(raw)['ok'] is False


def test_feed_encoded_content_has_priority_and_plain_text():
    parsed = article._parse_feed_xml('<rss xmlns:content="http://purl.org/rss/1.0/modules/content/">'
             '<channel><item><guid>1</guid><description>Short</description>'
             '<content:encoded><![CDATA[<p>Full <b>body</b>.</p>]]></content:encoded></item></channel></rss>')
    entry = parsed['entries'][0]
    assert entry['body'] == 'Full body .'
    assert entry['content_kind'] == 'encoded'


def test_atom_alternate_is_not_enclosure():
    parsed = article._parse_feed_xml('<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>urn:test:1</id>'
             '<title>Podcast</title><link rel="enclosure" href="https://example.com/audio.mp3" type="audio/mpeg"/>'
             '<link rel="alternate" href="https://example.com/post"/><author><name>Alice</name></author>'
             '<content type="html">&lt;p&gt;Text&lt;/p&gt;</content></entry></feed>')
    entry = parsed['entries'][0]
    assert entry['link'] == 'https://example.com/post'
    assert entry['body'] == 'Text' and entry['author'] == 'Alice'
    assert entry['enclosures'] == [{'url': 'https://example.com/audio.mp3', 'type': 'audio/mpeg'}]


def test_same_title_without_id_does_not_drop_distinct_entries():
    parsed = article._parse_feed_xml('<rss><channel><item><title>Same</title><description>One</description></item>'
             '<item><title>Same</title><description>Two</description></item></channel></rss>')
    assert len(parsed['entries']) == 2
    assert parsed['entries'][0]['guid'] != parsed['entries'][1]['guid']
    assert parsed['entries'][0]['identity_kind'] == 'content'


def test_opaque_id_whitespace_is_not_normalized():
    parsed = article._parse_feed_xml('<rss><channel><item><guid>opaque  id</guid><title>One</title></item>'
             '<item><guid>opaque id</guid><title>Two</title></item></channel></rss>')
    assert [entry['guid'] for entry in parsed['entries']] == ['opaque  id', 'opaque id']


def test_xhtml_paragraphs_keep_word_boundaries():
    parsed = article._parse_feed_xml('<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>one</id>'
             '<content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>First</p><p>Second</p>'
             '</div></content></entry></feed>')
    assert parsed['entries'][0]['body'] == 'First Second'


def test_capture_verifies_actual_bytes(tmp_path):
    path, root = feed(tmp_path), tmp_path / 'notes'
    result = invoke(path, root, apply=True)['results'][0]
    evidence = Path(result['evidence'])
    evidence.write_bytes(evidence.read_bytes() + b' ')
    with pytest.raises(ValueError, match='verification'):
        invoke(path, root)


def test_corrupt_nested_record_returns_json_error(tmp_path, capsys):
    path, root = feed(tmp_path), tmp_path / 'notes'
    result = invoke(path, root, apply=True)['results'][0]
    evidence = Path(result['evidence'])
    record = json.loads(evidence.read_text())
    record['entry'] = []
    evidence.write_text(json.dumps(record))
    assert rss.main([str(path), '--feed-url', URL, '--root', str(root)]) == 6
    assert json.loads(capsys.readouterr().out)['ok'] is False


def test_missing_fetch_gate_has_distinct_exit(tmp_path, capsys):
    assert rss.main([URL, '--root', str(tmp_path)]) == 4
    assert json.loads(capsys.readouterr().out)['error']['code'] == 'rss_permission_required'


def test_invalid_or_timezone_free_dates_remain_unknown():
    assert rss.timestamp('not a date') is None
    assert rss.timestamp('2026-09-01T12:00:00') is None


def test_remote_identity_cannot_be_overridden(tmp_path):
    with pytest.raises(ValueError, match='identity'):
        rss.capture(URL, tmp_path, identity_url='https://other.com/feed')


def test_local_identity_is_required(tmp_path):
    with pytest.raises(ValueError, match='feed-url'):
        rss.capture(str(feed(tmp_path)), tmp_path / 'notes')


def test_local_and_remote_feed_size_limits(tmp_path, monkeypatch):
    path = feed(tmp_path)
    monkeypatch.setattr(rss, 'MAX_BYTES', 10)
    with pytest.raises(ValueError, match='exceeds'):
        invoke(path, tmp_path / 'notes', apply=True)
    monkeypatch.setattr(article, '_fetch_url', lambda url: 'x' * 11)
    with pytest.raises(ValueError, match='exceeds'):
        rss.capture(URL, tmp_path / 'notes', allow_fetch=True, apply=True)
    assert not (tmp_path / 'notes').exists()


def test_capture_record_size_and_shape(tmp_path, monkeypatch):
    path = tmp_path / 'entry.json'
    monkeypatch.setattr(rss, 'MAX_BYTES', 10)
    path.write_text('x' * 11)
    with pytest.raises(ValueError, match='limit'):
        rss.read_record(path)
    path.write_text('[]')
    with pytest.raises(ValueError, match='object'):
        rss.read_record(path)
    with pytest.raises(ValueError, match='identity'):
        rss.verify(tmp_path, '../escape')


def test_entry_count_is_bounded():
    with pytest.raises(ValueError, match='too many'):
        rss.select(URL, {'entries': [], 'skipped': [{}] * 10001})


def test_encoded_record_limit_precedes_writes(tmp_path, monkeypatch):
    path = feed(tmp_path)
    monkeypatch.setattr(rss, 'MAX_BYTES', path.stat().st_size + 1)
    with pytest.raises(ValueError, match='entry exceeds'):
        invoke(path, tmp_path / 'notes', apply=True)
    assert not (tmp_path / 'notes').exists()


def test_changed_entry_respects_limit(tmp_path):
    path, root = feed(tmp_path), tmp_path / 'notes'
    invoke(path, root, apply=True)
    path.write_text(path.read_text().replace('Body.', 'New body.'))
    assert invoke(path, root, limit=1)['results'][0]['status'] == 'changed'


def test_cli_entrypoint_preview(tmp_path, monkeypatch, capsys):
    path, root = feed(tmp_path), tmp_path / 'notes'
    monkeypatch.setattr(sys, 'argv', ['rss_capture_helper.py', str(path), '--feed-url', URL, '--root', str(root)])
    with pytest.raises(SystemExit) as error:
        runpy.run_path(str(Path(rss.__file__)), run_name='__main__')
    assert error.value.code == 0
    assert json.loads(capsys.readouterr().out)['data']['mode'] == 'preview'
    assert not root.exists()


def test_skipped_entry_output_is_bounded(tmp_path):
    path = feed(tmp_path, '<item><title>First</title><guid>1</guid></item>' +
                '<item><title>Duplicate</title><guid>1</guid></item>' * 4)
    result = invoke(path, tmp_path / 'notes', limit=1)
    assert len(result['feed_skipped']) == 1
    assert result['feed_skipped_total'] == 4
