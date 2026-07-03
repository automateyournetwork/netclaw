# Feature Specification: Twitter Bidirectional Interaction

**Feature Branch**: `040-twitter-mentions`
**Created**: 2026-06-24
**Status**: Draft
**Input**: User description: "Add mention monitoring and reply capability to Twitter MCP. Poll for @mentions of @John_Capobianco, process them through NetClaw, and post intelligent replies. Uses pay-as-you-go API tier. New tools: twitter_get_mentions, twitter_reply_to_tweet, twitter_get_conversation. Should integrate with existing twitter-mcp server and Memory MCP for context."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Mention Detection (Priority: P1)

As @John_Capobianco, I want NetClaw to detect when someone mentions me on Twitter so that I can be aware of questions and engagement opportunities.

**Why this priority**: Core functionality - without mention detection, no bidirectional interaction is possible. This enables all other features.

**Independent Test**: Can be tested by having a test account tweet "@John_Capobianco test question" and verifying NetClaw detects and displays it.

**Acceptance Scenarios**:

1. **Given** NetClaw is running with Twitter credentials configured, **When** a user tweets "@John_Capobianco what's the best OSPF metric?", **Then** NetClaw retrieves and displays the mention within 5 minutes
2. **Given** multiple mentions exist, **When** NetClaw polls for mentions, **Then** it returns mentions in reverse chronological order (newest first)
3. **Given** a mention has already been processed, **When** NetClaw polls again, **Then** it does not return duplicate mentions

---

### User Story 2 - Intelligent Reply Generation (Priority: P2)

As @John_Capobianco, I want NetClaw to generate contextually appropriate CCIE-level replies to technical questions so that I can engage with my community efficiently.

**Why this priority**: Provides the core value proposition - automated intelligent responses. Depends on US1 for mention input.

**Independent Test**: Can be tested by providing a sample mention text and verifying NetClaw generates an appropriate technical response under 280 characters.

**Acceptance Scenarios**:

1. **Given** a mention asking a technical network question, **When** NetClaw processes it, **Then** it generates a helpful, accurate CCIE-level response
2. **Given** a generated reply exceeds 280 characters, **When** preparing to post, **Then** it is automatically split into a thread or condensed
3. **Given** a mention is spam or off-topic, **When** NetClaw analyzes it, **Then** it flags for human review rather than auto-replying

---

### User Story 3 - Reply Posting with Approval (Priority: P2)

As @John_Capobianco, I want to review and approve replies before they are posted so that I maintain control over my public communications (Constitution Principle XIV compliance).

**Why this priority**: Essential for brand safety and maintaining authentic voice. Same priority as US2 since they work together.

**Independent Test**: Can be tested by triggering a reply flow and verifying the approval prompt appears before any tweet is posted.

**Acceptance Scenarios**:

1. **Given** NetClaw has generated a reply, **When** it prepares to post, **Then** it shows the reply text and asks for human approval
2. **Given** the user approves the reply, **When** posted, **Then** it appears as a proper reply thread to the original mention
3. **Given** the user rejects or edits the reply, **When** resubmitted, **Then** the modified version is used

---

### User Story 4 - Conversation Context (Priority: P3)

As @John_Capobianco, I want NetClaw to understand the full conversation context when replying so that responses are relevant to the discussion thread.

**Why this priority**: Enhances reply quality but not essential for basic functionality. Can be added after core reply works.

**Independent Test**: Can be tested by replying to a tweet that is part of a longer thread and verifying NetClaw considers parent tweets.

**Acceptance Scenarios**:

1. **Given** a mention is a reply to another tweet, **When** NetClaw processes it, **Then** it retrieves up to 5 parent tweets for context
2. **Given** conversation context is available, **When** generating a reply, **Then** the response references relevant context from the thread

---

### User Story 5 - Memory Integration (Priority: P3)

As @John_Capobianco, I want NetClaw to remember past interactions with users so that replies can reference prior conversations and build relationships.

**Why this priority**: Nice-to-have feature that improves engagement quality. Builds on Memory MCP integration from feature 039.

**Independent Test**: Can be tested by having the same user ask follow-up questions and verifying NetClaw references the prior interaction.

