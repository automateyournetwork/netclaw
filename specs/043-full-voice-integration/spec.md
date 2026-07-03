# Feature Specification: Full NetClaw Voice Integration

**Feature Branch**: `043-full-voice-integration`
**Created**: 2026-06-26
**Revised**: 2026-06-26
**Status**: Draft
**Input**: "Voice is a universal input channel to Claude. Claude already has access to ALL 40+ MCPs and 100+ skills. Voice just provides speech-to-text input and text-to-speech output. Anything NetClaw can do via CLI should be accessible over the phone - IP Fabric, Forward Networks, Itential, ServiceNow, mind maps, diagrams, EVERYTHING."

## Overview

Voice integration is NOT about creating voice-specific handlers for each MCP. It's about providing **voice as an alternative input/output channel** to Claude, who already has access to ALL NetClaw capabilities:

- **40+ MCP Servers**: pyATS, CML, GNS3, PagerDuty, RFC, Memory, Twitter, IP Fabric, Forward Networks, Itential, ServiceNow, SuzieQ, Datadog, GitLab, Jenkins, Atlassian, Blender, Check Point, Prisma SD-WAN, Aruba CX, and more
- **100+ Skills**: Network health, lab management, diagram generation, ticket creation, compliance checks, and everything else

The architecture is simple:
```
Phone Call → Twilio STT → Claude (ALL MCPs + Skills) → Speech Formatter → Twilio TTS
```

Claude already knows how to use every tool. Voice is just another way to talk to Claude.

## User Scenarios & Testing

### User Story 1 - Universal Voice Access to Any Capability (Priority: P1)

A network engineer calls NetClaw and asks it to do ANYTHING that NetClaw can do via CLI - query IP Fabric, open a ServiceNow ticket, generate a mind map, check Forward Networks path analysis, run Itential automation, or any other capability.

**Why this priority**: This IS the feature. Everything else is implementation detail.

**Independent Test**: Call NetClaw, ask it to perform any operation from any MCP, verify it works.

**Acceptance Scenarios**:

1. **Given** Claude has access to all MCPs, **When** user says "Check device health on router R1", **Then** Claude uses pyATS MCP and speaks the result.
2. **Given** Claude has access to all MCPs, **When** user says "Open a ServiceNow ticket for the BGP issue", **Then** Claude uses ServiceNow MCP and confirms ticket creation.
3. **Given** Claude has access to all MCPs, **When** user says "Show me the path from site A to site B in Forward Networks", **Then** Claude uses Forward Networks MCP and describes the path.
4. **Given** Claude has access to all MCPs, **When** user says "Create a network mind map in Blender", **Then** Claude uses Blender MCP and confirms diagram creation.
5. **Given** Claude has access to all MCPs, **When** user says "Run the compliance check in IP Fabric", **Then** Claude uses IP Fabric MCP and speaks the results.
6. **Given** Claude has access to all MCPs, **When** user says "Trigger the Itential workflow for provisioning", **Then** Claude uses Itential MCP and reports status.
7. **Given** Claude has access to all MCPs, **When** user says "Check Datadog for any alerts", **Then** Claude uses Datadog MCP and speaks alert summary.
8. **Given** Claude has access to all MCPs, **When** user says "What's in my GitLab merge requests?", **Then** Claude uses GitLab MCP and lists MRs.

---

### User Story 2 - Conversation Context Across Calls (Priority: P1)

User calls NetClaw, discusses a topic, hangs up, calls back later, and NetClaw remembers the context tied to their caller ID.

**Why this priority**: Essential for natural conversation flow.

**Independent Test**: Call, discuss a device, hang up, call back, reference "the device we discussed" - verify context recalled.

**Acceptance Scenarios**:

1. **Given** user previously discussed router R1, **When** they call back and say "What about its BGP neighbors?", **Then** Claude recalls R1 from context and queries BGP.
2. **Given** user stored a fact via voice, **When** they call back days later and ask about it, **Then** Claude recalls the fact from Memory MCP.
3. **Given** context is stored per caller ID, **When** a different number calls, **Then** they get fresh context (no cross-contamination).

---

### User Story 3 - Proactive Outbound Alerts (Priority: P2)

NetClaw calls the engineer when critical events occur, rather than waiting for them to check.

**Why this priority**: Transforms NetClaw from reactive to proactive.

**Independent Test**: Trigger a critical event, verify NetClaw calls with details.

**Acceptance Scenarios**:

1. **Given** alert triggers are configured, **When** PagerDuty P1 incident fires, **Then** NetClaw calls the configured number and speaks incident details.
2. **Given** the call is answered, **When** engineer asks follow-up questions, **Then** Claude can use any MCP to investigate further.
3. **Given** engineer says "Acknowledge that incident", **Then** Claude uses PagerDuty MCP to acknowledge.

