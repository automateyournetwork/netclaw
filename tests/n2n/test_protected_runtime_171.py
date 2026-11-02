"""Adversarial synthetic runtime checks; no container, provider or device calls."""

import asyncio
import copy
import hashlib
from types import SimpleNamespace

import pytest

from protected_support_171 import NOW, approval, identity, module, runtime_module, pyats_module


@pytest.fixture
def payload():
    return approval(identity("border"), identity("member"))


def request(payload, text="fixture proposal"):
    return {"model": payload["model_profile"]["model"], "messages": [{"role": "user", "content": text}]}


@pytest.fixture
def inference(tmp_path, payload):
    runtime = runtime_module()
    fence = runtime.InferenceFence(tmp_path / "private" / "inference.db")
    forwarded, completed = [], [False]
    async def forward(body):
        forwarded.append(copy.deepcopy(body))
        return {"id": "fixture-response", "choices": []}
    facade = runtime.ScopedInference(payload, "fixture-operation-token", fence, forward,
        tool_finished=lambda: completed[0], clock_ms=lambda: NOW)
    yield runtime, facade, fence, forwarded, completed
    fence.close()


def call(facade, body, *, method="POST", path="/v1/chat/completions", headers=None):
    headers = headers if headers is not None else {"authorization": "Bearer fixture-operation-token"}
    return asyncio.run(facade.invoke(method, path, headers, body))


@pytest.mark.parametrize("method,path", [("GET", "/v1/chat/completions"),
    ("CONNECT", "api.anthropic.com:443"), ("POST", "/v1/responses"),
    ("POST", "/v1/chat/completions?target=https://attacker.example"),
    ("POST", "http://attacker.example/v1/chat/completions")])
def test_inference_only_exposes_exact_guarded_route(inference, payload, method, path):
    runtime, facade, fence, forwarded, _ = inference
    with pytest.raises(runtime.RuntimeRefused):
        call(facade, request(payload), method=method, path=path)
    assert forwarded == [] and fence.count(payload["operation_id"]) == 0


@pytest.mark.parametrize("auth", [None, "", "Bearer wrong", "Basic fixture-operation-token"])
def test_inference_missing_or_foreign_capability_never_forwards(inference, payload, auth):
    runtime, facade, fence, forwarded, _ = inference
    with pytest.raises(runtime.RuntimeRefused):
        call(facade, request(payload), headers={} if auth is None else {"authorization": auth})
    assert forwarded == [] and fence.count(payload["operation_id"]) == 0


def test_untrusted_routing_headers_do_not_reach_fixed_forwarder(inference, payload):
    _, facade, _, forwarded, _ = inference
    headers = {"authorization": "Bearer fixture-operation-token", "x-dc-auth": "stolen-guard-token",
               "x-dc-target-url": "https://attacker.example", "x-ai-auth": "Bearer attacker-key",
               "x-api-key": "attacker-key", "forwarded": "host=attacker.example"}
    body = request(payload)
    body.update(stream=True, stream_options={"include_usage": True}, parallel_tool_calls=True)
    call(facade, body, headers=headers)
    assert len(forwarded) == 1
    assert forwarded[0]["stream"] is False
    assert forwarded[0]["parallel_tool_calls"] is False
    assert "stream_options" not in forwarded[0]
    assert "attacker" not in str(forwarded)


@pytest.mark.parametrize("mutate", [lambda b: b.update(model="unapproved-model"),
    lambda b: b.update(base_url="https://attacker.example"),
    lambda b: b.update(api_key="attacker-key"), lambda b: b.update(messages="not-a-list")])
def test_changed_model_and_hidden_route_parameters_are_refused(inference, payload, mutate):
    runtime, facade, fence, forwarded, _ = inference
    body = request(payload)
    mutate(body)
    with pytest.raises(runtime.RuntimeRefused):
        call(facade, body)
    assert forwarded == [] and fence.count(payload["operation_id"]) == 0


def test_second_model_call_requires_actual_tool_evidence_and_third_is_refused(inference, payload):
    runtime, facade, fence, forwarded, completed = inference
    call(facade, request(payload))
    with pytest.raises(runtime.RuntimeRefused):
        call(facade, request(payload, "premature summary"))
    assert len(forwarded) == 1
    completed[0] = True
    call(facade, request(payload, "completed tool summary"))
    with pytest.raises(runtime.RuntimeRefused):
        call(facade, request(payload, "extra call"))
    assert len(forwarded) == 2 and fence.count(payload["operation_id"]) == 2


