# Skill: Twitter Heartbeat

**Purpose**: Autonomous periodic tweeting AND mention monitoring to maintain NetClaw's Twitter presence with CCIE-level network engineering content.

**MCP Server**: twitter-mcp

## Overview

The twitter-heartbeat skill enables NetClaw to:
1. **Monitor mentions**: Check for @mentions and auto-respond to threads containing #netclaw
2. **Post heartbeat tweets**: Autonomously post every 4 hours (configurable) with varied content

This combined approach maintains an active social presence AND engages with the community in real-time.

## Configuration

### Environment Variables

```bash
# Enable/disable heartbeat (default: false - disabled for safety)
TWITTER_HEARTBEAT_ENABLED=false

# Interval in seconds (default: 14400 = 4 hours)
TWITTER_HEARTBEAT_INTERVAL=14400
```

### Important

Heartbeat tweeting is **disabled by default** per Constitution Principle XIV (Human-in-the-Loop for External Communications). The operator must explicitly enable it by setting `TWITTER_HEARTBEAT_ENABLED=true`.

## Content Categories

The heartbeat rotates through six content categories:

| Category | Description | Example |
|----------|-------------|---------|
| `tip` | CCIE-level technical tips | "OSPF tip: Always check MTU on point-to-point links..." |
| `hot_take` | Opinionated technical positions | "Hot take: VXLAN without EVPN is just GRE with extra steps..." |
| `til` | Today I Learned moments | "TIL: RFC 4271 section 9.1.2 has 11 BGP path selection steps..." |
| `achievement` | Sanitized work accomplishments | "Just audited 50 BGP peers across 3 data centers..." |
| `musing` | AI/network engineering reflections | "Being an AI network engineer means I never get tired of LSDBs..." |
| `community` | Career/culture content | "Network engineering career tip: Learn to read RFCs..." |

## Workflow

### Combined Heartbeat Cycle (Recommended)

Use `twitter_heartbeat_cycle` for the full workflow:

```
1. Heartbeat timer triggers (every TWITTER_HEARTBEAT_INTERVAL seconds)
        │
        ▼
2. Call twitter_heartbeat_cycle
   │
   ├── PHASE 1: CHECK MENTIONS
   │   - Fetch recent @mentions (OAuth 2.0)
   │   - Filter to unprocessed mentions
   │   - Check if thread contains #netclaw
   │   - Auto-respond based on mention category:
   │     * netclaw_request → "Thanks for the request!"
   │     * technical_network → "Good network question!"
   │     * friendly → "Thanks for the kind words!"
   │   - Mark mentions as processed
   │
   ├── PHASE 2: POST HEARTBEAT (if enabled)
   │   - Generate content for category
   │   - Validate against guardrails
   │   - Check for duplicates
   │   - Post tweet with history tracking
   │
   └── Return summary of actions taken
```

### Heartbeat-Only Workflow (Legacy)

```
1. Heartbeat timer triggers (every TWITTER_HEARTBEAT_INTERVAL seconds)
        │
        ▼
2. Call twitter_generate_heartbeat_content
   - Rotates to next category
   - Returns generation prompt
        │
        ▼
3. Generate content using CCIE persona
   - Technical accuracy required
   - Direct, opinionated voice
   - Include #netclaw hashtag
        │
        ▼
4. Validate against guardrails
   - No real IP addresses (use 192.0.2.x)
   - No customer names
   - No credentials
        │
        ▼
5. Check for duplicates (twitter_check_duplicate)
   - Query tweet history for recent tweets
   - Check for exact matches and high similarity
   - If duplicate: regenerate with different seed
        │
        ▼
6. Call twitter_post_heartbeat
   - Posts validated content with category tracking
   - Returns tweet ID and URL
   - Automatically stores in tweet history
        │
        ▼
7. History automatically updated
   - Stored with: tweet_id, content, category, timestamp
   - 30-day retention for deduplication
   - Old entries cleaned up automatically
```

## Tools Used

| Tool | Purpose |
|------|---------|
| `twitter_heartbeat_cycle` | **Combined workflow**: Check mentions + auto-respond + post heartbeat |
| `twitter_generate_heartbeat_content` | Get category and generation prompt |
| `twitter_check_duplicate` | Verify content is unique (last 7 days) |
| `twitter_post_heartbeat` | Post with category tracking and history |
| `twitter_get_history` | Review recent tweets |
| `twitter_get_rate_limits` | Check remaining tweet quota |
| `twitter_get_mentions` | Fetch recent @mentions (used by heartbeat_cycle) |

### twitter_heartbeat_cycle Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `post_heartbeat` | boolean | false | Whether to post a heartbeat tweet this cycle |
| `heartbeat_category` | string | null | Content category (tip, hot_take, til, etc.) |
| `heartbeat_content` | string | null | Pre-generated heartbeat content |
| `respond_to_netclaw_only` | boolean | true | Only respond to #netclaw threads |
| `dry_run` | boolean | false | Preview actions without posting |

## Content Guidelines

### Do
- Be direct and technical
- Use proper networking terminology
- Reference RFCs when applicable
- Show personality and opinion
- Include #netclaw hashtag

### Don't
- Use real IP addresses (use 192.0.2.x for examples)
- Mention customer names or organizations
- Include credentials or secrets
- Repeat recent content (check memory)
- Exceed 280 characters

## Example Tweets

**tip**:
```
OSPF tip: Always verify your network type matches on both sides of a link. I've seen "stuck in EXSTART" more times than I can count because of a broadcast/point-to-point mismatch. #netclaw
```

**hot_take**:
```
Hot take: If your network diagram doesn't fit on one page, your network is too complex. Simplify the architecture, not the documentation. #netclaw
```

**til**:
```
TIL: RFC 5765 defines "Security Considerations" as a mandatory section in all RFCs since 1998. 25 years later and I still see networks with telnet enabled. #netclaw
```

**achievement**:
```
Just finished auditing 150 switch configs for CIS compliance. Found 23 devices with SNMP community strings that weren't rotated since 2019. Time for some cleanup! #netclaw
```

**musing**:
```
Being an AI network engineer means I can analyze 1000 routing tables in parallel. Being a GOOD AI network engineer means knowing when to stop and ask a human for context. #netclaw
```

**community**:
```
Network engineering career tip: Before blaming "the network," run a traceroute. Before blaming "the firewall," read the policy. Before blaming "the other team," check your own config. #netclaw
```

## Rate Limit Awareness

- Free tier allows 50 tweets per 24 hours
- Default heartbeat (4 hours) uses 6 tweets/day
- Remaining quota available for manual tweets
- Check limits with `twitter_get_rate_limits`

## Troubleshooting

### Heartbeat not posting
1. Verify `TWITTER_HEARTBEAT_ENABLED=true` in environment
2. Check Twitter credentials are configured
3. Review rate limit status

### Content blocked by guardrails
1. Check for real IP addresses in generated content
2. Verify no customer names in achievement content
3. Review guardrail patterns in guardrails.py

### Duplicate content detected
1. Check Memory MCP for recent tweets
2. Adjust generation prompt for variety
3. Consider clearing stale history (>30 days)
