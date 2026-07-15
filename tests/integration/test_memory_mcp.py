"""
Integration tests for Memory MCP Server.

These tests verify end-to-end workflows across multiple components.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# Add the memory-mcp module to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "mcp-servers" / "memory-mcp"))


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sqlite_store(temp_data_dir):
    """Create a SQLite store for testing."""
    from storage.sqlite_store import SQLiteStore
    db_path = os.path.join(temp_data_dir, "test.db")
    return SQLiteStore(db_path)


@pytest.fixture
def chroma_store(temp_data_dir):
    """Create a ChromaDB store with mock embedder for testing."""
    from storage.chroma_store import ChromaStore

    embedder = MagicMock()
    embedder.available = True
    embedder.embed.return_value = [0.1] * 384
    embedder.dimensions = 384

    return ChromaStore(temp_data_dir, embedder)


# =============================================================================
# User Story 1: Facts Integration Tests
# =============================================================================

class TestFactRecordingFlow:
    """Integration tests for fact recording workflow."""

    def test_record_and_retrieve_fact(self, sqlite_store):
        """Should record a fact and retrieve it."""
        # Record a fact
        result = sqlite_store.insert_fact("pe2", "bgp_state", "established")
        assert result["success"] is True
        fact_id = result["data"]["id"]

        # Retrieve it
        result = sqlite_store.get_current_facts("pe2")
        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["facts"][0]["id"] == fact_id
        assert result["data"]["facts"][0]["value"] == "established"

    def test_record_multiple_facts_same_entity(self, sqlite_store):
        """Should record multiple facts for same entity."""
        sqlite_store.insert_fact("pe2", "bgp_state", "established")
        sqlite_store.insert_fact("pe2", "location", "DC-East")
        sqlite_store.insert_fact("pe2", "model", "NCS-5501")

        result = sqlite_store.get_current_facts("pe2")
        assert result["success"] is True
        assert result["data"]["count"] == 3

    def test_supersession_preserves_history(self, sqlite_store):
        """Should supersede old fact but preserve in timeline."""
        # Record original fact
        result1 = sqlite_store.insert_fact("pe2", "bgp_state", "down")
        old_id = result1["data"]["id"]

        # Supersede with new value
        result2 = sqlite_store.insert_fact("pe2", "bgp_state", "established")
        new_id = result2["data"]["id"]
        assert result2["data"]["superseded_id"] == old_id

        # Current facts should only show new value
        current = sqlite_store.get_current_facts("pe2")
        assert current["data"]["count"] == 1
        assert current["data"]["facts"][0]["id"] == new_id

        # Timeline should show both
        timeline = sqlite_store.get_timeline("pe2")
        assert timeline["data"]["count"] == 2

    def test_invalidation_workflow(self, sqlite_store):
        """Should invalidate fact and exclude from current queries."""
        # Record a fact
        result = sqlite_store.insert_fact("pe2", "bgp_state", "down")
        fact_id = result["data"]["id"]

        # Invalidate it
        result = sqlite_store.invalidate_fact(fact_id, "Session recovered manually")
        assert result["success"] is True
        assert result["data"]["valid_to"] is not None

        # Should not appear in current facts
        current = sqlite_store.get_current_facts("pe2")
        assert current["data"]["count"] == 0

        # Should still appear in timeline
        timeline = sqlite_store.get_timeline("pe2")
        assert timeline["data"]["count"] == 1

    def test_entity_case_insensitivity(self, sqlite_store):
        """Should normalize entity names for consistent matching."""
        # Record with uppercase
        sqlite_store.insert_fact("PE2", "bgp_state", "established")

        # Query with lowercase
        result = sqlite_store.get_current_facts("pe2")
        assert result["data"]["count"] == 1

        # Query with mixed case
        result = sqlite_store.get_current_facts("Pe2")
        assert result["data"]["count"] == 1

    def test_fact_with_metadata(self, sqlite_store):
        """Should store and retrieve metadata."""
        metadata = {"peer_ip": "10.0.0.1", "asn": 65000, "hold_time": 180}
        result = sqlite_store.insert_fact("pe2", "bgp_peer", "active", metadata)
        assert result["success"] is True

        facts = sqlite_store.get_current_facts("pe2")
        assert facts["data"]["facts"][0]["metadata"] == metadata


# =============================================================================
# User Story 2: Semantic Search Integration Tests
# =============================================================================

class TestSemanticSearchFlow:
    """Integration tests for semantic search workflow."""

    def test_store_and_recall_session(self, chroma_store):
        """Should store a session and recall it semantically."""
        # Store a session
        result = chroma_store.store_session(
            summary="Troubleshot BGP flapping on PE2 by adjusting MTU settings",
            entities=["pe2", "rr1"],
            topics=["bgp", "mtu", "troubleshooting"],
        )
        assert result["success"] is True
        session_id = result["data"]["id"]
        assert session_id.startswith("sess_")

    def test_semantic_search_graceful_degradation(self, temp_data_dir):
        """Should gracefully degrade when embedder unavailable."""
        from storage.chroma_store import ChromaStore

        # Create store with unavailable embedder
        embedder = MagicMock()
        embedder.available = False

        store = ChromaStore(temp_data_dir, embedder)
        store._available = False

        # Search should succeed with empty results
        result = store.semantic_search("BGP troubleshooting")
        assert result["success"] is True
        assert result["data"]["count"] == 0
        assert "unavailable" in result["data"].get("note", "").lower()


# =============================================================================
# User Story 3: Decisions Integration Tests
# =============================================================================

class TestDecisionLogFlow:
    """Integration tests for decision logging workflow."""

    def test_record_and_retrieve_decision(self, sqlite_store):
        """Should record a decision and retrieve it."""
        # Record a decision
        result = sqlite_store.insert_decision(
            context="BGP session to RR1 was flapping every 30 seconds",
            decision="Increased BGP hold timer from 90s to 180s",
            rationale="Reduce flap frequency while investigating root cause",
            entities=["pe2", "rr1"],
            cr_number="CHG0001234",
        )
        assert result["success"] is True
        decision_id = result["data"]["id"]

        # Retrieve by entity
        result = sqlite_store.query_decisions(entity="pe2")
        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["decisions"][0]["id"] == decision_id

    def test_decision_linked_to_multiple_entities(self, sqlite_store):
        """Should link decision to all specified entities."""
        sqlite_store.insert_decision(
            context="Network-wide OSPF reconvergence",
            decision="Enabled OSPF LFA on all PE routers",
            rationale="Improve convergence time",
            entities=["pe1", "pe2", "pe3", "pe4"],
        )

        # Should be queryable by any entity
        for entity in ["pe1", "pe2", "pe3", "pe4"]:
            result = sqlite_store.query_decisions(entity=entity)
            assert result["data"]["count"] == 1


# =============================================================================
# User Story 4: Graph Links Integration Tests
# =============================================================================

class TestGraphLinksFlow:
    """Integration tests for entity graph workflow."""

    def test_create_and_query_relationships(self, sqlite_store):
        """Should create links and query the graph."""
        # Create relationships
        sqlite_store.insert_link("pe2", "peers_with", "rr1")
        sqlite_store.insert_link("pe2", "peers_with", "rr2")
        sqlite_store.insert_link("pe2", "connects_to", "sw1")

        # Query outgoing
        result = sqlite_store.query_graph("pe2", direction="outgoing")
        assert result["success"] is True
        assert len(result["data"]["relationships"]["outgoing"]) == 3

    def test_bidirectional_query(self, sqlite_store):
        """Should find relationships in both directions."""
        sqlite_store.insert_link("pe2", "peers_with", "rr1")

        # Query from subject
        result = sqlite_store.query_graph("pe2", direction="both")
        assert len(result["data"]["relationships"]["outgoing"]) == 1

        # Query from object
        result = sqlite_store.query_graph("rr1", direction="both")
        assert len(result["data"]["relationships"]["incoming"]) == 1

    def test_predicate_filtering(self, sqlite_store):
        """Should filter by predicate type."""
        sqlite_store.insert_link("pe2", "peers_with", "rr1")
        sqlite_store.insert_link("pe2", "connects_to", "sw1")

        # Filter by predicate
        result = sqlite_store.query_graph("pe2", predicate="peers_with")
        outgoing = result["data"]["relationships"]["outgoing"]
        assert all(r["predicate"] == "peers_with" for r in outgoing)

    def test_duplicate_link_handling(self, sqlite_store):
        """Should handle duplicate link gracefully."""
        result1 = sqlite_store.insert_link("pe2", "peers_with", "rr1")
        result2 = sqlite_store.insert_link("pe2", "peers_with", "rr1")

        # Should return existing link
        assert result2["data"]["id"] == result1["data"]["id"]
        assert result2["data"].get("existing") is True


# =============================================================================
# User Story 5: Fact Lifecycle Integration Tests
# =============================================================================

class TestFactLifecycleFlow:
    """Integration tests for fact lifecycle management."""

    def test_full_lifecycle(self, sqlite_store):
        """Should track fact through its full lifecycle."""
        # Create fact
        result = sqlite_store.insert_fact("pe2", "status", "online")
        fact_id = result["data"]["id"]
        assert result["data"]["valid_to"] is None

        # Update fact (supersession)
        result = sqlite_store.insert_fact("pe2", "status", "maintenance")
        new_id = result["data"]["id"]
        assert result["data"]["superseded_id"] == fact_id

        # Invalidate with reason
        result = sqlite_store.invalidate_fact(new_id, "Device decommissioned")
        assert result["data"]["valid_to"] is not None

        # Timeline shows full history
        timeline = sqlite_store.get_timeline("pe2")
        assert timeline["data"]["count"] == 2

        # Current shows nothing (all invalidated)
        current = sqlite_store.get_current_facts("pe2")
        assert current["data"]["count"] == 0

    def test_timeline_ordering(self, sqlite_store):
        """Should return timeline in chronological order."""
        import time

        # Create facts with small delays
        sqlite_store.insert_fact("pe2", "state", "v1")
        time.sleep(0.01)
        sqlite_store.insert_fact("pe2", "state", "v2")
        time.sleep(0.01)
        sqlite_store.insert_fact("pe2", "state", "v3")

        timeline = sqlite_store.get_timeline("pe2")
        facts = timeline["data"]["timeline"]

        # Should be ordered by valid_from
        timestamps = [f["valid_from"] for f in facts]
        assert timestamps == sorted(timestamps)


# =============================================================================
# Cross-Story Integration Tests
# =============================================================================

class TestCrossStoryIntegration:
    """Tests that span multiple user stories."""

    def test_decision_references_facts_and_links(self, sqlite_store):
        """Should track related facts, decisions, and links."""
        # Record initial state
        sqlite_store.insert_fact("pe2", "bgp_state", "down")
        sqlite_store.insert_link("pe2", "peers_with", "rr1")

        # Record decision
        sqlite_store.insert_decision(
            context="BGP session to RR1 is down",
            decision="Clear BGP session and monitor",
            rationale="Attempt recovery before escalation",
            entities=["pe2", "rr1"],
        )

        # Update state after action
        sqlite_store.insert_fact("pe2", "bgp_state", "established")

        # Verify all data accessible
        facts = sqlite_store.get_current_facts("pe2")
        assert facts["data"]["count"] == 1

        decisions = sqlite_store.query_decisions(entity="pe2")
        assert decisions["data"]["count"] == 1

        graph = sqlite_store.query_graph("pe2")
        assert len(graph["data"]["relationships"]["outgoing"]) == 1

    def test_multi_entity_incident_tracking(self, sqlite_store):
        """Should track incident across multiple entities."""
        entities = ["pe2", "pe3", "rr1"]

        # Create topology
        sqlite_store.insert_link("pe2", "peers_with", "rr1")
        sqlite_store.insert_link("pe3", "peers_with", "rr1")

        # Record incident state
        for entity in entities:
            sqlite_store.insert_fact(entity, "incident_id", "INC001")

        # Record resolution decision
        sqlite_store.insert_decision(
            context="Multiple PE routers lost BGP to RR1",
            decision="Restart RR1 BGP process",
            rationale="Common point of failure identified",
            entities=entities,
            cr_number="CHG0005678",
        )

        # Verify all entities linked to decision
        for entity in entities:
            decisions = sqlite_store.query_decisions(entity=entity)
            assert decisions["data"]["count"] == 1
