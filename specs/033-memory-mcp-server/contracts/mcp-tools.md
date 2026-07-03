# MCP Tool Contracts: Memory MCP Server

## memory_record_fact

**Purpose**: Store a network fact with temporal validity and auto-supersession.

**Input**:
```json
{
  "entity": "PE2",
  "key": "bgp_peer_10.0.0.1_state",
  "value": "Established",
  "metadata": "{\"peer_as\": 65001, \"prefixes_received\": 42}",
  "source": "pyats_health_check"
}
```

**Output (success)**:
```json
{
  "stored": true,
  "id": "a1b2c3d4-...",
  "entity": "PE2",
  "key": "bgp_peer_10.0.0.1_state",
  "valid_from": "2026-05-12T14:30:00+00:00"
}
```

---

## memory_get_facts

**Purpose**: Retrieve current (non-invalidated) facts for an entity.

**Input**:
```json
{
  "entity": "PE2",
  "key": "bgp_peer_10.0.0.1_state"
}
```

**Output**:
```json
{
  "entity": "PE2",
  "count": 1,
  "facts": [
    {
      "id": "a1b2c3d4-...",
      "entity": "PE2",
      "key": "bgp_peer_10.0.0.1_state",
      "value": "Established",
      "metadata": "{\"peer_as\": 65001}",
      "valid_from": "2026-05-12T14:30:00+00:00",
      "valid_to": null,
      "source": "pyats_health_check"
    }
  ]
}
```

---

## memory_timeline

**Purpose**: Get full history of facts for an entity (including invalidated).

**Input**:
```json
{
  "entity": "PE2",
  "start": "2026-05-01T00:00:00Z",
  "end": "2026-05-12T23:59:59Z"
}
```

**Output**:
```json
{
  "entity": "PE2",
  "count": 3,
  "timeline": [
    {"id": "...", "key": "bgp_peer_state", "value": "Idle", "valid_from": "...", "valid_to": "..."},
    {"id": "...", "key": "bgp_peer_state", "value": "Active", "valid_from": "...", "valid_to": "..."},
    {"id": "...", "key": "bgp_peer_state", "value": "Established", "valid_from": "...", "valid_to": null}
  ]
}
```

---

## memory_invalidate

**Purpose**: Explicitly mark a fact as no longer valid.

**Input**:
```json
{
  "fact_id": "a1b2c3d4-...",
  "reason": "Interface restored after maintenance"
}
```

**Output (success)**:
```json
{"invalidated": true, "fact_id": "a1b2c3d4-..."}
```

**Output (not found)**:
```json
{"error": "NOT_FOUND", "message": "No current fact with id a1b2c3d4-..."}
```

---

## memory_record_decision

**Purpose**: Record an operational decision with context and rationale.

**Input**:
```json
{
  "context": "PE2 BGP peer 10.0.0.1 flapping every 2 minutes for 30 minutes",
  "decision": "Shut BGP peer to prevent route churn across the fabric",
  "rationale": "Repeated flaps causing 15 route withdrawals per cycle, impacting PE3 and PE4 convergence",
  "entities": "PE2,PE3,PE4",
  "cr_number": "CHG0045678"
}
```

**Output**:
```json
{
  "stored": true,
  "id": "e5f6g7h8-...",
  "timestamp": "2026-05-12T15:00:00+00:00"
}
```

---

## memory_get_decisions

**Purpose**: Query past decisions by entity, time range, or text.

**Input**:
```json
{
  "entity": "PE2",
  "after": "2026-05-01T00:00:00Z"
}
```

**Output**:
```json
{
  "count": 1,
  "decisions": [
    {
      "id": "e5f6g7h8-...",
      "timestamp": "2026-05-12T15:00:00+00:00",
      "context": "PE2 BGP peer flapping...",
      "decision": "Shut BGP peer...",
      "rationale": "Repeated flaps...",
      "entities": ["PE2", "PE3", "PE4"],
      "cr_number": "CHG0045678"
    }
  ]
}
```

---

## memory_store_session

**Purpose**: Embed and store a session summary for semantic retrieval.

**Input**:
```json
{
  "summary": "Troubleshot BGP flapping on PE2 peer 10.0.0.1. Root cause was MTU mismatch on transit link. Fixed by adjusting TCP MSS. Peer stable after change.",
  "entities": "PE2,RR1",
  "topics": "bgp,flapping,mtu,troubleshooting"
}
```

**Output (success)**:
```json
{
  "stored": true,
  "id": "i9j0k1l2-...",
  "timestamp": "2026-05-12T16:00:00+00:00"
}
```

**Output (semantic unavailable)**:
```json
{
  "error": "SEMANTIC_UNAVAILABLE",
  "message": "Semantic memory unavailable: ... Structured memory (facts/decisions) still works."
}
```

---

## memory_recall

**Purpose**: Semantic search across stored session summaries.

**Input**:
```json
{
  "query": "BGP flapping problem we fixed",
  "top_k": 3,
  "after": "2026-04-01T00:00:00Z"
}
```

**Output**:
```json
{
  "query": "BGP flapping problem we fixed",
  "count": 1,
  "results": [
    {
      "id": "i9j0k1l2-...",
      "summary": "Troubleshot BGP flapping on PE2 peer 10.0.0.1...",
      "similarity": 0.847,
      "timestamp": "2026-05-12T16:00:00+00:00",
      "entities": ["PE2", "RR1"],
      "topics": ["bgp", "flapping", "mtu", "troubleshooting"],
      "session_id": ""
    }
  ]
}
```
