import json
import os
import stat
import time

import pytest

import result_retention as rr
from conftest import interface_table


def test_roundtrip_and_hash():
    p = interface_table()
    meta = rr.retain(p, tool="t", device="r1", command="show ip interface brief")
    m2, back = rr.load(meta["handle"])
    assert back == p
    assert m2["source_sha256"] == meta["source_sha256"] == m2["retained_sha256"]
    assert not m2["retention_truncated"]


def test_fixture_is_over_170kb():
    assert len(json.dumps(interface_table())) > 170_000


def test_private_permissions(store):
    meta = rr.retain({"a": [1, 2]}, tool="t")
    assert stat.S_IMODE(os.stat(store).st_mode) == 0o700
    assert stat.S_IMODE(os.stat(store / f"{meta['handle']}.json").st_mode) == 0o600


@pytest.mark.parametrize("bad", ["../etc/passwd", "r_zz", "", "r_" + "a" * 31, "r_" + "a" * 33,
                                 "R_" + "a" * 32, None, "r_" + "a" * 32 + "/../x"])
def test_malformed_handles_rejected(bad):
    with pytest.raises(rr.HandleError):
        rr.load(bad)


def test_unknown_handle_explicit():
    with pytest.raises(rr.HandleError, match="unknown"):
        rr.load("r_" + "0" * 32)


def test_ttl_expiry(monkeypatch):
    monkeypatch.setenv("NETCLAW_RESULT_TTL_SECONDS", "1")
    meta = rr.retain("x\ny", tool="t")
    time.sleep(1.2)
    with pytest.raises(rr.HandleError, match="expired|unknown"):
        rr.load(meta["handle"])


def test_tamper_detected(store):
    meta = rr.retain({"a": [1]}, tool="t")
    f = store / f"{meta['handle']}.json"
    doc = json.loads(f.read_text())
    doc["payload"] = {"a": [1, 2, 3]}
    f.write_text(json.dumps(doc))
    with pytest.raises(rr.HandleError, match="integrity"):
        rr.load(meta["handle"])


def test_retention_cap_text_marks_truncated(monkeypatch):
    monkeypatch.setenv("NETCLAW_RESULT_MAX_BYTES", "1000")
    meta = rr.retain("\n".join(f"line {i}" for i in range(2000)), tool="t")
    assert meta["retention_truncated"] and meta["retention_truncation"]["kind"] == "text"
    assert meta["source_bytes"] > meta["retained_bytes"]
    _, back = rr.load(meta["handle"])
    assert len(back.encode()) <= 1000


def test_retention_cap_records_marks_truncated(monkeypatch):
    monkeypatch.setenv("NETCLAW_RESULT_MAX_BYTES", "20000")
    meta = rr.retain(interface_table(), tool="t")
    t = meta["retention_truncation"]
    assert meta["retention_truncated"] and t["kind"] == "records"
    assert t["records_kept"] < t["records_total"]
    _, back = rr.load(meta["handle"])
    json.dumps(back)  # still valid structure


def test_binary_refused():
    with pytest.raises(rr.RetentionError):
        rr.retain(b"\x00\x01", tool="t")


def test_store_size_eviction(monkeypatch):
    monkeypatch.setenv("NETCLAW_RESULT_STORE_MAX_BYTES", "3000")
    handles = [rr.retain("x" * 1500, tool="t")["handle"] for _ in range(4)]
    live = {h["handle"] for h in rr.list_handles()}
    assert handles[-1] in live and handles[0] not in live


def test_small_result_byte_identical():
    obj = {"status": "completed", "output": "small"}
    rendered = json.dumps(obj, indent=2)
    assert rr.envelope(obj, rendered, tool="t") is rendered


def test_large_result_envelope_bounded_and_honest():
    obj = interface_table()
    out = rr.envelope(obj, json.dumps(obj, indent=2), tool="pyats", device="r1", command="c")
    assert len(out) < rr.inline_budget()
    env = json.loads(out)
    assert env["inline_complete"] is False and env["retained"] is True
    meta, back = rr.load(env["handle"])
    assert back == obj and env["source_sha256"] == meta["source_sha256"]
    assert "NOT the complete result" in env["message"]


def test_retention_failure_is_loud(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("NETCLAW_RESULTS_DIR", str(blocker / "sub"))
    obj = interface_table()
    env = json.loads(rr.envelope(obj, json.dumps(obj, indent=2), tool="t"))
    assert env["retained"] is False and env["handle"] is None
    assert env["inline_complete"] is False and "NOT retained" in env["message"]


def test_bounded_dict_text_output_is_line_searchable():
    res = {"status": "ok", "device": "d", "output": "\n".join(f"row {i}" for i in range(20000))}
    out = rr.bounded_dict(res, tool="run_command", device="d", command="show x")
    assert out["inline_complete"] is False and out["source_fields"]["status"] == "ok"
    meta, payload = rr.load(out["handle"])
    assert meta["kind"] == "text" and payload.count("\n") == 19999


def test_bounded_dict_small_unchanged():
    res = {"status": "ok", "output": "tiny"}
    assert rr.bounded_dict(res, tool="t") is res
