"""Adversarial inspection fixtures and loopback relay framing; not live posture."""

import copy
import http.client
from http.server import ThreadingHTTPServer
import json
import threading

import pytest

from protected_support_171 import docker_module, relay_module, runtime_module


def inspected():
    image = "sha256:" + "1" * 64
    network = {"Name": "fixture-agent-only", "Id": "2" * 64, "Internal": True,
        "EnableIPv6": False, "Options": {"com.docker.network.bridge.gateway_mode_ipv4": "isolated"}}
    container = {"Image": image, "Config": {"User": "10001", "Env": ["HOME=/home/agent",
        "PATH=/usr/local/bin:/usr/bin:/bin", "NETCLAW_OPERATION_TOKEN=fixture-scoped-token"]},
        "HostConfig": {"ReadonlyRootfs": True, "Privileged": False, "CapDrop": ["ALL"], "CapAdd": [],
            "SecurityOpt": ["no-new-privileges"], "PidMode": "", "IpcMode": "private",
            "Devices": [], "PortBindings": {}, "Memory": 2 * 1024 ** 3, "PidsLimit": 128,
            "NanoCpus": 10 ** 9, "NetworkMode": network["Name"],
            "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=128m", "/home/agent": "rw,noexec,nosuid,size=128m,uid=10001,gid=10001,mode=700"}},
        "NetworkSettings": {"Networks": {network["Name"]: {"NetworkID": network["Id"]}}},
        "Mounts": [{"Type": "bind", "Destination": "/config/openclaw.json", "Source": "/fixture/openclaw.json", "RW": False}]}
    return container, network, image, {"/config/openclaw.json": "/fixture/openclaw.json"}


def check(container, network, image, mounts):
    return docker_module().inspect_agent(container, network, image=image, mounts=mounts, uid=10001, gid=10001)


def test_conforming_inspection_fixture_is_accepted():
    container, network, image, mounts = inspected()
    assert check(container, network, image, mounts)["read_only"] is True


@pytest.mark.parametrize("user", ["0", "root", "0:0", "0:10001", "root:root", "root:10001"])
def test_root_user_spellings_are_refused(user):
    container, network, image, mounts = inspected()
    container["Config"]["User"] = user
    with pytest.raises(runtime_module().RuntimeRefused):
        check(container, network, image, mounts)


@pytest.mark.parametrize("field,value", [("Privileged", True), ("ReadonlyRootfs", False),
    ("CapAdd", ["NET_ADMIN"]), ("PidMode", "host"), ("IpcMode", "host"),
    ("Memory", 0), ("PidsLimit", -1), ("NanoCpus", 0),
    ("SecurityOpt", ["no-new-privileges", "seccomp=unconfined"]),
    ("SecurityOpt", ["no-new-privileges", "apparmor=unconfined"])])
def test_security_configuration_cannot_be_weakened(field, value):
    container, network, image, mounts = inspected()
    container["HostConfig"][field] = value
    with pytest.raises(runtime_module().RuntimeRefused):
        check(container, network, image, mounts)


@pytest.mark.parametrize("mutation", [
    lambda c, n: c["Config"]["Env"].append("ANTHROPIC_API_KEY=fixture-forbidden-secret"),
    lambda c, n: c["Mounts"].append({"Type": "bind", "Destination": "/var/run/docker.sock", "Source": "/var/run/docker.sock", "RW": False}),
    lambda c, n: c["Mounts"][0].update(RW=True),
    lambda c, n: c["NetworkSettings"]["Networks"].update(egress={}),
    lambda c, n: n.update(Internal=False),
    lambda c, n: n.update(EnableIPv6=True),
    lambda c, n: n["Options"].update({"com.docker.network.bridge.gateway_mode_ipv4": "nat"}),
])
def test_credential_mount_and_network_bypasses_are_refused(mutation):
    container, network, image, mounts = inspected()
    mutation(container, network)
    with pytest.raises(runtime_module().RuntimeRefused):
        check(container, network, image, mounts)


@pytest.fixture
def relay(monkeypatch):
    implementation = relay_module()
    original_connection = http.client.HTTPConnection
    forwarded = []
    class Reply:
        status = 200
        def read(self, bound): return b'{"fixture":true}'
        def getheader(self, name, default): return "application/json"
    class FixedUpstream:
        def __init__(self, host, port, timeout):
            self.host, self.port = host, port
        def request(self, method, path, body, headers):
            forwarded.append({"host": self.host, "port": self.port, "method": method,
                "path": path, "body": body, "headers": copy.deepcopy(headers)})
        def getresponse(self): return Reply()
        def close(self): pass
    monkeypatch.setattr(implementation, "PORT", 41001, raising=False)
    monkeypatch.setattr(implementation.http.client, "HTTPConnection", FixedUpstream)
    server = ThreadingHTTPServer(("127.0.0.1", 0), implementation.Relay)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    def send(path="/v1/chat/completions", *, headers=None, method="POST", body=b"{}"):
        conn = original_connection("127.0.0.1", server.server_port, timeout=3)
        conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
        for key, value in (headers or [("Content-Type", "application/json"), ("Content-Length", str(len(body))) ]):
            conn.putheader(key, value)
        conn.endheaders(body)
        response = conn.getresponse()
        result = response.status, response.read()
        conn.close()
        return result
    yield send, forwarded
    server.shutdown()
    server.server_close()
    thread.join(timeout=3)


def test_relay_fixes_upstream_and_strips_routing_headers(relay):
    send, forwarded = relay
    status, _ = send(headers=[("Content-Type", "application/json"), ("Content-Length", "2"),
        ("Host", "attacker.example"), ("Authorization", "Bearer fixture-capability"),
        ("X-DC-Target-URL", "https://attacker.example"), ("X-AI-Auth", "Bearer attacker"),
        ("X-DC-Auth", "guard-secret"), ("Forwarded", "host=attacker.example")])
    assert status == 200 and len(forwarded) == 1
    assert forwarded[0]["host"] == "host.docker.internal" and forwarded[0]["port"] == 41001
    assert set(forwarded[0]["headers"]) <= {"authorization", "content-type", "accept", "mcp-protocol-version", "Host"}
    assert "attacker" not in str(forwarded) and "guard-secret" not in str(forwarded)


@pytest.mark.parametrize("headers", [
    [("Content-Type", "application/json"), ("Content-Length", "2"), ("Content-Length", "2")],
    [("Content-Type", "application/json"), ("Content-Length", "2"), ("Transfer-Encoding", "chunked")],
    [("Content-Type", "application/json"), ("Content-Length", "1048577")],
    [("Content-Type", "application/json"), ("Content-Length", "-1")],
    [("Content-Type", "application/json"), ("Content-Length", "2"), ("Authorization", "Bearer a"), ("Authorization", "Bearer b")],
    [("Content-Type", "text/plain"), ("Content-Length", "2")],
])
def test_relay_rejects_ambiguous_or_oversized_framing(relay, headers):
    send, forwarded = relay
    status, _ = send(headers=headers)
    assert status in (400, 413, 415) and forwarded == []


@pytest.mark.parametrize("path", ["/v1/responses", "/mcp?target=http://attacker.example", "/admin", "http://attacker.example/mcp"])
def test_relay_has_no_generic_proxy_route(relay, path):
    send, forwarded = relay
    assert send(path)[0] == 404 and forwarded == []
