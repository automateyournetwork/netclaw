"""Spec 165 T002: opt-in Border hardening helper (scripts/border-harden.py).

Fake `openclaw` and `docker` executables on PATH record argv; no real OpenClaw
config, Docker daemon or service manager is touched. Real OpenClaw behaviour is
not exercised here (see specs/165-convergence-confinement/verification.md).
"""

import json
import os
import subprocess
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SCRIPT = os.path.join(REPO, "scripts", "border-harden.py")

FAKE_OPENCLAW = r'''
import json, os, sys
argv = sys.argv[1:]
state = json.load(open(os.environ["FAKE_OC_STATE"]))
record = {"argv": argv}
if "--batch-file" in argv:
    path = argv[argv.index("--batch-file") + 1]
    record["batch"] = json.load(open(path))
    record["batch_mode"] = oct(os.stat(path).st_mode & 0o777)
    record["dir_mode"] = oct(os.stat(os.path.dirname(path)).st_mode & 0o777)
with open(os.environ["FAKE_OC_LOG"], "a") as log:
    log.write(json.dumps(record) + "\n")
if argv[:2] == ["config", "get"]:
    path = argv[2]
    node = state
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            msg = ("Unknown config path: %s." % path if path in state.get("_unknown", [])
                   else "Config path is valid but unset: %s. The runtime default applies." % path)
            print(json.dumps({"ok": False, "error": {"type": "cli_error", "message": msg}}))
            sys.exit(1)
    print(json.dumps(node))
    sys.exit(0)
if argv[:2] == ["config", "set"]:
    if "--dry-run" in argv:
        print("Dry run successful: %d update(s) validated." % len(record["batch"]))
        sys.exit(int(os.environ.get("FAKE_OC_DRYRUN_RC", "0")))
    print("Updated %d config paths." % len(record["batch"]))
    sys.exit(0)
if argv[:2] == ["config", "validate"]:
    print("Config valid")
    sys.exit(int(os.environ.get("FAKE_OC_VALIDATE_RC", "0")))
sys.exit(3)
'''

FAKE_DOCKER = r'''
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["FAKE_DOCKER_LOG"], "a") as log:
    log.write(json.dumps(argv) + "\n")
mode = os.environ.get("FAKE_DOCKER_MODE", "ok")
if argv[:1] == ["info"]:
    if mode == "denied":
        sys.stderr.write("permission denied while trying to connect to the Docker daemon "
                         "socket at unix:///var/run/docker.sock\n")
        sys.exit(1)
    print("Server Version: 27.0.0")
    sys.exit(0)
if argv[:2] == ["image", "inspect"]:
    images = [i for i in os.environ.get("FAKE_DOCKER_IMAGES", "").split(",") if i]
    sys.exit(0 if argv[2] in images else 1)
if argv[:1] in (["build"], ["pull"], ["run"]):
    sys.exit(99)
sys.exit(2)
'''


class Harness:
    def __init__(self, tmp_path, config, docker_mode="ok",
                 images=("openclaw-sandbox:bookworm-slim",)):
        self.bin = tmp_path / "bin"
        self.bin.mkdir()
        for name, body in (("openclaw", FAKE_OPENCLAW), ("docker", FAKE_DOCKER)):
            exe = self.bin / name
            exe.write_text(f"#!{sys.executable}\n{body}")
            exe.chmod(0o755)
        self.state = tmp_path / "oc-state.json"
        self.state.write_text(json.dumps(config))
        self.oc_log = tmp_path / "oc.log"
        self.docker_log = tmp_path / "docker.log"
        self.env = {
            "PATH": f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin",
            "HOME": str(tmp_path / "home"),
            "TMPDIR": str(tmp_path),
            "FAKE_OC_STATE": str(self.state),
            "FAKE_OC_LOG": str(self.oc_log),
            "FAKE_DOCKER_LOG": str(self.docker_log),
            "FAKE_DOCKER_MODE": docker_mode,
            "FAKE_DOCKER_IMAGES": ",".join(images),
        }

    def run(self, *args, **extra_env):
        env = dict(self.env, **extra_env)
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True,
                              text=True, env=env, timeout=60, check=False)

    def oc_calls(self):
        if not self.oc_log.exists():
            return []
        return [json.loads(line) for line in self.oc_log.read_text().splitlines()]

    def set_calls(self):
        return [c for c in self.oc_calls() if c["argv"][:2] == ["config", "set"]]

    def docker_calls(self):
        if not self.docker_log.exists():
            return []
        return [json.loads(line) for line in self.docker_log.read_text().splitlines()]


