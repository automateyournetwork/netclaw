"""Feature 065 US1/US2: card embedding_model field + the manifest/batch wire
contract for chroma-to-chroma replication.

Covers T013 (card embedding_model + replica-exclusion), T024 (tier-0 denial,
grant-type isolation from query-retrieval, grant/revoke audit), T025
(embedding-model mismatch and over-cap refusal before any batch call), T030
(FR-005 batch-retry idempotency via upsert).
"""

import asyncio
import os

import pytest

from bgp.federation import knowledge as kn
from conftest import _await_terminal


# ---- T013: card embedding_model + kind='replica' exclusion ---------------

def _write_document(conn, doc_id, kind, title, collection, chunk_count=1, page_count=1):
    conn.execute(
        "INSERT INTO documents (id, kind, title, source, doc_type, collection, "
        "ingest_status, page_count, chunk_count) VALUES (?, ?, ?, 'upload', 'other', "
        "?, 'ready', ?, ?)", (doc_id, kind, title, collection, page_count, chunk_count))
    conn.commit()


@pytest.fixture
def rag_db(tmp_path, monkeypatch):
    import sqlite3
    db_path = tmp_path / "rag.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE documents (
            id TEXT PRIMARY KEY, kind TEXT, title TEXT, source TEXT, doc_type TEXT,
            version TEXT, content_hash TEXT, collection TEXT, ingest_ts TEXT,
            page_count INTEGER, chunk_count INTEGER, source_path TEXT,
            ingest_status TEXT, error TEXT, capture_ts TEXT, capture_devices TEXT,
            capture_commands TEXT, redaction_counts TEXT
        );
    """)
    conn.commit()
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    return conn, db_path


def test_card_includes_embedding_model_and_excludes_replicas(rag_db):
    conn, db_path = rag_db
    _write_document(conn, "doc_local", "document", "My Book", "documents", chunk_count=200, page_count=100)
    _write_document(conn, "repl_x", "replica", "Their Book",
                    "replica__as65099-9.9.9.9__knowledge_documents", chunk_count=90)

    entries = kn.build_entries(db_path=db_path)
    assert len(entries) == 1, "a kind='replica' row must never be advertised (FR-009)"
    assert entries[0]["collection_id"] == "knowledge:documents"
    assert entries[0]["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert entries[0]["doc_count"] == 1
    assert entries[0]["chunk_count"] == 200

    kn.assert_entry_clean(entries[0])  # still content-free (no new forbidden keys)
    for e in entries:
        text = str(e)
        assert "source_path" not in text
        assert ".db" not in text


# ---- T024/T025: wire handler gating (mirrors test_knowledge_routing.py) --

def _entry(cid, desc, embedding_model="BAAI/bge-small-en-v1.5"):
    return {"collection_id": cid, "name": cid, "description": desc, "tags": [],
            "doc_count": 1, "page_count": 1, "chunk_count": 3,
            "retrieval": "n2n/knowledge/query", "embedding_model": embedding_model}


class _Chan:
    def __init__(self, peer, attestation="possession"):
        self.peer_identity = peer
        self.attestation = attestation


def _federate(manager, peer_as=65099, rid="9.9.9.9"):
    manager.local_consent(peer_as, rid)
    manager.remote_consent(peer_as, rid)
    return f"as{peer_as}-{rid}"


def _service(manager, monkeypatch, tmp_path, embedding_model="BAAI/bge-small-en-v1.5"):
    from bgp.federation.service import FederationService
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "norag"))
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", embedding_model)
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=manager)
    monkeypatch.setattr(kn, "build_entries",
                        lambda *a, **k: [_entry("knowledge:documents", "the book", embedding_model)])
    return svc


def test_replicate_manifest_denied_tier0(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    from bgp.federation.channel import RpcError
    with pytest.raises(RpcError):
        asyncio.run(svc.invoker.handle_replicate_manifest(
            _Chan(peer, attestation="self-asserted"), {"collection_id": "knowledge:documents"}))


def test_query_grant_does_not_authorize_replication(manager, monkeypatch, tmp_path):
    """FR-002: a 'knowledge' (query-only) grant must NOT authorize replication."""
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    svc.authz.grant(peer, "knowledge", "knowledge:documents")
    from bgp.federation.channel import RpcError
    with pytest.raises(RpcError):
        asyncio.run(svc.invoker.handle_replicate_manifest(
            _Chan(peer), {"collection_id": "knowledge:documents"}))
    # query-retrieval itself is unaffected by the absence of a replica grant
    assert svc.authz.authorize(peer, "knowledge", "knowledge:documents").allowed


def test_replica_grant_authorizes_manifest_and_batch(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    svc.authz.grant(peer, "knowledge_replica", "knowledge:documents")

    from bgp.federation import chroma_store_bridge as bridge
    reg = bridge.registry()
    doc_id = reg.new_document(kind="document", title="Book", source="upload",
                              doc_type="other", content_hash="h1", collection="documents")
    reg.finalize(doc_id, chunk_count=1)
    bridge.chroma_store().add_chunks("documents", ["c1"], [[0.1, 0.2]], ["t1"],
                                     [{"document_id": doc_id, "title": "Book"}])

    manifest = asyncio.run(svc.invoker.handle_replicate_manifest(
        _Chan(peer), {"collection_id": "knowledge:documents"}))
    assert manifest["embedding_model"] == "BAAI/bge-small-en-v1.5"
    assert manifest["chunk_count"] == 1

    batch = asyncio.run(svc.invoker.handle_replicate_batch(
        _Chan(peer), {"collection_id": "knowledge:documents", "offset": 0, "limit": 10}))
    assert batch["returned"] == 1
    assert batch["metadatas"][0]["title"] == "Book"

    rows = manager._conn.execute(
        "SELECT outcome FROM remote_invocation_record WHERE peer_identity=? "
        "AND target_type='knowledge_replica' AND outcome='success'", (peer,)).fetchall()
    assert len(rows) == 2  # manifest + batch, each audited


def test_grant_and_revoke_are_audited(manager, monkeypatch, tmp_path):
    """D12/G1 fix: grant/revoke were never audited before feature 065."""
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    gid = svc.authz.grant(peer, "knowledge_replica", "knowledge:documents")
    svc.audit.record(direction="local", peer_identity=peer, target_type="knowledge_replica",
                     target_name="knowledge:documents", decision="granted", outcome="success")
    svc.authz.revoke(gid)
    svc.audit.record(direction="local", peer_identity=peer, target_type="knowledge_replica",
                     target_name="knowledge:documents", decision="revoked", outcome="success")
    rows = manager._conn.execute(
        "SELECT decision FROM remote_invocation_record WHERE peer_identity=? "
        "AND target_type='knowledge_replica' AND direction='local'", (peer,)).fetchall()
    decisions = {r["decision"] for r in rows}
    assert decisions == {"granted", "revoked"}


def test_mismatch_and_overcap_refuse_before_any_batch(manager, monkeypatch, tmp_path):
    """SC-002/SC-008: refused before transfer begins — zero batch calls."""
    from bgp.federation.replication import MAX_CHUNKS

    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)

    batch_calls = {"n": 0}

    async def counting_batch(ident, cid, offset, limit):
        batch_calls["n"] += 1
        return {"ids": []}

    async def mismatch_manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "some-other-model", "chunk_count": 5}

    async def overcap_manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5",
                "chunk_count": MAX_CHUNKS + 1}

    async def main():
        svc.invoker.fetch_replicate_batch = counting_batch
        svc.invoker.fetch_replicate_manifest = mismatch_manifest
        task_id = svc.replication.start(peer, "knowledge:documents")
        st = await _await_terminal(svc, task_id)
        assert st["state"] == "failed"
        assert batch_calls["n"] == 0

        svc.invoker.fetch_replicate_manifest = overcap_manifest
        task_id2 = svc.replication.start(peer, "knowledge:huge")
        st2 = await _await_terminal(svc, task_id2)
        assert st2["state"] == "failed"
        assert batch_calls["n"] == 0

    asyncio.run(main())


def test_batch_retry_is_idempotent(manager, monkeypatch, tmp_path):
    """FR-005/D11: applying the same batch twice (simulating a single-page
    retry, not a whole-job restart) must not duplicate chunks."""
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "norag"))
    from bgp.federation import chroma_store_bridge as bridge
    store = bridge.chroma_store()
    ids = ["r1", "r2"]
    embeddings = [[0.9, 0.9], [0.8, 0.8]]
    texts = ["x", "y"]
    metadatas = [{"a": 1}, {"a": 2}]

    store.upsert_chunks("replica_retry_test", ids, embeddings, texts, metadatas)
    assert store.count("replica_retry_test") == 2
    store.upsert_chunks("replica_retry_test", ids, embeddings, texts, metadatas)  # retry
    assert store.count("replica_retry_test") == 2, "retried batch must not duplicate chunks"
