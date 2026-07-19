#!/usr/bin/env python3
"""Generate read-video's deterministic, copyright-free Build Week demo fixture."""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO / "samples" / "build-week-demo.mp4"
SIDECAR = """1
00:00:00,000 --> 00:00:04,000
The demo begins on a red scene with a low tone.

2
00:00:04,000 --> 00:00:08,000
At four seconds the scene changes to green and the tone rises.

3
00:00:08,000 --> 00:00:12,000
At eight seconds the scene changes to blue and the tone rises again.
"""


def create_fixture(output: Path) -> tuple[Path, Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to generate the demo fixture")
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    sidecar = output.with_suffix(".srt")
    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", "color=c=red:s=640x360:d=4:r=12",
        "-f", "lavfi", "-i", "sine=frequency=330:duration=4:sample_rate=16000",
        "-f", "lavfi", "-i", "color=c=lime:s=640x360:d=4:r=12",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=4:sample_rate=16000",
        "-f", "lavfi", "-i", "color=c=blue:s=640x360:d=4:r=12",
        "-f", "lavfi", "-i", "sine=frequency=550:duration=4:sample_rate=16000",
        "-filter_complex",
        "[0:v][1:a][2:v][3:a][4:v][5:a]concat=n=3:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]", "-c:v", "mpeg4", "-q:v", "5",
        "-c:a", "aac", "-pix_fmt", "yuv420p", "-fflags", "+bitexact",
        "-flags:v", "+bitexact", "-flags:a", "+bitexact",
        "-metadata", "creation_time=1970-01-01T00:00:00Z", str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    sidecar.write_text(SIDECAR, encoding="utf-8", newline="\n")
    return output, sidecar


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        video, transcript = create_fixture(args.output)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(f"video={video}")
    print(f"sidecar={transcript}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
