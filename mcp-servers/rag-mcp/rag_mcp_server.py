#!/usr/bin/env python3
"""rag-mcp — NetClaw Agentic RAG Knowledge Base MCP server (Feature 062).

Fully offline, free, local document knowledge base:
- Ingestion: PDF/MD/HTML/TXT native; DOCX/XLSX/PPTX/VSDX via Python parsers;
  legacy DOC/XLS/PPT/VSD via LibreOffice-headless conversion fallback.
- Retrieval: hybrid dense (ChromaDB) + BM25 with reciprocal rank fusion and
  a local cross-encoder reranker; every result carries citation metadata.
- Snapshots: opt-in only, secret-scrubbed, timestamped, staleness-tagged.

Storage: ~/.openclaw/rag/ — completely separate from the Memory MCP's store
at ~/.openclaw/memory/ (GP-7 / FR-030). Transport: stdio (FastMCP).
"""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))

import config
from embeddings.embedder import Embedder, ModelsNotCachedError
from storage.bm25_store import BM25Store
from storage.chroma_store import ChromaStore
from storage.registry import Registry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("rag-mcp")

# ---------------------------------------------------------------------
# Component wiring (config -> registry -> embedder -> stores)
# ---------------------------------------------------------------------
config.ensure_dirs()
log.info(f"rag-mcp starting with data directory: {config.DATA_DIR}")

registry = Registry(config.DB_PATH)
embedder = Embedder(config.EMBEDDING_MODEL)
chroma = ChromaStore(config.CHROMA_DIR)
bm25 = BM25Store(config.BM25_DIR)

# Startup integrity sweep: purge partial index entries of interrupted ingests.
for _row in registry.sweep_interrupted():
    log.warning(f"Sweeping interrupted ingestion: {_row['id']} ({_row['title']})")
    chroma.delete_document(_row["collection"], _row["id"])
    try:
        bm25_chunks = chroma.get_document_chunks(_row["collection"], _row["id"])
        bm25.remove_chunks(_row["collection"], [c["chunk_id"] for c in bm25_chunks])
    except Exception:
        pass

from fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("rag-mcp")


# ---------------------------------------------------------------------
# Response helpers (memory-mcp envelope convention)
# ---------------------------------------------------------------------
def success_response(data: Any) -> Dict[str, Any]:
    return {"success": True, "data": data, "error": None}


def error_response(code: str, message: str) -> Dict[str, Any]:
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def gait_log(operation: str, detail: str) -> None:
    """Record the decision in GAIT; degrade gracefully when GAIT is absent."""
    try:
        from gait.repo import GaitRepo

        repo = GaitRepo.open_cwd()
        if repo:
            repo.log_event(f"rag_{operation}: {detail}")
    except Exception:
        log.debug(f"GAIT unavailable — rag_{operation}: {detail}")


# ---------------------------------------------------------------------
# Ingestion pipeline (single code path for Slack / HUD / URL — FR-005)
# ---------------------------------------------------------------------
import base64
import shutil
import time

from ingestion.chunker import chunk_document
from ingestion.parsers import IngestError, ParsedDocument, parse_file
from retrieval.hybrid import hybrid_retrieve
from retrieval.reranker import Reranker

reranker = Reranker(config.RERANKER_MODEL, enabled=config.RERANK_ENABLED)


def _example_question(title: str, doc_type: str) -> str:
    """Usage-teaching hook in the ingest confirmation (FR-048)."""
    templates = {
        "vendor": f'What are the prerequisites described in "{title}"?',
        "standard": f'What does "{title}" require?',
        "customer": f'What does our standard "{title}" say about maintenance windows?',
        "install-guide": f'What are the install steps in "{title}"?',
        "other": f'What does "{title}" cover?',
    }
    return templates.get(doc_type, templates["other"])


