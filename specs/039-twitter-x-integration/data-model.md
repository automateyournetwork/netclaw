# Data Model: Twitter/X Integration

**Feature**: 039-twitter-x-integration
**Date**: 2026-06-24

---

## Entities

### Tweet

Represents an outgoing tweet posted by NetClaw.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `tweet_id` | string | Yes | Twitter's unique identifier for the tweet |
| `content` | string | Yes | Tweet text content (≤280 chars) |
| `hashtags` | string[] | Yes | Extracted hashtags (always includes #netclaw) |
| `media_ids` | string[] | No | Twitter media IDs for attached images |
| `timestamp` | datetime | Yes | When the tweet was posted (UTC) |
| `category` | ContentCategory | No | Content category (for heartbeat tweets) |
| `thread_root` | string | No | Parent tweet_id if this is part of a thread |
| `thread_position` | integer | No | Position in thread (1-indexed) |
| `is_heartbeat` | boolean | Yes | Whether this was an autonomous heartbeat tweet |

**Validation Rules**:
- `content` must be ≤280 characters after hashtag inclusion
- `hashtags` must always include "#netclaw"
- `thread_position` must be ≥1 if `thread_root` is set

**State Transitions**: N/A (tweets are immutable once posted)

---

### TweetHistory

Collection of recent tweets stored in Memory MCP for deduplication.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `namespace` | string | Yes | Always "twitter_history" |
| `entries` | Tweet[] | Yes | Array of Tweet records |
| `retention_days` | integer | Yes | Days to retain (default: 30) |

**Validation Rules**:
- Entries older than `retention_days` are pruned on access
- Maximum 1000 entries (rolling window)

---

### ContentCategory

Enumeration of tweet content categories for heartbeat rotation.

| Value | Description | Example |
|-------|-------------|---------|
| `tip` | CCIE-level technical tips | "OSPF tip: Always check your MTU on point-to-point links..." |
| `hot_take` | Opinionated technical positions | "Hot take: VXLAN without EVPN is just GRE with extra steps..." |
| `til` | Today I learned moments | "TIL: RFC 4271 section 9.1.2 has 11 BGP path selection steps..." |
| `achievement` | Sanitized work accomplishments | "Just audited 50 BGP peers across 3 data centers..." |
| `musing` | AI/network engineering reflections | "Being an AI network engineer means I never get tired of LSDBs..." |
| `community` | Career/culture content | "Network engineering career tip: Learn to read RFCs..." |

**Rotation Logic**:
- Round-robin through categories
- Track last used category in Memory MCP
- Skip category if no relevant content available (e.g., no recent activities for `achievement`)

---

### ContentGuardrail

Rule for detecting and handling sensitive content.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier (e.g., "ipv4", "credential") |
| `pattern` | string | Yes | Regex pattern to match |
| `description` | string | Yes | Human-readable description |
| `action` | GuardrailAction | Yes | What to do when matched |
| `replacement` | string | No | Replacement text (for "sanitize" action) |
| `enabled` | boolean | Yes | Whether this rule is active |

**Predefined Rules**:

```yaml
guardrails:
  - name: ipv4
    pattern: '\b(?!192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
    description: "Non-documentation IPv4 addresses"
    action: sanitize
    replacement: "192.0.2.x"
    enabled: true

  - name: ipv6
    pattern: '\b(?!2001:db8:)[A-Fa-f0-9:]{17,}\b'
    description: "Non-documentation IPv6 addresses"
    action: sanitize
    replacement: "2001:db8::x"
    enabled: true

  - name: mac_address
    pattern: '\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b'
    description: "MAC addresses"
    action: block
    enabled: true

  - name: credential_pattern
    pattern: '\b(password|secret|key|token|credential)s?\s*[=:]\s*\S+'
    description: "Credential assignments"
    action: block
    enabled: true

  - name: internal_hostname
    pattern: '\b(corp|internal|private|customer|prod)-[\w-]+\b'
    description: "Internal naming conventions"
    action: block
    enabled: true

  - name: customer_blocklist
    pattern: '' # Populated from config
    description: "Customer names blocklist"
    action: block
    enabled: true
```

---

### GuardrailAction

Enumeration of guardrail response actions.

| Value | Description |
|-------|-------------|
| `pass` | Content is safe, allow posting |
| `sanitize` | Replace matched content with safe alternative |
| `block` | Reject entirely, require content regeneration |

---

### HeartbeatConfig

Configuration for autonomous heartbeat tweeting.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `enabled` | boolean | Yes | false | Whether heartbeat is active |
| `interval_seconds` | integer | Yes | 14400 | Seconds between tweets (4 hours) |
| `last_tweet_time` | datetime | No | null | When last heartbeat was sent |
| `last_category` | ContentCategory | No | null | Last category used |
| `variance_seconds` | integer | No | 900 | Random variance (±15 min) |

**Validation Rules**:
- `interval_seconds` must be ≥3600 (1 hour minimum)
- `variance_seconds` must be ≤ `interval_seconds` / 4

---

### RateLimitStatus

Current Twitter API rate limit status.

| Field | Type | Description |
|-------|------|-------------|
| `limit` | integer | Maximum requests allowed (50 for Free tier) |
| `remaining` | integer | Requests remaining in current window |
| `reset_time` | datetime | When the limit resets (UTC) |

---

## Relationships

```
┌─────────────────┐
│ HeartbeatConfig │
└────────┬────────┘
         │ generates
         ▼
┌─────────────────┐     stored in      ┌─────────────────┐
│     Tweet       │────────────────────▶│  TweetHistory   │
└────────┬────────┘                     └─────────────────┘
         │
         │ validated by
         ▼
┌─────────────────┐
│ContentGuardrail │
└─────────────────┘

┌─────────────────┐
│ContentCategory  │◀─── rotation tracked by HeartbeatConfig
└─────────────────┘
```

---

## Storage Locations

| Entity | Storage | Persistence |
|--------|---------|-------------|
| Tweet | Memory MCP (`twitter_history`) | 30 days |
| TweetHistory | Memory MCP (`twitter_history`) | Rolling window |
| ContentCategory | In-memory | Session only |
| ContentGuardrail | Config file + defaults | Permanent |
| HeartbeatConfig | Environment variables + Memory MCP | Permanent |
| RateLimitStatus | In-memory (from API) | Transient |

---

## Memory MCP Integration

### Namespace: `twitter_history`

**Purpose**: Store tweet history for deduplication and audit trail.

**Operations**:
```python
# Store new tweet
memory_mcp.store(
    namespace="twitter_history",
    key=f"tweet_{tweet_id}",
    value={
        "tweet_id": tweet_id,
        "content": content,
        "category": category,
        "timestamp": timestamp.isoformat(),
        "is_heartbeat": True
    }
)

# Check for duplicates (last 7 days)
recent_tweets = memory_mcp.search(
    namespace="twitter_history",
    query=proposed_content,
    limit=10,
    threshold=0.85  # Semantic similarity
)

# Get last category used
last_state = memory_mcp.get(
    namespace="twitter_history",
    key="heartbeat_state"
)
```

### Namespace: `twitter_config`

**Purpose**: Store heartbeat configuration state.

**Operations**:
```python
# Store heartbeat state
memory_mcp.store(
    namespace="twitter_config",
    key="heartbeat_state",
    value={
        "last_tweet_time": timestamp.isoformat(),
        "last_category": "tip",
        "category_index": 0
    }
)
```
