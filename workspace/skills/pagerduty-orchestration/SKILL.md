# PagerDuty Orchestration Skill

Manage event orchestration and routing rules in PagerDuty.

## Tools

| Tool | Description |
|------|-------------|
| `get_event_orchestration` | Get orchestration details |
| `get_event_orchestration_global` | Get global orchestration settings |
| `get_event_orchestration_router` | Get router rules for an orchestration |
| `get_event_orchestration_service` | Get service-specific orchestration |
| `list_event_orchestrations` | List all event orchestrations |
| `update_event_orchestration_router` | Update router rules (requires write) |
| `append_event_orchestration_router_rule` | Add a new router rule (requires write) |

## Example Queries

```
List all event orchestrations
→ list_event_orchestrations()

Get orchestration details
→ get_event_orchestration(orchestration_id="E1ABCD23")

Get router rules
→ get_event_orchestration_router(orchestration_id="E1ABCD23")

Get global orchestration settings
→ get_event_orchestration_global(orchestration_id="E1ABCD23")
```

## Workflows

### Event Routing Review
1. List orchestrations: `list_event_orchestrations()`
2. Get orchestration details: `get_event_orchestration(orchestration_id="...")`
3. Review router rules: `get_event_orchestration_router(orchestration_id="...")`
4. Check service-specific rules: `get_event_orchestration_service(orchestration_id="...", service_id="...")`

### Add Network Event Routing Rule
1. List current orchestrations: `list_event_orchestrations()`
2. Get current router rules: `get_event_orchestration_router(orchestration_id="...")`
3. Append new rule: `append_event_orchestration_router_rule(orchestration_id="...", rule={...})`
4. Verify rule added: `get_event_orchestration_router(orchestration_id="...")`

### Event Suppression Setup
1. Get global orchestration: `get_event_orchestration_global(orchestration_id="...")`
2. Review existing suppression rules
3. Add suppression rule for maintenance window
4. Verify: `get_event_orchestration_global(orchestration_id="...")`

### Routing Audit
1. List all orchestrations: `list_event_orchestrations()`
2. For each orchestration, get router rules
3. Document routing logic and destinations
4. Identify gaps or misconfigurations

## Prerequisites

- `PAGERDUTY_USER_API_KEY` PagerDuty User API key
- `PAGERDUTY_API_HOST` API host (optional, for EU customers)

## Server

This skill uses the `pagerduty-mcp` server via uvx (stdio transport).

## Notes

- Write operations (update/append rules) require `--enable-write-tools`
- Event orchestration changes affect all incoming events
- Test routing changes in a non-production orchestration first
- Document all routing rule changes in GAIT audit trail
