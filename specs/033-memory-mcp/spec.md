# Feature Specification: Hybrid Memory MCP Server

**Feature Branch**: `033-memory-mcp`
**Created**: 2026-06-20
**Status**: Draft
**Input**: User description: "Implement a hybrid memory MCP server for NetClaw that combines: 1) Structured storage (SQLite) for precise factual recall with temporal validity - facts about devices, configurations, states with valid_from/valid_to timestamps. 2) Semantic storage (ChromaDB with all-MiniLM-L6-v2 embeddings) for fuzzy recall of past sessions and troubleshooting narratives. 3) Graph links for entity relationships (device A peers_with device B, service X depends_on device Y). 4) Decision log with rationale for auditing why actions were taken. The server should have 10 MCP tools: memory_record_fact, memory_get_facts, memory_invalidate, memory_timeline, memory_store_session, memory_recall, memory_record_decision, memory_get_decisions, memory_link_entities, memory_query_graph. Persistence in ~/.openclaw/memory/ survives restarts. Integrates with existing SOUL.md, SOUL-EXPERTISE.md, SOUL-SKILLS.md, HEARTBEAT.md, and GAIT. Uses Docker container with pre-downloaded embedding model for offline operation."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record and Recall Network Facts (Priority: P1)

As a network engineer working with NetClaw across multiple sessions, I want the agent to remember factual information about my network (device states, configuration decisions, peering relationships, maintenance windows) with temporal validity so that it can answer precise questions like "what changed on PE2 last week?" or "when was the last time RR1's BGP session flapped?" without me repeating context.

**Why this priority**: Factual recall is the foundation of persistent memory. Every other capability (semantic search, decision log, graph relationships) depends on having structured facts stored with timestamps and entity references. This directly addresses the core problem where NetClaw forgets everything between sessions.

**Independent Test**: Store a fact about a device ("PE2 BGP peer 10.0.0.1 went down at 14:30"), then query it by entity ("PE2") and verify the fact is returned with correct timestamp and metadata.

**Acceptance Scenarios**:

1. **Given** NetClaw discovers a network fact during operations (e.g., "PE2 interface Gi0/0/0/1 is down since 14:30"), **When** the agent records the fact with entity, key, value, and metadata, **Then** the fact is persisted with auto-generated ID, timestamp, and no expiry.

2. **Given** facts exist for a device, **When** the agent queries facts by entity name, **Then** all current (non-invalidated) facts for that entity are returned, most recent first.

3. **Given** a fact was previously recorded and the state changes, **When** the agent records a new fact with the same entity and key, **Then** the previous fact is marked with an end timestamp and the new fact becomes current.

4. **Given** facts span multiple time periods, **When** the agent queries the timeline for an entity within a date range, **Then** all facts (including invalidated ones) within that window are returned chronologically.

5. **Given** no facts exist for a queried entity, **When** the agent queries by that entity name, **Then** an empty result set is returned (not an error).

---

### User Story 2 - Semantic Recall Across Sessions (Priority: P2)

As a network engineer, I want to ask NetClaw questions like "what was that BGP issue we troubleshot last month?" and get relevant context from past sessions, even if I don't remember exact device names or timestamps.

**Why this priority**: Semantic search enables the "feels like it remembers" experience. It covers the fuzzy recall that structured queries cannot handle — when you know roughly what happened but not the exact entity or timestamp. This is the second most valuable capability after structured facts.

**Independent Test**: Store a session summary describing a BGP troubleshooting session, then query "BGP flapping problem" and verify the relevant session is returned with a high similarity score.

**Acceptance Scenarios**:

1. **Given** session summaries have been stored from past interactions, **When** the agent searches with a natural language query about a topic, **Then** the most semantically similar stored entries are returned with similarity scores.

2. **Given** multiple sessions cover different topics, **When** the agent queries with a specific topic, **Then** only relevant sessions are returned, not unrelated ones (via similarity threshold filtering).

3. **Given** a session just completed, **When** the agent stores a session summary with associated entities and topics, **Then** the summary is embedded and stored for future semantic retrieval.

4. **Given** stored sessions span months, **When** the agent queries with an optional time filter, **Then** only sessions from after that date are considered.

---

