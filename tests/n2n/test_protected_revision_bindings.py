"""Runtime revision and raw-MCP checks using local files/sockets only.

No Docker daemon, guard, model, SSH or device operation is performed.
"""
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[2]
RUNTIME_SOURCE = Path(os.environ.get("NETCLAW_171_RUNTIME_SOURCE", REPO)).resolve()
sys.path.insert(0, str(RUNTIME_SOURCE / "mcp-servers/protocol-mcp"))
from bgp.federation import protected_runtime as runtime

NAME = "bgp.federation.protected_docker"
if NAME not in sys.modules:
    spec = importlib.util.spec_from_file_location(NAME, REPO / "mcp-servers/protocol-mcp/bgp/federation/protected_docker.py")
    docker = importlib.util.module_from_spec(spec)
    sys.modules[NAME] = docker
    spec.loader.exec_module(docker)
docker = sys.modules[NAME]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def bound(tmp_path, monkeypatch):
    tmp_path = tmp_path.resolve()
    native = tmp_path / "native"
    native.mkdir()
    executable = native / "docker"
    executable.write_text("#!/bin/sh\nexit 0\n")
    executable.chmod(0o700)
    python = tmp_path / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/bin/sh\nexit 0\n")
    python.chmod(0o700)
    (python.parent.parent / "pyvenv.cfg").write_text("fixture isolated interpreter\n")
    # A real owned Unix socket validates the endpoint contract, without a daemon.
    local = socket.socket(socket.AF_UNIX)
    socket_home = tempfile.TemporaryDirectory(prefix="nc171-", dir=str(Path("/tmp").resolve()))
    socket_path = Path(socket_home.name) / "docker.sock"
    local.bind(str(socket_path))
    source = tmp_path / "upstream"
    source.mkdir()
    manifest = {}
    for name in ("pyats_mcp_server.py", "pyats_testbed_builder.py", "pyats_tasks.py"):
        raw = ("# fixture " + name + "\n").encode()
        (source / name).write_bytes(raw)
        manifest[name] = digest(raw)
    testbed, keys, guard_config, guard_env = [tmp_path / name for name in
        ("testbed.yaml", "known_hosts", "config.yaml", "guard.env")]
    for path in (testbed, keys, guard_config, guard_env):
        path.write_text("fixture private bytes for " + path.name + "\n")
        path.chmod(0o600)
    scripts = Path(runtime.__file__).resolve().parents[4] / "scripts"
    config = {"state_dir": str(tmp_path / "state"), "agent_image": "sha256:" + "1" * 64,
        "relay_image": "sha256:" + "2" * 64, "docker": str(executable),
        "docker_host": "unix://" + str(socket_path), "guard_token_env": "NETCLAW_FIXTURE_TOKEN",
        "sandbox_address_pool": "198.18.0.0/15", "model_profile": {
            "profile_id": "fixture", "profile_revision": "pending", "runtime_kind": "openclaw",
            "runtime_version": "2026.7.1-2", "provider": "anthropic", "model": "claude-sonnet-4-6",
            "guard_policy_sha256": "0" * 64},
        "guard": {"image": "sha256:" + "3" * 64, "config_file": str(guard_config),
            "config_sha256": digest(guard_config.read_bytes()), "policy_manifest_sha256": "4" * 64,
            "env_file": str(guard_env)},
        "pyats": {"python": str(python), "upstream": str(source / "pyats_mcp_server.py"),
            "upstream_sha256": manifest["pyats_mcp_server.py"], "source_sha256": manifest,
            "adapter_sha256": {name: digest((scripts / name).read_bytes()) for name in
                ("protected-tool-broker.py", "lib/protected_pyats.py")},
            "testbed": str(testbed), "testbed_sha256": digest(testbed.read_bytes()),
            "known_hosts": str(keys), "known_hosts_sha256": digest(keys.read_bytes()),
            "endpoint_sha256": "5" * 64,
            "credential_env": ["PYATS_R02_USERNAME", "PYATS_R02_PASSWORD", "PYATS_R02_ENABLE_PASSWORD"]}}
    pins = docker.revision_bindings(config)
    config["model_profile"].update({key: pins[key] for key in ("profile_revision", "guard_policy_sha256")})
    payload = {"operation_id": "fixture-operation", "model_profile": copy.deepcopy(config["model_profile"]),
        "tool_call": {"tool_schema_sha256": pins["tool_schema_sha256"],
            "inventory_revision": config["pyats"]["testbed_sha256"], "endpoint_sha256": "5" * 64,
            "arguments": {"device_name": "R1", "command": "show version", "timeout": 30, "retries": 1}},
        "limits": {"expires_at_ms": 9_000_000_000_000}}
    monkeypatch.setenv("NETCLAW_FIXTURE_TOKEN", "fixture-only")
    yield config, payload, tmp_path
    local.close()
    socket_home.cleanup()


