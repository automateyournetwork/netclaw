"""Independent drift and resolved-endpoint tests; no child/device is started."""

import asyncio
import copy
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from protected_support_171 import canonical, docker_module, pyats_module, runtime_module
from test_protected_runtime_171 import fake_pyats


ARGUMENTS = {"device_name": "fixture-router", "command": "show version", "timeout": 30, "retries": 1}


def strict_document(known_hosts):
    return {"testbed": {"name": "synthetic-171", "credentials": {
        "default": {"username": "%ENV{PYATS_R02_USERNAME}", "password": "%ENV{PYATS_R02_PASSWORD}"},
        "enable": {"password": "%ENV{PYATS_R02_ENABLE_PASSWORD}"}}},
        "devices": {"fixture-router": {"os": "iosxe", "connections": {
            "defaults": {"class": "unicon.Unicon"},
            "cli": {"protocol": "ssh", "ip": "192.0.2.171", "port": 22,
                "ssh_options": "-F /dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile=" + str(known_hosts)}}}}}


@pytest.fixture
def source_binding(tmp_path, monkeypatch):
    runtime = runtime_module()
    source = tmp_path / "upstream"
    source.mkdir()
    contents = {name: ("# synthetic " + name + "\n").encode() for name in (
        "pyats_mcp_server.py", "pyats_testbed_builder.py", "pyats_tasks.py")}
    for name, raw in contents.items():
        (source / name).write_bytes(raw)
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_bytes(b"192.0.2.171 ssh-ed25519 fixture-public-key-no-SSH-is-performed\n")
    known_hosts.chmod(0o600)
    testbed = tmp_path / "testbed.yaml"
    testbed.write_text(yaml.safe_dump(strict_document(known_hosts)))
    testbed.chmod(0o600)
    manifest = {name: hashlib.sha256(raw).hexdigest() for name, raw in contents.items()}
    config = {"upstream": str(source / "pyats_mcp_server.py"), "source_sha256": manifest,
        "upstream_sha256": manifest["pyats_mcp_server.py"], "testbed": str(testbed),
        "testbed_sha256": hashlib.sha256(testbed.read_bytes()).hexdigest(),
        "known_hosts": str(known_hosts), "known_hosts_sha256": hashlib.sha256(known_hosts.read_bytes()).hexdigest(),
        "adapter_sha256": {name: hashlib.sha256((Path(runtime.__file__).parents[4] / "scripts" / name).read_bytes()).hexdigest()
            for name in ("protected-tool-broker.py", "lib/protected_pyats.py")},
        "endpoint_sha256": "c" * 64, "python": "/fixture/never-launched-python"}
    operation = tmp_path / "operation"
    launched = []
    @asynccontextmanager
    async def forbidden(params, **kwargs):
        launched.append(params)
        raise AssertionError("a drift refusal must precede child creation")
        yield
    import mcp.client.stdio
    monkeypatch.setattr(mcp.client.stdio, "stdio_client", forbidden)
    yield runtime, config, source, contents, testbed, operation, launched
    frozen = operation / "source"
    if frozen.exists():
        frozen.chmod(0o700)  # Permit pytest's ordinary temporary-file cleanup.


@pytest.mark.parametrize("name", ["pyats_mcp_server.py", "pyats_testbed_builder.py", "pyats_tasks.py"])
def test_source_closure_drift_refuses_before_child_creation(source_binding, name):
    runtime, config, source, _, _, operation, launched = source_binding
    (source / name).write_text("# changed after review\n")
    with pytest.raises(runtime.RuntimeRefused):
        asyncio.run(runtime.invoke_pyats(config, ARGUMENTS, operation))
    assert launched == []


def test_testbed_drift_refuses_before_child_creation(source_binding):
    runtime, config, _, _, testbed, operation, launched = source_binding
    testbed.write_text("devices: {different-router: {os: iosxe}}\n")
    with pytest.raises(runtime.RuntimeRefused):
        asyncio.run(runtime.invoke_pyats(config, ARGUMENTS, operation))
    assert launched == []


def test_known_host_key_drift_refuses_before_child_creation(source_binding):
    runtime, config, _, _, _, operation, launched = source_binding
    Path(config["known_hosts"]).write_text("192.0.2.171 fixture-different-host-key\n")
    with pytest.raises(runtime.RuntimeRefused):
        asyncio.run(runtime.invoke_pyats(config, ARGUMENTS, operation))
    assert launched == []


@pytest.mark.parametrize("adapter", ["protected-tool-broker.py", "lib/protected_pyats.py"])
def test_reviewed_adapter_digest_mismatch_refuses_before_child_creation(source_binding, adapter):
    runtime, config, _, _, _, operation, launched = source_binding
    config["adapter_sha256"][adapter] = "0" * 64
    with pytest.raises(runtime.RuntimeRefused):
        asyncio.run(runtime.invoke_pyats(config, ARGUMENTS, operation))
    assert launched == []


