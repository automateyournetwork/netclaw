---
name: gcp-cloud-monitoring
description: Google Cloud Monitoring — time series metrics, alert policies, active alerts, metric discovery
version: 1.0.0
tags: [gcp, cloud-monitoring, metrics, alerts, observability]
---

# GCP Cloud Monitoring

Monitor Google Cloud infrastructure via the Cloud Monitoring MCP server — query time series metrics, inspect alert policies, check active alerts, and discover available metric types.

## MCP Server

- **Endpoint**: `https://monitoring.googleapis.com/mcp` (Streamable HTTP)
- **Auth**: OAuth 2.0 via Google IAM — service account key (`GOOGLE_APPLICATION_CREDENTIALS`) or `gcloud auth application-default login`
- **Requires**: `GCP_PROJECT_ID` environment variable

## Available Tools (6)

| Tool | What It Does |
|------|-------------|
| `list_timeseries` | Query time series data — CPU, memory, network, disk metrics for any GCP resource |
| `list_metric_descriptors` | Discover available metric types in a project — find what you can monitor |
| `list_alert_policies` | List all alerting policies — conditions, notification channels, thresholds |
| `get_alert_policy` | Get details of a specific alerting policy |
| `list_alerts` | List current and past alert violations — what's firing right now |
| `get_alert` | Get details of a specific alert violation |

## Workflow: GCP Network Monitoring

When a user asks "how is our GCP network performing?":

1. **Check alerts**: `list_alerts` to find any active alert violations
2. **VM network metrics**: `list_timeseries` for `compute.googleapis.com/instance/network/received_bytes_count` and `sent_bytes_count`
3. **Packet drops**: `list_timeseries` for `compute.googleapis.com/instance/network/received_packets_dropped_count`
4. **Firewall metrics**: `list_timeseries` for `compute.googleapis.com/firewall/dropped_packets_count`
5. **Load balancer metrics**: `list_timeseries` for `loadbalancing.googleapis.com/https/request_count` and `total_latencies`
6. **Report**: Network health dashboard with any issues flagged

## Workflow: Alert Investigation

When investigating GCP alerts:

1. **List active alerts**: `list_alerts` — find what's currently firing
2. **Get alert details**: `get_alert` — condition, threshold, resource affected
3. **Get policy**: `get_alert_policy` — what triggers this alert, notification channels
4. **Pull metrics**: `list_timeseries` for the affected metric — see the spike/anomaly
5. **Cross-reference**: Use `gcp-cloud-logging` for correlated log entries
6. **Report**: Alert investigation with root cause and timeline

## Workflow: Resource Health Check

When checking GCP infrastructure health:

1. **Discover metrics**: `list_metric_descriptors` filtered by service (compute, networking, loadbalancing)
2. **VM CPU/Memory**: `list_timeseries` for `compute.googleapis.com/instance/cpu/utilization` and memory metrics
3. **Disk I/O**: `list_timeseries` for `compute.googleapis.com/instance/disk/read_bytes_count` and write metrics
4. **Network throughput**: `list_timeseries` for network sent/received bytes
5. **Alert status**: `list_alert_policies` + `list_alerts` — any policies in violation?
6. **Report**: Infrastructure health dashboard with severity ratings

## Common GCP Network Metrics

| Metric | What It Tells You |
|--------|-------------------|
| `compute.googleapis.com/instance/network/received_bytes_count` | Inbound network throughput per VM |
| `compute.googleapis.com/instance/network/sent_bytes_count` | Outbound network throughput per VM |
| `compute.googleapis.com/instance/network/received_packets_dropped_count` | Dropped inbound packets (congestion) |
| `compute.googleapis.com/instance/network/sent_packets_dropped_count` | Dropped outbound packets (congestion) |
| `compute.googleapis.com/firewall/dropped_packets_count` | Packets dropped by VPC firewall rules |
| `loadbalancing.googleapis.com/https/request_count` | HTTP(S) LB request rate |
| `loadbalancing.googleapis.com/https/total_latencies` | HTTP(S) LB end-to-end latency |
| `loadbalancing.googleapis.com/https/backend_latencies` | Backend response time behind LB |
| `vpn.googleapis.com/tunnel_established` | Cloud VPN tunnel state (1=up, 0=down) |
| `vpn.googleapis.com/sent_bytes_count` | Bytes sent through VPN tunnel |
| `router.googleapis.com/bgp/received_routes_count` | BGP routes received by Cloud Router |
| `interconnect.googleapis.com/link/received_bytes_count` | Cloud Interconnect link throughput |

## Important Rules

- **Remote MCP server** — hosted by Google, no local install needed
- **OAuth 2.0 authentication** — uses IAM for access control
- **Project-scoped** — metrics are scoped to the configured GCP project
- **Read-only** — monitoring queries don't modify anything
- **Record in GAIT** — log monitoring investigations for audit trail

## Environment Variables

- `GCP_PROJECT_ID` — Google Cloud project ID
- `GOOGLE_APPLICATION_CREDENTIALS` — Path to service account key JSON file
