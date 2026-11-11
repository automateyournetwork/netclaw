import json
import subprocess
import sys

from conftest import ROOT, make_skills, write_policy

CHECK = ROOT / "scripts" / "check-skill-limits.py"


def run(*args):
    return subprocess.run([sys.executable, str(CHECK), *map(str, args)], capture_output=True, text=True)


def test_repo_passes():
    result = run()
    assert result.returncode == 0, result.stdout
    assert "covered" in result.stdout


def test_exceeding_load_limit_fails_and_names_limit(tmp_path):
    make_skills(tmp_path / "s", 401)
    result = run("--skills-dir", tmp_path / "s")
    assert result.returncode == 1
    assert "FAIL maxSkillsLoadedPerSource 400 < 401" in result.stdout and "over by 1" in result.stdout


def test_warn_only_and_json(tmp_path):
    make_skills(tmp_path / "s", 401)
    assert run("--skills-dir", tmp_path / "s", "--warn-only").returncode == 0
    data = json.loads(run("--skills-dir", tmp_path / "s", "--json", "--warn-only").stdout)
    assert data["skills"] == 401 and any(f["level"] == "fail" for f in data["findings"])


def test_warn_note_does_not_fail(tmp_path):
    make_skills(tmp_path / "s", 330)
    result = run("--skills-dir", tmp_path / "s")
    assert result.returncode == 0 and "note maxSkillsLoadedPerSource" in result.stdout


def test_invalid_policy_exits_2(tmp_path):
    make_skills(tmp_path / "s", 1)
    bad = write_policy(tmp_path / "p.json", maxSkillsInPrompt=1)
    assert run("--skills-dir", tmp_path / "s", "--policy", bad).returncode == 2
    assert run("--skills-dir", tmp_path / "s", "--policy", tmp_path / "missing.json").returncode == 2


def test_reconcile_surface_runs_and_reports():
    result = subprocess.run([sys.executable, str(ROOT / "scripts/reconcile-mcp.py"), "--surface", "skill-limits"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "skill-limits" in result.stdout
