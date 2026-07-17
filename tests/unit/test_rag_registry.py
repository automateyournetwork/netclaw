"""Unit tests for rag-mcp SQLite registry (state machine, dedupe, sweep).

Fully offline: tempdir SQLite, no models, no network.
"""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

from storage.registry import Registry, SCHEMA_VERSION  # noqa: E402


@pytest.fixture()
def registry():
    with tempfile.TemporaryDirectory() as tmp:
        reg = Registry(str(Path(tmp) / "rag.db"))
        yield reg
        reg.close()


def _new_doc(reg, **overrides):
    kwargs = dict(
        kind="document",
        title="Test Guide",
        source="test-guide.pdf",
        doc_type="vendor",
        content_hash="abc123",
        collection="documents",
    )
    kwargs.update(overrides)
    return reg.new_document(**kwargs)


def test_schema_version_present(registry):
    assert registry.schema_version() == SCHEMA_VERSION


def test_state_machine_transitions(registry):
    doc_id = _new_doc(registry)
    assert registry.get(doc_id)["ingest_status"] == "pending"

    for status in ("parsing", "chunking", "embedding"):
        registry.set_status(doc_id, status)
        assert registry.get(doc_id)["ingest_status"] == status

    registry.finalize(doc_id, chunk_count=42, page_count=10)
    row = registry.get(doc_id)
    assert row["ingest_status"] == "ready"
    assert row["chunk_count"] == 42
    assert row["page_count"] == 10
    assert row["error"] is None


def test_error_state_records_verbatim_message(registry):
    doc_id = _new_doc(registry)
    registry.set_status(doc_id, "error", error="PARSE_FAILED: no extractable text")
    row = registry.get(doc_id)
    assert row["ingest_status"] == "error"
    assert "no extractable text" in row["error"]


def test_dedupe_hash_lookup(registry):
    doc_id = _new_doc(registry, content_hash="samehash")
    registry.finalize(doc_id, chunk_count=1)
    found = registry.find_by_hash("samehash")
    assert found is not None and found["id"] == doc_id
    assert registry.find_by_hash("otherhash") is None
    # Same hash, different kind (snapshot) is a distinct namespace
    assert registry.find_by_hash("samehash", kind="snapshot") is None


def test_dedupe_hash_uniqueness_enforced(registry):
    _new_doc(registry, content_hash="uniq1")
    with pytest.raises(Exception):
        _new_doc(registry, content_hash="uniq1")


def test_sweep_interrupted(registry):
    ok_id = _new_doc(registry, content_hash="h1")
    registry.finalize(ok_id, chunk_count=5)
    stuck_id = _new_doc(registry, content_hash="h2")
    registry.set_status(stuck_id, "embedding")

    swept = registry.sweep_interrupted()
    assert [r["id"] for r in swept] == [stuck_id]
    row = registry.get(stuck_id)
    assert row["ingest_status"] == "error"
    assert "interrupted" in row["error"]
    assert registry.get(ok_id)["ingest_status"] == "ready"
    # Second sweep is a no-op
    assert registry.sweep_interrupted() == []


def test_snapshot_fields_roundtrip(registry):
    snap_id = registry.new_document(
        kind="snapshot",
        title="core-bgp",
        source="pyats",
        doc_type="other",
        content_hash="snaphash",
        collection="snapshot_core-bgp_2026-07-16T14:02:00Z",
        capture_ts="2026-07-16T14:02:00Z",
        capture_devices=["PE1", "PE2"],
        capture_commands=["show ip bgp"],
    )
    registry.finalize(snap_id, chunk_count=3, redaction_counts={"password": 2, "snmp_community": 0})
    row = registry.get(snap_id)
    assert row["kind"] == "snapshot"
    assert row["capture_ts"] == "2026-07-16T14:02:00Z"
    assert "PE1" in row["capture_devices"]
    assert '"password": 2' in row["redaction_counts"]


def test_list_and_delete(registry):
    d1 = _new_doc(registry, content_hash="l1")
    registry.finalize(d1, chunk_count=1)
    docs = registry.list_documents(kind="document")
    assert len(docs) == 1
    assert registry.delete(d1) is True
    assert registry.list_documents(kind="document") == []
    assert registry.delete("doc_nonexistent") is False


def test_update_metadata(registry):
    d1 = _new_doc(registry)
    updated = registry.update_metadata(d1, doc_type="customer", version="2.0")
    assert updated["doc_type"] == "customer"
    assert updated["version"] == "2.0"
    assert updated["title"] == "Test Guide"


def test_retrieval_log_and_telemetry(registry):
    registry.log_retrieval(
        query="upgrade steps",
        collection="documents",
        filters={"doc_type": "vendor"},
        k=5,
        chunk_ids=["c1", "c2"],
        scores=[0.9, 0.4],
        latency_ms=120,
        low_confidence=1,
        round=1,
        sub_query_id="sq1",
    )
    registry.log_retrieval(
        query="upgrade steps refined",
        collection="documents",
        filters=None,
        k=5,
        chunk_ids=["c3"],
        scores=[0.8],
        latency_ms=80,
        low_confidence=0,
        round=2,
        sub_query_id="sq1",
    )
    t = registry.telemetry()
    assert t["query_count"] == 2
    assert t["mean_latency_ms"] == 100.0
    assert t["re_retrieval_rate"] == 1.0  # sq1 went to round 2
    assert t["low_confidence_rate"] == 0.5
