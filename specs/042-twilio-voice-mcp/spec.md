# Feature Specification: Twilio Voice MCP Integration

**Feature Branch**: `042-twilio-voice-mcp`
**Created**: 2026-06-25
**Status**: Draft
**Input**: User description: "Add bidirectional phone call capabilities to NetClaw using Twilio for emergency alerts, situation updates, daily check-ins, on-demand calls, AND the ability to call NetClaw for voice conversations. Strict guardrails required."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Emergency Alert Calls (Priority: P1)

As John, I want NetClaw to call me immediately when critical network events occur so that I can respond to emergencies even when not actively monitoring screens.

**Why this priority**: Life-of-network critical. When a P1 incident occurs or critical infrastructure fails, phone calls ensure notification regardless of screen time. This is the primary value proposition of voice integration.

**Independent Test**: Can be tested by simulating a P1 PagerDuty incident and verifying NetClaw initiates a phone call with the incident summary.

**Acceptance Scenarios**:

1. **Given** a P1 incident is triggered in PagerDuty, **When** NetClaw processes the incident, **Then** it immediately calls John's whitelisted phone number with a voice summary of the incident
2. **Given** critical device failure is detected (core router, firewall, WAN link), **When** NetClaw classifies it as emergency-level, **Then** it initiates a phone call within 60 seconds
3. **Given** an emergency call is in progress, **When** the call connects, **Then** NetClaw speaks a clear, concise summary using text-to-speech (no sensitive data like IPs or credentials)
4. **Given** the call fails to connect (voicemail, no answer), **When** 30 seconds elapse, **Then** NetClaw retries once and logs the attempt

---

### User Story 2 - On-Demand Status Calls (Priority: P2)

As John, I want to explicitly request NetClaw to call me with a status update so that I can get voice briefings while away from my desk.

**Why this priority**: Provides proactive value beyond emergencies. Allows John to request calls when convenient, maintaining human control over when calls occur.

**Independent Test**: Can be tested by issuing a command like "Call me with the current network status" and verifying NetClaw initiates a call with the requested information.

**Acceptance Scenarios**:

1. **Given** John sends "call me with network status" via Slack or CLI, **When** NetClaw processes the request, **Then** it calls John's number and speaks current network health summary
2. **Given** John requests a call about a specific topic (e.g., "call me about the CML lab status"), **When** NetClaw processes the request, **Then** the call content focuses on that specific topic
3. **Given** John is already on an active NetClaw call, **When** he requests another call, **Then** the system queues the request and notifies him

---

### User Story 3 - Situation Update Calls (Priority: P2)

As John, I want NetClaw to call me with updates during ongoing incidents when I request it so that I can stay informed while handling other responsibilities.

**Why this priority**: Same priority as on-demand since both require explicit human direction. Critical for incident management continuity.

**Independent Test**: Can be tested by having an open incident, requesting periodic updates, and verifying calls occur with relevant status changes.

**Acceptance Scenarios**:

1. **Given** an active incident is being tracked, **When** John says "call me every 30 minutes with updates", **Then** NetClaw schedules periodic calls until the incident is resolved or John cancels
2. **Given** a scheduled update call is due, **When** there are no status changes since last call, **Then** NetClaw skips the call and notifies via text instead (to avoid unnecessary calls)
3. **Given** significant progress occurs on the incident, **When** the change is critical (e.g., resolved, escalated), **Then** NetClaw calls immediately regardless of schedule

---

### User Story 4 - Daily Check-in Calls (Priority: P3)

As John, I want to optionally enable daily phone briefings from NetClaw so that I can start my day with a voice summary of network health.

**Why this priority**: Nice-to-have feature that builds on core calling capability. Not essential but adds value for routine operations.

**Independent Test**: Can be tested by enabling daily briefings, waiting for the scheduled time, and verifying the call occurs with a summary.

**Acceptance Scenarios**:

1. **Given** daily briefings are enabled with a scheduled time (e.g., 8:00 AM), **When** the scheduled time arrives, **Then** NetClaw calls with a summary of overnight events and current health status
2. **Given** no significant events occurred overnight, **When** the briefing call connects, **Then** NetClaw delivers a brief "all clear" message (under 30 seconds)
3. **Given** John disables daily briefings, **When** the previously scheduled time arrives, **Then** no call is made

---

