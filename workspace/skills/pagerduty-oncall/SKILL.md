---
name: pagerduty-oncall
description: "Manage on-call schedules and escalation policies in PagerDuty."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# PagerDuty On-Call Skill

Manage on-call schedules and escalation policies in PagerDuty.

## Tools

| Tool | Description |
|------|-------------|
| `list_oncalls` | List current on-call users across schedules |
| `get_schedule` | Get detailed schedule information |
| `list_schedules` | List all on-call schedules |
| `list_schedule_users` | List users assigned to a schedule |
| `get_escalation_policy` | Get escalation policy details |
| `list_escalation_policies` | List all escalation policies |
| `create_schedule` | Create a new on-call schedule (requires write) |
| `update_schedule` | Update an existing schedule (requires write) |
| `create_schedule_override` | Create a schedule override (requires write) |

## Example Queries

```
Who is on-call right now?
→ list_oncalls()

Get on-call for a specific schedule
→ list_oncalls(schedule_ids=["PSCHD123"])

List all schedules
→ list_schedules()

Get escalation policy details
→ get_escalation_policy(escalation_policy_id="PESCL456")

Create an override for vacation coverage
→ create_schedule_override(schedule_id="...", user_id="...", start="...", end="...")
```

## Workflows

### On-Call Visibility
1. List current on-calls: `list_oncalls()`
2. Get schedule details: `get_schedule(schedule_id="...")`
3. Review escalation policy: `get_escalation_policy(escalation_policy_id="...")`
4. Identify coverage gaps

### Shift Handoff
1. List current on-calls: `list_oncalls()`
2. Get schedule for next shift: `list_schedule_users(schedule_id="...")`
3. Review active incidents before handoff
4. Document handoff notes in incident

### Schedule Override (Vacation Coverage)
1. Get schedule details: `get_schedule(schedule_id="...")`
2. Identify coverage period
3. Create override: `create_schedule_override(schedule_id="...", user_id="...", start="...", end="...")`
4. Verify override applied: `list_oncalls(since="...", until="...")`

### Escalation Review
1. List all escalation policies: `list_escalation_policies()`
2. Get policy details: `get_escalation_policy(escalation_policy_id="...")`
3. Review escalation levels and timeouts
4. Identify gaps in coverage

## Prerequisites

- `PAGERDUTY_USER_API_KEY` PagerDuty User API key
- `PAGERDUTY_API_HOST` API host (optional, for EU customers)

## Server

This skill uses the `pagerduty-mcp` server via uvx (stdio transport).

## Notes

- Write operations (create/update schedule, overrides) require `--enable-write-tools`
- Schedule changes should be communicated to affected team members
- Overrides are useful for planned absences (vacation, training)
