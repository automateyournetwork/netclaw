# Twilio Inbound Voice Skill

**Feature**: 042-twilio-voice-mcp
**Priority**: P2
**User Stories**: US5 (Inbound Conversations), US6 (Voice Commands)

## Purpose

Enable John to call NetClaw's Twilio number and have a bidirectional voice conversation for status queries and network commands.

## Trigger Conditions

This skill activates when:

1. **Inbound Call Received**
   - Call from whitelisted number ([WHITELIST_NUMBER])
   - Caller ID authenticated

## Architecture

```
John's Phone
    │
    ▼
Twilio (Inbound Call)
    │
    ▼
Webhook: POST /webhooks/twilio/voice
    │
    ├─► Authenticate Caller ID
    │       └─► Not whitelisted? → Reject with message
    │
    ├─► Generate Greeting TwiML
    │       └─► "Hello John, this is NetClaw. How can I help?"
    │
    └─► Start Media Stream
            │
            ▼
    WebSocket: /webhooks/twilio/media-stream
            │
            ├─► Audio In → Whisper STT → Text
            │
            ├─► Text → Claude → Response
            │
            └─► Response → Twilio TTS → Audio Out
```

## Workflow

### Inbound Call Flow

```
Call Arrives at Twilio Number
    │
    ├─► Twilio sends webhook to NetClaw
    │
    ├─► Authenticate caller against whitelist
    │       └─► Rejected? → Play rejection message, hangup
    │
    ├─► Play greeting via TwiML <Say>
    │
    ├─► Connect Media Stream for real-time audio
    │
    ├─► [Loop] Conversation
    │       │
    │       ├─► Receive audio chunk
    │       │
    │       ├─► Transcribe via Whisper API
    │       │
    │       ├─► Process query/command
    │       │       └─► Network queries, status checks, commands
    │       │
    │       ├─► Generate response
    │       │
    │       └─► Speak via Twilio TTS
    │
    └─► On hangup: Log conversation to Memory MCP
```

## Webhook Endpoints

### POST /webhooks/twilio/voice

Initial call handler - returns TwiML.

**Request**: Twilio form-encoded data (CallSid, From, To, etc.)

**Response** (authenticated):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew">Hello John, this is NetClaw. How can I help you?</Say>
  <Connect>
    <Stream url="wss://your-server/webhooks/twilio/media-stream" />
  </Connect>
</Response>
```

**Response** (rejected):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew">This number is not authorized to call NetClaw. Goodbye.</Say>
  <Hangup />
</Response>
```

### WebSocket /webhooks/twilio/media-stream

Real-time bidirectional audio stream.

**Inbound Events**:
- `start`: Call connected, media format info
- `media`: Audio chunk (mulaw, 8kHz, base64)
- `stop`: Call ended

**Outbound Events**:
- `media`: Response audio chunk

## Voice Commands (US6)

John can issue network commands during the call:

### Query Commands (Safe)
- "What's the status of my network?"
- "Are there any active incidents?"
- "Show me BGP neighbors on router-1"
- "What's the CPU on the firewall?"

### Action Commands (Require Confirmation)
- "Run a health check on the core routers"
- "Restart the monitoring agent"
- "Clear the interface counters"

### Confirmation Flow

```
John: "Restart the monitoring agent"
NetClaw: "You want me to restart the monitoring agent. Say 'yes' to confirm or 'no' to cancel."
John: "Yes"
NetClaw: "Restarting monitoring agent... Done. Agent is now running."
```

## Guardrails

- **Caller ID Authentication**: Must be in whitelist
- **Content Sanitization**: Response sanitized before TTS
- **Command Confirmation**: Impactful actions require verbal "yes"
- **Session Timeout**: Max 15 minutes per call
- **Logging**: Full transcript logged to Memory MCP

## Message Templates

### Greeting

```
Hello John, this is NetClaw. How can I help you?
```

### Status Response

```
Your network status:
{device_count} devices monitored.
{healthy_count} operational.
{incident_count} active incidents.
Would you like more details?
```

### Confirmation Request

```
You want me to {action_description}.
Say 'yes' to confirm or 'no' to cancel.
```

### Error Response

```
I'm sorry, I couldn't complete that request.
Error: {error_summary}.
Would you like to try something else?
```

### Goodbye

```
Goodbye John. This conversation has been logged.
```

## Integration Points

- **Twilio Media Streams**: Real-time audio
- **OpenAI Whisper API**: Speech-to-text
- **Twilio TTS**: Text-to-speech (Polly voices)
- **Memory MCP**: Conversation logging
- **All MCP servers**: Query execution

## Security

1. **Signature Validation**: All webhooks validated via Twilio signature
2. **Whitelist Authentication**: Caller ID must be whitelisted
3. **Content Sanitization**: No IPs, credentials in spoken output
4. **Audit Trail**: Full transcript logged

## Example Conversation

```
[Call connects]
NetClaw: "Hello John, this is NetClaw. How can I help you?"

John: "What's the status of my network?"

NetClaw: "Your network status: 47 devices monitored. 45 operational,
         2 with warnings. No active incidents. The warnings are on
         switch-3 and ap-lobby-1 due to high memory usage."

John: "Run a health check on switch-3"

NetClaw: "You want me to run a health check on switch-3.
         Say 'yes' to confirm or 'no' to cancel."

John: "Yes"

NetClaw: "Running health check on switch-3...
         Check complete. CPU: 23%, Memory: 78%,
         All interfaces up. The high memory is within normal range."

John: "Thanks, goodbye"

NetClaw: "Goodbye John. This conversation has been logged."
[Call ends]
```

## Success Criteria

- [ ] Inbound calls authenticated within 5 seconds
- [ ] Unauthorized callers rejected with message
- [ ] Voice queries answered accurately
- [ ] Commands require verbal confirmation
- [ ] Full transcript logged to Memory MCP
- [ ] Max 15-minute call duration enforced
