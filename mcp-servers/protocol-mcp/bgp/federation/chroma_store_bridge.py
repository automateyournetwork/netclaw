"""Direct, no-MCP-spawn access to the RAG store's registry + Chroma data
(feature 065), shared by `invocation.py` (serving a local collection to a
replicating peer) and `replication.py` (writing a received replica locally).

Same "cheapest path; no MCP spawn" philosophy `knowledge.py` already
established for read-only registry access (feature 064) — extended here to
also cover raw vector reads/writes. rag-mcp's `storage/registry.py` and
`storage/chroma_store.py` are dependency-free besides the stdlib/chromadb, so
they are loaded directly by file path via `importlib` rather than imported as
a cross-package dependency (rag-mcp is a separately installed package with
its own top-level `storage`/`config` module names, potentially in a
different virtualenv — a normal `import` risks module-name collisions and
venv mismatches). Both files independently carry the schema/behavior this
feature needs so rag-mcp's own tools work on the same on-disk data too.
"""

import importlib.util
import os
from pathlib import Path

_registry_mod = None
_chroma_mod = None


def _rag_mcp_dir() -> Path:
    # .../mcp-servers/protocol-mcp/bgp/federation/chroma_store_bridge.py
    # -> .../mcp-servers/rag-mcp
    return Path(__file__).resolve().parents[3] / "rag-mcp"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _registry_module():
    global _registry_mod
    if _registry_mod is None:
        _registry_mod = _load_module(
            "_n2n_replication_registry", _rag_mcp_dir() / "storage" / "registry.py")
    return _registry_mod


def _chroma_module():
    global _chroma_mod
    if _chroma_mod is None:
        _chroma_mod = _load_module(
            "_n2n_replication_chroma", _rag_mcp_dir() / "storage" / "chroma_store.py")
    return _chroma_mod


def rag_data_dir() -> Path:
    return Path(os.path.expanduser(os.environ.get("RAG_DATA_DIR", "~/.openclaw/rag")))


def registry():
    d = rag_data_dir()
    d.mkdir(parents=True, exist_ok=True)
    return _registry_module().Registry(str(d / "rag.db"))


def chroma_store():
    chroma_dir = rag_data_dir() / "chroma"
    chroma_dir.mkdir(parents=True, exist_ok=True)
    return _chroma_module().ChromaStore(str(chroma_dir))


def chunk_count_for(collection: str) -> int:
    """Total chunk count for a local collection (manifest field, FR-006)."""
    return chroma_store().count(collection)


def get_chunks_page(collection: str, offset: int, limit: int) -> dict:
    """One page of {ids, embeddings, texts, metadatas} — chunk metadata is
    returned exactly as stored (FR-014: ingestion already scrubbed it; this
    is a mechanical forward, not an additional filtering step). Never
    includes source_path/content_hash/capture_commands because those are
    registry-only columns, not chunk metadata — they were never in Chroma to
    begin with."""
    return chroma_store().get_chunks_page(collection, offset, limit)
