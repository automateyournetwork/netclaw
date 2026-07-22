"""ChromaDB dense-vector store for rag-mcp.

PersistentClient at <RAG_DATA_DIR>/chroma — physically separate from the
Memory MCP's store at ~/.openclaw/memory/ (FR-030). Collections: 'documents'
plus on-demand 'snapshot_<label>_<ISO8601>' (FR-015), cosine space.
"""

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)
logging.getLogger("chromadb").setLevel(logging.WARNING)


class ChromaStore:
    def __init__(self, chroma_dir: str):
        import chromadb
        from chromadb.config import Settings

        self._client = chromadb.PersistentClient(
            path=str(chroma_dir), settings=Settings(anonymized_telemetry=False)
        )

    def _collection(self, name: str):
        return self._client.get_or_create_collection(
            name=name, metadata={"hnsw:space": "cosine"}
        )

    def collection_names(self) -> List[str]:
        return [c.name for c in self._client.list_collections()]

    def count(self, collection: str) -> int:
        try:
            return self._collection(collection).count()
        except Exception:
            return 0

    def add_chunks(
        self,
        collection: str,
        ids: List[str],
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        # Chroma metadata values must be str/int/float/bool — drop Nones.
        clean = [{k: v for k, v in m.items() if v is not None} for m in metadatas]
        self._collection(collection).add(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=clean
        )

    def query(
        self,
        collection: str,
        query_embedding: List[float],
        n_results: int,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Returns [{chunk_id, text, metadata, score}] with score = 1 - cosine distance."""
        coll = self._collection(collection)
        total = coll.count()
        if total == 0:
            return []
        res = coll.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, total),
            where=where or None,
            include=["documents", "metadatas", "distances"],
        )
        out = []
        for cid, text, meta, dist in zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0]
        ):
            out.append(
                {
                    "chunk_id": cid,
                    "text": text,
                    "metadata": meta or {},
                    "score": round(1.0 - dist, 4),
                }
            )
        return out

    def get_document_chunks(self, collection: str, document_id: str) -> List[Dict[str, Any]]:
        coll = self._collection(collection)
        res = coll.get(where={"document_id": document_id}, include=["documents", "metadatas"])
        return [
            {"chunk_id": cid, "text": text, "metadata": meta or {}}
            for cid, text, meta in zip(res["ids"], res["documents"], res["metadatas"])
        ]

    def delete_document(self, collection: str, document_id: str) -> int:
        coll = self._collection(collection)
        existing = coll.get(where={"document_id": document_id})
        n = len(existing["ids"])
        if n:
            coll.delete(where={"document_id": document_id})
        return n

    def update_document_metadata(
        self, collection: str, document_id: str, updates: Dict[str, Any]
    ) -> int:
        """Apply metadata field updates to every chunk of a document."""
        coll = self._collection(collection)
        existing = coll.get(where={"document_id": document_id}, include=["metadatas"])
        ids = existing["ids"]
        if not ids:
            return 0
        metas = []
        for meta in existing["metadatas"]:
            merged = dict(meta or {})
            merged.update({k: v for k, v in updates.items() if v is not None})
            metas.append(merged)
        coll.update(ids=ids, metadatas=metas)
        return len(ids)

    def delete_collection(self, collection: str) -> None:
        try:
            self._client.delete_collection(collection)
        except Exception:
            pass

    # ---- replication (feature 065) --------------------------------------

    def get_chunks_page(
        self, collection: str, offset: int, limit: int
    ) -> Dict[str, Any]:
        """Paginated export of a whole collection's raw chunks (source side of
        replication). Deterministic order (Chroma's own stored order), so the
        same {offset, limit} always returns the same page — safe to retry."""
        coll = self._collection(collection)
        res = coll.get(limit=limit, offset=offset,
                       include=["embeddings", "documents", "metadatas"])
        embeddings = res.get("embeddings")
        return {
            "ids": res["ids"],
            "embeddings": [list(map(float, v)) for v in embeddings]
                           if embeddings is not None else [],
            "texts": res["documents"] or [],
            "metadatas": res["metadatas"] or [],
        }

    def upsert_chunks(
        self,
        collection: str,
        ids: List[str],
        embeddings: List[List[float]],
        texts: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """Idempotent write for replication (FR-005): unlike add_chunks()'s
        add() (which errors/duplicates on a repeated id), upsert() applied to
        the same batch twice is a no-op the second time — safe for a single
        retried page without restarting the whole job."""
        clean = [{k: v for k, v in m.items() if v is not None} for m in metadatas]
        self._collection(collection).upsert(
            ids=ids, embeddings=embeddings, documents=texts, metadatas=clean
        )

    def promote_staging(self, staging_name: str, stable_name: str) -> None:
        """Atomic-enough rename-on-verify for re-sync (D7): drop the previous
        stable collection (if any), then rename the verified staging collection
        into the stable name every query/replicate call actually addresses."""
        try:
            self._client.delete_collection(stable_name)
        except Exception:
            pass
        staging = self._collection(staging_name)
        staging.modify(name=stable_name)
