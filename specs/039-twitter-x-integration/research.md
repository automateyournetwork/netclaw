# Research: Twitter/X Integration (Free Tier)

**Feature**: 039-twitter-x-integration
**Date**: 2026-06-24
**Status**: Complete

---

## Research Questions

### RQ1: Twitter API v2 Client Library Selection

**Question**: Which Python library should we use for Twitter API v2 integration?

**Decision**: **tweepy 4.x**

**Rationale**:
- Most mature and widely-used Twitter API library for Python
- Full support for Twitter API v2 with backwards compatibility for v1.1
- Well-documented with active maintenance
- Handles OAuth authentication complexity internally
- Built-in rate limit handling with wait_on_rate_limit option

**Alternatives Considered**:
| Library | Pros | Cons | Why Rejected |
|---------|------|------|--------------|
| python-twitter-v2 | Lightweight | Less mature, fewer features | Limited documentation |
| TwitterAPI | Supports both v1.1 and v2 | More complex API | Extra complexity not needed |
| requests (direct) | Full control | Manual OAuth, rate limiting | Too much boilerplate |

**Code Pattern**:
```python
import tweepy

# OAuth 1.0a User Context (required for posting)
client = tweepy.Client(
    consumer_key=os.environ["TWITTER_API_KEY"],
    consumer_secret=os.environ["TWITTER_API_SECRET"],
    access_token=os.environ["TWITTER_ACCESS_TOKEN"],
    access_token_secret=os.environ["TWITTER_ACCESS_SECRET"],
    wait_on_rate_limit=True
)

# Post a tweet
response = client.create_tweet(text="Hello from NetClaw! #netclaw")
tweet_id = response.data["id"]
```

---

### RQ2: Twitter Free Tier Capabilities and Limitations

**Question**: What can we do on Twitter's Free tier?

**Decision**: **One-way broadcast only (post tweets)**

**Findings**:

| Capability | Free Tier | Basic Tier ($100/mo) |
|------------|-----------|----------------------|
| Post tweets | Yes (50/24hr) | Yes (100/24hr) |
| Post threads | Yes | Yes |
| Upload media | Yes | Yes |
| Delete tweets | Yes | Yes |
| Read mentions | No | Yes |
| Read timeline | No | Yes |
| Search tweets | No | Yes |
| Reply to tweets | No | Yes |
| Get rate limits | Yes | Yes |

**Rate Limits (Free Tier)**:
- `POST /2/tweets`: 50 requests per 24 hours (per user)
- `DELETE /2/tweets/:id`: 50 requests per 24 hours
- `POST /2/tweets/:id/hidden`: 50 requests per 24 hours

**Implications for Design**:
1. Heartbeat tweets at 4-hour intervals = 6 tweets/day ≈ 12% of quota
2. Manual tweets have ample headroom
3. No need for complex read/reply logic on Free tier
4. Thread posting counts each tweet against quota

---

### RQ3: Authentication Method

**Question**: Which OAuth flow should we use?

**Decision**: **OAuth 1.0a User Context**

**Rationale**:
- Required for posting tweets on behalf of a user
- Uses 4 credentials: API Key, API Secret, Access Token, Access Token Secret
- Access tokens are long-lived (no refresh flow needed)
- Supports all write operations

**Alternative: OAuth 2.0 Bearer Token**:
- Only for read-only operations (timeline, search)
- Cannot post tweets
- Not suitable for our use case

**Environment Variables**:
```bash
TWITTER_API_KEY=<from Twitter Developer Portal>
TWITTER_API_SECRET=<from Twitter Developer Portal>
TWITTER_ACCESS_TOKEN=<from Twitter Developer Portal>
TWITTER_ACCESS_SECRET=<from Twitter Developer Portal>
```

---

### RQ4: Thread Splitting Strategy

**Question**: How should we split content exceeding 280 characters?

**Decision**: **Sentence-boundary splitting with word fallback**

**Algorithm**:
```
1. If content ≤ 280 chars → single tweet
2. Split content at sentence boundaries (., !, ?)
3. Greedily combine sentences until approaching 270 chars (leave room for thread numbering)
4. If a single sentence > 270 chars, split at word boundary
5. Add thread numbering: "[1/N]" suffix
6. Post tweets in sequence, each replying to previous
```

**Example**:
```
Input (350 chars):
"BGP path selection is a 11-step process defined in RFC 4271. The first step is weight (Cisco proprietary). Then local preference. Then locally originated routes. Then AS path length. Most networks only see the first 4 steps in action. #netclaw"

Output (2 tweets):
[1/2] "BGP path selection is a 11-step process defined in RFC 4271. The first step is weight (Cisco proprietary). Then local preference. Then locally originated routes. #netclaw"
[2/2] "Then AS path length. Most networks only see the first 4 steps in action. #netclaw"
```

