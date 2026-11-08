"""n2n_task_wait polls GET /n2n/tasks/{id} until a stored terminal state. No network."""

import asyncio
import importlib.util
import json
from pathlib import Path

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
    calls = []

    async def fake_get(path, params=None):
        calls.append(path)
        item = payloads[len(calls) - 1]
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(module, "_get", fake_get)
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


@pytest.mark.parametrize("state", ["working", "submitted", "unknown"])
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


def test_non_string_state_is_not_terminal(n2n, monkeypatch):
    module, _clock = n2n
    _patch_get(module, monkeypatch, [
        {"task_id": "t", "state": {"status": "completed"}},
        {"task_id": "t", "state": {"status": "completed"}},
    ])
    body = _run(module, "t", timeout_seconds=10, poll_interval_seconds=15)
    assert body["state"] == {"status": "completed"}
    assert body["still_running"] is True


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
