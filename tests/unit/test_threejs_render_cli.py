"""
Unit tests for the threejs-network-viz command-line entry point (render.py).
An agent runs it through exec, so the contract is: on success stdout is the
absolute path of the written HTML file and nothing else, exit code 0; on any
failure stdout is empty, stderr has the reason, exit code non-zero.
"""

import json
import subprocess
import sys
from pathlib import Path

skill_path = Path(__file__).parent.parent.parent / "workspace" / "skills" / "threejs-network-viz"
RENDER = skill_path / "render.py"

TWO_NODE = {
    "source": "cli-test",
    "devices": [
        {"hostname": "R1", "device_type": "router", "interfaces": [{"name": "Gi0/0"}]},
        {"hostname": "R2", "device_type": "router", "interfaces": [{"name": "Gi0/0"}]},
    ],
    "links": [
        {"source_device": "R1", "source_interface": "Gi0/0",
         "target_device": "R2", "target_interface": "Gi0/0"},
    ],
}


def run(*args, stdin=None, cwd=None):
    return subprocess.run([sys.executable, str(RENDER), *args], input=stdin,
                          capture_output=True, text=True, cwd=cwd, timeout=120)


def written_path(result) -> Path:
    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 1
    path = Path(lines[0])
    assert path.is_absolute() and path.is_file() and path.suffix == ".html"
    return path


def test_describe_writes_html_and_prints_only_the_path(tmp_path):
    r = run("--describe", "r1 is a router, sw1 is a switch, r1 connects to sw1",
            "--output-dir", str(tmp_path), cwd=tmp_path)
    path = written_path(r)
    assert path.parent == tmp_path.resolve()
    html = path.read_text(encoding="utf-8")
    assert "r1" in html and "sw1" in html


def test_json_file_two_node_topology(tmp_path):
    topo = tmp_path / "topo.json"
    topo.write_text(json.dumps(TWO_NODE), encoding="utf-8")
    path = written_path(run("--json", str(topo), "--output-dir", str(tmp_path)))
    html = path.read_text(encoding="utf-8")
    assert "R1" in html and "R2" in html and "Gi0/0" in html


def test_json_from_stdin_with_source(tmp_path):
    r = run("--json", "-", "--source", "gns3", "--output-dir", str(tmp_path),
            stdin=json.dumps(TWO_NODE))
    assert "gns3" in written_path(r).name


def test_runs_from_any_working_directory(tmp_path):
    other = tmp_path / "elsewhere"
    other.mkdir()
    written_path(run("--describe", "r1 connects to r2", "--output-dir", str(tmp_path), cwd=other))


def test_invalid_json_fails_cleanly(tmp_path):
    r = run("--json", "-", "--output-dir", str(tmp_path), stdin="{not json")
    assert r.returncode == 1 and r.stdout == ""
    assert "threejs-network-viz: error:" in r.stderr
    assert list(tmp_path.iterdir()) == []


def test_json_without_devices_list_fails(tmp_path):
    r = run("--json", "-", "--output-dir", str(tmp_path), stdin='{"links": []}')
    assert r.returncode == 1 and "devices" in r.stderr


def test_empty_description_fails(tmp_path):
    r = run("--describe", "   ", "--output-dir", str(tmp_path))
    assert r.returncode == 1 and r.stdout == ""


def test_missing_input_is_usage_error():
    r = run()
    assert r.returncode == 2 and r.stdout == ""
