"""Tests for GCF serializer: graph detection, session dedup, delta, mode control."""

import json
import os
import sys
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def reload_serializer(mode="full"):
    """Reload serializer with a specific GCF mode."""
    os.environ["NETCLAW_GCF_MODE"] = mode
    import netclaw_tokens.gcf_serializer as gs
    importlib.reload(gs)
    gs.get_session_manager().reset()
    return gs


def test_generic_flat_data():
    """Flat arrays use generic profile."""
    gs = reload_serializer()
    data = {"interfaces": [{"ifname": f"eth{i}", "state": "up", "mtu": 9000} for i in range(10)]}
    r = gs.serialize_response(data)
    assert r["profile_used"] == "generic"
    assert r["fallback_used"] is False
    assert r["savings_pct"] > 0
    assert "## interfaces" in r["encoded_data"]


def test_graph_auto_detection():
    """Data with nodes + edges triggers graph profile."""
    gs = reload_serializer()
    data = {
        "devices": [{"hostname": f"rtr-{i}", "role": "spine"} for i in range(5)],
        "links": [{"source": "rtr-0", "target": "rtr-1", "state": "up"}],
    }
    r = gs.serialize_response(data)
    assert r["profile_used"] in ("graph", "graph+session")
    assert r["fallback_used"] is False
    assert "@0" in r["encoded_data"]


def test_graph_no_edges_uses_generic():
    """Data with nodes but no edges falls to generic."""
    gs = reload_serializer()
    data = {"devices": [{"hostname": f"rtr-{i}", "role": "spine"} for i in range(5)]}
    r = gs.serialize_response(data)
    assert r["profile_used"] == "generic"


def test_session_dedup():
    """Second call with same data produces bare refs."""
    gs = reload_serializer()
    data = {
        "devices": [{"hostname": "rtr-001", "role": "spine"}, {"hostname": "rtr-002", "role": "leaf"}],
        "links": [{"source": "rtr-001", "target": "rtr-002", "state": "up"}],
    }
    r1 = gs.serialize_response(data, use_session=True)
    assert "rtr-001" in r1["encoded_data"]

    r2 = gs.serialize_response(data, use_session=True)
    assert "previously transmitted" in r2["encoded_data"]
    assert r2["gcf_token_count"] <= r1["gcf_token_count"]


def test_delta_encoding():
    """Delta sends only changes."""
    gs = reload_serializer()
    data1 = {
        "devices": [{"hostname": f"rtr-{i}", "role": "spine"} for i in range(5)],
        "links": [{"source": "rtr-0", "target": "rtr-1", "state": "up"}],
    }
    gs.serialize_response(data1, use_session=True, use_delta=True)

    # Same data, delta should be tiny
    r2 = gs.serialize_response(data1, use_session=True, use_delta=True)
    assert r2["profile_used"] == "delta"
    assert r2["gcf_token_count"] < 50


def test_delta_with_changes():
    """Delta with added device sends only the diff."""
    gs = reload_serializer()
    data1 = {
        "devices": [{"hostname": f"rtr-{i}", "role": "spine"} for i in range(5)],
        "links": [{"source": "rtr-0", "target": "rtr-1", "state": "up"}],
    }
    gs.serialize_response(data1, use_session=True, use_delta=True)

    data2 = {
        "devices": [{"hostname": f"rtr-{i}", "role": "spine"} for i in range(6)],
        "links": [{"source": "rtr-0", "target": "rtr-1", "state": "up"}],
    }
    r2 = gs.serialize_response(data2, use_session=True, use_delta=True)
    assert r2["profile_used"] == "delta"
    assert "rtr-5" in r2["encoded_data"]


def test_json_fallback_on_binary():
    """Binary data falls back to JSON."""
    gs = reload_serializer()
    r = gs.serialize_response(b"\x00\x01\x02")
    assert r["profile_used"] == "json"
    assert r["fallback_used"] is True


def test_empty_data():
    """Empty dict doesn't crash."""
    gs = reload_serializer()
    r = gs.serialize_response({})
    assert r["fallback_used"] is False
    assert r["profile_used"] == "generic"


def test_string_data():
    """Simple string value doesn't crash."""
    gs = reload_serializer()
    r = gs.serialize_response({"error": "not found"})
    assert r["fallback_used"] is False


def test_mode_full():
    """Full mode enables graph + session + delta."""
    gs = reload_serializer("full")
    data = {
        "devices": [{"hostname": "rtr-1", "role": "spine"}],
        "links": [{"source": "rtr-1", "target": "rtr-1", "state": "up"}],
    }
    r = gs.serialize_response(data, use_session=True, use_delta=True)
    assert r["profile_used"] in ("graph", "graph+session")


def test_mode_graph():
    """Graph mode enables graph but not session."""
    gs = reload_serializer("graph")
    data = {
        "devices": [{"hostname": "rtr-1", "role": "spine"}, {"hostname": "rtr-2", "role": "leaf"}],
        "links": [{"source": "rtr-1", "target": "rtr-2", "state": "up"}],
    }
    r1 = gs.serialize_response(data, use_session=True)
    assert r1["profile_used"] == "graph"  # not graph+session

    r2 = gs.serialize_response(data, use_session=True)
    assert "previously transmitted" not in r2["encoded_data"]


def test_mode_generic():
    """Generic mode skips graph detection."""
    gs = reload_serializer("generic")
    data = {
        "devices": [{"hostname": "rtr-1", "role": "spine"}, {"hostname": "rtr-2", "role": "leaf"}],
        "links": [{"source": "rtr-1", "target": "rtr-2", "state": "up"}],
    }
    r = gs.serialize_response(data)
    assert r["profile_used"] == "generic"


def test_mode_off():
    """Off mode returns JSON."""
    gs = reload_serializer("off")
    data = {"interfaces": [{"ifname": "eth0", "state": "up"}]}
    r = gs.serialize_response(data)
    assert r["profile_used"] == "json"
    assert r["fallback_used"] is True
    assert r["savings_pct"] == 0.0


def test_roundtrip_lossless():
    """GCF generic encode produces valid output that contains all field values."""
    gs = reload_serializer()
    records = [
        {"id": "001", "name": "Alice", "status": "active", "score": 95.5},
        {"id": "002", "name": "Bob", "status": "inactive", "score": 82.0},
    ]
    r = gs.serialize_response({"users": records})
    encoded = r["encoded_data"]
    # All values present in output
    assert "Alice" in encoded
    assert "Bob" in encoded
    assert "001" in encoded
    assert "95.5" in encoded


def test_edge_key_detection():
    """Various edge key names are detected."""
    gs = reload_serializer()
    for src_key, tgt_key in [("source", "target"), ("src", "dest"), ("from", "to")]:
        data = {
            "nodes": [{"hostname": "a"}, {"hostname": "b"}],
            "edges": [{src_key: "a", tgt_key: "b", "type": "link"}],
        }
        r = gs.serialize_response(data)
        assert r["profile_used"] in ("graph", "graph+session"), f"Failed for {src_key}/{tgt_key}"


def test_session_manager_reset():
    """Session reset clears state."""
    gs = reload_serializer()
    data = {
        "devices": [{"hostname": "rtr-1", "role": "spine"}, {"hostname": "rtr-2", "role": "leaf"}],
        "links": [{"source": "rtr-1", "target": "rtr-2", "state": "up"}],
    }
    gs.serialize_response(data, use_session=True)
    gs.get_session_manager().reset()
    r = gs.serialize_response(data, use_session=True)
    assert "previously transmitted" not in r["encoded_data"]


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS  {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL  {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} passed")
