"""Preview or process a bounded local recording inbox without cloud fallback."""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

import local_notes
from process_deadline import run as bounded_worker, ProcessDeadlineError
from triage_store import checked, digest, encoded, exclusive, file_digest, locked, TriageBusyError

REPO = Path(__file__).resolve().parents[1]
MEDIA = {'.mp4', '.mkv', '.mov', '.webm', '.avi', '.m4v', '.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.opus'}
LOCAL = {'captions', 'faster-whisper', 'whisper-cpp'}
SHA = re.compile('[a-f0-9]{64}')


def retain(path):
    path = checked(path)
    with path.open('r+b') as stream:
        os.fsync(stream.fileno())
    return {'path': str(path), 'sha256': file_digest(path)}


def metadata_bytes(path, limit=4 * 1024 * 1024):
    with checked(path).open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('inbox metadata exceeds limit')
    return raw


def json_file(path, limit=4 * 1024 * 1024):
    value = json.loads(metadata_bytes(path, limit))
    if not isinstance(value, dict):
        raise ValueError('inbox metadata must be an object')
    return value


def settled(source, min_age, *, now=None):
    """A quiet period reduces partial-copy reads; subsequent hashes still matter."""
    if not 0 <= min_age <= 86400:
        raise ValueError('quiet period must be between zero and one day')
    cutoff = (time.time() if now is None else now) - min_age
    paths = [checked(source)]
    for suffix in ('.srt', '.vtt', '.txt'):
        sidecar = checked(source.with_suffix(suffix))
        if sidecar.exists():
            paths.append(sidecar)
    return all(path.stat().st_mtime <= cutoff for path in paths)


def discover(root, limit, *, min_age=0):
    """Bound the directory walk as well as the number of selected recordings."""
    root = checked(root)
    if not root.is_dir() or not 1 <= limit <= 100:
        raise ValueError('existing inbox and limit 1..100 required')
    found, scanned = [], 0
    for directory, folders, files in os.walk(root, followlinks=False):
        scanned += len(folders) + len(files)
        if scanned > 10000:
            raise ValueError('inbox discovery exceeds 10000 entries')
        folders[:] = [name for name in folders if not name.startswith('.') and name != 'processed']
        for name in folders:
            checked(Path(directory) / name)
        for name in files:
            path = checked(Path(directory) / name)
            if (not name.startswith('.') and path.suffix.lower() in MEDIA and path.is_file()
                    and settled(path, min_age)):
                found.append((path.stat().st_mtime_ns, str(path.relative_to(root)), path))
    return [item[2] for item in sorted(found)[:limit]]


def checkpoint(root):
    path = checked(root / '.processed.json')
    if not path.exists():
        return {'schema': 1, 'owner': 'voidscape-inbox', 'items': {}}
    value = json_file(path)
    if (set(value) != {'schema', 'owner', 'items'} or value['schema'] != 1 or
            value['owner'] != 'voidscape-inbox' or not isinstance(value['items'], dict)):
        raise ValueError('unrecognized inbox checkpoint; preserve for review')
    return value


def note_path(notes_root, original, identity):
    relative = Path(original)
    if (relative.is_absolute() or not relative.name or
            any(part.startswith('.') or part == 'processed' for part in relative.parts)):
        raise ValueError('invalid original recording path')
    folder = notes_root / 'Conference' / relative.parts[0] if len(relative.parts) > 1 else notes_root / '03_Media/Transcripts'
    path = checked(folder / f'{identity}.md')
    path.relative_to(notes_root)
    return path


def mark(root, identity, receipt, status):
    """Replace only our validated index; immutable receipts remain authoritative."""
    path = checked(root / '.processed.json')
    before = metadata_bytes(path) if path.exists() else None
    value = checkpoint(root)
    value['items'][identity] = {'receipt_sha256': file_digest(receipt), 'status': status}
    raw = encoded(value)
    if raw == before:
        return
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('checkpoint capacity exceeded')
    stage = checked(root / f'.inbox-index-{uuid.uuid4().hex}.tmp')
    exclusive(stage, raw)
    if (metadata_bytes(path) if path.exists() else None) != before:
        raise ValueError('checkpoint changed during processing')
    os.replace(stage, path)