def test_lost_inference_reply_cannot_be_replayed_after_reopen(tmp_path, payload):
    runtime = runtime_module()
    path = tmp_path / "private" / "inference.db"
    fence = runtime.InferenceFence(path)
    forwards = []
    async def lost_reply(body):
        forwards.append(body)
        raise ConnectionError("fixture response lost after upstream admission")
    facade = runtime.ScopedInference(payload, "fixture-operation-token", fence, lost_reply, clock_ms=lambda: NOW)
    with pytest.raises(runtime.RuntimeUnknown):
        call(facade, request(payload))
    fence.close()
    fence = runtime.InferenceFence(path)
    facade = runtime.ScopedInference(payload, "fixture-operation-token", fence, lost_reply,
        tool_finished=lambda: True, clock_ms=lambda: NOW)
    try:
        for body in [request(payload), request(payload, "changed retry")]:
            with pytest.raises(runtime.RuntimeRefused):
                call(facade, body)
        assert len(forwards) == 1 and fence.count(payload["operation_id"]) == 1
    finally:
        fence.close()


def test_expired_inference_never_claims_or_forwards(inference, payload):
    runtime, facade, fence, forwarded, _ = inference
    facade.clock_ms = lambda: payload["limits"]["expires_at_ms"]
    with pytest.raises(runtime.RuntimeRefused):
        call(facade, request(payload))
    assert forwarded == [] and fence.count(payload["operation_id"]) == 0


def test_signed_inference_deadline_bounds_full_forward_without_replay(inference, payload):
    runtime, facade, fence, forwarded, _ = inference
    payload["limits"]["inference_timeout_ms"] = 10
    cancelled = []
    async def stalled(body):
        forwarded.append(body)
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.append(True)
    facade.forward = stalled
    async def run():
        task = asyncio.create_task(facade.invoke("POST", "/v1/chat/completions",
            {"authorization": "Bearer fixture-operation-token"}, request(payload)))
        done, pending = await asyncio.wait({task}, timeout=0.5)
        if pending:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            pytest.fail("signed inference deadline was not enforced by the runtime")
        return await task
    with pytest.raises(runtime.RuntimeUnknown):
        asyncio.run(run())
    assert cancelled == [True] and len(forwarded) == 1
    assert fence.count(payload["operation_id"]) == 1
    with pytest.raises(runtime.RuntimeRefused):
        call(facade, request(payload, "retry after full forward deadline"))
    assert len(forwarded) == 1


def test_broker_wraps_exact_effect_and_retains_actual_result(payload):
    runtime = runtime_module()
    calls, order = [], []
    result = {"raw_output": "fixture observed output"}
    async def invoke(tool, args):
        calls.append((tool, copy.deepcopy(args)))
        order.append("effect")
        return result
    async def gate(proposed, execute):
        assert proposed == payload["tool_call"]
        order.append("gate")
        return await execute()
    broker = runtime.ExactToolBroker(payload, gate, invoke)
    actual = asyncio.run(broker.call(payload["tool_call"]["tool"], payload["tool_call"]["arguments"]))
    assert actual == result and broker.evidence == result
    assert order == ["gate", "effect"] and len(calls) == 1
    with pytest.raises(runtime.RuntimeRefused):
        asyncio.run(broker.call(payload["tool_call"]["tool"], payload["tool_call"]["arguments"]))
    assert len(calls) == 1


@pytest.mark.parametrize("changed", ["device", "command", "retry", "timeout", "extra", "tool"])
def test_broker_rejects_scope_substitution_before_gate(payload, changed):
    runtime = runtime_module()
    called = []
    async def forbidden(*args):
        called.append(True)
        raise AssertionError("must not reach gate or integration")
    broker = runtime.ExactToolBroker(payload, forbidden, forbidden)
    arguments = copy.deepcopy(payload["tool_call"]["arguments"])
    tool = payload["tool_call"]["tool"]
    if changed == "device": arguments["device_name"] = "another-router"
    elif changed == "command": arguments["command"] = "show running-config"
    elif changed == "retry": arguments["retries"] = 2
    elif changed == "timeout": arguments["timeout"] = 120
    elif changed == "extra": arguments["shell"] = "sh"
    else: tool = "pyats_configure_device"
    with pytest.raises(runtime.RuntimeRefused):
        asyncio.run(broker.call(tool, arguments))
    assert called == []


