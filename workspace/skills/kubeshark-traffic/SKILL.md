---
name: kubeshark-traffic
description: "Kubeshark Kubernetes traffic analysis — L4/L7 deep packet inspection, TLS decryption, pcap export, flow analysis, service mapping (6 tools). Use when capturing Kubernetes pod traffic, debugging service-to-service latency, exporting pcaps from a cluster, or analyzing encrypted east-west traffic"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["kubectl"], "env": ["KUBESHARK_MCP_URL"] } } }
---

# Kubeshark Kubernetes Traffic Analysis

## MCP Server

| Property | Value |
|----------|-------|
| **Source** | [kubeshark/kubeshark](https://github.com/kubeshark/kubeshark) — [MCP docs](https://docs.kubeshark.com/en/mcp) |
| **Transport** | Remote HTTP (JSON-RPC 2.0, default port 8898) |
| **Language** | Go (built into Kubeshark Hub) |
| **Tools** | 6 (capture, export pcap, snapshot, filter, L4 flows, flow summary) |
| **Auth** | None (cluster-internal); requires `kubectl port-forward` for remote access |
| **Requires** | Kubernetes cluster with Kubeshark installed via Helm |

## How to Run

```bash
# Install Kubeshark with MCP enabled
helm install kubeshark kubeshark/kubeshark \
  --set mcp.enabled=true \
  --set mcp.port=8898

# Port-forward for local access (if not in-cluster)
kubectl port-forward svc/kubeshark-hub 8898:8898

# MCP endpoint is now available at:
# http://localhost:8898/mcp
```

## Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `KUBESHARK_MCP_URL` | Yes | `http://localhost:8898/mcp` | Kubeshark MCP endpoint URL |
| `KUBESHARK_MCP_PORT` | No | `8898` | MCP server port (default: 8898) |

## Tools

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `capture_traffic` | `filter?`, `duration?` | Start targeted packet capture across cluster pods |
| `export_pcap` | `filter?`, `time_range?` | Export captured traffic as pcap for Wireshark/tshark analysis |
| `create_snapshot` | `filter?` | Create point-in-time traffic snapshot within retention window |
| `apply_filter` | `kfl_expression` | Apply Kubeshark Filter Language (KFL) expressions to narrow results |
| `list_l4_flows` | `filter?` | List TCP/UDP flows with connection stats, RTT metrics, byte counts |
| `get_l4_flow_summary` | `filter?` | High-level summary: top talkers, protocol distribution, traffic volume |

## Resources Exposed

- Real-time L7 API streams (HTTP, gRPC, GraphQL, Redis, Kafka, DNS) with full request/response payloads
- Historical traffic queries within the configured retention window
- Decrypted TLS/HTTPS traffic via eBPF (no manual key management)
- TCP/UDP connection flows with timing, RTT, and byte statistics
- Kubernetes pod identity and service mapping (source → destination with namespace/labels)

---

## Workflow: Kubernetes Service Troubleshooting

When investigating connectivity or latency issues between Kubernetes services:

1. **Capture traffic**: `capture_traffic(filter="src.pod.name == 'frontend'")` — start targeted capture
2. **List flows**: `list_l4_flows` — see all TCP/UDP connections with RTT and stats
3. **Flow summary**: `get_l4_flow_summary` — identify top talkers and protocol breakdown
4. **Apply filter**: `apply_filter(kfl_expression="response.status >= 500")` — isolate errors
5. **Export pcap**: `export_pcap(filter="dst.pod.name == 'api-gateway'")` — export for deep analysis
6. **Cross-reference**: Use `packet-analysis` skill to analyze exported pcap with tshark
7. **Report**: Service communication analysis with latency, error rates, and traffic patterns
8. **GAIT**: Record all captures and findings in audit trail

### Example: API Gateway Latency Investigation

```
capture_traffic(filter="dst.pod.name == 'api-gateway'", duration="5m")
list_l4_flows(filter="dst.pod.name == 'api-gateway'")
get_l4_flow_summary(filter="dst.pod.name == 'api-gateway'")
apply_filter(kfl_expression="response.latency > 500ms")
export_pcap(filter="response.latency > 500ms")
```

## Workflow: TLS Traffic Inspection

When investigating encrypted service-to-service communication:

1. **Capture**: `capture_traffic` — Kubeshark automatically decrypts TLS via eBPF
2. **Filter**: `apply_filter(kfl_expression="request.headers['content-type'] == 'application/grpc'")` — isolate gRPC
3. **Flows**: `list_l4_flows` — see encrypted connections with decrypted payload summaries
4. **Export**: `export_pcap` — export decrypted traffic for offline analysis
5. **Report**: TLS communication audit with certificate info and payload analysis

## Workflow: Incident Traffic Forensics

When performing post-incident traffic analysis:

1. **Snapshot**: `create_snapshot` — capture current traffic state
2. **Historical query**: `apply_filter` with time range — find traffic around incident time
3. **Flow analysis**: `list_l4_flows` — identify unusual connections or traffic spikes
4. **Top talkers**: `get_l4_flow_summary` — find services with abnormal traffic volume
5. **Export evidence**: `export_pcap` — preserve traffic for incident report
6. **Cross-reference**: Correlate with Prometheus metrics, Grafana alerts, and pyATS device state

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **packet-analysis** | Export Kubeshark pcaps → analyze with Packet Buddy tshark (deeper protocol dissection) |
| **prometheus-monitoring** | Correlate Kubeshark flow metrics with Prometheus time-series data |
| **grafana-observability** | Cross-reference Kubeshark traffic patterns with Grafana dashboards and alerts |
| **pyats-health-check** | Compare Kubernetes network traffic with underlying infrastructure health |
| **gait-session-tracking** | Record all Kubeshark captures, exports, and analysis in GAIT audit trail |
| **servicenow-change-workflow** | Reference Kubeshark traffic captures as evidence in change requests or incidents |

---

## Kubeshark Filter Language (KFL) Examples

```
# Filter by pod name
src.pod.name == "frontend"

# Filter by namespace
dst.namespace == "production"

# HTTP status codes
response.status >= 400

# Latency threshold
response.latency > 200ms

# Protocol type
protocol == "grpc"

# Combined filters
src.namespace == "default" and response.status >= 500 and response.latency > 1s

# DNS queries
protocol == "dns" and request.query contains "api.internal"

# Kafka messages
protocol == "kafka" and request.topic == "orders"
```

---

## Important Rules

- **All tools are read-only** — Kubeshark captures and analyzes traffic but does not modify it
- **Cluster access required** — Kubeshark must be deployed in the target Kubernetes cluster via Helm
- **Port-forward for remote access** — use `kubectl port-forward svc/kubeshark-hub 8898:8898` when not in-cluster
- **Retention window** — historical queries are limited to the configured retention period
- **Large captures** — use KFL filters to scope captures and avoid overwhelming context with large traffic volumes
- **Sensitive data** — captured traffic may contain PII, credentials, or secrets in request/response payloads; handle exports accordingly
- **GAIT audit mandatory** — record all traffic captures, pcap exports, and analysis findings
- **No secrets in filters** — never embed credentials or sensitive data in KFL expressions

## Error Handling

- **Connection refused**: Verify Kubeshark is running (`kubectl get pods -n kubeshark`) and port-forward is active.
- **No traffic captured**: Check KFL filter syntax; verify target pods exist and are generating traffic.
- **MCP endpoint not found**: Ensure `mcp.enabled=true` in Helm values; verify MCP port matches `KUBESHARK_MCP_URL`.
- **Permission denied**: Check RBAC — Kubeshark needs cluster-wide read access for traffic capture.
- **Empty pcap exports**: Verify retention window covers the requested time range; check that traffic matching the filter exists.