**Implementation Notes**:
- Reserve ~10 chars for numbering `[NN/NN] `
- Always include #netclaw in last tweet of thread
- Track thread root tweet_id for reply chain

---

### RQ5: Content Guardrails Implementation

**Question**: How should we detect and block sensitive content?

**Decision**: **Regex-based pattern matching with configurable blocklist**

**Patterns**:
```python
GUARDRAIL_PATTERNS = {
    "ipv4": {
        "pattern": r"\b(?!192\.0\.2\.|198\.51\.100\.|203\.0\.113\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
        "description": "IPv4 addresses (except RFC 5737 documentation IPs)",
        "action": "sanitize",  # Replace with 192.0.2.x
    },
    "ipv6": {
        "pattern": r"\b(?:[A-Fa-f0-9]{1,4}:){7}[A-Fa-f0-9]{1,4}\b",
        "description": "IPv6 addresses",
        "action": "sanitize",  # Replace with 2001:db8::x
    },
    "mac": {
        "pattern": r"\b([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
        "description": "MAC addresses",
        "action": "block",
    },
    "credential": {
        "pattern": r"\b(password|secret|key|token|credential)s?\s*[=:]\s*\S+",
        "description": "Credential patterns",
        "action": "block",
    },
    "internal_naming": {
        "pattern": r"\b(corp|internal|private|customer|prod)-[\w-]+\b",
        "description": "Internal naming conventions",
        "action": "block",
    },
}
```

**Sanitization Strategy**:
- Real IPv4 → `192.0.2.x` (RFC 5737 documentation range)
- Real IPv6 → `2001:db8::x` (RFC 3849 documentation range)
- Hostnames → `router-01`, `switch-01`, etc.
- Customer names → `[redacted]` or omit entirely

**Validation Flow**:
```
Content → Pattern scan → Actions:
  - "pass": Content is safe
  - "sanitize": Replace matched text with safe alternative
  - "block": Reject entirely, request regeneration
```

---

### RQ6: Tweet History Storage

**Question**: Where should we store tweet history for deduplication?

**Decision**: **Memory MCP with `twitter_history` namespace**

**Rationale**:
- Memory MCP already provides persistent storage
- 30-day retention aligns with spec requirements
- Semantic search can help detect near-duplicates
- Consistent with NetClaw's memory architecture

**Storage Schema**:
```json
{
  "namespace": "twitter_history",
  "entries": [
    {
      "tweet_id": "1234567890",
      "content": "BGP tip of the day: Always check your AS path...",
      "category": "tip",
      "timestamp": "2026-06-24T10:00:00Z",
      "thread_root": null,
      "media_ids": []
    }
  ]
}
```

**Deduplication Logic**:
1. Exact match: Compare content hash
2. Semantic similarity: Use Memory MCP's embedding search (threshold: 0.85)
3. Category rotation: Don't repeat same category in consecutive tweets

---

### RQ7: HUD Integration Pattern

**Question**: How should the Twitter panel integrate with Visual HUD?

**Decision**: **WebSocket-based real-time updates**

**Findings from existing HUD**:
- HUD uses React components in `ui/netclaw-visual/src/components/`
- Real-time updates via WebSocket connection to gateway
- Panels follow consistent styling pattern

**TwitterPanel.jsx Structure**:
```jsx
// Key features:
// - Display last 10 outbound tweets
// - Show timestamp, content preview, link to tweet
// - Real-time update when new tweet posted
// - Status indicator (connected/disconnected)
// - Rate limit display (X/50 remaining)
```

**Data Flow**:
```
twitter-mcp posts tweet
    │
    ▼
Emit event via gateway WebSocket
    │
    ▼
TwitterPanel receives event
    │
    ▼
Update UI with new tweet
```

---

## Summary of Decisions

| Question | Decision |
|----------|----------|
| API Client | tweepy 4.x |
| Auth Method | OAuth 1.0a User Context |
| Thread Strategy | Sentence-boundary splitting |
| Guardrails | Regex patterns with sanitize/block actions |
| History Storage | Memory MCP (`twitter_history` namespace) |
| HUD Integration | WebSocket real-time updates |

---

## References

- [Twitter API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [tweepy Documentation](https://docs.tweepy.org/en/stable/)
- [RFC 5737 - IPv4 Address Blocks Reserved for Documentation](https://datatracker.ietf.org/doc/html/rfc5737)
- [RFC 3849 - IPv6 Address Prefix Reserved for Documentation](https://datatracker.ietf.org/doc/html/rfc3849)
- [Twitter Rate Limits](https://developer.twitter.com/en/docs/twitter-api/rate-limits)
