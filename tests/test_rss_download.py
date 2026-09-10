import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.error import HTTPError
import wave

import pytest

import rss_download as download
from test_rss_resource import fixture as capture_fixture


class Response(io.BytesIO):
    def __init__(self, body=b'audio', headers=None):
        super().__init__(body)
        self.headers = {'Content-Type': 'audio/mpeg', **(headers or {})}


def wav(path):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(b'\0\0' * 8000)


def test_preview_no_network_or_writes(tmp_path, monkeypatch):
    root, key, _ = capture_fixture(tmp_path)
    monkeypatch.setattr(download, 'run_worker', lambda *a, **k: pytest.fail('worker started'))
    result = download.capture(root, key, tmp_path / 'absent')
    assert result['status'] == 'preview' and result['requires_fetch_approval']
    assert not result['transcribes'] and not result['source_action_authorized']
    assert not (tmp_path / 'absent').exists()


def test_streamed_fetch_flushes_original_bytes(tmp_path):
    target = tmp_path / 'source.bin'
    result = download.fetch('https://example.com/audio', target, 10,
                            opener=lambda *a: Response(b'audio', {'Content-Length': '5'}))
    assert target.read_bytes() == b'audio' and result['bytes'] == 5 and result['redirects'] == 0


@pytest.mark.parametrize('headers,body,budget', [({'Content-Type': 'text/html'}, b'login', 10),
    ({'Content-Type': 'audio/'}, b'a', 10), ({'Content-Encoding': 'gzip'}, b'a', 10),
    ({'Content-Length': '999'}, b'a', 10), ({'Content-Length': '-1'}, b'a', 10),
    ({'Content-Length': '5'}, b'abc', 10), ({}, b'abc', 2), ({}, b'', 10)])
def test_invalid_or_over_budget_response(tmp_path, headers, body, budget):
    with pytest.raises(ValueError):
        download.fetch('https://example.com/audio', tmp_path / 'source', budget,
                       opener=lambda *a: Response(body, headers))


def test_redirects_do_not_retain_secret_destination(tmp_path):
    calls = []
    def opener(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 302, 'redirect', {'Location': '/cdn?token=private'}, None)
        return Response()
    result = download.fetch('https://example.com/audio', tmp_path / 'source', 10, opener=opener)
    assert calls == ['https://example.com/audio', 'https://example.com/cdn?token=private']
    assert result['redirects'] == 1 and 'private' not in json.dumps(result)


@pytest.mark.parametrize('code,location', [(302, 'http://example.com/media'), (302, ''), (401, ''), (403, ''), (500, '')])
def test_denied_fetch_has_no_fallback(tmp_path, code, location):
    def opener(request, timeout):
        raise HTTPError(request.full_url, code, 'denied', {'Location': location}, None)
    with pytest.raises((ValueError, PermissionError)):
        download.fetch('https://example.com/audio', tmp_path / 'source', 10, opener=opener)
    assert not (tmp_path / 'source').exists()


def test_redirect_limit(tmp_path):
    calls = []
    def opener(request, timeout):
        calls.append(request.full_url)
        raise HTTPError(request.full_url, 302, 'loop', {'Location': '/loop'}, None)
    with pytest.raises(ValueError):
        download.fetch('https://example.com/audio', tmp_path / 'source', 10, opener=opener)
    assert len(calls) == download.article.MAX_REDIRECTS + 1


def test_real_pinned_transport_rejects_private_redirect(tmp_path, monkeypatch):
    calls = []
    original = download.article._open_url
    def opener(request, timeout):
        calls.append(request.full_url)
        if len(calls) == 1:
            raise HTTPError(request.full_url, 302, 'redirect', {'Location': 'http://127.0.0.1/media'}, None)
        return original(request, timeout)
    monkeypatch.setattr(download.article, '_connection_for', lambda *a: pytest.fail('private socket attempted'))
    with pytest.raises(ValueError):
        download.fetch('http://example.com/audio', tmp_path / 'source', 10, opener=opener)
    assert len(calls) == 2


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
def test_actual_descriptor_remux_and_retained_resume(tmp_path):
    root, key, _ = capture_fixture(tmp_path)
    work = tmp_path / 'work'
    work.mkdir()
    def fetcher(url, target, budget):
        wav(target)
        return {'bytes': target.stat().st_size, 'response_type': 'audio/wav', 'redirects': 0}
    assert not download.prepare(root, key, work, fetcher=fetcher)['duplicate']
    record, paths = download.verify_download(root, key, work)
    assert paths[1].read_bytes().startswith(b'\x1a\x45\xdf\xa3')
    assert record['decode_policy'] == 'descriptor-only-v1'
    before = {p: p.read_bytes() for p in work.iterdir() if p.is_file()}
    assert download.prepare(root, key, work, fetcher=lambda *a: pytest.fail('refetch'))['duplicate']
    assert before == {p: p.read_bytes() for p in work.iterdir() if p.is_file()}
    paths[0].write_bytes(b'changed')
    with pytest.raises(ValueError):
        download.verify_download(root, key, work)


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='FFmpeg required')
@pytest.mark.parametrize('content', ['#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXTINF:1,\nhttp://127.0.0.1/never\n',
    "ffconcat version 1.0\nfile 'canary.wav'\n"])
