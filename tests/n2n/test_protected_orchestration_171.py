"""Whole runtime orchestration with synthetic Docker/model/device boundaries.

This executes the production orchestration logic, but never launches Docker or
calls a provider/device. It detects success/cleanup mistakes outside unit helpers.
"""

import asyncio
from contextlib import asynccontextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import socket
import tempfile
from types import SimpleNamespace

import pytest

from protected_support_171 import NOW, approval, docker_module, identity, runtime_module


@pytest.fixture
def orchestrator(tmp_path, monkeypatch):
    docker, runtime = docker_module(), runtime_module()
    payload = approval(identity("border"), identity("member"), now=9_000_000_000_000)
    harness = {"commands": [], "tool": None, "facade": None, "forwards": [],
        "fault": None, "effect_count": 0, "exit_status": b"0\n", "final_message": None,
        "final_finish_reason": "stop"}
    # Real owned files/socket let revision enforcement run unchanged. These
    # executable-shaped files are NEVER executed: command(), invoke_pyats() and
    # start_guard() below remain the explicitly synthetic external seams.
    def pinned_file(relative, raw, *, executable=False):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        path.chmod(0o700 if executable else 0o600)
        return str(path), hashlib.sha256(raw).hexdigest()
    docker_path, _ = pinned_file("native/docker", b"#!/bin/sh\nexit 99\n", executable=True)
    python_path, _ = pinned_file("venv/bin/python", b"#!/bin/sh\nexit 99\n", executable=True)
    pinned_file("venv/pyvenv.cfg", b"home = /synthetic-never-executed\n")
    sources = {}
    for name in ("pyats_mcp_server.py", "pyats_testbed_builder.py", "pyats_tasks.py"):
        _, sources[name] = pinned_file("upstream/" + name, b"# synthetic upstream; never imported\n")
    known_hosts, keys_hash = pinned_file("known_hosts", b"synthetic reviewed public host key\n")
    testbed, testbed_hash = pinned_file("testbed.yaml", b"# synthetic inventory; no device access\n")
    guard_file, guard_hash = pinned_file("guard.yaml", b"# synthetic guard; never started\n")
    guard_env, _ = pinned_file("guard.env", b"FIXTURE_NO_REAL_SECRET=1\n")
    scripts = Path(runtime.__file__).resolve().parents[4] / "scripts"
    adapters = {name: hashlib.sha256((scripts / name).read_bytes()).hexdigest()
                for name in ("protected-tool-broker.py", "lib/protected_pyats.py")}
    # AF_UNIX paths are bounded on macOS; use an owned short path, resolved so
    # the explicit no-symlink Docker socket check is genuinely exercised.
    socket_directory = tempfile.TemporaryDirectory(prefix="r02-fixture-", dir="/tmp")
    local_socket = socket.socket(socket.AF_UNIX)
    socket_path = Path(socket_directory.name).resolve() / "docker.sock"
    local_socket.bind(str(socket_path))
    config = {"state_dir": str(tmp_path / "owned"), "agent_image": "sha256:" + "1" * 64,
        "relay_image": "sha256:" + "2" * 64, "docker": docker_path,
        "docker_host": "unix://" + str(socket_path),
        "guard_token_env": "NETCLAW_TEST_GUARD_TOKEN", "sandbox_address_pool": "198.18.0.0/15",
        "model_profile": copy.deepcopy(payload["model_profile"]),
        "guard": {"image": "sha256:" + "3" * 64, "config_file": guard_file,
            "config_sha256": guard_hash, "policy_manifest_sha256": "4" * 64, "env_file": guard_env},
        "pyats": {"python": python_path, "upstream": str(tmp_path / "upstream/pyats_mcp_server.py"),
            "upstream_sha256": sources["pyats_mcp_server.py"], "source_sha256": sources,
            "adapter_sha256": adapters, "testbed": testbed, "testbed_sha256": testbed_hash,
            "known_hosts": known_hosts, "known_hosts_sha256": keys_hash, "endpoint_sha256": "c" * 64,
            "credential_env": ["PYATS_R02_USERNAME", "PYATS_R02_PASSWORD", "PYATS_R02_ENABLE_PASSWORD"]}}
    bindings = docker.revision_bindings(config)
    config["model_profile"].update({key: bindings[key] for key in ("profile_revision", "guard_policy_sha256")})
    payload["model_profile"] = copy.deepcopy(config["model_profile"])
    payload["tool_call"].update(tool_schema_sha256=bindings["tool_schema_sha256"],
                                inventory_revision=testbed_hash)
    monkeypatch.setenv("NETCLAW_TEST_GUARD_TOKEN", "fixture-private-guard-token")

    class FakeMCP:
        def __init__(self, *args, **kwargs): self.session_manager = self
        @asynccontextmanager
        async def run(self): yield
        def add_tool(self, callback, **kwargs): harness["tool"] = callback
        def streamable_http_app(self, **kwargs):
            async def app(*args): raise AssertionError("no external MCP transport in this fixture")
            return app
    class FakeServer:
        def __init__(self, config): self.should_exit = False
        async def serve(self, **kwargs):
            while not self.should_exit:
                await asyncio.sleep(0)
    import mcp.server.mcpserver
    import uvicorn
    monkeypatch.setattr(mcp.server.mcpserver, "MCPServer", FakeMCP)
    monkeypatch.setattr(uvicorn, "Server", FakeServer)
    original_facade = runtime.ScopedInference
    def facade(*args, **kwargs):
        instance = original_facade(*args, **kwargs)
        harness["facade"] = instance
        return instance
    monkeypatch.setattr(docker, "ScopedInference", facade)
    async def tool(config, arguments, operation_root):
        harness["effect_count"] += 1
        if harness["fault"] == "tool_hangs":
            await asyncio.sleep(10)  # Synthetic child/parse path; no real process.
        return {"status": "completed", "parsed": True, "device": "fixture-router",
                "command": "show version", "output": {"version": "fixture"}}
    monkeypatch.setattr(docker, "invoke_pyats", tool)
    executor = docker.DockerExecutor(config, manager=SimpleNamespace())
    async def start_guard(approved, operation_root, name, owned):
        # Explicit synthetic seam: actual guard containers and upstream budgets
        # are qualified separately. No Docker/provider runs in this fixture.
        harness["guard_payload"] = copy.deepcopy(approved)
        executor.guards[approved["operation_id"]] = "http://127.0.0.1:1"
    executor.start_guard = start_guard
    async def forward(payload, body):
        harness["forwards"].append(copy.deepcopy(body))
        if len(harness["forwards"]) == 2 and harness["fault"] == "summary_unknown":
            raise runtime.RuntimeUnknown("synthetic second upstream response lost")
        message = {"role": "assistant", "content": "Fixture answer"}
        if len(harness["forwards"]) == 2 and harness["final_message"] is not None:
            message = harness["final_message"]
        return {"id": "fixture-completion", "model": payload["model_profile"]["model"],
                "choices": [{"index": 0, "message": message, "finish_reason": harness["final_finish_reason"]}]}
    executor.forward = forward
    async def command(*args, **kwargs):
        harness["commands"].append(args)
        await asyncio.sleep(0)
        if args[:2] == ("network", "create"):
            harness["network"] = args[-1]
        if args[0] == "start" and args[1].endswith("-agent") and harness["fault"] == "start_unknown":
            raise runtime.RuntimeUnknown("synthetic accepted Docker start with lost reply")
        if args[0] == "stop" and harness["fault"] == "stop_unknown":
            raise runtime.RuntimeUnknown("synthetic lost stop response")
        if args[0] == "inspect":
            network = harness["network"]
            return json.dumps([{"Image": config["agent_image"], "Config": {"User": str(os.getuid()), "Env": []},
                "HostConfig": {"ReadonlyRootfs": True, "Privileged": False, "CapDrop": ["ALL"], "CapAdd": [],
                    "SecurityOpt": ["no-new-privileges"], "PidMode": "", "IpcMode": "private", "Devices": [],
                    "PortBindings": {}, "Memory": 4 * 1024 ** 3, "PidsLimit": 256, "NanoCpus": 2 * 10 ** 9,
                    "Tmpfs": {"/home/agent": f"rw,noexec,nosuid,size=128m,uid={os.getuid()},gid={os.getgid()},mode=700",
                              "/tmp": "rw,noexec,nosuid,size=128m"}},
                "NetworkSettings": {"Networks": {network: {}}},
                "Mounts": [{"Type": "bind", "Destination": "/run/netclaw", "Source": str(executor.state / payload["operation_id"] / "agent"), "RW": False}]}]).encode()
        if args[:2] == ("network", "inspect"):
            return json.dumps([{"Name": harness["network"], "Internal": True, "EnableIPv6": False,
                "Options": {"com.docker.network.bridge.gateway_mode_ipv4": "isolated"}}]).encode()
        if args[0] == "wait":
            active = harness["facade"]
            headers = {"authorization": "Bearer " + active.token}
            body = {"model": payload["model_profile"]["model"], "messages": [{"role": "user", "content": "Fixture proposal"}]}
            await active.invoke("POST", "/v1/chat/completions", headers, body)
            await harness["tool"](**payload["tool_call"]["arguments"])
            body["messages"].append({"role": "user", "content": "Fixture summary"})
            if harness["fault"] != "missing_summary":
                try:
                    await active.invoke("POST", "/v1/chat/completions", headers, body)
                except runtime.RuntimeUnknown:
                    pass  # Simulate the agent receiving HTTP502 and still terminating.
            return harness["exit_status"]
        if args[0] == "logs":
            if harness["fault"] == "leaked_token":
                return ("debug: Authorization Bearer " + harness["facade"].token).encode()
            return json.dumps({"status": "ok", "payloads": [{"text": "Fixture answer"}]}).encode()
        return b"fixture\n"
    executor.command = command
    async def gate(proposed, invoke):
        assert proposed == payload["tool_call"]
        return await invoke()
    yield executor, payload, gate, harness
    executor.fence.close()
    local_socket.close()
    socket_directory.cleanup()