---

### User Story 4 - Speech-Optimized Response Formatting (Priority: P2)

All responses are formatted for natural speech - no UUIDs read aloud, IPs spoken naturally, large outputs summarized.

**Why this priority**: Usability requirement for voice interface.

**Independent Test**: Request data with UUIDs/IPs, verify they're spoken naturally.

**Acceptance Scenarios**:

1. **Given** a response contains IP "10.0.0.1", **When** spoken, **Then** it sounds like "10 dot 0 dot 0 dot 1".
2. **Given** a response contains a UUID, **When** spoken, **Then** it's either omitted or abbreviated "identifier ending in A-B-C".
3. **Given** a response has 50 items, **When** spoken, **Then** it summarizes "50 items found, here are the top 5..."
4. **Given** sensitive data (credentials), **When** requested, **Then** Claude refuses to speak it aloud.

---

### Edge Cases

- **Ambiguous commands**: When user says "Check the router" but multiple routers exist, NetClaw asks for clarification: "I found 3 routers. Which one: R1, R2, or R3?"
- **Long-running operations**: When lab startup takes 5+ minutes, NetClaw provides periodic progress updates and offers to call back when complete.
- **Speech recognition failures**: When speech is unclear, NetClaw asks for repetition: "I didn't catch that. Could you repeat your request?"
- **Extended call duration**: At 25 minutes, NetClaw warns and offers to summarize. At 30 minutes, call auto-disconnects with summary of session.
- **MCP tool failures**: When tools are unavailable, NetClaw explains which capability is down and suggests alternatives.
- **Sensitive information**: NetClaw never speaks credentials, keys, or secrets; offers to send via secure channel instead.
- **Concurrent device queries**: When user asks about multiple devices, NetClaw processes sequentially and reports results per device.
- **Network timeouts**: When device queries timeout, NetClaw reports partial results and identifies which devices failed.

## Requirements

### Functional Requirements

- **FR-001**: System MUST accept inbound voice calls via Twilio
- **FR-002**: System MUST transcribe speech to text using Twilio/Whisper
- **FR-003**: System MUST pass transcribed text to Claude with access to ALL registered MCPs
- **FR-004**: System MUST format Claude's response for natural speech
- **FR-005**: System MUST convert formatted response to speech via Twilio TTS
- **FR-006**: System MUST maintain conversation context per caller ID via Memory MCP
- **FR-007**: System MUST support proactive outbound calls for configured alert triggers
- **FR-008**: System MUST enforce caller whitelist for security
- **FR-009**: System MUST log all voice sessions for audit
- **FR-010**: System MUST enforce 30-minute call duration limit

### Non-Functional Requirements

- **NFR-001**: Response latency under 5 seconds for simple queries
- **NFR-002**: Support 10 concurrent voice sessions
- **NFR-003**: Speech formatting must handle any MCP response (not just known formats)

### Key Entities

- **VoiceSession**: Active call (Twilio SID, caller ID, start time, conversation history, current device/lab focus).
- **ConversationContext**: Per-caller state persisted in Memory MCP - each phone number maintains its own history across calls.
- **AlertTrigger**: Configuration for proactive outbound calls (event source, filter, recipient phone number, cooldown).
- **CallerWhitelist**: Authorized phone numbers with roles and call limits.

## Success Criteria

- **SC-001**: User can perform ANY NetClaw operation via voice that they can do via CLI
- **SC-002**: Context persists across calls for same caller ID
- **SC-003**: Proactive alerts call within 30 seconds of trigger
- **SC-004**: No UUIDs, raw IPs, or unpronounceable strings spoken
- **SC-005**: All 40+ MCPs accessible via voice (no exceptions)

## Clarifications

### Session 2026-06-26

- Q: How should outbound call recipients authenticate? → A: No authentication - speak immediately
- Q: Should conversation context persist across calls? → A: Yes, per caller ID via Memory MCP
- Q: What is the maximum call duration? → A: 30 minutes (warn at 25, disconnect at 30)
- Q: Should voice have specific handlers per MCP? → A: NO - Claude already has all tools, voice is just I/O

## Assumptions

- Twilio Voice MCP (Feature 042) is deployed and functional
- All 40+ MCPs are registered and accessible to Claude
- Caller whitelist is configured in ~/.openclaw/voice/whitelist.json
- Memory MCP available for context persistence
- Twilio account has sufficient credits for voice calls
- Claude is available with tool calling capabilities
- Sensitive credentials are stored securely and never spoken aloud
