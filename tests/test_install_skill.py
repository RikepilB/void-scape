"""The installer copies the skills into a Codex-compatible root without private config."""
import subprocess
from pathlib import Path

from conftest import requires_powershell, powershell_exe

REPO = Path(__file__).resolve().parent.parent
INSTALL_SCRIPT = REPO / "scripts" / "install-skill.ps1"


def _run_install(codex_root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            powershell_exe(), "-NoProfile", "-NonInteractive", "-File", str(INSTALL_SCRIPT),
            "-CodexSkillsRoot", str(codex_root),
        ],
        capture_output=True, text=True, timeout=60,
    )


@requires_powershell
def test_install_copies_primary_and_compatibility_skills(tmp_path):
    root = tmp_path / "codex_skills"
    result = _run_install(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (root / "voidscape" / "SKILL.md").exists()
    assert (root / "voidscape" / "scripts" / "video.py").exists()
    assert (root / "read-video" / "scripts" / "video.py").exists()


@requires_powershell
def test_install_reports_verification(tmp_path):
    result = _run_install(tmp_path / "codex_skills")
    assert "RESULT codex voidscape copy OK" in result.stdout
    assert "RESULT codex read-video copy OK" in result.stdout
    assert "RESULT codex voidscape verify:frontmatter OK" in result.stdout
    assert "RESULT codex read-video verify:cli OK" in result.stdout


@requires_powershell
def test_install_creates_missing_parent(tmp_path):
    root = tmp_path / "missing" / "codex_skills"
    result = _run_install(root)
    assert result.returncode == 0
    assert (root / "read-video" / "SKILL.md").exists()


@requires_powershell
def test_install_preserves_existing_local_config(tmp_path):
    root = tmp_path / "codex_skills"
    dest = root / "voidscape"
    dest.mkdir(parents=True)
    (dest / "workspace.json").write_text('{"inbox_dir": "keep-me"}', encoding="utf-8")
    result = _run_install(root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (dest / "workspace.json").read_text(encoding="utf-8") == '{"inbox_dir": "keep-me"}'


@requires_powershell
def test_install_does_not_copy_source_workspace(tmp_path):
    source_workspace = REPO / "skill" / "workspace.json"
    source_workspace.write_text('{"inbox_dir": "private-source"}', encoding="utf-8")
    try:
        root = tmp_path / "codex_skills"
        result = _run_install(root)
        assert result.returncode == 0, result.stdout + result.stderr
        assert not (root / "voidscape" / "workspace.json").exists()
    finally:
        source_workspace.unlink(missing_ok=True)


@requires_powershell
def test_legacy_facade_forwards_to_engine(tmp_path):
    root = tmp_path / "codex_skills"
    result = _run_install(root)
    assert result.returncode == 0, result.stdout + result.stderr
    legacy_cli = root / "read-video" / "scripts" / "video.py"
    manifest = subprocess.run(
        ["python", str(legacy_cli), "manifest", "--compact"],
        capture_output=True, text=True, timeout=30,
    )
    assert manifest.returncode == 0, manifest.stdout + manifest.stderr
    assert '"manifest"' in manifest.stdout
    assert '"probe"' in manifest.stdout


@requires_powershell
def test_install_prints_summary(tmp_path):
    result = _run_install(tmp_path / "codex_skills")
    assert "SUMMARY install complete" in result.stdout
    assert result.returncode == 0
