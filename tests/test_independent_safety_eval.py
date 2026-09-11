"""Regression checks for the bounded independent-safety evaluation record."""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
EVAL = REPO / "evals" / "independent-safety"


def _load_grader():
    spec = importlib.util.spec_from_file_location("independent_safety_grader", EVAL / "grader.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_valid_codex_actor_records_satisfy_every_safety_assertion():
    grader = _load_grader()
    for name in ("codex-with-skill.json", "codex-baseline.json"):
        result = grader.grade(EVAL / "raw" / name)
        assert result["passed"]
        assert result["passed_assertions"] == result["total_assertions"] == 30


def test_results_preserve_the_cross_harness_limit_and_invalid_attempt():
    results = (EVAL / "RESULTS.md").read_text(encoding="utf-8")
    assert "partial acceptance evidence" in results
    assert "not a cross-harness benchmark" in results
    assert (EVAL / "raw" / "codex-with-skill-attempt1-invalid.json").is_file()
    assert (EVAL / "raw" / "claude-with-skill-unavailable.txt").is_file()
