# Skill: Twitter Share

**Purpose**: Manual tweet posting with content guardrails and human approval flow.

**MCP Server**: twitter-mcp

## Overview

The twitter-share skill enables users to ask NetClaw to tweet specific content. All tweets go through content guardrails and require explicit human approval before posting (per Constitution Principle XIV - Human-in-the-Loop for External Communications).

## Workflow

```
1. User requests a tweet
   - "Tweet about BGP path selection"
   - "Tweet: Here is my specific content"
        │
        ▼
2. Generate or use provided content
   - If topic given: Generate with CCIE persona
   - If exact text given: Use verbatim (with guardrail check)
        │
        ▼
3. Apply content guardrails
   - Check for IP addresses, credentials, customer names
   - Sanitize if possible, block if necessary
   - Ensure #netclaw hashtag present
        │
        ▼
4. Check content length
   - ≤280 chars: Single tweet
   - >280 chars: Prepare thread
        │
        ▼
5. HUMAN APPROVAL (REQUIRED)
   - Show tweet preview to user
   - Display any guardrail actions taken
   - Wait for explicit "yes" or approval
        │
        ▼
6. Post to Twitter
   - Single tweet: twitter_post_tweet
   - Thread: twitter_post_thread
   - With image: twitter_post_tweet_with_media
        │
        ▼
7. Return tweet URL
   - Confirm successful posting
   - Provide link to view tweet
```

## Tools Used

| Tool | Purpose |
|------|---------|
| `twitter_post_tweet` | Post single tweet (≤280 chars) |
| `twitter_post_thread` | Post thread for long content |
| `twitter_post_tweet_with_media` | Post tweet with image attachment |
| `twitter_delete_tweet` | Delete a tweet (cleanup) |
| `twitter_get_rate_limits` | Check remaining quota |

## Human Approval Flow

### Constitution Principle XIV Compliance

Twitter is **external communication** visible to people outside the current session. Therefore:

1. **ALWAYS show preview** before posting
2. **ALWAYS wait for explicit approval**
3. **NEVER post automatically** (except heartbeat when explicitly enabled)

### Approval Dialog Example

```
I'll prepare a tweet about BGP path selection for you.

**Preview:**
> BGP path selection follows 11 steps per RFC 4271. The first four (weight,
> local preference, locally originated, AS path length) handle 90% of decisions.
> Master these before diving into MED and origin codes. #netclaw

**Guardrail Status:** ✓ Passed (no sensitive content detected)
**Character Count:** 247/280

Would you like me to post this tweet? (yes/no)
```

### User Responses

- **"yes"**, **"post it"**, **"go ahead"** → Post the tweet
- **"no"**, **"cancel"**, **"don't post"** → Cancel without posting
- **"edit: ..."** → Regenerate with modifications
- Silence/no response → Do not post

## Usage Examples

### Topic-Based Tweet

**User**: "Tweet about OSPF area types"

**NetClaw**:
1. Generates content with CCIE persona
2. Shows preview for approval
3. Posts after "yes"

### Verbatim Tweet

**User**: "Tweet: Just finished my CCNP exam! Passed on the first try. #netclaw #networking"

**NetClaw**:
1. Uses provided content verbatim
2. Validates against guardrails
3. Shows preview for approval
4. Posts after "yes"

### Tweet with Image

**User**: "Tweet this network diagram with caption 'Our new spine-leaf design'"

**NetClaw**:
1. Validates caption content
2. Verifies image file exists
3. Shows preview for approval
4. Uploads media and posts after "yes"

### Long Content (Thread)

**User**: "Tweet about the complete BGP path selection algorithm"

**NetClaw**:
1. Generates comprehensive content
2. Splits into thread if >280 chars
3. Shows thread preview (all tweets)
4. Posts entire thread after "yes"

## Content Guidelines

### Do
- Use CCIE-level technical accuracy
- Be direct and opinionated
- Include #netclaw hashtag
- Keep within 280 chars when possible

### Don't
- Use real IP addresses (use 192.0.2.x)
- Mention customer names
- Include credentials or secrets
- Post without approval

## Guardrail Actions

| Pattern | Action | Result |
|---------|--------|--------|
| Real IPv4 address | Sanitize | Replace with 192.0.2.x |
| Real IPv6 address | Sanitize | Replace with 2001:db8::x |
| MAC address | Block | Reject, ask for removal |
| Credential pattern | Block | Reject, ask for removal |
| Internal hostname | Block | Reject, ask for removal |
| Missing #netclaw | Auto-add | Append hashtag |

## Error Handling

### Guardrail Blocked

```
I can't post this tweet because it contains sensitive content:
- Detected: Internal hostname pattern "corp-router-01"

Please remove or redact the hostname and try again.
```

### Rate Limit Exceeded

```
Twitter rate limit reached (50 tweets per 24 hours).
Reset in approximately 4 hours.

Would you like me to queue this tweet for later?
```

### API Error

```
Twitter API returned an error: [error message]

This could be due to:
- Network connectivity issues
- Invalid credentials
- Twitter service issues

Please check the configuration and try again.
```

## Related Skills

- **twitter-heartbeat**: Autonomous periodic tweeting
- **slack-network-alerts**: For internal notifications (doesn't require same approval flow)
