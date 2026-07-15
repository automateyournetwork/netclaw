"""
Contract tests for Memory MCP Server tools.

These tests verify that the MCP tools conform to their API contracts
as defined in specs/033-memory-mcp/contracts/mcp-tools.md.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the memory-mcp module to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "memory-mcp"))


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_env(temp_data_dir):
    """Mock environment variables."""
    with patch.dict(os.environ, {"MEMORY_DATA_DIR": temp_data_dir}):
        yield temp_data_dir


# =============================================================================
# User Story 1: Facts
# =============================================================================

class TestMemoryRecordFactContract:
    """Contract tests for memory_record_fact tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        return SQLiteStore(db_path)

    def test_returns_success_structure(self, sqlite_store):
        """Response should have success, data, error structure."""
        result = sqlite_store.insert_fact("pe2", "bgp_state", "established")

        assert "success" in result
        assert result["success"] is True
        assert "data" in result
        assert result.get("error") is None or result["error"] is None

    def test_returns_required_fields(self, sqlite_store):
        """Response data should have all required fields."""
        result = sqlite_store.insert_fact("pe2", "bgp_state", "established")

        data = result["data"]
        assert "id" in data
        assert "entity" in data
        assert "key" in data
        assert "value" in data
        assert "valid_from" in data
        assert "valid_to" in data

    def test_entity_normalized_to_lowercase(self, sqlite_store):
        """Entity should be normalized to lowercase."""
        result = sqlite_store.insert_fact("PE2", "bgp_state", "established")

        assert result["data"]["entity"] == "pe2"

    def test_returns_superseded_id_when_superseding(self, sqlite_store):
        """Should return superseded_id when superseding existing fact."""
        result1 = sqlite_store.insert_fact("pe2", "bgp_state", "down")
        result2 = sqlite_store.insert_fact("pe2", "bgp_state", "established")

        assert result2["data"]["superseded_id"] == result1["data"]["id"]

    def test_error_response_structure(self, sqlite_store):
        """Error response should have code and message."""
        result = sqlite_store.insert_fact("", "key", "value")  # Empty entity

        assert result["success"] is False
        assert "error" in result
        assert "code" in result["error"]
        assert "message" in result["error"]

    def test_invalid_entity_error_code(self, sqlite_store):
        """Should return INVALID_ENTITY for empty entity."""
        result = sqlite_store.insert_fact("", "key", "value")

        assert result["error"]["code"] == "INVALID_ENTITY"

    def test_invalid_key_error_code(self, sqlite_store):
        """Should return INVALID_KEY for empty key."""
        result = sqlite_store.insert_fact("pe2", "", "value")

        assert result["error"]["code"] == "INVALID_KEY"

    def test_invalid_value_error_code(self, sqlite_store):
        """Should return INVALID_VALUE for empty value."""
        result = sqlite_store.insert_fact("pe2", "key", "")

        assert result["error"]["code"] == "INVALID_VALUE"

    def test_invalid_metadata_error_code(self, sqlite_store):
        """Should return INVALID_METADATA for non-dict metadata."""
        result = sqlite_store.insert_fact("pe2", "key", "value", metadata="not a dict")

        assert result["error"]["code"] == "INVALID_METADATA"


