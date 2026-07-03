# Quickstart: Full NetClaw Voice Integration

**Feature**: 043-full-voice-integration
**Date**: 2026-06-26

## Prerequisites

1. **Existing Feature 042** - Twilio Voice MCP must be deployed and working
2. **Twilio Account** - With voice capabilities and sufficient credits
3. **ngrok or Public URL** - For webhook endpoint
4. **MCP Servers** - pyATS, CML, GNS3, PagerDuty, RFC, Memory configured

## Quick Setup

### 1. Verify Feature 042 Base

```bash
# Check webhook server is running
curl http://localhost:5001/health

# Check Twilio MCP is registered
grep "twilio" ~/.openclaw/openclaw.json
```

### 2. Configure Caller Whitelist

Create or update `~/.openclaw/voice/whitelist.json`:

```json
{
  "callers": [
    {
      "phone_number": "+15551234567",
      "name": "John",
      "role": "admin",
      "enabled": true,
      "max_call_minutes": 30
    }
  ]
}
```

### 3. Configure Alert Triggers (Optional)

Create `~/.openclaw/voice/alert_triggers.json`:

```json
{
  "triggers": [
    {
      "trigger_id": "pagerduty_critical",
      "name": "Critical PagerDuty Alert",
      "enabled": true,
      "event_source": "pagerduty",
      "event_filter": {
        "priority": "P1"
      },
      "recipient_phone": "+15551234567",
      "message_template": "Critical incident: {title}. {description}",
      "cooldown_minutes": 15
    }
  ]
}
```

### 4. Set Environment Variables

Add to `~/.openclaw/.env`:

```bash
# Twilio (should exist from Feature 042)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+15559876543

# Voice-specific
VOICE_WEBHOOK_URL=https://your-ngrok-url.ngrok-free.app
VOICE_MAX_CALL_MINUTES=30
VOICE_WARN_MINUTES=25
```

### 5. Restart Services

```bash
# Restart webhook server
pkill -f webhook_server.py
cd mcp-servers/twilio-voice-mcp
python webhook_server.py &

# Restart gateway
systemctl --user restart openclaw-gateway.service
```

## Testing

### Basic Voice Call Test

1. Call your Twilio phone number
2. Say: "Check the health of my network"
3. NetClaw should respond with device status

### Lab Management Test

1. Call NetClaw
2. Say: "What labs do I have?"
3. Say: "Start the [lab name]"
4. Verify lab starts in CML

### Context Test

1. Call NetClaw
2. Say: "Check router R1"
3. Say: "What's its uptime?" (should reference R1)
4. Say: "And its BGP neighbors?" (should still reference R1)

### Proactive Alert Test

1. Create a test P1 incident in PagerDuty
2. Verify NetClaw calls your phone
3. Answer and ask follow-up questions

## Troubleshooting

### "Caller not authorized"
- Check whitelist.json has your phone number in E.164 format
- Ensure `enabled: true`

### No response from NetClaw
- Check webhook_server.py is running
- Verify ngrok tunnel is active
- Check Claude API key is valid

### MCP tools not available
- Verify MCP servers are registered in openclaw.json
- Check individual MCP server health

### Speech recognition issues
- Speak clearly and at moderate pace
- Avoid background noise
- Use explicit device/lab names

## Voice Command Cheat Sheet

| Say This | To Do This |
|----------|------------|
| "Check router [name]" | Get device health |
| "BGP neighbors on [device]" | Show BGP table |
| "What labs do I have?" | List CML labs |
| "Start [lab name]" | Boot up a lab |
| "Stop all labs" | Shut down all labs |
| "Any incidents?" | Check PagerDuty |
| "Acknowledge it" | Ack current incident |
| "Look up RFC [number]" | Get RFC summary |
| "Remember that..." | Store a fact |
| "What did we decide about...?" | Recall decision |
| "Summarize what we've found" | Get conversation recap |
