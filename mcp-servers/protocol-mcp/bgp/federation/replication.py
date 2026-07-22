"""Chroma-to-chroma vector replication over eN2N (feature 065).

Lets a consenting peer copy a claw's already-embedded RAG collection (feature
062) directly into its own local Chroma store — vectors, chunk text, and
metadata written as-is via Chroma's own upsert — instead of re-embedding the
source documents. Builds on feature 064's knowledge capability card (which
this feature extends with an `embedding_model` field) and its per-peer
visibility/no-existence-oracle rules.

Data access: like `knowledge.py`, this module reads and writes the RAG store
directly via `chroma_store_bridge` (which also backs `invocation.py`'s server
handlers) rather than importing rag-mcp's own Python package — see that
module's docstring for why.

Replicas do NOT get re-advertised as this claw's own knowledge, and are not
replicated onward to a third peer, unless the operator explicitly opts a
specific replica into re-sharing — there is no such opt-in path in v1 (a
deliberate boundary, not an oversight; see build_entries()'s exclusion of
`kind='replica'` rows in `knowledge.py`, which this module's manifest/batch
handlers reuse for visibility, so a replica is refused as not-found to a
third peer exactly like a nonexistent collection).
"""

import hashlib
import os
import time
import uuid
from typing import Optional

from . import chroma_store_bridge as _bridge

MAX_CHUNKS = int(os.environ.get("N2N_REPLICATION_MAX_CHUNKS", "20000"))
BATCH_SIZE = int(os.environ.get("N2N_REPLICATION_BATCH_SIZE", "200"))


def local_embedding_model() -> str:
    """The embedding model this claw's own RAG uses today — same default
    rag-mcp's own config.py uses, read directly (D5) rather than imported,
    since config.py is rag-mcp-package-local."""
    return os.environ.get("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")


def local_replica_identity(peer_identity: str, source_collection_id: str) -> str:
    """A replica's local Chroma collection name AND its registry `collection`
    value — always derived from source peer + source collection_id (never the
    bare collection_id alone), so replicas of same-named collections from two
    different source peers can never collide (D6/FR-016).

    Chroma collection names are restricted to `[a-zA-Z0-9._-]` (3-512 chars) —
    `peer_identity` (e.g. `as65099-9.9.9.9`) and `collection_id` (e.g.
    `knowledge:documents`) both contain characters outside that set, so `:`
    is replaced with `_` here. This substitution is deterministic and applied
    identically on every call, so identity derivation stays collision-free."""
    safe_collection_id = source_collection_id.replace(":", "_")
    return f"replica__{peer_identity}__{safe_collection_id}"


