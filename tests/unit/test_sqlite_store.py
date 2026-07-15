"""
Unit tests for SQLite storage backend.
"""

import os
import tempfile
import pytest
from pathlib import Path

# Add the memory-mcp module to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "memory-mcp"))

from storage.sqlite_store import (
    SQLiteStore,
    normalize_entity,
    validate_entity,
    validate_key,
    validate_value,
    validate_metadata,
    validate_timestamp,
    validate_predicate,
    validate_cr_number,
)


class TestNormalization:
    """Tests for entity normalization."""

    def test_normalize_lowercase(self):
        assert normalize_entity("PE2") == "pe2"

    def test_normalize_strips_whitespace(self):
        assert normalize_entity("  PE2  ") == "pe2"

    def test_normalize_mixed_case(self):
        assert normalize_entity("Router-1-DC-East") == "router-1-dc-east"


class TestValidation:
    """Tests for validation functions."""

    def test_validate_entity_valid(self):
        is_valid, err = validate_entity("PE2")
        assert is_valid is True
        assert err is None

    def test_validate_entity_empty(self):
        is_valid, err = validate_entity("")
        assert is_valid is False
        assert "empty" in err.lower()

    def test_validate_entity_too_long(self):
        is_valid, err = validate_entity("x" * 300)
        assert is_valid is False
        assert "255" in err

    def test_validate_key_valid(self):
        is_valid, err = validate_key("bgp_state")
        assert is_valid is True

    def test_validate_value_valid(self):
        is_valid, err = validate_value("established")
        assert is_valid is True

    def test_validate_value_empty(self):
        is_valid, err = validate_value("")
        assert is_valid is False

    def test_validate_metadata_valid(self):
        is_valid, err = validate_metadata({"peer": "10.0.0.1"})
        assert is_valid is True

    def test_validate_metadata_none(self):
        is_valid, err = validate_metadata(None)
        assert is_valid is True

    def test_validate_metadata_not_dict(self):
        is_valid, err = validate_metadata("not a dict")
        assert is_valid is False

    def test_validate_timestamp_valid(self):
        is_valid, err = validate_timestamp("2026-06-20T14:30:00Z")
        assert is_valid is True

    def test_validate_timestamp_invalid(self):
        is_valid, err = validate_timestamp("not a timestamp")
        assert is_valid is False

    def test_validate_predicate_valid(self):
        is_valid, err = validate_predicate("peers_with")
        assert is_valid is True

    def test_validate_predicate_invalid_chars(self):
        is_valid, err = validate_predicate("Peers-With")
        assert is_valid is False

    def test_validate_cr_number_valid(self):
        is_valid, err = validate_cr_number("CHG0001234")
        assert is_valid is True

    def test_validate_cr_number_invalid(self):
        is_valid, err = validate_cr_number("INC0001234")
        assert is_valid is False

    def test_validate_cr_number_none(self):
        is_valid, err = validate_cr_number(None)
        assert is_valid is True


