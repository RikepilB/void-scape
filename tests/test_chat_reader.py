"""Chat export reader: parsing, citations, gates, and guided dispatch."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import chat
import voidscape


REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "skill" / "scripts"

EXPORT_SAMPLE = """[05/12/24, 10:15:33] Messages and calls are end-to-end encrypted. No one outside of this chat, not even WhatsApp, can read or listen to them.
[05/12/24, 10:15:41] Ana: hola! recuerda la reunion del viernes
[05/12/24, 10:16:02] Luis: si, 10am con el equipo de datos
[05/12/24, 10:16:30] Ana: <attached: 00000042-PHOTO-2024-05-12-10-16-30.jpg>
[05/12/24, 10:17:00] Luis: perfecto
la agenda llego anoche
[05/12/24, 10:18:00] Luis created group "Proyecto"
"""


@pytest.fixture
def chat_export(tmp_path):
    folder = tmp_path / "Family"
    folder.mkdir()
    path = folder / "_chat.txt"
    path.write_text(EXPORT_SAMPLE, encoding="utf-8")
    (folder / "00000042-PHOTO-2024-05-12-10-16-30.jpg").write_bytes(b"fake-image")
    return path


def test_detection_requires_timestamped_chat_shape(tmp_path, chat_export):
    assert chat.is_chat_input(str(chat_export))
    plain = tmp_path / "note.txt"
    plain.write_text("# Title\n\nJust an article body.\n", encoding="utf-8")
    assert not chat.is_chat_input(str(plain))
    assert not chat.is_chat_input("https://example.com/chat.txt")


def test_probe_parses_senders_media_and_system_lines(chat_export):
    info = chat.probe(str(chat_export))
    assert info["kind"] == "chat"
    assert info["chat_title"] == "Family"
    assert info["item_count"] == 6
    assert info["participants"] == ["Ana", "Luis"]
    assert info["kind_counts"] == {"text": 3, "media": 1, "system": 2}
    assert info["entries"][1]["citation"] == "[message 2]"
    assert info["entries"][1]["sender"] == "Ana"
    media = info["entries"][3]
    assert media["kind"] == "media"
    assert media["media"] == "00000042-PHOTO-2024-05-12-10-16-30.jpg"
    assert info["requires_cloud_approval"] is False
    assert info["needs_model_download"] is False


def test_continuation_lines_join_previous_message(chat_export):
    parsed = chat._parse_export(chat_export)
    continued = parsed["entries"][4]
    assert continued["sender"] == "Luis"
    assert "perfecto" in continued["text"] and "la agenda llego anoche" in continued["text"]


def test_estimate_is_free_local_and_priced_in_tokens(chat_export):
    estimate = chat.estimate(str(chat_export))
    assert estimate["free"] is True
    assert estimate["requires_cloud_approval"] is False
    assert estimate["needs_model_download"] is False
    assert estimate["cost_usd"]["transcription"] == 0.0
    assert estimate["tokens"]["read_total"] > 0


def test_run_writes_transcript_manifest_and_media_reference(chat_export, tmp_path):
    workdir = tmp_path / "evidence"
    result = chat.run(str(chat_export), str(workdir))
    transcript = Path(result["transcript"])
    assert transcript.is_file()
    body = transcript.read_text(encoding="utf-8")
    assert "[message 2] Ana · 05/12/24, 10:15:41" in body
    assert "hola! recuerda la reunion del viernes" in body
    manifest = json.loads((workdir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["item_count"] == 6
    media_entry = manifest["entries"][3]
    assert media_entry["media_file"] is not None
    assert media_entry["media_file"].endswith(".jpg")
    assert manifest["content_trust"]["source_content"] == "untrusted"
    assert manifest["citation_guide"].startswith("cite each excerpt with message N")


def test_run_refuses_non_empty_workdir(chat_export, tmp_path):
    workdir = tmp_path / "busy"
    workdir.mkdir()
    (workdir / "stale.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not empty"):
        chat.run(str(chat_export), str(workdir))


def test_oversized_export_is_rejected_with_narrower_window_guidance(tmp_path):
    folder = tmp_path / "Big"
    folder.mkdir()
    lines = [f"[05/12/24, 10:15:{i % 60:02d}] Ana: mensaje numero {i}" for i in range(chat.MAX_MESSAGES + 5)]
    (folder / "_chat.txt").write_text("\n".join(lines), encoding="utf-8")
    with pytest.raises(ValueError, match="narrower window"):
        chat.run(str(folder / "_chat.txt"))


def test_unrecognized_txt_reports_input_error(tmp_path):
    plain = tmp_path / "plain.txt"
    plain.write_text("no timestamps here\njust prose\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "chat.py"), "probe", str(plain), "--envelope", "--compact"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 3
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


def test_manifest_matches_standard_protocol(capsys):
    assert chat.main(["manifest", "--compact"]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["protocol_version"] == "1.0"
    assert set(manifest["commands"]) == {"manifest", "probe", "estimate", "run"}
    assert manifest["exit_codes"]["4"] == "approval_required"


def test_guided_flow_dispatches_chat_reader(chat_export, tmp_path, capsys):
    assert voidscape.main(["inspect", str(chat_export)]) == 0
    out = capsys.readouterr().out
    assert "Chat: Family" in out
    assert "Messages: 6" in out
    assert voidscape._select_reader(str(chat_export)) == "chat"
    workdir = tmp_path / "guided-evidence"
    assert voidscape.main([
        "read", str(chat_export), "--workdir", str(workdir),
    ]) == 0
    out = capsys.readouterr().out
    assert "messages.txt" in out
    assert "[message 1]" in out
    assert (workdir / "manifest.json").is_file()


def test_reader_override_forces_chat_on_txt(chat_export):
    assert voidscape._select_reader(str(chat_export), "chat") == "chat"