def test_playlist_demuxers_rejected(tmp_path, content):
    source, target = tmp_path / 'source', tmp_path / 'media.mkv'
    source.write_text(content, encoding='utf-8')
    with pytest.raises(ValueError, match='remux failed'):
        download.remux(source, target, 10000)
    assert not (tmp_path / 'download.json').exists()


def test_invalid_bounds_before_work(tmp_path):
    root, key, _ = capture_fixture(tmp_path)
    for options in ({'max_bytes': 0}, {'max_bytes': True}, {'max_bytes': download.MAX_BYTES + 1},
                    {'timeout': 0}, {'timeout': 1801}, {'timeout': True}):
        with pytest.raises(ValueError):
            download.capture(root, key, tmp_path / 'absent', **options)
    assert not (tmp_path / 'absent').exists()


def test_failure_envelope_redacts_selection(tmp_path, capsys):
    assert download.main([str(tmp_path), 'secret-key', str(tmp_path / 'work')]) == 6
    output = capsys.readouterr().out
    assert not json.loads(output)['ok'] and 'secret-key' not in output


def test_incomplete_artifacts_stop_before_refetch(tmp_path):
    root, key, _ = capture_fixture(tmp_path)
    work = tmp_path / 'work'
    work.mkdir()
    (work / 'source.bin').write_bytes(b'partial')
    with pytest.raises(ValueError, match='incomplete'):
        download.prepare(root, key, work, fetcher=lambda *a: pytest.fail('refetched'))


def test_missing_descriptor_support_stops_before_fetch(tmp_path, monkeypatch):
    root, key, _ = capture_fixture(tmp_path)
    monkeypatch.setattr(download, 'ffmpeg_ready', lambda: False)
    monkeypatch.setattr(download, 'run_worker', lambda *a, **k: pytest.fail('worker started'))
    with pytest.raises(ValueError, match='fd input/output'):
        download.capture(root, key, tmp_path / 'absent', allow_fetch=True)
    assert not (tmp_path / 'absent').exists()


def test_worker_access_denial_reaches_safe_cli_status(tmp_path, monkeypatch, capsys):
    root, key, _ = capture_fixture(tmp_path)
    monkeypatch.setattr(download, 'ffmpeg_ready', lambda: True)
    def denied(command, *, timeout, log, cwd):
        log.write_text(json.dumps({'ok': False, 'error': {'code': 'rss_access_denied',
                       'http_status': 403, 'message': 'Do not echo this untrusted secret'}}))
        raise download.ProcessDeadlineError('worker failed')
    monkeypatch.setattr(download, 'run_worker', denied)
    assert download.main([str(root), key, str(tmp_path / 'work'), '--allow-fetch']) == 6
    output = capsys.readouterr().out
    assert json.loads(output)['error']['http_status'] == 403
    assert 'secret' not in output and 'example.com' not in output
    assert not (tmp_path / 'work/download.json').exists()


def test_remux_stderr_is_bounded_and_child_reaped(tmp_path, monkeypatch):
    source, target = tmp_path / 'source.wav', tmp_path / 'media.mkv'
    wav(source)
    original = subprocess.Popen
    processes = []
    def noisy(command, **kwargs):
        child = original([sys.executable, '-c', "import sys; sys.stderr.write('x' * (2 * 1024 * 1024))"], **kwargs)
        processes.append(child)
        return child
    monkeypatch.setattr(download.subprocess, 'Popen', noisy)
    with pytest.raises(ValueError, match='diagnostics exceeded'):
        download.remux(source, target, 100000)
    assert target.with_suffix('.stderr').stat().st_size == download.MAX_DIAGNOSTICS
    assert processes[0].poll() is not None
