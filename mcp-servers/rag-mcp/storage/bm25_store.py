"""Per-collection BM25 keyword index for rag-mcp (FR-016, FR-021).

The keyword leg exists so exact-match networking tokens — CLI syntax
(`Gi0/0/1`), prefixes (`192.0.2.0/24`), CVE and RFC identifiers — are
findable even when embeddings miss them. The tokenizer therefore keeps
punctuation-embedded tokens whole.

Indexes are pickled to <RAG_DATA_DIR>/bm25/<collection>.pkl and rebuilt
whole on ingest/delete (corpus <= ~5k chunks keeps this trivial).
"""

import pickle
import re
import os
import tempfile
import threading
from functools import wraps
from pathlib import Path
from typing import Dict, List, Tuple

from storage.registry import utc_now

# Split ONLY on whitespace and sentence punctuation followed by space/EOL,
# preserving '/', ':', '-', '.' inside tokens (interface names, prefixes, IDs).
_TOKEN_RE = re.compile(r"[^\s,;()\[\]{}\"']+")
_STRIP_EDGE = ".:!?"


def _synchronized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


class _PrimitiveCacheReader(pickle.Unpickler):
    """Existing caches contain primitive data, never importable Python objects."""

    def find_class(self, module, name):
        raise pickle.UnpicklingError("BM25 cache contains a forbidden Python global")


def tokenize(text: str) -> List[str]:
    tokens = []
    for raw in _TOKEN_RE.findall(text.lower()):
        tok = raw.strip(_STRIP_EDGE)
        if tok:
            tokens.append(tok)
    return tokens


class BM25Store:
    def __init__(self, bm25_dir: str):
        self.dir = Path(bm25_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        # collection -> (chunk_ids, tokenized_corpus, bm25_index)
        self._cache: Dict[str, Tuple[List[str], List[List[str]], object]] = {}
        self._fingerprints = {}
        self._lock = threading.RLock()

    def _path(self, collection: str) -> Path:
        return self.dir / f"{collection}.pkl"

    def _build_index(self, tokenized: List[List[str]]):
        from rank_bm25 import BM25Okapi

        return BM25Okapi(tokenized) if tokenized else None

    @_synchronized
    def _load(self, collection: str):
        path = self._path(collection)
        info = path.stat() if path.exists() else None
        fingerprint = (info.st_ino, info.st_mtime_ns, info.st_size) if info else None
        if collection in self._cache and self._fingerprints.get(collection) == fingerprint:
            return self._cache[collection]
        chunk_ids: List[str] = []
        tokenized: List[List[str]] = []
        if path.exists():
            with open(path, "rb") as f:
                data = _PrimitiveCacheReader(f).load()
            if not isinstance(data, dict):
                raise ValueError("BM25 cache must contain a dictionary")
            chunk_ids = data.get("chunk_ids", [])
            tokenized = data.get("tokenized_corpus", [])
            if (not isinstance(chunk_ids, list) or not isinstance(tokenized, list)
                    or len(chunk_ids) != len(tokenized)
                    or not all(isinstance(cid, str) for cid in chunk_ids)
                    or not all(isinstance(tokens, list) and all(isinstance(token, str) for token in tokens)
                               for tokens in tokenized)):
                raise ValueError("BM25 cache has an invalid corpus shape")
        index = self._build_index(tokenized)
        self._cache[collection] = (chunk_ids, tokenized, index)
        self._fingerprints[collection] = fingerprint
        return self._cache[collection]

    @_synchronized
    def _persist(self, collection: str, chunk_ids: List[str], tokenized: List[List[str]]):
        index = self._build_index(tokenized)
        fd, temporary = tempfile.mkstemp(prefix='.bm25-', suffix='.tmp', dir=self.dir)
        try:
            with os.fdopen(fd, 'wb') as stream:
                pickle.dump({'chunk_ids': chunk_ids, 'tokenized_corpus': tokenized,
                             'built_ts': utc_now()}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(collection))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        self._cache[collection] = (chunk_ids, tokenized, index)
        info = self._path(collection).stat()
        self._fingerprints[collection] = (info.st_ino, info.st_mtime_ns, info.st_size)

    @_synchronized
    def rebuild(self, collection: str, chunks: List[Dict]) -> None:
        """Full rebuild from [{chunk_id, text}, ...] (post ingest/delete)."""
        chunk_ids = [c["chunk_id"] for c in chunks]
        tokenized = [tokenize(c["text"]) for c in chunks]
        self._persist(collection, chunk_ids, tokenized)

    @_synchronized
    def add(self, collection: str, chunks: List[Dict]) -> None:
        """Append chunks and rebuild the index."""
        chunk_ids, tokenized, _ = self._load(collection)
        chunk_ids = list(chunk_ids) + [c["chunk_id"] for c in chunks]
        tokenized = list(tokenized) + [tokenize(c["text"]) for c in chunks]
        self._persist(collection, chunk_ids, tokenized)

    @_synchronized
    def remove_chunks(self, collection: str, remove_ids: List[str]) -> int:
        chunk_ids, tokenized, _ = self._load(collection)
        remove = set(remove_ids)
        kept = [(cid, toks) for cid, toks in zip(chunk_ids, tokenized) if cid not in remove]
        removed = len(chunk_ids) - len(kept)
        self._persist(
            collection, [c for c, _ in kept], [t for _, t in kept]
        )
        return removed

    @_synchronized
    def search(self, collection: str, query: str, n_results: int) -> List[Dict]:
        """Returns [{chunk_id, score}] ranked by BM25. Candidacy requires at
        least one shared query token — BM25Okapi's IDF can go negative in tiny
        corpora, so score sign alone cannot gate membership."""
        chunk_ids, tokenized, index = self._load(collection)
        if index is None or not chunk_ids:
            return []
        query_tokens = set(tokenize(query))
        scores = index.get_scores(list(query_tokens))
        ranked = sorted(
            (
                (cid, score)
                for cid, score, tokens in zip(chunk_ids, scores, tokenized)
                if query_tokens & set(tokens)
            ),
            key=lambda x: x[1],
            reverse=True,
        )
        return [{"chunk_id": cid, "score": float(score)} for cid, score in ranked[:n_results]]

    @_synchronized
    def delete_collection(self, collection: str) -> None:
        self._cache.pop(collection, None)
        path = self._path(collection)
        if path.exists():
            path.unlink()
