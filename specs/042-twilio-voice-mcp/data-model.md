# Data Model: Twilio Voice MCP Integration

**Feature**: 042-twilio-voice-mcp
**Date**: 2026-06-25

## Entities

### CallRequest

A request to initiate an outbound phone call.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| request_id | string | Unique identifier (UUID) | Required, auto-generated |
| phone_number | string | E.164 format target number | Required, must be in whitelist |
| content_summary | string | What to say in the call | Required, max 1000 chars |
| priority | enum | `emergency` or `normal` | Required |
| approval_status | enum | `pending`, `approved`, `rejected` | Required |
| requested_by | string | Source of request (slack, cli, pagerduty) | Required |
| requested_at | datetime | ISO 8601 timestamp | Required, auto-set |
| approved_at | datetime | When approval was granted | Null until approved |

**State Transitions**:
```
[created] → pending → approved → (call initiated)
                   → rejected → (end)
```

**Emergency Exception**: If `priority=emergency`, transitions directly from `created` to `approved`.

---

### CallRecord

Audit record of a completed or attempted call.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| call_id | string | Unique identifier (UUID) | Required, auto-generated |
| twilio_call_sid | string | Twilio's call SID | Set after call initiated |
| direction | enum | `inbound` or `outbound` | Required |
| phone_number | string | E.164 format | Required |
| duration_seconds | integer | Call length | 0 for failed calls |
| status | enum | `completed`, `failed`, `no-answer`, `busy`, `rejected` | Required |
| content_spoken | string | Sanitized transcript of what was said | Optional |
| transcript | string | Full conversation transcript (inbound calls) | Optional |
| timestamp | datetime | When call was initiated | Required |
| ended_at | datetime | When call ended | Null if ongoing |
| triggered_by | string | What caused the call | Required |
| trigger_id | string | Incident ID, command, or schedule name | Optional |
| retry_count | integer | Number of retry attempts | Default 0 |

**Indexes**: `direction`, `timestamp`, `status`, `triggered_by`

---

### PhoneWhitelist

Approved phone numbers for outbound calls and inbound authentication.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| phone_number | string | E.164 format | Required, unique |
| label | string | Human-readable name | Required |
| can_receive_calls | boolean | Allowed for outbound | Default true |
| can_initiate_calls | boolean | Allowed for inbound auth | Default true |
| added_at | datetime | When added to whitelist | Required |
| added_by | string | Who added it | Required |

**Initial Data**:
```json
{
  "phone_number": "+18734550127",
  "label": "John Mobile",
  "can_receive_calls": true,
  "can_initiate_calls": true,
  "added_at": "2026-06-25T00:00:00Z",
  "added_by": "initial_config"
}
```

---

### QuietHours

Time windows when non-emergency outbound calls are blocked.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| id | string | Unique identifier | Required |
| start_time | string | HH:MM format | Required, valid time |
| end_time | string | HH:MM format | Required, valid time |
| timezone | string | IANA timezone | Required |
| days_of_week | array | 0-6 (Sun-Sat), empty = all days | Optional |
| p1_override | boolean | P1 emergencies bypass | Default true |
| enabled | boolean | Is this rule active | Default true |

**Default Configuration**:
```json
{
  "id": "default",
  "start_time": "22:00",
  "end_time": "07:00",
  "timezone": "America/Toronto",
  "days_of_week": [],
  "p1_override": true,
  "enabled": true
}
```

---

### EmergencyCategory

Pre-approved event categories that trigger auto-calls.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| category_name | string | Unique category identifier | Required, unique |
| description | string | Human-readable description | Required |
| source | string | Where events come from | Required |
| match_pattern | string | Regex or exact match | Required |
| enabled | boolean | Is auto-call active | Default true |

**Initial Categories**:
```json
[
  {
    "category_name": "pagerduty_p1",
    "description": "PagerDuty P1 Critical Incidents",
    "source": "pagerduty",
    "match_pattern": "severity:P1",
    "enabled": true
  },
  {
    "category_name": "core_device_down",
    "description": "Core router, firewall, or WAN link failure",
    "source": "netclaw_monitoring",
    "match_pattern": "device_type:(core_router|firewall|wan_link) AND status:down",
    "enabled": true
  }
]
```

---

### VoiceConversation

Record of an inbound voice conversation with NetClaw.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| conversation_id | string | Unique identifier (UUID) | Required |
| twilio_call_sid | string | Twilio's call SID | Required |
| caller_number | string | E.164 format | Required |
| caller_label | string | From whitelist lookup | Optional |
| start_time | datetime | When call connected | Required |
| end_time | datetime | When call ended | Null if ongoing |
| duration_seconds | integer | Total call length | Calculated |
| transcript | array | Ordered list of utterances | Required |
| commands_issued | array | List of commands requested | Optional |
| actions_taken | array | List of actions performed | Optional |
| auth_status | enum | `authenticated`, `rejected` | Required |

**Transcript Entry Structure**:
```json
{
  "speaker": "john" | "netclaw",
  "timestamp": "2026-06-25T10:30:45Z",
  "text": "What's the status of router-1?",
  "confidence": 0.95
}
```

---

### RateLimitState

Tracking for rate limit enforcement.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| window_type | enum | `hourly` or `daily` | Required |
| window_start | datetime | Start of current window | Required |
| call_count | integer | Calls in this window | Default 0 |
| last_updated | datetime | When count was updated | Required |

**Note**: Stored in Memory MCP for persistence across sessions.

---

## Relationships

```
CallRequest (1) → (0..1) CallRecord
                         ↓ creates on completion

PhoneWhitelist (1) ← validates → (many) CallRequest
               (1) ← validates → (many) CallRecord
               (1) ← validates → (many) VoiceConversation

EmergencyCategory (1) → triggers → (many) CallRequest (auto-approved)

QuietHours (many) → blocks → (many) CallRequest (non-emergency)

VoiceConversation (1) → contains → (many) Transcript Entries
                   (1) → logs to → (1) CallRecord
```

---

## Storage Strategy

| Entity | Storage | Retention |
|--------|---------|-----------|
| CallRequest | Memory MCP | 30 days |
| CallRecord | Memory MCP | 90 days |
| PhoneWhitelist | twilio-voice.json | Permanent |
| QuietHours | twilio-voice.json | Permanent |
| EmergencyCategory | twilio-voice.json | Permanent |
| VoiceConversation | Memory MCP | 90 days |
| RateLimitState | Memory MCP | Rolling window |

---

## Configuration File Schema

**File**: `config/twilio-voice.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "properties": {
    "whitelist": {
      "type": "array",
      "items": { "$ref": "#/definitions/PhoneWhitelist" }
    },
    "quiet_hours": {
      "type": "array",
      "items": { "$ref": "#/definitions/QuietHours" }
    },
    "emergency_categories": {
      "type": "array",
      "items": { "$ref": "#/definitions/EmergencyCategory" }
    },
    "rate_limits": {
      "type": "object",
      "properties": {
        "hourly_max": { "type": "integer", "default": 3 },
        "daily_max": { "type": "integer", "default": 10 }
      }
    },
    "twilio_phone_number": {
      "type": "string",
      "description": "Twilio number for inbound calls"
    },
    "webhook_url": {
      "type": "string",
      "description": "Public URL for Twilio webhooks"
    },
    "voice": {
      "type": "string",
      "default": "Polly.Matthew",
      "description": "TTS voice to use"
    }
  }
}
```
