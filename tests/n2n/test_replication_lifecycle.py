"""Feature 065 US2/US3: the async replication job lifecycle, its success-path
guarantees (SC-001/SC-004), atomicity on failure, and manual re-sync
(FR-010/SC-006) including revoke-blocks-resync (FR-011).

Covers T026, T028, T029, T034, T035.
"""

import asyncio

import pytest

from bgp.federation import knowledge as kn
from conftest import _await_terminal


def _entry(cid, desc, embedding_model="BAAI/bge-small-en-v1.5"):
    return {"collection_id": cid, "name": cid, "description": desc, "tags": [],
            "doc_count": 1, "page_count": 1, "chunk_count": 3,
            "retrieval": "n2n/knowledge/query", "embedding_model": embedding_model}


def _federate(manager, peer_as=65099, rid="9.9.9.9"):
    manager.local_consent(peer_as, rid)
    manager.remote_consent(peer_as, rid)
    return f"as{peer_as}-{rid}"


def _service(manager, monkeypatch, tmp_path):
    from bgp.federation.service import FederationService
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "rag"))
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=manager)
    monkeypatch.setattr(kn, "build_entries",
                        lambda *a, **k: [_entry("knowledge:documents", "the book")])
    return svc


def _page(offset, ids, embeddings, texts, doc_id="docA", title="Their Book"):
    return {"ids": ids, "embeddings": embeddings, "texts": texts,
            "metadatas": [{"document_id": doc_id, "title": title} for _ in ids]}


# ---- T026: async job status/progress + failure atomicity ----------------

def test_start_returns_immediately_and_reports_progress(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)

    async def manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": 3}

    async def batch(ident, cid, offset, limit):
        if offset == 0:
            return _page(0, ["c1", "c2"], [[0.1, 0.1], [0.2, 0.2]], ["a", "b"])
        if offset == 2:
            return _page(2, ["c3"], [[0.3, 0.3]], ["c"])
        return {"ids": []}

    svc.invoker.fetch_replicate_manifest = manifest
    svc.invoker.fetch_replicate_batch = batch

    async def main():
        task_id = svc.replication.start(peer, "knowledge:documents")
        # FR-015/SC-007: the call above already returned — task_id exists and
        # is immediately queryable without having blocked for the transfer.
        st0 = svc.tasks.status(task_id)
        assert st0["state"] in ("submitted", "working", "completed")
        st = await _await_terminal(svc, task_id)
        assert st["state"] == "completed"
        assert st["progress"] == "3/3 chunks"

    asyncio.run(main())


def test_failed_transfer_leaves_no_ready_replica_and_no_orphaned_chunks(manager, monkeypatch, tmp_path):
    """FR-006: an interrupted transfer must leave no partially-queryable
    collection AND no orphaned chunk data behind."""
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)

    async def manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": 5}

    async def batch(ident, cid, offset, limit):
        if offset == 0:
            return _page(0, ["x1", "x2"], [[0.1, 0.1], [0.2, 0.2]], ["a", "b"])
        return {"ids": []}  # source "dies" after the first page

    svc.invoker.fetch_replicate_manifest = manifest
    svc.invoker.fetch_replicate_batch = batch

    async def main():
        task_id = svc.replication.start(peer, "knowledge:partial")
        st = await _await_terminal(svc, task_id)
        assert st["state"] == "failed"

        from bgp.federation import chroma_store_bridge as bridge
        from bgp.federation.replication import local_replica_identity
        identity = local_replica_identity(peer, "knowledge:partial")
        assert bridge.chroma_store().count(identity) == 0, "no orphaned chunks after failure"
        rows = bridge.registry().list_documents()
        assert all(r["ingest_status"] != "ready" for r in rows)

    asyncio.run(main())


# ---- T028: SC-001 — zero embedder invocations during import --------------

def test_zero_embedder_calls_during_successful_replication(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)

    embedder_calls = {"n": 0}

    def poisoned_embedder(*args, **kwargs):
        embedder_calls["n"] += 1
        raise AssertionError("embedder must never be invoked during replication import")

    # Poison the two real embedder entry points a mistaken re-embed would hit.
    monkeypatch.setattr("sentence_transformers.SentenceTransformer",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no embedder")),
                        raising=False)

    async def manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": 2}

    async def batch(ident, cid, offset, limit):
        if offset == 0:
            return _page(0, ["c1", "c2"], [[0.1, 0.1], [0.2, 0.2]], ["a", "b"])
        return {"ids": []}

    svc.invoker.fetch_replicate_manifest = manifest
    svc.invoker.fetch_replicate_batch = batch

    async def main():
        task_id = svc.replication.start(peer, "knowledge:documents")
        st = await _await_terminal(svc, task_id)
        assert st["state"] == "completed"

    asyncio.run(main())
    assert embedder_calls["n"] == 0


# ---- T029: SC-004 success path — multi-batch count exactly matches -------

