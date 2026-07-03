# Research: Twilio Voice MCP Integration

**Feature**: 042-twilio-voice-mcp
**Date**: 2026-06-25

## Research Tasks

### 1. @twilio-alpha/mcp Package Capabilities

**Question**: What tools does @twilio-alpha/mcp provide and how to configure it for voice calls?

**Decision**: Use @twilio-alpha/mcp with service filter `twilio_api_v2010` and tag `Api20100401Call`

**Rationale**:
- Official Twilio MCP package supports ~2000 endpoints
- Filtering to `twilio_api_v2010` service limits to core voice/SMS APIs
- Tag `Api20100401Call` further restricts to call-specific operations
- NPM package runs via `npx -y @twilio-alpha/mcp` with credential string

**Configuration**:
```json
{
  "twilio-mcp": {
    "command": "npx",
    "args": [
      "-y",
      "@twilio-alpha/mcp",
      "${TWILIO_ACCOUNT_SID}/${TWILIO_API_KEY_SID}:${TWILIO_API_SECRET}",
      "--services", "twilio_api_v2010",
      "--tags", "Api20100401Call,Api20100401Message"
    ]
  }
}
```

**Alternatives Considered**:
- Custom Twilio SDK integration: More work, less maintained
- twilio-docs MCP: Read-only documentation, doesn't execute calls

---

### 2. Inbound Call Webhook Architecture

**Question**: How to handle inbound calls where John calls NetClaw?

**Decision**: Custom FastMCP webhook server using Twilio Media Streams for real-time audio

**Rationale**:
- Twilio sends HTTP POST to webhook when call arrives
- TwiML response controls call flow
- Media Streams (WebSocket) enables real-time bidirectional audio
- Can integrate with Whisper API for STT and Twilio TTS for responses

**Architecture**:
```
John's Phone → Twilio → Webhook (HTTP POST) → TwiML Response
                     ↓
              Media Stream (WebSocket) ←→ FastMCP Server
                     ↓
              Whisper STT → Claude → Twilio TTS
```

**Alternatives Considered**:
- Twilio `<Gather>` with speech input: Limited to single utterances, no conversation flow
- Third-party voice AI (Retell, Vapi): Additional vendor dependency, cost
- Twilio Conversation Relay: Requires additional Twilio add-on subscription

---

### 3. Speech-to-Text Integration

**Question**: Which STT service to use for inbound voice transcription?

**Decision**: Use existing openai-whisper-api skill with streaming support

**Rationale**:
- Already configured in NetClaw with API key
- Whisper has excellent accuracy (>95% for English)
- Supports streaming for real-time transcription
- Cost-effective ($0.006/minute)

**Alternatives Considered**:
- Twilio Speech Recognition: Built-in but less accurate for technical terms
- Deepgram: Fast but requires new vendor setup
- Google Cloud Speech: Good accuracy but complex setup

---

### 4. Text-to-Speech for Responses

**Question**: Which TTS service to use for NetClaw voice responses?

**Decision**: Use Twilio's built-in `<Say>` TwiML verb with Polly voices

**Rationale**:
- No additional API calls needed - TwiML handles it
- Amazon Polly voices available (e.g., "Polly.Matthew" for male, "Polly.Joanna" for female)
- Neural voices sound natural
- Integrated into call flow without latency

**Configuration**:
```xml
<Response>
  <Say voice="Polly.Matthew">Hello John, this is NetClaw.</Say>
</Response>
```

**Alternatives Considered**:
- OpenAI TTS: Higher quality but requires streaming audio back to Twilio
- ElevenLabs: Best quality but expensive, complex integration
- Google Cloud TTS: Good but adds vendor dependency

---

### 5. Content Guardrails Implementation

**Question**: How to filter sensitive data from voice content?

**Decision**: Regex-based sanitization + Claude pre-processing

**Rationale**:
- IP addresses: Regex `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}` → "an IP address"
- Credentials: Pattern matching for API keys, passwords → "[redacted]"
- Customer names: Named entity recognition or explicit blocklist
- Claude can summarize technical output without revealing sensitive details

**Implementation**:
```python
def sanitize_for_voice(text: str) -> str:
    # Replace IPs
    text = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'an IP address', text)
    # Replace MACs
    text = re.sub(r'([0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}', 'a MAC address', text)
    # Replace common credential patterns
    text = re.sub(r'(password|secret|key|token)\s*[:=]\s*\S+', r'\1: [redacted]', text, flags=re.I)
    return text
```

**Alternatives Considered**:
- No filtering: Security risk
- Full NER processing: Overkill for this use case, adds latency

---

### 6. Rate Limiting Strategy

**Question**: How to enforce call rate limits (3/hour, 10/day)?

**Decision**: In-memory counter with Memory MCP persistence for cross-session tracking

**Rationale**:
- Track outbound calls in Memory MCP with timestamps
- Check before each call initiation
- Window-based counting: hourly and daily buckets
- Emergency (P1) calls can override but still count against limit

**Implementation**:
```python
async def check_rate_limit() -> tuple[bool, str]:
    hour_ago = datetime.now() - timedelta(hours=1)
    day_ago = datetime.now() - timedelta(days=1)

    # Query Memory MCP for recent calls
    hourly_calls = await memory.query_facts(
        category="voice_call",
        since=hour_ago.isoformat()
    )
    daily_calls = await memory.query_facts(
        category="voice_call",
        since=day_ago.isoformat()
    )

    if len(hourly_calls) >= 3:
        return False, "Hourly rate limit reached (3/hour)"
    if len(daily_calls) >= 10:
        return False, "Daily rate limit reached (10/day)"
    return True, "OK"
```

---

### 7. Quiet Hours Enforcement

**Question**: How to block calls during quiet hours (10 PM - 7 AM)?

**Decision**: Time-based check with timezone awareness and P1 override

**Rationale**:
- Store quiet hours config in twilio-voice.json
- Check local time before initiating outbound calls
- P1 emergencies bypass quiet hours
- Log all quiet hours blocks for audit

**Configuration**:
```json
{
  "quiet_hours": {
    "start": "22:00",
    "end": "07:00",
    "timezone": "America/Toronto",
    "p1_override": true
  }
}
```

---

### 8. Webhook Hosting Requirements

**Question**: Where to host the inbound call webhook?

**Decision**: Run webhook server on OpenClaw gateway with ngrok/Tailscale for public access

**Rationale**:
- Gateway already runs 24/7
- Can use existing ngrok setup (webex webhooks already use it)
- Alternatively, Tailscale funnel for stable URL
- No additional server infrastructure needed

**Configuration**:
```json
{
  "webhook": {
    "path": "/webhooks/twilio/voice",
    "port": 18789,
    "public_url": "https://netclaw.tail12345.ts.net/webhooks/twilio/voice"
  }
}
```

**Alternatives Considered**:
- Dedicated cloud function: More reliable but adds infrastructure
- Twilio Functions: Limited to Twilio's runtime, can't access NetClaw tools

---

## Summary of Decisions

| Area | Decision | Key Dependency |
|------|----------|----------------|
| Outbound calls | @twilio-alpha/mcp | NPM, Twilio account |
| Inbound calls | Custom FastMCP webhook | Twilio Media Streams |
| Speech-to-Text | OpenAI Whisper API | Existing skill |
| Text-to-Speech | Twilio Polly voices | TwiML |
| Content filtering | Regex + Claude | Python, guardrails.py |
| Rate limiting | Memory MCP tracking | Feature 033 |
| Quiet hours | Config-based | twilio-voice.json |
| Webhook hosting | Gateway + ngrok/Tailscale | Existing infrastructure |
