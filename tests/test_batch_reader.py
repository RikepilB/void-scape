"""Manual batch invariants: validate all, gate all, then isolate each read."""
import json
from pathlib import Path

import pytest
import batch_reader as batch
import video
import voidscape


def manifest(tmp_path, rows):
    path = tmp_path / 'batch.jsonl'
    path.write_text('\n'.join(json.dumps(row) for row in rows), encoding='utf-8')
    return path


def sources(tmp_path, count=2):
    rows = []
    for number in range(count):
        path = tmp_path / f'clip{number}.mp4'
        path.write_bytes(b'synthetic media placeholder')
        rows.append({'id': f'item{number}', 'input': path.name, 'reader': 'video', 'tier': 'audio'})
    return rows


def estimate(args, workspace):
    return 'video', {'duration_s': 10.0, 'cost_usd': {'agent': 0.01, 'total': 0.01},
                     'requires_cloud_approval': False, 'needs_model_download': False,
                     'needs_install': False}


def read_result(args, workspace):
    root = Path(args.workdir)
    root.mkdir()
    (root / 'manifest.json').write_text('{}')
    return 'video', {'workdir': str(root), 'status': 'complete'}


@pytest.mark.parametrize('field,value', [('allow_cloud', True), ('workdir', '../outside'),
                                        ('config', 'other.json'), ('frames', True),
                                        ('frames', -1), ('tier', 'unknown'), ('unknown', 1)])
def test_invalid_rows_never_start_preview_or_read(tmp_path, monkeypatch, field, value):
    rows = sources(tmp_path)
    rows[-1][field] = value
    path = manifest(tmp_path, rows)
    def forbidden(*args):
        pytest.fail('work began before complete schema validation')
    monkeypatch.setattr(voidscape, '_preview_data', forbidden)
    monkeypatch.setattr(voidscape, '_read_data', forbidden)
    with pytest.raises(ValueError):
        batch.read(path, tmp_path / 'output', {}, voidscape)
    assert not (tmp_path / 'output').exists()


def test_invalid_later_estimate_prevents_all_execution(tmp_path, monkeypatch):
    rows = sources(tmp_path)
    path = manifest(tmp_path, rows)
    def preview(args, workspace):
        if args.input.endswith('clip1.mp4'):
            raise ValueError('synthetic invalid second input')
        return estimate(args, workspace)
    monkeypatch.setattr(voidscape, '_preview_data', preview)
    monkeypatch.setattr(voidscape, '_read_data', lambda *args: pytest.fail('read started'))
    with pytest.raises(ValueError):
        batch.read(path, tmp_path / 'output', {}, voidscape)
    assert not (tmp_path / 'output').exists()


@pytest.mark.parametrize('field,kind', [('requires_cloud_approval', 'cloud_approval'),
                                      ('needs_model_download', 'model_download')])
def test_all_permissions_checked_before_output(tmp_path, monkeypatch, field, kind):
    path = manifest(tmp_path, sources(tmp_path))
    def preview(args, workspace):
        reader, data = estimate(args, workspace)
        data[field] = args.input.endswith('clip1.mp4')
        return reader, data
    monkeypatch.setattr(voidscape, '_preview_data', preview)
    monkeypatch.setattr(voidscape, '_read_data', lambda *args: pytest.fail('read started'))
    with pytest.raises(video.ApprovalRequired) as error:
        batch.read(path, tmp_path / 'output', {}, voidscape)
    assert error.value.gate['type'] == kind
    assert error.value.gate['items'] == ['item1']
    assert not (tmp_path / 'output').exists()