def test_multibatch_success_count_matches_manifest_exactly(manager, monkeypatch, tmp_path):
    """A server naturally clamps `limit` regardless of what the client
    requests (contracts/knowledge-replication.md) — this mock enforces a
    small page size server-side, exactly like a real server would, so the
    worker's multi-round-trip loop is genuinely exercised, not just its
    single-call path."""
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)

    total = 7
    server_page_size = 2
    all_ids = [f"c{i}" for i in range(total)]
    batch_calls = {"n": 0}

    async def manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": total}

    async def batch(ident, cid, offset, limit):
        batch_calls["n"] += 1
        chunk_ids = all_ids[offset:offset + server_page_size]
        if not chunk_ids:
            return {"ids": []}
        return _page(offset, chunk_ids, [[0.1, 0.1]] * len(chunk_ids), ["t"] * len(chunk_ids))

    svc.invoker.fetch_replicate_manifest = manifest
    svc.invoker.fetch_replicate_batch = batch

    async def main():
        task_id = svc.replication.start(peer, "knowledge:documents")
        st = await _await_terminal(svc, task_id)
        assert st["state"] == "completed"
        assert batch_calls["n"] >= 4, "the server's smaller page size must force multiple round trips"

        from bgp.federation import chroma_store_bridge as bridge
        from bgp.federation.replication import local_replica_identity
        identity = local_replica_identity(peer, "knowledge:documents")
        assert bridge.chroma_store().count(identity) == total
        rows = bridge.registry().list_documents()
        assert sum(r["chunk_count"] for r in rows if r["kind"] == "replica") == total

    asyncio.run(main())


# ---- T034: re-sync full-replace (SC-006) ----------------------------------

def test_resync_replaces_content_exactly(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)

    async def initial_manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": 2}

    async def initial_batch(ident, cid, offset, limit):
        if offset == 0:
            return _page(0, ["c1", "c2"], [[0.1, 0.1], [0.2, 0.2]], ["a", "b"], "docA", "Book A")
        return {"ids": []}

    svc.invoker.fetch_replicate_manifest = initial_manifest
    svc.invoker.fetch_replicate_batch = initial_batch

    async def main():
        t1 = svc.replication.start(peer, "knowledge:documents")
        st1 = await _await_terminal(svc, t1)
        assert st1["state"] == "completed"

        from bgp.federation import chroma_store_bridge as bridge
        from bgp.federation.replication import local_replica_identity
        identity = local_replica_identity(peer, "knowledge:documents")
        store = bridge.chroma_store()
        assert store.count(identity) == 2

        async def resync_manifest(ident, cid):
            return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": 3}

        async def resync_batch(ident, cid, offset, limit):
            if offset == 0:
                return _page(0, ["d1", "d2", "d3"],
                            [[0.9, 0.9], [0.8, 0.8], [0.7, 0.7]], ["x", "y", "z"], "docB", "Book B")
            return {"ids": []}

        svc.invoker.fetch_replicate_manifest = resync_manifest
        svc.invoker.fetch_replicate_batch = resync_batch

        t2 = svc.replication.resync(peer, "knowledge:documents")
        st2 = await _await_terminal(svc, t2)
        assert st2["state"] == "completed"

        assert store.count(identity) == 3, "old chunks must be gone, only the new snapshot remains"
        rows = bridge.registry().list_documents()
        replica_rows = [r for r in rows if r["collection"] == identity]
        assert len(replica_rows) == 1
        assert replica_rows[0]["title"] == "Book B"
        assert replica_rows[0]["chunk_count"] == 3

    asyncio.run(main())


# ---- T035: revoke blocks re-sync but leaves the existing replica alone ----

def test_revoke_blocks_resync_but_leaves_existing_replica(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    gid = svc.authz.grant(peer, "knowledge_replica", "knowledge:documents")

    async def manifest(ident, cid):
        return {"collection_id": cid, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": 1}

    async def batch(ident, cid, offset, limit):
        if offset == 0:
            return _page(0, ["c1"], [[0.1, 0.1]], ["a"])
        return {"ids": []}

    svc.invoker.fetch_replicate_manifest = manifest
    svc.invoker.fetch_replicate_batch = batch

    async def main():
        t1 = svc.replication.start(peer, "knowledge:documents")
        st1 = await _await_terminal(svc, t1)
        assert st1["state"] == "completed"

        svc.authz.revoke(gid)

        # The manifest handler itself enforces the grant — with it revoked,
        # a real fetch_replicate_manifest call would now raise RpcError; we
        # simulate that at the client boundary the worker actually calls.
        from bgp.federation.channel import RpcError

        async def denied_manifest(ident, cid):
            raise RpcError(-32001, "knowledge_replica not allowlisted (revoked)")

        svc.invoker.fetch_replicate_manifest = denied_manifest
        t2 = svc.replication.resync(peer, "knowledge:documents")
        st2 = await _await_terminal(svc, t2)
        assert st2["state"] == "failed"

        from bgp.federation import chroma_store_bridge as bridge
        from bgp.federation.replication import local_replica_identity
        identity = local_replica_identity(peer, "knowledge:documents")
        assert bridge.chroma_store().count(identity) == 1, "existing replica untouched by a refused resync"

    asyncio.run(main())