### User Story 5 - Inbound Voice Conversations (Priority: P2)

As John, I want to call a dedicated phone number and have a voice conversation with NetClaw so that I can interact with my network assistant hands-free while driving or away from screens.

**Why this priority**: Enables true bidirectional communication. High value for mobile/hands-free scenarios. Same priority as other explicit-request features since it requires John to initiate.

**Independent Test**: Can be tested by calling the NetClaw phone number and having a spoken conversation about network status.

**Acceptance Scenarios**:

1. **Given** John calls the dedicated NetClaw phone number, **When** the call connects, **Then** NetClaw greets him and listens for voice commands
2. **Given** John speaks a question like "What's the status of my CML lab?", **When** NetClaw processes the speech, **Then** it responds with the relevant information via voice
3. **Given** John asks NetClaw to perform an action (e.g., "Run a health check on the core routers"), **When** the action requires approval, **Then** NetClaw asks for verbal confirmation before proceeding
4. **Given** John says "goodbye" or hangs up, **When** the call ends, **Then** NetClaw logs the conversation summary
5. **Given** an unknown caller dials the NetClaw number, **When** caller ID doesn't match the whitelist, **Then** the call is rejected with a polite message

---

### User Story 6 - Voice-Initiated Network Commands (Priority: P3)

As John, I want to issue network commands via voice during a phone call so that I can manage the network without needing a screen.

**Why this priority**: Advanced feature building on inbound calling. Enables full hands-free network management but not essential for basic voice interaction.

**Independent Test**: Can be tested by calling NetClaw and issuing a voice command that triggers a network action.

**Acceptance Scenarios**:

1. **Given** John is on a call with NetClaw, **When** he says "Show me BGP neighbors on router-1", **Then** NetClaw speaks the BGP neighbor summary
2. **Given** John requests a potentially impactful action, **When** the command involves configuration changes, **Then** NetClaw requires verbal confirmation ("Say 'confirm' to proceed")
3. **Given** John asks for information that would contain sensitive data, **When** responding, **Then** NetClaw sanitizes the response (e.g., "Interface on the core router is down" instead of revealing the IP)

---

### Edge Cases

- What happens when John's phone is unreachable (no signal, phone off)? System retries once after 2 minutes, then falls back to SMS/Slack notification and logs the failed attempt.
- What happens if multiple emergencies occur simultaneously? System prioritizes by severity, queues calls, and consolidates if appropriate (e.g., "Multiple issues detected: ...").
- What happens when Twilio service is unavailable? System logs the failure, sends Slack/SMS fallback notification, and retries when service recovers.
- How does the system handle call duration limits? Calls are limited to 5 minutes maximum for outbound; inbound conversations can last up to 15 minutes.
- What happens if NetClaw attempts to call outside quiet hours? Calls are blocked during configured quiet hours (e.g., 10 PM - 7 AM) except for P1 emergencies.
- What if the rate limit is exceeded? System queues the call, notifies via Slack that call is delayed, and processes when limit resets.
- What if speech recognition fails to understand John? NetClaw asks for clarification up to 2 times, then suggests using Slack instead.
- What if someone other than John calls the NetClaw number? Caller ID is checked against whitelist; unauthorized callers hear a rejection message and are logged.
- What happens during network outages affecting the voice service? Graceful degradation with SMS/Slack fallback and notification that voice is unavailable.

## Requirements *(mandatory)*

### Functional Requirements - Outbound Calls

- **FR-001**: System MUST only place outbound calls to phone numbers on an approved whitelist
- **FR-002**: System MUST require explicit human approval for all non-emergency outbound calls before dialing
- **FR-003**: System MUST automatically call for pre-approved emergency categories (P1 incidents, critical device failures) without requiring per-call approval
- **FR-004**: System MUST enforce rate limits: maximum 3 outbound calls per hour, maximum 10 per 24-hour period
- **FR-005**: System MUST apply content guardrails to all spoken content (no IP addresses, credentials, customer names, or other sensitive data)
- **FR-006**: System MUST log all call attempts (successful and failed) for audit trail
- **FR-007**: System MUST provide clear text-to-speech output that is understandable at normal speaking pace
- **FR-008**: System MUST support call cancellation during dialing or active call via command
- **FR-009**: System MUST respect quiet hours configuration, blocking non-P1 outbound calls during specified times
- **FR-010**: System MUST integrate with PagerDuty to trigger emergency calls on P1/P2 incidents
- **FR-011**: System MUST fall back to Slack/SMS notification when calls fail after retry
- **FR-012**: System MUST provide status feedback about call success/failure in the originating channel

