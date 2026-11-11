import json
from pathlib import Path

import pytest

import result_query as q
import result_retention as rr
import result_stream as rs
import server
from conftest import interface_table


def call(tool, **kw):
    fn = getattr(tool, "fn", tool)
    return fn(**kw)


def retain_table(**kw):
    return rr.retain(interface_table(), tool="pyats_run_show_command", device="r1",
                     command="show ip interface brief", **kw)["handle"]


# ---- US1: the issue's acceptance case ----------------------------------------------------

def test_tunnel_counts_exact_over_170kb():
    p = interface_table(300, 120, 1500)
    assert len(json.dumps(p)) > 170_000
    h = rr.retain(p, tool="t", device="r1", command="show ip interface brief")["handle"]
    r = call(server.result_count, handle=h, record_path="output.interface",
             where=[{"field": "_key", "op": "startswith", "value": "Tunnel"}],
             group_by=["status"])
    assert r["count"] == 420
    assert {g["status"]: g["count"] for g in r["groups"]} == {"up": 300,
                                                              "administratively down": 120}
    cov = r["coverage"]
    assert cov["complete"] is True and cov["records_scanned"] == cov["records_total"] == 1920
    assert cov["basis"] == "complete-retained-copy"
    assert cov["source_sha256"] and cov["command"] == "show ip interface brief"


def test_zero_tunnels_is_a_complete_zero():
    h = rr.retain(interface_table(0, 0, 50), tool="t")["handle"]
    r = call(server.result_count, handle=h, record_path="output.interface",
             where=[{"field": "_key", "op": "startswith", "value": "Tunnel"}])
    assert r["count"] == 0 and r["coverage"]["complete"] is True


def test_auto_record_path_picks_largest_collection():
    h = retain_table()
    d = call(server.result_describe, handle=h)
    assert d["record_collections"][0]["path"] == "output.interface"
    assert "status" in d["fields_seen_in_first_500"]


def test_select_pages_and_never_claims_whole():
    h = retain_table()
    r = call(server.result_select, handle=h, record_path="output.interface",
             where=[{"field": "_key", "op": "startswith", "value": "Tunnel"}],
             fields=["_key", "status"], limit=100)
    cov = r["coverage"]
    assert len(r["rows"]) == 100 and cov["records_matched"] == 420
    assert cov["truncated_page"] is True and cov["complete"] is False
    assert cov["next_offset"] == 100
    seen = len(r["rows"])
    off = cov["next_offset"]
    while off is not None:
        r = call(server.result_select, handle=h, record_path="output.interface",
                 where=[{"field": "_key", "op": "startswith", "value": "Tunnel"}],
                 fields=["_key"], offset=off, limit=500)
        seen += len(r["rows"])
        off = r["coverage"]["next_offset"]
    assert seen == 420


def test_response_always_within_budget():
    h = retain_table()
    r = call(server.result_select, handle=h, record_path="output.interface", limit=500)
    assert len(json.dumps(r)) <= q.MAX_RESPONSE_CHARS + 2500  # coverage block included
    assert r["coverage"]["truncated_page"] is True


def test_unknown_and_malformed_handles_explicit_errors():
    for h in ("r_" + "0" * 32, "bogus"):
        r = call(server.result_count, handle=h)
        assert "error" in r and r["complete"] is False and "count" not in r


# ---- US3: incomplete bases are never complete ------------------------------------------

def test_retention_truncated_never_complete(monkeypatch):
    monkeypatch.setenv("NETCLAW_RESULT_MAX_BYTES", "30000")
    h = retain_table()
    r = call(server.result_count, handle=h, record_path="output.interface")
    cov = r["coverage"]
    assert cov["complete"] is False and cov["retention_truncated"] is True
    assert cov["basis"] == "truncated-retained-copy"
    assert cov["records_total"] < 1920


def test_producer_notes_surface():
    h = rr.retain(interface_table(), tool="t", notes=["partial=true: fields omitted"])["handle"]
    r = call(server.result_count, handle=h, record_path="output.interface")
    assert r["coverage"]["producer_notes"] == ["partial=true: fields omitted"]


def test_scan_budget_hit_not_complete(monkeypatch):
    h = retain_table()
    monkeypatch.setenv("NETCLAW_RESULT_MAX_SCAN", "100")
    r = call(server.result_count, handle=h, record_path="output.interface")
    assert r["coverage"]["complete"] is False and r["coverage"]["records_scanned"] == 100


# ---- US4: windows, text ------------------------------------------------------------------

def _logs():
    recs = [{"ts": f"2026-11-0{d}T10:00:00Z", "sev": "err", "msg": f"m{d}"} for d in range(1, 6)]
    recs.append({"ts": "garbage", "sev": "err", "msg": "bad"})
    recs.append({"sev": "warn", "msg": "none"})
    return {"events": recs}