def _batch(call):
    return {entry["path"]: entry["value"] for entry in call["batch"]}


EXISTING = {
    "agents": {"defaults": {"sandbox": {"docker": {"image": "custom/sandbox:1",
                                                   "network": "bridge"}}}},
    "tools": {"elevated": {"allowFrom": {"webchat": ["owner"]}},
              "sandbox": {"tools": {"alsoAllow": ["outlook__*", "bundle-mcp", "computer"]}}},
}


def test_dry_run_never_applies(tmp_path):
    h = Harness(tmp_path, {})
    proc = h.run()
    assert proc.returncode == 0, proc.stderr
    sets = h.set_calls()
    assert len(sets) == 1 and "--dry-run" in sets[0]["argv"]
    assert not any(c["argv"][:2] == ["config", "validate"] for c in h.oc_calls())
    assert "nothing was written" in proc.stdout
    # Private batch file: 0600 inside a 0700 directory, removed afterwards.
    assert sets[0]["batch_mode"] == "0o600" and sets[0]["dir_mode"] == "0o700"
    assert not any(p.name.startswith("netclaw-border-harden-") for p in tmp_path.iterdir())


def test_apply_runs_dry_run_then_set_then_validate(tmp_path):
    h = Harness(tmp_path, {})
    proc = h.run("--apply")
    assert proc.returncode == 0, proc.stderr
    writes = [c["argv"] for c in h.oc_calls() if c["argv"][:2] != ["config", "get"]]
    assert writes[0][:3] == ["config", "set", "--batch-file"] and "--dry-run" in writes[0]
    assert writes[1][:3] == ["config", "set", "--batch-file"] and "--dry-run" not in writes[1]
    assert writes[2] == ["config", "validate"]
    assert len(writes) == 3
    batch = _batch(h.set_calls()[1])
    assert batch == {
        "agents.defaults.sandbox.mode": "all",
        "agents.defaults.sandbox.backend": "docker",
        "agents.defaults.sandbox.scope": "session",
        "agents.defaults.sandbox.workspaceAccess": "none",
        "agents.defaults.sandbox.docker.network": "none",
        "tools.elevated.enabled": False,
        "tools.sandbox.tools.alsoAllow": ["bundle-mcp"],
        "skills.workshop.autonomous.mode": "off",
    }
    assert "openclaw sandbox explain --agent main" in proc.stdout
    assert "host scripts" in proc.stdout and "WARNING" in proc.stdout
    # Never builds, pulls or runs containers itself.
    assert all(c[0] in ("info", "image") for c in h.docker_calls())


def test_merge_preserves_existing_entries_and_docker_image(tmp_path):
    h = Harness(tmp_path, EXISTING, images=("custom/sandbox:1",))
    proc = h.run("--apply")
    assert proc.returncode == 0, proc.stderr
    batch = _batch(h.set_calls()[-1])
    assert batch["tools.sandbox.tools.alsoAllow"] == ["outlook__*", "bundle-mcp", "computer"]
    assert batch["agents.defaults.sandbox.docker.network"] == "none"
    # Leaf assignments only: image, docker siblings and elevated.allowFrom are not rewritten.
    assert not any(path in batch for path in ("agents.defaults.sandbox", "agents.defaults.sandbox.docker",
                                               "agents.defaults.sandbox.docker.image", "tools.elevated",
                                               "tools.elevated.allowFrom"))
    assert ["image", "inspect", "custom/sandbox:1"] in h.docker_calls()
    assert '"bridge" -> "none"' in proc.stdout


def test_existing_allow_list_receives_bundle_mcp_instead_of_alsoallow(tmp_path):
    config = {"tools": {"sandbox": {"tools": {"allow": ["exec", "read"]}}}}
    h = Harness(tmp_path, config)
    proc = h.run()
    assert proc.returncode == 0, proc.stderr
    batch = _batch(h.set_calls()[0])
    assert batch["tools.sandbox.tools.allow"] == ["exec", "read", "bundle-mcp"]
    assert "tools.sandbox.tools.alsoAllow" not in batch