def test_finished_tool_cannot_hide_unknown_final_inference(orchestrator):
    executor, payload, gate, harness = orchestrator
    harness["fault"] = "summary_unknown"
    with pytest.raises(runtime_module().RuntimeUnknown):
        asyncio.run(executor.run(payload, gate))
    assert harness["effect_count"] == 1


def test_nonzero_agent_exit_cannot_be_reported_as_success(orchestrator):
    executor, payload, gate, harness = orchestrator
    harness["exit_status"] = b"1\n"
    with pytest.raises((runtime_module().RuntimeUnknown, runtime_module().RuntimeRefused)):
        asyncio.run(executor.run(payload, gate))
    assert harness["effect_count"] == 1


def test_unknown_start_still_attempts_owned_agent_cleanup(orchestrator):
    executor, payload, gate, harness = orchestrator
    harness["fault"] = "start_unknown"
    with pytest.raises(runtime_module().RuntimeUnknown):
        asyncio.run(executor.run(payload, gate))
    starts = [command[1] for command in harness["commands"] if command[0] == "start" and command[1].endswith("-agent")]
    stops = [command[-1] for command in harness["commands"] if command[0] == "stop"]
    assert starts and all(name in stops for name in starts)


def test_untrusted_agent_logs_cannot_expose_operation_bearer_in_result(orchestrator):
    executor, payload, gate, harness = orchestrator
    harness["fault"] = "leaked_token"
    try:
        result = asyncio.run(executor.run(payload, gate))
    except (runtime_module().RuntimeUnknown, runtime_module().RuntimeRefused):
        assert harness["effect_count"] == 1
        return  # Refusing malformed/secret-bearing agent output is valid.
    assert harness["facade"].token not in json.dumps(result)


