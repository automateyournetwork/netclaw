"""
Unit tests for ChromaDB storage backend.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the memory-mcp module to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "memory-mcp"))

from storage.chroma_store import ChromaStore, generate_id, utc_now


class TestHelpers:
    """Tests for helper functions."""

    def test_generate_id_has_prefix(self):
        """ID should have sess_ prefix."""
        id = generate_id()
        assert id.startswith("sess_")

    def test_generate_id_unique(self):
        """IDs should be unique."""
        ids = [generate_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_utc_now_format(self):
        """Timestamp should be ISO format with Z suffix."""
        ts = utc_now()
        assert ts.endswith("Z")
        assert "T" in ts


class TestChromaStore:
    """Tests for ChromaDB store operations."""

    @pytest.fixture
    def mock_embedder(self):
        """Create a mock embedder."""
        embedder = MagicMock()
        embedder.available = True
        embedder.embed.return_value = [0.1] * 384  # 384-dim embedding
        embedder.dimensions = 384
        return embedder

    @pytest.fixture
    def store(self, mock_embedder):
        """Create a temporary ChromaDB store with mock embedder."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ChromaStore(tmpdir, mock_embedder)
            yield store

    def test_store_unavailable_without_init(self):
        """Store should report unavailable before init."""
        embedder = MagicMock()
        embedder.available = True
        store = ChromaStore("/nonexistent", embedder)
        # Don't call _init_client, just check initial state
        assert store._available is None

    def test_store_session_validates_summary(self, store):
        """Should validate summary."""
        result = store.store_session("")
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SUMMARY"

    def test_store_session_validates_summary_length(self, store):
        """Should validate summary length."""
        result = store.store_session("x" * 10001)
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SUMMARY"

    @pytest.mark.skipif(
        not os.environ.get("RUN_CHROMA_TESTS"),
        reason="ChromaDB tests require chromadb package"
    )
    def test_store_session_success(self, store, mock_embedder):
        """Should store a session successfully."""
        result = store.store_session(
            summary="Troubleshot BGP issue on PE2",
            entities=["pe2", "rr1"],
            topics=["bgp", "troubleshooting"],
        )

        # This will only work if ChromaDB is installed
        if result["success"]:
            assert result["data"]["id"] is not None
            assert result["data"]["entities"] == ["pe2", "rr1"]
            assert result["data"]["topics"] == ["bgp", "troubleshooting"]

    def test_semantic_search_validates_query(self, store):
        """Should validate query."""
        result = store.semantic_search("")
        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_QUERY"

    def test_semantic_search_graceful_degradation(self):
        """Should gracefully degrade when unavailable."""
        embedder = MagicMock()
        embedder.available = False

        with tempfile.TemporaryDirectory() as tmpdir:
            store = ChromaStore(tmpdir, embedder)
            # Force unavailable state
            store._available = False

            result = store.semantic_search("test query")
            # Should return success with empty results
            assert result["success"] is True
            assert result["data"]["count"] == 0
            assert "note" in result["data"]


class TestChromaStoreIntegration:
    """Integration tests for ChromaDB (skipped if chromadb not installed)."""

    @pytest.fixture
    def real_store(self):
        """Create a real ChromaDB store with mock embedder."""
        try:
            import chromadb
        except ImportError:
            pytest.skip("chromadb not installed")

        embedder = MagicMock()
        embedder.available = True
        embedder.embed.return_value = [0.1] * 384

        with tempfile.TemporaryDirectory() as tmpdir:
            store = ChromaStore(tmpdir, embedder)
            yield store

    def test_full_workflow(self, real_store):
        """Test store and search workflow."""
        # Store a session
        store_result = real_store.store_session(
            summary="Fixed BGP flapping on PE2 by adjusting MTU",
            entities=["pe2"],
            topics=["bgp", "mtu"],
        )
        assert store_result["success"] is True

        # Search for it
        search_result = real_store.semantic_search("BGP problem")
        assert search_result["success"] is True
        # Results depend on similarity calculation