def test_missing_image_refuses_apply_with_build_instruction(tmp_path):
    h = Harness(tmp_path, {}, images=())
    proc = h.run("--apply")
    assert proc.returncode == 2
    assert "docker build -t openclaw-sandbox:bookworm-slim" in proc.stderr
    assert "refusing --apply" in proc.stderr
    sets = h.set_calls()
    assert all("--dry-run" in c["argv"] for c in sets)
    assert not any(c["argv"][:2] == ["config", "validate"] for c in h.oc_calls())


def test_missing_image_dry_run_reports_and_exits_nonzero(tmp_path):
    h = Harness(tmp_path, {}, images=())
    proc = h.run()
    assert proc.returncode == 2
    assert "--apply would be refused" in proc.stdout
    assert all("--dry-run" in c["argv"] for c in h.set_calls())


def test_skip_image_check_allows_apply(tmp_path):
    h = Harness(tmp_path, {}, images=())
    proc = h.run("--apply", "--skip-image-check")
    assert proc.returncode == 0, proc.stderr
    assert not any(c[:2] == ["image", "inspect"] for c in h.docker_calls())
    assert any(c["argv"] == ["config", "validate"] for c in h.oc_calls())


def test_docker_permission_denied_explains_group_and_user_manager(tmp_path):
    h = Harness(tmp_path, {}, docker_mode="denied")
    proc = h.run("--apply")
    assert proc.returncode == 2
    assert "permission denied" in proc.stderr
    assert "docker group" in proc.stderr
    assert "sudo systemctl restart user@$(id -u)" in proc.stderr
    assert "never runs sudo" in proc.stderr
    assert all("--dry-run" in c["argv"] for c in h.set_calls())


def test_workshop_mode_off_is_planned(tmp_path):
    h = Harness(tmp_path, {"skills": {"workshop": {"autonomous": {"mode": "auto"}}}})
    proc = h.run()
    assert proc.returncode == 0, proc.stderr
    assert _batch(h.set_calls()[0])["skills.workshop.autonomous.mode"] == "off"
    assert 'skills.workshop.autonomous.mode: "auto" -> "off"' in proc.stdout


def test_openclaw_dry_run_rejection_stops_before_write(tmp_path):
    h = Harness(tmp_path, {})
    proc = h.run("--apply", FAKE_OC_DRYRUN_RC="1")
    assert proc.returncode == 1
    assert len(h.set_calls()) == 1 and "--dry-run" in h.set_calls()[0]["argv"]
    assert "nothing was written" in proc.stderr


def test_validate_failure_is_nonzero(tmp_path):
    h = Harness(tmp_path, {})
    proc = h.run("--apply", FAKE_OC_VALIDATE_RC="1")
    assert proc.returncode == 1
    assert "does not validate" in proc.stderr


def test_unknown_config_path_is_preflight_failure(tmp_path):
    h = Harness(tmp_path, {"_unknown": ["skills.workshop.autonomous.mode"]})
    proc = h.run()
    assert proc.returncode == 2
    assert "upgrade OpenClaw" in proc.stderr
    assert h.set_calls() == []


def test_missing_openclaw_is_preflight_failure(tmp_path):
    h = Harness(tmp_path, {})
    (h.bin / "openclaw").unlink()
    proc = h.run()
    assert proc.returncode == 2
    assert "openclaw" in proc.stderr


@pytest.mark.parametrize("secret", ["sk-test-SECRET-value"])
def test_unrelated_secret_values_are_never_printed(tmp_path, secret):
    config = {"agents": {"defaults": {"sandbox": {"docker": {"env": {"API_KEY": secret}}}}},
              "models": {"providers": {"anthropic": {"apiKey": secret}}}}
    h = Harness(tmp_path, config)
    proc = h.run("--apply")
    assert proc.returncode == 0, proc.stderr
    assert secret not in proc.stdout + proc.stderr
    for call in h.set_calls():
        assert secret not in json.dumps(call["batch"])
    read_paths = {c["argv"][2] for c in h.oc_calls() if c["argv"][:2] == ["config", "get"]}
    assert not any(p.startswith("models") for p in read_paths)
