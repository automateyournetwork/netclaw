"""n2n_task_wait polls GET /n2n/tasks/{id} until a stored terminal state. No network."""

import asyncio
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

SERVER = Path(__file__).resolve().parents[2] / "mcp-servers" / "n2n-mcp" / "server.py"


def _load():
    spec = importlib.util.spec_from_file_location("n2n_mcp_server_181", SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture(scope="module")
def n2n_module():
    return _load()


@pytest.fixture
def n2n(n2n_module, monkeypatch):
    monkeypatch.setenv("NETCLAW_FEDERATION_JSON", "1")
    clock = _Clock()
    monkeypatch.setattr(n2n_module.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(n2n_module.asyncio, "sleep", clock.sleep)
    return n2n_module, clock


def _patch_get(module, monkeypatch, payloads):
    """Each item is a body (HTTP 200), a (status, body) tuple, or an exception."""
    calls = []

    async def fake_get(path):
        calls.append(path)
        item = payloads[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        if isinstance(item, tuple):
            return item
        return 200, item

    async def refuse(*_args, **_kwargs):
        raise AssertionError("n2n_task_wait must read the status code, not _get")

    monkeypatch.setattr(module, "_get_with_status", fake_get)
    monkeypatch.setattr(module, "_get", refuse)
    return calls


def _run(module, *args, **kwargs):
    return json.loads(asyncio.run(module.n2n_task_wait(*args, **kwargs)))


def test_terminal_at_once(n2n, monkeypatch):
    module, clock = n2n
    calls = _patch_get(module, monkeypatch, [{
        "task_id": "task-1", "state": "completed", "progress": "done", "output_text": "ok",
    }])
    body = _run(module, "task-1")
    assert body["state"] == "completed"
    assert body["progress"] == "done"
    assert body["output_text"] == "ok"
    assert "still_running" not in body
    assert clock.sleeps == []
    assert calls == ["/n2n/tasks/task-1"]


@pytest.mark.parametrize("state", ["completed", "failed", "cancelled", "outcome_unknown", "interrupted"])
def test_each_stored_terminal_state_returns_immediately(n2n, monkeypatch, state):
    module, clock = n2n
    _patch_get(module, monkeypatch, [{"task_id": "t", "state": state}])
    body = _run(module, "t")
    assert body == {"task_id": "t", "state": state}
    assert clock.sleeps == []


def test_working_then_completed(n2n, monkeypatch):
    module, clock = n2n
    calls = _patch_get(module, monkeypatch, [
        {"task_id": "t", "state": "working", "progress": "1/2"},
        {"task_id": "t", "state": "completed", "progress": "2/2"},
    ])
    body = _run(module, "t")
    assert body["state"] == "completed"
    assert body["progress"] == "2/2"
    assert "still_running" not in body
    assert clock.sleeps == [5.0]
    assert calls == ["/n2n/tasks/t", "/n2n/tasks/t"]


@pytest.mark.parametrize("state", ["working", "submitted"])
def test_open_state_ends_the_slice_with_still_running(n2n, monkeypatch, state):
    module, clock = n2n
    calls = _patch_get(module, monkeypatch, [
        {"task_id": "t", "state": state, "progress": "nodes 1/4"},
        {"task_id": "t", "state": state, "progress": "nodes 1/4"},
    ])
    body = _run(module, "t", timeout_seconds=10, poll_interval_seconds=15)
    assert body["state"] == state
    assert body["progress"] == "nodes 1/4"
    assert body["still_running"] is True
    assert body["hint"] == module._TASK_WAIT_HINT
    assert clock.sleeps == [10.0]
    assert clock.now == 10.0
    assert len(calls) == 2


def test_free_text_does_not_count_as_terminal(n2n, monkeypatch):
    module, clock = n2n
    _patch_get(module, monkeypatch, [
        {
            "task_id": "t",
            "state": "working",
            "status": "completed",
            "result": "task completed successfully",
        },
        {
            "task_id": "t",
            "state": "working",
            "status": "completed",
            "result": "task completed successfully",
        },
    ])
    body = _run(module, "t", timeout_seconds=10, poll_interval_seconds=15)
    assert body["state"] == "working"
    assert body["still_running"] is True
    assert clock.sleeps == [10.0]


def test_daemon_404_returns_not_found_at_once(n2n, monkeypatch):
    # bgp-daemon-v2 answers a missing or purged task with 404 {"error": "unknown task"}.
    module, clock = n2n
    calls = _patch_get(module, monkeypatch, [(404, {"error": "unknown task"})])
    body = _run(module, "gone-1")
    assert body["not_found"] is True
    assert body["task_id"] == "gone-1"
    assert body["error"] == "unknown task"
    assert body["hint"] == module._TASK_NOT_FOUND_HINT
    assert "still_running" not in body
    assert "state" not in body
    assert clock.sleeps == []
    assert calls == ["/n2n/tasks/gone-1"]


def test_peer_state_unknown_returns_not_found_at_once(n2n, monkeypatch):
    # tasks.py status() answers {"task_id", "state": "unknown"} for a missing or unowned task.
    module, clock = n2n
    _patch_get(module, monkeypatch, [{"task_id": "t", "state": "unknown"}])
    body = _run(module, "t")
    assert body["state"] == "unknown"
    assert body["not_found"] is True
    assert "still_running" not in body
    assert clock.sleeps == []


@pytest.mark.parametrize("status", [500, 502, 503, 403, 409])
def test_non_2xx_other_than_404_is_a_retryable_error(n2n, monkeypatch, status):
    module, clock = n2n
    _patch_get(module, monkeypatch, [(status, {"error": "daemon busy"})])
    body = _run(module, "t")
    assert body["state"] == "error"
    assert body["http_status"] == status
    assert body["error"] == "daemon busy"
    assert body["task_id"] == "t"
    assert body["hint"] == module._TASK_ERROR_HINT
    assert "not_found" not in body
    assert "still_running" not in body
    assert clock.sleeps == []


def test_non_2xx_without_a_json_body_reports_the_status(n2n, monkeypatch):
    module, _clock = n2n
    _patch_get(module, monkeypatch, [(500, None)])
    body = _run(module, "t")
    assert body == {
        "task_id": "t", "state": "error", "http_status": 500,
        "error": "HTTP 500", "hint": module._TASK_ERROR_HINT,
    }


def test_404_with_state_unknown_is_not_found_too(n2n, monkeypatch):
    module, _clock = n2n
    _patch_get(module, monkeypatch, [(404, {"task_id": "t", "state": "unknown"})])
    body = _run(module, "t")
    assert body["not_found"] is True
    assert body["state"] == "unknown"


@pytest.mark.parametrize("payload", [
    {"error": "unknown task"},
    {"task_id": "t", "state": {"status": "completed"}},
    {"task_id": "t", "state": None},
    {"task_id": "t", "progress": "1/2"},
    ["not", "a", "dict"],
])
def test_2xx_without_string_state_is_a_retryable_error(n2n, monkeypatch, payload):
    module, clock = n2n
    _patch_get(module, monkeypatch, [payload])
    body = _run(module, "t")
    assert body["state"] == "error"
    assert body["http_status"] == 200
    assert body["response"] == payload
    assert body["task_id"] == "t"
    assert "not_found" not in body
    assert "still_running" not in body
    assert clock.sleeps == []


def test_error_beside_an_open_state_keeps_waiting(n2n, monkeypatch):
    module, _clock = n2n
    _patch_get(module, monkeypatch, [
        {"task_id": "t", "state": "working", "error": "transient"},
        {"task_id": "t", "state": "completed"},
    ])
    body = _run(module, "t")
    assert body == {"task_id": "t", "state": "completed"}


def _mock_daemon(module, monkeypatch, status, body):
    real_client = httpx.AsyncClient

    def handler(request):
        assert request.url.path == "/n2n/tasks/t"
        if body is None:
            return httpx.Response(status, text="<html>bad gateway</html>")
        return httpx.Response(status, json=body)

    def client(**kwargs):
        kwargs.pop("timeout", None)
        return real_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.delenv("NETCLAW_FEDERATION_SCOPED", raising=False)
    monkeypatch.setattr(module.httpx, "AsyncClient", client)


@pytest.mark.parametrize("status,body,expected", [
    (404, {"error": "unknown task"}, "not_found"),
    (500, {"error": "database is locked"}, "error"),
    (502, None, "error"),
])
def test_status_code_is_read_from_the_daemon_response(n2n_module, monkeypatch, status, body, expected):
    monkeypatch.setenv("NETCLAW_FEDERATION_JSON", "1")
    _mock_daemon(n2n_module, monkeypatch, status, body)
    got = json.loads(asyncio.run(n2n_module.n2n_task_wait("t")))
    if expected == "not_found":
        assert got["not_found"] is True
        assert got["error"] == "unknown task"
        assert "still_running" not in got
    else:
        assert got["state"] == "error"
        assert got["http_status"] == status
        assert "not_found" not in got


def test_task_status_and_result_still_use_get(n2n_module, monkeypatch):
    monkeypatch.setenv("NETCLAW_FEDERATION_JSON", "1")
    _mock_daemon(n2n_module, monkeypatch, 404, {"error": "unknown task"})
    assert json.loads(asyncio.run(n2n_module.n2n_task_status("t"))) == {"error": "unknown task"}


def test_scoped_refusal_is_a_retryable_error(n2n, monkeypatch):
    module, _clock = n2n
    request = httpx.Request("POST", "http://127.0.0.1:1/effect")
    response = httpx.Response(403, json={"error": "execution refused"}, request=request)

    async def refuse(method, path, body):
        raise httpx.HTTPStatusError("refused", request=request, response=response)

    monkeypatch.setenv("NETCLAW_FEDERATION_SCOPED", "1")
    monkeypatch.setattr(module, "_scoped", refuse)
    body = _run(module, "t")
    assert body["state"] == "error"
    assert body["http_status"] == 403
    assert body["error"] == "execution refused"
    assert "not_found" not in body


def test_get_error_returns_error_payload(n2n, monkeypatch):
    module, clock = n2n
    _patch_get(module, monkeypatch, [RuntimeError("daemon down")])
    body = _run(module, "task-9")
    assert body == {"task_id": "task-9", "state": "error", "error": "daemon down"}
    assert clock.sleeps == []


def test_low_bounds_are_clamped(n2n, monkeypatch):
    module, clock = n2n
    _patch_get(module, monkeypatch, [
        {"task_id": "t", "state": "working"},
        {"task_id": "t", "state": "completed"},
    ])
    body = _run(module, "t", timeout_seconds=3, poll_interval_seconds=0.5)
    assert body["state"] == "completed"
    assert clock.sleeps == [2.0]


def test_high_bounds_are_clamped(n2n, monkeypatch):
    module, clock = n2n
    _patch_get(module, monkeypatch, [{"task_id": "t", "state": "working"}] * 8)
    body = _run(module, "t", timeout_seconds=90, poll_interval_seconds=30)
    assert body["still_running"] is True
    assert body["state"] == "working"
    assert clock.sleeps == [15.0, 15.0, 15.0, 5.0]
    assert clock.now == 50.0
