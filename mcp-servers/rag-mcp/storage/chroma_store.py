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
