"""Hybrid retrieval for rag-mcp (FR-021).

Dense (ChromaDB) and BM25 legs each retrieve a candidate set; results are
fused by reciprocal rank fusion (k=60). The BM25 leg guarantees exact-match
networking tokens (CLI syntax, CVE/RFC IDs, interface names) stay findable
when embeddings miss them.
"""

from typing import Dict, List

RRF_K = 60
LEG_DEPTH = 20  # each leg retrieves top-20 before fusion


def reciprocal_rank_fusion(
    ranked_lists: List[List[str]], k: int = RRF_K
) -> List[Dict]:
    """Fuse ranked chunk-id lists. Returns [{chunk_id, rrf_score}] descending,
    with deterministic tie-breaking (score, then chunk_id)."""
    scores: Dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, chunk_id in enumerate(ranked, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)
    fused = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [{"chunk_id": cid, "rrf_score": round(score, 6)} for cid, score in fused]


def hybrid_retrieve(
    chroma_store,
    bm25_store,
    collection: str,
    query: str,
    query_embedding: List[float],
    where: Dict = None,
    depth: int = LEG_DEPTH,
) -> List[Dict]:
    """Run both legs and fuse. Returns fused candidates as
    [{chunk_id, rrf_score, text, metadata, dense_score}] — text/metadata
    hydrated from Chroma for every fused candidate."""
    dense_hits = chroma_store.query(collection, query_embedding, n_results=depth, where=where)
    dense_by_id = {h["chunk_id"]: h for h in dense_hits}
    dense_ranked = [h["chunk_id"] for h in dense_hits]

    bm25_hits = bm25_store.search(collection, query, n_results=depth)
    bm25_ranked = [h["chunk_id"] for h in bm25_hits]

    fused = reciprocal_rank_fusion([dense_ranked, bm25_ranked])[:depth]

    # Hydrate text/metadata for BM25-only candidates from Chroma
    missing = [f["chunk_id"] for f in fused if f["chunk_id"] not in dense_by_id]
    if missing:
        coll = chroma_store._collection(collection)
        got = coll.get(ids=missing, include=["documents", "metadatas"])
        for cid, text, meta in zip(got["ids"], got["documents"], got["metadatas"]):
            dense_by_id[cid] = {"chunk_id": cid, "text": text, "metadata": meta or {}, "score": 0.0}

    results = []
    for f in fused:
        hit = dense_by_id.get(f["chunk_id"])
        if hit is None:  # chunk deleted between legs — skip gracefully
            continue
        results.append(
            {
                "chunk_id": f["chunk_id"],
                "rrf_score": f["rrf_score"],
                "text": hit["text"],
                "metadata": hit["metadata"],
                "dense_score": hit["score"],
            }
        )
    return results
