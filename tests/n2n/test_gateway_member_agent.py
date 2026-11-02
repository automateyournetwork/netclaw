"""Embedded member turns name their agent when OpenClaw would otherwise refuse."""
import asyncio
import json
import shutil

import pytest

from bgp.federation import gateway, negotiate


def _run(tmp_path, monkeypatch, agents=None, env_agent=None):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for the CLI argv fixture")
    seen = tmp_path / "argv.json"
    cli = tmp_path / "agent-cli"
    cli.write_text(
        f"#!{node}\n"
        f"require('fs').writeFileSync({json.dumps(str(seen))}, JSON.stringify(process.argv.slice(2)));\n"
        "process.stdout.write(JSON.stringify({payloads:[{text:'OK'}],meta:{}}));\n"
    )
    cli.chmod(0o700)
    config = tmp_path / "openclaw.json"
    if agents is None:
        config.write_text("not json")
    else:
        config.write_text(json.dumps({"agents": agents}))
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(config))
    monkeypatch.setattr(gateway, "_openclaw_bin", lambda: str(cli))
    monkeypatch.setattr(negotiate, "local_descriptor", lambda: {"agent_invoke": "session-id"})

    async def controls(cmd, prompt):
        return cmd

    monkeypatch.setattr(gateway, "_apply_production_controls", controls)
    if env_agent is None:
        monkeypatch.delenv("N2N_MEMBER_AGENT", raising=False)
    else:
        monkeypatch.setenv("N2N_MEMBER_AGENT", env_agent)
    reply, _ = asyncio.run(gateway.run_agent_turn("fixture", local=True, model="ollama/m", timeout_s=10))
    assert reply == "OK"
    return json.loads(seen.read_text())


def test_several_agents_name_main(tmp_path, monkeypatch):
    argv = _run(tmp_path, monkeypatch, {"entries": {"main": {}, "alert": {}}})
    assert argv[:4] == ["agent", "--local", "--agent", "main"]
    assert argv[argv.index("--model") + 1] == "ollama/m"


def test_agents_list_layout_is_recognised(tmp_path, monkeypatch):
    argv = _run(tmp_path, monkeypatch, {"list": [{"id": "main"}, {"id": "alert"}]})
    assert argv[:4] == ["agent", "--local", "--agent", "main"]


@pytest.mark.parametrize("agents", [{}, {"entries": {"ops": {}}}, {"entries": {"ops": {}, "alert": {}}}, None])
def test_unambiguous_or_unknown_homes_keep_the_unnamed_command(tmp_path, monkeypatch, agents):
    argv = _run(tmp_path, monkeypatch, agents)
    assert "--agent" not in argv


def test_embedded_turn_agent_is_overridable(tmp_path, monkeypatch):
    argv = _run(tmp_path, monkeypatch, {"entries": {"ops": {}}}, env_agent="triage")
    assert argv[argv.index("--agent") + 1] == "triage"


def test_failed_turn_reports_cli_error_message(tmp_path, monkeypatch):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for the CLI argv fixture")
    cli = tmp_path / "agent-cli"
    cli.write_text(
        f"#!{node}\n"
        "process.stdout.write(JSON.stringify({ok:false,error:{type:'cli_error',message:'This model\\nwas not found.'}}));\n"
        "process.stderr.write('apiKey=do-not-surface');\n"
        "process.exit(1);\n"
    )
    cli.chmod(0o700)
    monkeypatch.setenv("OPENCLAW_CONFIG_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setattr(gateway, "_openclaw_bin", lambda: str(cli))
    monkeypatch.setattr(negotiate, "local_descriptor", lambda: {"agent_invoke": "session-id"})

    async def controls(cmd, prompt):
        return cmd

    monkeypatch.setattr(gateway, "_apply_production_controls", controls)
    with pytest.raises(RuntimeError) as err:
        asyncio.run(gateway.run_agent_turn("fixture", local=True, timeout_s=10))
    assert str(err.value) == ("Agent process exited 1; task result unavailable: "
                              "This model was not found.")
