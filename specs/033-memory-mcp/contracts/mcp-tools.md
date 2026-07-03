# MCP Tool Contracts: Hybrid Memory MCP Server

**Feature**: 033-memory-mcp
**Date**: 2026-06-20

## Overview

This document defines the interface contracts for the 10 MCP tools exposed by the Memory MCP server. All tools follow FastMCP conventions with JSON responses.

## Common Patterns

### Response Format

All tools return structured JSON responses:

```json
{
  "success": true,
  "data": { ... },
  "error": null
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  }
}
```

### Entity Normalization

- Entity names are normalized to lowercase for matching
- Original casing preserved in metadata where applicable
- Maximum entity name length: 255 characters

---

## Tool Definitions

### 1. memory_record_fact

Record a fact about a network entity with temporal validity.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity | string | Yes | Network entity name (device, interface, service) |
| key | string | Yes | Fact type/attribute name |
| value | string | Yes | Fact value |
| metadata | object | No | Additional context as key-value pairs |

**Returns**:

```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4e5f6",
    "entity": "pe2",
    "key": "bgp_state",
    "value": "established",
    "metadata": {"peer": "10.0.0.1"},
    "valid_from": "2026-06-20T14:30:00Z",
    "valid_to": null,
    "superseded_id": "prev123456"
  }
}
```

**Behavior**:
- If a current fact exists with same entity+key, it is automatically superseded (valid_to set to now)
- Returns `superseded_id` if a previous fact was invalidated
- Logs to GAIT: `memory_record_fact: {entity}/{key}`

**Error Codes**:
- `INVALID_ENTITY`: Entity name empty or exceeds 255 chars
- `INVALID_KEY`: Key empty or exceeds 255 chars
- `INVALID_VALUE`: Value empty or exceeds 10000 chars
- `INVALID_METADATA`: Metadata is not valid JSON

---

### 2. memory_get_facts

Query current (non-invalidated) facts for an entity.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity | string | Yes | Entity name to query |
| key | string | No | Specific key to filter by |

**Returns**:

```json
{
  "success": true,
  "data": {
    "entity": "pe2",
    "facts": [
      {
        "id": "a1b2c3d4e5f6",
        "key": "bgp_state",
        "value": "established",
        "metadata": {"peer": "10.0.0.1"},
        "valid_from": "2026-06-20T14:30:00Z"
      },
      {
        "id": "b2c3d4e5f6a1",
        "key": "location",
        "value": "DC-East Rack 14",
        "metadata": null,
        "valid_from": "2026-06-01T09:00:00Z"
      }
    ],
    "count": 2
  }
}
```

**Behavior**:
- Returns only current facts (valid_to IS NULL)
- Results ordered by created_at descending (most recent first)
- Empty array returned if no facts exist (not an error)
- Case-insensitive entity matching

**Error Codes**:
- `INVALID_ENTITY`: Entity name empty

---

### 3. memory_invalidate

Explicitly invalidate a fact with a reason.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| fact_id | string | Yes | ID of the fact to invalidate |
| reason | string | Yes | Why the fact is being invalidated |

**Returns**:

```json
{
  "success": true,
  "data": {
    "id": "a1b2c3d4e5f6",
    "entity": "pe2",
    "key": "bgp_state",
    "valid_to": "2026-06-20T15:00:00Z",
    "invalidation_reason": "BGP session torn down for maintenance"
  }
}
```

**Behavior**:
- Sets valid_to to current timestamp
- Stores reason in metadata
- Fact no longer appears in memory_get_facts but remains in timeline
- Logs to GAIT: `memory_invalidate: {fact_id}`

**Error Codes**:
- `FACT_NOT_FOUND`: No fact with given ID exists
- `ALREADY_INVALIDATED`: Fact already has valid_to set
- `INVALID_REASON`: Reason is empty

---

### 4. memory_timeline

Query historical facts including invalidated ones within a time range.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity | string | Yes | Entity name to query |
| after | string | No | ISO timestamp - only facts valid after this time |
| before | string | No | ISO timestamp - only facts valid before this time |
| key | string | No | Filter by specific key |

**Returns**:

