"""Large embedded CLI results must survive process exit and noisy stderr."""
import asyncio
import json
import shutil

import pytest

from bgp.federation import gateway, negotiate


def test_large_node_result_survives_exit_and_stderr(tmp_path, monkeypatch):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for the real CLI stdout regression")
    cli = tmp_path / "agent-cli"
    cli.write_text(
        f"#!{node}\n"
        "process.stdout.write(JSON.stringify({payloads:[{text:'report '.repeat(80000)}],"
        "meta:{agentMeta:{usage:{total:12345}}}}));\n"
        "process.stderr.write(JSON.stringify({payloads:[{text:'diagnostic, not reply'}]}));\n"
        "process.exit(0);\n"
    )
    cli.chmod(0o700)
    monkeypatch.setattr(gateway, "_openclaw_bin", lambda: str(cli))
    monkeypatch.setattr(negotiate, "local_descriptor", lambda: {"agent_invoke": "session-id"})

    async def controls(cmd, prompt):
        return cmd

    monkeypatch.setattr(gateway, "_apply_production_controls", controls)
    reply, tokens = asyncio.run(gateway.run_agent_turn("fixture", local=True, timeout_s=10))
    assert reply == "report " * 80000
    assert tokens == 12345


@pytest.mark.parametrize("stdout", ["", "plugin diagnostic only", '{"payloads": [], "meta": {}}',
                                  '{"payloads": [{"text": "truncated'])
def test_empty_or_truncated_result_is_not_success(stdout):
    with pytest.raises(RuntimeError, match="task result unavailable"):
        gateway._extract_reply(stdout)


def test_empty_gateway_response_is_not_success():
    with pytest.raises(RuntimeError, match="no reply text"):
        gateway._extract_reply_from_ws_payload({"result": {"payloads": []}})


def test_failed_process_cannot_report_success(tmp_path, monkeypatch):
    cli = tmp_path / "failed-cli"
    cli.write_text('#!/bin/sh\nprintf \'{"payloads":[{"text":"partial reply"}]}\'\nexit 7\n')
    cli.chmod(0o700)
    monkeypatch.setattr(gateway, "_openclaw_bin", lambda: str(cli))
    monkeypatch.setattr(negotiate, "local_descriptor", lambda: {"agent_invoke": "session-id"})

    async def controls(cmd, prompt):
        return cmd

    monkeypatch.setattr(gateway, "_apply_production_controls", controls)
    with pytest.raises(RuntimeError, match="process exited 7"):
        asyncio.run(gateway.run_agent_turn("fixture", local=True, timeout_s=10))



def test_timed_out_turn_names_the_timeout(tmp_path, monkeypatch):
    cli = tmp_path / "hung-cli"
    cli.write_text("#!/bin/sh\nexec sleep 30\n")
    cli.chmod(0o700)
    monkeypatch.setattr(gateway, "_openclaw_bin", lambda: str(cli))
    monkeypatch.setattr(negotiate, "local_descriptor", lambda: {"agent_invoke": "session-id"})

    async def controls(cmd, prompt):
        return cmd

    monkeypatch.setattr(gateway, "_apply_production_controls", controls)
    with pytest.raises(asyncio.TimeoutError, match="session 'n2n-viz' timed out after 1s"):
        asyncio.run(gateway.run_agent_turn("fixture", session_key="n2n-viz", local=True, timeout_s=1))

def test_large_reply_with_braces_and_trailing_noise():
    text = "Topology report {observations}:\n" * 4000
    output = 'plugin banner\n' + json.dumps({"payloads": [{"text": text}],
        "meta": {"agentMeta": {"usage": {"total": 98}}}}) + '\n[agent] complete\n'
    assert gateway._extract_reply(output) == (text, 98)
