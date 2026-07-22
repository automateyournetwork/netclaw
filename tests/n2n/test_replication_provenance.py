"""Feature 065 US4: replica provenance, non-advertisement, non-propagation
onward to a third peer, and cleanup.

Covers T039, T040, T041.
"""

import asyncio

from bgp.federation import knowledge as kn
from conftest import _await_terminal


def _entry(cid, desc, embedding_model="BAAI/bge-small-en-v1.5"):
    return {"collection_id": cid, "name": cid, "description": desc, "tags": [],
            "doc_count": 1, "page_count": 1, "chunk_count": 3,
            "retrieval": "n2n/knowledge/query", "embedding_model": embedding_model}


def _federate(manager, peer_as, rid):
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


class _Chan:
    def __init__(self, peer, attestation="possession"):
        self.peer_identity = peer
        self.attestation = attestation


def _replicate_one(svc, peer, cid="knowledge:documents"):
    async def manifest(ident, c):
        return {"collection_id": c, "embedding_model": "BAAI/bge-small-en-v1.5", "chunk_count": 1}

    async def batch(ident, c, offset, limit):
        if offset == 0:
            return {"ids": ["c1"], "embeddings": [[0.1, 0.1]], "texts": ["a"],
                    "metadatas": [{"document_id": "docA", "title": "Their Book"}]}
        return {"ids": []}

    svc.invoker.fetch_replicate_manifest = manifest
    svc.invoker.fetch_replicate_batch = batch

    async def main():
        task_id = svc.replication.start(peer, cid)
        return await _await_terminal(svc, task_id)
    return asyncio.run(main())


# ---- T039: provenance + non-advertisement to a third peer -----------------

def test_replica_provenance_and_not_advertised_to_third_peer(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer_b = _federate(manager, 65099, "9.9.9.9")   # the source we replicate FROM
    st = _replicate_one(svc, peer_b)
    assert st["state"] == "completed"

    from bgp.federation import chroma_store_bridge as bridge
    from bgp.federation.replication import local_replica_identity
    identity = local_replica_identity(peer_b, "knowledge:documents")
    rows = [dict(r) for r in bridge.registry().list_documents() if r["collection"] == identity]
    assert len(rows) == 1
    assert rows[0]["source_peer_identity"] == peer_b
    assert rows[0]["source_collection_id"] == "knowledge:documents"
    assert rows[0]["replicated_at"] is not None
    assert rows[0]["kind"] == "replica"

    # Now build OUR OWN card (as if a third peer C were pulling it) — the
    # real, un-monkeypatched knowledge.build_entries() must read this same
    # RAG store and exclude the replica (FR-009).
    monkeypatch.undo()  # remove the build_entries() stub from _service() above
    import importlib
    importlib.reload(kn)
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "rag"))
    entries = kn.build_entries()
    assert not any(e["collection_id"] == identity for e in entries)
    assert not any("Their Book" in e.get("description", "") for e in entries)


# ---- T041: a third peer cannot replicate a replica directly either -------

def test_third_peer_cannot_replicate_a_replica_directly(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer_b = _federate(manager, 65099, "9.9.9.9")
    st = _replicate_one(svc, peer_b)
    assert st["state"] == "completed"

    from bgp.federation.replication import local_replica_identity
    identity = local_replica_identity(peer_b, "knowledge:documents")

    peer_c = _federate(manager, 65007, "7.7.7.7")   # a third peer
    # Even with a (hypothetically granted) replication grant for this exact
    # id, C is refused as not-found — the replica was never in the visible
    # set C could have legitimately learned this collection_id from (FR-009
    # second clause: no onward propagation).
    svc.authz.grant(peer_c, "knowledge_replica", identity)
    result = asyncio.run(svc.invoker.handle_replicate_manifest(
        _Chan(peer_c), {"collection_id": identity}))
    assert result.get("not_found") is True


# ---- T040: delete removes everything --------------------------------------

def test_delete_removes_all_chunks_and_registry_rows(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer_b = _federate(manager, 65099, "9.9.9.9")
    st = _replicate_one(svc, peer_b)
    assert st["state"] == "completed"

    from bgp.federation import chroma_store_bridge as bridge
    from bgp.federation.replication import local_replica_identity
    identity = local_replica_identity(peer_b, "knowledge:documents")
    assert bridge.chroma_store().count(identity) == 1

    result = svc.replication.delete(peer_b, "knowledge:documents")
    assert result["documents_removed"] == 1
    assert bridge.chroma_store().count(identity) == 0
    rows = [r for r in bridge.registry().list_documents() if r["collection"] == identity]
    assert rows == []