```json
{
  "success": true,
  "data": {
    "entity": "pe2",
    "timeline": [
      {
        "id": "old123456",
        "key": "bgp_state",
        "value": "down",
        "valid_from": "2026-06-20T14:00:00Z",
        "valid_to": "2026-06-20T14:30:00Z",
        "superseded_by": "a1b2c3d4e5f6"
      },
      {
        "id": "a1b2c3d4e5f6",
        "key": "bgp_state",
        "value": "established",
        "valid_from": "2026-06-20T14:30:00Z",
        "valid_to": null,
        "superseded_by": null
      }
    ],
    "count": 2
  }
}
```

**Behavior**:
- Returns all facts (current and invalidated) ordered chronologically
- Time range is inclusive
- If no time range specified, returns last 30 days by default

**Error Codes**:
- `INVALID_ENTITY`: Entity name empty
- `INVALID_TIMESTAMP`: After/before not valid ISO format
- `INVALID_RANGE`: After is greater than before

---

### 5. memory_store_session

Store a session summary for semantic retrieval.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| summary | string | Yes | Session summary text (max 10000 chars) |
| entities | array | No | List of entity names mentioned |
| topics | array | No | List of topic tags |
| session_id | string | No | GAIT session reference |

**Returns**:

```json
{
  "success": true,
  "data": {
    "id": "sess_abc123",
    "summary_preview": "Troubleshot BGP flapping between PE2 and RR1...",
    "entities": ["pe2", "rr1"],
    "topics": ["bgp", "troubleshooting", "mtu"],
    "embedding_dimensions": 384,
    "created_at": "2026-06-20T16:00:00Z"
  }
}
```

**Behavior**:
- Generates embedding using all-MiniLM-L6-v2 model
- Stores in ChromaDB with metadata for filtering
- Logs to GAIT: `memory_store_session: {session_id or id}`

**Error Codes**:
- `INVALID_SUMMARY`: Summary empty or exceeds 10000 chars
- `EMBEDDING_FAILED`: Model failed to generate embedding (graceful degradation: stores without embedding)

---

### 6. memory_recall

Semantic search across stored sessions.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | string | Yes | Natural language query |
| top_k | integer | No | Number of results (default: 5, max: 20) |
| min_score | float | No | Minimum similarity threshold (default: 0.5) |
| after | string | No | Only sessions after this ISO timestamp |
| topics | array | No | Filter by topic tags |

**Returns**:

```json
{
  "success": true,
  "data": {
    "query": "BGP flapping problem",
    "results": [
      {
        "id": "sess_abc123",
        "summary": "Troubleshot BGP flapping between PE2 and RR1. Root cause was MTU mismatch...",
        "score": 0.87,
        "entities": ["pe2", "rr1"],
        "topics": ["bgp", "troubleshooting"],
        "created_at": "2026-06-15T10:30:00Z"
      }
    ],
    "count": 1
  }
}
```

**Behavior**:
- Embeds query and performs cosine similarity search
- Results ordered by similarity score descending
- Filters applied before similarity ranking

**Error Codes**:
- `INVALID_QUERY`: Query empty
- `SEMANTIC_UNAVAILABLE`: ChromaDB not available (returns empty results, not error)

---

### 7. memory_record_decision

Record an operational decision with context and rationale.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| context | string | Yes | What was happening when decision was made |
| decision | string | Yes | What was decided |
| rationale | string | Yes | Why this decision was made |
| entities | array | Yes | Related entity names (at least one) |
| cr_number | string | No | ServiceNow Change Request (CHG0001234) |
| gait_ref | string | No | GAIT commit reference |

**Returns**:

```json
{
  "success": true,
  "data": {
    "id": "dec_xyz789",
    "context": "PE2 BGP session to RR1 flapping every 30 seconds",
    "decision": "Reduced BGP hold timer from 180s to 90s",
    "rationale": "Faster convergence needed for this critical path",
    "entities": ["pe2", "rr1"],
    "cr_number": "CHG0001234",
    "created_at": "2026-06-20T17:00:00Z"
  }
}
```

**Behavior**:
- Validates CR number format if provided (CHG followed by digits)
- Logs to GAIT: `memory_record_decision: {id}`

**Error Codes**:
- `INVALID_CONTEXT`: Context empty or exceeds 5000 chars
- `INVALID_DECISION`: Decision empty or exceeds 2000 chars
- `INVALID_RATIONALE`: Rationale empty or exceeds 5000 chars
- `INVALID_ENTITIES`: Entities array empty
- `INVALID_CR_NUMBER`: CR number doesn't match pattern CHG[0-9]+

---