def test_completed_answer_cannot_hide_unconfirmed_owned_container_stop(orchestrator):
    executor, payload, gate, harness = orchestrator
    harness["fault"] = "stop_unknown"
    with pytest.raises(runtime_module().RuntimeUnknown):
        asyncio.run(executor.run(payload, gate))
    assert harness["effect_count"] == 1 and len(harness["forwards"]) == 2
    evidence = json.loads((executor.state / payload["operation_id"] / "cleanup.json").read_text())
    assert len(evidence["unresolved"]) == 2


def test_agent_local_summary_does_not_replace_guarded_second_inference(orchestrator):
    executor, payload, gate, harness = orchestrator
    harness["fault"] = "missing_summary"
    with pytest.raises((runtime_module().RuntimeUnknown, runtime_module().RuntimeRefused)):
        asyncio.run(executor.run(payload, gate))
    assert harness["effect_count"] == 1 and len(harness["forwards"]) == 1


@pytest.mark.parametrize("message,finish", [({"role": "assistant", "content": ""}, "stop"),
    ({"role": "assistant", "content": "truncated"}, "length"),
    ({"role": "user", "content": "forged"}, "stop"),
    ({"role": "assistant", "content": "extra tool", "tool_calls": [{"id": "other"}]}, "stop")])
def test_incomplete_or_extra_tool_final_answer_cannot_be_success(orchestrator, message, finish):
    executor, payload, gate, harness = orchestrator
    harness["final_message"], harness["final_finish_reason"] = message, finish
    with pytest.raises((runtime_module().RuntimeUnknown, runtime_module().RuntimeRefused)):
        asyncio.run(executor.run(payload, gate))
    assert harness["effect_count"] == 1