@pytest.mark.parametrize("reserved", ["PYATS_TESTBED_PATH", "PYATS_TESTBED_MODE",
    "PYATS_MCP_CONN_CACHE_TTL", "PYATS_MCP_ARTIFACTS_DIR", "PYTHONPATH", "ANTHROPIC_API_KEY"])
def test_credential_slots_cannot_override_execution_environment(source_binding, monkeypatch, reserved):
    runtime, config, _, _, _, operation, launched = source_binding
    config["credential_env"] = [reserved]
    monkeypatch.setenv(reserved, "fixture-untrusted-override")
    with pytest.raises(runtime.RuntimeRefused):
        asyncio.run(runtime.invoke_pyats(config, ARGUMENTS, operation))
    assert launched == []


def test_child_receives_frozen_source_and_testbed_after_originals_change(source_binding, monkeypatch):
    runtime, config, source, contents, testbed, operation, launched = source_binding
    original_testbed = testbed.read_bytes()
    original_keys = Path(config["known_hosts"]).read_bytes()
    config["credential_env"] = ["PYATS_R02_USERNAME", "PYATS_R02_PASSWORD"]
    monkeypatch.setenv("PYATS_R02_USERNAME", "fixture-user")
    monkeypatch.setenv("PYATS_R02_PASSWORD", "fixture-password")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fixture-never-forwarded")
    monkeypatch.setenv("HTTPS_PROXY", "http://fixture-never-forwarded.invalid")
    @asynccontextmanager
    async def capture(params, **kwargs):
        launched.append(params)
        for name in contents:
            (source / name).write_text("# original changed after preparation\n")
        testbed.write_text("devices: {}\n")
        Path(config["known_hosts"]).write_text("fixture changed original host keys\n")
        pairs = dict(zip(params.args[1::2], params.args[2::2]))
        frozen_main = Path(pairs["--upstream"])
        assert frozen_main.parent == operation / "source"
        assert {name: (frozen_main.parent / name).read_bytes() for name in contents} == contents
        materialized = yaml.safe_load(Path(params.env["PYATS_TESTBED_PATH"]).read_bytes())
        expected = yaml.safe_load(original_testbed)
        expected["devices"]["fixture-router"]["connections"]["cli"]["ssh_options"] = (
            "-F /dev/null -o StrictHostKeyChecking=yes -o UserKnownHostsFile=" + str(operation / "known_hosts"))
        assert materialized == expected
        assert (operation / "known_hosts").read_bytes() == original_keys
        assert Path(params.args[0]) == operation / "adapter" / "protected-tool-broker.py"
        for name, digest in config["adapter_sha256"].items():
            assert hashlib.sha256((operation / "adapter" / name).read_bytes()).hexdigest() == digest
        binding = json.loads((operation / "inventory-binding.json").read_text())
        assert binding["reviewed_testbed_sha256"] == hashlib.sha256(original_testbed).hexdigest()
        assert binding["known_hosts_sha256"] == hashlib.sha256(original_keys).hexdigest()
        assert Path(params.env["HOME"]) == operation
        assert params.env["PYATS_MCP_CONN_CACHE_TTL"] == "0"
        assert params.env["PYTHON_DOTENV_DISABLED"] == "1"
        assert params.env["PYATS_R02_USERNAME"] == "fixture-user"
        assert params.env["PYATS_R02_PASSWORD"] == "fixture-password"
        assert "ANTHROPIC_API_KEY" not in params.env and "HTTPS_PROXY" not in params.env
        yield object(), object()
    class Session:
        def __init__(self, *args): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def initialize(self): pass
        async def call_tool(self, name, arguments):
            assert name == "pyats_run_show_command" and arguments == ARGUMENTS
            return SimpleNamespace(is_error=False, structured_content={"fixture": "evidence"})
    import mcp
    import mcp.client.stdio
    monkeypatch.setattr(mcp.client.stdio, "stdio_client", capture)
    monkeypatch.setattr(mcp, "ClientSession", Session)
    assert asyncio.run(runtime.invoke_pyats(config, ARGUMENTS, operation)) == {"fixture": "evidence"}
    assert len(launched) == 1


def endpoint_fixture():
    server, trace = fake_pyats()
    device = server._load_testbed().devices["fixture-router"]
    device.connections = {"cli": {"protocol": "ssh", "ip": "192.0.2.171", "port": 22}}
    endpoint = {"device_name": "fixture-router", "os": "iosxe", "protocol": "ssh",
                "host": "192.0.2.171", "port": 22, "connection": "cli"}
    return server, device, trace, hashlib.sha256(canonical(endpoint)).hexdigest()


