"""Integration tests for rag-mcp: ingest -> search round trips.

Fully offline: RAG_DATA_DIR is a tempdir set before module import, and the
embedder is replaced with a deterministic bag-of-words hash vectorizer so
similarity ranking is meaningful without any model download.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = tempfile.mkdtemp(prefix="rag-mcp-test-")
os.environ["RAG_DATA_DIR"] = _TMP

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

import rag_mcp_server as server  # noqa: E402


class HashEmbedder:
    """Deterministic 64-dim bag-of-words hash vectors. Offline, no models."""

    DIM = 64

    def _vec(self, text: str):
        vec = [0.0] * self.DIM
        for token in text.lower().split():
            vec[hash(token) % self.DIM] += 1.0
        norm = sum(v * v for v in vec) ** 0.5 or 1.0
        return [v / norm for v in vec]

    def embed_passages(self, texts):
        return [self._vec(t) for t in texts]

    def embed_query(self, query):
        return self._vec(query)

    def count_tokens(self, text):
        return len(text.split())


@pytest.fixture(autouse=True)
def fake_embedder():
    server.embedder = HashEmbedder()
    server.reranker.enabled = False  # offline passthrough — no model download
    yield


GUIDE_MD = """# WLC 9800 Upgrade Guide

## Pre-Upgrade Checks

Verify the boot variable points at the correct image. Back up the startup
configuration to bootflash before beginning the zorbified upgrade window.

## Install Procedure

Run install add file bootflash:C9800.bin activate commit from the exec prompt.
"""


def _ingest_md(content: str, name: str = "guide.md", **kwargs):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(content)
        path = f.name
    try:
        return server._do_ingest(path, **kwargs)
    finally:
        os.unlink(path)


def test_ingest_confirmation_payload():
    resp = _ingest_md(GUIDE_MD, doc_type="vendor")
    assert resp["success"], resp
    data = resp["data"]
    assert data["title"] == "WLC 9800 Upgrade Guide"
    assert data["doc_type"] == "vendor"
    assert data["chunk_count"] >= 1
    assert data["collection"] == "documents"
    assert data["deduplicated"] is False
    assert "WLC 9800 Upgrade Guide" in data["example_question"]
    # Original retained for rag_reindex
    row = server.registry.get(data["document_id"])
    assert row["source_path"] and Path(row["source_path"]).exists()


def test_search_returns_citation_and_logs_chunk_ids():
    _ingest_md(GUIDE_MD, doc_type="vendor")
    resp = server._do_search("zorbified upgrade window boot variable", k=3)
    assert resp["success"]
    data = resp["data"]
    assert data["corpus_empty"] is False
    assert data["results"], "expected at least one hit"
    top = data["results"][0]
    assert "zorbified" in top["chunk_text"]
    assert top["citation"].startswith("[WLC 9800 Upgrade Guide")
    assert "— ingested 20" in top["citation"]
    # Chunk IDs are log-only: present in result payload for traceability
    # but the citation string itself must not contain them
    assert top["chunk_id"] not in top["citation"]
    # Retrieval log captured the call
    cur = server.registry._conn.execute("SELECT * FROM retrieval_log ORDER BY id DESC")
    row = dict(cur.fetchone())
    assert "zorbified" in row["query"]
    assert top["chunk_id"] in row["chunk_ids"]


def test_dedupe_same_bytes_noop():
    first = _ingest_md(GUIDE_MD, doc_type="vendor")
    again = _ingest_md(GUIDE_MD, doc_type="vendor")
    assert again["success"]
    assert again["data"]["deduplicated"] is True
    assert again["data"]["document_id"] == first["data"]["document_id"]


def test_reindex_same_title_new_content():
    first = _ingest_md(GUIDE_MD)
    updated = GUIDE_MD + "\n## Rollback\n\nUse install rollback to committed.\n"
    second = _ingest_md(updated)
    assert second["success"]
    assert second["data"]["reindexed"] is True
    assert second["data"]["document_id"] != first["data"]["document_id"]
    # Old document fully gone from registry and index
    assert server.registry.get(first["data"]["document_id"]) is None
    resp = server._do_search("install rollback to committed", k=3)
    titles = {r["title"] for r in resp["data"]["results"]}
    assert titles == {"WLC 9800 Upgrade Guide"}


def test_base64_slack_path():
    import base64 as b64

    content = "# Slack Doc\n\n## Notes\n\nUploaded through the channel."
    resp = server._do_ingest_base64(
        "slack-doc.md", b64.b64encode(content.encode()).decode(), doc_type="other"
    )
    assert resp["success"], resp
    assert resp["data"]["title"] == "Slack Doc"
    row = server.registry.get(resp["data"]["document_id"])
    assert row["source"] == "slack:attachment"


def test_empty_collection_search_is_soft():
    resp = server._do_search("anything", collection="never_created")
    assert resp["success"]
    assert resp["data"]["corpus_empty"] is True
    assert resp["data"]["results"] == []


def test_unsupported_and_size_errors_surface():
    with tempfile.NamedTemporaryFile("wb", suffix=".pcap", delete=False) as f:
        f.write(b"\x00")
        path = f.name
    try:
        resp = server._do_ingest(path)
    finally:
        os.unlink(path)
    assert resp["success"] is False
    assert resp["error"]["code"] == "UNSUPPORTED_FORMAT"


def test_gait_absent_does_not_crash():
    # gait_log swallows import errors; a plain call must not raise
    server.gait_log("test", "no gait installed here")


# ---------------------------------------------------------------------
# US2: filters, low_confidence, round logging (T027)
# ---------------------------------------------------------------------
STANDARD_MD = """# Customer WLAN Standard

