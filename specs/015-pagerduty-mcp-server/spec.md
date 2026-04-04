# Feature Specification: PagerDuty MCP Server Integration

**Feature ID**: 015-pagerduty-mcp-server
**Status**: Draft
**Created**: 2026-04-04

## Overview

Integrate the official PagerDuty MCP server to provide incident management capabilities within NetClaw. This closes the loop on the ServiceNow CR workflow by enabling direct incident creation, escalation, and resolution.

## Source

- **Repository**: https://github.com/PagerDuty/pagerduty-mcp-server
- **Type**: Official (PagerDuty-maintained)
- **License**: Apache-2.0
- **Transport**: stdio (uvx) or Docker

## Tools Available (70 total)

### Read-Only Tools (Always Available)

| Category | Tools |
|----------|-------|
| **Incidents** | get_incident, list_incidents, get_alert_from_incident, list_alerts_from_incident, list_incident_notes, get_outlier_incident, get_past_incidents, get_related_incidents |
| **Services** | get_service, list_services |
| **Escalation Policies** | get_escalation_policy, list_escalation_policies |
| **Schedules** | get_schedule, list_schedules, list_schedule_users |
| **On-Call** | list_oncalls |
| **Teams** | get_team, list_teams, list_team_members |
| **Users** | get_user_data, list_users |
| **Log Entries** | get_log_entry, list_log_entries |
| **Change Events** | get_change_event, list_change_events, list_incident_change_events, list_service_change_events |
| **Event Orchestrations** | get_event_orchestration, get_event_orchestration_global, get_event_orchestration_router, get_event_orchestration_service, list_event_orchestrations |
| **Incident Workflows** | get_incident_workflow, list_incident_workflows |
| **Alert Grouping** | get_alert_grouping_setting, list_alert_grouping_settings |
| **Status Pages** | get_status_page_post, list_status_page_impacts, list_status_page_post_updates, list_status_page_severities, list_status_page_statuses, list_status_pages |

### Write Tools (Requires --enable-write-tools)

| Category | Tools |
|----------|-------|
| **Incidents** | create_incident, manage_incidents, add_note_to_incident, add_responders |
| **Services** | create_service, update_service |
| **Schedules** | create_schedule, update_schedule, create_schedule_override |
| **Teams** | create_team, update_team, delete_team, add_team_member, remove_team_member |
| **Event Orchestrations** | update_event_orchestration_router, append_event_orchestration_router_rule |
| **Incident Workflows** | start_incident_workflow |
| **Alert Grouping** | create_alert_grouping_setting, update_alert_grouping_setting, delete_alert_grouping_setting |
| **Status Pages** | create_status_page_post, create_status_page_post_update |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PAGERDUTY_USER_API_KEY` | Yes | PagerDuty User API Token |
| `PAGERDUTY_API_HOST` | No | API endpoint (default: https://api.pagerduty.com, EU: https://api.eu.pagerduty.com) |

## User Stories

### US1: Incident Visibility (Priority: P1) MVP
**As a** network engineer using NetClaw
**I want to** query active PagerDuty incidents
**So that** I can understand current operational issues affecting the network

**Acceptance Criteria:**
- Can list all active incidents with severity, status, and assigned responders
- Can filter incidents by service, urgency, or status
- Can view incident timeline and notes

### US2: On-Call Awareness (Priority: P1) MVP
**As a** network engineer
**I want to** see who is on-call for network services
**So that** I know who to escalate issues to

**Acceptance Criteria:**
- Can list current on-call engineers by escalation policy
- Can view schedule rotations
- Can identify coverage gaps

### US3: Incident Creation (Priority: P2)
**As a** network engineer detecting an issue
**I want to** create a PagerDuty incident from NetClaw
**So that** I can immediately alert the appropriate team

**Acceptance Criteria:**
- Can create incident with title, description, service, and urgency
- Incident triggers appropriate escalation policy
- Requires ServiceNow CR approval for production services (ITSM gating)

### US4: Event Orchestration (Priority: P3)
**As a** network operations manager
**I want to** view and manage event orchestration rules
**So that** I can understand how alerts are routed and suppressed

**Acceptance Criteria:**
- Can list event orchestration configurations
- Can view routing rules and conditions
- Write operations require explicit approval

## Proposed Skills

| Skill | Tools | Description |
|-------|-------|-------------|
| `pagerduty-incidents` | 8 | Incident visibility, timeline, notes, related incidents |
| `pagerduty-oncall` | 6 | On-call schedules, escalation policies, coverage |
| `pagerduty-services` | 4 | Service catalog and health status |
| `pagerduty-orchestration` | 5 | Event routing and alert grouping configuration |

## Integration Points

- **ServiceNow**: CR approval for write operations on production services
- **Slack/WebEx**: Cross-reference incidents with alert channels
- **Grafana**: Correlate incidents with metric anomalies

## Clarifications

### Session 2026-04-04
- Q: Write tools enablement policy? → A: Enable write tools by default (all 70 tools available)

## Security Considerations

- Write tools enabled by default (--enable-write-tools flag set)
- Write operations on production services gated by ServiceNow CR workflow
- API key stored in .env, never logged

## Success Criteria

1. Can query "show active PagerDuty incidents" and get formatted results
2. Can query "who is on-call for network-core?" and get responder info
3. Integration appears in NetClaw UI with correct tool count
4. All 4 skills documented with SKILL.md files
