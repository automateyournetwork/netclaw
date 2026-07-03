# Twitter MCP Server

MCP server for Twitter/X integration. Enables NetClaw to post tweets, threads, and media to @John_Capobianco's account. Also supports bidirectional interaction via mention monitoring and reply generation.

## Tier

**Pay-as-you-go Tier** - Full bidirectional interaction. Can post tweets, read mentions, and reply to conversations.

## Features

- Post single tweets (≤280 chars)
- Post threads for longer content (auto-split at sentence boundaries)
- Post tweets with image attachments
- Delete tweets
- Content guardrails (blocks IPs, credentials, customer names)
- #netclaw hashtag enforcement
- Tweet history for deduplication
- **Monitor @mentions** (feature 040)
- **Classify mention intent** (netclaw_request, technical, friendly, spam)
- **Generate CCIE-level replies** with conversation context
- **Post replies with human approval** (Constitution Principle XIV)
- **Track interaction history** with users

## Tools

### Posting Tools (Feature 039)

| Tool | Description |
|------|-------------|
| `twitter_post_tweet` | Post a single tweet with guardrail validation |
| `twitter_post_thread` | Post a thread for content >280 chars |
| `twitter_post_tweet_with_media` | Post a tweet with image attachment |
| `twitter_delete_tweet` | Delete a tweet by ID |
| `twitter_get_rate_limits` | Check posting quota |
| `twitter_generate_heartbeat_content` | Generate content prompt for heartbeat tweets |
| `twitter_check_duplicate` | Check if content duplicates recent tweets |
| `twitter_get_history` | Get recent tweet history |
| `twitter_post_heartbeat` | Post heartbeat tweet with category tracking |

### Bidirectional Tools (Feature 040)

| Tool | Description |
|------|-------------|
| `twitter_get_mentions` | Fetch recent @mentions |
| `twitter_classify_mention` | Classify mention intent (netclaw_request, technical, friendly, spam) |
| `twitter_get_conversation` | Get thread context for better replies |
| `twitter_generate_reply` | Generate CCIE-level reply draft |
| `twitter_reply_to_tweet` | Post approved reply (requires human approval) |
| `twitter_mark_processed` | Mark mention as handled |
| `twitter_get_user_history` | Get interaction history with a user |

## Environment Variables

```bash
# Required
TWITTER_API_KEY=<from Twitter Developer Portal>
TWITTER_API_SECRET=<from Twitter Developer Portal>
TWITTER_ACCESS_TOKEN=<from Twitter Developer Portal>
TWITTER_ACCESS_SECRET=<from Twitter Developer Portal>

# Optional - Heartbeat
TWITTER_HEARTBEAT_ENABLED=false    # Enable autonomous tweets (default: false)
TWITTER_HEARTBEAT_INTERVAL=14400   # Seconds between heartbeats (default: 4 hours)

# Optional - Mention Polling
TWITTER_MENTION_POLL_INTERVAL=300  # Seconds between mention checks (default: 5 minutes)
```

## Installation

```bash
cd mcp-servers/twitter-mcp
pip install -r requirements.txt
```

## Configuration

Add to `~/.openclaw/config/openclaw.json`:

```json
{
  "mcpServers": {
    "twitter-mcp": {
      "command": "python",
      "args": ["/path/to/netclaw/mcp-servers/twitter-mcp/server.py"],
      "transport": "stdio"
    }
  }
}
```

## Content Guardrails

The server validates all content before posting:

| Pattern | Action | Description |
|---------|--------|-------------|
| IPv4 addresses | Sanitize | Replace with 192.0.2.x (RFC 5737) |
| IPv6 addresses | Sanitize | Replace with 2001:db8::x (RFC 3849) |
| MAC addresses | Block | Reject entirely |
| Credentials | Block | Detect password/key/token patterns |
| Internal hostnames | Block | Detect corp-*, internal-*, etc. |

## Rate Limits

With pay-as-you-go tier:
- Check mentions: ~$0.01 per call
- Post tweet: ~$0.01 per call
- Full reply interaction: ~$0.03-0.05

With $5 credit, expect ~100-150 interactions.

## Human Approval

Per Constitution Principle XIV, all manual tweets and replies require explicit human approval before posting:
- Heartbeat tweets require opt-in via `TWITTER_HEARTBEAT_ENABLED=true`
- Replies require `approved=true` parameter on `twitter_reply_to_tweet`
- All posted replies are logged to audit trail

## Mention Classification

Incoming mentions are classified into:

| Category | Description | Recommended Action |
|----------|-------------|-------------------|
| `netclaw_request` | Questions about NetClaw | Generate reply |
| `technical_network` | Networking questions | Generate reply |
| `friendly` | Thanks, greetings | Brief friendly reply |
| `off_topic` | Unrelated content | Consider skipping |
| `spam` | Bot/spam accounts | Skip automatically |

## Spam Detection

Heuristics to filter spam:
- Account created within 7 days
- Following/followers ratio > 100:1
- Username contains 8+ digits
- Known spam patterns (crypto, giveaway, airdrop)

## Dependencies

- tweepy>=4.14.0
- mcp>=1.0.0
- python-dotenv>=1.0.0
