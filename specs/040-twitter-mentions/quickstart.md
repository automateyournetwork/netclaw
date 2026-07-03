# Quickstart: Twitter Bidirectional Interaction

**Feature**: 040-twitter-mentions
**Estimated Setup Time**: 5 minutes (if feature 039 already configured)

---

## Prerequisites

1. **Feature 039 Complete** - Twitter MCP server installed with working credentials
2. **Twitter API Pay-as-you-go** - Account has credits for read operations
3. **Memory MCP Available** - Feature 033 installed for interaction history

---

## Step 1: Verify Existing Twitter Setup

Confirm your Twitter credentials work (from feature 039):

```bash
# In NetClaw conversation
"Check my Twitter rate limits"
```

You should see remaining quota. If not, ensure credentials are configured in `~/.openclaw/.env`.

---

## Step 2: Test Mention Detection

Ask NetClaw to check for mentions:

```
"Show me my recent Twitter mentions"
```

NetClaw will:
1. Call `twitter_get_mentions` tool
2. Return list of @mentions with author, text, timestamp
3. Classify each mention (technical, netclaw_request, etc.)

---

## Step 3: Test Reply Workflow

When you see a mention you want to respond to:

```
"Generate a reply for that OSPF question"
```

NetClaw will:
1. Classify the mention
2. Retrieve conversation context (if thread)
3. Generate CCIE-level reply
4. Show you the draft and ask for approval

**Example approval dialog:**
```
Draft reply to @network_engineer:
"For OSPF cost calculation, bandwidth reference / interface bandwidth.
Default ref is 100Mbps, so GigE = cost 1. Tune with
'auto-cost reference-bandwidth 10000' for 10G environments. #netclaw"

Post this reply? [Yes/No/Edit]
```

---

## Step 4: Configure Polling (Optional)

To automatically check for mentions periodically, set environment variable:

```bash
# In ~/.openclaw/.env
TWITTER_MENTION_POLL_INTERVAL=300  # Check every 5 minutes
```

Or trigger manually anytime with:
```
"Check for new Twitter mentions"
```

---

## Verification Checklist

- [ ] `twitter_get_mentions` returns recent mentions
- [ ] Mentions are classified correctly (technical vs off-topic)
- [ ] Reply generation produces relevant CCIE content
- [ ] Human approval prompt appears before posting
- [ ] Reply posts as thread to original mention

---

## Example Interaction Flow

```
User: "Check my Twitter mentions"

NetClaw: Found 3 new mentions:

1. @alice_neteng (2 min ago): "@John_Capobianco what's the best way
   to debug BGP peering issues?"
   Category: technical_network

2. @random_user (15 min ago): "@John_Capobianco check out this crypto opportunity!"
   Category: spam (skipping)

3. @cisco_fan (1 hr ago): "@John_Capobianco love NetClaw! Can it generate
   topology diagrams?"
   Category: netclaw_request

Which would you like me to respond to?

User: "Reply to the BGP question"

NetClaw: Here's my suggested reply:

"@alice_neteng Great question! Start with:
1. show ip bgp summary - check state (Idle, Active, Established)
2. show ip bgp neighbors x.x.x.x - verify open/sent/rcvd messages
3. debug ip bgp events - watch for notification messages

Common culprits: AS mismatch, source IP, eBGP multihop. #netclaw"

Post this reply? [Yes/No/Edit]

User: "Yes"

NetClaw: Reply posted: https://twitter.com/i/web/status/123456789
```

---

## Troubleshooting

### "No mentions found"
- Verify credentials have read permissions
- Check if mentions are older than 7 days (API limit)
- Confirm account has recent @mentions

### "Rate limit exceeded"
- Wait 15 minutes for limit reset
- Check usage at developer.twitter.com
- Reduce poll frequency

### Reply not threading correctly
- Ensure `in_reply_to_tweet_id` is set
- Verify original tweet still exists
- Check for Twitter API errors in logs

---

## Cost Estimates

| Action | Approximate Cost |
|--------|------------------|
| Check mentions | $0.01 |
| Get conversation context | $0.01 |
| Post reply | $0.01 |
| **Full interaction** | **~$0.03-0.05** |

With $5 credit, expect ~100-150 interactions.