def test_actual_files_and_native_endpoints_bind_successfully(bound):
    config, payload, _ = bound
    assert docker.validate_execution_bindings(config, payload) == docker.revision_bindings(config)
    assert len(payload["model_profile"]["profile_revision"]) == 64
    assert set(docker.protected_tool_input_schema()["properties"]) == set(payload["tool_call"]["arguments"])


@pytest.mark.parametrize("change", [
    {"provider": "openai"}, {"provider": "fixture-provider"},
    {"model": "claude-opus-4-6"}, {"model": "fixture-sonnet"},
    {"runtime_kind": "unqualified"}, {"runtime_version": "2026.7.1"},
    {"runtime_kind": "openclaw", "runtime_version": "v0.21.6"},
    {"runtime_kind": "hermes", "runtime_version": "2026.7.1-2"},
    {"runtime_kind": "hermes", "runtime_version": "v0.21.7"},
])
def test_profile_cannot_mislabel_fixed_provider_or_qualified_harness(bound, change):
    config, payload, _ = bound
    config["model_profile"].update(change)
    payload["model_profile"] = copy.deepcopy(config["model_profile"])
    # Even recomputing a fresh revision cannot qualify an unsupported label.
    with pytest.raises(runtime.RuntimeRefused, match="unqualified_execution_profile"):
        docker.revision_bindings(config)
    with pytest.raises(runtime.RuntimeRefused, match="unqualified_execution_profile"):
        docker.validate_execution_bindings(config, payload)


def test_qualified_hermes_profile_can_bind_without_claiming_actual_image_qualification(bound):
    config, payload, _ = bound
    config["model_profile"].update(runtime_kind="hermes", runtime_version="v0.21.6")
    pins = docker.revision_bindings(config)
    config["model_profile"].update({key: pins[key] for key in ("profile_revision", "guard_policy_sha256")})
    payload["model_profile"] = copy.deepcopy(config["model_profile"])
    assert docker.validate_execution_bindings(config, payload) == pins


@pytest.mark.parametrize("field", ["agent_image", "relay_image", "sandbox_address_pool"])
def test_runtime_change_cannot_retain_approved_revision(bound, field):
    config, payload, _ = bound
    config[field] = "198.19.0.0/16" if field == "sandbox_address_pool" else "sha256:" + "6" * 64
    with pytest.raises(runtime.RuntimeRefused, match="signed_execution_revision_changed"):
        docker.validate_execution_bindings(config, payload)


@pytest.mark.parametrize("field", ["image", "config_sha256", "policy_manifest_sha256"])
def test_guard_change_cannot_retain_approved_revision(bound, field):
    config, payload, _ = bound
    config["guard"][field] = ("sha256:" if field == "image" else "") + "6" * 64
    with pytest.raises(runtime.RuntimeRefused, match="signed_execution_revision_changed"):
        docker.validate_execution_bindings(config, payload)


@pytest.mark.parametrize("key", ["docker", "python"])
def test_native_executable_bytes_are_bound(bound, key):
    config, payload, _ = bound
    path = config["docker"] if key == "docker" else config["pyats"]["python"]
    Path(path).write_text("#!/bin/sh\n# changed after approval\nexit 0\n")
    with pytest.raises(runtime.RuntimeRefused, match="signed_execution_revision_changed"):
        docker.validate_execution_bindings(config, payload)


