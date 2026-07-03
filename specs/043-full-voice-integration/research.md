# Research: Full NetClaw Voice Integration

**Feature**: 043-full-voice-integration
**Date**: 2026-06-26

## Research Tasks

### 1. Voice Processing Architecture

**Question**: How should voice input/output be processed for natural conversation?

**Decision**: Use Twilio's built-in speech recognition (STT) and text-to-speech (TTS) with Claude as the reasoning engine.

**Rationale**:
- Twilio handles telephony infrastructure (inbound/outbound calls, PSTN connectivity)
- Twilio's STT is already integrated in Feature 042 webhook
- Claude provides natural language understanding and tool orchestration
- TTS converts Claude's responses to speech

**Alternatives Considered**:
- OpenAI Whisper API for STT: More accurate but adds latency and cost
- Local Whisper: Lower latency but requires GPU resources
- Amazon Polly for TTS: More voice options but additional integration

### 2. MCP Tool Integration Strategy

**Question**: How should voice commands map to MCP tool calls?

**Decision**: Claude handles natural language → tool mapping directly. No explicit intent classification layer.

**Rationale**:
- Claude already has tool calling capabilities
- Existing MCP tools are well-documented with clear descriptions
- Adding an intent classifier adds complexity without benefit
- Claude can ask clarifying questions naturally when ambiguous

**Alternatives Considered**:
- Rasa NLU for intent classification: Overkill for single-user system
- Custom intent patterns: Brittle, requires maintenance
- Voice-specific tool wrappers: Unnecessary indirection

### 3. Conversation Context Management

**Question**: How should multi-turn conversation context be maintained?

**Decision**: Per-caller ID context stored in Memory MCP with session-scoped in-memory cache.

**Rationale**:
- Caller ID provides natural user identity
- Memory MCP already provides persistent storage
- In-memory cache enables fast lookups during active call
- Context includes: current device focus, recent findings, conversation history

**Alternatives Considered**:
- Redis for session state: Overkill for single-user
- SQLite local storage: Doesn't integrate with existing Memory MCP
- Stateless (context in prompt): Loses cross-call continuity

### 4. Proactive Outbound Alerts

**Question**: How should outbound alert triggers be configured and executed?

**Decision**: Configuration file + event subscription pattern using existing MCP servers.

**Rationale**:
- Alert triggers defined in JSON/YAML config
- Subscribe to events from PagerDuty MCP, pyATS health checks, CML status
- Twilio MCP initiates outbound call when trigger fires
- Simple, explicit, auditable

**Alternatives Considered**:
- Database-driven triggers: Over-engineered for initial scope
- Webhook-based triggers: Requires external event sources to push
- Polling-based: Inefficient, high latency

### 5. Speech Formatting

**Question**: How should technical data be formatted for natural speech?

**Decision**: Dedicated speech formatter module that transforms MCP responses.

**Rationale**:
- UUIDs → omit or say "identifier ending in X-Y-Z"
- IP addresses → spoken naturally "10 dot 0 dot 0 dot 1"
- Timestamps → relative time "3 hours ago"
- Large lists → summarize with option to hear more
- Error codes → human-readable descriptions

**Alternatives Considered**:
- SSML markup: Twilio supports but complex to generate
- Prompt engineering only: Inconsistent results
- Pre-recorded responses: Not flexible enough

### 6. Call Duration Management

**Question**: How should long calls be handled?

**Decision**: 25-minute warning, 30-minute hard disconnect with summary.

**Rationale**:
- Prevents runaway Twilio costs
- Most queries complete in under 3 minutes
- Warning gives user time to wrap up
- Summary ensures no information lost

**Alternatives Considered**:
- No limit: Cost risk, resource exhaustion
- Shorter limit (10 min): May cut off legitimate troubleshooting
- Configurable limit: Complexity for little benefit initially

### 7. Concurrent Call Handling

**Question**: How should multiple simultaneous calls be handled?

**Decision**: Support up to 10 concurrent sessions with per-session isolation.

**Rationale**:
- Webhook server already handles async requests
- Each call gets dedicated context manager instance
- MCP tool calls are stateless and concurrent-safe
- 10 is reasonable for team expansion

**Alternatives Considered**:
- Single call only: Too limiting
- Unlimited: Resource exhaustion risk
- Queue system: Adds complexity, poor UX

## Technology Decisions Summary

| Component | Choice | Reason |
|-----------|--------|--------|
| STT | Twilio built-in | Already integrated, good enough quality |
| TTS | Twilio built-in | Low latency, natural voices |
| Reasoning | Claude (claude-sonnet-4-6) | Tool calling, context handling |
| Context Storage | Memory MCP | Existing infrastructure, per-caller persistence |
| Alert Config | JSON file | Simple, auditable, no DB needed |
| Speech Format | Custom Python module | Full control over output |

## Integration Points

### Existing MCP Servers to Integrate

| MCP Server | Voice Use Cases |
|------------|-----------------|
| pyATS MCP | Device health, BGP/OSPF status, interface queries |
| CML MCP | Lab list, start, stop, node status |
| GNS3 MCP | Project list, node management |
| PagerDuty MCP | Incident list, acknowledge, details |
| RFC MCP | RFC lookup, section queries |
| Memory MCP | Fact storage, recall, decision history |
| Twitter MCP | Post tweets, read mentions |

### New Components Required

| Component | Purpose | Location |
|-----------|---------|----------|
| Context Manager | Per-caller conversation state | `context_manager.py` |
| Speech Formatter | Technical data → natural speech | `speech_formatter.py` |
| Alert Triggers | Proactive outbound call config | `alert_triggers.py` |
| Voice Skills | SKILL.md for each capability | `workspace/skills/voice-*/` |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Speech recognition errors | Medium | Medium | Confirmation for destructive actions |
| MCP tool timeouts on voice | Medium | Low | Progress updates, async handling |
| Twilio cost overrun | Low | Medium | Call duration limits, rate limiting |
| Context confusion | Low | Low | Clear context scoping per caller |

## Open Questions (Resolved)

1. ~~Outbound call authentication~~ → No authentication, speak immediately (clarified in spec)
2. ~~Context persistence scope~~ → Per caller ID via Memory MCP (clarified in spec)
3. ~~Max call duration~~ → 30 minutes with 25-minute warning (clarified in spec)

## Next Steps

1. Create data-model.md with entity definitions
2. Define voice command contracts in contracts/
3. Create quickstart.md with setup instructions
4. Proceed to /speckit.tasks for implementation breakdown
