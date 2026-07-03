# Twilio Daily Briefing Skill

**Feature**: 042-twilio-voice-mcp
**Priority**: P3
**User Story**: US4 - Daily Check-in Calls

## Purpose

Provide optional daily phone briefings at a scheduled time with overnight event summaries.

## Trigger Conditions

This skill activates when:

1. **Scheduled Time** (e.g., 8 AM daily)
   - If `daily_briefing.enabled: true` in config
   - Integrated with NetClaw heartbeat system

2. **Manual Request**
   - "Give me my daily briefing"
   - "What happened overnight?"

## Configuration

In `config/twilio-voice.json`:

```json
{
  "daily_briefing": {
    "enabled": false,
    "time": "08:00",
    "timezone": "America/Toronto",
    "days": [1, 2, 3, 4, 5],
    "include_quiet_nights": true
  }
}
```

### Configuration Options

| Option | Type | Description |
|--------|------|-------------|
| `enabled` | boolean | Enable/disable daily briefings |
| `time` | string | HH:MM format in local timezone |
| `timezone` | string | IANA timezone (e.g., "America/Toronto") |
| `days` | array | Days of week (0=Sun, 1=Mon, ..., 6=Sat) |
| `include_quiet_nights` | boolean | Call even if nothing happened overnight |

## Workflow

```
Heartbeat Trigger at Scheduled Time
    │
    ├─► Check if daily_briefing.enabled
    │       └─► Disabled? → Skip
    │
    ├─► Check day of week
    │       └─► Not scheduled? → Skip
    │
    ├─► Gather Overnight Events
    │       ├─► PagerDuty incidents (since last briefing)
    │       ├─► Device alerts
    │       ├─► Configuration changes
    │       └─► Security events
    │
    ├─► Generate Briefing Content
    │       ├─► Events found → Summary of events
    │       └─► No events → "All clear" message
    │
    ├─► Pre-call Validation
    │       └─► Rate limit, whitelist
    │
    └─► Initiate Briefing Call
```

## Message Templates

### Briefing with Events

```
Good morning John, this is your NetClaw daily briefing.

Overnight summary:
{incident_count} incidents occurred.
{resolved_count} resolved, {active_count} still active.

Top events:
{event_1_summary}.
{event_2_summary}.

{device_health_summary}.

Have a great day.
```

### All Clear Briefing

```
Good morning John, this is your NetClaw daily briefing.

All quiet overnight. No incidents, no alerts.
All {device_count} devices are operational.

Have a great day.
```

### Skipped (Nothing to Report)

If `include_quiet_nights: false` and no events:
- No call is made
- Logged as "skipped - no events"

## Tool Usage

### Enable Daily Briefings

```json
{
  "action": "update_config",
  "path": "daily_briefing.enabled",
  "value": true
}
```

### Manual Briefing Request

```json
{
  "tool": "twilio_voice_call",
  "arguments": {
    "to": "+18734550127",
    "message": "[Generated daily briefing content]",
    "priority": "normal"
  }
}
```

## Integration Points

- **Heartbeat System**: Triggers at scheduled time
- **PagerDuty MCP**: Overnight incident data
- **Memory MCP**: Event history, call logging
- **pyATS MCP**: Device health summary
- **@twilio-alpha/mcp**: Call initiation

## Guardrails

- **Rate Limits**: Counts toward daily limit
- **Quiet Hours**: Not applicable (scheduled during work hours)
- **Whitelist**: Required
- **Content**: Sanitized as always

## Example Scenarios

### Scenario 1: Busy Night

```
Time: 8:00 AM Monday
Events Overnight:
  - 2 PagerDuty incidents (1 resolved, 1 active)
  - 3 device alerts (all auto-resolved)

Briefing:
"Good morning John. Overnight summary: 2 incidents occurred.
The P2 on core-router-1 is resolved. There's still an active P3
on switch-floor-2 for high CPU. 3 device alerts auto-resolved.
All 47 devices are currently operational. Have a great day."
```

### Scenario 2: Quiet Night

```
Time: 8:00 AM Tuesday
Events Overnight: None

Briefing (include_quiet_nights: true):
"Good morning John. All quiet overnight. No incidents, no alerts.
All 47 devices are operational. Have a great day."

Briefing (include_quiet_nights: false):
[No call made - logged as skipped]
```

### Scenario 3: Weekend Skip

```
Time: 8:00 AM Saturday
Config: days: [1, 2, 3, 4, 5]  # Monday-Friday only

Action: No call made (weekend)
```

## Heartbeat Integration

The daily briefing integrates with NetClaw's heartbeat system:

```python
# In heartbeat_cycle:
if is_daily_briefing_time():
    await trigger_daily_briefing()
```

## Success Criteria

- [ ] Briefing calls at configured time
- [ ] Correct day-of-week filtering
- [ ] Accurate overnight event summary
- [ ] "All clear" message for quiet nights
- [ ] Optional skip when no events
- [ ] Enable/disable via config
