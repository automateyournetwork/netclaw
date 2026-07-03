---
name: grafana-observability
description: "Grafana observability platform — dashboards, Prometheus PromQL, Loki LogQL, alerting, incidents, OnCall schedules, annotations, datasource queries, panel rendering (75+ tools). Use when querying Grafana dashboards, running PromQL for interface metrics, searching Loki logs for syslog events, investigating firing alerts, or checking who is on call."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["uvx"], "env": ["GRAFANA_URL", "GRAFANA_SERVICE_ACCOUNT_TOKEN"] } } }
---

# Grafana Observability

## MCP Server

| Property | Value |
|----------|-------|
| **Source** | [grafana/mcp-grafana](https://github.com/grafana/mcp-grafana) |
| **Transport** | stdio (default), SSE, or streamable-http |
| **Language** | Go (runs via `uvx mcp-grafana`) |
| **Tools** | 75+ (dashboards, Prometheus, Loki, alerting, incidents, OnCall, annotations, admin) |
| **Auth** | Service account token (preferred) or username/password |
| **Requires** | Grafana 9.0+, service account with Editor role or granular RBAC |

## How to Run

```bash
# stdio mode (default — used by NetClaw)
uvx mcp-grafana

# Read-only mode (prevents dashboard/alert modifications)
uvx mcp-grafana --disable-write
```

## Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `GRAFANA_URL` | Yes | `http://grafana.example.com:3000` | Grafana instance URL |
| `GRAFANA_SERVICE_ACCOUNT_TOKEN` | Yes* | `glsa_abc123...` | Service account token (preferred auth) |
| `GRAFANA_USERNAME` | Alt | `admin` | Basic auth username (alternative to token) |
| `GRAFANA_PASSWORD` | Alt | `changeme` | Basic auth password |
| `GRAFANA_ORG_ID` | No | `1` | Organization ID for multi-org setups |

*Either service account token or username/password required.

## Key Tool Categories

### Dashboard Operations

| Tool | What It Does |
|------|-------------|
| `search_dashboards` | Find dashboards by title or metadata |
| `get_dashboard_summary` | Lightweight overview (context-efficient — use this first) |
| `get_dashboard_by_uid` | Full dashboard JSON (large — use sparingly) |
| `get_dashboard_property` | Extract specific fields via JSONPath |
| `get_dashboard_panel_queries` | Extract panel query details |
| `update_dashboard` | Create or modify dashboards |
| `patch_dashboard` | Targeted modifications without full JSON replacement |

### Prometheus (PromQL)

| Tool | What It Does |
|------|-------------|
| `query_prometheus` | Execute instant or range PromQL queries |
| `list_prometheus_metric_names` | Discover available metrics |
| `list_prometheus_label_names` | List labels matching selectors |
| `list_prometheus_label_values` | Retrieve values for a specific label |
| `query_prometheus_histogram` | Calculate percentiles (p50, p90, p95, p99) |
| `list_prometheus_metric_metadata` | Metric type, help text, unit |

### Loki (LogQL)

| Tool | What It Does |
|------|-------------|
| `query_loki_logs` | Execute LogQL queries against log streams |
| `list_loki_label_names` | Discover available log labels |
| `list_loki_label_values` | List values for a specific log label |
| `query_loki_stats` | Stream statistics (volume, rate) |
| `query_loki_patterns` | Detect log structure patterns |

### Alerting

| Tool | What It Does |
|------|-------------|
| `list_alert_rules` | View all Grafana and datasource-managed alert rules |
| `get_alert_rule_by_uid` | Retrieve specific alert rule details |
| `create_alert_rule` | Create new alert rule |
| `update_alert_rule` | Modify existing alert rule |
| `delete_alert_rule` | Remove alert rule |
| `list_contact_points` | View notification endpoints (email, Slack, PagerDuty, etc.) |

### Incident Management

| Tool | What It Does |
|------|-------------|
| `list_incidents` | View Grafana Incidents with filtering |
| `get_incident` | Single incident details |
| `create_incident` | Create a new incident |
| `add_activity_to_incident` | Add timeline entry to incident |

### OnCall

| Tool | What It Does |
|------|-------------|
| `list_oncall_schedules` | View on-call rotation schedules |
| `get_oncall_shift` | Shift details |
| `get_current_oncall_users` | Who is on call right now |
| `list_alert_groups` | OnCall alert groups with filtering |

### Annotations & Rendering

| Tool | What It Does |
|------|-------------|
| `get_annotations` | Query annotations with time/tag filters |
| `create_annotation` | Add annotation to dashboard/panel |
| `get_panel_image` | Render a panel or dashboard as PNG image |
| `generate_deeplink` | Create accurate Grafana URLs for sharing |

### Investigation (Sift)

| Tool | What It Does |
|------|-------------|
| `list_sift_investigations` | List automated investigations |
| `get_sift_investigation` | Investigation details |
| `find_error_pattern_logs` | Detect elevated error patterns in logs |
| `find_slow_requests` | Identify slow requests via Tempo traces |

---

## Workflow: Network Infrastructure Monitoring

When checking network device metrics in Grafana:

1. **Find dashboards**: `search_dashboards` with keyword (e.g., "network", "interface", "BGP")
2. **Dashboard overview**: `get_dashboard_summary` for panel list without full JSON
3. **Query metrics**: `query_prometheus` with PromQL for specific metrics:
   - Interface traffic: `rate(ifHCInOctets{instance="router1"}[5m]) * 8`
   - BGP peer state: `bgp_peer_state{peer="10.1.1.2"}`
   - CPU utilization: `device_cpu_utilization{device="core-rtr-01"}`
   - Interface errors: `increase(ifInErrors{device=~".*"}[1h])`
4. **Check alerts**: `list_alert_rules` to see active alerting thresholds
5. **Search logs**: `query_loki_logs` for syslog or SNMP trap data
6. **Report**: Metrics summary with alert status and log correlation
7. **GAIT**: Record all queries in audit trail

### Example: Interface Utilization Check

```
search_dashboards(title="Network Interfaces")
get_dashboard_summary(uid="abc123")
query_prometheus(expr="rate(ifHCInOctets{device='core-rtr-01'}[5m]) * 8", time_range="1h")
query_prometheus(expr="rate(ifHCOutOctets{device='core-rtr-01'}[5m]) * 8", time_range="1h")
list_alert_rules(folder="Network")
```

## Workflow: Alert Investigation

When investigating Grafana alerts:

1. **List alerts**: `list_alert_rules` — find firing or pending rules
2. **Alert details**: `get_alert_rule_by_uid` — thresholds, conditions, datasource
3. **Query metrics**: `query_prometheus` — check the metric that triggered the alert
4. **Search logs**: `query_loki_logs` — correlate with log events around alert time
5. **Check incidents**: `list_incidents` — is this already tracked?
6. **Contact points**: `list_contact_points` — verify notification routes
7. **Report**: Alert analysis with root cause and metric evidence

## Workflow: Incident Response

When responding to a Grafana incident:

1. **List incidents**: `list_incidents` — find open incidents
2. **Incident details**: `get_incident` — timeline, severity, labels
3. **OnCall**: `get_current_oncall_users` — who should be notified
4. **Correlate metrics**: `query_prometheus` — check affected service metrics
5. **Correlate logs**: `query_loki_logs` — find error patterns around incident time
6. **Investigate**: `find_error_pattern_logs` — automated error pattern detection
7. **Update incident**: `add_activity_to_incident` — add findings to timeline
8. **Annotate**: `create_annotation` — mark event on relevant dashboards

## Workflow: Log Analysis

When investigating network logs stored in Loki:

1. **Discover labels**: `list_loki_label_names` — find available labels (host, severity, facility)
2. **Label values**: `list_loki_label_values` — enumerate hosts, severity levels
3. **Query logs**: `query_loki_logs` with LogQL:
   - By device: `{host="core-rtr-01"}`
   - By severity: `{host="core-rtr-01"} |= "error"`
   - Pattern match: `{job="syslog"} |~ "BGP|OSPF"`
4. **Patterns**: `query_loki_patterns` — detect recurring log structures
5. **Stats**: `query_loki_stats` — log volume and rate analysis

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-health-check** | Cross-reference pyATS health data with Grafana metrics and dashboards |
| **pyats-routing** | Correlate OSPF/BGP state changes with Grafana metric timelines |
| **gait-session-tracking** | Record all Grafana queries and findings in GAIT audit trail |
| **slack-network-alerts** | Grafana alerts fed through Slack + NetClaw for automated investigation |
| **servicenow-change-workflow** | Annotate Grafana dashboards during change windows; correlate incidents with CRs |
| **te-network-monitoring** | Pair ThousandEyes path data with Grafana infrastructure metrics |
| **aws-cloud-monitoring** | Compare Grafana dashboards with CloudWatch data for hybrid visibility |
| **markmap-viz** | Visualize Grafana alert rule hierarchies as mind maps |

---

## Context Window Management

Grafana dashboards can be large JSON documents. Use these strategies:

1. **Always start with `get_dashboard_summary`** — lightweight overview, not full JSON
2. **Use `get_dashboard_property`** with JSONPath for specific fields
3. **Avoid `get_dashboard_by_uid`** unless you need the complete dashboard definition
4. **Use `get_dashboard_panel_queries`** to extract just the query definitions

---

## Important Rules

- **Prefer read-only operations** — use `search_dashboards`, `get_dashboard_summary`, `query_prometheus`, `query_loki_logs`, `list_alert_rules` before any write operations
- **Dashboard modifications require ServiceNow CR** — unless in lab/dev Grafana instance
- **Alert rule changes require approval** — creating/updating/deleting alert rules affects production monitoring
- **Token-efficient queries** — use `get_dashboard_summary` over `get_dashboard_by_uid`, use time ranges to limit Prometheus/Loki result size
- **GAIT audit mandatory** — record all Grafana queries, dashboard modifications, alert changes, and incident updates
- **No secrets in queries** — never embed credentials or sensitive data in PromQL/LogQL expressions

## Error Handling

- **Auth fails (401/403)**: Check `GRAFANA_URL` and `GRAFANA_SERVICE_ACCOUNT_TOKEN` in `~/.openclaw/.env`. Verify service account has Editor role or required RBAC permissions.
- **Datasource not found**: Use `list_datasources` to discover available datasource UIDs and names.
- **PromQL/LogQL errors**: Use `list_prometheus_metric_names` or `list_loki_label_names` to discover valid metric/label names before querying.
- **Dashboard not found**: Use `search_dashboards` to find dashboards by title before using UID-based tools.
- **Rate limiting**: Grafana may rate-limit API requests; space out large query batches.
