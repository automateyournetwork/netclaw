# Twitter Respond Skill

**Skill ID**: twitter-respond
**Category**: Social Media / Engagement
**Feature**: 040-twitter-mentions

## Overview

Enables bidirectional Twitter interaction by monitoring @mentions of @John_Capobianco and generating CCIE-level technical replies. All replies require human approval per Constitution Principle XIV.

## Capabilities

1. **Mention Detection** - Poll for @mentions and classify them
2. **Reply Generation** - Create context-aware, technically accurate replies
3. **Reply Posting** - Post approved replies as threads when needed
4. **Conversation Context** - Retrieve thread history for better responses
5. **User Memory** - Track interaction history with users

## MCP Tools

This skill uses the twitter-mcp server's bidirectional tools:

| Tool | Purpose |
|------|---------|
| `twitter_get_mentions` | Fetch recent @mentions |
| `twitter_classify_mention` | Categorize mention intent |
| `twitter_get_conversation` | Get thread context |
| `twitter_generate_reply` | Generate reply draft |
| `twitter_reply_to_tweet` | Post approved reply |
| `twitter_mark_processed` | Mark mention as handled |
| `twitter_get_user_history` | Get user interaction history |

## Mention Categories

Mentions are classified into:

- **netclaw_request** - Questions about NetClaw automation, diagrams, skills
- **technical_network** - Networking questions (BGP, OSPF, Cisco, etc.)
- **friendly** - Thanks, greetings, positive engagement
- **off_topic** - Unrelated to networking/NetClaw
- **spam** - Bot accounts, crypto/NFT spam

## Workflow

```
1. Check Mentions     → twitter_get_mentions
2. Classify Intent    → twitter_classify_mention
3. Get Context        → twitter_get_conversation (if thread)
4. Get User History   → twitter_get_user_history
5. Generate Reply     → twitter_generate_reply
6. Human Reviews      → [Approval Required]
7. Post Reply         → twitter_reply_to_tweet (approved=true)
8. Mark Processed     → twitter_mark_processed
```

## Example Interaction

```
User: "Check my Twitter mentions"

NetClaw: Found 3 new mentions:

1. @alice_neteng: "@John_Capobianco what's the best way to debug BGP peering?"
   Category: technical_network

2. @random_user: "@John_Capobianco check out this crypto deal!"
   Category: spam (skipping)

3. @cisco_fan: "@John_Capobianco can NetClaw generate topology diagrams?"
   Category: netclaw_request

User: "Reply to the BGP question"

NetClaw: Here's my suggested reply:

"@alice_neteng Start with: 1) show ip bgp summary - check state
2) show ip bgp neighbors - verify open/sent/rcvd messages
3) debug ip bgp events - watch notifications

Common issues: AS mismatch, source IP, eBGP multihop. #netclaw"

Post this reply? [Yes/No/Edit]

User: "Yes"

NetClaw: Reply posted: https://twitter.com/i/web/status/123456789
```

## Configuration

Environment variables in `~/.openclaw/.env`:

```bash
# Required (from feature 039)
TWITTER_API_KEY=your_consumer_key
TWITTER_API_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_SECRET=your_access_secret

# Optional mention polling
TWITTER_MENTION_POLL_INTERVAL=300  # Check every 5 minutes
```

## Human Approval Requirement

Per Constitution Principle XIV (Human-in-the-Loop for External Communications):

- All replies are generated as drafts first
- Human must explicitly approve before posting
- `approved=true` parameter required for `twitter_reply_to_tweet`
- Audit log tracks all posted replies

## Cost Estimates

Using pay-as-you-go Twitter API tier:

| Action | Cost |
|--------|------|
| Check mentions | ~$0.01 |
| Get conversation | ~$0.01 |
| Post reply | ~$0.01 |
| **Full interaction** | **~$0.03-0.05** |

With $5 credit, expect ~100-150 interactions.

## Spam Detection

Heuristics to filter spam accounts:
- Account created within 7 days
- Following/followers ratio > 100:1
- Username contains 8+ digits
- Known spam patterns (crypto, giveaway, airdrop)

## Related Skills

- **twitter-heartbeat** - Autonomous posting (feature 039)
- **twitter-share** - Share NetClaw outputs to Twitter (feature 039)
