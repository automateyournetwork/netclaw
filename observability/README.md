# Observability Stack

Portable observability pipeline for the Nautobot Workshop ContainerLab topology. Deploys alongside the lab on the same Docker network — no NAT, no port forwarding.

Part of the [Building Convergence](https://byrnbaker.me) blog series (Part 13+).

---

## Architecture

```
ContainerLab (18 devices)
├── 10 Cisco IOL (P1-P4, PE1-PE3, CE1-CE2, RR1)
└── 8 Arista cEOS (West/East Spine01-02, Leaf01-02)
        │
        ├── SNMP (udp/161) ──→ OTEL Collector (.200)
        │                           │
        │                           ├── metrics ──→ VictoriaMetrics (.201:8428)
        │                           └── logs ────→ Loki (.202:3100)
        │
        └── Syslog (udp/1514) ──→ OTEL Collector ──→ Loki
                                                          │
                                                          ▼
                                                    Grafana (.203:3000)
                                                          │
                                                          ▼
                                                    NetClaw (via Grafana MCP + Prometheus MCP)
```

All services share the `clab-mgmt` Docker network (192.168.220.0/24).

---

## Prerequisites

1. **ContainerLab topology running** — the `clab-mgmt` Docker network must exist
2. **SNMP + syslog configured on devices** — managed via golden config (see below)
3. **Docker and docker compose** available on the host

---

## Quick Start

```bash
# 1. Ensure ContainerLab is running
docker network inspect clab-mgmt >/dev/null 2>&1 && echo "OK" || echo "Deploy ContainerLab first"

# 2. Deploy the observability stack
cd /path/to/netclaw/observability
docker compose -f docker-compose.observability.yml up -d

# 3. Wait for first SNMP poll cycle (~90 seconds)
sleep 90

# 4. Verify metrics are flowing
curl -s "http://localhost:8428/api/v1/query?query=interface_status" | \
  python3 -c "import sys,json; r=json.load(sys.stdin); print(f'{len(r[\"data\"][\"result\"])} series')"

# 5. Open Grafana
# http://localhost:3000 (admin / netclaw)
```

---

## Device Configuration (Golden Config Pipeline)

SNMP and syslog are **not** configured manually. They're managed through the Nautobot golden config pipeline:

### Config Context

`Nautobot-Workshop/config_contexts/observability.yml` defines the intent:

```yaml
observability:
  snmp:
    community: public
    access: ro
  syslog:
    host: 192.168.220.200
    port: 1514
    transport: udp
    trap_level: informational
```

Applied to all device roles via `_metadata.roles`.

### Jinja Templates

- `templates/ios/observability.j2` — renders `snmp-server community` + `logging host` for Cisco IOL
- `templates/eos/observability.j2` — renders `snmp-server community` + `logging host` for Arista cEOS

### Deployment

```bash
cd ~/Nautobot-Workshop/ansible-lab
ansible-playbook pb.build-lab.yml --tags build   # regenerate intended configs
ansible-playbook pb.build-lab.yml --tags deploy  # push to devices
```

### Schema Validation

`config_context_schemas/observability_schema.yaml` validates the config context structure in Nautobot.

---

## Services

| Service | Container | IP | Port | Purpose |
|---------|-----------|-----|------|---------|
| OTEL Collector | otel-collector | 192.168.220.200 | 4317 (gRPC), 1514/udp (syslog) | SNMP polling + syslog ingestion |
| VictoriaMetrics | victoriametrics | 192.168.220.201 | 8428 | Prometheus-compatible metrics storage |
| Loki | loki | 192.168.220.202 | 3100 | Log aggregation |
| Grafana | grafana | 192.168.220.203 | 3000 | Dashboards + visualization |

---

## Metrics Collected

| Metric | OID | Platforms | Description |
|--------|-----|-----------|-------------|
| `system_cpu_utilization` | 1.3.6.1.4.1.9.9.109.1.1.1.1.8.1 | Cisco IOL | CPU % (5-min average) |
| `system_memory_utilization` | 1.3.6.1.4.1.9.9.48.1.1.1.5.1 | Cisco IOL | Memory pool used |
| `interface_octets_in` | 1.3.6.1.2.1.31.1.1.1.6 | All | ifHCInOctets (64-bit) |
| `interface_octets_out` | 1.3.6.1.2.1.31.1.1.1.10 | All | ifHCOutOctets (64-bit) |
| `interface_packets_in` | 1.3.6.1.2.1.2.2.1.11 | All | ifInUcastPkts |
| `interface_packets_out` | 1.3.6.1.2.1.2.2.1.17 | All | ifOutUcastPkts |
| `interface_errors_in` | 1.3.6.1.2.1.2.2.1.14 | All | ifInErrors |
| `interface_errors_out` | 1.3.6.1.2.1.2.2.1.20 | All | ifOutErrors |
| `interface_status` | 1.3.6.1.2.1.2.2.1.8 | All | ifOperStatus (1=up, 2=down) |

All metrics are labeled with `device_name` and `interface_name`.

---

## Dashboards

### Network Device Health
- CPU utilization per device (thresholds: green < 60%, yellow < 85%, red ≥ 85%)
- Memory utilization per device
- Device status (interface count as health indicator)
- Interface error rates across fleet

### Interface Status
- Per-device interface operational status table
- Inbound/outbound traffic (bits/s)
- Packet rates (pps)
- Error rates with threshold coloring

---

## NetClaw Integration

Set these environment variables to connect NetClaw's MCP servers to the lab stack:

```bash
export GRAFANA_URL=http://192.168.220.203:3000
export GRAFANA_USERNAME=admin
export GRAFANA_PASSWORD=netclaw
export PROMETHEUS_URL=http://192.168.220.201:8428
```

This enables:
- **Grafana MCP** (75+ tools) — dashboard search, PromQL via Grafana, Loki log queries, alerting, incidents
- **Prometheus MCP** (6 tools) — direct PromQL against VictoriaMetrics, metric discovery, target health

### Example PromQL Queries

```promql
# Interface traffic rate (bits/s) for a specific device
rate(interface_octets_in{device_name="West-Spine01"}[5m]) * 8

# All interfaces with errors in the last hour
increase(interface_errors_in[1h]) > 0

# CPU utilization across all Cisco devices
system_cpu_utilization{device_vendor="cisco"}

# Down interfaces
interface_status == 2
```

---

## Teardown

```bash
docker compose -f docker-compose.observability.yml down -v
```

The `-v` flag removes named volumes (metrics/logs data). Omit it to preserve data across restarts.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| No metrics after 2 minutes | SNMP not configured on devices | Run `ansible-playbook pb.build-lab.yml --tags deploy` |
| `clab-mgmt` network not found | ContainerLab not running | Deploy the topology first |
| Grafana shows "No data" | VictoriaMetrics not receiving | Check `docker logs otel-collector` for SNMP errors |
| Syslog not appearing in Loki | Devices not sending to .200:1514 | Verify `logging host` config on devices |
