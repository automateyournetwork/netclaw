"""Spec 177: the sidecar unit starts DefenseClaw so its CLI can reach the gateway."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
HELPER = REPO / "scripts/systemd/defenseclaw-sidecar-start.py"


def services(monkeypatch, gateway):
    spec = importlib.util.spec_from_file_location("in2n_services_177", REPO / "scripts/in2n-services.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    which = mod.shutil.which
    monkeypatch.setattr(mod.shutil, "which", lambda name: gateway if name == "defenseclaw-gateway" else which(name))
    return mod


def test_unit_starts_the_gateway_through_defenseclaw_and_tracks_its_pid(monkeypatch):
    gateway = "/opt/defense claw/bin/defenseclaw-gateway"
    text = services(monkeypatch, gateway)._defenseclaw_unit_text()
    lines = dict(line.split("=", 1) for line in text.splitlines() if "=" in line and not line.startswith("#"))
    assert lines["Type"] == "forking"
    assert lines["PIDFile"] == "%t/defenseclaw-sidecar/gateway.pid"
    assert lines["RuntimeDirectory"] == "defenseclaw-sidecar"
    assert lines["ExecStart"] == f'"{sys.executable}" "{HELPER}" "{gateway}"'
    assert lines["ExecStartPre"] == f'-"{gateway}" stop'
    assert lines["ExecStop"] == f'"{gateway}" stop'
    assert lines["Restart"] == "always"
    assert "@" not in text.replace("%t", "")


def fake_gateway(tmp_path, record, code=0):
    script = tmp_path / "defenseclaw-gateway"
    script.write_text(
        "#!/bin/sh\n"
        f'[ "$1" = start ] || exit 9\n'
        f"printf '%s' '{json.dumps(record)}' > \"$DEFENSECLAW_HOME/gateway.pid\"\n"
        f"exit {code}\n")
    script.chmod(0o755)
    return script


def run_helper(tmp_path, gateway, runtime=True):
    env = {**os.environ, "DEFENSECLAW_HOME": str(tmp_path / "home")}
    (tmp_path / "home").mkdir(exist_ok=True)
    env.pop("RUNTIME_DIRECTORY", None)
    if runtime:
        (tmp_path / "run").mkdir(exist_ok=True)
        env["RUNTIME_DIRECTORY"] = str(tmp_path / "run")
    return subprocess.run([sys.executable, str(HELPER), str(gateway)], env=env, capture_output=True, text=True)


def test_helper_copies_only_the_pid_for_systemd(tmp_path):
    record = {"pid": 4321, "executable": "/x/defenseclaw-gateway", "start_identity": "99"}
    result = run_helper(tmp_path, fake_gateway(tmp_path, record))
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "run/gateway.pid").read_text() == "4321\n"
    # DefenseClaw's own record is left exactly as the gateway wrote it.
    assert json.loads((tmp_path / "home/gateway.pid").read_text()) == record


def test_helper_fails_when_start_fails_or_the_record_is_unusable(tmp_path):
    assert run_helper(tmp_path, fake_gateway(tmp_path, {"pid": 4321}, code=3)).returncode == 3
    assert run_helper(tmp_path, fake_gateway(tmp_path, {"pid": "4321"})).returncode == 1
    assert run_helper(tmp_path, fake_gateway(tmp_path, {"executable": "x"})).returncode == 1
    assert run_helper(tmp_path, fake_gateway(tmp_path, {"pid": 4321}), runtime=False).returncode == 1
    assert not (tmp_path / "run/gateway.pid").exists()