**Acceptance Scenarios**:

1. **Given** a user has interacted before, **When** they mention @John_Capobianco again, **Then** NetClaw retrieves relevant past interaction history
2. **Given** past context exists, **When** generating a reply, **Then** it can reference "as we discussed" or similar continuity

---

### Edge Cases

- What happens when the Twitter API rate limit is exceeded? System queues mentions for later processing and resumes when limit resets.
- How does system handle mentions in languages other than English? Attempt reply in same language using detected language, or skip with flag for human review.
- What happens when a mention is deleted before reply is posted? Skip gracefully, log the event, do not error.
- How does system handle mentions from blocked/muted accounts? Respect user's block list, skip those mentions automatically.
- What happens during Twitter API outages? Retry with exponential backoff, alert user after 3 consecutive failures.
- How does system handle off-topic mentions (sports, politics, etc.)? Skip silently - only respond to NetClaw-related requests and technical network questions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST poll for new mentions of @John_Capobianco at configurable intervals (default: 5 minutes)
- **FR-002**: System MUST track which mentions have been processed to prevent duplicate handling
- **FR-003**: System MUST retrieve mention text, author handle, tweet ID, and timestamp for each mention
- **FR-004**: System MUST generate contextually appropriate replies using CCIE-level network expertise
- **FR-005**: System MUST enforce human approval before posting any reply (Constitution Principle XIV)
- **FR-006**: System MUST post replies as proper Twitter thread replies (in_reply_to_tweet_id)
- **FR-007**: System MUST apply content guardrails to generated replies (no IPs, credentials, customer names)
- **FR-008**: System MUST log all mentions received and replies posted to Memory MCP for history
- **FR-009**: System MUST handle rate limits gracefully with queuing and retry logic
- **FR-010**: System MUST provide a tool to retrieve conversation context (parent tweets in a thread)
- **FR-011**: System MUST filter spam/bot mentions using basic heuristics (new accounts, high volume, suspicious patterns)
- **FR-012**: System MUST use context-aware response logic: reply to NetClaw-related requests (automations, diagrams, network tasks) and technical network questions; skip non-NetClaw/off-topic mentions silently

### Key Entities

- **Mention**: A tweet that @mentions the configured user account. Contains tweet_id, author_handle, text, timestamp, conversation_id, in_reply_to_tweet_id
- **Reply**: A response tweet posted to a mention. Contains tweet_id, in_reply_to_tweet_id, text, timestamp, approval_status
- **Conversation**: A thread of related tweets. Contains conversation_id, list of tweet_ids in thread order
- **InteractionHistory**: Memory MCP record of past interactions with a specific Twitter user. Contains user_handle, interaction_count, last_interaction, topic_summary

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mentions are detected and available for processing within 5 minutes of being posted
- **SC-002**: 95% of technical network questions receive relevant, accurate replies
- **SC-003**: Zero replies posted without human approval (100% compliance with Principle XIV)
- **SC-004**: Reply generation completes within 30 seconds of mention retrieval
- **SC-005**: System correctly threads replies 100% of the time (no orphaned tweets)
- **SC-006**: Spam/bot mentions are filtered with at least 80% accuracy
- **SC-007**: API costs stay under $0.10 per interaction (mention read + reply post)

## Clarifications

### Session 2026-06-24

- Q: How should system handle non-technical mentions (greetings, general comments)? → A: Context-aware response - reply to NetClaw-related requests (automations, diagrams, network tasks) and technical network questions; skip non-NetClaw/off-topic mentions

## Assumptions

- Twitter pay-as-you-go API tier provides access to mentions timeline endpoint
- User has configured valid Twitter API credentials with read and write permissions
- Existing twitter-mcp server (feature 039) is installed and functional
- Memory MCP server (feature 033) is available for interaction history storage
- English is the primary language for interactions (other languages handled best-effort)
- Poll-based mention detection is acceptable (no real-time streaming required)
- Human operator is available to approve replies within reasonable timeframe (async workflow acceptable)
- Rate limit of ~100 mention reads per 15 minutes is sufficient for typical engagement volume
