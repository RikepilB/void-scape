"""Result recovery exposes output paths, not a second content archive."""
import hashlib
import json
from pathlib import Path

import pytest

import article
import video


def test_article_success_records_confined_recovery_paths(tmp_path):
    source = tmp_path / "source.md"
    source.write_text("# Private title\n\nPrivate message body.\n", encoding="utf-8")
    root = tmp_path / "evidence"
    result = article.run(str(source), str(root))
    pointer = json.loads((root / ".agent/latest-read.json").read_text(encoding="utf-8"))
    assert pointer["status"] == "success"
    assert pointer["manifest"] == "manifest.json"
    assert pointer["manifest_sha256"] == hashlib.sha256((root / "manifest.json").read_bytes()).hexdigest()
    assert pointer["evidence"] == [
        Path(item["file"]).relative_to(root).as_posix() for item in result["entries"]
    ]
    assert "Private message body" not in json.dumps(pointer)
    assert "source.md" not in json.dumps(pointer)


def test_pointer_requires_success_manifest(tmp_path):
    with pytest.raises(FileNotFoundError):
        video.write_read_pointer({"workdir": str(tmp_path)})
    assert not (tmp_path / ".agent").exists()


def test_video_pointer_uses_frame_files_and_transcript(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    video.write_read_pointer({
        "workdir": str(tmp_path),
        "frames": [{"file": str(tmp_path / "frames/001.jpg"), "t": "00:01"}],
        "transcript": str(tmp_path / "transcript.txt"),
    })
    pointer = json.loads((tmp_path / ".agent/latest-read.json").read_text(encoding="utf-8"))
    assert pointer["evidence"] == ["frames/001.jpg", "transcript.txt"]


def test_pointer_rejects_external_evidence_path(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        video.write_read_pointer({"workdir": str(tmp_path), "transcript": str(tmp_path.parent / "outside.txt")})
    assert not (tmp_path / ".agent").exists()


def test_pointer_does_not_replace_existing_recovery_record(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / ".agent").mkdir()
    pointer = tmp_path / ".agent/latest-read.json"
    pointer.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        video.write_read_pointer({"workdir": str(tmp_path)})
    assert pointer.read_text(encoding="utf-8") == "existing"
