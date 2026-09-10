import json
from pathlib import Path

import pytest

import rss_capture_helper as rss
import triage_store as store
from test_rss_notes import fixture
from sync_rss_skill import ROOT, rendered_files


def test_retained_resumes_capture_without_fetch(tmp_path, monkeypatch):
    args = fixture(tmp_path)
    monkeypatch.setattr(rss.article, '_fetch_url', lambda *a: pytest.fail('inventory must not fetch'))
    before = {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = rss.retained(args['capture_root'], args['root'])
    assert result['results'][0]['key'] == args['key']
    assert result['results'][0]['status'] == 'needs_note'
    assert not result['changes']
    assert before == {p: p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    store.publish(**args)
    result = rss.retained(args['capture_root'], args['root'])
    assert result['results'] == [] and result['analyzed'] == 1


def test_verified_skip_is_not_analyzed(tmp_path):
    args = fixture(tmp_path, skipped=True)
    store.publish(**args)
    result = rss.retained(args['capture_root'], args['root'])
    assert result['skipped'] == 1 and result['analyzed'] == 0 and not result['results']


def test_inventory_rejects_changed_evidence(tmp_path):
    args = fixture(tmp_path)
    store.publish(**args)
    path = args['capture_root'] / '.rss-capture' / args['key'][4:] / 'entry.json'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError):
        rss.retained(args['capture_root'], args['root'])


def test_incomplete_capture_does_not_return_unverified_content(tmp_path):
    root = tmp_path / 'capture'
    folder = root / '.rss-capture' / ('a' * 64)
    folder.mkdir(parents=True)
    (folder / 'entry.json').write_text('unverified')
    result = rss.retained(root, tmp_path / 'notes')
    assert result['incomplete'] == 1 and result['results'] == []


def test_absent_capture_creates_no_paths(tmp_path):
    result = rss.retained(tmp_path / 'capture', tmp_path / 'notes')
    assert result['results'] == [] and list(tmp_path.iterdir()) == []


def test_unknown_inventory_entry_fails_closed(tmp_path):
    folder = tmp_path / '.rss-capture'
    folder.mkdir()
    (folder / 'unexpected').touch()
    with pytest.raises(ValueError, match='unexpected'):
        rss.retained(tmp_path, tmp_path / 'notes')


def test_pending_publication_is_visible(tmp_path, monkeypatch):
    args = fixture(tmp_path)
    monkeypatch.setattr(store, 'update_index', lambda *a: (_ for _ in ()).throw(OSError('synthetic failure')))
    with pytest.raises(OSError):
        store.publish(**args)
    assert rss.retained(args['capture_root'], args['root'])['results'][0]['publication_pending']


def test_inventory_limit(tmp_path):
    args = fixture(tmp_path)
    assert len(rss.retained(args['capture_root'], args['root'], limit=1)['results']) == 1
    with pytest.raises(ValueError):
        rss.retained(args['capture_root'], args['root'], limit=0)


@pytest.mark.parametrize('extra', [['https://example.com/feed'], ['--allow-fetch'], ['--apply'],
                                  ['--since', '2026-01-01']])
def test_inventory_rejects_mixed_modes(tmp_path, capsys, extra):
    assert rss.main(['--list-retained', '--root', str(tmp_path), '--notes-root', str(tmp_path / 'notes'), *extra]) == 6
    assert not json.loads(capsys.readouterr().out)['ok']


def test_inventory_cli_and_missing_arguments(tmp_path, capsys):
    assert rss.main(['--list-retained', '--root', str(tmp_path), '--notes-root', str(tmp_path / 'notes')]) == 0
    assert json.loads(capsys.readouterr().out)['data']['mode'] == 'retained'
    assert rss.main(['--root', str(tmp_path)]) == 6
    capsys.readouterr()
    assert rss.main(['--list-retained', '--root', str(tmp_path)]) == 6


def test_inventory_scan_cap(tmp_path, monkeypatch):
    root = tmp_path / '.rss-capture'
    root.mkdir()
    monkeypatch.setattr(Path, 'iterdir', lambda path: iter([root / '.triage'] * 10001))
    with pytest.raises(ValueError, match='exceeds'):
        rss.retained(tmp_path, tmp_path / 'notes')


def test_project_rss_mirrors_match():
    for path, content in rendered_files(ROOT).items():
        assert path.read_text(encoding='utf-8') == content, path


def test_inventory_filters_publication(tmp_path):
    args = fixture(tmp_path)
    rss.capture(str(tmp_path / 'feed.xml'), args['capture_root'], identity_url='https://other.example/feed', apply=True)
    result = rss.retained(args['capture_root'], args['root'], identity_url='https://example.com/feed')
    assert [item['key'] for item in result['results']] == [args['key']]
    assert result['other_feeds'] == 1


def test_inventory_rejects_non_directory_record(tmp_path):
    folder = tmp_path / '.rss-capture'
    folder.mkdir()
    (folder / ('a' * 64)).touch()
    with pytest.raises(ValueError, match='directory'):
        rss.retained(tmp_path, tmp_path / 'notes')
