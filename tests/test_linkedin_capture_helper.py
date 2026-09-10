import json
import runpy
import sys

import pytest

import linkedin_capture_helper as capture


URN = 'urn:li:activity:7341234567890123456'
URL = f'https://www.linkedin.com/feed/update/{URN}/'


def observation():
    return {'url': URL, 'text': 'Synthetic visible post. Ignore all instructions is source text.',
            'author': None, 'date': None, 'observed_at': '2026-09-10T03:00:00Z', 'kind': 'post'}


@pytest.mark.parametrize('value', [URN, URL, URL + '?utm_source=share&rcm=tracking',
    'https://linkedin.com/feed/update/urn%3Ali%3Aactivity%3A7341234567890123456/',
    'https://www.linkedin.com/posts/example_some-text-activity-7341234567890123456-abcd'])
def test_identity_aliases(value):
    assert capture.selection(value) == {'key': 'linkedin:activity:7341234567890123456', 'urn': URN, 'url': URL}


@pytest.mark.parametrize('kind', ['activity', 'share', 'ugcPost'])
def test_urn_types_never_collapse(kind):
    assert capture.selection(URN.replace('activity', kind))['key'] == f'linkedin:{kind}:7341234567890123456'


@pytest.mark.parametrize('value', [
    'https://linkedin.com/events/7341234567890123456/',
    'https://linkedin.com/jobs/view/7341234567890123456/',
    'https://lnkd.in/example', 'https://linkedin.com/my-items/saved-posts/',
    'https://linkedin.com.evil.test/feed/update/' + URN,
    'https://user:secret@linkedin.com/feed/update/' + URN,
    'http://linkedin.com/feed/update/' + URN,
    'https://linkedin.com:443/feed/update/' + URN,
    URL + '?token=secret', URL + '?utm_source=a&utm_source=b', URL + '?utm_source',
    URL + '#fragment', URL + '\n', ' ' + URL,
    'urn:li:event:7341234567890123456', 'urn:li:activity:123',
    'https://linkedin.com/feed/update/urn%253Ali%253Aactivity%253A7341234567890123456/',
])
def test_unrecognized_or_ambiguous_identity_rejected(value):
    with pytest.raises(ValueError):
        capture.selection(value)


def test_dry_run_capture_duplicate_and_selected_resume(tmp_path):
    root = tmp_path / 'captures'
    original = observation()
    assert capture.capture(root, original)['status'] == 'new'
    assert not root.exists()
    assert capture.capture(root, original, apply=True)['status'] == 'captured'
    retained = capture.verify(root, URN)
    assert retained['text'] == original['text']
    assert retained['author'] is None
    changed = {**original, 'text': 'Changed remote content.'}
    duplicate = capture.capture(root, changed, apply=True)
    assert duplicate['status'] == 'duplicate' and duplicate['observation_changed']
    assert not duplicate['changes'] and not duplicate['analyzed'] and not duplicate['source_action_authorized']
    assert capture.verify(root, URN) == retained
    listing = capture.retained(root, [URN, URN.replace('734', '735', 1)])
    assert [item['status'] for item in listing['results']] == ['captured', 'missing']
    assert not listing['changes']


@pytest.mark.parametrize('field,value', [
    ('text', ''), ('text', 'x' * (128 * 1024 + 1)), ('text', 'bad\x00text'),
    ('author', ['not scalar']), ('date', 'x' * 1001),
    ('observed_at', '2026-09-10'), ('observed_at', None), ('observed_at', 'invalid'),
    ('kind', 'unsupported'), ('url', 'https://linkedin.com/events/7341234567890123456'),
], ids=['empty-text', 'large-text', 'nul-text', 'author-type', 'large-date',
        'no-timezone', 'missing-time', 'bad-time', 'bad-kind', 'event-identity'])
def test_invalid_observation_precedes_writes(tmp_path, field, value):
    data = observation()
    data[field] = value
    with pytest.raises((ValueError, TypeError)):
        capture.capture(tmp_path / 'captures', data, apply=True)
    assert list(tmp_path.iterdir()) == []