### User Story 3 - Decision Log with Rationale (Priority: P3)

As a network engineer reviewing past actions, I want NetClaw to maintain a log of significant decisions (why a particular route was chosen, why a change was rolled back, why a device was quarantined) so I can understand the rationale behind past actions without re-reading entire session transcripts.

**Why this priority**: Decisions are the highest-value memory for audit and handoff purposes. They capture not just what happened (GAIT does that) but *why*. This is critical for post-incident reviews, handoffs between engineers, and compliance.

**Independent Test**: Record a decision with context and rationale, then retrieve it by entity or time range and verify all fields are preserved including the change request reference.

**Acceptance Scenarios**:

1. **Given** the agent makes a significant operational decision, **When** it records the decision with context, decision text, rationale, related entities, and optional change request number, **Then** the decision is stored with all fields and a generated ID.

2. **Given** decisions have been recorded over time, **When** the agent queries decisions by entity, **Then** all decisions involving that entity are returned chronologically.

3. **Given** decisions exist, **When** the agent queries decisions within a time window, **Then** only decisions within that window are returned.

---

### User Story 4 - Entity Relationship Tracking (Priority: P4)

As a network engineer, I want NetClaw to track relationships between network entities (device A peers with device B, service X depends on device Y) so that I can ask questions like "what devices depend on RR1?" or understand the impact radius of a potential change.

**Why this priority**: Graph relationships enable impact analysis and topology awareness. While not essential for basic memory, they significantly enhance NetClaw's ability to reason about network dependencies and provide intelligent recommendations.

**Independent Test**: Create a link between two entities with a relationship type, then query the graph for all entities related to one of them and verify the relationship is returned.

**Acceptance Scenarios**:

1. **Given** a relationship is discovered between entities, **When** the agent creates a link with subject, predicate, and object, **Then** the link is stored with timestamp and metadata.

2. **Given** links exist for an entity, **When** the agent queries incoming relationships to that entity, **Then** all entities linking TO it are returned with relationship types.

3. **Given** links exist with various relationship types, **When** the agent queries by specific predicate, **Then** only relationships of that type are returned.

4. **Given** a network of linked entities, **When** the agent queries with a traversal depth greater than one, **Then** multi-hop neighbors are returned.

---

### User Story 5 - Fact Lifecycle Management (Priority: P5)

As a network engineer, I want facts to have a lifecycle — they can be superseded by newer facts or explicitly invalidated — so that NetClaw's memory reflects current reality rather than stale state.

**Why this priority**: Without lifecycle management, memory becomes polluted with outdated facts. The agent needs to know that "PE2 was down" is no longer true without deleting the historical record for timeline queries.

**Independent Test**: Record a fact, invalidate it with a reason, verify it no longer appears in current queries but still appears in timeline queries.

**Acceptance Scenarios**:

1. **Given** a fact exists, **When** the agent explicitly invalidates it with a reason, **Then** the fact is marked with an end timestamp and excluded from current queries but included in timeline queries.

2. **Given** a fact is recorded with the same entity and key as an existing current fact, **When** the new fact is stored, **Then** the old fact is automatically superseded.

---

### Edge Cases