def _index_parsed_document(
    doc_id: str,
    parsed: ParsedDocument,
    collection: str,
    doc_type: str,
    source: str,
    kind: str = "document",
    extra_chunk_meta: Optional[Dict[str, Any]] = None,
) -> int:
    """Chunk -> embed -> commit to Chroma + BM25. Registry flip to 'ready'
    happens in the caller AFTER this returns (atomic commit point)."""
    registry.set_status(doc_id, "chunking")
    chunks = chunk_document(parsed, embedder.count_tokens)
    if not chunks:
        raise IngestError("PARSE_FAILED", f"No indexable content in '{parsed.title}'")

    registry.set_status(doc_id, "embedding")
    texts = [c.text for c in chunks]
    embeddings = embedder.embed_passages(texts)

    row = registry.get(doc_id)
    ids = [f"chunk_{doc_id}_{c.seq}" for c in chunks]
    metadatas = []
    for c in chunks:
        meta = {
            "document_id": doc_id,
            "title": parsed.title,
            "doc_type": doc_type,
            "source": source,
            "breadcrumb": c.breadcrumb,
            "section": c.section,
            "page": c.page,
            "ingest_ts": row["ingest_ts"],
            "atomic": c.atomic,
            "kind": kind,
        }
        if extra_chunk_meta:
            meta.update(extra_chunk_meta)
        metadatas.append(meta)

    chroma.add_chunks(collection, ids, embeddings, texts, metadatas)
    bm25.add(collection, [{"chunk_id": cid, "text": t} for cid, t in zip(ids, texts)])
    return len(chunks)


def _remove_document_from_indexes(doc_row: Dict[str, Any]) -> int:
    collection = doc_row["collection"]
    chunk_rows = chroma.get_document_chunks(collection, doc_row["id"])
    bm25.remove_chunks(collection, [c["chunk_id"] for c in chunk_rows])
    return chroma.delete_document(collection, doc_row["id"])


