"""
Embedding utilities for Memory MCP Server.

Provides lazy-loaded sentence-transformers wrapper with:
- all-MiniLM-L6-v2 model (80MB, 384 dimensions)
- Lazy loading on first use
- Batch embedding support
- Graceful degradation if model unavailable
"""

from __future__ import annotations

import logging
from typing import List, Optional

log = logging.getLogger("MemoryMCP.Embedder")

# Model configuration
MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384


class Embedder:
    """Sentence-transformers wrapper with lazy model loading."""

    def __init__(self):
        """Initialize embedder (model loaded on first use)."""
        self._model = None
        self._available = None

    def _load_model(self) -> bool:
        """
        Load the embedding model.

        Returns True if model loaded successfully, False otherwise.
        """
        if self._model is not None:
            return True

        if self._available is False:
            return False

        try:
            from sentence_transformers import SentenceTransformer

            log.info(f"Loading embedding model: {MODEL_NAME}")
            self._model = SentenceTransformer(MODEL_NAME)
            self._available = True
            log.info(f"Embedding model loaded successfully ({EMBEDDING_DIMENSIONS} dimensions)")
            return True
        except ImportError as e:
            log.warning(f"sentence-transformers not available: {e}")
            self._available = False
            return False
        except Exception as e:
            log.error(f"Failed to load embedding model: {e}")
            self._available = False
            return False

    @property
    def available(self) -> bool:
        """Check if embedding model is available."""
        if self._available is None:
            self._load_model()
        return self._available or False

    @property
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        return EMBEDDING_DIMENSIONS

    def embed(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a single text.

        Returns list of floats, or None if embedding failed.
        """
        if not self._load_model():
            return None

        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            log.error(f"Embedding generation failed: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Generate embeddings for multiple texts.

        Returns list of embeddings, or None if embedding failed.
        """
        if not texts:
            return []

        if not self._load_model():
            return None

        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            log.error(f"Batch embedding generation failed: {e}")
            return None

    def warmup(self) -> bool:
        """
        Pre-load the model to reduce first-query latency.

        Returns True if warmup successful.
        """
        if self._load_model():
            # Run a dummy embedding to fully initialize
            try:
                _ = self._model.encode("warmup", convert_to_numpy=True)
                log.info("Embedding model warmed up")
                return True
            except Exception as e:
                log.error(f"Warmup failed: {e}")
                return False
        return False
