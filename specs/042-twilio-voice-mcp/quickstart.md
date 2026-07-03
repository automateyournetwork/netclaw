# Quickstart: Twilio Voice MCP Integration

**Feature**: 042-twilio-voice-mcp
**Date**: 2026-06-25

## Prerequisites

- Twilio account with Voice capability
- Twilio phone number for inbound calls
- API Key SID and Secret (already provided)
- ngrok or Tailscale for webhook public URL
- Memory MCP (feature 033) running

## 1. Environment Setup

Add to `~/.openclaw/.env`:

```bash
# Twilio Credentials (get from https://console.twilio.com)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_KEY_SID=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret_here

# Twilio Phone Number (for inbound calls)
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX

# Webhook URL (update after ngrok/Tailscale setup)
TWILIO_WEBHOOK_URL=https://your-domain.ngrok.io/webhooks/twilio/voice
```

## 2. Install @twilio-alpha/mcp

Add to `~/.openclaw/openclaw.json` under `mcp.servers`:

```json
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
```

## 3. Create Configuration File

Create `config/twilio-voice.json`:

```json
{
  "whitelist": [
    {
      "phone_number": "+18734550127",
      "label": "John Mobile",
      "can_receive_calls": true,
      "can_initiate_calls": true
    }
  ],
  "quiet_hours": [
    {
      "id": "default",
      "start_time": "22:00",
      "end_time": "07:00",
      "timezone": "America/Toronto",
      "p1_override": true,
      "enabled": true
    }
  ],
  "emergency_categories": [
    {
      "category_name": "pagerduty_p1",
      "description": "PagerDuty P1 Critical Incidents",
      "source": "pagerduty",
      "enabled": true
    },
    {
      "category_name": "core_device_down",
      "description": "Core router, firewall, or WAN link failure",
      "source": "netclaw_monitoring",
      "enabled": true
    }
  ],
  "rate_limits": {
    "hourly_max": 3,
    "daily_max": 10
  },
  "voice": "Polly.Matthew"
}
```

## 4. Setup Webhook Server

The twilio-voice-mcp server handles inbound calls:

```bash
# Install dependencies
cd mcp-servers/twilio-voice-mcp
pip install -r requirements.txt

# Start the server (runs on gateway port)
python server.py
```

## 5. Configure Twilio Webhook

In Twilio Console:
1. Go to Phone Numbers → Manage → Active Numbers
2. Select your Twilio number
3. Under "Voice & Fax", set:
   - "A Call Comes In" → Webhook: `https://your-domain/webhooks/twilio/voice`
   - "Call Status Changes" → Webhook: `https://your-domain/webhooks/twilio/voice/status`

## 6. Verify Setup

### Test Outbound Call

```
User: Call me with a test message
NetClaw: [Initiates call to +18734550127 with test message]
```

### Test Inbound Call

1. Call your Twilio number from +18734550127
2. NetClaw should greet you and listen for commands
3. Say "What's my network status?"
4. NetClaw responds with current status

### Test Emergency Call

```
# Simulate P1 incident
User: Simulate a P1 incident for testing voice alerts
NetClaw: [Auto-calls +18734550127 with incident summary]
```

## 7. Troubleshooting

| Issue | Check |
|-------|-------|
| Call not connecting | Verify Twilio credentials in .env |
| Webhook not receiving | Check ngrok/Tailscale URL is accessible |
| Caller rejected | Verify phone number is in whitelist |
| Rate limit hit | Check Memory MCP for recent call count |
| Quiet hours blocking | Check local time vs quiet_hours config |

## Usage Examples

### Request a Status Call
```
"Call me with the network status"
"Phone me about router-1"
"Give me a voice update on the CML lab"
```

### Schedule Update Calls
```
"Call me every 30 minutes with incident updates"
"Set up daily briefing calls at 8 AM"
```

### Inbound Voice Commands
```
"What's the status of my network?"
"Run a health check on the core routers"
"Are there any active incidents?"
```