def test_preview_aggregates_costs_and_resolves_source_relative_paths(tmp_path, monkeypatch):
    path = manifest(tmp_path, sources(tmp_path))
    monkeypatch.setattr(voidscape, '_preview_data', estimate)
    other = tmp_path / 'elsewhere'
    other.mkdir()
    monkeypatch.chdir(other)
    plan = batch.prepare(path, {}, voidscape)
    assert plan['items'][0]['args'].input == str(tmp_path / 'clip0.mp4')
    preview = batch.preview_result(plan)
    assert preview['cost_usd']['total'] == 0.02
    assert preview['total'] == 2
    assert len(preview['manifest_sha256']) == 64
    assert not (tmp_path / 'output').exists()


def test_mixed_results_continue_and_persist_exact_summary(tmp_path, monkeypatch):
    rows = sources(tmp_path, 3)
    path = manifest(tmp_path, rows)
    calls = []
    monkeypatch.setattr(voidscape, '_preview_data', estimate)
    def read(args, workspace):
        calls.append(args.input)
        if args.input.endswith('clip1.mp4'):
            raise RuntimeError('synthetic execution failure')
        reader, result = read_result(args, workspace)
        if args.input.endswith('clip2.mp4'):
            result.update(status='stopped', stop_at='probe', stopped_by='user')
        return reader, result
    monkeypatch.setattr(voidscape, '_read_data', read)
    result = batch.read(path, tmp_path / 'output', {}, voidscape)
    assert len(calls) == 3
    assert (result['completed'], result['stopped'], result['failed']) == (1, 1, 1)
    assert result['items'][1]['result']['error']['code'] == 'operation_failed'
    assert result['items'][2]['result']['meta']['stopped_at'] == 'probe'
    assert json.loads((tmp_path / 'output/batch-summary.json').read_text()) == result
    assert not (tmp_path / 'output/batch-summary.next.json').exists()


def test_flags_are_not_persisted_or_reused(tmp_path, monkeypatch):
    rows = sources(tmp_path, 1)
    rows[0]['initial_prompt'] = 'SYNTHETIC_PRIVATE_VOCAB'
    path = manifest(tmp_path, rows)
    def preview(args, workspace):
        reader, data = estimate(args, workspace)
        data['requires_cloud_approval'] = True
        return reader, data
    monkeypatch.setattr(voidscape, '_preview_data', preview)
    def read(args, workspace):
        assert args.allow_cloud is True
        return read_result(args, workspace)
    monkeypatch.setattr(voidscape, '_read_data', read)
    batch.read(path, tmp_path / 'first', {}, voidscape, allow_cloud=True)
    saved = (tmp_path / 'first/batch-summary.json').read_text()
    assert 'SYNTHETIC_PRIVATE_VOCAB' not in saved
    assert '"allow_cloud"' not in saved
    with pytest.raises(video.ApprovalRequired):
        batch.read(path, tmp_path / 'second', {}, voidscape)
    assert not (tmp_path / 'second').exists()


@pytest.mark.parametrize('raw', ['{"input":"a","input":"b"}', '{"input":"a","start":NaN}', '[]', ''])
def test_strict_json_manifest(raw, tmp_path):
    path = tmp_path / 'manifest.jsonl'
    path.write_text(raw)
    with pytest.raises(ValueError):
        batch.load(path, voidscape)


@pytest.mark.parametrize('identifier', ['../escape', '/absolute', 'a/b', '..', 'a.b'])
def test_ids_cannot_express_paths(tmp_path, identifier):
    rows = sources(tmp_path, 1)
    rows[0]['id'] = identifier
    with pytest.raises(ValueError):
        batch.load(manifest(tmp_path, rows), voidscape)


def test_casefold_duplicate_ids_fail(tmp_path):
    rows = sources(tmp_path)
    rows[0]['id'], rows[1]['id'] = 'Same', 'same'
    with pytest.raises(ValueError):
        batch.load(manifest(tmp_path, rows), voidscape)


def test_bounds(tmp_path):
    path = tmp_path / 'manifest.jsonl'
    path.write_bytes(b' ' * (batch.MAX_BYTES + 1))
    with pytest.raises(ValueError, match='1 MiB'):
        batch.load(path, voidscape)
    rows = sources(tmp_path, 1)
    many = [{**rows[0], 'id': f'row{i}'} for i in range(101)]
    with pytest.raises(ValueError, match='100 items'):
        batch.load(manifest(tmp_path, many), voidscape)


