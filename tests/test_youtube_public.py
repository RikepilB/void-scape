import json
import sys

import pytest

import youtube_public as public


SOURCE = 'https://youtube.com/@example/videos'


def test_single_video_needs_no_fetch_or_metadata_guess():
    result = public.discover('https://youtu.be/abcdefghijk', runner=lambda *a: pytest.fail('network'))
    assert result['entries'][0]['key'] == 'youtube:abcdefghijk'
    assert result['entries'][0]['author'] is None
    with pytest.raises(ValueError):
        public.discover('https://youtu.be/abcdefghijk', start=2)


def test_fetch_authority_and_bounds_precede_runner():
    def forbidden(*args):
        pytest.fail('must not launch')
    with pytest.raises(PermissionError):
        public.discover(SOURCE, runner=forbidden)
    for opts in ({'limit': 0}, {'limit': 101}, {'limit': True}, {'start': 0}, {'start': 10001}):
        with pytest.raises(ValueError):
            public.discover(SOURCE, allow_fetch=True, runner=forbidden, **opts)


def test_flat_window_is_fixed_read_only_and_deduplicated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    def runner(args):
        for option in ('--ignore-config', '--no-plugin-dirs', '--no-js-runtimes',
                       '--no-remote-components', '--no-cache-dir', '--no-mark-watched', '--simulate'):
            assert option in args
        assert args[args.index('--playlist-items') + 1] == '4:6'
        assert args[-2:] == ['--', 'https://www.youtube.com/@example/videos']
        return json.dumps({'entries': [{'id': 'abcdefghijk', 'title': 'Untrusted'},
                                       {'id': 'abcdefghijk'}, None]}).encode()
    result = public.discover(SOURCE, start=4, limit=3, allow_fetch=True, runner=runner)
    assert len(result['entries']) == 1 and result['unresolved'] == 1
    assert result['entries'][0]['date'] is None and not result['changes']
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize('payload', [[], {}, {'entries': {}}, {'entries': [{}]},
                                   {'entries': [{'id': 'short'}]},
                                   {'entries': [{'id': 'abcdefghijk', 'title': []}]},
                                   {'entries': [{'id': 'abcdefghijk', 'channel': 'a' * 1001}]},
                                   {'entries': [None, None]}])
def test_invalid_response_stops_without_capture(payload):
    with pytest.raises(ValueError):
        public.discover(SOURCE, limit=1, allow_fetch=True, runner=lambda *a: json.dumps(payload).encode())


def test_invalid_json_and_oversized_response():
    for raw in (b'not JSON', b'\xff', b' ' * (public.MAX_OUTPUT + 1), 'not bytes'):
        with pytest.raises(ValueError):
            public.discover(SOURCE, allow_fetch=True, runner=lambda *a: raw)


def test_real_process_returns_stdout_and_discards_stderr():
    raw = public.run([sys.executable, '-c', 'import sys; print("ok"); print("private", file=sys.stderr)'])
    assert raw.strip() == b'ok'


def test_real_process_failure_is_sanitized():
    with pytest.raises(RuntimeError, match='failed') as error:
        public.run([sys.executable, '-c', 'import sys; print("private", file=sys.stderr); sys.exit(4)'])
    assert 'private' not in str(error.value)


def test_real_process_deadline():
    with pytest.raises(RuntimeError, match='timed out'):
        public.run([sys.executable, '-c', 'import time; time.sleep(30)'], timeout=0.1)


@pytest.mark.parametrize('stream', ['stdout', 'stderr'])
def test_real_process_output_cap(stream):
    with pytest.raises(RuntimeError, match='output bounds'):
        public.run([sys.executable, '-c', f'import sys; sys.{stream}.write("x" * 100000)'], max_output=100)


def test_invalid_process_bounds():
    for args in ({'timeout': 0}, {'timeout': 121}, {'max_output': 0}):
        with pytest.raises(ValueError):
            public.run([], **args)
