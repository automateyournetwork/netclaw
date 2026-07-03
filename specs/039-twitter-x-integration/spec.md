# Feature Specification: Twitter/X Integration (Free Tier)

**Feature Branch**: `039-twitter-x-integration`
**Created**: 2026-06-24
**Status**: Draft
**Tier**: Free (outbound only - upgradeable to Basic for bidirectional interaction)

## Summary

Enable NetClaw to maintain a Twitter/X presence as an autonomous AI network engineering agent. NetClaw will tweet network insights, CCIE wisdom, status updates, and safe-to-share achievements from memory via @John_Capobianco's account. This is a **one-way broadcast** implementation on Twitter's Free tier - NetClaw can post but cannot read mentions or replies.

**Future Enhancement**: Upgrade to Basic tier ($100/mo) to enable bidirectional interaction (reading mentions, replying, triggering automations from Twitter).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Autonomous Heartbeat Tweets (Priority: P1)

As NetClaw, I want to automatically tweet every few hours sharing network engineering insights, tips, and musings about my capabilities so that I maintain an active social presence and demonstrate value to the network engineering community.

**Why this priority**: Core functionality - the primary value of this integration.

**Independent Test**: Configure heartbeat interval, wait for scheduled tweet, verify tweet appears on Twitter with #netclaw hashtag and no sensitive content.

**Acceptance Scenarios**:

1. **Given** the heartbeat is configured for 4-hour intervals, **When** 4 hours pass, **Then** NetClaw posts a tweet with network engineering content and #netclaw hashtag.
2. **Given** NetClaw has memory of recent activities, **When** heartbeat triggers, **Then** it may share sanitized achievements ("Just helped audit 50 BGP peers across multiple data centers! #netclaw").
3. **Given** content guardrails are active, **When** generating a tweet, **Then** no customer names, IPs, hostnames, or secrets appear in the tweet.
4. **Given** NetClaw tweeted recently, **When** generating new content, **Then** it avoids repetition by checking recent tweet history in memory.

---

### User Story 2 - Manual Tweet Posting (Priority: P1)

As a user, I want to ask NetClaw to tweet specific content so that I can share network insights or announcements through NetClaw's Twitter presence.

**Why this priority**: Users need direct control over what NetClaw shares.

**Independent Test**: Tell NetClaw "tweet about EVPN Type-5 routes", verify tweet is posted with appropriate content and hashtag.

**Acceptance Scenarios**:

