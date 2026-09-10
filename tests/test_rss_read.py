import json
from pathlib import Path

import pytest

import rss_read as reader
from rss_capture_helper import article
from test_rss_resource import fixture as capture_fixture


def fixture(tmp_path, monkeypatch, gates=None):
    root, key, _ = capture_fixture(tmp_path)
    work = tmp_path / 'read'
    work.mkdir()
    calls = []
    monkeypatch.setattr(article, '_fetch_url', lambda url: '<html><title>Example</title>'
                        '<article><p>The workshop starts on Thursday. Bring a laptop.</p></article></html>')
    def invoke(command, url, folder, *options):
        calls.append(command)
        assert options[:2] == ('--reader', 'article')
        if command == 'inspect':
            return article.probe(url)
        if command == 'preview':
            return {**article.estimate(url), **(gates or {})}
        assert '--allow-cloud' in options
        return article.run(url, options[options.index('--workdir') + 1], allow_fetch=True)
    return root, key, work, calls, invoke


def test_real_article_engine_and_verified_resume(tmp_path, monkeypatch):
    root, key, work, calls, invoke = fixture(tmp_path, monkeypatch)
    assert reader.prepare(root, key, work, reader=invoke)['duplicate'] is False
    assert calls == ['inspect', 'preview', 'read']
    ready, manifest, files = reader.verify_read(root, key, work)
    assert manifest['entries'][0]['citation'] == '[article 1]'
    assert 'Bring a laptop.' in Path(manifest['entries'][0]['file']).read_text()
    before = {p: p.read_bytes() for p in work.rglob('*') if p.is_file()}
    assert reader.prepare(root, key, work, reader=lambda *a: pytest.fail('refetched'))['duplicate']
    assert before == {p: p.read_bytes() for p in work.rglob('*') if p.is_file()}


@pytest.mark.parametrize('gates', [{'needs_install': True}, {'needs_model_download': True},
    {'gate': None}, {'requires_fetch_approval': None}, {'requires_cloud_approval': False},
    {'requires_browser_auth': True}, {'input': 'https://other.example/post'}])
def test_unexpected_preview_gates_stop_before_fetch(tmp_path, monkeypatch, gates):
    root, key, work, calls, invoke = fixture(tmp_path, monkeypatch, gates)
    with pytest.raises(ValueError):
        reader.prepare(root, key, work, reader=invoke)
    assert calls == ['inspect', 'preview']
    assert not (work / 'ready.json').exists()


def test_no_consent_means_no_work_or_network(tmp_path, monkeypatch):
    root, key, _ = capture_fixture(tmp_path)
    monkeypatch.setattr(reader, 'run_worker', lambda *a, **k: pytest.fail('worker started'))
    with pytest.raises(PermissionError):
        reader.read(root, key, tmp_path / 'absent')
    assert not (tmp_path / 'absent').exists()


@pytest.mark.parametrize('change', ['text', 'capture', 'manifest', 'receipt'])
def test_evidence_tampering_fails_resume(tmp_path, monkeypatch, change):
    root, key, work, calls, invoke = fixture(tmp_path, monkeypatch)
    reader.prepare(root, key, work, reader=invoke)
    ready, manifest, files = reader.verify_read(root, key, work)
    path = {'text': Path(manifest['entries'][0]['file']),
            'capture': root / '.rss-capture' / key[4:] / 'entry.json',
            'manifest': work / 'evidence/manifest.json', 'receipt': work / 'ready.json'}[change]
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises((ValueError, KeyError)):
        reader.prepare(root, key, work, reader=lambda *a: pytest.fail('refetched damaged evidence'))


def test_unexpected_feed_does_not_publish_article_receipt(tmp_path, monkeypatch):
    root, key, work, calls, invoke = fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(article, '_fetch_url', lambda url: '<rss><channel><item><title>A</title>'
                        '<description>A feed is not the selected article.</description></item></channel></rss>')
    with pytest.raises(ValueError):
        reader.prepare(root, key, work, reader=invoke)
    assert not (work / 'ready.json').exists()


