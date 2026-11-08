"""Collection aliases for investigation snapshots. Fakes only; no model download."""

import importlib
from pathlib import Path

import pytest

sys_path = Path(__file__).resolve().parents[2] / "mcp-servers" / "rag-mcp"


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    import sys
    sys.path.insert(0, str(sys_path))
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("RAG_DATA_DIR", str(tmp_path_factory.mktemp("rag-181")))
        module = importlib.import_module("rag_mcp_server")
        yield module


def _hit(chunk_id, text, score, collection, **meta):
    metadata = {"title": text, "doc_type": "other", "kind": "snapshot", "collection": "not-the-source"}
    metadata.update(meta)
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": metadata,
        "dense_score": score,
        "rrf_score": score,
    }


def _rows():
    return [
        {"kind": "snapshot", "ingest_status": "ready", "collection": "snapshot_a"},
        {"kind": "snapshot", "ingest_status": "pending", "collection": "snapshot_pending"},
        {"kind": "snapshot", "ingest_status": "ready", "collection": ""},
        {"kind": "snapshot", "ingest_status": "ready", "collection": None},
        {"kind": "document", "ingest_status": "ready", "collection": "documents"},
        {"kind": "snapshot", "ingest_status": "error", "collection": "snapshot_error"},
        {"kind": "snapshot", "ingest_status": "ready", "collection": "snapshot_a"},
        {"kind": "replica", "ingest_status": "ready", "collection": "replica_x"},
        {"kind": "snapshot", "ingest_status": "ready", "collection": "snapshot_b"},
    ]


def _install(server, monkeypatch, rows, counts, hits):
    seen = {"embed": 0, "retrieve": []}

    def list_documents(kind=None):
        return rows

    def count(name):
        value = counts[name]
        if isinstance(value, Exception):
            raise value
        return value

    def retrieve(_chroma, _bm25, collection, _query, _embedding, where=None):
        seen["retrieve"].append(collection)
        return [dict(hit) for hit in hits.get(collection, [])]

    def embed_query(_query):
        seen["embed"] += 1
        return [0.0]

    def rerank(_query, candidates, k, floor):
        # Preserve input order. The alias search has to sort by score itself.
        out = []
        for candidate in candidates[:k]:
            score = candidate["dense_score"]
            out.append({**candidate, "score": score, "low_confidence": score < floor})
        return out

    monkeypatch.setattr(server.registry, "list_documents", list_documents)
    monkeypatch.setattr(server.chroma, "count", count)
    monkeypatch.setattr(server, "hybrid_retrieve", retrieve)
    monkeypatch.setattr(server.embedder, "embed_query", embed_query)
    monkeypatch.setattr(server.reranker, "rerank", rerank)
    return seen


@pytest.mark.parametrize("alias", ["investigations", "snapshots", "cases", " investigations "])
def test_snapshot_aliases_search_ready_collections_only(server, monkeypatch, alias):
    hits = {
        "snapshot_a": [_hit("a1", "alpha", 0.4, "snapshot_a")],
        "snapshot_b": [_hit("b1", "beta", 0.8, "snapshot_b")],
    }
    seen = _install(server, monkeypatch, _rows(), {"snapshot_a": 1, "snapshot_b": 1}, hits)
    response = server._do_search("prior outage", k=5, collection=alias)
    assert response["success"] is True
    assert response["error"] is None
    assert seen["retrieve"] == ["snapshot_a", "snapshot_b"]
    assert [hit["chunk_id"] for hit in response["data"]["results"]] == ["b1", "a1"]
    assert response["data"]["collection"] == alias
    assert response["data"]["corpus_empty"] is False


@pytest.mark.parametrize("alias", ["all", "*"])
def test_all_alias_includes_documents_and_snapshots(server, monkeypatch, alias):
    hits = {
        "documents": [_hit("d1", "guide", 0.99, "documents", kind="document", doc_type="vendor")],
        "snapshot_a": [_hit("a1", "alpha", 0.4, "snapshot_a")],
        "snapshot_b": [_hit("b1", "beta", 0.5, "snapshot_b")],
    }
    counts = {"documents": 2, "snapshot_a": 1, "snapshot_b": 1}
    seen = _install(server, monkeypatch, _rows(), counts, hits)
    response = server._do_search("guide", k=1, collection=alias)
    assert seen["retrieve"] == ["documents", "snapshot_a", "snapshot_b"]
    result = response["data"]["results"]
    assert [hit["chunk_id"] for hit in result] == ["d1"]
    assert result[0]["collection"] == "documents"
    assert result[0]["doc_type"] == "vendor"


