# Data Model: Twitter Bidirectional Interaction

**Feature**: 040-twitter-mentions
**Date**: 2026-06-24

## Entities

### Mention

A tweet that @mentions the configured user account.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| tweet_id | string | Twitter's unique tweet identifier | Required, unique |
| author_id | string | Twitter user ID of mention author | Required |
| author_handle | string | @username of mention author | Required |
| text | string | Full text of the mention tweet | Required, max 280 chars |
| created_at | datetime | When the mention was posted | Required, UTC |
| conversation_id | string | ID of the conversation thread | Optional |
| in_reply_to_tweet_id | string | Parent tweet ID if this is a reply | Optional |
| category | enum | Classification result | netclaw_request, technical_network, friendly, off_topic, spam |
| processed | boolean | Whether mention has been handled | Default: false |
| processed_at | datetime | When mention was processed | Optional |

**State Transitions**:
```
[received] → [classified] → [processed | skipped]
                         → [flagged_spam]
```

---

### Reply

A response tweet posted to a mention.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| reply_id | string | Twitter's unique tweet identifier | Set after posting |
| in_reply_to_tweet_id | string | The mention being replied to | Required |
| text | string | Reply content | Required, max 280 chars per tweet |
| is_thread | boolean | Whether reply spans multiple tweets | Default: false |
| thread_ids | array[string] | Tweet IDs if thread | Optional |
| generated_at | datetime | When reply was generated | Required |
| approved | boolean | Human approval status | Required, default: false |
| approved_at | datetime | When human approved | Optional |
| posted_at | datetime | When posted to Twitter | Optional |
| status | enum | Current reply status | draft, pending_approval, approved, posted, rejected |

**State Transitions**:
```
[draft] → [pending_approval] → [approved] → [posted]
                            → [rejected]
```

---

### Conversation

A thread of related tweets for context retrieval.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| conversation_id | string | Twitter's conversation identifier | Required |
| root_tweet_id | string | First tweet in conversation | Required |
| tweets | array[Tweet] | Ordered list of tweets in thread | Max 5 for context |
| fetched_at | datetime | When context was retrieved | Required |

**Tweet (embedded)**:
| Field | Type | Description |
|-------|------|-------------|
| tweet_id | string | Tweet identifier |
| author_handle | string | @username |
| text | string | Tweet content |
| created_at | datetime | Posted timestamp |

---

### InteractionHistory

Memory MCP record of past interactions with a Twitter user.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| user_handle | string | @username being tracked | Required, unique |
| user_id | string | Twitter user ID | Required |
| first_interaction | datetime | First mention received | Required |
| last_interaction | datetime | Most recent interaction | Required |
| interaction_count | integer | Total mentions from user | Min: 1 |
| topics | array[string] | Network topics discussed | Optional |
| sentiment | enum | Overall interaction tone | positive, neutral, negative |

---

### ProcessedMentionTracker

In-memory/Memory MCP record for deduplication.

| Field | Type | Description | Constraints |
|-------|------|-------------|-------------|
| mention_id | string | Tweet ID of processed mention | Required |
| processed_at | datetime | When processed | Required |
| ttl | duration | Time-to-live | 24 hours |

---

## Relationships

```
Mention 1 ──────── 0..1 Reply
    │
    └──── 0..1 Conversation (via conversation_id)
    │
    └──── 1 InteractionHistory (via author_handle)
```

---

## Validation Rules

### Mention Validation
- `tweet_id` must be numeric string (Twitter ID format)
- `author_handle` must not be own account (@John_Capobianco)
- `text` must contain @mention of monitored account
- `category` must be classified before processing

### Reply Validation
- `text` must pass content guardrails (no IPs, credentials, customer names)
- `text` must be ≤280 characters OR `is_thread` must be true
- `approved` must be true before `status` can be `posted`
- `in_reply_to_tweet_id` must reference valid mention

### Spam Detection Thresholds
- Account age < 7 days → spam
- Following/Followers ratio > 100 → spam
- Username digit count > 8 → spam
- Duplicate text from known spam patterns → spam

---

## Memory MCP Schema

Keys used in Memory MCP for persistence:

| Key Pattern | Value Type | TTL | Purpose |
|-------------|------------|-----|---------|
| `twitter_mention_{id}` | JSON | 24h | Deduplication tracking |
| `twitter_user_{handle}` | InteractionHistory | 30d | User interaction history |
| `twitter_reply_{id}` | Reply | 7d | Reply audit trail |
