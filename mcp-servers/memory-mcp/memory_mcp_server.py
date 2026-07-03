#!/usr/bin/env python3
"""
Memory MCP Server - Hybrid persistent memory for NetClaw.

Provides 10 MCP tools for:
- Structured facts with temporal validity (SQLite)
- Semantic session recall (ChromaDB + embeddings)
- Decision logging with rationale
- Entity relationship graphs

Design goals:
- STDIO MCP: Never write to stdout except protocol
- Log to STDERR only
- Graceful degradation if semantic search unavailable
- GAIT integration for audit trail
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------
# Logging (stderr only)
# ---------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    stream=sys.stderr,
)
logging.getLogger("mcp.server.lowlevel.server").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

log = logging.getLogger("MemoryMCP")

# ---------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:
        from fastmcp import FastMCP  # type: ignore
    except ImportError as e:
        log.error("FastMCP not found. Install with: pip install mcp fastmcp")
        raise

# ---------------------------------------------------------------------
# Storage backends
# ---------------------------------------------------------------------
from storage import SQLiteStore, ChromaStore
from embeddings import Embedder

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------
DATA_DIR = os.environ.get("MEMORY_DATA_DIR", os.path.expanduser("~/.openclaw/memory"))
DB_PATH = os.path.join(DATA_DIR, "memory.db")

# ---------------------------------------------------------------------
# Initialize components
# ---------------------------------------------------------------------
log.info(f"Memory MCP Server starting with data directory: {DATA_DIR}")

# Ensure data directory exists
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

# Initialize storage backends
sqlite_store = SQLiteStore(DB_PATH)
embedder = Embedder()
chroma_store = ChromaStore(DATA_DIR, embedder)

# Check database integrity on startup
ok, msg = sqlite_store.check_integrity()
if ok:
    log.info(msg)
else:
    log.warning(msg)

# ---------------------------------------------------------------------
# FastMCP Server
# ---------------------------------------------------------------------
mcp = FastMCP("memory-mcp")


# ---------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------
def success_response(data: Any) -> Dict[str, Any]:
    """Create a success response."""
    return {"success": True, "data": data, "error": None}


def error_response(code: str, message: str) -> Dict[str, Any]:
    """Create an error response."""
    return {"success": False, "data": None, "error": {"code": code, "message": message}}


def gait_log(operation: str, identifier: str) -> None:
    """Log operation to GAIT (if available)."""
    try:
        # Try to import and use GAIT
        from gait.repo import GaitRepo
        repo = GaitRepo.open_cwd()
        if repo:
            repo.log_event(f"memory_{operation}: {identifier}")
    except Exception:
        # GAIT not available, log to stderr instead
        log.info(f"GAIT: memory_{operation}: {identifier}")


# ---------------------------------------------------------------------
# MCP Tools: Facts (User Story 1)
# ---------------------------------------------------------------------
@mcp.tool()
def memory_record_fact(
    entity: str,
    key: str,
    value: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Record a fact about a network entity with temporal validity.

    If a current fact exists with the same entity+key, it is automatically
    superseded (marked with end timestamp).

    Args:
        entity: Network entity name (device, interface, service)
        key: Fact type/attribute name
        value: Fact value
        metadata: Optional additional context as key-value pairs

    Returns:
        Dict with id, entity, key, value, metadata, valid_from, superseded_id
    """
    result = sqlite_store.insert_fact(entity, key, value, metadata)

    if result.get("success"):
        gait_log("record_fact", f"{entity}/{key}")

    return result


