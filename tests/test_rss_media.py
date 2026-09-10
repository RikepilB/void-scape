import json
from pathlib import Path

import pytest

import rss_download as download
import rss_media as media
import triage_store as store
from test_rss_resource import fixture as capture_fixture


def fixture(tmp_path, *, gates=None, tier='audio'):
    root, key, _ = capture_fixture(tmp_path, mime='audio/mpeg' if tier == 'audio' else 'video/mp4')
    downloaded = tmp_path / 'download'
    downloaded.mkdir()
    def fetch(url, path, budget):
        path.write_bytes(b'synthetic source')
        return {'bytes': path.stat().st_size, 'response_type': 'audio/mpeg', 'redirects': 0}
    download.prepare(root, key, downloaded, fetcher=fetch,
                     normalizer=lambda src, dst, bound: dst.write_bytes(b'synthetic remux'))
    work = tmp_path / 'read'
    work.mkdir()
    calls = []
    def invoke(command, source, folder, *options):
        calls.append(command)
        expected = 'none' if tier == 'visual' else 'faster-whisper'
        assert Path(source) == downloaded / 'media.mkv'
        if command == 'inspect':
            return {'source': 'local', 'input': source, 'sidecar_transcript': None}
        if command == 'preview':
            return {'source': 'local', 'input': source, 'sidecar_transcript': None,
                    'backend': expected, 'tier': tier, 'free': True, 'requires_cloud_approval': False,
                    'needs_model_download': False, 'needs_install': False, **(gates or {})}
        assert '--allow-cloud' not in options and '--allow-model-download' not in options
        bundle = Path(options[options.index('--workdir') + 1])
        bundle.mkdir()
        transcript = bundle / 'transcript.txt'
        transcript.write_text('[00:00] Bring a laptop.\n[00:04] The workshop starts Friday.\n')
        image = bundle / 'frame.jpg'
        image.write_bytes(b'synthetic frame')
        result = {'status': 'complete', 'workdir': str(bundle), 'backend': expected, 'tier': tier,
                  'content_trust': {'source_content': 'untrusted'},
                  'frames': [] if tier == 'audio' else [{'file': str(image), 't': '00:02'}],
                  'transcript': str(transcript) if tier != 'visual' else None}
        (bundle / 'manifest.json').write_text(json.dumps(result))
        return result
    args = dict(root=root, key=key, download_root=downloaded, work=work, tier=tier)
    return args, calls, invoke


@pytest.mark.parametrize('tier', ['audio', 'visual', 'both'])
def test_read_stages_and_verified_reuse(tmp_path, tier):
    args, calls, invoke = fixture(tmp_path, tier=tier)
    assert not media.prepare(**args, reader=invoke)['duplicate']
    assert calls == ['inspect', 'preview', 'read']
    ready, manifest, files = media.verify_read(args['root'], args['key'], args['work'])
    assert manifest['tier'] == tier
    assert media.prepare(**args, reader=lambda *a: pytest.fail('read repeated'))['duplicate']


@pytest.mark.parametrize('gates', [{'needs_install': True}, {'needs_model_download': True},
    {'requires_cloud_approval': True}, {'free': False}, {'backend': 'groq'}, {'tier': 'visual'},
    {'sidecar_transcript': 'unverified.txt'}, {'source': 'url'}, {'needs_install': None}])
def test_preview_gates_stop_read(tmp_path, gates):
    args, calls, invoke = fixture(tmp_path, gates=gates)
    with pytest.raises(ValueError):
        media.prepare(**args, reader=invoke)
    assert calls == ['inspect', 'preview'] and not (args['work'] / 'ready.json').exists()


def test_no_consent_no_worker(tmp_path, monkeypatch):
    monkeypatch.setattr(media, 'run_worker', lambda *a, **k: pytest.fail('worker ran'))
    with pytest.raises(PermissionError):
        media.read(tmp_path, 'invalid', tmp_path, tmp_path / 'absent')
    assert not (tmp_path / 'absent').exists()


@pytest.mark.parametrize('artifact', ['source.bin', 'media.mkv', 'download.json', 'ready.json', 'evidence/transcript.txt'])
def test_mutation_prevents_read_reuse(tmp_path, artifact):
    args, _, invoke = fixture(tmp_path)
    media.prepare(**args, reader=invoke)
    base = args['download_root'] if artifact in {'source.bin', 'media.mkv', 'download.json'} else args['work']
    path = base / artifact
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises((ValueError, KeyError)):
        media.prepare(**args, reader=lambda *a: pytest.fail('repeated read'))


@pytest.mark.parametrize('payload', [[], None, 'not an object'])
def test_malformed_read_receipt_fails_closed(tmp_path, payload):
    args, _, _ = fixture(tmp_path)
    (args['work'] / 'ready.json').write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        media.verify_read(args['root'], args['key'], args['work'])


def note(args):
    text = ('---\nsource: rss\nurl: https://example.com/post\nauthor: null\ndate: null\ncategory: Tech\n---\n'
            '# Enclosure example\nSource: ' + args['key'] + '\nPriority: **Medium** - Workshop context.\n'
            '## Synopsis\nWorkshop instructions.\n## Key points\nBring a laptop.\n'
            '## Action Items\nBring a laptop.\n## Key moments\n- [00:00] Bring a laptop.\n'
            '## Links\nhttps://example.com/post\n## Evidence\n')
    path = args['work'].parent / 'draft.md'
    path.write_text(text, encoding='utf-8')
    return {'root': args['work'].parent / 'notes', 'source': 'rss', 'key': args['key'],
            'category': 'Tech', 'note': path, 'evidence': [], 'capture_root': args['root'], 'read_root': args['work']}


def test_media_note_binds_capture_download_read_and_citations(tmp_path):
    args, _, invoke = fixture(tmp_path)
    media.prepare(**args, reader=invoke)
    publish = note(args)
    result = store.publish(**publish)
    assert result['artifact_verified'] and not result['source_action_authorized']
    assert 'Scope: RSS enclosure 1; timestamps refer to the retained normalized media.' in Path(result['note']).read_text(encoding='utf-8')
    assert store.lookup(publish['root'], 'rss', args['key'])['analyzed']
    (args['download_root'] / 'media.mkv').write_bytes(b'changed')
    with pytest.raises(ValueError):
        store.inspect(publish['root'], result['id'])


@pytest.mark.parametrize('old,new', [('[00:00]', '[99:59]'), ('[00:00]', ''),
    ('[00:00]', '[article 1]'), ('## Key moments', '## RSS Excerpt')])
def test_note_requires_actual_media_labels(tmp_path, old, new):
    args, _, invoke = fixture(tmp_path)
    media.prepare(**args, reader=invoke)
    publish = note(args)
    publish['note'].write_text(publish['note'].read_text(encoding='utf-8').replace(old, new), encoding='utf-8')
    with pytest.raises(ValueError):
        store.publish(**publish)
    assert not publish['root'].exists()


@pytest.mark.parametrize('text', ['', '[00:00]\n[00:02]\n'])
def test_empty_transcript_is_not_ready_audio(tmp_path, text):
    args, _, invoke = fixture(tmp_path)
    def empty(command, *rest):
        result = invoke(command, *rest)
        if command == 'read':
            Path(result['transcript']).write_text(text)
        return result
    with pytest.raises(ValueError, match='usable timestamped'):
        media.prepare(**args, reader=empty)
    assert not (args['work'] / 'ready.json').exists()
