# Wi-Fi Diagnosis — MCP Server Requirements & Data Access

This document defines what MCP servers NetClaw needs installed and how to access
each data source for the `wifi-diagnosis` skill.

---

## Required MCP Servers

| MCP Server | Purpose | Config location |
|-----------|---------|-----------------|
| **unifi-network** | Ad-hoc queries to the UniFi controller (list clients, device details, trigger RF scans, radio config) | `pi-hole-deployer/.kiro/settings/mcp.json` |
| **pfsense** | Firewall rules, gateway status, ARP/DHCP, connectivity diagnostics, interface info | `pi-hole-deployer/.kiro/settings/mcp.json` |
| **pyats-mcp** | Switch show commands (interface status, CDP neighbors, VLAN verify) — HomeSwitch01/02/03 | `pi-hole-deployer/.kiro/settings/mcp.json` |

### Optional (enrichment, not required for core Wi-Fi diagnosis)

| MCP Server | Purpose |
|-----------|---------|
| **nautobot-mcp-v2** | Source of truth: device inventory, VLANs, IP prefixes, cabling |
| **proxmox** | VM status (is the UniFi controller VM healthy?) |
| **rancher** | K3s pod status (is the unifi-exporter / OTel / Prometheus running?) |

---

## Data Sources & How to Query

### Prometheus (metrics — scrape-based, 15-30s resolution)

**Access from NetClaw:** HTTP at `PROMETHEUS_URL` env var (default: query through
the K3s cluster — `http://<k3s-server-1>:9090` via port-forward, or from within
the cluster at `http://prometheus:9090`).

**Key queries for Wi-Fi diagnosis:**
```promql
# Health overview
guardian:health_score
guardian:wan_latency_ms:avg
guardian:wan_loss_ratio:5m

# Per-AP Wi-Fi quality
unifi_radio_tx_retries_pct                    # by device + band
unifi_ap_clients                              # by device
unifi_device_up{role="ap"}
unifi_device_cpu_pct{role="ap"}
unifi_device_memory_pct{role="ap"}
unifi_site_clients_wireless

# WAN probes
probe_success{job=~"blackbox_wan_.*"}
probe_duration_seconds{job="blackbox_wan_tcp"}

# Speedtest
speedtest_download_bits_per_second
speedtest_upload_bits_per_second
speedtest_ping_latency_ms

# WAN throughput (query VictoriaMetrics datasource)
rate(interface_octets_in_bytes_total{device_name="pfsense",interface_name="igc0.201"}[5m])*8
```

### VictoriaMetrics (long-term metrics — 365d retention)

**Access:** `http://victoriametrics:8428` (same PromQL API). Use for SNMP
interface counters and long-term trends (the `victoriametrics-longterm` Grafana
datasource).

### Loki (logs — 14d retention)

**Access:** `http://loki:3100` (LogQL API).

**Key queries for Wi-Fi diagnosis:**
```logql
# UniFi client lifecycle (roaming, connect, disconnect)
{device_name="unifi"} |~ "Client Roamed"
{device_name="unifi"} |~ "Client Disconnected" |~ "Basement"
{device_name="unifi"} |~ "Client Connected"
sum(count_over_time({device_name="unifi"} |~ "Client Roamed" [6h]))

# pfSense gateway health
{device_name="pfsense"} |= "dpinger"
{device_name="pfsense"} |~ "(?i)(Alarm|gateway)"

# Switch link events
{device_name=~"HomeSwitch.*"} |~ "(?i)(UPDOWN|changed state|LINK)"
```

### UniFi MCP (ad-hoc controller queries — point-in-time)

**When to use:** metrics/logs don't answer the question; need per-client detail,
radio config, or to trigger an action.

