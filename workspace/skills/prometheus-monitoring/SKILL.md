---
name: prometheus-monitoring
description: "Prometheus monitoring — PromQL instant/range queries, metric discovery, metadata, scrape target health, system health checks (6 tools). Use when querying Prometheus metrics, checking scrape targets, investigating alert thresholds, or analyzing network device utilization trends."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["pip3"], "env": ["PROMETHEUS_URL"] } } }
---

# Prometheus Monitoring

## MCP Server

| Property | Value |
|----------|-------|
| **Source** | [pab1it0/prometheus-mcp-server](https://github.com/pab1it0/prometheus-mcp-server) |
| **Transport** | stdio (default), SSE, or HTTP |
| **Language** | Python 3.10+ |
| **Tools** | 6 (query, range query, list metrics, metadata, targets, health check) |
| **Auth** | Basic auth (username/password), bearer token, or unauthenticated |
| **Install** | `pip3 install prometheus-mcp-server` (PyPI) |
| **Run** | `prometheus-mcp-server` (stdio) |

## How to Run

```bash
# stdio mode (default — used by NetClaw)
PROMETHEUS_URL=http://prometheus:9090 prometheus-mcp-server

# HTTP transport mode
PROMETHEUS_MCP_SERVER_TRANSPORT=http PROMETHEUS_URL=http://prometheus:9090 prometheus-mcp-server

# With basic auth
PROMETHEUS_URL=http://prometheus:9090 PROMETHEUS_USERNAME=admin PROMETHEUS_PASSWORD=secret prometheus-mcp-server

# With bearer token (Grafana Cloud, Thanos, etc.)
PROMETHEUS_URL=https://prom.example.com PROMETHEUS_TOKEN=your_bearer_token prometheus-mcp-server
```

## Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `PROMETHEUS_URL` | Yes | `http://prometheus:9090` | Prometheus server endpoint |
| `PROMETHEUS_USERNAME` | No | `admin` | Basic auth username |
| `PROMETHEUS_PASSWORD` | No | `changeme` | Basic auth password |
| `PROMETHEUS_TOKEN` | No | `eyJhbG...` | Bearer token (Grafana Cloud, Thanos, Cortex) |
| `PROMETHEUS_URL_SSL_VERIFY` | No | `false` | Disable SSL certificate verification |
| `PROMETHEUS_REQUEST_TIMEOUT` | No | `30` | Request timeout in seconds (default: 30) |
| `PROMETHEUS_DISABLE_LINKS` | No | `true` | Disable Prometheus UI links in responses (saves context) |
| `ORG_ID` | No | `1` | Multi-tenant organization ID (Cortex/Mimir) |
| `PROMETHEUS_CUSTOM_HEADERS` | No | `{"X-Custom":"val"}` | Additional HTTP headers as JSON |
| `PROMETHEUS_MCP_SERVER_TRANSPORT` | No | `stdio` | Transport: stdio (default), http, or sse |

## Tools

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `execute_query` | `query`, `timeout?` | Execute instant PromQL query at current time |
| `execute_range_query` | `query`, `start`, `end`, `step`, `timeout?` | Execute PromQL range query over time interval |
| `list_metrics` | `page?`, `page_size?` | Browse available metric names with pagination |
| `get_metric_metadata` | `metric?`, `limit?` | Retrieve metric type, help text, and unit info |
| `get_targets` | none | View scrape target details (up/down, labels, last scrape) |
| `health_check` | none | Check Prometheus server availability and readiness |

---

## Workflow: Network Device Metric Monitoring

When checking Prometheus for network device metrics:

1. **Health check**: `health_check` — verify Prometheus is reachable
2. **Discover metrics**: `list_metrics` — find available SNMP/device metrics
3. **Metric metadata**: `get_metric_metadata(metric="ifHCInOctets")` — check type and description
4. **Instant query**: `execute_query(query="up{job='snmp'}")` — check which targets are up
5. **Range query**: `execute_range_query` — trend analysis over time:
   - Interface traffic: `rate(ifHCInOctets{instance="router1"}[5m]) * 8`
   - CPU utilization: `device_cpu_utilization{device="core-rtr-01"}`
   - Interface errors: `increase(ifInErrors{device=~".*"}[1h])`
   - BGP peer state: `bgp_peer_state{peer="10.1.1.2"}`
6. **Scrape targets**: `get_targets` — verify SNMP exporters and device scrape health
7. **GAIT**: Record all queries in audit trail

### Example: Interface Utilization Check

```
health_check()
list_metrics(page=1, page_size=50)
execute_query(query="rate(ifHCInOctets{device='core-rtr-01'}[5m]) * 8")
execute_range_query(query="rate(ifHCOutOctets{device='core-rtr-01'}[5m]) * 8", start="2024-01-01T00:00:00Z", end="2024-01-01T01:00:00Z", step="60s")
get_targets()
```

## Workflow: Alert Threshold Investigation

When investigating whether metrics are crossing alert thresholds:

1. **Discover metrics**: `list_metrics` — find the metric name
2. **Check metadata**: `get_metric_metadata` — understand metric type (counter, gauge, histogram)
3. **Current value**: `execute_query` — get current metric value
4. **Historical trend**: `execute_range_query` — check trend over past 1h/6h/24h
5. **Compare targets**: `get_targets` — check if specific exporters are down
6. **Report**: Metric analysis with current value, trend direction, and recommendation

## Workflow: Capacity Planning

When analyzing capacity trends for network infrastructure:

1. **Discover metrics**: `list_metrics` — find bandwidth/utilization metrics
2. **Peak analysis**: `execute_range_query` with `max_over_time()`:
   - `max_over_time(rate(ifHCInOctets{device="core-rtr-01",ifName="Gi0/0"}[5m])[7d:1h]) * 8`
3. **95th percentile**: `execute_range_query` with `quantile_over_time()`:
   - `quantile_over_time(0.95, rate(ifHCInOctets{device="core-rtr-01"}[5m])[30d:1h]) * 8`
4. **Growth rate**: Compare weekly/monthly averages
5. **Report**: Utilization summary with capacity headroom and growth projection

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **grafana-observability** | Grafana dashboards visualize Prometheus data; use Prometheus skill for direct PromQL when Grafana isn't available or for ad-hoc queries |
| **pyats-health-check** | Cross-reference pyATS device health with Prometheus time-series metrics |
| **pyats-routing** | Correlate OSPF/BGP state changes with Prometheus metric timelines |
| **gait-session-tracking** | Record all Prometheus queries and findings in GAIT audit trail |
| **te-network-monitoring** | Pair ThousandEyes path data with Prometheus infrastructure metrics |
| **sdwan-ops** | Correlate SD-WAN vManage alarms with Prometheus device metrics |
| **servicenow-change-workflow** | Reference Prometheus metrics as evidence in change requests |

---

## Important Rules

- **Prefer read-only operations** — all 6 tools are read-only; no Prometheus configuration changes
- **Use pagination for metric lists** — `list_metrics` supports `page` and `page_size` to avoid large responses
- **Specify time ranges carefully** — overly broad `execute_range_query` time ranges return large result sets
- **Disable links for context efficiency** — set `PROMETHEUS_DISABLE_LINKS=true` to reduce response size
- **GAIT audit mandatory** — record all Prometheus queries and metric analysis in audit trail
- **No secrets in queries** — never embed credentials or sensitive data in PromQL expressions
- **Verify connectivity first** — use `health_check` before running queries to confirm Prometheus is reachable

## Error Handling

- **Auth fails (401/403)**: Check `PROMETHEUS_URL`, `PROMETHEUS_USERNAME`/`PROMETHEUS_PASSWORD`, or `PROMETHEUS_TOKEN` in `~/.openclaw/.env`. Verify Prometheus allows the configured auth method.
- **Connection refused**: Verify `PROMETHEUS_URL` is reachable. Use `health_check` to diagnose connectivity.
- **PromQL syntax errors**: Use `list_metrics` and `get_metric_metadata` to discover valid metric names before querying.
- **Empty results**: Check `get_targets` to verify scrape targets are up and the expected labels exist.
- **Timeout errors**: Increase `PROMETHEUS_REQUEST_TIMEOUT` for slow queries or large result sets.
- **SSL errors**: Set `PROMETHEUS_URL_SSL_VERIFY=false` for self-signed certificates (development only).