def test_preexisting_root_is_preserved(tmp_path, monkeypatch):
    rows = sources(tmp_path)
    path = manifest(tmp_path, rows)
    root = tmp_path / 'output'
    root.mkdir()
    (root / 'keep.txt').write_text('keep')
    monkeypatch.setattr(voidscape, '_preview_data', lambda *args: pytest.fail('preview started'))
    with pytest.raises(ValueError):
        batch.read(path, root, {}, voidscape)
    assert (root / 'keep.txt').read_text() == 'keep'


def test_observed_root_replacement_stops_following_items(tmp_path, monkeypatch):
    path = manifest(tmp_path, sources(tmp_path))
    monkeypatch.setattr(voidscape, '_preview_data', estimate)
    original = batch._identity
    replaced = False
    def identity(root):
        device, inode = original(root)
        return device, inode + int(replaced)
    monkeypatch.setattr(batch, '_identity', identity)
    calls = []
    def read(args, workspace):
        nonlocal replaced
        calls.append(args.input)
        result = read_result(args, workspace)
        replaced = True
        return result
    monkeypatch.setattr(voidscape, '_read_data', read)
    with pytest.raises(ValueError, match='replaced'):
        batch.read(path, tmp_path / 'output', {}, voidscape)
    assert len(calls) == 1


def test_video_options_rejected_for_articles(tmp_path):
    source = tmp_path / 'note.md'
    source.write_text('# Local note\n\nBody.')
    path = manifest(tmp_path, [{'input': 'note.md', 'reader': 'article', 'frames': 3}])
    with pytest.raises(ValueError, match='video-only'):
        batch.load(path, voidscape)


def test_cli_failure_retains_batch_data(tmp_path, monkeypatch, capsys):
    path = manifest(tmp_path, sources(tmp_path))
    monkeypatch.setattr(voidscape, '_load_workspace', lambda *args: {})
    monkeypatch.setattr(voidscape, '_preview_data', estimate)
    monkeypatch.setattr(voidscape, '_read_data', lambda *args: (_ for _ in ()).throw(RuntimeError('synthetic failure')))
    assert voidscape.main(['batch-read', str(path), '--workdir', str(tmp_path / 'output'), '--json']) == 6
    output = json.loads(capsys.readouterr().out)
    assert output['ok'] is False
    assert output['meta']['command'] == 'batch-read'
    assert output['data']['failed'] == 2
    assert len(output['data']['items']) == 2