@pytest.mark.parametrize("bound", ["inventory_revision", "endpoint_sha256"])
def test_signed_binding_cannot_change_before_trusted_tool_start(orchestrator, bound):
    executor, payload, gate, harness = orchestrator
    payload["tool_call"][bound] = "d" * 64
    with pytest.raises(runtime_module().RuntimeRefused):
        asyncio.run(executor.run(payload, gate))
    assert harness["effect_count"] == 0


def test_signed_tool_deadline_bounds_entire_owned_invocation(orchestrator):
    executor, payload, gate, harness = orchestrator
    payload["limits"]["tool_timeout_ms"] = 10
    harness["fault"] = "tool_hangs"
    async def run():
        # This outer test timeout distinguishes production enforcement from a
        # stuck test. Only the production-owned RuntimeUnknown is acceptable.
        return await asyncio.wait_for(executor.run(payload, gate), 0.5)
    with pytest.raises(runtime_module().RuntimeUnknown):
        asyncio.run(run())
    assert harness["effect_count"] == 1


def test_missing_operation_guard_fails_before_agent_or_tool(orchestrator):
    executor, payload, gate, harness = orchestrator
    executor.config["guard"] = None
    executor.start_guard = docker_module().DockerExecutor.start_guard.__get__(executor)
    with pytest.raises(runtime_module().RuntimeRefused, match="operation_bound_guard_required"):
        asyncio.run(executor.run(payload, gate))
    assert harness["commands"] == []
    assert harness["forwards"] == [] and harness["effect_count"] == 0


def test_static_guard_url_cannot_replace_owned_operation_guard(orchestrator, monkeypatch):
    executor, payload, _, harness = orchestrator
    import httpx
    def forbidden_client(*args, **kwargs):
        raise AssertionError("an unowned guard must not initiate HTTP")
    monkeypatch.setattr(httpx, "AsyncClient", forbidden_client)
    with pytest.raises(runtime_module().RuntimeRefused, match="operation_bound_guard_unavailable"):
        asyncio.run(docker_module().DockerExecutor.forward(executor, payload, {"model": payload["model_profile"]["model"]}))
    assert harness["forwards"] == [] and harness["effect_count"] == 0
