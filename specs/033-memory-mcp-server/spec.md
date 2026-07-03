# Feature Specification: Hybrid Memory MCP Server

**Feature Branch**: `033-memory-mcp-server`
**Created**: 2026-05-12
**Status**: Complete
**Input**: User description: "Implement better memory for NetClaw using a hybrid approach — structured database (SQLite) for precise factual recall with temporal validity, plus vector store (ChromaDB) for semantic search across past sessions."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record and Recall Network Facts (Priority: P1)

As a network engineer working with NetClaw across multiple sessions, I want the agent to remember factual information about my network (device states, configuration decisions, peering relationships, maintenance windows) with temporal validity so that it can answer precise questions like "what changed on PE2 last week?" or "when was the last time RR1's BGP session flapped?" without me repeating context.

**Why this priority**: Factual recall is the foundation. Every other memory capability (semantic search, decision log, timeline) depends on having structured facts stored with timestamps and entity references. This directly addresses the gap where daily markdown logs have no queryable structure.

**Independent Test**: Store a fact about a device ("PE2 BGP peer 10.0.0.1 went down"), then query it by entity ("PE2") and verify the fact is returned with correct timestamp and metadata.

**Acceptance Scenarios**:

1. **Given** NetClaw discovers a network fact during operations (e.g., "PE2 interface Gi0/0/0/1 is down since 14:30"),
   **When** the agent calls `memory_record_fact(entity="PE2", key="interface_gi0001_status", value="down", metadata={"interface": "Gi0/0/0/1", "since": "2026-05-12T14:30:00Z"})`,
   **Then** the fact is persisted with auto-generated ID, timestamp, and no expiry.

2. **Given** facts exist for a device,
   **When** the agent calls `memory_get_facts(entity="PE2")`,
   **Then** all current (non-invalidated) facts for PE2 are returned, most recent first.

3. **Given** a fact was previously recorded and the state changes,
   **When** the agent records a new fact with the same entity+key,
   **Then** the previous fact is marked with `valid_to` timestamp and the new fact becomes current.

4. **Given** facts span multiple time periods,
   **When** the agent calls `memory_timeline(entity="PE2", start="2026-05-01", end="2026-05-12")`,
   **Then** all facts (including invalidated ones) for PE2 within that window are returned chronologically.

5. **Given** no facts exist for a queried entity,
   **When** the agent calls `memory_get_facts(entity="NONEXISTENT")`,
   **Then** an empty result set is returned (not an error).

---

### User Story 2 - Semantic Recall Across Sessions (Priority: P2)

As a network engineer, I want to ask NetClaw questions like "what was that BGP issue we troubleshot last month?" and get relevant context from past sessions, even if I don't remember exact device names or timestamps.

**Why this priority**: Semantic search enables the "feels like it remembers" experience. It covers the fuzzy recall that structured queries can't handle — when you know roughly what happened but not the exact entity or timestamp.

**Independent Test**: Store a session summary describing a BGP troubleshooting session, then query "BGP flapping problem" and verify the relevant session is returned with a high similarity score.

**Acceptance Scenarios**:

1. **Given** session summaries have been stored from past interactions,
   **When** the agent calls `memory_recall(query="that OSPF adjacency issue on the core routers")`,
   **Then** the most semantically similar stored entries are returned (top-k, default 5) with similarity scores.

2. **Given** multiple sessions cover different topics,
   **When** the agent queries with a specific topic,
   **Then** only relevant sessions are returned, not unrelated ones (similarity threshold filtering).

3. **Given** a session just completed,
   **When** the agent calls `memory_store_session(summary="Troubleshot BGP...", entities=["PE2", "RR1"], topics=["bgp", "flapping"])`,
   **Then** the summary is embedded and stored for future semantic retrieval.

4. **Given** stored sessions span months,
   **When** the agent queries with optional time filter `memory_recall(query="...", after="2026-04-01")`,
   **Then** only sessions from after that date are considered.

---

### User Story 3 - Decision Log (Priority: P3)

As a network engineer reviewing past actions, I want NetClaw to maintain a log of significant decisions (why a particular route was chosen, why a change was rolled back, why a device was quarantined) so I can understand the rationale behind past actions without re-reading entire session transcripts.

**Why this priority**: Decisions are the highest-value memory. They capture not just what happened (GAIT does that) but *why*. This is critical for post-incident reviews, handoffs between engineers, and audit compliance.

**Independent Test**: Record a decision with context and rationale, then retrieve it by entity or time range and verify all fields are preserved.

**Acceptance Scenarios**:

1. **Given** the agent makes a significant operational decision,
   **When** it calls `memory_record_decision(context="PE2 BGP flapping for 30min", decision="Shut peer to prevent route churn", rationale="Repeated flaps causing network-wide convergence events", entities=["PE2"], cr_number="CHG0045678")`,
   **Then** the decision is stored with all fields and a generated ID.