## Change Windows

All controller upgrades occur inside an approved flanverted maintenance window.
"""


def test_filter_scopes_by_doc_type():
    _ingest_md(GUIDE_MD, doc_type="vendor")
    _ingest_md(STANDARD_MD, doc_type="customer")
    resp = server._do_search(
        "flanverted maintenance window upgrades", k=5, filters={"doc_type": "customer"}
    )
    assert resp["success"]
    results = resp["data"]["results"]
    assert results, "expected customer-scoped hits"
    assert all(r["doc_type"] == "customer" for r in results)

    # Vendor-scoped search for the same phrase must not return the standard
    resp = server._do_search(
        "flanverted maintenance window upgrades", k=5, filters={"doc_type": "vendor"}
    )
    assert all(r["doc_type"] == "vendor" for r in resp["data"]["results"])


def test_low_confidence_flagged_not_dropped():
    _ingest_md(GUIDE_MD, doc_type="vendor")
    # Query with zero token overlap: dense hash similarity ~0 -> below floor
    resp = server._do_search("quantum entanglement espresso recipes", k=3)
    assert resp["success"]
    results = resp["data"]["results"]
    assert results, "sub-floor results must be returned, flagged — never dropped"
    # Invariant (FR-024): the flag mirrors score-vs-floor, and sub-floor hits
    # are present in the result set rather than silently removed
    import config as rag_config

    assert all(
        r["low_confidence"] == (r["score"] < rag_config.RELEVANCE_FLOOR) for r in results
    )
    assert any(r["low_confidence"] for r in results), "expected at least one sub-floor hit"


def test_round_and_sub_query_id_logged():
    _ingest_md(GUIDE_MD, doc_type="vendor")
    server._do_search("boot variable", k=2, round=1, sub_query_id="sq-42")
    server._do_search("boot variable image", k=2, round=2, sub_query_id="sq-42")
    cur = server.registry._conn.execute(
        "SELECT round, sub_query_id FROM retrieval_log WHERE sub_query_id = 'sq-42' ORDER BY id"
    )
    rows = cur.fetchall()
    assert [(r[0], r[1]) for r in rows] == [(1, "sq-42"), (2, "sq-42")]
    telemetry = server.registry.telemetry()
    assert telemetry["re_retrieval_rate"] > 0


# ---------------------------------------------------------------------
# US6: management tools (T039/T040)
# ---------------------------------------------------------------------
def test_list_and_stats():
    _ingest_md(GUIDE_MD, doc_type="vendor")
    listing = server._do_list()["data"]
    assert len(listing["documents"]) >= 1
    assert any(d["title"] == "WLC 9800 Upgrade Guide" for d in listing["documents"])
    assert "snapshots" in listing  # separate array, present even when empty

    stats = server._do_stats()["data"]
    assert stats["document_count"] >= 1
    assert stats["total_chunks"] >= 1
    assert stats["schema_version"] == 1
    assert "telemetry" in stats and "query_count" in stats["telemetry"]


def test_update_metadata_tool():
    resp = _ingest_md(GUIDE_MD, doc_type="other")
    doc_id = resp["data"]["document_id"]
    updated = server._do_update_metadata(doc_id, doc_type="vendor", version="17.9")
    assert updated["success"]
    assert updated["data"]["doc_type"] == "vendor"
    assert updated["data"]["version"] == "17.9"
    bad = server._do_update_metadata(doc_id, doc_type="not-a-type")
    assert bad["success"] is False


def test_delete_requires_confirmation_then_removes_everywhere():
    resp = _ingest_md(GUIDE_MD, doc_type="vendor")
    doc_id = resp["data"]["document_id"]

    gate = server._do_delete(doc_id)  # no confirmed flag -> HIIL gate
    assert gate["success"] and gate["data"]["confirmation_required"] is True
    assert server.registry.get(doc_id) is not None  # nothing deleted yet

    done = server._do_delete(doc_id, confirmed=True)
    assert done["success"] and done["data"]["deleted"] is True
    assert done["data"]["chunks_removed"] >= 1
    assert server.registry.get(doc_id) is None
    # Gone from search too
    found = server._do_search("zorbified upgrade window", k=5)
    assert all(r["title"] != "WLC 9800 Upgrade Guide" for r in found["data"]["results"])


def test_reindex_confirmation_and_roundtrip():
    resp = _ingest_md(GUIDE_MD, doc_type="vendor")
    doc_id = resp["data"]["document_id"]
    gate = server._do_reindex(doc_id)
    assert gate["data"]["confirmation_required"] is True
    done = server._do_reindex(doc_id, confirmed=True)
    assert done["success"], done
    assert done["data"]["title"] == "WLC 9800 Upgrade Guide"
    assert done["data"]["chunk_count"] >= 1
    assert server.registry.get(doc_id) is None  # old id replaced by new ingest


# ---------------------------------------------------------------------
# US7: snapshots (T048/T049/T051)
# ---------------------------------------------------------------------
SNAPSHOT_CONTENT = """PE1# show run | sec bgp
router bgp 65000
 neighbor 10.0.0.1 password 7 095C4F1A0A1218000F