| Tool | Use case |
|------|----------|
| `load_network_tools` | Must call first to register UniFi tools |
| `unifi_list_devices` | AP inventory, firmware, model, online state |
| `unifi_get_device_details` | Full AP detail (radio table, port table) |
| `unifi_get_device_radio` | Per-band config: channel, tx_power, min_rssi, channel width |
| `unifi_list_clients` | All connected clients with uplink AP, IP, type |
| `unifi_trigger_rf_scan` | Start an RF environment scan (takes 5-10 min) |
| `unifi_get_rf_scan_results` | Per-channel interference/utilization after scan |
| `unifi_update_device_radio` | Change tx_power, channel, min_rssi (requires confirm) |

**Auth:** local Integration API key (`X-API-Key` header to
`https://192.168.100.10:11443`). The MCP server handles this from its env config.

### pfSense MCP (firewall/gateway context)

| Tool | Use case |
|------|----------|
| `search_firewall_rules` | Verify VLAN rules (e.g., is VLAN13→controller allowed?) |
| `get_gateway_status` | Live gateway health (latency, loss, online/offline) |
| `diagnose_connectivity` | Ping + ARP + gateway check to a host |
| `search_dhcp_leases` | Find a client's IP from MAC or hostname |
| `get_arp_table` | Who's on the network right now |
| `search_interface_configs` | Interface status and IP addressing |

### pyATS MCP (switch verification)

| Tool | Use case |
|------|----------|
| `pyats_run_show_command` | `show interfaces status`, `show cdp neighbors`, `show vlan` |
| `pyats_device_health` | Switch CPU/memory/interface summary |
| `pyats_get_neighbors` | What's physically connected to each port |

Use when: AP shows offline but `unifi_device_up=0` — verify the switch port is up,
check CDP for the AP's MAC, confirm the uplink is passing the right VLAN.

---

## Network Topology (relevant to Wi-Fi)

```
ISP (1 Gbps symmetric, Lumen/CenturyLink)
  → pfSense (igc0.201 WAN, 192.168.100.1 gateway)
    → HomeSwitch01/02 (Cisco 3850, core, VLAN 3 management)
      → U6-Pro Basement Laundry Room (192.168.3.15, ~27 clients)
      → U6-Pro Sophie's Office (192.168.3.16, ~7 clients)
    → K3s cluster (VLAN 13, observability stack)
      → unifi-exporter → Prometheus → Alertmanager → NetClaw webhook
    → UniFi OS Server VM (192.168.100.10:11443, VLAN 100)
```

**Key facts:**
- APs are on VLAN 3 (management), clients bridge to their respective VLANs
- The UniFi controller VM is on VLAN 100 (HomeLan)
- The observability stack is on VLAN 13 (K3s)
- pfSense rule 95 allows VLAN13 → controller:11443 (exporter path)
- WAN interface confirmed: `igc0.201`
- ISP: Lumen/CenturyLink, Denver CO, 1 Gbps symmetric

---

## Alert → Skill Trigger Flow

```
UniFi exporter (metrics) → Prometheus (rule eval) → Alertmanager → NetClaw webhook
                                                                        ↓
                                                              wifi-diagnosis skill
                                                                        ↓
                                                        Query Prometheus + Loki + MCP
                                                                        ↓
                                                              Diagnosis + recommendations
```

Alerts that trigger this skill:
- `WifiHighTxRetries` — TX retries >35% for 10m
- `AccessPointOffline` — AP down 5m
- `InternetDown` — all WAN probes fail 2m
- `WanHighLatency` — avg WAN RTT >80ms for 5m
- `WanHighLoss` — WAN loss >10% for 5m
- `SpeedtestBelowSLA` — <70% of 1 Gbps for 2h
- `UniFiExporterDown` — exporter unreachable 10m

---

## Environment Variables NetClaw Needs

| Variable | Value | Purpose |
|----------|-------|---------|
| `PROMETHEUS_URL` | `http://192.168.13.X:9090` (or port-forward) | PromQL queries |
| `LOKI_URL` | `http://192.168.13.X:3100` (or port-forward) | LogQL queries |

The MCP servers (unifi-network, pfsense, pyats-mcp) are configured separately in
their own `mcp.json` blocks — NetClaw calls them by name, not by URL.