@mcp.tool()
def memory_get_facts(
    entity: str,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query current (non-invalidated) facts for an entity.

    Args:
        entity: Entity name to query
        key: Optional specific key to filter by

    Returns:
        Dict with entity, facts list, count
    """
    return sqlite_store.get_current_facts(entity, key)


# ---------------------------------------------------------------------
# MCP Tools: Fact Lifecycle (User Story 5)
# ---------------------------------------------------------------------
@mcp.tool()
def memory_invalidate(
    fact_id: str,
    reason: str,
) -> Dict[str, Any]:
    """
    Explicitly invalidate a fact with a reason.

    The fact will no longer appear in current queries but remains
    in timeline queries for historical reference.

    Args:
        fact_id: ID of the fact to invalidate
        reason: Why the fact is being invalidated

    Returns:
        Dict with id, entity, key, valid_to, invalidation_reason
    """
    result = sqlite_store.invalidate_fact(fact_id, reason)

    if result.get("success"):
        gait_log("invalidate", fact_id)

    return result


@mcp.tool()
def memory_timeline(
    entity: str,
    after: Optional[str] = None,
    before: Optional[str] = None,
    key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Query historical facts including invalidated ones within a time range.

    Args:
        entity: Entity name to query
        after: ISO timestamp - only facts valid after this time
        before: ISO timestamp - only facts valid before this time
        key: Optional filter by specific key

    Returns:
        Dict with entity, timeline list, count
    """
    return sqlite_store.get_timeline(entity, after, before, key)


# ---------------------------------------------------------------------
# MCP Tools: Semantic Search (User Story 2)
# ---------------------------------------------------------------------
@mcp.tool()
def memory_store_session(
    summary: str,
    entities: Optional[List[str]] = None,
    topics: Optional[List[str]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Store a session summary for semantic retrieval.

    The summary is embedded using sentence-transformers and stored
    in ChromaDB for similarity search.

    Args:
        summary: Session summary text (max 10000 chars)
        entities: Optional list of entity names mentioned
        topics: Optional list of topic tags
        session_id: Optional GAIT session reference

    Returns:
        Dict with id, summary_preview, entities, topics, embedding_dimensions, created_at
    """
    result = chroma_store.store_session(summary, entities, topics, session_id)

    if result.get("success"):
        session_ref = session_id or result.get("data", {}).get("id", "unknown")
        gait_log("store_session", session_ref)

    return result


@mcp.tool()
def memory_recall(
    query: str,
    top_k: int = 5,
    min_score: float = 0.5,
    after: Optional[str] = None,
    topics: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Semantic search across stored sessions.

    Embeds the query and finds the most similar stored sessions
    using cosine similarity.

    Args:
        query: Natural language query
        top_k: Number of results (default: 5, max: 20)
        min_score: Minimum similarity threshold (default: 0.5)
        after: Only sessions after this ISO timestamp
        topics: Filter by topic tags

    Returns:
        Dict with query, results list (with scores), count
    """
    return chroma_store.semantic_search(query, top_k, min_score, after, topics)


# ---------------------------------------------------------------------
# MCP Tools: Decisions (User Story 3)
# ---------------------------------------------------------------------
@mcp.tool()
def memory_record_decision(
    context: str,
    decision: str,
    rationale: str,
    entities: List[str],
    cr_number: Optional[str] = None,
    gait_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Record an operational decision with context and rationale.

    Args:
        context: What was happening when decision was made (max 5000 chars)
        decision: What was decided (max 2000 chars)
        rationale: Why this decision was made (max 5000 chars)
        entities: Related entity names (at least one required)
        cr_number: Optional ServiceNow Change Request (CHG0001234)
        gait_ref: Optional GAIT commit reference

    Returns:
        Dict with id, context, decision, rationale, entities, cr_number, created_at
    """
    result = sqlite_store.insert_decision(
        context, decision, rationale, entities, cr_number, gait_ref
    )

    if result.get("success"):
        decision_id = result.get("data", {}).get("id", "unknown")
        gait_log("record_decision", decision_id)

    return result


@mcp.tool()
def memory_get_decisions(
    entity: Optional[str] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    Query past decisions by entity and/or time range.

    Args:
        entity: Filter by entity (at least one of entity/after required)
        after: Decisions after this ISO timestamp
        before: Decisions before this ISO timestamp
        limit: Max results (default: 50, max: 200)

    Returns:
        Dict with decisions list, count
    """
    return sqlite_store.query_decisions(entity, after, before, limit)


# ---------------------------------------------------------------------
# MCP Tools: Graph Links (User Story 4)
# ---------------------------------------------------------------------
@mcp.tool()
def memory_link_entities(
    subject: str,
    predicate: str,
    object: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a relationship between two entities.

    Standard predicates:
    - peers_with: BGP/OSPF peering relationship
    - depends_on: Service dependency
    - connects_to: Physical/logical connectivity
    - managed_by: Management relationship
    - caused: Incident causality
    - fixed_by: Resolution relationship
    - learned_from: Knowledge provenance

    Args:
        subject: Source entity
        predicate: Relationship type (lowercase alphanumeric + underscore)
        object: Target entity
        metadata: Optional additional context

    Returns:
        Dict with id, subject, predicate, object, metadata, created_at
    """
    result = sqlite_store.insert_link(subject, predicate, object, metadata)

    if result.get("success"):
        gait_log("link_entities", f"{subject} {predicate} {object}")

    return result


@mcp.tool()
def memory_query_graph(
    entity: str,
    direction: str = "both",
    predicate: Optional[str] = None,
    depth: int = 1,
) -> Dict[str, Any]:
    """
    Query entity relationships with optional depth traversal.

    Args:
        entity: Entity to query relationships for
        direction: "outgoing", "incoming", or "both" (default: "both")
        predicate: Optional filter by relationship type
        depth: Traversal depth (default: 1, max: 3)

    Returns:
        Dict with entity, relationships (outgoing/incoming), neighbors_at_depth_N
    """
    return sqlite_store.query_graph(entity, direction, predicate, depth)


# ---------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------
def main():
    """Run the Memory MCP Server."""
    log.info("Memory MCP Server ready")
    mcp.run()


if __name__ == "__main__":
    main()
