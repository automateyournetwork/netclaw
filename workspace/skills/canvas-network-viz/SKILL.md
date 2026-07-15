---
name: canvas-network-viz
description: "Canvas/A2UI inline network visualizations — topology maps, health dashboards, alert cards, change timelines, config diffs, path traces, and health scorecards rendered directly in the OpenClaw chat interface. Consumes existing MCP server data (pyATS, Grafana, Prometheus, ServiceNow, SuzieQ, Batfish) and outputs A2UI JSON for Canvas rendering. Use when the operator asks to see a network map, device dashboard, alert summary, change request timeline, config diff, forwarding path trace, or health scorecard."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": [], "env": [] } } }
---

# Canvas Network Visualization

## Overview

This skill renders inline network visualizations in the OpenClaw chat interface using the Canvas/A2UI framework. It does NOT establish direct device connections or create new MCP servers. All data is sourced from existing MCP tools.

## Visualization Types

| Type | Component | Data Sources | Trigger |
|------|-----------|-------------|---------|
| Topology Map | `topology-map` | pyATS CDP/LLDP, health metrics | "show network topology" |
| Dashboard Panel | `dashboard-panel` | pyATS, Grafana, Prometheus | "show health dashboard for {device}" |
| Alert Card | `alert-card` | Grafana alerts, Prometheus alertmanager | "show current alerts" |
| Change Timeline | `change-timeline` | ServiceNow | "show change request {CR} status" |
| Diff View | `diff-view` | pyATS config/route/ACL | "show config diff for {device}" |
| Path Trace | `path-trace` | pyATS, SuzieQ | "trace path from {src} to {dst}" |
| Health Scorecard | `health-scorecard` | pyATS, Grafana, Prometheus | "show health scorecard for {site}" |

## How It Works

1. Operator requests a visualization via natural language
2. Skill identifies visualization type from request pattern
3. Data is fetched from relevant MCP servers via existing tools
4. Data is transformed into the visualization-specific content model
5. A2UI JSON envelope is built with component type, props, and content
6. Canvas framework renders the visualization inline in chat
7. GAIT audit log entry is emitted for the visualization event

## Output Format

All visualizations produce A2UI JSON:

```json
{
  "a2ui": {
    "version": "1.0",
    "type": "canvas",
    "component": "<visualization-type>",
    "props": {
      "id": "<uuid>",
      "title": "<title>",
      "timestamp": "<ISO 8601>",
      "dataSources": [...],
      "scope": {...},
      "warnings": [...],
      "content": {...}
    }
  }
}
```

## Graceful Degradation

- If a data source is unavailable, partial data is rendered with warnings
- If no data is available at all, an error-card is returned with guidance
- Health status defaults to "unknown" (gray) when metrics are missing
- Large topologies (200+ nodes) are automatically clustered by site

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **gait-session-tracking** | All visualization events are GAIT-logged |
| **pyats-topology** | CDP/LLDP discovery data for topology maps |
| **pyats-health-check** | Health metrics for node coloring and dashboards |
| **grafana-observability** | Prometheus metrics, alerts, dashboard data |
| **prometheus-monitoring** | Direct PromQL queries for metrics |
| **servicenow-change-workflow** | Change request lifecycle data |

## Important Rules

- **Read-only**: This skill never modifies network devices or MCP server state
- **No new credentials**: Uses existing MCP server connections only
- **Complements Three.js HUD**: Does not replace `ui/netclaw-visual/`
- **GAIT mandatory**: Every visualization generation is audit-logged
- **WCAG 2.1 AA**: Color scales meet accessibility contrast requirements
