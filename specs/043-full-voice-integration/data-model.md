# Data Model: Full NetClaw Voice Integration

**Feature**: 043-full-voice-integration
**Date**: 2026-06-26

## Entities

### VoiceSession

Represents an active phone call with NetClaw.

| Field | Type | Description |
|-------|------|-------------|
| session_id | string | Unique identifier (Twilio Call SID) |
| caller_id | string | Phone number of caller (E.164 format) |
| caller_name | string | Display name from whitelist (optional) |
| start_time | datetime | UTC timestamp when call started |
| end_time | datetime | UTC timestamp when call ended (null if active) |
| status | enum | `active`, `completed`, `timeout`, `error` |
| transcript | list[TranscriptEntry] | Full conversation transcript |
| context | ConversationContext | Current conversation state |
| tool_calls | list[ToolCallRecord] | MCP tools invoked during session |

**Lifecycle**:
```
INITIATED → ACTIVE → (COMPLETED | TIMEOUT | ERROR)
```

### TranscriptEntry

A single turn in the conversation.

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | When this entry was recorded |
| speaker | enum | `user`, `assistant` |
| text | string | Transcribed speech (user) or response text (assistant) |
| confidence | float | Speech recognition confidence (0-1, user only) |
| audio_url | string | URL to audio recording (optional) |

### ConversationContext

Per-caller session state persisted to Memory MCP.

| Field | Type | Description |
|-------|------|-------------|
| caller_id | string | Phone number (primary key) |
| current_device | string | Currently focused device name (optional) |
| current_lab | string | Currently focused lab name (optional) |
| current_interface | string | Currently focused interface (optional) |
| recent_findings | list[Finding] | Last 10 findings from queries |
| conversation_summary | string | Rolling summary of conversation |
| last_updated | datetime | When context was last modified |

**Persistence**: Stored in Memory MCP with key `voice_context_{caller_id}`

### Finding

A discrete piece of information discovered during the call.

| Field | Type | Description |
|-------|------|-------------|
| timestamp | datetime | When discovered |
| category | enum | `health`, `config`, `incident`, `memory`, `other` |
| summary | string | Brief description |
| details | dict | Full structured data |
| source_tool | string | MCP tool that produced this |

### ToolCallRecord

Audit record of an MCP tool invocation.

| Field | Type | Description |
|-------|------|-------------|
| call_id | string | Unique identifier |
| timestamp | datetime | When tool was called |
| tool_name | string | MCP tool name |
| parameters | dict | Input parameters |
| result | dict | Tool response |
| duration_ms | int | Execution time |
| success | bool | Whether call succeeded |

### AlertTrigger

Configuration for proactive outbound alerts.

| Field | Type | Description |
|-------|------|-------------|
| trigger_id | string | Unique identifier |
| name | string | Human-readable name |
| enabled | bool | Whether trigger is active |
| event_source | enum | `pagerduty`, `pyats`, `cml`, `custom` |
| event_filter | dict | Conditions that match events |
| recipient_phone | string | Phone number to call (E.164) |
| message_template | string | Template for alert message |
| cooldown_minutes | int | Minimum time between alerts |
| last_triggered | datetime | When last fired (null if never) |

### CallerWhitelist

Authorized callers for voice access.

| Field | Type | Description |
|-------|------|-------------|
| phone_number | string | E.164 format phone number |
| name | string | Display name |
| role | enum | `admin`, `operator`, `readonly` |
| enabled | bool | Whether caller is active |
| added_at | datetime | When added to whitelist |
| max_call_minutes | int | Per-call duration limit (default 30) |

## Relationships

```
CallerWhitelist 1──* VoiceSession (caller_id)
VoiceSession 1──* TranscriptEntry
VoiceSession 1──1 ConversationContext
VoiceSession 1──* ToolCallRecord
AlertTrigger *──1 CallerWhitelist (recipient_phone)
ConversationContext 1──* Finding
```

## Storage Strategy

| Entity | Storage | Retention |
|--------|---------|-----------|
| VoiceSession | Memory MCP | 30 days |
| TranscriptEntry | Memory MCP (with session) | 30 days |
| ConversationContext | Memory MCP | Indefinite (per caller) |
| ToolCallRecord | Memory MCP (with session) | 30 days |
| AlertTrigger | JSON config file | Permanent |
| CallerWhitelist | JSON config file | Permanent |

## Validation Rules

1. **caller_id** must be valid E.164 phone number
2. **session_id** must be valid Twilio Call SID format
3. **max_call_minutes** must be between 1 and 60
4. **cooldown_minutes** must be at least 5
5. **ConversationContext.recent_findings** limited to 10 entries (FIFO)

## State Transitions

### VoiceSession Status

```
INITIATED: Call received, not yet answered
    ↓ (answer)
ACTIVE: Call in progress, processing commands
    ↓ (hangup)         ↓ (30 min)        ↓ (error)
COMPLETED          TIMEOUT            ERROR
```

### AlertTrigger Lifecycle

```
CREATED → ENABLED → TRIGGERED → COOLDOWN → ENABLED
                        ↑                      │
                        └──────────────────────┘
```
