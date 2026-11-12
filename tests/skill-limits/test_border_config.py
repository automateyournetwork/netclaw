import importlib.util
import json
import re
from pathlib import Path

import skill_limits as sl
from conftest import ROOT

spec = importlib.util.spec_from_file_location("imc188", ROOT / "scripts/install-mcp-config.py")
imc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imc)

TEMPLATE = {"demo": {"command": "python3", "args": ["x.py"]}}
GENERATED = {"demo": {"command": "python3", "args": ["x.py"], "cwd": "."}}


def merge(path):
    imc.merge_config(path, GENERATED, TEMPLATE)
    return json.loads(path.read_text())


def test_fresh_config_gets_limits(tmp_path):
    config = merge(tmp_path / "openclaw.json")
    assert config["skills"]["limits"] == sl.policy_limits()
    assert "demo" in config["mcp"]["servers"]


def test_operator_values_preserved_and_unrelated_keys_untouched(tmp_path):
    path = tmp_path / "openclaw.json"
    path.write_text(json.dumps({"gateway": {"mode": "local"}, "mcpServers": {},
                                "skills": {"entries": {"a": {"enabled": False}},
                                           "limits": {"maxSkillsLoadedPerSource": 1000, "maxSkillsInPrompt": 10}}}))
    config = merge(path)
    limits = config["skills"]["limits"]
    assert limits["maxSkillsLoadedPerSource"] == 1000
    assert limits["maxSkillsInPrompt"] == sl.policy_limits()["maxSkillsInPrompt"]
    assert config["skills"]["entries"] == {"a": {"enabled": False}}
    assert config["gateway"] == {"mode": "local"} and "demo" in config["mcpServers"]


def test_second_run_is_a_noop_without_new_backup(tmp_path):
    path = tmp_path / "openclaw.json"
    merge(path)
    first = path.read_text()
    backups = list(tmp_path.glob("*.before-netclaw-*"))
    merge(path)
    assert path.read_text() == first
    assert list(tmp_path.glob("*.before-netclaw-*")) == backups


def test_hermes_branch_never_passes_config_to_merge():
    steps = (ROOT / "scripts/lib/install-steps.sh").read_text()
    block = steps[steps.index('if [ "$RUNTIME" = "hermes" ]; then\n    # Port NetClaw'):]
    hermes, rest = block.split("\nelse\n", 1)
    assert "install-mcp-config.py" not in hermes and "--config \"$RUNTIME_CONFIG\"" not in hermes.replace("--config \"$RUNTIME_CONFIG\" \\\n                --sidecar", "")
    assert re.search(r'install-mcp-config\.py.*?--config "\$RUNTIME_CONFIG"', rest, re.S)
