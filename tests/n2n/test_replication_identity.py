"""Feature 065 US2: replica local identity (FR-016) — never collides across
source peers, never merges into a locally-authored collection.

Covers T027.
"""

from bgp.federation.replication import local_replica_identity


def test_identity_derived_from_peer_and_collection():
    a = local_replica_identity("as65001-1.1.1.1", "knowledge:documents")
    b = local_replica_identity("as65099-9.9.9.9", "knowledge:documents")
    assert a != b, "same collection_id from two different peers must not collide"


def test_identity_is_deterministic():
    a1 = local_replica_identity("as65001-1.1.1.1", "knowledge:documents")
    a2 = local_replica_identity("as65001-1.1.1.1", "knowledge:documents")
    assert a1 == a2


def test_identity_is_a_valid_chroma_collection_name(monkeypatch, tmp_path):
    """Chroma collection names are restricted to [a-zA-Z0-9._-] — collection_id
    values (e.g. 'knowledge:documents') and peer identities contain ':' and
    '.', so the derived identity must be sanitized enough to actually work."""
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "rag"))
    from bgp.federation import chroma_store_bridge as bridge
    identity = local_replica_identity("as65099-9.9.9.9", "knowledge:documents")
    store = bridge.chroma_store()
    store.upsert_chunks(identity, ["c1"], [[0.1, 0.1]], ["t"], [{"a": 1}])
    assert store.count(identity) == 1


def test_replica_never_overwrites_locally_authored_collection(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "rag"))
    from bgp.federation import chroma_store_bridge as bridge

    store = bridge.chroma_store()
    store.add_chunks("documents", ["local1"], [[0.5, 0.5]], ["mine"], [{"a": "mine"}])

    identity = local_replica_identity("as65099-9.9.9.9", "knowledge:documents")
    assert identity != "documents", "a replica's identity must never equal a local collection name"
    store.upsert_chunks(identity, ["r1"], [[0.9, 0.9]], ["theirs"], [{"a": "theirs"}])

    assert store.count("documents") == 1  # local collection untouched
    assert store.count(identity) == 1     # replica is its own, separate collection
