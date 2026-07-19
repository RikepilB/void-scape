import subprocess
import sys
from pathlib import Path

import video
from conftest import requires_ffmpeg


REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "create-demo-fixture.py"


@requires_ffmpeg
def test_demo_fixture_is_local_and_sidecar_grounded(tmp_path):
    output = tmp_path / "build-week-demo.mp4"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        capture_output=True, text=True, timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert output.exists()
    assert output.with_suffix(".srt").exists()
    info = video.probe(str(output))
    assert 11.5 <= info["duration_s"] <= 12.5
    assert info["sidecar_transcript"] == str(output.with_suffix(".srt"))
    estimate = video.estimate(str(output), backend="captions")
    assert estimate["requires_cloud_approval"] is False
    assert estimate["needs_model_download"] is False