### Functional Requirements - Inbound Calls

- **FR-013**: System MUST provide a dedicated phone number that John can call to reach NetClaw
- **FR-014**: System MUST authenticate inbound callers via caller ID whitelist before allowing conversation
- **FR-015**: System MUST convert John's speech to text for processing (speech-to-text)
- **FR-016**: System MUST respond to John's questions and commands via voice (text-to-speech)
- **FR-017**: System MUST maintain conversation context throughout the call (remember what was discussed)
- **FR-018**: System MUST require verbal confirmation for any commands that modify network state
- **FR-019**: System MUST gracefully handle speech recognition failures with clarification prompts
- **FR-020**: System MUST reject calls from non-whitelisted numbers with a polite message
- **FR-021**: System MUST log all inbound call conversations for audit trail

### Functional Requirements - Common

- **FR-022**: System MUST configure John's mobile (+1-873-455-0127) as the sole whitelisted phone number for outbound calls and inbound caller authentication

### Key Entities

- **CallRequest**: A request to place a phone call. Contains request_id, phone_number, content_summary, priority (emergency/normal), approval_status, requested_by, requested_at
- **CallRecord**: An audit record of a completed or attempted call. Contains call_id, direction (inbound/outbound), phone_number, duration, status (completed/failed/no-answer), content_spoken, timestamp, triggered_by
- **PhoneWhitelist**: Approved phone numbers for outbound calls and inbound caller authentication. Contains phone_number, label (e.g., "John Mobile"), added_at, can_receive_calls, can_initiate_calls
- **QuietHours**: Time windows when non-emergency outbound calls are blocked. Contains start_time, end_time, timezone, override_for_p1
- **EmergencyCategory**: Pre-approved categories that trigger auto-calls. Contains category_name, description, enabled
- **VoiceConversation**: A record of an inbound voice conversation. Contains conversation_id, caller_number, start_time, end_time, transcript, commands_issued, actions_taken

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Emergency outbound calls are initiated within 60 seconds of triggering event detection
- **SC-002**: 100% of outbound calls are placed only to whitelisted phone numbers (zero unauthorized calls)
- **SC-003**: 100% of non-emergency outbound calls require explicit human approval before dialing
- **SC-004**: Call content is clearly understandable in text-to-speech playback (subjective test by John)
- **SC-005**: Zero instances of sensitive data (IPs, credentials, customer names) spoken in calls
- **SC-006**: All call attempts (inbound and outbound) are logged with full audit trail retrievable
- **SC-007**: Outbound rate limits are enforced with zero violations (max 3/hour, 10/day)
- **SC-008**: System successfully falls back to Slack notification within 5 minutes when outbound calls fail
- **SC-009**: Inbound calls from whitelisted numbers connect and begin conversation within 5 seconds
- **SC-010**: Speech recognition accurately captures John's commands at least 90% of the time
- **SC-011**: 100% of inbound calls from non-whitelisted numbers are rejected

## Assumptions

- John has a valid Twilio account with voice calling capability, a phone number, and sufficient credits
- Default quiet hours are 10:00 PM - 7:00 AM local time for outbound calls, configurable
- P1 incidents from PagerDuty and critical device failures are pre-approved emergency categories
- P2 incidents require explicit approval before outbound calling (not auto-call)
- Text-to-speech will use Twilio's default voice engine (voice selection is configurable)
- SMS fallback uses the same Twilio account/number
- The official @twilio-alpha/mcp NPM package will be used for outbound call initiation
- A webhook server component will handle inbound calls (can run on OpenClaw gateway or separately)
- Speech-to-text will use Twilio's built-in capabilities or integrate with existing Whisper skill
- Memory MCP (feature 033) is available for call logging and audit trail
- DefenseClaw guardrails will be extended to cover voice call tool restrictions
- Inbound calls require a persistent webhook endpoint (HTTP server) to be running

## Clarifications

### Session 2026-06-25

- Q: How many phone numbers should be whitelisted? → A: Single mobile number (simplest approach, can add more later)
- Q: What is John's mobile number for the whitelist? → A: +1-873-455-0127