@pytest.mark.parametrize('stopped_count', [1, 2])
def test_cli_success_with_stopped_items(tmp_path, monkeypatch, capsys, stopped_count):
    path = manifest(tmp_path, sources(tmp_path))
    monkeypatch.setattr(voidscape, '_load_workspace', lambda *args: {})
    monkeypatch.setattr(voidscape, '_preview_data', estimate)
    def read(args, workspace):
        reader, result = read_result(args, workspace)
        if stopped_count == 2 or args.input.endswith('clip0.mp4'):
            result.update(status='stopped', stop_at='probe', stopped_by='user')
        return reader, result
    monkeypatch.setattr(voidscape, '_read_data', read)
    root = tmp_path / 'output'
    assert voidscape.main(['batch-read', str(path), '--workdir', str(root), '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['ok'] is True
    assert result['data']['status'] == 'completed_with_stops'
    assert result['data']['stopped'] == stopped_count
    assert result['data']['completed'] == 2 - stopped_count
    assert 'stopped_at' not in result['meta']
    assert json.loads((root / 'batch-summary.json').read_text()) == result['data']


def test_runtime_reader_rechecks_permission(tmp_path, monkeypatch):
    path = manifest(tmp_path, [{'input': 'https://example.com/article', 'reader': 'article'}])
    calls = []
    def article_estimate(*args):
        calls.append(1)
        return {'requires_cloud_approval': len(calls) > 1,
                'cost_usd': {'agent': 0.01, 'total': 0.01}}
    monkeypatch.setattr(voidscape.article_engine, 'estimate', article_estimate)
    monkeypatch.setattr(voidscape.article_engine, 'run', lambda *args, **kwargs: pytest.fail('unapproved fetch'))
    result = batch.read(path, tmp_path / 'output', {}, voidscape)
    assert len(calls) == 2
    assert result['failed'] == 1
    assert result['items'][0]['result']['error']['code'] == 'approval_required'
    assert not (tmp_path / 'output/001-item001').exists()


def test_failed_reader_keeps_its_partial_evidence(tmp_path, monkeypatch):
    path = manifest(tmp_path, sources(tmp_path, 1))
    monkeypatch.setattr(voidscape, '_preview_data', estimate)
    def operation(progress, args):
        root = Path(args.workdir)
        root.mkdir()
        transcript = root / 'transcript.txt'
        transcript.write_text('[00:00] synthetic evidence')
        progress.result = {'workdir': str(root), 'transcript': str(transcript)}
        progress.complete('transcribe')
        progress.begin('align')
        raise RuntimeError('synthetic alignment failure')
    monkeypatch.setattr(voidscape, '_read_data', lambda args, workspace: video.execute_read(operation, args))
    result = batch.read(path, tmp_path / 'output', {}, voidscape)
    outcome = result['items'][0]['result']
    assert outcome['ok'] is False
    assert outcome['data']['status'] == 'partial'
    assert outcome['meta']['failed_stage'] == 'align'
    assert Path(outcome['data']['transcript']).is_file()


def test_real_article_and_chat_batch(tmp_path, monkeypatch, capsys):
    (tmp_path / 'note.md').write_text('# Local note\n\nSynthetic batch evidence.')
    (tmp_path / 'chat.txt').write_text('[01/01/2026, 10:00:00] Alex: Hello\n[01/01/2026, 10:01:00] Sam: Agreed\n')
    path = manifest(tmp_path, [{'id': 'note', 'input': 'note.md', 'reader': 'article'},
                               {'id': 'chat', 'input': 'chat.txt', 'reader': 'chat'}])
    monkeypatch.setattr(voidscape, '_load_workspace', lambda *args: {})
    assert voidscape.main(['batch-preview', str(path), '--json']) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview['data']['total'] == 2
    assert preview['data']['gates'] == []
    root = tmp_path / 'output'
    assert voidscape.main(['batch-read', str(path), '--workdir', str(root), '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['ok'] is True
    assert result['data']['completed'] == 2
    for item in result['data']['items']:
        wd = Path(item['result']['data']['workdir'])
        pointer = json.loads((wd / '.agent/latest-read.json').read_text())
        assert all((wd / evidence).is_file() for evidence in pointer['evidence'])
    assert (tmp_path / 'note.md').is_file()
    assert (tmp_path / 'chat.txt').is_file()


def test_symlink_source_is_rejected(tmp_path):
    target = tmp_path / 'real.mp4'
    target.write_bytes(b'synthetic')
    link = tmp_path / 'link.mp4'
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip('symlink creation unavailable')
    path = manifest(tmp_path, [{'input': str(link), 'reader': 'video'}])
    with pytest.raises(ValueError, match='links'):
        batch.load(path, voidscape)


def test_manifest_reference_resolves_relative_to_manifest(tmp_path, monkeypatch):
    rows = sources(tmp_path, 1)
    reference = tmp_path / 'vocabulary.txt'
    reference.write_text('Synthetic reference')
    rows[0]['align_reference'] = 'vocabulary.txt'
    plan = batch.load(manifest(tmp_path, rows), voidscape)
    assert plan['items'][0]['args'].align_reference == str(reference)
