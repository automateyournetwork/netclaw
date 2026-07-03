# Feature Specification: Layered Memory Integration

**Feature Branch**: `034-layered-memory-integration`
**Created**: 2026-06-20
**Status**: Draft
**Input**: Integrate Memory MCP Server with existing MEMORY.md system in SOUL.md as a layered memory architecture mimicking human brain organization.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record Facts During Operation (Priority: P1)

As a network engineer working with NetClaw, I want the agent to automatically record facts about network entities during troubleshooting sessions so that specific device states, configurations, and observations are preserved for future reference.

**Why this priority**: Recording facts is the foundation of the memory system. Without capturing information during sessions, there is nothing to retrieve later. This enables all other memory capabilities.

**Independent Test**: Can be fully tested by asking NetClaw to troubleshoot a device, then immediately querying what facts were recorded about that device.

**Acceptance Scenarios**:

1. **Given** a troubleshooting session is active, **When** the agent discovers a device state (e.g., "PE2 BGP state is established"), **Then** this fact is automatically recorded to Memory MCP with the entity name, key, value, and timestamp.

2. **Given** a fact already exists for an entity/key pair, **When** the agent discovers a new value for the same fact, **Then** the old fact is superseded (not deleted) and the new fact becomes current.

3. **Given** the Memory MCP is unavailable, **When** the agent attempts to record a fact, **Then** the operation fails gracefully without interrupting the user's workflow.

---

### User Story 2 - Query Recent Facts First (Priority: P1)

As a network engineer, I want NetClaw to check Memory MCP first when I ask about a device so that I get the most recent, specific information before falling back to consolidated knowledge.

**Why this priority**: The retrieval order is critical to providing accurate, up-to-date information. Recent facts in Memory MCP should take precedence over older consolidated knowledge.

**Independent Test**: Can be tested by recording a fact about a device, then asking NetClaw about that device and verifying it returns the Memory MCP fact rather than (or in addition to) MEMORY.md content.

**Acceptance Scenarios**:

1. **Given** a fact exists in Memory MCP for entity "PE2", **When** the user asks "What do you know about PE2?", **Then** the agent queries Memory MCP first and includes those facts in the response.

2. **Given** Memory MCP has no facts about "R1" but MEMORY.md contains historical knowledge, **When** the user asks about R1, **Then** the agent falls back to MEMORY.md and returns that information.

3. **Given** both Memory MCP and MEMORY.md have information about the same entity, **When** the user asks about it, **Then** Memory MCP facts are presented as "current state" and MEMORY.md as "historical context".

---

### User Story 3 - Semantic Session Recall (Priority: P2)

As a network engineer, I want to search for past troubleshooting sessions using natural language so that I can find relevant prior work even if I don't remember exact device names or dates.

**Why this priority**: Semantic search enables finding relevant past work without exact keyword matches, which is how engineers naturally think about problems ("that BGP issue we had last month").

**Independent Test**: Can be tested by storing several session summaries, then querying with natural language that doesn't exactly match any summary text.

**Acceptance Scenarios**:

1. **Given** multiple session summaries are stored in Memory MCP, **When** the user asks "What do you remember about BGP troubleshooting?", **Then** the agent performs semantic search and returns the most relevant sessions.

2. **Given** a query has low semantic similarity to any stored sessions, **When** the search returns few/no results, **Then** the agent falls back to searching MEMORY.md for related keywords.

3. **Given** semantic search is unavailable (embeddings not loaded), **When** the user requests session recall, **Then** the agent informs them and offers keyword-based search as an alternative.

---

### User Story 4 - Record Decisions with Rationale (Priority: P2)

As a network engineer, I want NetClaw to record operational decisions with full context so that future sessions (and auditors) can understand why changes were made.

**Why this priority**: Decision audit trails are essential for compliance and institutional knowledge. They answer "why was this changed?" months later.

**Independent Test**: Can be tested by making a configuration decision, then querying decisions for that entity and verifying context/rationale are preserved.

**Acceptance Scenarios**:

1. **Given** the agent recommends or executes a configuration change, **When** the change is approved, **Then** the decision is recorded with context, rationale, affected entities, and optional change request number.

2. **Given** a decision was recorded for entity "PE2", **When** the user asks "Why was PE2's hold timer changed?", **Then** the agent queries Memory MCP decisions and returns the full context.

3. **Given** multiple decisions affect the same entity, **When** querying decisions, **Then** they are returned in chronological order with clear timestamps.

---

### User Story 5 - Consolidate Patterns to Long-Term Memory (Priority: P3)

As a network engineer, I want NetClaw to periodically consolidate important patterns from Memory MCP into MEMORY.md so that critical institutional knowledge is preserved in human-readable format.

**Why this priority**: While Memory MCP stores structured data, MEMORY.md provides narrative context that's easier for humans to read and survives even if the database is reset.

**Independent Test**: Can be tested by recording repeated similar facts/decisions, then triggering consolidation and verifying a pattern entry appears in MEMORY.md.

**Acceptance Scenarios**:

1. **Given** the same type of issue has been recorded 3+ times for similar entities, **When** consolidation runs, **Then** a pattern entry is written to MEMORY.md summarizing the recurring issue.

