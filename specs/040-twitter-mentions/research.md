# Research: Twitter Bidirectional Interaction

**Feature**: 040-twitter-mentions
**Date**: 2026-06-24

## Research Tasks

### 1. Twitter API v2 Mentions Endpoint

**Decision**: Use `GET /2/users/:id/mentions` endpoint via tweepy

**Rationale**:
- Tweepy 4.x provides `client.get_users_mentions(id)` method
- Returns tweets that @mention the specified user
- Supports pagination via `pagination_token`
- Available on pay-as-you-go tier (confirmed working with feature 039)

**Alternatives Considered**:
- Filtered Stream API - Requires higher tier, overkill for single-user mentions
- Search API - More expensive, less efficient for mentions-only use case

**Implementation Notes**:
```python
# Get user ID for @John_Capobianco
user = client.get_user(username="John_Capobianco")
user_id = user.data.id

# Fetch recent mentions
mentions = client.get_users_mentions(
    id=user_id,
    max_results=10,
    tweet_fields=["created_at", "conversation_id", "in_reply_to_user_id", "author_id"],
    expansions=["author_id"],
    user_fields=["username"]
)
```

---

### 2. Reply Threading (in_reply_to_tweet_id)

**Decision**: Use `in_reply_to_tweet_id` parameter in `create_tweet()`

**Rationale**:
- Standard Twitter API v2 pattern for threaded replies
- Tweepy supports this natively
- Ensures reply appears in conversation thread

**Implementation Notes**:
```python
# Post reply to a specific tweet
response = client.create_tweet(
    text="Reply content here",
    in_reply_to_tweet_id=original_tweet_id
)
```

---

### 3. Conversation Context Retrieval

**Decision**: Use `GET /2/tweets/:id` with conversation lookup

**Rationale**:
- Can fetch parent tweets using `conversation_id`
- Allows building context for better replies
- Limited to 5 parent tweets per spec requirement

**Implementation Notes**:
```python
# Get conversation context
conversation = client.get_tweet(
    id=tweet_id,
    tweet_fields=["conversation_id", "in_reply_to_user_id"],
    expansions=["referenced_tweets.id"]
)
```

---

### 4. Duplicate Mention Prevention

**Decision**: Track processed mention IDs in Memory MCP with 24-hour TTL

**Rationale**:
- Persists across server restarts (unlike in-memory set)
- Memory MCP already integrated in feature 039
- 24-hour TTL sufficient since Twitter API returns recent mentions only

**Alternatives Considered**:
- In-memory set - Lost on restart, would reprocess mentions
- File-based tracking - More complex, less integrated

**Implementation Notes**:
```python
# Check if mention already processed
async def is_processed(mention_id: str) -> bool:
    result = await memory_mcp.recall(f"twitter_mention_{mention_id}")
    return result is not None

# Mark mention as processed
async def mark_processed(mention_id: str):
    await memory_mcp.remember(
        key=f"twitter_mention_{mention_id}",
        value={"processed_at": datetime.utcnow().isoformat()},
        ttl_days=1
    )
```

---

### 5. Spam/Bot Detection Heuristics

**Decision**: Basic heuristics based on account age, follower ratio, tweet patterns

**Rationale**:
- No external spam detection API needed
- Sufficient for filtering obvious bot accounts
- Human review for edge cases (per FR-011)

**Heuristics**:
1. Account created within last 7 days → flag
2. Following/followers ratio > 100:1 → flag
3. Username contains 8+ digits → flag
4. Tweet text is identical to recent spam patterns → flag

**Implementation Notes**:
```python
def is_likely_spam(author_data: dict, tweet_text: str) -> bool:
    # Check account age
    created_at = datetime.fromisoformat(author_data["created_at"])
    if (datetime.utcnow() - created_at).days < 7:
        return True

    # Check follower ratio
    following = author_data.get("public_metrics", {}).get("following_count", 0)
    followers = author_data.get("public_metrics", {}).get("followers_count", 1)
    if following > 0 and following / max(followers, 1) > 100:
        return True

    return False
```

---

### 6. Context-Aware Response Logic

**Decision**: Classify mentions into categories before processing

**Rationale**:
- Per clarification: respond to NetClaw-related and technical network topics only
- Skip off-topic mentions silently
- Uses keyword matching and topic classification

**Categories**:
1. **NetClaw Request** - Contains "netclaw", "automation", "diagram", "MCP"
2. **Technical Network** - Contains routing/switching/security keywords
3. **Friendly Engagement** - Greetings, thanks, follows (respond briefly)
4. **Off-Topic** - Everything else (skip silently)

**Implementation Notes**:
```python
NETCLAW_KEYWORDS = ["netclaw", "automation", "diagram", "mcp", "skill", "pyats"]
NETWORK_KEYWORDS = ["ospf", "bgp", "vlan", "routing", "switching", "firewall", "aci", "cisco", "juniper", "f5"]

def classify_mention(text: str) -> str:
    text_lower = text.lower()
    if any(kw in text_lower for kw in NETCLAW_KEYWORDS):
        return "netclaw_request"
    if any(kw in text_lower for kw in NETWORK_KEYWORDS):
        return "technical_network"
    if any(word in text_lower for word in ["thanks", "thank you", "hello", "hi", "hey"]):
        return "friendly"
    return "off_topic"
```

---

### 7. Rate Limit Handling

**Decision**: Implement exponential backoff with queue

**Rationale**:
- Twitter API returns 429 on rate limit
- Queue mentions for retry rather than dropping
- Alert after 3 consecutive failures

**Implementation Notes**:
```python
async def fetch_mentions_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.get_users_mentions(...)
        except tweepy.TooManyRequests as e:
            wait_time = 2 ** attempt * 60  # 1, 2, 4 minutes
            logger.warning(f"Rate limited, waiting {wait_time}s")
            await asyncio.sleep(wait_time)
    raise RateLimitExceeded("Failed after 3 retries")
```

---

## API Cost Estimates

| Operation | Endpoint | Cost (pay-as-you-go) |
|-----------|----------|---------------------|
| Get mentions | GET /2/users/:id/mentions | ~$0.01 per request |
| Get tweet | GET /2/tweets/:id | ~$0.01 per request |
| Post reply | POST /2/tweets | ~$0.01 per request |
| Get user | GET /2/users/by/username | ~$0.01 per request |

**Per-interaction estimate**: ~$0.03-0.05 (mention read + optional context + reply)

---

## Summary

All technical decisions are resolved. The implementation extends the existing twitter-mcp server with:
- New `mentions.py` module for polling and tracking
- New `replies.py` module for reply generation and posting
- Updates to `server.py` to register new MCP tools
- Integration with Memory MCP for deduplication and history
