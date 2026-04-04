# PagerDuty Incidents Skill

Manage and investigate incidents in PagerDuty.

## Tools

| Tool | Description |
|------|-------------|
| `list_incidents` | List incidents with filters (status, urgency, time range) |
| `get_incident` | Get detailed incident information |
| `get_alert_from_incident` | Get specific alert from an incident |
| `list_alerts_from_incident` | List all alerts associated with an incident |
| `list_incident_notes` | Get notes/timeline from an incident |
| `get_outlier_incident` | Identify anomalous incident patterns |
| `get_past_incidents` | Get historical incidents for pattern analysis |
| `get_related_incidents` | Find related incidents by service or time |
| `create_incident` | Create a new incident (requires write permission) |
| `manage_incidents` | Acknowledge, resolve, or merge incidents |
| `add_note_to_incident` | Add investigation notes to incident |
| `add_responders` | Add additional responders to an incident |

## Example Queries

```
List all triggered incidents
→ list_incidents(statuses=["triggered"])

Get details of a specific incident
→ get_incident(incident_id="P12ABC3")

List incidents for a service in the past hour
→ list_incidents(service_ids=["PSERVICE1"], since="1h")

Get all alerts from an incident
→ list_alerts_from_incident(incident_id="P12ABC3")

Find related incidents to investigate
→ get_related_incidents(incident_id="P12ABC3")
```

## Workflows

### Incident Investigation
1. List triggered incidents: `list_incidents(statuses=["triggered"])`
2. Get incident details: `get_incident(incident_id="...")`
3. Review alerts: `list_alerts_from_incident(incident_id="...")`
4. Check for related incidents: `get_related_incidents(incident_id="...")`
5. Add investigation notes: `add_note_to_incident(incident_id="...", note="...")`

### Network Outage Response
1. List high-urgency incidents: `list_incidents(urgencies=["high"])`
2. Filter by network services: `list_incidents(service_ids=["network-core"])`
3. Acknowledge incident: `manage_incidents(incident_ids=["..."], type="acknowledge")`
4. Check past incidents for patterns: `get_past_incidents(incident_id="...")`
5. Add responders if needed: `add_responders(incident_id="...", responder_ids=["..."])`

### Incident Pattern Analysis
1. Get historical incidents: `list_incidents(since="7d", until="now")`
2. Identify outliers: `get_outlier_incident()`
3. Find related incidents: `get_related_incidents(incident_id="...")`
4. Review notes for root cause: `list_incident_notes(incident_id="...")`

## Prerequisites

- `PAGERDUTY_USER_API_KEY` PagerDuty User API key
- `PAGERDUTY_API_HOST` API host (optional, for EU customers)

## Server

This skill uses the `pagerduty-mcp` server via uvx (stdio transport).

## Notes

- Write operations (create, manage, add_note) require `--enable-write-tools` flag
- NetClaw requires explicit confirmation before modifying incidents
- Incident creation should integrate with ServiceNow CR workflow