def verify_receipt(root, notes_root, path, *, repair=False):
    record = json_file(path)
    identity = record.get('source_sha256', '')
    if (not isinstance(identity, str) or not SHA.fullmatch(identity) or path.stem != identity or
            record.get('schema') != 1):
        raise ValueError('invalid inbox receipt identity')
    prior = checkpoint(root)['items'].get(identity)
    if prior and prior['receipt_sha256'] != file_digest(path):
        raise ValueError('inbox receipt changed')
    expected_note = note_path(notes_root, record['original_name'], identity)
    if record['note']['path'] != str(expected_note):
        raise ValueError('published inbox note path changed')
    if not isinstance(record['evidence'], list) or not 1 <= len(record['evidence']) <= 512:
        raise ValueError('invalid retained evidence list')
    scope = checked(root / '.inbox/work' / identity)
    for item in record['evidence']:
        artifact = checked(item['path'])
        artifact.relative_to(scope)
        if file_digest(artifact) != item['sha256']:
            raise ValueError('retained inbox evidence changed')
    draft = checked(record['draft'])
    draft.relative_to(scope)
    if file_digest(draft) != record['note']['sha256']:
        raise ValueError('retained inbox draft changed')
    relative = Path(record['original_name'])
    if relative.is_absolute() or any(part in {'..', '.', 'processed', '.inbox'} for part in relative.parts):
        raise ValueError('invalid original recording path')
    destination = checked(root / 'processed' / relative)
    destination.relative_to(root / 'processed')
    if repair and not prior and not expected_note.exists():
        expected_note.parent.mkdir(parents=True, exist_ok=True)
        with draft.open('rb') as stream:
            raw = stream.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('retained note exceeds limit')
        exclusive(expected_note, raw)
    if file_digest(expected_note) != record['note']['sha256']:
        raise ValueError('published inbox note changed')
    return record, destination


def finish_move(root, notes_root, source, receipt, *, current_name=False):
    record, destination = verify_receipt(root, notes_root, receipt)
    if current_name:
        destination = checked(root / 'processed' / source.relative_to(root))
        destination.relative_to(root / 'processed')
    identity = record['source_sha256']
    if file_digest(source) != identity:
        raise ValueError('recording changed before move')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        # Same-filesystem link plus unlink never overwrites a competing destination.
        os.link(source, destination)
    if file_digest(destination) != identity:
        raise ValueError('processed destination collision')
    with destination.open('r+b') as stream:
        os.fsync(stream.fileno())
    verify_receipt(root, notes_root, receipt)
    if file_digest(source) != identity:
        raise ValueError('recording changed during move')
    source.unlink()
    mark(root, identity, receipt, 'processed')
    return {'status': 'processed', 'source_sha256': identity, 'note': record['note']['path'],
            'processed': str(destination)}


def invoke_reader(command, source, work, *options):
    identity = uuid.uuid4().hex
    log = checked(work / f'{command}-{identity}.json')
    error = checked(work / f'{command}-{identity}.stderr')
    with log.open('xb') as output, error.open('xb') as stderr:
        result = subprocess.run([sys.executable, '-m', 'skill.scripts.voidscape', command,
                                 str(source), *options, '--json'], cwd=REPO,
                                stdin=subprocess.DEVNULL, stdout=output, stderr=stderr)
    if result.returncode:
        raise ValueError('reader failed; evidence retained locally')
    value = json_file(log)
    if any(key in value for key in ('error', 'ok', 'data')):
        raise ValueError('unexpected reader response contract')
    return value


def prepare(source, work, model, backend, port):
    info = invoke_reader('inspect', source, work)
    if info.get('source') != 'local':
        raise ValueError('inbox accepts local recordings only')
    selected = ('captions' if info.get('sidecar_transcript') else 'faster-whisper') if backend == 'auto' else backend
    tier = 'both' if info.get('width') and info.get('height') else 'audio'
    options = ('--tier', tier, '--backend', selected)
    preview = invoke_reader('preview', source, work, *options)
    if (preview.get('backend') not in LOCAL or preview.get('free') is not True or
            any(preview.get(gate) is not False for gate in
                ('requires_cloud_approval', 'needs_model_download', 'needs_install'))):
        raise ValueError('unattended reader requires available local backend and explicit safe gates')
    bundle = work / 'evidence'
    sidecar = checked(info['sidecar_transcript']) if info.get('sidecar_transcript') else None
    inputs = {'source': str(source), 'source_sha256': file_digest(source), 'backend': backend,
              'sidecar': str(sidecar) if sidecar else None,
              'sidecar_sha256': file_digest(sidecar) if sidecar else None}
    ready = work / 'ready.json'
    if ready.exists():
        retained = json_file(ready)
        if retained['inputs'] != inputs:
            raise ValueError('retained read input changed')
        for artifact in retained['artifacts']:
            path = checked(artifact['path'])
            path.relative_to(bundle)
            if file_digest(path) != artifact['sha256']:
                raise ValueError('retained read evidence changed')
    else:
        result = invoke_reader('read', source, work, *options, '--workdir', str(bundle))
        if result.get('status') != 'complete' or result.get('backend') not in LOCAL:
            raise ValueError('completed local evidence required')
        if file_digest(source) != inputs['source_sha256'] or (sidecar and file_digest(sidecar) != inputs['sidecar_sha256']):
            raise ValueError('recording or sidecar changed during read')
        artifacts = [path for path in bundle.rglob('*') if path.is_file()]
        if not 1 <= len(artifacts) <= 512:
            raise ValueError('retained read file limit exceeded')
        exclusive(ready, encoded({'inputs': inputs, 'artifacts': [retain(path) for path in artifacts]}))
    draft = work / f'draft-{uuid.uuid4().hex}.md'
    local_notes.draft(bundle, draft, model, port=port, timeout=300)
    text = draft.read_text(encoding='utf-8')
    # Provenance comes from the local probe, not from the model's interpretation.
    provenance = (f'Source: {html.escape(json.dumps(str(source), ensure_ascii=False))}\n'
                  f'Duration seconds: {info.get("duration_s")}\nLanguage: unknown\n')
    text = '\n'.join(provenance.rstrip() if line.startswith('Source: ') else line for line in text.splitlines()) + '\n'
    published = work / f'publication-{uuid.uuid4().hex}.md'
    exclusive(published, text.encode('utf-8'))
    artifacts = [path for path in bundle.rglob('*') if path.is_file() and '.note-checkpoints' not in path.parts]
    if not artifacts or len(artifacts) > 512:
        raise ValueError('evidence file limit exceeded')
    return published, artifacts


