# PagerDuty MCP Tools Contract

**Feature**: 015-pagerduty-mcp-server | **Date**: 2026-04-04

## Overview

This document defines the tool interface contract for the official PagerDuty MCP server integration.

## MCP Server Configuration

```json
{
  "pagerduty-mcp": {
    "command": "uvx",
    "args": ["pagerduty-mcp", "--enable-write-tools"],
    "env": {
      "PAGERDUTY_USER_API_KEY": "${PAGERDUTY_USER_API_KEY}"
    }
  }
}
```

## Tool Catalog by Skill

### pagerduty-incidents (12 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `list_incidents` | read | status?, urgency?, service_ids?, since?, until?, limit? | Array of incidents |
| `get_incident` | read | id | Incident details |
| `get_alert_from_incident` | read | incident_id, alert_id | Alert details |
| `list_alerts_from_incident` | read | incident_id | Array of alerts |
| `list_incident_notes` | read | incident_id | Array of notes |
| `get_outlier_incident` | read | incident_id | Outlier analysis |
| `get_past_incidents` | read | incident_id | Related past incidents |
| `get_related_incidents` | read | incident_id | Related current incidents |
| `create_incident` | write | title, service_id, urgency?, body? | Created incident |
| `manage_incidents` | write | ids, action (acknowledge/resolve) | Updated incidents |
| `add_note_to_incident` | write | incident_id, content | Created note |
| `add_responders` | write | incident_id, responder_ids | Added responders |

### pagerduty-oncall (9 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `list_oncalls` | read | schedule_ids?, escalation_policy_ids?, since?, until? | Array of on-calls |
| `get_schedule` | read | id | Schedule details |
| `list_schedules` | read | query?, limit? | Array of schedules |
| `list_schedule_users` | read | schedule_id, since?, until? | Users on schedule |
| `get_escalation_policy` | read | id | Policy details |
| `list_escalation_policies` | read | query?, limit? | Array of policies |
| `create_schedule` | write | name, time_zone, schedule_layers | Created schedule |
| `update_schedule` | write | id, schedule_layers? | Updated schedule |
| `create_schedule_override` | write | schedule_id, user_id, start, end | Created override |

### pagerduty-services (4 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `get_service` | read | id | Service details |
| `list_services` | read | query?, team_ids?, limit? | Array of services |
| `create_service` | write | name, escalation_policy_id, description? | Created service |
| `update_service` | write | id, name?, description?, status? | Updated service |

### pagerduty-orchestration (7 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `get_event_orchestration` | read | id | Orchestration details |
| `get_event_orchestration_global` | read | orchestration_id | Global rules |
| `get_event_orchestration_router` | read | orchestration_id | Router rules |
| `get_event_orchestration_service` | read | service_id | Service rules |
| `list_event_orchestrations` | read | limit? | Array of orchestrations |
| `update_event_orchestration_router` | write | orchestration_id, rules | Updated router |
| `append_event_orchestration_router_rule` | write | orchestration_id, rule | Appended rule |

## Additional Tools (38 tools)

These tools are available but not assigned to specific skills:

### Teams (7 tools)
- `get_team`, `list_teams`, `list_team_members` (read)
- `create_team`, `update_team`, `delete_team`, `add_team_member`, `remove_team_member` (write)

### Users (2 tools)
- `get_user_data`, `list_users` (read)

### Log Entries (2 tools)
- `get_log_entry`, `list_log_entries` (read)

### Change Events (4 tools)
- `get_change_event`, `list_change_events`, `list_incident_change_events`, `list_service_change_events` (read)

### Incident Workflows (3 tools)
- `get_incident_workflow`, `list_incident_workflows` (read)
- `start_incident_workflow` (write)

### Alert Grouping (5 tools)
- `get_alert_grouping_setting`, `list_alert_grouping_settings` (read)
- `create_alert_grouping_setting`, `update_alert_grouping_setting`, `delete_alert_grouping_setting` (write)

### Status Pages (8 tools)
- `get_status_page_post`, `list_status_page_impacts`, `list_status_page_post_updates`, `list_status_page_severities`, `list_status_page_statuses`, `list_status_pages` (read)
- `create_status_page_post`, `create_status_page_post_update` (write)

## Error Responses

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad Request | Invalid parameters |
| 401 | Unauthorized | Invalid API key |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Rate Limited | Too many requests |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PAGERDUTY_USER_API_KEY` | Yes | User API Token from PagerDuty settings |
| `PAGERDUTY_API_HOST` | No | API host (default: api.pagerduty.com) |