@pytest.mark.parametrize("kind", ["source", "adapter"])
def test_tool_implementation_manifest_is_signed(bound, kind):
    config, payload, _ = bound
    manifest = config["pyats"]["source_sha256" if kind == "source" else "adapter_sha256"]
    name = "pyats_tasks.py" if kind == "source" else "lib/protected_pyats.py"
    manifest[name] = "8" * 64
    with pytest.raises(runtime.RuntimeRefused, match="signed_execution_revision_changed"):
        docker.validate_execution_bindings(config, payload)


@pytest.mark.parametrize("kind", ["guard", "source", "testbed", "known_hosts"])
def test_actual_file_drift_refuses_even_with_unchanged_declared_pins(bound, kind):
    config, payload, _ = bound
    path = (config["guard"]["config_file"] if kind == "guard" else
        str(Path(config["pyats"]["upstream"]).parent / "pyats_tasks.py") if kind == "source" else config["pyats"][kind])
    Path(path).write_text("changed after approval\n")
    with pytest.raises(runtime.RuntimeRefused):
        docker.validate_execution_bindings(config, payload)


@pytest.mark.parametrize("kind", ["extra", "string", "boolean", "float", "name"])
def test_raw_mcp_is_exact_before_sdk_coercion(bound, kind):
    _, payload, _ = bound
    approved = payload["tool_call"]["arguments"]
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "pyats_run_show_command", "arguments": dict(approved)}}
    docker.validate_raw_mcp_call(body, approved)
    if kind == "extra": body["params"]["arguments"]["unexpected"] = "hidden"
    elif kind == "name": body["params"]["name"] = "another_tool"
    else: body["params"]["arguments"]["retries"] = {"string": "1", "boolean": True, "float": 1.0}[kind]
    with pytest.raises(runtime.RuntimeRefused, match="raw_mcp_arguments_changed"):
        docker.validate_raw_mcp_call(body, approved)


def test_raw_mcp_duplicate_fields_are_rejected_before_sdk():
    with pytest.raises(runtime.RuntimeRefused):
        docker.strict_inference_json(b'{"method":"tools/call","params":{"arguments":{"retries":1,"retries":2}}}')


def test_constructor_copies_config_and_blocks_ambient_docker_configuration(bound, monkeypatch):
    config, _, _ = bound
    monkeypatch.setenv("DOCKER_HOST", "tcp://untrusted.invalid:2375")
    executor = docker.DockerExecutor(config, manager=SimpleNamespace())
    try:
        config["agent_image"] = "sha256:" + "0" * 64
        assert executor.config["agent_image"] != config["agent_image"]
        (executor.docker_config / "config.json").write_text('{"proxies":{"default":{"httpProxy":"untrusted"}}}')
        with pytest.raises(runtime.RuntimeRefused, match="native_docker_configuration_changed"):
            asyncio.run(executor.command("version"))
    finally:
        executor.fence.close()


def test_remote_or_symlink_docker_host_is_refused(bound):
    config, _, root = bound
    with pytest.raises(runtime.RuntimeRefused):
        docker._docker_host("tcp://127.0.0.1:2375")
    link = root / "linked.sock"
    link.symlink_to(config["docker_host"].removeprefix("unix://"))
    with pytest.raises(runtime.RuntimeRefused):
        docker._docker_host("unix://" + str(link))


def test_native_command_uses_only_pinned_socket_and_private_empty_config(bound, monkeypatch):
    config, _, _ = bound
    # This executable prints its invocation; it is not a Docker client.
    Path(config["docker"]).write_text("#!" + sys.executable + "\nimport json,os,sys\nprint(json.dumps({'argv':sys.argv[1:],'env':dict(os.environ)}))\n")
    monkeypatch.setenv("DOCKER_HOST", "tcp://untrusted.invalid:2375")
    monkeypatch.setenv("DOCKER_CONFIG", "/untrusted")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-never-inherited")
    executor = docker.DockerExecutor(config, manager=SimpleNamespace())
    try:
        result = json.loads(asyncio.run(executor.command("fixture")))
        assert result["argv"] == ["--host", config["docker_host"], "--config", str(executor.docker_config), "fixture"]
        assert result["env"]["HOME"] == str(executor.docker_config)
        assert not set(result["env"]) & {"DOCKER_HOST", "DOCKER_CONFIG", "ANTHROPIC_API_KEY"}
    finally:
        executor.fence.close()