def reusable_work(root, identity, source, backend):
    scope = checked(root / '.inbox/work' / identity)
    if not scope.exists():
        return None
    for ready in sorted(scope.glob('*/ready.json'), reverse=True):
        inputs = json_file(ready)['inputs']
        if inputs['source'] != str(source) or inputs['source_sha256'] != identity or inputs['backend'] != backend:
            continue
        if inputs['sidecar']:
            sidecar = checked(inputs['sidecar'])
            if sidecar not in {source.with_suffix(suffix) for suffix in ('.srt', '.vtt', '.txt')}:
                raise ValueError('retained sidecar is outside recording scope')
            if file_digest(sidecar) != inputs['sidecar_sha256']:
                continue
        return checked(ready.parent)
    return None


def process_one(root, notes_root, source, model, backend, port, producer=prepare, *, min_age=0):
    root, notes_root, source = checked(root), checked(notes_root), checked(source)
    relative = source.relative_to(root)
    if any(part.startswith('.') or part == 'processed' for part in relative.parts) or source.suffix.lower() not in MEDIA:
        raise ValueError('recording outside selected input scope')
    if not settled(source, min_age):
        return {'status': 'deferred', 'source': str(source), 'reason': 'recording or sidecar is still changing'}
    identity = file_digest(source)
    receipt = checked(root / '.inbox/receipts' / f'{identity}.json')
    if receipt.exists():
        record, destination = verify_receipt(root, notes_root, receipt, repair=True)
        if destination.exists():
            if file_digest(destination) != identity:
                raise ValueError('processed recording changed')
            # A leftover source from a linked-but-not-unlinked move is recoverable.
            if str(relative) == record['original_name']:
                return finish_move(root, notes_root, source, receipt)
            result = finish_move(root, notes_root, source, receipt, current_name=True)
            result.update(status='skipped', reason='verified-content-duplicate')
            return result
        return finish_move(root, notes_root, source, receipt)
    if identity in checkpoint(root)['items']:
        raise ValueError('checkpoint references a missing receipt')
    work = reusable_work(root, identity, source, backend)
    if work is None:
        work = checked(root / '.inbox/work' / identity / uuid.uuid4().hex)
        work.mkdir(parents=True)
    draft, evidence = producer(source, work, model, backend, port)
    if file_digest(source) != identity:
        raise ValueError('recording changed during processing')
    with checked(draft).open('rb') as stream:
        raw = stream.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('recording note exceeds limit')
    text = raw.decode('utf-8')
    if any(text.splitlines().count(title) != 1 for title in ('## Synopsis', '## Action Items', '## Key moments', '## Full Transcript')):
        raise ValueError('recording note lacks required sections')
    note = note_path(notes_root, relative, identity)
    artifacts = [retain(path) for path in evidence]
    for artifact in artifacts:
        Path(artifact['path']).relative_to(work)
    record = {'schema': 1, 'source_sha256': identity, 'original_name': str(relative), 'draft': str(checked(draft)),
              'note': {'path': str(note), 'sha256': digest(raw)}, 'evidence': artifacts,
              'content_trust': 'untrusted'}
    receipt.parent.mkdir(parents=True, exist_ok=True)
    exclusive(receipt, encoded(record))
    note.parent.mkdir(parents=True, exist_ok=True)
    exclusive(note, raw)
    mark(root, identity, receipt, 'published')
    return finish_move(root, notes_root, source, receipt)