def _do_ingest(
    file_path: str,
    doc_type: str = "other",
    title: Optional[str] = None,
    version: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    path = Path(file_path).expanduser()
    if doc_type not in config.DOC_TYPES:
        doc_type = "other"

    try:
        parsed = parse_file(path, config.MAX_DOC_MB, config.MAX_DOC_PAGES)
    except IngestError as exc:
        return error_response(exc.code, exc.message)
    if title:
        parsed.title = title
    src = source or path.name

    # Dedupe: identical content hash is a no-op (FR-007)
    existing = registry.find_by_hash(parsed.content_hash)
    if existing and existing["ingest_status"] == "ready":
        return success_response(
            {
                "document_id": existing["id"],
                "title": existing["title"],
                "doc_type": existing["doc_type"],
                "source": existing["source"],
                "page_count": existing["page_count"],
                "chunk_count": existing["chunk_count"],
                "collection": existing["collection"],
                "ingest_ts": existing["ingest_ts"],
                "deduplicated": True,
                "reindexed": False,
                "message": f'"{existing["title"]}" is already indexed (identical content).',
            }
        )

    # Same title, different hash: replace the prior version (FR-007)
    reindexed = False
    prior = registry.find_by_title(parsed.title)
    if prior and prior["content_hash"] != parsed.content_hash:
        _remove_document_from_indexes(prior)
        if prior.get("source_path"):
            shutil.rmtree(Path(prior["source_path"]).parent, ignore_errors=True)
        registry.delete(prior["id"])
        reindexed = True

    doc_id = registry.new_document(
        kind="document",
        title=parsed.title,
        source=src,
        doc_type=doc_type,
        content_hash=parsed.content_hash,
        collection=config.DOCUMENTS_COLLECTION,
        version=version,
    )
    try:
        registry.set_status(doc_id, "parsing")
        # Retain the original for rag_reindex (FR-052)
        retained_dir = config.SOURCES_DIR / doc_id
        retained_dir.mkdir(parents=True, exist_ok=True)
        retained_path = retained_dir / path.name
        shutil.copy2(path, retained_path)
        registry.set_source_path(doc_id, str(retained_path))

        chunk_count = _index_parsed_document(
            doc_id, parsed, config.DOCUMENTS_COLLECTION, doc_type, src
        )
        registry.finalize(doc_id, chunk_count=chunk_count, page_count=parsed.page_count)
    except ModelsNotCachedError as exc:
        registry.set_status(doc_id, "error", error=str(exc))
        return error_response("MODELS_NOT_CACHED", str(exc))
    except IngestError as exc:
        registry.set_status(doc_id, "error", error=exc.message)
        return error_response(exc.code, exc.message)
    except Exception as exc:
        registry.set_status(doc_id, "error", error=str(exc))
        return error_response("PARSE_FAILED", str(exc))

    action = "re-indexed (replaced prior version)" if reindexed else "ingested"
    gait_log(
        "ingest",
        f"{action} '{parsed.title}' ({doc_type}, {chunk_count} chunks) from {src} "
        f"— user-supplied knowledge for the RAG store",
    )
    return success_response(
        {
            "document_id": doc_id,
            "title": parsed.title,
            "doc_type": doc_type,
            "source": src,
            "page_count": parsed.page_count,
            "chunk_count": chunk_count,
            "collection": config.DOCUMENTS_COLLECTION,
            "ingest_ts": registry.get(doc_id)["ingest_ts"],
            "deduplicated": False,
            "reindexed": reindexed,
            "example_question": _example_question(parsed.title, doc_type),
        }
    )


# ---------------------------------------------------------------------
# Tools: ingestion (FR-001–FR-009)
# ---------------------------------------------------------------------
@mcp.tool()
def rag_ingest(
    file_path: str,
    doc_type: str = "other",
    title: Optional[str] = None,
    version: Optional[str] = None,
    source: Optional[str] = None,
) -> Dict[str, Any]:
    """Ingest a document file (PDF/MD/HTML/TXT/DOCX/XLSX/PPTX/VSDX, plus legacy
    DOC/XLS/PPT/VSD via LibreOffice) into the knowledge base. doc_type is one of
    vendor|standard|customer|install-guide|other."""
    return _do_ingest(file_path, doc_type, title, version, source)


def _do_ingest_base64(
    filename: str,
    content_base64: str,
    doc_type: str = "other",
    title: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    safe_name = Path(filename).name
    intake_path = config.INTAKE_DIR / safe_name
    try:
        intake_path.write_bytes(base64.b64decode(content_base64))
    except Exception as exc:
        return error_response("PARSE_FAILED", f"Could not decode base64 content: {exc}")
    return _do_ingest(
        str(intake_path), doc_type, title, version, source="slack:attachment"
    )


@mcp.tool()
def rag_ingest_base64(
    filename: str,
    content_base64: str,
    doc_type: str = "other",
    title: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Ingest a document supplied as base64 (Slack attachment path). Decodes into
    the intake directory then runs the standard ingestion pipeline."""
    return _do_ingest_base64(filename, content_base64, doc_type, title, version)


# ---------------------------------------------------------------------
# URL ingestion — two-phase with structural crawl-confirmation gate (FR-004)
# ---------------------------------------------------------------------
from ingestion.url_fetcher import (
    FetchError,
    discover_links,
    fetch,
    filename_for_url,
    page_title,
    scope_token,
    verify_scope_token,
)


def _ingest_fetched(url: str, content: bytes, content_type: str, doc_type: str, title: Optional[str]) -> Dict[str, Any]:
    fname = filename_for_url(url, content_type)
    intake_path = config.INTAKE_DIR / fname
    intake_path.write_bytes(content)
    return _do_ingest(str(intake_path), doc_type, title, source=url)


def _do_ingest_url(
    url: str,
    mode: str = "preview",
    include_linked: bool = False,
    scope_token_value: Optional[str] = None,
    doc_type: str = "other",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        content, content_type = fetch(url)
    except FetchError as exc:
        return error_response("FETCH_FAILED", exc.message)

    is_html = content_type == "text/html" or (
        not content_type and content.lstrip()[:1] == b"<"
    )

    if mode == "preview":
        if not is_html:
            return success_response(
                {
                    "url": url,
                    "title": Path(url).name,
                    "content_type": content_type,
                    "linked_pages": [],
                    "truncated": False,
                    "scope_token": scope_token(url, []),
                    "message": "Non-HTML content — single-document ingest only.",
                }
            )
        html = content.decode("utf-8", errors="replace")
        links = discover_links(html, url, config.CRAWL_MAX_PAGES)
        linked_urls = [p["url"] for p in links["linked_pages"]]
        return success_response(
            {
                "url": url,
                "title": page_title(html, url),
                "content_type": content_type,
                "linked_pages": links["linked_pages"],
                "truncated": links["truncated"],
                "scope_token": scope_token(url, linked_urls),
            }
        )

    if mode != "ingest":
        return error_response("PARSE_FAILED", f"Unknown mode '{mode}' — use preview|ingest.")

    results = [_ingest_fetched(url, content, content_type, doc_type, title)]

    if include_linked:
        if not is_html:
            return error_response(
                "SCOPE_TOKEN_INVALID", "include_linked requires an HTML page with links."
            )
        html = content.decode("utf-8", errors="replace")
        links = discover_links(html, url, config.CRAWL_MAX_PAGES)
        linked_urls = [p["url"] for p in links["linked_pages"]]
        if not verify_scope_token(scope_token_value or "", url, linked_urls):
            return error_response(
                "SCOPE_TOKEN_INVALID",
                "Linked-page ingestion requires the scope_token from a preceding "
                "preview of this exact URL (confirm scope with the user, then echo "
                "the token). Run mode='preview' first.",
            )
        for page_url in linked_urls:
            try:
                page_content, page_type = fetch(page_url)
                results.append(
                    _ingest_fetched(page_url, page_content, page_type, doc_type, None)
                )
            except FetchError as exc:
                results.append(error_response("FETCH_FAILED", exc.message))

    ok = sum(1 for r in results if r.get("success"))
    gait_log(
        "ingest_url",
        f"ingested {ok}/{len(results)} page(s) from {url} "
        f"(depth-1={'yes' if include_linked else 'no'}, user-confirmed scope)",
    )
    return success_response({"pages": results, "ingested": ok, "failed": len(results) - ok})


@mcp.tool()
def rag_ingest_url(
    url: str,
    mode: str = "preview",
    include_linked: bool = False,
    scope_token: Optional[str] = None,
    doc_type: str = "other",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Two-phase URL ingestion. mode='preview' returns the page title, same-domain
    depth-1 linked pages, and a scope_token — no ingestion. After the user confirms
    scope, call mode='ingest' (echoing scope_token when include_linked=true)."""
    return _do_ingest_url(url, mode, include_linked, scope_token, doc_type, title)


# ---------------------------------------------------------------------
# Search (v1 dense leg; hybrid + rerank layered on in retrieval/)
# ---------------------------------------------------------------------
def _format_citation(meta: Dict[str, Any]) -> str:
    """User-visible citation (FR-044). Chunk IDs are log-only."""
    parts = [meta.get("title", "Unknown")]
    if meta.get("section"):
        parts.append(f"§{meta['section']}")
    if meta.get("page"):
        parts.append(f"p.{meta['page']}")
    ingested = (meta.get("ingest_ts") or "")[:10]
    return f"[{' '.join(str(p) for p in parts)} — ingested {ingested}]"


def _result_from_hit(hit: Dict[str, Any], low_confidence: bool) -> Dict[str, Any]:
    meta = hit["metadata"]
    result = {
        "chunk_text": hit["text"],
        "score": hit["score"],
        "chunk_id": hit["chunk_id"],
        "title": meta.get("title"),
        "doc_type": meta.get("doc_type"),
        "section": meta.get("section"),
        "page": meta.get("page"),
        "ingest_ts": meta.get("ingest_ts"),
        "low_confidence": low_confidence,
        "citation": _format_citation(meta),
    }
    if meta.get("kind") == "snapshot":
        # Staleness is always visible and must be surfaced verbatim (FR-027/FR-046)
        result["capture_ts"] = meta.get("capture_ts")
        result["age_human"] = _age_human(meta.get("capture_ts"))
        result["device"] = meta.get("device")
        result["command"] = meta.get("command")
        result["staleness_notice"] = (
            f"{result['age_human']} — live state is available via MCP tools."
            if result["age_human"]
            else None
        )
    return result


def _chroma_where(filters: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Translate contract filters to a Chroma where-clause. Date-range filters
    are applied as a Python post-filter (Chroma string comparison is limited)."""
    if not filters:
        return None
    clauses = []
    for key in ("doc_type", "document_id", "title"):
        if filters.get(key):
            clauses.append({key: filters[key]})
    if not clauses:
        return None
    return clauses[0] if len(clauses) == 1 else {"$and": clauses}


def _passes_date_filters(meta: Dict[str, Any], filters: Optional[Dict[str, Any]]) -> bool:
    if not filters:
        return True
    ts = meta.get("ingest_ts") or ""
    after, before = filters.get("ingested_after"), filters.get("ingested_before")
    if after and ts < after:
        return False
    if before and ts > before:
        return False
    return True


def _do_search(
    query: str,
    k: int = 5,
    collection: str = "documents",
    filters: Optional[Dict[str, Any]] = None,
    round: Optional[int] = None,
    sub_query_id: Optional[str] = None,
) -> Dict[str, Any]:
    start = time.monotonic()
    try:
        if chroma.count(collection) == 0:
            registry.log_retrieval(query, collection, filters, k, [], [], 0, 0, round, sub_query_id)
            return success_response(
                {
                    "results": [],
                    "corpus_empty": True,
                    "collection": collection,
                    "latency_ms": 0,
                    "message": f"Collection '{collection}' is empty — nothing indexed yet.",
                }
            )
        query_embedding = embedder.embed_query(query)
    except ModelsNotCachedError as exc:
        return error_response("MODELS_NOT_CACHED", str(exc))

    # Hybrid: dense + BM25 legs fused by RRF (FR-021)
    candidates = hybrid_retrieve(
        chroma, bm25, collection, query, query_embedding, where=_chroma_where(filters)
    )
    # Date-range + (BM25-leg) metadata post-filters
    candidates = [
        c
        for c in candidates
        if _passes_date_filters(c["metadata"], filters)
        and (not filters or all(
            c["metadata"].get(key) == filters[key]
            for key in ("doc_type", "document_id", "title")
            if filters.get(key)
        ))
    ]

    # Local cross-encoder rerank -> top-k, low_confidence flagged (FR-022/024)
    top = reranker.rerank(query, candidates, k, config.RELEVANCE_FLOOR)

    results = []
    for c in top:
        hit = {"chunk_id": c["chunk_id"], "text": c["text"], "metadata": c["metadata"], "score": c["score"]}
        results.append(_result_from_hit(hit, c["low_confidence"]))

    latency_ms = int((time.monotonic() - start) * 1000)
    registry.log_retrieval(
        query,
        collection,
        filters,
        k,
        [r["chunk_id"] for r in results],
        [r["score"] for r in results],
        latency_ms,
        sum(1 for r in results if r["low_confidence"]),
        round,
        sub_query_id,
    )
    return success_response(
        {
            "results": results,
            "corpus_empty": False,
            "collection": collection,
            "latency_ms": latency_ms,
        }
    )


@mcp.tool()
def rag_search(
    query: str,
    k: int = 5,
    collection: str = "documents",
    filters: Optional[Dict[str, Any]] = None,
    round: Optional[int] = None,
    sub_query_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Search the knowledge base. Returns top-k chunks with citation metadata.
    Filters: doc_type, document_id, title, ingested_after, ingested_before.
    Results below the relevance floor are flagged low_confidence, never dropped."""
    return _do_search(query, k, collection, filters, round, sub_query_id)


# ---------------------------------------------------------------------
# Document management (GP-6, FR-050 – FR-054)
# ---------------------------------------------------------------------
from datetime import datetime, timezone


def _age_human(capture_ts: Optional[str]) -> Optional[str]:
    """'captured 2026-07-16 14:02 UTC — 31 days ago' (FR-027)."""
    if not capture_ts:
        return None
    try:
        captured = datetime.fromisoformat(capture_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    days = max(0, (datetime.now(timezone.utc) - captured).days)
    age = "today" if days == 0 else ("1 day ago" if days == 1 else f"{days} days ago")
    return f"captured {captured.strftime('%Y-%m-%d %H:%M')} UTC — {age}"


def _snapshot_age_days(capture_ts: Optional[str]) -> Optional[int]:
    if not capture_ts:
        return None
    try:
        captured = datetime.fromisoformat(capture_ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, (datetime.now(timezone.utc) - captured).days)


def _doc_public(row: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        k: row.get(k)
        for k in (
            "id",
            "kind",
            "title",
            "source",
            "doc_type",
            "version",
            "collection",
            "ingest_ts",
            "page_count",
            "chunk_count",
            "ingest_status",
            "error",
        )
    }
    if row["kind"] == "snapshot":
        days = _snapshot_age_days(row.get("capture_ts"))
        out.update(
            {
                "capture_ts": row.get("capture_ts"),
                "capture_devices": json.loads(row["capture_devices"]) if row.get("capture_devices") else [],
                "capture_commands": json.loads(row["capture_commands"]) if row.get("capture_commands") else [],
                "redaction_counts": json.loads(row["redaction_counts"]) if row.get("redaction_counts") else {},
                "age_human": _age_human(row.get("capture_ts")),
                "stale": days is not None and days > config.SNAPSHOT_WARN_DAYS,
            }
        )
    return out


def _do_list(kind: str = "all") -> Dict[str, Any]:
    documents, snapshots = [], []
    for row in registry.list_documents():
        if row["kind"] == "document" and kind in ("all", "documents"):
            documents.append(_doc_public(row))
        elif row["kind"] == "snapshot" and kind in ("all", "snapshots"):
            snapshots.append(_doc_public(row))
    return success_response({"documents": documents, "snapshots": snapshots})


@mcp.tool()
def rag_list(kind: str = "all") -> Dict[str, Any]:
    """List indexed documents and snapshots (separately) with full metadata.
    kind: documents|snapshots|all."""
    return _do_list(kind)


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _do_stats() -> Dict[str, Any]:
    rows = registry.list_documents()
    ready = [r for r in rows if r["ingest_status"] == "ready"]
    return success_response(
        {
            "document_count": sum(1 for r in ready if r["kind"] == "document"),
            "snapshot_count": sum(1 for r in ready if r["kind"] == "snapshot"),
            "total_chunks": sum(r["chunk_count"] or 0 for r in ready),
            "disk_usage_bytes": _dir_size(config.DATA_DIR),
            "embedding_model": config.EMBEDDING_MODEL,
            "reranker_model": config.RERANKER_MODEL,
            "rerank_enabled": config.RERANK_ENABLED,
            "collections": sorted({r["collection"] for r in ready} | {config.DOCUMENTS_COLLECTION}),
            "schema_version": registry.schema_version(),
            "telemetry": registry.telemetry(),
        }
    )


@mcp.tool()
def rag_stats() -> Dict[str, Any]:
    """Corpus totals (docs, chunks, disk usage, models, collections) plus rolling
    retrieval telemetry (query count, mean latency, re-retrieval and low-confidence rates)."""
    return _do_stats()


def _do_update_metadata(
    document_id: str,
    doc_type: Optional[str] = None,
    title: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    row = registry.get(document_id)
    if not row:
        return error_response("NOT_FOUND", f"No document with id '{document_id}'")
    if doc_type is not None and doc_type not in config.DOC_TYPES:
        return error_response(
            "PARSE_FAILED", f"doc_type must be one of {', '.join(config.DOC_TYPES)}"
        )
    updated = registry.update_metadata(document_id, doc_type=doc_type, title=title, version=version)
    chroma.update_document_metadata(
        row["collection"], document_id, {"doc_type": doc_type, "title": title}
    )
    gait_log("update_metadata", f"{document_id}: doc_type={doc_type} title={title} version={version}")
    return success_response(_doc_public(updated))


@mcp.tool()
def rag_update_metadata(
    document_id: str,
    doc_type: Optional[str] = None,
    title: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Edit a document's doc_type (vendor|standard|customer|install-guide|other),
    title, or version. Updates registry and chunk metadata."""
    return _do_update_metadata(document_id, doc_type, title, version)


_CONFIRM_NOTICE = (
    "Confirmation required: this is a destructive corpus operation. Confirm with "
    "the user, then call again with confirmed=true (FR-053 human-in-the-loop gate)."
)


def _do_delete(document_id: str, confirmed: bool = False) -> Dict[str, Any]:
    row = registry.get(document_id)
    if not row:
        return error_response("NOT_FOUND", f"No document with id '{document_id}'")
    if not confirmed:
        return success_response(
            {"deleted": False, "confirmation_required": True, "message": _CONFIRM_NOTICE,
             "title": row["title"], "chunk_count": row["chunk_count"]}
        )
    removed = _remove_document_from_indexes(row)
    if row.get("source_path"):
        shutil.rmtree(Path(row["source_path"]).parent, ignore_errors=True)
    if row["kind"] == "snapshot" and row["collection"].startswith("snapshot_"):
        chroma.delete_collection(row["collection"])
        bm25.delete_collection(row["collection"])
    registry.delete(document_id)
    gait_log("delete", f"deleted '{row['title']}' ({document_id}, {removed} chunks) — user-confirmed")
    return success_response({"deleted": True, "chunks_removed": removed, "title": row["title"]})


@mcp.tool()
def rag_delete(document_id: str, confirmed: bool = False) -> Dict[str, Any]:
    """Delete a document or snapshot: removes chunks from dense AND keyword
    indexes plus the retained original. Requires confirmed=true after the user
    has explicitly approved (destructive — HIIL gate)."""
    return _do_delete(document_id, confirmed)


def _do_reindex(document_id: str, confirmed: bool = False) -> Dict[str, Any]:
    row = registry.get(document_id)
    if not row:
        return error_response("NOT_FOUND", f"No document with id '{document_id}'")
    if row["kind"] == "snapshot":
        return error_response("NOT_FOUND", "Snapshots have no retained source — they cannot be re-indexed.")
    if not row.get("source_path") or not Path(row["source_path"]).exists():
        return error_response("NOT_FOUND", f"Retained source for '{row['title']}' is missing.")
    if not confirmed:
        return success_response(
            {"reindexed": False, "confirmation_required": True, "message": _CONFIRM_NOTICE,
             "title": row["title"]}
        )
    source_path = row["source_path"]
    doc_type, title, version, source = row["doc_type"], row["title"], row["version"], row["source"]
    _remove_document_from_indexes(row)
    registry.delete(document_id)
    result = _do_ingest(source_path, doc_type, title, version, source)
    if result.get("success"):
        gait_log("reindex", f"re-indexed '{title}' under current chunking/embedding config — user-confirmed")
    return result


@mcp.tool()
def rag_reindex(document_id: str, confirmed: bool = False) -> Dict[str, Any]:
    """Re-chunk and re-embed a document from its retained original (use after
    chunking/embedding config changes). Requires confirmed=true after the user
    has explicitly approved (HIIL gate)."""
    return _do_reindex(document_id, confirmed)


# ---------------------------------------------------------------------
# Snapshots — opt-in only, secret-scrubbed, staleness-tagged (FR-070 – FR-075)
# ---------------------------------------------------------------------
import hashlib as _hashlib
import re as _re

from ingestion.parsers import Section as _Section
from scrubber import scrub


def _do_snapshot(
    label: str,
    content: str,
    source_description: str,
    devices: Optional[list] = None,
    commands: Optional[list] = None,
    capture_ts: Optional[str] = None,
) -> Dict[str, Any]:
    if not content or not content.strip():
        return error_response("PARSE_FAILED", "Snapshot content is empty.")

    slug = _re.sub(r"[^A-Za-z0-9_-]+", "-", label.strip()).strip("-") or "snapshot"
    ts = capture_ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    collection = f"snapshot_{slug}_{ts.replace(':', '').replace('+', '')}"

    # Secret scrubbing BEFORE vectorization — counts include explicit zeros
    scrubbed, redaction_counts = scrub(content)

    content_hash = _hashlib.sha256(scrubbed.encode()).hexdigest()
    devices, commands = devices or [], commands or []

    snap_id = registry.new_document(
        kind="snapshot",
        title=slug,
        source=source_description,
        doc_type="other",
        content_hash=content_hash,
        collection=collection,
        capture_ts=ts,
        capture_devices=devices,
        capture_commands=commands,
    )
    try:
        registry.set_status(snap_id, "parsing")
        section = _Section(heading_path=[source_description])
        for para in _re.split(r"\n\s*\n", scrubbed):
            para = para.strip()
            if para:
                section.blocks.append(("atomic", para, None))
        parsed = ParsedDocument(
            title=slug, sections=[section], page_count=None, content_hash=content_hash
        )
        chunk_count = _index_parsed_document(
            snap_id,
            parsed,
            collection,
            "other",
            source_description,
            kind="snapshot",
            extra_chunk_meta={
                "capture_ts": ts,
                "device": ", ".join(devices) or None,
                "command": ", ".join(commands) or None,
            },
        )
        registry.finalize(snap_id, chunk_count=chunk_count, redaction_counts=redaction_counts)
    except ModelsNotCachedError as exc:
        registry.set_status(snap_id, "error", error=str(exc))
        return error_response("MODELS_NOT_CACHED", str(exc))
    except IngestError as exc:
        registry.set_status(snap_id, "error", error=exc.message)
        return error_response(exc.code, exc.message)

    total_redactions = sum(redaction_counts.values())
    gait_log(
        "snapshot",
        f"snapshot '{slug}' -> {collection} ({chunk_count} chunks, "
        f"{total_redactions} redactions, devices={devices}, commands={commands}) "
        f"— explicitly user-requested and scope-confirmed",
    )
    return success_response(
        {
            "snapshot_id": snap_id,
            "collection": collection,
            "chunk_count": chunk_count,
            "capture_ts": ts,
            "redaction_counts": redaction_counts,
            "total_redactions": total_redactions,
            "message": (
                f"Snapshot stored in '{collection}'. Redactions: "
                + ", ".join(f"{k}: {v}" for k, v in redaction_counts.items() if v)
                + (" (none found — 0 redactions)" if total_redactions == 0 else "")
            ),
        }
    )


@mcp.tool()
def rag_snapshot(
    label: str,
    content: str,
    source_description: str,
    devices: Optional[list] = None,
    commands: Optional[list] = None,
    capture_ts: Optional[str] = None,
) -> Dict[str, Any]:
    """Vectorize explicitly requested live network output into a NEW timestamped
    snapshot collection (never 'documents'). OPT-IN ONLY: never call this
    automatically, from a heartbeat, or as a side effect — the user must
    explicitly request it and confirm scope first. Content is secret-scrubbed
    before vectorization; redaction counts are reported per type."""
    return _do_snapshot(label, content, source_description, devices, commands, capture_ts)


def main() -> None:
    log.info(
        f"rag-mcp ready (embedding={config.EMBEDDING_MODEL}, "
        f"reranker={config.RERANKER_MODEL}, rerank_enabled={config.RERANK_ENABLED})"
    )
    mcp.run()


if __name__ == "__main__":
    main()
