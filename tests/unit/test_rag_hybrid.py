"""Unit tests for hybrid retrieval: RRF math, BM25 exact-token findability,
reranker passthrough. Fully offline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "rag-mcp"))

import tempfile  # noqa: E402

from retrieval.hybrid import reciprocal_rank_fusion  # noqa: E402
from retrieval.reranker import Reranker  # noqa: E402
from storage.bm25_store import BM25Store, tokenize  # noqa: E402


# ---------------------------------------------------------------------
# RRF math against hand-computed values
# ---------------------------------------------------------------------
def test_rrf_hand_computed():
    dense = ["a", "b", "c"]
    keyword = ["b", "a", "d"]
    fused = reciprocal_rank_fusion([dense, keyword], k=60)
    scores = {f["chunk_id"]: f["rrf_score"] for f in fused}
    assert scores["a"] == round(1 / 61 + 1 / 62, 6)
    assert scores["b"] == round(1 / 62 + 1 / 61, 6)
    assert scores["c"] == round(1 / 63, 6)
    assert scores["d"] == round(1 / 63, 6)
    # a and b tie -> deterministic tie-break by chunk_id
    assert [f["chunk_id"] for f in fused][:2] == ["a", "b"]
    # single-leg items rank below dual-leg items
    assert [f["chunk_id"] for f in fused][2:] == ["c", "d"]


def test_rrf_empty_legs():
    assert reciprocal_rank_fusion([[], []]) == []
    fused = reciprocal_rank_fusion([["x"], []])
    assert fused[0]["chunk_id"] == "x"


# ---------------------------------------------------------------------
# BM25 tokenizer + exact-token findability (FR-021)
# ---------------------------------------------------------------------
def test_tokenizer_preserves_networking_tokens():
    text = "interface Gi0/0/1 has 192.0.2.0/24 configured; see CVE-2026-1234."
    tokens = tokenize(text)
    assert "gi0/0/1" in tokens
    assert "192.0.2.0/24" in tokens
    assert "cve-2026-1234" in tokens  # trailing period stripped, hyphen kept


def test_bm25_finds_exact_cli_token_when_dense_misses():
    with tempfile.TemporaryDirectory() as tmp:
        store = BM25Store(tmp)
        store.rebuild(
            "documents",
            [
                {"chunk_id": "c1", "text": "Configure interface Gi0/0/1 with no shutdown"},
                {"chunk_id": "c2", "text": "General overview of wireless architecture"},
                {"chunk_id": "c3", "text": "router bgp 65000 neighbor setup"},
            ],
        )
        hits = store.search("documents", "Gi0/0/1", n_results=5)
        assert hits and hits[0]["chunk_id"] == "c1"

        hits = store.search("documents", "router bgp 65000", n_results=5)
        assert hits[0]["chunk_id"] == "c3"

        # Adversarial "dense miss" scenario: fuse an empty dense leg with BM25
        fused = reciprocal_rank_fusion([[], [h["chunk_id"] for h in hits]])
        assert fused[0]["chunk_id"] == "c3"


def test_bm25_persistence_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = BM25Store(tmp)
        store.rebuild("documents", [{"chunk_id": "c1", "text": "snmp community string"}])
        # Fresh instance loads from pickle
        store2 = BM25Store(tmp)
        hits = store2.search("documents", "snmp community", n_results=5)
        assert hits[0]["chunk_id"] == "c1"
        # Removal persists too
        store2.remove_chunks("documents", ["c1"])
        store3 = BM25Store(tmp)
        assert store3.search("documents", "snmp community", n_results=5) == []


# ---------------------------------------------------------------------
# Reranker toggle behavior (FR-022/FR-024)
# ---------------------------------------------------------------------
def _candidates():
    return [
        {"chunk_id": "c1", "text": "highly relevant text", "metadata": {}, "rrf_score": 0.03, "dense_score": 0.9},
        {"chunk_id": "c2", "text": "weak match", "metadata": {}, "rrf_score": 0.02, "dense_score": 0.2},
    ]


def test_reranker_disabled_passthrough_keeps_fusion_order():
    rr = Reranker("any-model", enabled=False)
    top = rr.rerank("query", _candidates(), k=2, relevance_floor=0.3)
    assert [c["chunk_id"] for c in top] == ["c1", "c2"]
    assert top[0]["score"] == 0.9 and top[0]["low_confidence"] is False
    assert top[1]["score"] == 0.2 and top[1]["low_confidence"] is True  # flagged, not dropped


def test_reranker_unavailable_model_degrades_gracefully():
    rr = Reranker("nonexistent/model-that-cannot-load", enabled=True)
    rr._failed = True  # simulate load failure without touching the network
    top = rr.rerank("query", _candidates(), k=1, relevance_floor=0.3)
    assert top[0]["chunk_id"] == "c1"


def test_reranker_empty_candidates():
    rr = Reranker("any", enabled=False)
    assert rr.rerank("q", [], k=5, relevance_floor=0.3) == []
