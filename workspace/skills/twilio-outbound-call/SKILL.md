# Twilio Outbound Call Skill

**Feature**: 042-twilio-voice-mcp
**Priority**: P2
**User Stories**: US2 (On-Demand), US3 (Situation Updates)

## Purpose

Enable John to request on-demand phone calls for network status updates and schedule periodic update calls during ongoing incidents.

## Trigger Conditions

This skill activates when:

1. **Explicit Request**
   - "Call me with network status"
   - "Phone me about router-1"
   - "Give me a voice update"

2. **Scheduled Updates**
   - "Call me every 30 minutes with incident updates"
   - During active incidents when updates are needed

## Workflows

### On-Demand Status Call (US2)

```
User Request → "Call me with network status"
    │
    ├─► Gather Network Status
    │       └─► Query relevant MCP servers
    │
    ├─► Generate Voice Summary
    │       └─► Concise status overview
    │
    ├─► Pre-call Validation
    │       ├─► Rate limit check
    │       ├─► Quiet hours check
    │       └─► Whitelist validation
    │
    ├─► Sanitize Content
    │       └─► Remove IPs, credentials
    │
    └─► Initiate Call via Twilio
```

### Scheduled Update Calls (US3)

```
Schedule Request → "Call me every 30 minutes"
    │
    ├─► Register Schedule in Memory MCP
    │       └─► Store interval, incident_id
    │
    ├─► [Loop] On Schedule Trigger
    │       │
    │       ├─► Check Incident Status
    │       │       └─► Resolved? → Cancel schedule
    │       │
    │       ├─► Check for Changes
    │       │       └─► No updates? → Skip call
    │       │
    │       └─► Initiate Status Call
    │
    └─► Critical Change Detection
            └─► Immediate call on: resolved, escalated
```

## Tool Usage

### On-Demand Call

```json
{
  "tool": "twilio_voice_call",
  "arguments": {
    "to": "[WHITELIST_NUMBER]",
    "message": "Network status update. All 47 devices are operational. No active incidents. BGP sessions healthy.",
    "priority": "normal"
  }
}
```

### Check Before Calling

```json
{
  "tool": "twilio_voice_check_rate_limit",
  "arguments": {}
}
```

### Check Quiet Hours

```json
{
  "tool": "twilio_voice_check_quiet_hours",
  "arguments": {
    "priority": "normal"
  }
}
```

## Message Templates

### Network Status Summary

```
Network status update.
{device_count} devices monitored.
{healthy_count} healthy, {warning_count} warnings, {critical_count} critical.
{active_incidents} active incidents.
Most recent: {recent_event}.
```

### Device-Specific Status

```
Status for {device_name}.
Device type: {device_type}.
State: {operational_state}.
CPU: {cpu_percent}%, Memory: {mem_percent}%.
Uptime: {uptime}.
```

### Incident Update

```
Update on incident {incident_id}.
Status: {status}.
Duration: {duration}.
Affected: {affected_services}.
Latest update: {update_summary}.
```

## Guardrails

- **Rate Limits**: Enforced (3/hour, 10/day)
- **Quiet Hours**: Respected (10 PM - 7 AM)
- **Whitelist**: Required
- **Content**: IPs, credentials sanitized
- **Approval**: Implicit (user requested)

## Configuration

```json
{
  "scheduled_calls": {
    "max_interval_minutes": 60,
    "min_interval_minutes": 15,
    "auto_cancel_on_resolve": true,
    "skip_if_no_changes": true
  }
}
```

## Example Scenarios

### Scenario 1: On-Demand Status

```
User: "Call me with the network status"

Action:
  1. Check rate limits (OK)
  2. Check quiet hours (OK)
  3. Gather status from MCP servers
  4. Generate summary: "47 devices operational, no incidents"
  5. Sanitize content
  6. Initiate call to [WHITELIST_NUMBER]
```

### Scenario 2: Scheduled Updates

```
User: "Call me every 30 minutes about incident INC12345"

Action:
  1. Register schedule in Memory MCP
  2. Every 30 minutes:
     a. Check if incident resolved → Cancel if yes
     b. Check for status changes → Skip if none
     c. Generate update message
     d. Initiate call
  3. On incident resolve → Final call + cancel schedule
```

## Integration Points

- **Memory MCP**: Schedule storage, call history
- **PagerDuty MCP**: Incident status
- **pyATS MCP**: Device status
- **NetBox MCP**: Inventory data
- **@twilio-alpha/mcp**: Call initiation

## Success Criteria

- [ ] On-demand calls work within 30 seconds
- [ ] Scheduled calls fire at correct intervals
- [ ] Calls skipped when no status changes
- [ ] Schedule auto-cancels on incident resolution
- [ ] Rate limits respected
- [ ] Quiet hours respected
