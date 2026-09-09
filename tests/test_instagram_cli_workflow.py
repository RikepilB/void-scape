"""Exercise the actual local CLI contract used by the source skill."""
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not shutil.which('ffmpeg'), reason='local fixture needs ffmpeg')
def test_guided_local_export_success_is_flat_and_retains_evidence(tmp_path):
    create = runpy.run_path(str(ROOT / 'scripts/create-demo-fixture.py'))['create_fixture']
    video, sidecar = create(tmp_path / 'input/demo.mp4')
    workdir = tmp_path / 'evidence'

    def invoke(command, *options):
        result = subprocess.run(
            [sys.executable, '-m', 'skill.scripts.voidscape', command, str(video),
             *options, '--json'], cwd=ROOT, capture_output=True, text=True,
            encoding='utf-8', timeout=60)
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert isinstance(payload, dict)
        assert 'error' not in payload and 'data' not in payload and 'ok' not in payload
        return payload

    inspection = invoke('inspect')
    assert inspection['source'] == 'local'
    assert Path(inspection['sidecar_transcript']) == sidecar
    preview = invoke('preview', '--tier', 'both', '--backend', 'captions')
    assert preview['free'] is True
    for gate in ('needs_install', 'needs_model_download', 'requires_cloud_approval'):
        assert preview[gate] is False
    assert not workdir.exists()
    result = invoke('read', '--tier', 'both', '--backend', 'captions', '--workdir', str(workdir))
    assert result['status'] == 'complete'
    assert Path(result['transcript']).is_file()
    assert result['frames'] and all(Path(frame['file']).is_file() for frame in result['frames'])
    assert (workdir / 'manifest.json').is_file()
    assert video.is_file() and sidecar.is_file()
