# Data Model: PagerDuty MCP Server Integration

**Feature**: 015-pagerduty-mcp-server | **Date**: 2026-04-04

## Overview

This is a stateless MCP server integration. The PagerDuty MCP server acts as a proxy to the PagerDuty REST API. No local data storage is required.

## External Entities (PagerDuty API)

### Incident

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique incident identifier |
| incident_number | integer | Human-readable incident number |
| title | string | Incident title |
| description | string | Detailed description |
| status | enum | triggered, acknowledged, resolved |
| urgency | enum | high, low |
| created_at | datetime | Creation timestamp |
| escalation_policy | object | Associated escalation policy |
| service | object | Affected service |
| assignments | array | Current assignees |
| teams | array | Associated teams |
| alert_counts | object | Triggered/resolved alert counts |

### Service

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique service identifier |
| name | string | Service name |
| description | string | Service description |
| status | enum | active, warning, critical, maintenance, disabled |
| escalation_policy | object | Default escalation policy |
| teams | array | Owning teams |
| integrations | array | Connected integrations |

### Schedule

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique schedule identifier |
| name | string | Schedule name |
| time_zone | string | Timezone for schedule |
| schedule_layers | array | Rotation layers |
| final_schedule | object | Computed final schedule |
| escalation_policies | array | Policies using this schedule |

### Escalation Policy

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique policy identifier |
| name | string | Policy name |
| escalation_rules | array | Ordered escalation rules |
| num_loops | integer | Number of escalation loops |
| services | array | Services using this policy |
| teams | array | Associated teams |

### On-Call

| Field | Type | Description |
|-------|------|-------------|
| escalation_policy | object | Policy reference |
| escalation_level | integer | Current level |
| schedule | object | Associated schedule |
| user | object | On-call user |
| start | datetime | On-call period start |
| end | datetime | On-call period end |

### Event Orchestration

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique orchestration identifier |
| name | string | Orchestration name |
| description | string | Description |
| routes | integer | Number of routing rules |
| integrations | array | Connected integrations |
| team | object | Owning team |

### User

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique user identifier |
| name | string | Display name |
| email | string | Email address |
| role | enum | User role in PagerDuty |
| teams | array | Team memberships |
| contact_methods | array | Contact information |

## Relationships

```
┌──────────────────┐       ┌─────────────────────┐
│     Service      │───────│  Escalation Policy  │
└──────────────────┘       └─────────────────────┘
         │                          │
         │                          │
         ▼                          ▼
┌──────────────────┐       ┌─────────────────────┐
│     Incident     │       │      Schedule       │
└──────────────────┘       └─────────────────────┘
         │                          │
         │                          │
         ▼                          ▼
┌──────────────────┐       ┌─────────────────────┐
│      Alert       │       │       On-Call       │
└──────────────────┘       └─────────────────────┘
                                    │
                                    │
                                    ▼
                           ┌─────────────────────┐
                           │        User         │
                           └─────────────────────┘
```

## State Transitions

### Incident Lifecycle

```
[triggered] ──acknowledge──> [acknowledged] ──resolve──> [resolved]
     │                             │
     └──────────resolve────────────┘
```

### Service Status

```
[active] ──degradation──> [warning] ──failure──> [critical]
    │                         │                      │
    └────maintenance─────────────────────────────────┘
                              │
                              ▼
                        [maintenance]
```

## No Local Storage

This integration does not persist any data locally. All state is maintained by PagerDuty's API.
