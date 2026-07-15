---
name: pagerduty-services
description: "Manage service catalog and service health in PagerDuty."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# PagerDuty Services Skill

Manage service catalog and service health in PagerDuty.

## Tools

| Tool | Description |
|------|-------------|
| `get_service` | Get detailed service information |
| `list_services` | List all services with optional filters |
| `create_service` | Create a new service (requires write permission) |
| `update_service` | Update service configuration (requires write permission) |

## Example Queries

```
List all services
→ list_services()

Get details of a specific service
→ get_service(service_id="PSVCS123")

List network-related services
→ list_services(query="network")

Get service with integrations
→ get_service(service_id="...", include=["integrations"])
```

## Workflows

### Service Catalog Review
1. List all services: `list_services()`
2. Get service details: `get_service(service_id="...")`
3. Review integration keys and escalation policies
4. Verify service-to-team mappings

### Service Health Assessment
1. List services by team: `list_services(team_ids=["..."])`
2. Get service status: `get_service(service_id="...")`
3. Check active incidents per service
4. Review service dependencies

### New Service Onboarding
1. Review existing services: `list_services()`
2. Identify appropriate escalation policy
3. Create service: `create_service(name="...", escalation_policy_id="...")`
4. Configure integrations (manual step)
5. Verify service: `get_service(service_id="...")`

### Service Configuration Update
1. Get current service config: `get_service(service_id="...")`
2. Review escalation policy and alert settings
3. Update service: `update_service(service_id="...", ...)`
4. Verify changes: `get_service(service_id="...")`

## Prerequisites

- `PAGERDUTY_USER_API_KEY` PagerDuty User API key
- `PAGERDUTY_API_HOST` API host (optional, for EU customers)

## Server

This skill uses the `pagerduty-mcp` server via uvx (stdio transport).

## Notes

- Write operations (create/update service) require `--enable-write-tools`
- Service creation should follow your organization's naming conventions
- Always associate services with appropriate escalation policies
