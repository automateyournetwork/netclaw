"""Configuration for rag-mcp.

All settings come from RAG_* environment variables with contract defaults
(specs/062-rag-mcp/contracts/rag-mcp-tools.md). No credentials are used.
"""

import os
from pathlib import Path


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


DATA_DIR = Path(os.environ.get("RAG_DATA_DIR", "~/.openclaw/rag")).expanduser()

EMBEDDING_MODEL = os.environ.get("RAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
RERANKER_MODEL = os.environ.get(
    "RAG_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)
RERANK_ENABLED = _env_bool("RAG_RERANK_ENABLED", True)
RELEVANCE_FLOOR = _env_float("RAG_RELEVANCE_FLOOR", 0.3)

MAX_DOC_MB = _env_int("RAG_MAX_DOC_MB", 100)
MAX_DOC_PAGES = _env_int("RAG_MAX_DOC_PAGES", 1000)
CRAWL_MAX_PAGES = _env_int("RAG_CRAWL_MAX_PAGES", 30)
SNAPSHOT_WARN_DAYS = _env_int("RAG_SNAPSHOT_WARN_DAYS", 90)
MAX_ROUNDS = _env_int("RAG_MAX_ROUNDS", 3)

DB_PATH = DATA_DIR / "rag.db"
CHROMA_DIR = DATA_DIR / "chroma"
BM25_DIR = DATA_DIR / "bm25"
SOURCES_DIR = DATA_DIR / "sources"
INTAKE_DIR = DATA_DIR / "intake"

DOC_TYPES = ("vendor", "standard", "customer", "install-guide", "other")

DOCUMENTS_COLLECTION = "documents"


def ensure_dirs() -> None:
    """Create the persistent data layout (idempotent)."""
    for d in (DATA_DIR, CHROMA_DIR, BM25_DIR, SOURCES_DIR, INTAKE_DIR):
        d.mkdir(parents=True, exist_ok=True)
