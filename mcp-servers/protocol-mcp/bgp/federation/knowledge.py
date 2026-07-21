"""Knowledge capability cards & eN2N knowledge selection (feature 064).

Advertisement: build content-free A2A-style entries — one per RAG collection —
from the feature-062 registry (`~/.openclaw/rag/rag.db`, `documents` table), read
directly (cheapest path; no MCP spawn). Only ready documents are advertised, and
only registry metadata (title, doc_type, collection, page/chunk counts) is used —
never chunk text, embeddings, source paths, hashes, or capture commands.

Selection (eN2N): choosing which advertised collection answers a query lives here
too (finding H2 — NOT the iN2N `router.py`). It is added in a later task (US2) as
`select_collection()`; this module currently ships the advertisement builder.
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

RETRIEVAL_METHOD = "n2n/knowledge/query"

# Registry columns that are safe to read for advertisement. Everything else in
# the documents table (source_path, content_hash, capture_commands, ...) is
# deliberately NOT read, so no path/secret can reach the card.
_SAFE_KEYS = {"collection_id", "name", "description", "tags",
              "doc_count", "page_count", "chunk_count", "retrieval"}


def _rag_db_path() -> Path:
    base = os.environ.get("RAG_DATA_DIR", "~/.openclaw/rag")
    return Path(os.path.expanduser(base)) / "rag.db"


def _topic_only_default() -> bool:
    return os.environ.get("N2N_KNOWLEDGE_TOPIC_ONLY", "").strip().lower() in (
        "1", "true", "yes", "on")


def build_entries(topic_only: Optional[bool] = None,
                  db_path: Optional[Path] = None) -> list:
    """Return one content-free knowledge entry per RAG collection with >=1 ready
    document. Empty list if there is no RAG db or no ready documents (absence,
    not an empty entry). `topic_only` omits document titles from the description
    (research D5); defaults to the N2N_KNOWLEDGE_TOPIC_ONLY env toggle."""
    if topic_only is None:
        topic_only = _topic_only_default()
    path = Path(db_path) if db_path else _rag_db_path()
    if not path.exists():
        return []
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT collection, title, doc_type, page_count, chunk_count "
            "FROM documents WHERE ingest_status='ready'").fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    by_coll: dict = {}
    for r in rows:
        coll = r["collection"] or "documents"
        agg = by_coll.setdefault(coll, {"titles": [], "doc_types": set(),
                                        "doc_count": 0, "page_count": 0,
                                        "chunk_count": 0})
        if r["title"] and r["title"] not in agg["titles"]:
            agg["titles"].append(r["title"])
        if r["doc_type"]:
            agg["doc_types"].add(r["doc_type"])
        agg["doc_count"] += 1
        agg["page_count"] += int(r["page_count"] or 0)
        agg["chunk_count"] += int(r["chunk_count"] or 0)

    entries = []
    for coll in sorted(by_coll):
        agg = by_coll[coll]
        tags = sorted(agg["doc_types"])
        if topic_only:
            desc = f"Knowledge collection '{coll}'"
            if tags:
                desc += " covering " + ", ".join(tags)
            desc += f"; {agg['doc_count']} document(s)."
        else:
            desc = f"Knowledge collection '{coll}'"
            if agg["titles"]:
                desc += ": " + "; ".join(agg["titles"][:20])
            if tags:
                desc += f" ({', '.join(tags)})"
            desc += "."
        entries.append({
            "collection_id": f"knowledge:{coll}",
            "name": f"Knowledge: {coll}",
            "description": desc,
            "tags": tags,
            "doc_count": agg["doc_count"],
            "page_count": agg["page_count"],
            "chunk_count": agg["chunk_count"],
            "retrieval": RETRIEVAL_METHOD,
        })
    return entries


def _match_threshold() -> float:
    try:
        return float(os.environ.get("N2N_KNOWLEDGE_MATCH_THRESHOLD", "0.5"))
    except ValueError:
        return 0.5


def _embed_texts(texts: list):
    """Embed texts with the RAG embedder (feature 062). Lazy-loaded and cached;
    returns a list of vectors, or None if the embedder cannot be loaded — the
    caller then falls back to lexical scoring so a missing model never breaks the
    daemon. Deterministic: the same model yields the same vectors (FR-005)."""
    global _EMBEDDER
    try:
        if _EMBEDDER is None:
            from sentence_transformers import SentenceTransformer  # heavy, lazy
            model = os.environ.get("RAG_EMBED_MODEL", "all-MiniLM-L6-v2")
            _EMBEDDER = SentenceTransformer(model)
        return [list(map(float, v)) for v in _EMBEDDER.encode(texts)]
    except Exception:
        return None


_EMBEDDER = None


def _cosine(a: list, b: list) -> float:
    import math
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def _lexical(query: str, desc: str) -> float:
    """Deterministic token-overlap (Jaccard) fallback when no embedder is loaded."""
    q = {w for w in query.lower().split() if len(w) > 2}
    d = {w for w in desc.lower().split() if len(w) > 2}
    if not q or not d:
        return 0.0
    return len(q & d) / len(q | d)


def score_query(query: str, descriptions: list) -> list:
    """Similarity of `query` to each description, in [0,1]. Embedding cosine when
    the embedder loads (deterministic), else lexical overlap."""
    if not descriptions:
        return []
    vecs = _embed_texts([query] + list(descriptions))
    if vecs:
        qv, dvs = vecs[0], vecs[1:]
        return [max(0.0, _cosine(qv, dv)) for dv in dvs]
    return [_lexical(query, d) for d in descriptions]


def select_collection(query: str, sources: list, threshold: Optional[float] = None) -> dict:
    """Choose which advertised collection answers `query`. `sources` is a list of
    {"source": "local"|<peer_identity>, "entries": [knowledge entries]}. Returns a
    Knowledge Route Decision (data-model.md): highest-scoring collection at/above
    the threshold, deterministic tiebreak by ascending source then collection_id;
    fallback to the model when nothing clears the threshold (FR-005/FR-006). Never
    emits a peer/collection when nothing matches (no fabricated source)."""
    if threshold is None:
        threshold = _match_threshold()
    cands = [(s["source"], e) for s in sources for e in s.get("entries", [])]
    if not cands:
        return {"query": query, "target": "model", "peer_identity": None,
                "collection_id": None, "score": 0.0,
                "rationale": "no advertised collections"}
    scores = score_query(query, [e["description"] for _, e in cands])
    ranked = sorted(
        zip(scores, cands),
        key=lambda x: (-x[0], str(x[1][0]), x[1][1]["collection_id"]))
    best_score, (src, entry) = ranked[0]
    if best_score < threshold:
        return {"query": query, "target": "model", "peer_identity": None,
                "collection_id": None, "score": round(best_score, 4),
                "rationale": f"best score {best_score:.4f} < threshold {threshold}"}
    target = "local" if src == "local" else "peer"
    return {"query": query, "target": target,
            "peer_identity": None if target == "local" else src,
            "collection_id": entry["collection_id"], "score": round(best_score, 4),
            "rationale": f"{target} collection {entry['collection_id']} scored "
                         f"{best_score:.4f} (>= {threshold}); deterministic tiebreak "
                         f"by source then collection_id"}


def assert_entry_clean(entry: dict) -> None:
    """Defense in depth (FR-002): a knowledge entry MUST carry only the allowed
    content-free keys — no source path, hash, chunk text, or other registry
    column can slip onto the card. Raises ValueError on any unexpected key."""
    extra = set(entry) - _SAFE_KEYS
    if extra:
        raise ValueError(
            f"knowledge entry has forbidden key(s) {sorted(extra)} — only "
            f"{sorted(_SAFE_KEYS)} may be advertised (FR-002)")