- What happens when the database file is corrupted or missing on startup?
- How does the system handle concurrent writes from multiple tool calls in rapid succession? → Serialize writes via queue.
- What happens when the embedding model fails to load or generate embeddings?
- How does the system behave when the vector store grows very large (greater than 100K entries)?
- What happens when an entity name contains special characters or is extremely long?
- How does the system handle timezone differences in temporal queries?
- What happens when semantic search returns no results above the similarity threshold?
- How does the system recover if shutdown occurs mid-write?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store structured facts with entity, key, value, metadata, valid_from, and optional valid_to timestamps.
- **FR-002**: System MUST support temporal queries to retrieve facts valid at a specific point in time or within a time range.
- **FR-003**: System MUST support fact supersession where recording a new fact with same entity and key automatically invalidates the previous one.
- **FR-004**: System MUST embed and store session summaries for semantic retrieval using similarity search.
- **FR-005**: System MUST support similarity-based retrieval with configurable result count and minimum threshold.
- **FR-006**: System MUST store decisions with context, decision text, rationale, related entities, and optional change request reference.
- **FR-007**: System MUST store entity relationships as subject-predicate-object triples with timestamps.
- **FR-008**: System MUST support graph queries by entity, relationship type, and traversal depth.
- **FR-009**: System MUST NOT require network access for core operations after initial setup.
- **FR-010**: System MUST initialize storage transparently on first run without manual setup.
- **FR-011**: System MUST persist all data across restarts without data loss.
- **FR-012**: System MUST gracefully degrade if semantic search is unavailable — structured queries continue working.
- **FR-013**: System MUST provide exactly 10 MCP tools: memory_record_fact, memory_get_facts, memory_invalidate, memory_timeline, memory_store_session, memory_recall, memory_record_decision, memory_get_decisions, memory_link_entities, memory_query_graph.
- **FR-014**: System MUST automatically prune facts, sessions, and decisions older than 1 year to manage storage growth.
- **FR-015**: System MUST serialize concurrent write operations via an internal queue to prevent race conditions.
- **FR-016**: System MUST log all memory write operations (facts, decisions, sessions, links) to GAIT audit trail.
- **FR-017**: System MUST normalize entity names to lowercase for matching while preserving original casing for display.

### Key Entities

- **Fact**: A piece of knowledge about a network entity with temporal validity. Contains entity reference, key-value pair, metadata, and validity timestamps.
- **Decision**: A recorded operational decision with context describing what was happening, the decision made, rationale explaining why, entity references, and optional change request link.
- **Session Summary**: An embedded text summary of a past interaction, stored for semantic retrieval with associated entities and topics.
- **Entity Link**: A relationship between two entities expressed as subject-predicate-object with timestamp, enabling graph queries.
- **Entity**: A network object (device, interface, protocol instance, service) that facts, decisions, and links reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Network engineers can retrieve facts about a specific device in under one second for collections with up to 100,000 facts.
- **SC-002**: Semantic search returns the most relevant past session as the top result at least 80% of the time when the query matches stored content.
- **SC-003**: Fact supersession correctly invalidates previous facts 100% of the time with no stale facts appearing in current queries.
- **SC-004**: Timeline queries return chronologically ordered results spanning the full history of an entity.
- **SC-005**: The system initializes and becomes ready on first run with no pre-existing data files within 30 seconds.
- **SC-006**: All stored data survives system restarts with zero data loss under normal shutdown conditions.
- **SC-007**: The system operates fully offline after initial setup with no external service dependencies.
- **SC-008**: Existing NetClaw skills and MCP servers remain fully functional after memory integration.
- **SC-009**: Network engineers report reduced time spent re-explaining network context by at least 50% after one week of use.

## Clarifications

### Session 2026-06-20

- Q: Should the system automatically prune or archive old memory data? → A: Auto-prune facts older than 1 year
- Q: How should the system handle concurrent write operations? → A: Serialize writes (queue, process one at a time)
- Q: What level of observability should memory operations have? → A: Log writes to GAIT only (audit trail)
- Q: Should entity names be normalized for consistent matching? → A: Case-insensitive (normalize to lowercase for matching)
- Q: Should memory data be encrypted at rest? → A: No encryption (rely on filesystem permissions)
- Q: How should the system handle timezone differences in temporal queries? → A: All timestamps stored as UTC; client responsible for display conversion
- Q: How does the system behave when the vector store grows very large? → A: ChromaDB handles 100K+ entries efficiently; 1-year auto-prune bounds growth

## Assumptions

- The host machine has sufficient disk space for storage (approximately 500MB for one year of typical use).
- The embedding model (approximately 80MB) can be pre-downloaded and cached locally.
- Session summaries are generated by the agent at session end or can be derived from existing daily logs.
- The MCP server runs as a uvx package (consistent with other NetClaw MCP servers); OpenShell provides container isolation at the platform level.
- Operators accept that semantic search quality depends on the quality of stored summaries.
- The storage location (~/.openclaw/memory/) is writable and has appropriate permissions.
- The system will integrate with but not replace existing GAIT audit functionality.
- Heavy dependencies for embeddings are managed by uv cache rather than installed system-wide.
- Data protection relies on filesystem permissions; no encryption at rest is required for this local-only system.
