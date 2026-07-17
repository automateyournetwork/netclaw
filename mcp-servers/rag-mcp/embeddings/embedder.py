"""Local sentence-transformers embedder for rag-mcp.

Env-configurable model (RAG_EMBEDDING_MODEL, default BAAI/bge-small-en-v1.5),
lazy-loaded, fully offline after the one-time install download. BGE-family
models use an instruction prefix on QUERIES only; passages are embedded bare.
"""

import logging
from typing import List, Optional

log = logging.getLogger(__name__)

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class ModelsNotCachedError(RuntimeError):
    """Raised when the embedding model is unavailable locally (no hang, no fetch)."""


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._load_error: Optional[str] = None

    @property
    def _is_bge(self) -> bool:
        return "bge-" in self.model_name.lower()

    def _load(self):
        if self._model is not None:
            return self._model
        if self._load_error is not None:
            raise ModelsNotCachedError(self._load_error)
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        except Exception as exc:  # model absent, no network, or lib missing
            self._load_error = (
                f"Embedding model '{self.model_name}' is not available locally: {exc}. "
                "Run the installer (component rag-mcp) or pre-seed the model cache "
                "on air-gapped hosts."
            )
            raise ModelsNotCachedError(self._load_error) from exc
        return self._model

    def embed_passages(self, texts: List[str]) -> List[List[float]]:
        model = self._load()
        return model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()

    def embed_query(self, query: str) -> List[float]:
        model = self._load()
        text = f"{BGE_QUERY_PREFIX}{query}" if self._is_bge else query
        return model.encode([text], show_progress_bar=False, convert_to_numpy=True)[0].tolist()

    def count_tokens(self, text: str) -> int:
        """Token count via the model's own tokenizer; word-count fallback when
        the model (and hence tokenizer) is unavailable, so chunking still works
        in degraded/test mode."""
        try:
            model = self._load()
            return len(model.tokenizer.encode(text, add_special_tokens=False))
        except Exception:
            # ~1.3 tokens per word is a serviceable approximation for English prose
            return max(1, int(len(text.split()) * 1.3))
