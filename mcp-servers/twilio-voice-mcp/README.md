# Twilio Voice MCP Server

**Features**: 042-twilio-voice-mcp, 043-full-voice-integration

Universal voice interface for NetClaw using Twilio. **Voice is just I/O** - Claude already has access to ALL 40+ MCPs and 100+ skills via voice.

## Overview

This MCP server provides:
- **Universal Voice Access**: ANY NetClaw capability accessible via voice
- **Inbound Call Handling**: Webhook endpoints for Twilio voice callbacks
- **Proactive Alerts**: Outbound calls for critical events (PagerDuty, Datadog, etc.)
- **Per-Caller Context**: Conversation history persisted via Memory MCP
- **Speech Formatting**: Natural speech output (no UUIDs, IPs spoken naturally)
- **Call Logging**: All calls logged to Memory MCP for audit trail
- **Guardrails**: Rate limiting, quiet hours, whitelist validation, content sanitization

## Architecture

```
Phone → Twilio STT → Claude (ALL 40+ MCPs) → Speech Formatter → Twilio TTS → Phone
```

Voice is a universal I/O channel. Claude already knows how to:
- Query IP Fabric, Forward Networks, Itential
- Open ServiceNow tickets
- Generate Blender diagrams
- Check CML/GNS3 labs
- Query PagerDuty incidents
- And everything else...

## Tools

| Tool | Description |
|------|-------------|
| `twilio_voice_call` | Initiate outbound call with message |
| `twilio_voice_check_rate_limit` | Check if call allowed within limits |
| `twilio_voice_get_call_history` | Retrieve call records from Memory MCP |

## Webhook Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhooks/twilio/voice` | POST | Inbound call handler (TwiML) |
| `/webhooks/twilio/voice/process-command` | POST | Process voice commands |
| `/webhooks/twilio/voice/status` | POST | Call status callback |
| `/webhooks/twilio/voice/alert-call` | POST | Handle outbound alert calls |
| `/webhooks/twilio/voice/trigger-alert` | POST | API to trigger outbound alerts |
| `/webhooks/twilio/media-stream` | WebSocket | Real-time audio stream |
| `/health` | GET | Health check with integration status |

## Configuration

### Voice Config (~/.openclaw/voice/)

**whitelist.json** - Authorized callers:
```json
{
  "callers": [
    {"phone_number": "+15551234567", "name": "John", "role": "admin", "enabled": true}
  ],
  "settings": {"default_max_call_minutes": 30}
}
```

**alert_triggers.json** - Proactive alert config:
```json
{
  "triggers": [
    {
      "trigger_id": "pagerduty_critical",
      "event_source": "pagerduty",
      "event_filter": {"priority": "P1"},
      "recipient_phone": "+15551234567",
      "message_template": "Critical incident: {title}",
      "cooldown_minutes": 15
    }
  ]
}
```

### Legacy Config (config/twilio-voice.json)
- `whitelist`: Approved phone numbers (E.164 format)
- `quiet_hours`: Time windows blocking non-emergency calls
- `emergency_categories`: Auto-approved call triggers
- `rate_limits`: Hourly/daily call limits
- `voice`: TTS voice (default: Polly.Matthew)

## Environment Variables

Required in `~/.openclaw/.env`:
```bash
# Twilio credentials
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_API_KEY_SID=SKxxxxx
TWILIO_API_SECRET=xxxxx
TWILIO_PHONE_NUMBER=+1xxxxx

# Voice settings
VOICE_WEBHOOK_URL=https://your-domain/webhooks/twilio/voice
VOICE_MAX_CALL_MINUTES=30
VOICE_WARN_MINUTES=25

# Claude for universal tool access
ANTHROPIC_API_KEY=sk-ant-xxxxx
```

## Quick Start

```bash
# Install dependencies
cd mcp-servers/twilio-voice-mcp
pip install -r requirements.txt

# Start server (runs webhook handler)
python server.py
```

## Security

- All webhook requests validated via Twilio signature
- Inbound callers authenticated against whitelist
- Content sanitized (IPs, credentials filtered from TTS)
- Rate limits enforced per hour/day
- Quiet hours block non-emergency calls

## Voice Command Examples

| Say This | What Happens |
|----------|--------------|
| "Check my CML labs" | Lists all CML lab status |
| "Start the BGP lab" | Starts the specified lab |
| "Any PagerDuty incidents?" | Lists active incidents |
| "Open a ServiceNow ticket for the BGP issue" | Creates a ticket |
| "Show the path from site A to site B" | Queries Forward Networks |
| "Generate a network mind map" | Creates Blender diagram |
| "Remember that R1 has the BGP issue" | Stores fact in memory |
| "What did we discuss last time?" | Recalls previous context |

## Files

| File | Purpose |
|------|---------|
| `webhook_server.py` | Main Flask server with universal voice handler |
| `speech_formatter.py` | Format responses for natural speech |
| `context_manager.py` | Per-caller conversation context |
| `alert_triggers.py` | Proactive outbound call management |
| `guardrails.py` | Security: whitelist, rate limits, sanitization |
| `server.py` | MCP server with voice tools |

## Related

- Feature 042 Spec: `/specs/042-twilio-voice-mcp/spec.md`
- Feature 043 Spec: `/specs/043-full-voice-integration/spec.md`
- Quickstart: `/specs/043-full-voice-integration/quickstart.md`
- Skills: `/workspace/skills/twilio-*/`
- Voice Config: `~/.openclaw/voice/`