2. **Given** a significant decision was made with high impact, **When** consolidation runs, **Then** the decision is summarized in MEMORY.md with a reference to query Memory MCP for full details.

3. **Given** MEMORY.md already contains an entry about a topic, **When** new related information should be consolidated, **Then** the existing entry is updated rather than duplicated.

---

### User Story 6 - Track Entity Relationships (Priority: P3)

As a network engineer, I want NetClaw to track relationships between network entities so that impact analysis and topology understanding are available across sessions.

**Why this priority**: Understanding "what depends on what" is critical for impact analysis but often lost between sessions.

**Independent Test**: Can be tested by recording several entity links, then querying the graph for a device and verifying relationships are returned.

**Acceptance Scenarios**:

1. **Given** the agent learns that PE2 peers with RR1, **When** this relationship is recorded, **Then** it can be queried from either entity's perspective.

2. **Given** a service depends on multiple devices, **When** the user asks about impact of taking down one device, **Then** the agent queries the entity graph to identify affected services.

3. **Given** a relationship already exists, **When** the same relationship is recorded again, **Then** no duplicate is created.

---

### Edge Cases

- What happens when Memory MCP database is corrupted or missing? System should fall back to MEMORY.md only with a warning.
- How does system handle conflicting information between Memory MCP and MEMORY.md? Memory MCP is treated as "current truth" while MEMORY.md is "historical context".
- What happens when MEMORY.md file doesn't exist? System should create it on first consolidation.
- How are facts invalidated when a device is decommissioned? Explicit invalidation with reason, facts remain in timeline for history.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Agent MUST query Memory MCP for entity facts before consulting MEMORY.md when answering questions about specific entities.
- **FR-002**: Agent MUST record discovered facts to Memory MCP during active troubleshooting sessions.
- **FR-003**: Agent MUST use semantic search via Memory MCP's `memory_recall` tool when users ask about past sessions or troubleshooting history.
- **FR-004**: Agent MUST fall back to MEMORY.md when Memory MCP returns no results or is unavailable.
- **FR-005**: Agent MUST record operational decisions with context, rationale, and affected entities.
- **FR-006**: Agent MUST track entity relationships (peering, dependencies, connectivity) in Memory MCP's graph.
- **FR-007**: Agent MUST consolidate repeated patterns and significant decisions to MEMORY.md at the end of each session.
- **FR-008**: SOUL.md MUST contain clear instructions defining when to use Memory MCP vs MEMORY.md.
- **FR-009**: System MUST present Memory MCP data as "current state" and MEMORY.md as "consolidated knowledge" when both contain relevant information.
- **FR-010**: System MUST gracefully degrade to MEMORY.md-only operation if Memory MCP is unavailable.
- **FR-011**: Agent MUST log all memory operations (fact recording, decision logging, consolidation, failures) to GAIT audit trail.
- **FR-012**: Agent MUST NOT record credentials, secrets, passwords, API keys, or tokens to Memory MCP or MEMORY.md.

### Key Entities

- **Memory MCP**: Structured storage system providing fast access to facts, decisions, entity graphs, and semantic session search
- **MEMORY.md**: Markdown file containing consolidated long-term knowledge distilled from patterns and significant events
- **Fact**: A key-value observation about a network entity with temporal validity (valid_from, valid_to)
- **Decision**: An operational choice with context, rationale, affected entities, and optional change request reference
- **Entity Link**: A relationship between two entities (subject, predicate, object) such as "peers_with" or "depends_on"
- **Session Summary**: A natural language description of a troubleshooting session stored for semantic retrieval

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When asked about a specific device, agent returns Memory MCP facts within 2 seconds in 95% of queries.
- **SC-002**: Users can find relevant past sessions via natural language search with at least 80% relevance accuracy.
- **SC-003**: All operational decisions are recorded with context, achieving 100% audit trail completeness.
- **SC-004**: Repeated patterns (3+ occurrences) are automatically consolidated to MEMORY.md at session end.
- **SC-005**: Entity relationship queries return accurate results, enabling impact analysis for at least 90% of topology questions.
- **SC-006**: System continues to function (with reduced capability) when Memory MCP is unavailable, achieving 99.9% availability for basic memory operations.
- **SC-007**: SOUL.md instructions are unambiguous, verified by testing that the agent correctly chooses Memory MCP vs MEMORY.md in 10 representative scenarios.

## Clarifications

### Session 2026-06-20

- Q: When should consolidation from Memory MCP to MEMORY.md occur? → A: At the end of each session (natural checkpoint)
- Q: How should users/operators be informed about memory operations? → A: Log to GAIT audit trail only (standard NetClaw pattern)
- Q: Should the agent avoid recording certain types of sensitive information? → A: Exclude credentials/secrets only (passwords, keys, tokens)

## Assumptions

- Memory MCP Server (Feature 033) is installed and configured in the OpenClaw deployment
- MEMORY.md file exists at the standard workspace location (`~/.openclaw/workspace/MEMORY.md`)
- The agent has access to both Memory MCP tools and file read/write capabilities
- Consolidation to MEMORY.md can be triggered manually or at session end (not real-time)
- The existing SOUL.md structure supports adding new memory-related instructions
- Network engineers are the primary users and understand basic memory concepts (facts, decisions, relationships)