class TestMemoryGetFactsContract:
    """Contract tests for memory_get_facts tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        store = SQLiteStore(db_path)
        # Add some test data
        store.insert_fact("pe2", "bgp_state", "established")
        store.insert_fact("pe2", "location", "DC-East")
        return store

    def test_returns_success_structure(self, sqlite_store):
        """Response should have success, data, error structure."""
        result = sqlite_store.get_current_facts("pe2")

        assert "success" in result
        assert result["success"] is True
        assert "data" in result

    def test_returns_required_fields(self, sqlite_store):
        """Response data should have entity, facts, count."""
        result = sqlite_store.get_current_facts("pe2")

        data = result["data"]
        assert "entity" in data
        assert "facts" in data
        assert "count" in data

    def test_facts_have_required_fields(self, sqlite_store):
        """Each fact should have required fields."""
        result = sqlite_store.get_current_facts("pe2")

        for fact in result["data"]["facts"]:
            assert "id" in fact
            assert "key" in fact
            assert "value" in fact
            assert "valid_from" in fact

    def test_empty_result_for_unknown_entity(self, sqlite_store):
        """Should return empty list for unknown entity."""
        result = sqlite_store.get_current_facts("unknown-device")

        assert result["success"] is True
        assert result["data"]["facts"] == []
        assert result["data"]["count"] == 0


# =============================================================================
# User Story 2: Semantic Search
# =============================================================================

class TestMemoryStoreSessionContract:
    """Contract tests for memory_store_session tool."""

    @pytest.fixture
    def chroma_store(self, temp_data_dir):
        """Create a ChromaDB store for testing."""
        from storage.chroma_store import ChromaStore
        from embeddings.embedder import Embedder

        embedder = MagicMock()
        embedder.available = True
        embedder.embed.return_value = [0.1] * 384

        return ChromaStore(temp_data_dir, embedder)

    def test_validates_empty_summary(self, chroma_store):
        """Should reject empty summary."""
        result = chroma_store.store_session("")

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SUMMARY"

    def test_validates_summary_length(self, chroma_store):
        """Should reject summary exceeding max length."""
        result = chroma_store.store_session("x" * 10001)

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_SUMMARY"


class TestMemoryRecallContract:
    """Contract tests for memory_recall tool."""

    @pytest.fixture
    def chroma_store(self, temp_data_dir):
        """Create a ChromaDB store for testing."""
        from storage.chroma_store import ChromaStore

        embedder = MagicMock()
        embedder.available = False  # Force unavailable

        return ChromaStore(temp_data_dir, embedder)

    def test_validates_empty_query(self, chroma_store):
        """Should reject empty query."""
        result = chroma_store.semantic_search("")

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_QUERY"

    def test_graceful_degradation(self, chroma_store):
        """Should return success with empty results when unavailable."""
        chroma_store._available = False

        result = chroma_store.semantic_search("test query")

        # Should succeed but with empty results
        assert result["success"] is True
        assert result["data"]["count"] == 0


# =============================================================================
# User Story 3: Decisions
# =============================================================================

class TestMemoryRecordDecisionContract:
    """Contract tests for memory_record_decision tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        return SQLiteStore(db_path)

    def test_returns_success_structure(self, sqlite_store):
        """Response should have success, data, error structure."""
        result = sqlite_store.insert_decision(
            context="Test context",
            decision="Test decision",
            rationale="Test rationale",
            entities=["pe2"],
        )

        assert "success" in result
        assert result["success"] is True
        assert "data" in result

    def test_returns_required_fields(self, sqlite_store):
        """Response data should have all required fields."""
        result = sqlite_store.insert_decision(
            context="Test context",
            decision="Test decision",
            rationale="Test rationale",
            entities=["pe2"],
            cr_number="CHG0001234",
        )

        data = result["data"]
        assert "id" in data
        assert "context" in data
        assert "decision" in data
        assert "rationale" in data
        assert "entities" in data
        assert "created_at" in data

    def test_validates_empty_entities(self, sqlite_store):
        """Should reject empty entities list."""
        result = sqlite_store.insert_decision(
            context="Test context",
            decision="Test decision",
            rationale="Test rationale",
            entities=[],
        )

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_ENTITIES"

    def test_validates_cr_number_format(self, sqlite_store):
        """Should validate CR number format."""
        result = sqlite_store.insert_decision(
            context="Test context",
            decision="Test decision",
            rationale="Test rationale",
            entities=["pe2"],
            cr_number="INVALID",
        )

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_CR_NUMBER"


class TestMemoryGetDecisionsContract:
    """Contract tests for memory_get_decisions tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        store = SQLiteStore(db_path)
        store.insert_decision(
            context="Test context",
            decision="Test decision",
            rationale="Test rationale",
            entities=["pe2"],
        )
        return store

    def test_requires_entity_or_after(self, sqlite_store):
        """Should require at least entity or after."""
        result = sqlite_store.query_decisions()

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_QUERY"


# =============================================================================
# User Story 4: Graph Links
# =============================================================================

class TestMemoryLinkEntitiesContract:
    """Contract tests for memory_link_entities tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        return SQLiteStore(db_path)

    def test_returns_success_structure(self, sqlite_store):
        """Response should have success, data, error structure."""
        result = sqlite_store.insert_link("pe2", "peers_with", "rr1")

        assert "success" in result
        assert result["success"] is True
        assert "data" in result

    def test_returns_required_fields(self, sqlite_store):
        """Response data should have all required fields."""
        result = sqlite_store.insert_link("pe2", "peers_with", "rr1")

        data = result["data"]
        assert "id" in data
        assert "subject" in data
        assert "predicate" in data
        assert "object" in data
        assert "created_at" in data

    def test_normalizes_entities(self, sqlite_store):
        """Should normalize entity names to lowercase."""
        result = sqlite_store.insert_link("PE2", "peers_with", "RR1")

        assert result["data"]["subject"] == "pe2"
        assert result["data"]["object"] == "rr1"

    def test_rejects_self_link(self, sqlite_store):
        """Should reject self-referencing links."""
        result = sqlite_store.insert_link("pe2", "peers_with", "pe2")

        assert result["success"] is False
        assert result["error"]["code"] == "SELF_LINK"

    def test_validates_predicate_format(self, sqlite_store):
        """Should validate predicate format."""
        result = sqlite_store.insert_link("pe2", "Invalid-Predicate", "rr1")

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_PREDICATE"