class TestSQLiteStore:
    """Tests for SQLite store operations."""

    @pytest.fixture
    def store(self):
        """Create a temporary SQLite store."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = SQLiteStore(db_path)
            yield store
            store.close()

    def test_init_creates_database(self, store):
        """Database file should be created on init."""
        assert os.path.exists(store.db_path)

    def test_check_integrity(self, store):
        """Integrity check should pass on fresh database."""
        ok, msg = store.check_integrity()
        assert ok is True

    def test_insert_fact(self, store):
        """Should insert a fact successfully."""
        result = store.insert_fact("pe2", "bgp_state", "established")
        assert result["success"] is True
        assert result["data"]["entity"] == "pe2"
        assert result["data"]["key"] == "bgp_state"
        assert result["data"]["value"] == "established"
        assert result["data"]["id"] is not None

    def test_insert_fact_with_metadata(self, store):
        """Should insert a fact with metadata."""
        metadata = {"peer": "10.0.0.1", "asn": 65000}
        result = store.insert_fact("pe2", "bgp_peer", "active", metadata)
        assert result["success"] is True
        assert result["data"]["metadata"] == metadata

    def test_insert_fact_supersedes_existing(self, store):
        """Should supersede existing fact with same entity+key."""
        # Insert first fact
        result1 = store.insert_fact("pe2", "bgp_state", "down")
        assert result1["success"] is True
        first_id = result1["data"]["id"]

        # Insert second fact with same entity+key
        result2 = store.insert_fact("pe2", "bgp_state", "established")
        assert result2["success"] is True
        assert result2["data"]["superseded_id"] == first_id

    def test_get_current_facts(self, store):
        """Should return current facts for entity."""
        store.insert_fact("pe2", "bgp_state", "established")
        store.insert_fact("pe2", "location", "DC-East")

        result = store.get_current_facts("pe2")
        assert result["success"] is True
        assert result["data"]["count"] == 2

    def test_get_current_facts_excludes_invalidated(self, store):
        """Should not return invalidated facts."""
        result1 = store.insert_fact("pe2", "bgp_state", "down")
        store.invalidate_fact(result1["data"]["id"], "Session recovered")
        store.insert_fact("pe2", "bgp_state", "established")

        result = store.get_current_facts("pe2")
        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["facts"][0]["value"] == "established"

    def test_invalidate_fact(self, store):
        """Should invalidate a fact."""
        result1 = store.insert_fact("pe2", "bgp_state", "down")
        fact_id = result1["data"]["id"]

        result2 = store.invalidate_fact(fact_id, "Session recovered")
        assert result2["success"] is True
        assert result2["data"]["valid_to"] is not None

    def test_invalidate_nonexistent_fact(self, store):
        """Should fail to invalidate nonexistent fact."""
        result = store.invalidate_fact("nonexistent", "reason")
        assert result["success"] is False
        assert result["error"]["code"] == "FACT_NOT_FOUND"

    def test_get_timeline(self, store):
        """Should return timeline including invalidated facts."""
        store.insert_fact("pe2", "bgp_state", "down")
        store.insert_fact("pe2", "bgp_state", "established")

        result = store.get_timeline("pe2")
        assert result["success"] is True
        assert result["data"]["count"] == 2

    def test_insert_decision(self, store):
        """Should insert a decision."""
        result = store.insert_decision(
            context="BGP session flapping",
            decision="Increased hold timer",
            rationale="Reduce flap frequency",
            entities=["pe2", "rr1"],
            cr_number="CHG0001234",
        )
        assert result["success"] is True
        assert result["data"]["entities"] == ["pe2", "rr1"]

    def test_query_decisions_by_entity(self, store):
        """Should query decisions by entity."""
        store.insert_decision(
            context="Issue with PE2",
            decision="Restart BGP",
            rationale="Clear stuck session",
            entities=["pe2"],
        )

        result = store.query_decisions(entity="pe2")
        assert result["success"] is True
        assert result["data"]["count"] == 1

    def test_insert_link(self, store):
        """Should insert a link between entities."""
        result = store.insert_link("pe2", "peers_with", "rr1")
        assert result["success"] is True
        assert result["data"]["subject"] == "pe2"
        assert result["data"]["predicate"] == "peers_with"
        assert result["data"]["object"] == "rr1"

    def test_insert_link_returns_existing(self, store):
        """Should return existing link if duplicate."""
        result1 = store.insert_link("pe2", "peers_with", "rr1")
        result2 = store.insert_link("pe2", "peers_with", "rr1")
        assert result2["success"] is True
        assert result2["data"]["id"] == result1["data"]["id"]
        assert result2["data"].get("existing") is True

    def test_insert_link_self_reference(self, store):
        """Should fail for self-referencing link."""
        result = store.insert_link("pe2", "peers_with", "pe2")
        assert result["success"] is False
        assert result["error"]["code"] == "SELF_LINK"

    def test_query_graph_outgoing(self, store):
        """Should query outgoing relationships."""
        store.insert_link("pe2", "peers_with", "rr1")
        store.insert_link("pe2", "connects_to", "sw1")

        result = store.query_graph("pe2", direction="outgoing")
        assert result["success"] is True
        assert len(result["data"]["relationships"]["outgoing"]) == 2

    def test_query_graph_incoming(self, store):
        """Should query incoming relationships."""
        store.insert_link("nms1", "managed_by", "pe2")

        result = store.query_graph("pe2", direction="incoming")
        assert result["success"] is True
        assert len(result["data"]["relationships"]["incoming"]) == 1

    def test_prune_old_data(self, store):
        """Should prune old data."""
        # Insert some data
        store.insert_fact("pe2", "test", "value")

        # Prune with 0 days (should prune nothing since data is fresh)
        result = store.prune_old_data(days=0)
        assert result["success"] is True
        # Data should still exist since it's less than 0 days old
        # (This is a boundary test - real pruning would use 365 days)
