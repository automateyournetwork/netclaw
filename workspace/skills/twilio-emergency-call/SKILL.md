# Twilio Emergency Call Skill

**Feature**: 042-twilio-voice-mcp
**Priority**: P1 (MVP)
**User Story**: US1 - Emergency Alert Calls

## Purpose

Automatically call John when critical network events occur (P1 incidents, core device failures). Emergency calls bypass quiet hours and are auto-approved without user confirmation.

## Trigger Conditions

This skill activates when:

1. **PagerDuty P1 Incident**
   - Source: `pagerduty`
   - Match: `severity:P1`
   - Auto-approved: Yes

2. **Core Device Down**
   - Source: `netclaw_monitoring`
   - Match: `device_type:(core_router|firewall|wan_link) AND status:down`
   - Auto-approved: Yes

## Workflow

```
Event Detected
    │
    ├─► Check Emergency Category
    │       └─► Not emergency? → Skip call
    │
    ├─► Pre-call Validation
    │       ├─► Rate limit check (warning only for emergencies)
    │       └─► Get whitelist target
    │
    ├─► Sanitize Message
    │       └─► Remove IPs, credentials, sensitive data
    │
    ├─► Initiate Call via Twilio
    │       └─► Uses @twilio-alpha/mcp Api20100401Call
    │
    ├─► Log to Memory MCP
    │       └─► CallRecord with trigger_id
    │
    └─► Fallback on Failure
            └─► T018: SMS or Slack notification
```

## Tool Usage

### Primary Tool

```json
{
  "tool": "twilio_voice_emergency_call",
  "arguments": {
    "source": "pagerduty",
    "event_data": {
      "severity": "P1",
      "incident_id": "PD12345",
      "summary": "Core router LAX-CORE-01 is unreachable"
    }
  }
}
```

### Manual Emergency Call

```json
{
  "tool": "twilio_voice_call",
  "arguments": {
    "to": "[WHITELIST_NUMBER]",
    "message": "Emergency: Core router is down. BGP sessions lost on LAX-CORE-01.",
    "priority": "emergency"
  }
}
```

## Message Templates

### P1 Incident

```
NetClaw Emergency Alert.
PagerDuty Priority 1 Incident.
{incident_summary}.
Incident ID: {incident_id}.
```

### Core Device Down

```
NetClaw Emergency Alert.
Core device failure detected.
{device_name} is {status}.
Last seen: {last_seen}.
```

## Configuration

See `config/twilio-voice.json`:

```json
{
  "emergency_categories": [
    {
      "category_name": "pagerduty_p1",
      "source": "pagerduty",
      "match_pattern": "severity:P1",
      "enabled": true
    },
    {
      "category_name": "core_device_down",
      "source": "netclaw_monitoring",
      "match_pattern": "device_type:(core_router|firewall|wan_link) AND status:down",
      "enabled": true
    }
  ]
}
```

## Retry Logic

On call failure:

1. Wait 30 seconds
2. Retry (attempt 2)
3. Wait 60 seconds
4. Retry (attempt 3)
5. Fallback to SMS/Slack

```python
retry_config = {
    "max_retries": 3,
    "backoff_base_seconds": 30,
    "backoff_multiplier": 2
}
```

## Fallback Notifications

If all call attempts fail:

1. **SMS via Twilio** (if configured)
2. **Slack notification** to alerts channel
3. **Log failure** to Memory MCP

## Guardrails

- **Rate Limits**: Logged but not blocking for emergencies
- **Quiet Hours**: Bypassed (p1_override: true)
- **Whitelist**: Must be in whitelist (no exceptions)
- **Content**: IPs and credentials sanitized

## Example Scenarios

### Scenario 1: PagerDuty P1 Alert

```
Input:
  - PagerDuty webhook received
  - Severity: P1
  - Summary: "Database primary node unresponsive"

Action:
  1. Event matches pagerduty_p1 category
  2. Call initiated to [WHITELIST_NUMBER]
  3. Voice message: "NetClaw Emergency Alert. PagerDuty Priority 1 Incident. Database primary node unresponsive."
  4. Call logged to Memory MCP
```

### Scenario 2: Core Router Down

```
Input:
  - NetClaw monitoring detects
  - device_type: core_router
  - status: down
  - device_name: CHI-CORE-02

Action:
  1. Event matches core_device_down category
  2. Call initiated to [WHITELIST_NUMBER]
  3. Voice message: "NetClaw Emergency Alert. Core device failure detected. CHI-CORE-02 is down."
```

## Integration Points

- **PagerDuty MCP**: Triggers emergency calls on P1 incidents
- **Memory MCP**: Stores all call records
- **Slack MCP**: Fallback notification
- **@twilio-alpha/mcp**: Call initiation

## Success Criteria

- [ ] P1 incident triggers call within 60 seconds
- [ ] Call logged to Memory MCP with incident ID
- [ ] Quiet hours bypassed for emergencies
- [ ] Retry logic works on failure
- [ ] Fallback notification sent after max retries
