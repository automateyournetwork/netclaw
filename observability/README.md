# Observability Stack

Portable observability pipeline for the Nautobot Workshop ContainerLab topology. Deploys alongside the lab on the same Docker network — no NAT, no port forwarding.

Part of the [Building Convergence](https://byrnbaker.me) blog series (Part 13+).

---

## Architecture

```
ContainerLab (18 devices — CSR1000v + Arista cEOS)
        │
        ├─ PLANE 1: BMP (RR1) ──→ gobmp (.205) ──→ Redpanda ──→ bgp-bmp-consumer (.206)
        ├─ PLANE 2a: SNMP ──→ bgp-snmp-exporter (.204) ──→ netclaw_bgp_* + netclaw_path_*
        ├─ PLANE 2b: gNMI ──→ bgp-gnmi-exporter (.207) ──→ netclaw_bgp_* (Arista)
        ├─ PLANE 2c: SNMP infra ──→ OTEL Collector (.200) ──→ interface_status, CPU, …
        └─ PLANE 3: Syslog (udp/1514) ──→ OTEL ──→ Loki (.202) with device_name labels
                                    │
                                    ▼
                          VictoriaMetrics (.201:8428)
                                    │
                                    ▼
                          Grafana (.203:3000) → NetClaw agents
```

All services share the `clab-mgmt` Docker network (192.168.220.0/24).

### BGP Route Stability (Part 15 — spec 031 complete)

| Plane | Lab adapter | Metrics |
|-------|-------------|---------|
| BMP events | RR1 → gobmp | `netclaw_bgp_prefix_*` |
| BGP state | SNMP exporter (Cisco CSR) | `netclaw_bgp_peer_*` |
| BGP state | gNMI exporter (Arista cEOS) | `netclaw_bgp_peer_*` `{source="gnmi"}` |
| Path quality | IP SLA via SNMP exporter | `netclaw_path_jitter_ms`, `netclaw_path_rtt_ms` |
| Narrative | Syslog → Loki | `{device_name}` + BGP/UPDOWN |

**Spec (spec-kit)**: [`specs/031-bgp-route-observability`](../specs/031-bgp-route-observability/spec.md)  
**Architecture**: [`docs/architecture/bgp-route-observability.md`](../docs/architecture/bgp-route-observability.md)  
**Quickstart**: [`specs/031-bgp-route-observability/quickstart.md`](../specs/031-bgp-route-observability/quickstart.md)

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

# Optional: BMP event plane (Phase 3 — spec 031)
docker compose -f docker-compose.observability.yml -f docker-compose.bmp.yml up -d --build
bash ../scripts/validate-bgp-metrics.sh --phase 3

# Optional: gNMI BGP stream (Phase 4 — Arista cEOS)
docker compose -f docker-compose.observability.yml -f docker-compose.gnmi.yml up -d --build
bash ../scripts/validate-bgp-metrics.sh --phase 4

# Phase 5: netclaw_* Grafana alerts (provisioned) + agent skills
docker restart grafana
bash ../scripts/validate-bgp-metrics.sh --phase 5

# Phase 6: golden config BMP + gNMI (SoT → Ansible render)
python3 ../scripts/nautobot-push-observability.py
bash ../scripts/validate-bgp-metrics.sh --phase 6

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

[byrn-baker/Nautobot-Workshop-Datasource](https://github.com/byrn-baker/Nautobot-Workshop-Datasource.git) `config_contexts/observability.yml` defines the intent (sync this Git repo into Nautobot, not the Workshop clone):

```yaml
observability:
  mgmt_vrf: clab-mgmt
  snmp:
    community: public
    access: ro
  syslog:
    host: 192.168.220.200
    port: 1514
    transport: udp
    trap_level: informational
  bmp:
    enabled: true
    host: 192.168.220.205
    port: 5000
  gnmi:
    enabled: true
    transport: default
    port: 6030
```

Applied to all device roles via `_metadata.roles`.

### Jinja Templates

- `templates/ios/observability.j2` — SNMP + syslog (RR: global logging; PE: `vrf clab-mgmt`)
- `templates/ios/bmp.j2` — BMP server stanza on IOS-XE/CSR RR only (skips IOL)
- `templates/ios/gnmi-telemetry.j2` — optional IOS-XE gNMI (lab uses SNMP)
- `templates/eos/observability.j2` — SNMP + syslog for Arista cEOS
- `templates/eos/gnmi-telemetry.j2` — `management api gnmi` from context

Templates live in `Nautobot-Workshop/ansible-lab/roles/build_lab_config/templates/` and mirror to `nautobot_workshop_golden_config_templates` for Nautobot Golden Config Git sync.

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
| Redpanda | redpanda | 192.168.220.210 | 9092 (internal) | BMP event bus (Kafka API) |
| gobmp | gobmp | 192.168.220.205 | 5000 | BMP collector (production peers) |
| BMP consumer | bgp-bmp-consumer | 192.168.220.206 | 9100 | Kafka → `netclaw_bgp_prefix_*` metrics |

### BMP overlay (`docker-compose.bmp.yml`)

Production IOS-XE/XR route reflectors peer BMP to **192.168.220.205:5000**. gobmp parses updates and publishes to Redpanda topics `gobmp.parsed.unicast_prefix_v4|v6` and `gobmp.parsed.statistics`. `bgp-bmp-consumer` (`observability/exporters/bgp-normalizer.py`) exposes Prometheus metrics scraped by VictoriaMetrics job `netclaw-bgp-bmp`.

Cisco IOL lab devices do not export BMP; the stack remains healthy with zero prefix events until production peers connect.

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

Register both in `config/openclaw.json` (`grafana-mcp`, `prometheus-mcp`). Grafana alert rules for the lab are file-provisioned in `observability/grafana/provisioning/alerting/` (`lab-network.yaml`, `bgp-route-stability.yaml`).

### Part 15 full chain (four-source correlation)

```bash
# One-time lab wiring: GRE tunnel, RR1 BGP neighbor, IP SLA, OTEL regen
bash scripts/setup-part15-lab.sh

# Restart OpenClaw gateway so protocol-mcp loads AS 65099 + RR1 peer
# Then validate:
bash scripts/validate-part15-chain.sh
```

Demo scenarios: `docs/blogs/failure-scenarios.md` (interface isolation, BGP peer loss, route flap injection).

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
