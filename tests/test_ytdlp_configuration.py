import json
import subprocess

import pytest

import video


@pytest.mark.parametrize('operation', ['metadata', 'download', 'captions'])
def test_media_calls_disable_external_configuration(tmp_path, monkeypatch, operation):
    calls = []
    def invoke(args):
        calls.append(args)
        if operation == 'download':
            (tmp_path / 'source.mp4').write_bytes(b'synthetic')
        return subprocess.CompletedProcess(args, 0, json.dumps({'duration': 1}), '')
    monkeypatch.setattr(video, 'run_cmd', invoke)
    monkeypatch.setattr(video, 'validate_remote_media_url', lambda url: url)
    monkeypatch.delenv('READ_VIDEO_YTDLP_COOKIES', raising=False)
    url = 'https://www.youtube.com/watch?v=abcdefghijk'
    if operation == 'metadata':
        video.ytdlp_meta(url)
    elif operation == 'download':
        video._download(url, tmp_path)
    else:
        video._fetch_captions(url, tmp_path)
    assert len(calls) == 1
    for flag in ('--ignore-config', '--no-plugin-dirs', '--no-remote-components',
                 '--no-cache-dir', '--no-playlist', '--no-mark-watched'):
        assert flag in calls[0]
    assert '--cookies' not in calls[0] and '--cookies-from-browser' not in calls[0]


@pytest.mark.parametrize('url,identity,expected', [
    ('https://www.youtube.com/watch?v=abcdefghijk', 'abcdefghijk', 'abcdefghijk'),
    ('https://www.youtube.com/watch?v=abcdefghijk', 'invalid?token=hidden', None),
    ('https://example.com/video', 'abcdefghijk', None),
])
def test_only_valid_youtube_ids_are_exposed(monkeypatch, url, identity, expected):
    monkeypatch.setattr(video, 'validate_remote_media_url', lambda value: value)
    monkeypatch.setattr(video, 'run_cmd', lambda args: subprocess.CompletedProcess(args, 0,
                        json.dumps({'duration': 1, 'id': identity}), ''))
    assert video.ytdlp_meta(url)['youtube_id'] == expected