@pytest.mark.parametrize("key,value", [("ip", "192.0.2.172"), ("port", 2222),
    ("protocol", "telnet"), ("ip", "router.example"), ("proxy", "other-router"),
    ("command", "ssh -W attacker.example:22"), ("via", "other")])
def test_resolved_endpoint_change_refuses_before_connect(tmp_path, key, value):
    server, device, trace, digest = endpoint_fixture()
    device.connections["cli"][key] = value
    with pytest.raises(pyats_module().ProtectedPyatsRefused):
        pyats_module().execute_once(server, ARGUMENTS, logfile=tmp_path / "device.log", endpoint_sha256=digest)
    assert trace["connect"] == [] and trace["execute"] == []


def test_resolved_endpoint_binding_selects_exact_connection(tmp_path):
    server, _, trace, digest = endpoint_fixture()
    result = pyats_module().execute_once(server, ARGUMENTS, logfile=tmp_path / "device.log", endpoint_sha256=digest)
    assert result["execute_calls"] == 1 and trace["connect"][0]["via"] == "cli"


@pytest.mark.parametrize("field,value", [
    ("ssh_options", "-oProxyCommand=ssh other.example -W %h:%p"),
    ("arguments", {"init_exec_commands": ["show running-config"]}),
    ("class", "unreviewed.Connection"),
])
def test_unreviewed_connection_hooks_cannot_hide_behind_same_endpoint(tmp_path, field, value):
    server, device, trace, digest = endpoint_fixture()
    device.connections["cli"][field] = value
    with pytest.raises(pyats_module().ProtectedPyatsRefused):
        pyats_module().execute_once(server, ARGUMENTS, logfile=tmp_path / "device.log", endpoint_sha256=digest)
    assert trace["connect"] == [] and trace["execute"] == []


def test_known_host_bytes_are_part_of_resolved_endpoint_before_connect(tmp_path):
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_bytes(b"fixture reviewed public host key\n")
    known_hosts.chmod(0o600)
    server, device, trace, _ = endpoint_fixture()
    device.connections = strict_document(known_hosts)["devices"]["fixture-router"]["connections"]
    expected = {"device_name": "fixture-router", "os": "iosxe", "protocol": "ssh",
        "host": "192.0.2.171", "port": 22, "connection": "cli", "host_key_policy": "strict",
        "known_hosts_sha256": hashlib.sha256(known_hosts.read_bytes()).hexdigest()}
    assert pyats_module().endpoint_identity("fixture-router", device) == expected
    digest = hashlib.sha256(canonical(expected)).hexdigest()
    known_hosts.write_bytes(b"fixture substituted public host key\n")
    with pytest.raises(pyats_module().ProtectedPyatsRefused):
        pyats_module().execute_once(server, ARGUMENTS, logfile=tmp_path / "device.log", endpoint_sha256=digest)
    assert trace["connect"] == [] and trace["execute"] == []


@pytest.mark.parametrize("change", [
    lambda d: d.update(extends="unreviewed.yaml"),
    lambda d: d["devices"].update(other={"os": "iosxe"}),
    lambda d: d["devices"]["fixture-router"].update(custom={"connection_args": {"mit": True}}),
    lambda d: d["devices"]["fixture-router"]["connections"]["defaults"].update(arguments={"mit": True}),
    lambda d: d["devices"]["fixture-router"]["connections"]["defaults"].update({"class": "unreviewed.Connection"}),
    lambda d: d["devices"]["fixture-router"]["connections"]["cli"].update(credentials={"default": "other"}),
    lambda d: d["devices"]["fixture-router"]["connections"]["cli"].pop("ssh_options"),
    lambda d: d["testbed"]["credentials"]["default"].update(password="inline-secret-is-refused"),
])
def test_minimal_document_rejects_inheritance_hooks_unscoped_credentials(tmp_path, change):
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_bytes(b"fixture public key\n")
    known_hosts.chmod(0o600)
    document = strict_document(known_hosts)
    pyats_module().validate_document(copy.deepcopy(document), "fixture-router")
    change(document)
    with pytest.raises(pyats_module().ProtectedPyatsRefused):
        pyats_module().validate_document(document, "fixture-router")


@pytest.mark.parametrize("raw", [b'{"model":"a","model":"b"}',
    b'{"messages":[{"content":"a","content":"b"}]}', b'{"temperature":NaN}',
    b'{"temperature":Infinity}', b'{"temperature":1e999}', b'{"messages":"\xff"}'])
def test_inference_body_rejects_ambiguous_nonfinite_and_invalid_utf8(raw):
    with pytest.raises(runtime_module().RuntimeRefused):
        docker_module().strict_inference_json(raw)
