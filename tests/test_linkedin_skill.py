import subprocess
import sys

from sync_linkedin_skill import ROOT, rendered_files


def test_harness_files_are_current():
    for path, expected in rendered_files(ROOT).items():
        assert path.read_text(encoding='utf-8') == expected
    result = subprocess.run([sys.executable, str(ROOT / 'scripts/sync_linkedin_skill.py')],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_command_reference_points_to_real_subcommands():
    reference = (ROOT / '.agents/skills/linkedin-triage/references/commands.md').read_text(encoding='utf-8')
    for line in reference.splitlines():
        if not line.startswith('python scripts/'):
            continue
        _, script, command, *_ = line.split()
        result = subprocess.run([sys.executable, str(ROOT / script), command, '--help'],
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