def test_access_denial_has_no_ready_receipt(tmp_path, monkeypatch):
    root, key, work, calls, invoke = fixture(tmp_path, monkeypatch)
    def denied(url):
        raise PermissionError('login required')
    monkeypatch.setattr(article, '_fetch_url', denied)
    with pytest.raises((PermissionError, RuntimeError)):
        reader.prepare(root, key, work, reader=invoke)
    assert not (work / 'ready.json').exists()


def test_failure_envelope_does_not_echo_sensitive_input(tmp_path, capsys):
    assert reader.main([str(tmp_path), 'secret-key', str(tmp_path / 'work')]) == 6
    output = capsys.readouterr().out
    assert 'secret-key' not in output
    assert json.loads(output)['ok'] is False


def test_article_note_publication_binds_and_rechecks_evidence(tmp_path, monkeypatch):
    import triage_store as store
    from test_rss_notes import fixture as note_fixture
    args = note_fixture(tmp_path)
    work = tmp_path / 'article-read'
    work.mkdir()
    monkeypatch.setattr(article, '_fetch_url', lambda url: '<p>The launch is Friday. Review the checklist.</p>')
    def invoke(command, url, folder, *options):
        if command == 'inspect':
            return article.probe(url)
        if command == 'preview':
            return article.estimate(url)
        return article.run(url, options[options.index('--workdir') + 1], allow_fetch=True)
    reader.prepare(args['capture_root'], args['key'], work, reader=invoke)
    args['note'].write_text(args['note'].read_text(encoding='utf-8').replace('Review the checklist.\n## Action',
                           'Review the checklist. [article 1]\n## Action'), encoding='utf-8')
    with pytest.raises(ValueError, match='citations'):
        store.publish(**args)
    args['read_root'] = work
    args['note'].write_text(args['note'].read_text(encoding='utf-8').replace('## RSS Excerpt', '## Article Excerpt'), encoding='utf-8')
    result = store.publish(**args)
    assert result['artifact_verified'] and not result['source_action_authorized']
    assert store.lookup(args['root'], 'rss', args['key'])['analyzed']
    _, manifest, _ = reader.verify_read(args['capture_root'], args['key'], work)
    Path(manifest['entries'][0]['file']).write_text('changed evidence')
    with pytest.raises(ValueError):
        store.inspect(args['root'], result['id'])


def test_article_claim_without_binding_is_rejected(tmp_path):
    import triage_store as store
    from test_rss_notes import fixture as note_fixture
    args = note_fixture(tmp_path)
    args['note'].write_text(args['note'].read_text() + '\n[article 99]\n')
    with pytest.raises(ValueError, match='citations'):
        store.publish(**args)


@pytest.mark.parametrize('field,value', [('input', 'https://other.example/post'),
    ('status', 'partial'), ('content_trust', {}), ('entries', []), ('item_count', 2)])
def test_invalid_manifest_cannot_publish_ready(tmp_path, monkeypatch, field, value):
    root, key, work, calls, invoke = fixture(tmp_path, monkeypatch)
    def changed(command, url, out, *options):
        result = invoke(command, url, out, *options)
        if command == 'read':
            path = work / 'evidence/manifest.json'
            manifest = json.loads(path.read_bytes())
            manifest[field] = value
            path.write_text(json.dumps(manifest), encoding='utf-8')
        return result
    with pytest.raises(ValueError):
        reader.prepare(root, key, work, reader=changed)
    assert not (work / 'ready.json').exists()


@pytest.mark.parametrize('timeout', [0, -1, 601, True, '60'])
def test_deadline_bound_before_work(tmp_path, timeout):
    root, key, _ = capture_fixture(tmp_path)
    with pytest.raises(ValueError):
        reader.read(root, key, tmp_path / 'absent', allow_fetch=True, timeout=timeout)
    assert not (tmp_path / 'absent').exists()


@pytest.mark.parametrize('payload', [[], None, 'not an object'])
def test_malformed_receipt_rejected_without_attribute_error(tmp_path, payload):
    root, key, _ = capture_fixture(tmp_path)
    work = tmp_path / 'read'
    work.mkdir()
    (work / 'ready.json').write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        reader.verify_read(root, key, work)
