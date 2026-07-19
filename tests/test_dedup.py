from pathlib import Path

import video

T = video._DEDUP_THUMB * video._DEDUP_THUMB  # 256 bytes per thumbnail


def thumb(val: int) -> bytes:
    return bytes([val]) * T


def jobs_for(tmp_path: Path, n: int):
    out = []
    for i in range(n):
        fp = tmp_path / f"frame_{i + 1:04d}.jpg"
        fp.write_bytes(b"jpeg")
        out.append((float(i), fp, False))
    return out


def test_frame_delta_identical_is_zero():
    assert video._frame_delta(thumb(100), thumb(100)) == 0.0


def test_frame_delta_known_value():
    assert video._frame_delta(thumb(100), thumb(103)) == 3.0


def test_frame_delta_mismatch_is_inf():
    assert video._frame_delta(thumb(1), thumb(1)[:-1]) == float("inf")
    assert video._frame_delta(b"", b"") == float("inf")


def test_dedupe_drops_near_duplicates_and_deletes_files(tmp_path):
    jobs = jobs_for(tmp_path, 4)
    thumbs = [thumb(10), thumb(11), thumb(10), thumb(200)]  # deltas: 1, 1, 190
    kept, dropped = video._dedupe_jobs(jobs, thumbs)
    assert dropped == 2
    assert [j[0] for j in kept] == [0.0, 3.0]
    assert not jobs[1][1].exists() and not jobs[2][1].exists()
    assert jobs[0][1].exists() and jobs[3][1].exists()


def test_dedupe_compares_against_last_kept(tmp_path):
    """Slow drift: each step under threshold vs neighbor but eventually far from last kept."""
    jobs = jobs_for(tmp_path, 4)
    thumbs = [thumb(10), thumb(11), thumb(12), thumb(13)]  # all within 2.0 of neighbor; 13 is 3 from 10
    kept, dropped = video._dedupe_jobs(jobs, thumbs)
    assert [j[0] for j in kept] == [0.0, 3.0]
    assert dropped == 2


def test_dedupe_never_drops_pinned(tmp_path):
    jobs = jobs_for(tmp_path, 3)
    jobs[1] = (jobs[1][0], jobs[1][1], True)               # pin the middle duplicate
    thumbs = [thumb(10), thumb(10), thumb(10)]
    kept, dropped = video._dedupe_jobs(jobs, thumbs)
    assert [j[0] for j in kept] == [0.0, 1.0]
    assert dropped == 1


def test_dedupe_fail_open_on_mismatch(tmp_path):
    jobs = jobs_for(tmp_path, 3)
    kept, dropped = video._dedupe_jobs(jobs, [thumb(1)])   # 1 thumb for 3 jobs
    assert kept == jobs and dropped == 0
