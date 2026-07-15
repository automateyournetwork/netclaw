"""
Unit tests for Embedder module.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import os

# Add the memory-mcp module to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "memory-mcp"))

from embeddings.embedder import Embedder, MODEL_NAME, EMBEDDING_DIMENSIONS


class TestEmbedderConfig:
    """Tests for embedder configuration."""

    def test_model_name(self):
        """Should use all-MiniLM-L6-v2 model."""
        assert MODEL_NAME == "all-MiniLM-L6-v2"

    def test_embedding_dimensions(self):
        """Should have 384 dimensions."""
        assert EMBEDDING_DIMENSIONS == 384


class TestEmbedderLazyLoading:
    """Tests for lazy model loading."""

    def test_model_not_loaded_on_init(self):
        """Model should not be loaded on initialization."""
        embedder = Embedder()
        assert embedder._model is None

    def test_available_property_triggers_load(self):
        """Accessing available should trigger load attempt."""
        embedder = Embedder()
        # This will try to load the model
        # If sentence-transformers not installed, available will be False
        _ = embedder.available
        assert embedder._available is not None

    def test_dimensions_property(self):
        """Should return configured dimensions."""
        embedder = Embedder()
        assert embedder.dimensions == 384


class TestEmbedderWithMock:
    """Tests for embedder with mocked model."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock SentenceTransformer model."""
        import numpy as np

        model = MagicMock()
        model.encode.return_value = np.array([0.1] * 384)
        return model

    def test_embed_single_text(self, mock_model):
        """Should embed a single text."""
        embedder = Embedder()
        embedder._model = mock_model
        embedder._available = True

        result = embedder.embed("test text")

        assert result is not None
        assert len(result) == 384
        mock_model.encode.assert_called_once()

    def test_embed_batch(self, mock_model):
        """Should embed multiple texts."""
        import numpy as np

        mock_model.encode.return_value = np.array([[0.1] * 384, [0.2] * 384])

        embedder = Embedder()
        embedder._model = mock_model
        embedder._available = True

        result = embedder.embed_batch(["text1", "text2"])

        assert result is not None
        assert len(result) == 2
        assert len(result[0]) == 384

    def test_embed_empty_batch(self, mock_model):
        """Should handle empty batch."""
        embedder = Embedder()
        embedder._model = mock_model
        embedder._available = True

        result = embedder.embed_batch([])

        assert result == []

    def test_warmup(self, mock_model):
        """Should warm up the model."""
        import numpy as np

        mock_model.encode.return_value = np.array([0.1] * 384)

        embedder = Embedder()
        embedder._model = mock_model
        embedder._available = True

        result = embedder.warmup()

        assert result is True
        mock_model.encode.assert_called()


class TestEmbedderUnavailable:
    """Tests for embedder when model is unavailable."""

    def test_embed_returns_none_when_unavailable(self):
        """Should return None when model unavailable."""
        embedder = Embedder()
        embedder._available = False

        result = embedder.embed("test")

        assert result is None

    def test_embed_batch_returns_none_when_unavailable(self):
        """Should return None when model unavailable."""
        embedder = Embedder()
        embedder._available = False

        result = embedder.embed_batch(["test1", "test2"])

        assert result is None

    def test_warmup_returns_false_when_unavailable(self):
        """Should return False when warmup fails."""
        embedder = Embedder()
        embedder._available = False

        result = embedder.warmup()

        assert result is False


@pytest.mark.skipif(
    not os.environ.get("RUN_EMBEDDING_TESTS"),
    reason="Embedding tests require sentence-transformers package"
)
class TestEmbedderIntegration:
    """Integration tests with real model (skipped by default)."""

    def test_real_model_loading(self):
        """Test real model loading."""
        embedder = Embedder()

        # This will download the model if not cached
        is_available = embedder.available

        if is_available:
            result = embedder.embed("Test sentence for embedding")
            assert result is not None
            assert len(result) == 384