def test_merge_returns_top_k_by_score_across_collections(server, monkeypatch):
    hits = {
        "snapshot_a": [_hit("a1", "alpha", 0.5, "snapshot_a", doc_type="customer")],
        "snapshot_b": [
            _hit("b1", "beta", 0.95, "snapshot_b", doc_type="customer"),
            _hit("b2", "gamma", 0.2, "snapshot_b", doc_type="vendor"),
        ],
    }
    _install(server, monkeypatch, _rows(), {"snapshot_a": 1, "snapshot_b": 3}, hits)
    response = server._do_search("outage", k=2, collection="investigations")
    results = response["data"]["results"]
    assert [hit["chunk_id"] for hit in results] == ["b1", "a1"]
    assert [hit["collection"] for hit in results] == ["snapshot_b", "snapshot_a"]
    first = results[0]
    assert first["chunk_text"] == "beta"
    assert first["score"] == 0.95
    assert first["title"] == "beta"
    assert "citation" in first
    assert "low_confidence" in first
    assert "ingest_ts" in first
    filtered = server._do_search(
        "outage", k=5, collection="investigations", filters={"doc_type": "vendor"}
    )
    assert [hit["chunk_id"] for hit in filtered["data"]["results"]] == ["b2"]


def test_literal_collection_is_unchanged(server, monkeypatch):
    def refuse_registry(kind=None):
        raise AssertionError("literal search must not expand aliases")

    seen = _install(
        server,
        monkeypatch,
        [],
        {"Investigations": 1, "snapshot_exact": 0},
        {"Investigations": [_hit("c1", "literal", 0.7, "Investigations")]},
    )
    monkeypatch.setattr(server.registry, "list_documents", refuse_registry)
    found = server._do_search("literal", k=3, collection="Investigations")
    assert seen["retrieve"] == ["Investigations"]
    assert found["data"]["results"][0]["chunk_id"] == "c1"
    assert "collection" not in found["data"]["results"][0]
    assert found["data"]["collection"] == "Investigations"
    empty = server._do_search("anything", collection="snapshot_exact")
    assert empty["data"]["corpus_empty"] is True
    assert empty["data"]["results"] == []
    assert empty["data"]["message"] == "Collection 'snapshot_exact' is empty — nothing indexed yet."
    assert set(empty["data"]) == {"results", "corpus_empty", "collection", "latency_ms", "message"}


def test_no_snapshots_returns_the_empty_corpus_shape(server, monkeypatch):
    seen = _install(server, monkeypatch, [], {}, {})
    response = server._do_search("prior case", collection="investigations")
    assert response["success"] is True
    assert response["error"] is None
    assert response["data"]["results"] == []
    assert response["data"]["corpus_empty"] is True
    assert response["data"]["collection"] == "investigations"
    assert response["data"]["latency_ms"] == 0
    assert response["data"]["message"] == "No investigation snapshots are indexed."
    assert set(response["data"]) == {"results", "corpus_empty", "collection", "latency_ms", "message"}
    assert seen["embed"] == 0
    assert seen["retrieve"] == []


def test_unreadable_snapshot_is_skipped(server, monkeypatch):
    rows = [
        {"kind": "snapshot", "ingest_status": "ready", "collection": "snapshot_broken"},
        {"kind": "snapshot", "ingest_status": "ready", "collection": "snapshot_ok"},
    ]
    hits = {"snapshot_ok": [_hit("ok1", "kept", 0.6, "snapshot_ok")]}
    counts = {"snapshot_broken": OSError("secret-index-path"), "snapshot_ok": 1}
    _install(server, monkeypatch, rows, counts, hits)
    response = server._do_search("kept", collection="cases")
    assert response["success"] is True
    assert [hit["chunk_id"] for hit in response["data"]["results"]] == ["ok1"]
    assert "secret-index-path" not in str(response)


def test_all_alias_document_index_failure_is_fatal(server, monkeypatch):
    rows = [{"kind": "snapshot", "ingest_status": "ready", "collection": "snapshot_ok"}]
    counts = {"documents": OSError("secret-doc-index"), "snapshot_ok": 1}
    seen = _install(server, monkeypatch, rows, counts, {"snapshot_ok": [_hit("ok1", "kept", 0.6, "snapshot_ok")]})
    response = server._do_search("kept", collection="all")
    assert response["success"] is False
    assert response["error"]["code"] == "STORAGE_UNAVAILABLE"
    assert "corpus_empty" not in str(response)
    assert "secret-doc-index" not in str(response)
    assert seen["retrieve"] == []


def test_all_alias_skips_a_broken_snapshot_and_keeps_documents(server, monkeypatch):
    rows = [{"kind": "snapshot", "ingest_status": "ready", "collection": "snapshot_broken"}]
    counts = {"documents": 1, "snapshot_broken": OSError("secret-index-path")}
    hits = {"documents": [_hit("d1", "guide", 0.7, "documents", kind="document")]}
    seen = _install(server, monkeypatch, rows, counts, hits)
    response = server._do_search("guide", collection="*")
    assert response["success"] is True
    assert [hit["chunk_id"] for hit in response["data"]["results"]] == ["d1"]
    assert seen["retrieve"] == ["documents"]
    assert "secret-index-path" not in str(response)