def _content_hash_for(peer_identity: str, collection_id: str, source_document_id: str) -> str:
    """A deterministic, synthetic content_hash for a replica's per-document
    registry row (real content hashing isn't available/needed here — this
    only needs to be unique per (peer, source collection, source document) so
    the registry's UNIQUE(content_hash, kind) index never collides across
    distinct replicas, including two peers' same-named collections)."""
    raw = f"{peer_identity}:{collection_id}:{source_document_id}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class ReplicationManager:
    """Operator-facing replication job orchestration: start / resync / delete.
    Wire-level manifest/batch handlers live on `Invoker` (invocation.py),
    mirroring where `n2n/knowledge/query` lives — this class is the async job
    layer on top, analogous to `ChatManager`."""

    def __init__(self, service):
        self.service = service

    def start(self, peer: str, collection_id: str) -> str:
        """Trigger a one-shot replication (FR-015): returns a task_id
        immediately; the actual transfer runs in the background."""
        task_id = self.service.tasks.create(
            direction="inbound", peer_identity=peer,
            target_type="knowledge_replicate", target_name=collection_id)
        self.service.tasks.run(task_id, self._worker(peer, collection_id, resync=False))
        return task_id

    def resync(self, peer: str, collection_id: str) -> str:
        """Trigger a manual re-sync of a previously replicated collection
        (FR-010): same checks as start(), full-replace on completion."""
        task_id = self.service.tasks.create(
            direction="inbound", peer_identity=peer,
            target_type="knowledge_replicate", target_name=collection_id)
        self.service.tasks.run(task_id, self._worker(peer, collection_id, resync=True))
        return task_id

    def delete(self, peer: str, collection_id: str) -> dict:
        """Remove a local replica entirely: registry rows + Chroma collection
        (FR-011 — an explicit, separate operator action; not a side effect of
        revoking the replication grant)."""
        identity = local_replica_identity(peer, collection_id)
        registry = _bridge.registry()
        removed = registry.delete_by_collection(identity)
        _bridge.chroma_store().delete_collection(identity)
        return {"peer": peer, "collection_id": collection_id,
                "local_identity": identity, "documents_removed": removed}

    def _worker(self, peer: str, collection_id: str, resync: bool):
        """Returns the `worker(progress)` coroutine TaskManager.run() drives.
        Fetch manifest -> refuse before any batch on mismatch/over-cap ->
        page through replicate_batch, writing via upsert_chunks() (idempotent
        retries, FR-005) -> verify count -> finalize (FR-006/FR-007)."""
        async def worker(progress):
            manifest = await self.service.invoker.fetch_replicate_manifest(peer, collection_id)
            if manifest.get("not_found"):
                raise ValueError(f"source collection '{collection_id}' not found or not visible")
            remote_model = manifest["embedding_model"]
            local_model = local_embedding_model()
            if remote_model != local_model:
                raise ValueError(
                    f"embedding model mismatch: source uses '{remote_model}', "
                    f"local RAG uses '{local_model}' — refusing before any transfer")
            total = int(manifest["chunk_count"])
            if total > MAX_CHUNKS:
                raise ValueError(
                    f"source collection has {total} chunks, exceeding the configured "
                    f"maximum of {MAX_CHUNKS} (N2N_REPLICATION_MAX_CHUNKS) — refusing "
                    f"before any transfer")

            identity = local_replica_identity(peer, collection_id)
            write_target = f"{identity}__staging_{uuid.uuid4().hex[:8]}" if resync else identity
            chroma = _bridge.chroma_store()
            registry = _bridge.registry()

            received = 0
            # source_document_id -> {"title": str, "chunk_count": int} — one
            # registry row per distinct source document once the transfer is
            # verified complete (D8: derived from chunk metadata, not a
            # separate manifest breakdown).
            docs_seen: dict = {}
            offset = 0
            try:
                while received < total:
                    page = await self.service.invoker.fetch_replicate_batch(
                        peer, collection_id, offset, BATCH_SIZE)
                    if not page.get("ids"):
                        break
                    chroma.upsert_chunks(write_target, page["ids"], page["embeddings"],
                                         page["texts"], page["metadatas"])
                    for meta in page["metadatas"]:
                        doc_id = meta.get("document_id") or "unknown"
                        entry = docs_seen.setdefault(
                            doc_id, {"title": meta.get("title") or doc_id, "chunk_count": 0})
                        entry["chunk_count"] += 1
                    received += len(page["ids"])
                    offset += len(page["ids"])
                    progress(f"{received}/{total} chunks")

                if received != total:
                    raise ValueError(
                        f"transfer incomplete: received {received} of {total} chunks "
                        f"declared by the manifest — discarding, not exposing a partial replica")
            except Exception:
                # FR-006: an interrupted/failed transfer must leave no
                # partially-queryable collection AND no orphaned chunk data —
                # write_target only ever holds this attempt's chunks (never a
                # prior successful version, since resync writes to a fresh
                # staging name and initial replication has nothing to lose),
                # so it is always safe to discard entirely on any failure here.
                chroma.delete_collection(write_target)
                raise

            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if resync:
                registry.delete_by_collection(identity)
                chroma.promote_staging(write_target, identity)
            for doc_id, info in docs_seen.items():
                row_id = registry.new_document(
                    kind="replica", title=info["title"], source=f"n2n:{peer}",
                    doc_type="other", content_hash=_content_hash_for(peer, collection_id, doc_id),
                    collection=identity, source_peer_identity=peer,
                    source_collection_id=collection_id,
                    source_embedding_model=remote_model, replicated_at=now)
                registry.finalize(row_id, chunk_count=info["chunk_count"])
            return f"replicated {received} chunks into '{identity}'", 0
        return worker