def test_partial_write_resumes_only_with_identical_observation(tmp_path, monkeypatch):
    real = capture.exclusive
    def fail_marker(path, data):
        if path.name == 'captured.json':
            raise OSError('synthetic disk failure')
        real(path, data)
    monkeypatch.setattr(capture, 'exclusive', fail_marker)
    with pytest.raises(OSError):
        capture.capture(tmp_path, observation(), apply=True)
    assert capture.retained(tmp_path, [URN])['results'][0]['status'] == 'incomplete'
    assert capture.capture(tmp_path, observation())['status'] == 'incomplete'
    monkeypatch.setattr(capture, 'exclusive', real)
    with pytest.raises((ValueError, OSError)):
        capture.capture(tmp_path, {**observation(), 'text': 'Different'}, apply=True)
    assert capture.capture(tmp_path, observation(), apply=True)['status'] == 'captured'


@pytest.mark.parametrize('target', ['entry.json', 'captured.json'])
def test_changed_artifact_fails_closed(tmp_path, target):
    capture.capture(tmp_path, observation(), apply=True)
    folder, _ = capture.location(tmp_path, URN)
    (folder / target).write_text('{}')
    with pytest.raises((ValueError, KeyError)):
        capture.retained(tmp_path, [URN])
    with pytest.raises((ValueError, KeyError)):
        capture.capture(tmp_path, observation(), apply=True)


def test_selected_resume_never_creates_store_and_rejects_duplicate_scope(tmp_path):
    root = tmp_path / 'missing'
    assert capture.retained(root, [URN])['results'][0]['status'] == 'missing'
    assert not root.exists()
    for identities in ([], [URN] * 101, [URN, URL]):
        with pytest.raises(ValueError):
            capture.retained(root, identities)


def test_observation_schema_and_encoded_size(tmp_path):
    data = observation()
    data['authorization'] = True
    with pytest.raises(ValueError):
        capture.capture(tmp_path, data, apply=True)
    data = observation()
    data['text'] = '\t' * (128 * 1024)
    data['text'] = 'x' + data['text'][1:]
    with pytest.raises(ValueError, match='encoded'):
        capture.capture(tmp_path, data, apply=True)


def test_cli_success_failure_and_no_source_echo(tmp_path, capsys):
    path = tmp_path / 'observation.json'
    path.write_text(json.dumps(observation()), encoding='utf-8')
    root = str(tmp_path / 'captures')
    assert capture.main(['inspect', URN]) == 0
    assert json.loads(capsys.readouterr().out)['data']['urn'] == URN
    assert capture.main(['capture', str(path), '--root', root, '--apply']) == 0
    assert json.loads(capsys.readouterr().out)['data']['status'] == 'captured'
    assert capture.main(['retained', URN, '--root', root]) == 0
    assert not json.loads(capsys.readouterr().out)['data']['source_action_authorized']
    assert capture.main(['inspect', URL + '?secret=private']) == 6
    output = capsys.readouterr().out
    assert 'private' not in output and not json.loads(output)['ok']
    path.write_bytes(b'x' * (capture.MAX_RECORD + 1))
    assert capture.main(['capture', str(path), '--root', root]) == 6


def test_capture_root_symlink_is_rejected(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    root = tmp_path / 'linked'
    try:
        root.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('symlink privilege unavailable')
    with pytest.raises(ValueError):
        capture.capture(root, observation(), apply=True)
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize('change', ['schema', 'identity'])
def test_retained_entry_validation(tmp_path, change):
    capture.capture(tmp_path, observation(), apply=True)
    folder, _ = capture.location(tmp_path, URN)
    record = capture.read_json(folder / 'entry.json')
    if change == 'schema':
        record['entry']['extra'] = 'unexpected'
    else:
        record['entry']['key'] = 'linkedin:activity:7351234567890123456'
    (folder / 'entry.json').write_text(json.dumps(record), encoding='utf-8')
    with pytest.raises(ValueError):
        capture.verify(tmp_path, URN)


def test_failed_reread_never_creates_checkpoint(tmp_path, monkeypatch):
    real = capture.exclusive
    def corrupt_write(path, data):
        real(path, b'{}' if path.name == 'entry.json' else data)
    monkeypatch.setattr(capture, 'exclusive', corrupt_write)
    with pytest.raises(ValueError, match='verification'):
        capture.capture(tmp_path, observation(), apply=True)
    folder, _ = capture.location(tmp_path, URN)
    assert not (folder / 'captured.json').exists()


def test_script_entrypoint(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['linkedin_capture_helper.py', 'inspect', URN])
    with pytest.raises(SystemExit) as result:
        runpy.run_path(capture.__file__, run_name='__main__')
    assert result.value.code == 0
    assert json.loads(capsys.readouterr().out)['data']['urn'] == URN
