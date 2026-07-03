# Webhook API Contract: Twilio Voice

**Feature**: 042-twilio-voice-mcp
**Date**: 2026-06-25

## Overview

This document defines the HTTP webhook endpoints that Twilio calls when voice events occur.

---

## Endpoints

### POST /webhooks/twilio/voice

Called when an inbound call arrives or needs TwiML instructions.

**Request Headers**:
```
Content-Type: application/x-www-form-urlencoded
X-Twilio-Signature: <signature for validation>
```

**Request Body** (form-encoded):
| Field | Type | Description |
|-------|------|-------------|
| CallSid | string | Unique call identifier |
| AccountSid | string | Twilio account SID |
| From | string | Caller's phone number (E.164) |
| To | string | Called number (E.164) |
| CallStatus | string | `ringing`, `in-progress`, `completed`, `busy`, `no-answer`, `canceled`, `failed` |
| Direction | string | `inbound` or `outbound-api` |
| CallerName | string | Caller ID name (if available) |

**Response** (for inbound calls - authenticated):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew">Hello John, this is NetClaw. How can I help you?</Say>
  <Connect>
    <Stream url="wss://your-server/media-stream" />
  </Connect>
</Response>
```

**Response** (for inbound calls - rejected):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Matthew">This number is not authorized. Goodbye.</Say>
  <Hangup />
</Response>
```

**Status Codes**:
- `200 OK`: TwiML response returned
- `400 Bad Request`: Invalid request format
- `403 Forbidden`: Signature validation failed

---

### POST /webhooks/twilio/voice/status

Called when call status changes (completion callback).

**Request Body** (form-encoded):
| Field | Type | Description |
|-------|------|-------------|
| CallSid | string | Unique call identifier |
| CallStatus | string | Final status |
| CallDuration | integer | Duration in seconds |
| RecordingUrl | string | URL of recording (if enabled) |
| Timestamp | string | ISO 8601 timestamp |

**Response**:
```json
{
  "acknowledged": true
}
```

**Status Codes**:
- `200 OK`: Status recorded
- `400 Bad Request`: Invalid request

---

### WebSocket /webhooks/twilio/media-stream

Real-time audio stream for inbound conversations.

**Connection**: Initiated by Twilio's `<Connect><Stream>` TwiML

**Inbound Messages** (from Twilio):
```json
{
  "event": "media",
  "streamSid": "MZ123...",
  "media": {
    "track": "inbound",
    "chunk": "1",
    "timestamp": "1234567890",
    "payload": "<base64 encoded audio>"
  }
}
```

**Outbound Messages** (to Twilio):
```json
{
  "event": "media",
  "streamSid": "MZ123...",
  "media": {
    "payload": "<base64 encoded audio response>"
  }
}
```

**Control Messages**:
```json
// Start event
{
  "event": "start",
  "streamSid": "MZ123...",
  "start": {
    "accountSid": "AC123...",
    "callSid": "CA123...",
    "tracks": ["inbound"],
    "mediaFormat": {
      "encoding": "audio/x-mulaw",
      "sampleRate": 8000,
      "channels": 1
    }
  }
}

// Stop event
{
  "event": "stop",
  "streamSid": "MZ123..."
}
```

---

## MCP Tool Contracts

### twilio_voice_call

Initiate an outbound voice call.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "to": {
      "type": "string",
      "description": "Phone number to call (E.164 format)",
      "pattern": "^\\+[1-9]\\d{1,14}$"
    },
    "message": {
      "type": "string",
      "description": "Message to speak (will be sanitized)",
      "maxLength": 1000
    },
    "priority": {
      "type": "string",
      "enum": ["emergency", "normal"],
      "default": "normal"
    }
  },
  "required": ["to", "message"]
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "success": { "type": "boolean" },
    "call_sid": { "type": "string" },
    "status": { "type": "string" },
    "message": { "type": "string" }
  }
}
```

---

### twilio_voice_check_rate_limit

Check if a call can be made within rate limits.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {},
  "required": []
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "allowed": { "type": "boolean" },
    "hourly_remaining": { "type": "integer" },
    "daily_remaining": { "type": "integer" },
    "next_available": { "type": "string", "format": "date-time" }
  }
}
```

---

### twilio_voice_get_call_history

Retrieve call history from Memory MCP.

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "direction": {
      "type": "string",
      "enum": ["inbound", "outbound", "all"],
      "default": "all"
    },
    "since": {
      "type": "string",
      "format": "date-time",
      "description": "Filter calls after this timestamp"
    },
    "limit": {
      "type": "integer",
      "default": 10,
      "maximum": 100
    }
  }
}
```

**Output Schema**:
```json
{
  "type": "object",
  "properties": {
    "calls": {
      "type": "array",
      "items": { "$ref": "#/definitions/CallRecord" }
    },
    "total": { "type": "integer" }
  }
}
```

---

## Security

### Signature Validation

All webhook requests MUST be validated using Twilio's signature:

```python
from twilio.request_validator import RequestValidator

validator = RequestValidator(auth_token)
is_valid = validator.validate(
    request_url,
    request.form,
    request.headers.get('X-Twilio-Signature', '')
)
```

### Caller Authentication

Inbound calls MUST check caller ID against whitelist before proceeding:

```python
async def authenticate_caller(from_number: str) -> bool:
    whitelist = load_whitelist()
    for entry in whitelist:
        if entry['phone_number'] == from_number and entry['can_initiate_calls']:
            return True
    return False
```