### 8. memory_get_decisions

Query past decisions by entity or time range.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity | string | No | Filter by entity (at least one of entity/after required) |
| after | string | No | Decisions after this ISO timestamp |
| before | string | No | Decisions before this ISO timestamp |
| limit | integer | No | Max results (default: 50, max: 200) |

**Returns**:

```json
{
  "success": true,
  "data": {
    "decisions": [
      {
        "id": "dec_xyz789",
        "context": "PE2 BGP session to RR1 flapping...",
        "decision": "Reduced BGP hold timer...",
        "rationale": "Faster convergence needed...",
        "entities": ["pe2", "rr1"],
        "cr_number": "CHG0001234",
        "created_at": "2026-06-20T17:00:00Z"
      }
    ],
    "count": 1
  }
}
```

**Behavior**:
- Returns decisions ordered by created_at descending
- If entity specified, returns decisions involving that entity
- Entity matching is case-insensitive

**Error Codes**:
- `INVALID_QUERY`: Neither entity nor after specified
- `INVALID_TIMESTAMP`: After/before not valid ISO format

---

### 9. memory_link_entities

Create a relationship between two entities.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| subject | string | Yes | Source entity |
| predicate | string | Yes | Relationship type |
| object | string | Yes | Target entity |
| metadata | object | No | Additional context |

**Returns**:

```json
{
  "success": true,
  "data": {
    "id": "link_abc123",
    "subject": "pe2",
    "predicate": "peers_with",
    "object": "rr1",
    "metadata": {"protocol": "bgp", "asn": "65000"},
    "created_at": "2026-06-20T18:00:00Z"
  }
}
```

**Standard Predicates**:
- `peers_with` — BGP/OSPF peering relationship
- `depends_on` — Service dependency
- `connects_to` — Physical/logical connectivity
- `managed_by` — Management relationship
- `caused` — Incident causality
- `fixed_by` — Resolution relationship
- `learned_from` — Knowledge provenance

**Behavior**:
- Entities normalized to lowercase
- Duplicate links (same subject+predicate+object) return existing link
- Logs to GAIT: `memory_link_entities: {subject} {predicate} {object}`

**Error Codes**:
- `INVALID_SUBJECT`: Subject empty or exceeds 255 chars
- `INVALID_PREDICATE`: Predicate empty, exceeds 100 chars, or invalid format
- `INVALID_OBJECT`: Object empty or exceeds 255 chars
- `SELF_LINK`: Subject and object are the same

---

### 10. memory_query_graph

Query entity relationships with optional depth traversal.

**Parameters**:

| Name | Type | Required | Description |
|------|------|----------|-------------|
| entity | string | Yes | Entity to query relationships for |
| direction | string | No | "outgoing", "incoming", or "both" (default: "both") |
| predicate | string | No | Filter by relationship type |
| depth | integer | No | Traversal depth (default: 1, max: 3) |

**Returns**:

```json
{
  "success": true,
  "data": {
    "entity": "pe2",
    "relationships": {
      "outgoing": [
        {
          "predicate": "peers_with",
          "target": "rr1",
          "metadata": {"protocol": "bgp"}
        },
        {
          "predicate": "connects_to",
          "target": "sw1",
          "metadata": null
        }
      ],
      "incoming": [
        {
          "predicate": "managed_by",
          "source": "nms1",
          "metadata": null
        }
      ]
    },
    "neighbors_at_depth_2": ["rr2", "pe1", "pe3"]
  }
}
```

**Behavior**:
- Direction "both" returns incoming and outgoing relationships
- Depth > 1 performs recursive traversal (returns unique entities at each depth)
- Entity matching is case-insensitive

**Error Codes**:
- `INVALID_ENTITY`: Entity empty
- `INVALID_DIRECTION`: Direction not one of outgoing/incoming/both
- `INVALID_DEPTH`: Depth < 1 or > 3

---

## GAIT Integration

All write operations log to GAIT with the pattern:

```
memory_{operation}: {identifier}
```

Examples:
- `memory_record_fact: pe2/bgp_state`
- `memory_invalidate: a1b2c3d4e5f6`
- `memory_store_session: sess_abc123`
- `memory_record_decision: dec_xyz789`
- `memory_link_entities: pe2 peers_with rr1`

Read operations (memory_get_facts, memory_timeline, memory_recall, memory_get_decisions, memory_query_graph) do not log to GAIT.