PE1# show ip bgp summary
Neighbor        V  AS    MsgRcvd MsgSent Up/Down  State/PfxRcd
10.0.0.1        4  65001 88203   88191   8w0d     42
"""


def test_snapshot_roundtrip_scrubbed_and_staleness_tagged():
    resp = server._do_snapshot(
        label="core-bgp",
        content=SNAPSHOT_CONTENT,
        source_description="core router BGP tables",
        devices=["PE1"],
        commands=["show ip bgp summary"],
        capture_ts="2026-06-16T14:02:00Z",
    )
    assert resp["success"], resp
    data = resp["data"]
    assert data["collection"].startswith("snapshot_core-bgp_")
    assert data["collection"] != "documents"
    assert data["redaction_counts"]["routing_auth_key"] == 1
    assert data["redaction_counts"]["snmp_community"] == 0  # zeros reported
    # Search inside the snapshot collection: staleness surfaced
    found = server._do_search("BGP neighbor state PfxRcd", k=3, collection=data["collection"])
    assert found["data"]["results"], "snapshot content must be retrievable"
    top = found["data"]["results"][0]
    assert top["age_human"] and "captured 2026-06-16 14:02 UTC" in top["age_human"]
    assert "live state is available via MCP" in top["staleness_notice"]
    assert "095C4F1A0A1218000F" not in top["chunk_text"]  # scrubbed before vectorizing
    # Listed separately with stale flag (>90 days if run after 2026-09; tolerate either)
    listing = server._do_list("snapshots")["data"]
    snap = next(s for s in listing["snapshots"] if s["id"] == data["snapshot_id"])
    assert snap["age_human"] and isinstance(snap["stale"], bool)
    # Snapshots are deletable but not reindexable
    assert server._do_reindex(data["snapshot_id"], confirmed=True)["success"] is False
    deleted = server._do_delete(data["snapshot_id"], confirmed=True)
    assert deleted["success"] and deleted["data"]["deleted"] is True


def test_snapshot_empty_content_rejected():
    resp = server._do_snapshot("empty", "   ", "nothing")
    assert resp["success"] is False


def test_ingested_date_filters():
    resp_ingest = _ingest_md(GUIDE_MD, doc_type="vendor")
    ts = resp_ingest["data"].get("ingest_ts") or server.registry.get(
        resp_ingest["data"]["document_id"]
    )["ingest_ts"]
    resp = server._do_search("boot variable", k=3, filters={"ingested_after": "2099-01-01"})
    assert resp["data"]["results"] == []
    resp = server._do_search("boot variable", k=3, filters={"ingested_before": "2099-01-01"})
    assert resp["data"]["results"], f"doc ingested {ts} should pass the before-filter"
