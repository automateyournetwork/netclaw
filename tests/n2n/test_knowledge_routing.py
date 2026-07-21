"""Feature 064 US2/US3: knowledge-aware routing + the n2n/knowledge/query method.

Covers T016 (deterministic cosine selection + tiebreak), T017 (peer/local/model
targets + threshold), T018 (granted possession-tier retrieval returns a composed
cited answer), T022 (tier-0 + default-deny denials, audited), T023 (no existence
oracle + one audit record on success).
"""

import asyncio
import json

import pytest

from bgp.federation import knowledge as kn


# ---- fixtures -------------------------------------------------------------

def _entry(cid, desc):
    return {"collection_id": cid, "name": cid, "description": desc, "tags": [],
            "doc_count": 1, "page_count": 1, "chunk_count": 1,
            "retrieval": "n2n/knowledge/query"}


@pytest.fixture
def fixed_embedder(monkeypatch):
    """Deterministic stand-in for the embedder: map known texts to fixed vectors
    so cosine scores are stable and assertable (T016)."""
    vecs = {
        "book about network automation": [1.0, 0.0],
        "Automate Your Network — network automation, Ansible": [0.98, 0.02],
        "Kubernetes operations and Helm charts": [0.0, 1.0],
    }
    monkeypatch.setattr(kn, "_embed_texts",
                        lambda texts: [vecs.get(t, [0.5, 0.5]) for t in texts])
    return vecs


# ---- T016 / T017: selection ----------------------------------------------

def test_deterministic_selection_and_target(fixed_embedder):
    sources = [
        {"source": "as65099-9.9.9.9", "entries": [
            _entry("knowledge:book", "Automate Your Network — network automation, Ansible")]},
        {"source": "local", "entries": [
            _entry("knowledge:k8s", "Kubernetes operations and Helm charts")]},
    ]
    d1 = kn.select_collection("book about network automation", sources, threshold=0.5)
    d2 = kn.select_collection("book about network automation", sources, threshold=0.5)
    assert d1 == d2                                   # deterministic
    assert d1["target"] == "peer"
    assert d1["peer_identity"] == "as65099-9.9.9.9"
    assert d1["collection_id"] == "knowledge:book"
    assert d1["score"] >= 0.5


def test_local_wins_when_highest(fixed_embedder):
    sources = [
        {"source": "local", "entries": [
            _entry("knowledge:book", "Automate Your Network — network automation, Ansible")]},
        {"source": "as65099-9.9.9.9", "entries": [
            _entry("knowledge:k8s", "Kubernetes operations and Helm charts")]},
    ]
    d = kn.select_collection("book about network automation", sources, threshold=0.5)
    assert d["target"] == "local" and d["peer_identity"] is None


def test_below_threshold_falls_back_to_model(fixed_embedder):
    sources = [{"source": "as65099-9.9.9.9", "entries": [
        _entry("knowledge:k8s", "Kubernetes operations and Helm charts")]}]
    d = kn.select_collection("book about network automation", sources, threshold=0.5)
    assert d["target"] == "model"
    assert d["peer_identity"] is None and d["collection_id"] is None


def test_tiebreak_is_stable(monkeypatch):
    # identical scores → deterministic tiebreak by ascending source then id
    monkeypatch.setattr(kn, "_embed_texts", lambda texts: [[1.0, 0.0] for _ in texts])
    sources = [
        {"source": "as65099-9.9.9.9", "entries": [_entry("knowledge:z", "same")]},
        {"source": "as65007-7.7.7.7", "entries": [_entry("knowledge:a", "same")]},
    ]
    d = kn.select_collection("q", sources, threshold=0.0)
    assert d["peer_identity"] == "as65007-7.7.7.7"     # lower source wins tie


def test_lexical_fallback_when_no_embedder(monkeypatch):
    monkeypatch.setattr(kn, "_embed_texts", lambda texts: None)   # embedder unavailable
    sources = [{"source": "local", "entries": [
        _entry("knowledge:book", "network automation ansible book guide")]}]
    d = kn.select_collection("network automation book", sources, threshold=0.1)
    assert d["target"] == "local" and d["score"] > 0.0


# ---- handler tests (US2 T018 / US3 T022, T023) ----------------------------

def _service(manager, monkeypatch, tmp_path):
    """A FederationService wired enough to exercise handle_knowledge_query."""
    from bgp.federation.service import FederationService
    monkeypatch.setenv("RAG_DATA_DIR", str(tmp_path / "norag"))  # no real rag
    svc = FederationService(local_as=65001, router_id="4.4.4.4", manager=manager)
    # advertise one collection regardless of rag.db (visible-set source)
    monkeypatch.setattr(kn, "build_entries",
                        lambda *a, **k: [_entry("knowledge:documents", "the book")])
    return svc


class _Chan:
    def __init__(self, peer, attestation="possession"):
        self.peer_identity = peer
        self.attestation = attestation


def _federate(manager, peer_as=65099, rid="9.9.9.9"):
    manager.local_consent(peer_as, rid)
    manager.remote_consent(peer_as, rid)
    return f"as{peer_as}-{rid}"


def test_tier0_peer_denied(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    from bgp.federation.channel import RpcError
    with pytest.raises(RpcError):
        asyncio.run(svc.invoker.handle_knowledge_query(
            _Chan(peer, attestation="self-asserted"),
            {"collection_id": "knowledge:documents", "query": "hi"}))


def test_no_grant_denied_default_deny(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    from bgp.federation.channel import RpcError
    with pytest.raises(RpcError):   # possession tier but no grant → not_allowlisted
        asyncio.run(svc.invoker.handle_knowledge_query(
            _Chan(peer), {"collection_id": "knowledge:documents", "query": "hi"}))


def test_unknown_collection_is_not_an_oracle(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    svc.authz.grant(peer, "knowledge", "knowledge:documents")
    # hidden/unknown id → not_found shape, identical whether it exists or not
    res = asyncio.run(svc.invoker.handle_knowledge_query(
        _Chan(peer), {"collection_id": "knowledge:secret", "query": "hi"}))
    assert res["not_found"] is True and res["answer"] is None


def test_granted_retrieval_returns_composed_answer(manager, monkeypatch, tmp_path):
    svc = _service(manager, monkeypatch, tmp_path)
    peer = _federate(manager)
    svc.authz.grant(peer, "knowledge", "knowledge:documents")

    async def fake_turn(prompt, **kw):
        return ("Automate Your Network is about network automation (Preface p.13).", 42)
    import bgp.federation.gateway as gw
    monkeypatch.setattr(gw, "run_agent_turn", fake_turn)

    res = asyncio.run(svc.invoker.handle_knowledge_query(
        _Chan(peer), {"collection_id": "knowledge:documents",
                      "query": "summarize the book", "request_id": "r1"}))
    assert "Automate Your Network" in res["answer"]
    assert res["provenance"]["peer"] == "as65001-4.4.4.4"
    assert res["provenance"]["collection_id"] == "knowledge:documents"
    # exactly one success audit row for this collection
    rows = manager._conn.execute(
        "SELECT outcome FROM remote_invocation_record WHERE peer_identity=? "
        "AND target_type='knowledge' AND target_name='knowledge:documents' "
        "AND outcome='success'", (peer,)).fetchall()
    assert len(rows) == 1