2. **Given** decisions have been recorded over time,
   **When** the agent calls `memory_get_decisions(entity="PE2")`,
   **Then** all decisions involving PE2 are returned chronologically.

3. **Given** decisions exist,
   **When** the agent calls `memory_get_decisions(after="2026-05-01", before="2026-05-12")`,
   **Then** only decisions within that window are returned.

---

### User Story 4 - Fact Invalidation and Lifecycle (Priority: P4)

As a network engineer, I want facts to have a lifecycle — they can be superseded by newer facts or explicitly invalidated — so that NetClaw's memory reflects current reality, not stale state.

**Why this priority**: Without invalidation, memory becomes polluted with outdated facts. The agent needs to know that "PE2 was down" is no longer true without deleting the historical record.

**Independent Test**: Record a fact, invalidate it, verify it no longer appears in current queries but still appears in timeline queries.

**Acceptance Scenarios**:

1. **Given** a fact exists (e.g., "PE2 interface down"),
   **When** the agent calls `memory_invalidate(fact_id="...", reason="Interface restored")`,
   **Then** the fact's `valid_to` is set to now and it no longer appears in `memory_get_facts()` but appears in `memory_timeline()`.

2. **Given** a fact is recorded with the same entity+key as an existing current fact,
   **When** the new fact is stored,
   **Then** the old fact is automatically superseded (valid_to set, new fact becomes current).

---

### Edge Cases

- What happens when the SQLite database file is corrupted or missing on startup?
- How does the system handle concurrent writes (multiple tool calls in rapid succession)?
- What happens when ChromaDB embedding fails (network issue to embedding API, model unavailable)?
- How does the system behave when the vector store grows very large (>100K entries)?
- What happens when an entity name contains special characters or is extremely long?
- How does the system handle timezone differences in temporal queries?
- What happens when memory_recall returns no results above the similarity threshold?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store structured facts with entity, key, value, metadata, valid_from, and optional valid_to timestamps in SQLite.
- **FR-002**: System MUST support temporal queries — retrieve facts valid at a specific point in time or within a time range.
- **FR-003**: System MUST support fact supersession — recording a new fact with same entity+key automatically invalidates the previous one.
- **FR-004**: System MUST embed and store session summaries in ChromaDB for semantic retrieval.
- **FR-005**: System MUST support similarity-based retrieval with configurable top-k and threshold.
- **FR-006**: System MUST store decisions with context, decision text, rationale, related entities, and optional CR number.
- **FR-007**: System MUST NOT require network access for core operations — SQLite and ChromaDB are both local/file-based.
- **FR-008**: System MUST log all memory write operations to GAIT audit trail.
- **FR-009**: System MUST handle database initialization transparently — create schema on first run.
- **FR-010**: System MUST support filtering by entity, time range, and topic across all query tools.
- **FR-011**: System MUST use a local embedding model (sentence-transformers) to avoid external API dependencies for embeddings.
- **FR-012**: System MUST gracefully degrade if ChromaDB/embeddings fail — structured queries via SQLite continue working.

### Key Entities

- **Fact**: A piece of knowledge about a network entity with temporal validity (entity, key, value, valid_from, valid_to, metadata).
- **Decision**: A recorded operational decision with context, rationale, and entity references.
- **Session Summary**: An embedded text summary of a past interaction, stored in the vector store for semantic retrieval.
- **Entity**: A network object (device, interface, protocol instance, service) that facts and decisions reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Facts are retrievable by entity in <50ms for databases with up to 100K facts.
- **SC-002**: Semantic search returns relevant results (top-1 accuracy >80%) for queries that match stored session content.
- **SC-003**: Fact supersession correctly invalidates previous facts 100% of the time (no stale facts in current view).
- **SC-004**: Timeline queries return chronologically ordered results spanning the full history of an entity.
- **SC-005**: The system initializes cleanly on first run with no pre-existing database files.
- **SC-006**: All write operations produce GAIT audit entries.
- **SC-007**: The system operates fully offline (no external API calls for embeddings or storage).
- **SC-008**: Existing NetClaw skills and MCP servers remain fully functional after addition.

## Assumptions

- The host machine has Docker installed and sufficient disk space for the container image (~2GB with torch CPU + chromadb + sentence-transformers) and runtime data (SQLite ~100MB for 100K facts, ChromaDB ~500MB for 50K embedded sessions).
- The `sentence-transformers` library with `all-MiniLM-L6-v2` model (~80MB) is acceptable for local embeddings. The model is downloaded on first use inside the container.
- ChromaDB's persistent storage mode (file-based, no server) is sufficient for the expected data volume.
- Session summaries are generated by the agent at session end (OpenClaw's existing `memory/YYYY-MM-DD.md` pattern provides the raw material).
- The MCP server runs as a Docker container with stdio transport (`docker run -i`), with `memory/` volume-mounted for persistent storage.
- Heavy Python dependencies (torch, chromadb, sentence-transformers) are isolated in the container, not installed in the host venv.