def test_time_window_reports_gap():
    h = rr.retain(_logs(), tool="syslog")["handle"]
    r = call(server.result_count, handle=h, record_path="events", time_field="ts",
             since="2026-11-02T00:00:00Z", until="2026-11-04T00:00:00Z")
    assert r["count"] == 2
    cov = r["coverage"]
    assert cov["complete"] is False
    assert any("2 record(s)" in g for g in cov["gaps"])


def test_time_window_requires_time_field_and_valid_bounds():
    h = rr.retain(_logs(), tool="syslog")["handle"]
    assert "error" in call(server.result_count, handle=h, record_path="events",
                           since="2026-11-02T00:00:00Z")
    assert "error" in call(server.result_count, handle=h, record_path="events",
                           time_field="ts", since="notadate")


def test_text_lines_and_search():
    text = "\n".join(f"Nov 1 host proc[{i}]: link {'DOWN' if i % 7 == 0 else 'up'}"
                     for i in range(5000))
    h = rr.retain(text, tool="pyats_show_logging", device="r1", command="show logging")["handle"]
    r = call(server.result_text_search, handle=h, needle="link down", limit=20, context=1)
    assert r["matching_lines"] == len(range(0, 5000, 7))
    assert len(r["matches"]) == 20 and r["coverage"]["truncated_page"] is True
    assert r["coverage"]["records_scanned"] == 5000
    p = call(server.result_lines, handle=h, offset=4990, limit=100)
    assert len(p["lines"]) == 10 and p["coverage"]["complete"] is True
    assert "error" in call(server.result_count, handle=h)  # text handle rejects record ops


def test_search_is_literal_not_regex():
    h = rr.retain("a.c\nabc\n", tool="t")["handle"]
    r = call(server.result_text_search, handle=h, needle="a.c")
    assert r["matching_lines"] == 1


# ---- filters / safety ----------------------------------------------------------------------

@pytest.mark.parametrize("op", ["regex", "eval", "sql", "exec"])
def test_unsupported_ops_rejected(op):
    h = retain_table()
    r = call(server.result_count, handle=h, record_path="output.interface",
             where=[{"field": "_key", "op": op, "value": "x"}])
    assert "error" in r and "count" not in r


def test_numeric_and_membership_ops():
    h = rr.retain([{"n": i, "k": "a" if i % 2 else "b"} for i in range(100)], tool="t")["handle"]
    assert call(server.result_count, handle=h, where=[{"field": "n", "op": "ge", "value": 90}]
                )["count"] == 10
    assert call(server.result_count, handle=h, where=[{"field": "k", "op": "in",
                                                      "value": ["a"]}])["count"] == 50
    g = call(server.result_count, handle=h, group_by=["k"])
    assert {x["k"]: x["count"] for x in g["groups"]} == {"a": 50, "b": 50}


def test_modules_have_no_execution_surface():
    src = Path(server.__file__).parent
    for f in ("result_query.py", "result_retention.py", "result_stream.py", "server.py"):
        text = (src / f).read_text()
        for bad in ("eval(", "exec(", "subprocess", "os.system", "import duckdb", "import sqlite3"):
            assert bad not in text, f"{f} contains {bad}"
    assert "import re\n" not in (src / "result_query.py").read_text()


def test_audit_log_has_no_result_content(store):
    h = rr.retain({"secret": ["hunter2-token"]}, tool="t")["handle"]
    call(server.result_describe, handle=h)
    audit = (store / "audit.jsonl").read_text()
    assert "hunter2" not in audit and h in audit


# ---- US5: streams ----------------------------------------------------------------------------

def test_stream_counts_drops_and_gaps():
    s = rs.StreamBuffer(capacity=100, name="syslog")
    for i in range(250):
        s.push({"i": i, "ts": 1000 + i})
        if i == 120:
            s.record_gap("reconnect")
    st = s.stats()
    assert st["received"] == 250 and st["kept"] == 100 and st["dropped"] == 150
    meta = s.snapshot(tool="syslog_snapshot")
    r = call(server.result_count, handle=meta["handle"])
    cov = r["coverage"]
    assert r["count"] == 100 and cov["complete"] is False
    assert cov["stream"]["dropped"] == 150 and len(cov["stream"]["gaps"]) == 1
    assert any("dropped 150" in x for x in cov["incomplete_reasons"])
    assert any("gap" in x for x in cov["incomplete_reasons"])
    # the retained window is the newest 100 events
    first = call(server.result_select, handle=meta["handle"], limit=1)["rows"][0]
    assert first["i"] == 150


def test_stream_without_loss_is_complete_for_window():
    s = rs.StreamBuffer(capacity=10)
    for i in range(5):
        s.push({"i": i})
    r = call(server.result_count, handle=s.snapshot(tool="t")["handle"])
    assert r["coverage"]["complete"] is True


def test_multivendor_tools_route_through_retention():
    """multivendor-cli-mcp needs nornir/napalm to import, so assert the wiring statically."""
    src = (Path(server.__file__).parents[1] / "multivendor-cli-mcp" / "server.py").read_text()
    for call in ('"run_command", device, command)', '"get_facts", device, None)',
                 '"run_fleet", None, command)'):
        assert call in src
    assert "bounded_dict" in src
