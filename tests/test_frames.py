import shutil
from pathlib import Path

import video
from conftest import requires_ffmpeg


@requires_ffmpeg
def test_static_clip_collapses(static_clip, tmp_path):
    entries, deduped = video._extract_frames(str(static_clip), tmp_path, 10, 0.0, 8.0, 128)
    assert deduped > 0
    assert len(entries) < 10                      # near-identical frames were dropped
    assert all(Path(e["file"]).exists() for e in entries)


@requires_ffmpeg
def test_scene_clip_keeps_distinct(scene_clip, tmp_path):
    entries, deduped = video._extract_frames(str(scene_clip), tmp_path, 6, 0.0, 6.0, 128)
    assert len(entries) >= 3                      # at least one frame per distinct scene


@requires_ffmpeg
def test_no_dedup_keeps_budget_count(static_clip, tmp_path):
    entries, deduped = video._extract_frames(str(static_clip), tmp_path, 10, 0.0, 8.0, 128,
                                             dedup=False)
    assert deduped == 0
    assert len(entries) == 10                     # oversampled then even-sampled back to budget


@requires_ffmpeg
def test_entries_are_contiguous_and_chronological(static_clip, tmp_path):
    entries, _ = video._extract_frames(str(static_clip), tmp_path, 10, 0.0, 8.0, 128)
    names = [Path(e["file"]).name for e in entries]
    assert names == [f"frame_{i:04d}.jpg" for i in range(1, len(entries) + 1)]
    times = [e["t"] for e in entries]
    assert times == sorted(times)


def test_cap_jobs_even_samples_and_keeps_pins(tmp_path):
    jobs = []
    for i in range(10):
        fp = tmp_path / f"frame_{i + 1:04d}.jpg"
        fp.write_bytes(b"j")
        jobs.append((float(i), fp, i == 7))       # pin t=7.0
    kept = video._cap_jobs(jobs, 4)
    assert len(kept) == 4
    assert any(j[2] for j in kept)                # pin survived
    assert sum(1 for j in jobs if j[1].exists()) == 4  # culled files deleted


def test_audio_tier_includes_frames_deduped_key(static_clip, tmp_path, monkeypatch):
    """Verify that run() output always includes frames_deduped key, even on audio-only tier."""
    # Monkeypatch _transcribe to return a stub result without network access
    def mock_transcribe(inp, info, media, wd, backend, transcribe_mode="auto",
                        allow_model_download=False):
        # Create a dummy transcript file
        tpath = wd / "transcript.txt"
        tpath.write_text("dummy transcript", encoding="utf-8")
        return str(tpath), "dummy transcript"

    monkeypatch.setattr(video, "_transcribe", mock_transcribe)

    result = video.run(str(static_clip), tier="audio", workdir=str(tmp_path))

    # Assert frames_deduped is present and set to 0 (no frame extraction on audio tier)
    assert "frames_deduped" in result
    assert result["frames_deduped"] == 0
    assert result["frames"] == []


@requires_ffmpeg
def test_run_resolves_workspace_bare_filename_for_frames(static_clip, tmp_path, monkeypatch):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    media = inbox / "bare.mp4"
    shutil.copyfile(static_clip, media)

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(video, "load_workspace", lambda: {"inbox_dir": str(inbox)})

    result = video.run("bare.mp4", tier="visual", frames=2, workdir=str(tmp_path / "work"),
                       dedup=False)

    assert result["frames"]
    assert all(Path(frame["file"]).exists() for frame in result["frames"])


@requires_ffmpeg
def test_extract_frames_fail_open_on_raised_exception(static_clip, tmp_path, monkeypatch, capsys):
    """Dedup block exception (e.g. OSError from subprocess) is caught and logged, not propagated."""
    # Force _thumb_frames to raise an exception (simulating OS-level ffmpeg failure)
    def mock_thumb_frames(paths):
        raise OSError("simulated subprocess/resource failure")

    monkeypatch.setattr(video, "_thumb_frames", mock_thumb_frames)

    # Extract frames with dedup enabled (default)
    entries, deduped = video._extract_frames(str(static_clip), tmp_path, 10, 0.0, 8.0, 128, dedup=True)

    # Should succeed (not propagate the exception)
    assert len(entries) > 0
    assert deduped == 0  # no dedup occurred
    assert all(Path(e["file"]).exists() for e in entries)

    # Should print the fail-open warning
    captured = capsys.readouterr()
    assert "WARNING: thumbnail pass failed — dedup skipped" in captured.err