def recover(root, notes_root):
    """Repair only completion records when a source was already moved."""
    folder = checked(root / '.inbox/receipts')
    if not folder.exists():
        return
    receipts = list(folder.glob('*.json'))
    if len(receipts) > 10000:
        raise ValueError('receipt count exceeds limit')
    for receipt in receipts:
        record, destination = verify_receipt(root, notes_root, receipt, repair=True)
        if destination.exists():
            if file_digest(destination) != record['source_sha256']:
                raise ValueError('processed source integrity failed')
            prior = checkpoint(root)['items'].get(record['source_sha256'], {})
            if prior.get('status') != 'processed':
                mark(root, record['source_sha256'], receipt, 'processed')


def _process(root, notes_root, model, *, backend='auto', port=11434, limit=10, timeout=1800, min_age=60, apply=False):
    if (backend not in LOCAL | {'auto'} or type(port) is not int or not 1 <= port <= 65535 or
            not 0 < timeout <= 86400 or not 0 <= min_age <= 86400 or not isinstance(model, str) or
            not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,160}', model)):
        raise ValueError('invalid inbox processing settings')
    root, notes_root = checked(root), checked(notes_root)
    for destination in (notes_root / '03_Media/Transcripts', notes_root / 'Conference'):
        if destination == root or root in destination.parents or destination in root.parents:
            raise ValueError('inbox and note destination must be separate trees')
    selected = discover(root, limit, min_age=min_age)
    if not apply:
        return {'mode': 'preview', 'selected': [str(path) for path in selected],
                'notes_root': str(notes_root), 'min_age': min_age, 'changes': False}
    results = []
    with locked(root / '.inbox'):
        # Recovery also runs under the deadline; rehashing large retained files
        # must not stall the foreground controller indefinitely.
        jobs = ([None] if (root / '.inbox/receipts').exists() else []) + selected
        for source in jobs:
            run_root = checked(root / '.inbox/runs' / uuid.uuid4().hex)
            run_root.mkdir(parents=True)
            result_path = run_root / 'result.json'
            command = [sys.executable, str(Path(__file__).resolve()), '--worker', '--root', str(root),
                       '--notes-root', str(notes_root), '--model', model,
                       '--backend', backend, '--port', str(port), '--min-age', str(min_age), '--result', str(result_path)]
            command += ['--recover'] if source is None else ['--source', str(source)]
            try:
                bounded_worker(command, timeout=timeout, log=run_root / 'worker.log', cwd=REPO)
                result = json_file(result_path)
            except (OSError, ValueError, ProcessDeadlineError):
                result = {'status': 'failed', 'source': str(source),
                          'reason': 'Processing failed or exceeded deadline; retained evidence requires local review.'}
                exclusive(run_root / 'failure.json', encoded(result))
            results.append(result)
    return {'mode': 'apply', 'processed': sum(item['status'] == 'processed' for item in results),
            'skipped': sum(item['status'] == 'skipped' for item in results),
            'failed': sum(item['status'] == 'failed' for item in results),
            'deferred': sum(item['status'] == 'deferred' for item in results), 'results': results}


def process(root, notes_root, model, **options):
    try:
        return _process(root, notes_root, model, **options)
    except TriageBusyError:
        return {'mode': 'apply', 'status': 'busy', 'processed': 0, 'skipped': 0,
                'failed': 0, 'deferred': 0, 'results': []}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root')
    parser.add_argument('--notes-root', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--backend', choices=['auto', *sorted(LOCAL)], default='auto')
    parser.add_argument('--port', type=int, default=11434)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--timeout', type=float, default=1800)
    parser.add_argument('--min-age', type=float, default=60)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--recover', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--source', help=argparse.SUPPRESS)
    parser.add_argument('--result', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        if args.root is None:
            sys.path.insert(0, str(REPO / 'skill/scripts'))
            from video import load_workspace
            args.root = load_workspace().get('inbox_dir') or str(Path.home() / 'Documents/Voidscape/Inbox')
        if args.worker:
            if sys.stdin.readline() != 'GO\n':
                return 6
            if args.recover:
                recover(checked(args.root), checked(args.notes_root))
                result = {'status': 'recovered'}
            else:
                result = process_one(Path(args.root), Path(args.notes_root), Path(args.source),
                                     args.model, args.backend, args.port, min_age=args.min_age)
            exclusive(checked(args.result), encoded(result))
        else:
            result = process(args.root, args.notes_root, args.model, backend=args.backend,
                             port=args.port, limit=args.limit, timeout=args.timeout,
                             min_age=args.min_age, apply=args.apply)
        print(json.dumps({'ok': True, 'data': result, 'error': None}))
        return 0 if not result.get('failed') else 6
    except (OSError, ValueError, KeyError, TypeError, ProcessDeadlineError):
        print(json.dumps({'ok': False, 'data': None, 'error': 'Inbox processing failed; preserve local evidence.'}))
        return 6


if __name__ == '__main__':
    raise SystemExit(main())