def fake_pyats(*, parse_failure=False, execute_failure=False):
    trace = {"execute": [], "parse": [], "connect": [], "disconnect": []}
    class Device:
        os = "iosxe"
        def is_connected(self): return False
        def execute(self, command, **kwargs):
            trace["execute"].append((command, kwargs))
            if execute_failure: raise TimeoutError("fixture uncertain device command")
            return "Cisco IOS XE Software, Version fixture\n"
        def parse(self, command, **kwargs):
            trace["parse"].append((command, kwargs))
            if parse_failure: raise ValueError("fixture parser unavailable")
            return {"version": {"version": "fixture"}}
    device = Device()
    server = SimpleNamespace(_CONN_CACHE_TTL=0)
    server._load_testbed = lambda: SimpleNamespace(devices={"fixture-router": device})
    server._get_testbed_connection_args = lambda _: {"init_config_commands": ["unsafe fixture init"]}
    def get_device(name):
        chosen = server._load_testbed().devices[name]
        trace["connect"].append(server._get_testbed_connection_args(chosen))
        return chosen
    server._get_device = get_device
    server._disconnect_device = lambda chosen: trace["disconnect"].append(chosen)
    return server, trace


@pytest.mark.parametrize("parse_failure", [False, True])
def test_pyats_parses_captured_output_without_second_execute(tmp_path, payload, parse_failure):
    adapter = pyats_module()
    server, trace = fake_pyats(parse_failure=parse_failure)
    before = server._get_testbed_connection_args
    result = adapter.execute_once(server, payload["tool_call"]["arguments"], logfile=tmp_path / "fixture.log")
    assert len(trace["execute"]) == 1 and len(trace["parse"]) == 1
    assert trace["parse"][0][1] == {"output": result["raw_output"]}
    assert result["parsed"] is (not parse_failure)
    assert result["raw_sha256"] == hashlib.sha256(result["raw_output"].encode()).hexdigest()
    assert trace["connect"][0]["init_config_commands"] == []
    assert trace["connect"][0]["init_exec_commands"] == []
    assert len(trace["disconnect"]) == 1
    assert server._get_testbed_connection_args is before


def test_pyats_timeout_does_not_retry_or_parse(tmp_path, payload):
    adapter = pyats_module()
    server, trace = fake_pyats(execute_failure=True)
    with pytest.raises(TimeoutError):
        adapter.execute_once(server, payload["tool_call"]["arguments"], logfile=tmp_path / "fixture.log")
    assert len(trace["execute"]) == 1 and trace["parse"] == []
    assert len(trace["disconnect"]) == 1


def test_pyats_refused_final_gate_runs_no_command(tmp_path, payload):
    adapter = pyats_module()
    server, trace = fake_pyats()
    def refused(): raise PermissionError("fixture authority revoked before effect")
    with pytest.raises(PermissionError):
        adapter.execute_once(server, payload["tool_call"]["arguments"],
            logfile=tmp_path / "fixture.log", before_execute=refused)
    assert trace["execute"] == [] and trace["parse"] == []


@pytest.mark.parametrize("key,value", [("device_name", "unknown-device"),
    ("command", "show version; configure terminal"), ("retries", 2), ("timeout", True)])
def test_pyats_unknown_device_or_unqualified_arguments_never_connect(tmp_path, payload, key, value):
    adapter = pyats_module()
    server, trace = fake_pyats()
    arguments = {**payload["tool_call"]["arguments"], key: value}
    with pytest.raises(adapter.ProtectedPyatsRefused):
        adapter.execute_once(server, arguments, logfile=tmp_path / "fixture.log")
    assert trace["connect"] == [] and trace["execute"] == []


@pytest.mark.parametrize("method,args", [
    ("delegate_to_member", ("fixture/member", "pyats", "show version")),
    ("_in2n_member_submit", (None, {"skill": "pyats", "input": "show version"})),
    ("_edge_on_ask", (None, {"input": "show version"})),
])
def test_direct_legacy_entrypoints_refuse_before_accessing_runtime(method, args):
    service_type = module("service").FederationService
    service = service_type.__new__(service_type)
    service.protected_enabled = True
    # Deliberately no runtime/manager/invoker: this gate must precede all legacy use.
    with pytest.raises(module("channel").RpcError):
        asyncio.run(getattr(service, method)(*args))