class TestMemoryQueryGraphContract:
    """Contract tests for memory_query_graph tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        store = SQLiteStore(db_path)
        store.insert_link("pe2", "peers_with", "rr1")
        store.insert_link("pe2", "connects_to", "sw1")
        return store

    def test_returns_success_structure(self, sqlite_store):
        """Response should have success, data, error structure."""
        result = sqlite_store.query_graph("pe2")

        assert "success" in result
        assert result["success"] is True
        assert "data" in result

    def test_returns_required_fields(self, sqlite_store):
        """Response data should have entity and relationships."""
        result = sqlite_store.query_graph("pe2")

        data = result["data"]
        assert "entity" in data
        assert "relationships" in data
        assert "outgoing" in data["relationships"]
        assert "incoming" in data["relationships"]

    def test_validates_direction(self, sqlite_store):
        """Should validate direction parameter."""
        result = sqlite_store.query_graph("pe2", direction="invalid")

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_DIRECTION"

    def test_validates_depth_range(self, sqlite_store):
        """Should validate depth is 1-3."""
        result = sqlite_store.query_graph("pe2", depth=5)

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_DEPTH"


# =============================================================================
# User Story 5: Fact Lifecycle
# =============================================================================

class TestMemoryInvalidateContract:
    """Contract tests for memory_invalidate tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        store = SQLiteStore(db_path)
        result = store.insert_fact("pe2", "bgp_state", "down")
        store._test_fact_id = result["data"]["id"]
        return store

    def test_returns_success_structure(self, sqlite_store):
        """Response should have success, data, error structure."""
        result = sqlite_store.invalidate_fact(sqlite_store._test_fact_id, "Reason")

        assert "success" in result
        assert result["success"] is True

    def test_returns_required_fields(self, sqlite_store):
        """Response data should have required fields."""
        result = sqlite_store.invalidate_fact(sqlite_store._test_fact_id, "Reason")

        data = result["data"]
        assert "id" in data
        assert "valid_to" in data
        assert "invalidation_reason" in data

    def test_fact_not_found_error(self, sqlite_store):
        """Should return FACT_NOT_FOUND for unknown ID."""
        result = sqlite_store.invalidate_fact("nonexistent", "Reason")

        assert result["success"] is False
        assert result["error"]["code"] == "FACT_NOT_FOUND"

    def test_validates_empty_reason(self, sqlite_store):
        """Should reject empty reason."""
        result = sqlite_store.invalidate_fact(sqlite_store._test_fact_id, "")

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_REASON"


class TestMemoryTimelineContract:
    """Contract tests for memory_timeline tool."""

    @pytest.fixture
    def sqlite_store(self, temp_data_dir):
        """Create a SQLite store for testing."""
        from storage.sqlite_store import SQLiteStore
        db_path = os.path.join(temp_data_dir, "test.db")
        store = SQLiteStore(db_path)
        store.insert_fact("pe2", "bgp_state", "down")
        store.insert_fact("pe2", "bgp_state", "established")
        return store

    def test_returns_success_structure(self, sqlite_store):
        """Response should have success, data, error structure."""
        result = sqlite_store.get_timeline("pe2")

        assert "success" in result
        assert result["success"] is True

    def test_returns_required_fields(self, sqlite_store):
        """Response data should have entity, timeline, count."""
        result = sqlite_store.get_timeline("pe2")

        data = result["data"]
        assert "entity" in data
        assert "timeline" in data
        assert "count" in data

    def test_includes_superseded_facts(self, sqlite_store):
        """Timeline should include superseded facts."""
        result = sqlite_store.get_timeline("pe2")

        # Should have both the original and superseding fact
        assert result["data"]["count"] == 2

    def test_validates_timestamp_format(self, sqlite_store):
        """Should validate timestamp format."""
        result = sqlite_store.get_timeline("pe2", after="invalid-timestamp")

        assert result["success"] is False
        assert result["error"]["code"] == "INVALID_TIMESTAMP"