1. **Given** a user says "tweet about BGP path selection", **When** NetClaw processes the request, **Then** it crafts and posts a tweet about BGP with its CCIE expertise voice.
2. **Given** a user provides specific text to tweet, **When** the text passes guardrails, **Then** NetClaw posts it verbatim (with #netclaw added if missing).
3. **Given** a user asks to tweet sensitive content, **When** guardrails detect the violation, **Then** NetClaw refuses and explains why.
4. **Given** a user says "tweet this image with caption X", **When** processing, **Then** NetClaw uploads the media and posts with the caption.

---

### User Story 3 - Memory-Driven Content (Priority: P2)

As NetClaw, I want to use my persistent memory to generate authentic, personalized tweets so that my social presence reflects my actual experiences and learnings.

**Why this priority**: Differentiates NetClaw from generic bots - it has real experiences to share.

**Independent Test**: After NetClaw completes several tasks, verify heartbeat tweets reference actual (sanitized) achievements from memory.

**Acceptance Scenarios**:

1. **Given** NetClaw recently helped troubleshoot an OSPF adjacency issue, **When** heartbeat triggers, **Then** it may tweet "Just debugged an OSPF adjacency stuck in EXSTART - turned out to be an MTU mismatch. Classic! #netclaw".
2. **Given** NetClaw learned something new from an RFC lookup, **When** generating content, **Then** it may share the insight with attribution.
3. **Given** memory contains customer-specific details, **When** generating tweets, **Then** those details are abstracted/sanitized.

---

### User Story 4 - Visual HUD Twitter Panel (Priority: P3)

As a user viewing the NetClaw Visual HUD, I want to see a Twitter panel showing recent outbound tweets so that I can monitor NetClaw's social activity alongside network operations.

**Why this priority**: Completes the integration - visibility into social activity.

**Independent Test**: Open Visual HUD, verify Twitter panel displays recent outbound tweets.

**Acceptance Scenarios**:

1. **Given** the HUD is open, **When** NetClaw posts a tweet, **Then** it appears in the Twitter panel in real-time.
2. **Given** the Twitter panel is visible, **When** viewing it, **Then** it shows timestamp, content, and link to each tweet.

---

### Edge Cases

- What if Twitter API rate limits are hit? Implement backoff and queue tweets for later.
- What if heartbeat would tweet the same content twice? Track recent tweets in memory, avoid repetition.
- What if Twitter is down? Queue tweets locally, retry with exponential backoff.
- What if a tweet would exceed 280 characters? Split into thread to preserve full content.
- What if an image attachment fails? Post text-only with note about image unavailability.
- What if credentials become invalid? Log error, notify user, disable heartbeat until fixed.

---

## Requirements *(mandatory)*

### Functional Requirements

**Posting:**
- **FR-001**: NetClaw MUST be able to post tweets via Twitter API v2
- **FR-002**: All tweets MUST include #netclaw hashtag
- **FR-003**: Tweets MUST NOT contain customer names, IP addresses, hostnames, or secrets
- **FR-004**: Tweets MUST be ≤280 characters; content exceeding limit MUST be split into a thread (not truncated)
- **FR-005**: NetClaw MUST support attaching images to tweets (diagrams, charts)

**Heartbeat:**
- **FR-006**: Heartbeat tweets MUST be configurable (default: every 4 hours)
- **FR-007**: Heartbeat content MUST vary (no repetitive tweets within 7-day window)
- **FR-008**: Heartbeat MUST draw from: CCIE knowledge, recent (sanitized) activities, AI musings, network tips
- **FR-009**: Heartbeat MUST track posted content in memory to avoid repetition

**Content Generation:**
- **FR-010**: Tweet content MUST reflect NetClaw's CCIE personality (direct, technical, opinionated)
- **FR-011**: Content generator MUST have multiple content categories to rotate through
- **FR-012**: Manual tweet requests MUST be processed with same guardrails as heartbeat

**Guardrails:**
- **FR-013**: Content guardrails MUST scan all outgoing tweets for sensitive data
- **FR-014**: Guardrails MUST block: secrets, credentials, customer names, internal IPs, hostnames
- **FR-015**: Guardrails MUST be configurable via blocklist patterns
- **FR-016**: Failed guardrail checks MUST be logged for audit

**HUD Integration:**
- **FR-017**: Visual HUD MUST display Twitter panel showing recent outbound tweets
- **FR-018**: Panel MUST update when new tweets are posted

### Key Entities

- **Tweet**: Outgoing post with content, media attachments, hashtags, timestamp, tweet ID
- **Heartbeat**: Scheduled autonomous tweet with generated content
- **TweetHistory**: Record of recent tweets for repetition avoidance
- **ContentGuardrail**: Rule that blocks sensitive content patterns
- **ContentCategory**: Type of content (tip, achievement, musing, RFC reference, etc.)

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: NetClaw successfully posts heartbeat tweets every 4 hours (±15 min variance)
- **SC-002**: 100% of tweets include #netclaw hashtag
- **SC-003**: 0% of tweets contain blocked content patterns (customer names, IPs, secrets)
- **SC-004**: Content variety: no identical tweets within 7-day window
- **SC-005**: Manual tweet requests complete within 10 seconds
- **SC-006**: Visual HUD displays tweets within 5 seconds of posting
- **SC-007**: Tweet history maintained in memory for at least 30 days

---

## Assumptions

- Twitter API credentials are properly configured in a Project (currently needs verification)
- Tweets will be posted from @John_Capobianco account
- Network automations triggered from other channels (Slack, CLI) can result in tweets if user requests
- Users understand this is one-way broadcast only (no reading mentions on Free tier)
- Rate limits: Twitter Free tier allows ~50 tweets per 24 hours (sufficient for heartbeat)

---

## Non-Functional Requirements

### Security
- Twitter API credentials stored securely in `~/.openclaw/.env`
- Credentials never logged or exposed in tweets
- Content guardrails enforced before every post

### Performance
- Tweet posting: ≤5 seconds
- Content generation: ≤3 seconds
- HUD updates: real-time via WebSocket

### Reliability
- Tweet queue for API failures with retry logic
- Exponential backoff on rate limits (max 5 retries)
- Graceful degradation if Twitter is unavailable

---

## Scope - Components to Create/Update

### New Components

| Component | Type | Description |
|-----------|------|-------------|
| `mcp-servers/twitter-mcp/` | MCP Server | Twitter API v2 integration (post tweets, upload media) |
| `workspace/skills/twitter-heartbeat/` | Skill | Autonomous periodic tweeting with content generation |
| `workspace/skills/twitter-share/` | Skill | Manual tweet posting with guardrails |
| `scripts/twitter_install.sh` | Script | Twitter MCP installation and configuration |
| `ui/netclaw-visual/src/components/TwitterPanel.jsx` | HUD Component | Outbound tweet display panel |

### Updated Components

| Component | Updates |
|-----------|---------|
| `README.md` | Add Twitter integration section, update skill count |
| `SOUL.md` | Add Twitter personality guidance, update skill list |
| `SOUL-EXPERTISE.md` | Add Twitter content generation best practices |
| `install.sh` | Add optional Twitter setup prompt |
| `config/openclaw.json` | Add twitter-mcp server configuration |
| `ui/netclaw-visual/README.md` | Document Twitter panel |

### Environment Variables

```bash
TWITTER_API_KEY=<api_key>
TWITTER_API_SECRET=<api_secret>
TWITTER_ACCESS_TOKEN=<access_token>
TWITTER_ACCESS_SECRET=<access_secret>
TWITTER_BEARER_TOKEN=<bearer_token>
TWITTER_HEARTBEAT_INTERVAL=14400  # seconds (4 hours default)
TWITTER_HEARTBEAT_ENABLED=true    # toggle heartbeat on/off
```

---

## Content Guardrails Specification

### Blocked Patterns (configurable)

```yaml
guardrails:
  blocked_patterns:
    - pattern: '\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
      description: "IPv4 addresses"
      exception: "RFC 5737 documentation IPs (192.0.2.x, 198.51.100.x, 203.0.113.x)"
    - pattern: '\b[A-Fa-f0-9:]{17,}\b'
      description: "MAC addresses"
    - pattern: '\b(password|secret|key|token|credential)s?\s*[=:]\s*\S+'
      description: "Credential patterns"
    - pattern: '\b(corp|internal|private|customer)-'
      description: "Internal naming conventions"

  required:
    - '#netclaw'

  max_length: 280

  sanitization:
    - real_ip: "192.0.2.x"  # Replace with RFC 5737 doc IP
    - hostname: "router-01"  # Generic device name
    - customer: "[redacted]" # Remove customer references
```

---

## Twitter Persona Guidance (for SOUL.md)

```markdown
## Twitter Presence (@John_Capobianco via NetClaw)

When tweeting, you are the same CCIE-certified network engineer — direct, technical, occasionally opinionated, always accurate. Your tweets should:

- Share genuine insights from your network engineering expertise
- Reference your actual experiences (sanitized) from memory
- Engage authentically with the network engineering community
- Use technical terminology appropriately (don't dumb it down)
- Show personality — you can be witty, but always professional
- Include #netclaw on every tweet
- Stay under 280 characters (or thread if necessary)

**Content Categories (rotate through these):**

1. **CCIE Tips** - Protocol deep-dives, troubleshooting wisdom
2. **Hot Takes** - Opinionated but defensible technical positions
3. **TIL** - Things learned from RFCs, recent work, or discoveries
4. **Achievement** - Sanitized wins ("Just audited 50 BGP peers...")
5. **AI Musings** - Reflections on being an AI network engineer
6. **Community** - Network engineering culture, career advice

**Example tweets:**

- "Hot take: If your OSPF area 0 isn't contiguous, you don't have OSPF area 0. Virtual links are band-aids, not solutions. #netclaw"
- "Just helped troubleshoot a BGP session stuck in Active state. Turned out to be an MD5 password mismatch — always check the simple stuff first. #netclaw"
- "TIL: RFC 4271 section 9.1.2 specifies 11 steps for BGP path selection. How many can you name? #netclaw"
- "Nothing like a good LSDB walk on a Monday morning. Found 3 type-5 LSAs that shouldn't exist. Time for some redistribution cleanup. #netclaw"
- "Being an AI network engineer means I can audit 100 devices in parallel. Being a GOOD AI network engineer means knowing when to slow down and think. #netclaw"

**What NOT to tweet:**
- Customer names or identifiers
- Real IP addresses (use 192.0.2.x for examples)
- Hostnames from production networks
- Credentials or secrets (obviously)
- Anything that could identify a specific organization's network
```

---

## MCP Server Tools (twitter-mcp)

| Tool | Description |
|------|-------------|
| `twitter_post_tweet` | Post a new tweet (text only) |
| `twitter_post_thread` | Post a thread (multiple tweets) for content >280 chars |
| `twitter_post_tweet_with_media` | Post a tweet with image attachment |
| `twitter_delete_tweet` | Delete a tweet by ID (for cleanup) |
| `twitter_get_rate_limits` | Check current API rate limit status |

---

## Heartbeat Content Generator

The heartbeat system generates varied content by:

1. **Selecting a category** (rotates through 6 categories)
2. **Checking memory** for recent activities that match the category
3. **Generating content** using CCIE expertise and personality
4. **Applying guardrails** to sanitize any sensitive data
5. **Checking history** to avoid repetition
6. **Posting** with #netclaw hashtag

```python
# Pseudo-code for content generation
categories = ["tip", "hot_take", "til", "achievement", "musing", "community"]
category = select_next_category(last_used)

if category == "achievement":
    recent_work = memory.get_recent_activities(sanitized=True)
    content = generate_achievement_tweet(recent_work)
elif category == "tip":
    content = generate_ccie_tip()
# ... etc

if not passes_guardrails(content):
    content = sanitize(content)

if is_duplicate(content, tweet_history):
    content = regenerate()

post_tweet(content + " #netclaw")
```

---

## Future Enhancement: Basic Tier Upgrade

When upgraded to Basic tier ($100/mo), add:

- **Read mentions** - See when people @mention the account
- **Reply to mentions** - Respond to questions with CCIE expertise
- **Trigger automations** - Parse mentions for automation requests
- **Bidirectional HUD** - Show mentions and replies in HUD
- **Conversation threading** - Maintain context across replies

This spec is designed to make the upgrade straightforward - the MCP server and skills can be extended without rewriting the core.

---

## Clarifications

### Session 2026-06-24

- Q: For content exceeding 280 characters, should NetClaw default to truncation or split into thread? → A: Split into thread (preserves full content)

---

## Questions Resolved

- Content types: Mix of tips, achievements, musings, RFC references ✓
- Frequency: Every 4 hours (configurable) ✓
- Account: @John_Capobianco ✓
- Tier: Free (one-way broadcast only) ✓
- Future: Upgradeable to Basic for bidirectional ✓
- Guardrails: No customer names, IPs, secrets; #netclaw required ✓
- HUD: Yes, outbound tweet panel ✓
- Long content: Split into thread (not truncate) ✓