def test_native_command_output_is_bounded_while_reading(bound):
    config, _, _ = bound
    Path(config["docker"]).write_text("#!" + sys.executable + "\nimport sys\nsys.stdout.buffer.write(b'x' * (5*1024*1024))\n")
    executor = docker.DockerExecutor(config, manager=SimpleNamespace())
    try:
        with pytest.raises(runtime.RuntimeUnknown):
            asyncio.run(executor.command("fixture"))
    finally:
        executor.fence.close()


def guard_inspect(config, payload, home):
    return {"Image": config["guard"]["image"], "Config": {"User": str(os.getuid()),
        "Entrypoint": ["python3", "/opt/netclaw/scripts/protected-guard.py"],
        "Cmd": ["--home", "/guard", "--config-sha256", config["guard"]["config_sha256"],
                "--policy-manifest-sha256", config["guard"]["policy_manifest_sha256"]],
        "Env": ["HOME=/guard-user", "DEFENSECLAW_HOME=/guard", "NETCLAW_OPERATION_ID=" + payload["operation_id"],
            "NETCLAW_OPERATION_EXPIRES_MS=" + str(payload["limits"]["expires_at_ms"]),
            "NETCLAW_OPERATION_MODEL=" + payload["model_profile"]["model"], "NETCLAW_OPERATION_MAX_PROVIDER_CALLS=2"]},
        "HostConfig": {"ReadonlyRootfs": True, "CapDrop": ["ALL"], "SecurityOpt": ["no-new-privileges"],
            "NetworkMode": "bridge", "IpcMode": "private", "Memory": 768*1024*1024,
            "PidsLimit": 128, "NanoCpus": 1000000000, "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=64m"},
            "PortBindings": {"4000/tcp": [{"HostIp": "127.0.0.1", "HostPort": ""}]}},
        "NetworkSettings": {"Networks": {"bridge": {}}, "Ports": {"4000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "12345"}]}},
        "Mounts": [{"Type": "bind", "Destination": "/guard", "Source": str(home), "RW": True},
            {"Type": "bind", "Destination": "/guard/guard.env", "Source": config["guard"]["env_file"], "RW": False}]}


@pytest.mark.parametrize("mutation", ["none", "public", "provider_env", "extra_mount", "privileged", "memory", "cmd", "image", "host_network"])
def test_guard_inspection_matches_fixed_owned_launch(bound, mutation):
    config, payload, root = bound
    inspected = guard_inspect(config, payload, root / "guard")
    if mutation == "public": inspected["NetworkSettings"]["Ports"]["4000/tcp"][0]["HostIp"] = "0.0.0.0"
    elif mutation == "provider_env": inspected["Config"]["Env"].append("ANTHROPIC_API_KEY=fixture-forbidden")
    elif mutation == "extra_mount": inspected["Mounts"].append({"Type": "bind", "Destination": "/host", "Source": "/", "RW": False})
    elif mutation == "privileged": inspected["HostConfig"]["Privileged"] = True
    elif mutation == "memory": inspected["HostConfig"]["Memory"] = 0
    elif mutation == "cmd": inspected["Config"]["Cmd"] += ["--unreviewed"]
    elif mutation == "image": inspected["Image"] = "sha256:" + "9" * 64
    elif mutation == "host_network": inspected["HostConfig"]["NetworkMode"] = "host"
    kwargs = dict(image=config["guard"]["image"], home=root / "guard", env_file=config["guard"]["env_file"], payload=payload,
        config_sha256=config["guard"]["config_sha256"], policy_manifest_sha256=config["guard"]["policy_manifest_sha256"], running=True)
    if mutation == "none":
        assert docker.inspect_guard(inspected, **kwargs) == "http://127.0.0.1:12345"
    else:
        with pytest.raises(runtime.RuntimeRefused):
            docker.inspect_guard(inspected, **kwargs)
