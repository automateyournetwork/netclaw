---
name: alert-triage
description: "Investigate alerts from the home network observability stack. Receives enriched alert context (device name, IP, platform, role) from the alert receiver webhook and uses appropriate MCP tools to diagnose. Covers pfSense, Cisco switches, Proxmox nodes, and Linux hosts."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PROMETHEUS_URL"] } } }
---

# Alert Triage

Investigate alerts received from the observability stack (Prometheus → Alertmanager → NetClaw Alert Receiver).

## When to Use

- Alert receiver triggers investigation (autonomous mode)
- User asks "what's alerting?" or "check on <device>"
- User asks to investigate a specific alert or device issue
- Follow-up from monitoring-onboard after new alerts fire

## Observability Stack

| Service | Address | Query via | Use |
|---------|---------|-----------|-----|
| Prometheus | http://192.168.3.250:9090 | `prometheus-mcp` | Metrics, targets, `up`/probe status |
| Grafana | http://192.168.3.250:3000 | `grafana-mcp` | Dashboards + query Loki/VictoriaMetrics datasources |
| Loki | http://192.168.3.250:3100 | `grafana-mcp` (Loki datasource) | Logs, syslog, **NetFlow flow records** |
| VictoriaMetrics | (Grafana datasource) | `grafana-mcp` | `goflow2_*` flow metrics |
| Alertmanager | http://192.168.3.250:9093 | HTTP `/api/v2/alerts` | Check firing alerts |

### NetFlow / connection data (IMPORTANT — this exists, use it)

The home network already exports flow data. Do **not** tell the user to enable
NetFlow, install a flow exporter, or SSH into pfSense to run `pfTop`/`netflow show` —
that infrastructure is already running. To find **what a host is connecting to
(destination IP, port, protocol)**, query the existing flow data:

- **goflow2** (`v2.1.3`, `-format=json`) receives IPFIX on `4739/udp` → writes
  `/flows/netflow.jsonl` → OTel collector tails it → Loki (`service_name="netflow"`).
- **Loki** (via `grafana-mcp`, Loki datasource). goflow2 v2 emits **snake_case** JSON
  keys (NOT the PascalCase `SrcAddr` in some older dashboards):
  ```logql
  {service_name="netflow"} | json | src_addr="192.168.100.45"
  {service_name="netflow"} | json | dst_port="179" | proto="TCP"
  ```
  Fields: `src_addr`, `dst_addr`, `src_port`, `dst_port`, `proto`, `sampler_address`,
  `bytes`, `packets`, `etype`, `type`, `time_received_ns`.
  Note: `proto` and `etype` are **strings** (`"TCP"`, `"IPv6"`) — filter with quotes
  (`dst_port="179"`), a numeric filter like `dst_port=179` will not match.
- **VictoriaMetrics** (via `grafana-mcp`, `192.168.3.250:8428`): `goflow2_*` counters
  for volume/rate, labels `sampler_address`, `dst_port`, etc.
- Grafana dashboard: `lab-network/netflow-traffic.json`.

**Verify before relying on it:** the NetFlow overlay is defined but may not always be
running. Before concluding, check data is actually present — query
`{service_name="netflow"}` (no filter) for the last 5m, or check VictoriaMetrics for
`goflow2_flow_traffic_packets_total`. If both are empty, NetFlow is down/not exporting;
say so and fall back to `search_firewall_states` (live pfSense connections). Do not
tell the user to "enable NetFlow" — the pipeline exists; if it's empty it needs
restarting (`docker compose ... -f docker-compose.netflow.yml up -d` on the OBS host)
or pfSense isn't sending IPFIX to `192.168.3.250:4739`.

## Alert Context

When triggered by the alert receiver, you will receive:
- **alertname** — what fired (e.g., InstanceDown, HighCPU)
- **device_name** — resolved hostname
- **device_ip** — management IP
- **device_platform** — pfsense, ios, proxmox, linux
- **device_role** — firewall, switch, hypervisor, etc.
- **severity** — critical, warning, info
- **summary** — human-readable description
- **status** — firing or resolved

## Investigation Principles (read first)

1. **Use the data you already have before recommending new tooling.** Before you
   suggest "enable X", "install a flow exporter", "forward syslog", or "SSH in and
   run Y", check whether that capability already exists. This network already has:
   pfSense MCP (ARP, DHCP, states, logs, NAT), NetFlow (goflow2 → Loki/VictoriaMetrics),
   Prometheus, Loki, Grafana, SNMP. Recommending something already configured is a
   failure, not a help.
2. **Reach for an MCP tool before declaring "I can't."** Never say "I can't SSH into
   pfSense" as a dead end — the `pfsense-mcp` answers ARP, DHCP leases, firewall
   states, NAT, and logs over its REST API. If you don't know a tool exists, list
   your available tools before concluding data is unavailable.
3. **State what you checked.** If a query returns empty, say what you queried and the
   window. Do not fabricate a root cause (e.g. "syslog only maps 192.168.220.x") from
   a guess — verify against the live config or data before asserting it.
4. **Match the tool to the question:**
   | Question | Tool |
   |----------|------|
   | What is host X connecting to / on what port? | NetFlow (Loki `{service_name="netflow"}`) + `search_firewall_states` |
   | What/where is host X (IP, MAC, name)? | `get_arp_table`, `search_dhcp_leases` |
   | What's the LAN/DHCP lease range? | `get_dhcp_server_config` |
   | Why is X being blocked? | `diagnose_blocked_traffic`, `get_firewall_log` |
   | Is the block count real/excessive? | `analyze_blocked_traffic` (compare to threshold) |

## Procedure

### Step 1: Confirm Alert is Active

Query Prometheus or Alertmanager to verify the alert is still firing:

```
# Via Prometheus instant query
up{instance="<device_name>"} == 0

# Or check Alertmanager API
GET http://192.168.3.250:9093/api/v2/alerts?filter=alertname="<alertname>"
```

**GATE:** If alert already resolved, post brief all-clear and stop.

### Step 2: Gather Metrics Context (15-minute window)

Query Prometheus for relevant metrics based on alert type:

| Alert Type | Key Queries |
|------------|-------------|
| InstanceDown | `up{instance="<name>"}`, `probe_success{instance="<name>"}` |
| HighCPU | `node_cpu_seconds_total{instance="<name>"}`, `process_cpu_seconds_total` |
| HighMemory | `node_memory_MemAvailable_bytes{instance="<name>"}` |
| DiskFull | `node_filesystem_avail_bytes{instance="<name>"}` |
| InterfaceDown | `ifOperStatus{instance="<name>"}` (via SNMP exporter) |
| HighTraffic | `node_network_receive_bytes_total{instance="<name>"}` |

Use range queries for trend: `query_range?query=<expr>&start=<15m-ago>&end=now&step=60s`

### Step 3: Device-Specific Investigation

Based on **device_platform**:

#### pfSense (`platform: pfsense`)

Use the `pfsense-mcp` tools (these are the real tool names — you do NOT need SSH):

Health / config:
- `system_status` — uptime, CPU, memory, disk, temp, version
- `search_interfaces` / `search_interface_configs` — interface states, IPs, traffic
- `search_firewall_rules` / `find_blocked_rules` — active ruleset, block/reject rules
- `search_services` — service states (DNS, DHCP, unbound, OpenVPN)

Who/where is a host (answers "what is host X, what's it connecting to, what's its IP"):
- `get_arp_table` — live IP↔MAC on each interface (filter by `ip_address` / `mac_address`)
- `search_dhcp_leases` — active/expired leases (hostname, IP, MAC)
- `get_dhcp_server_config` — the DHCP pool ranges per interface (answers "what's the LAN lease range")
- `search_firewall_states` — live active connections (source, dest, port, proto, state)
- `search_nat_port_forwards` / `search_nat_outbound_mappings` — NAT translations

Logs / blocked traffic:
- `get_firewall_log` — filterlog entries (filter by source/dest IP, port, protocol, action)
- `search_logs_by_ip` — all log activity for one IP
- `analyze_blocked_traffic` — grouped block analysis with threat scoring
- `diagnose_blocked_traffic` — why a specific source is being blocked (rules + log + alias)
- `diagnose_connectivity` — ping + ARP + gateway check to a target

For "what port / where is host X connecting?" prefer **NetFlow** (see NetFlow
section) for historical flows, and `search_firewall_states` for live connections.
The pfSense filterlog only records what the firewall *blocked or passed by rule* —
NetFlow is the authoritative source for full connection detail.

#### Cisco IOS/IOS-XE (`platform: ios` or `iosxe`)

Use pyATS MCP:
- `pyats_run_command(device="<name>", command="show ip interface brief")`
- `pyats_run_command(device="<name>", command="show processes cpu")`
- `pyats_run_command(device="<name>", command="show logging last 30")`
- `pyats_run_command(device="<name>", command="show interfaces status")`

#### Proxmox (`platform: proxmox`)

Use Proxmox MCP:
- Check node status (CPU, memory, storage)
- List VMs/containers and their states
- Check recent tasks/events
- Review cluster health if multi-node

#### Linux (`platform: linux`)

Use SSH or node_exporter queries:
- System load, memory, disk via Prometheus queries
- Loki logs: `{hostname="<name>"} |~ "error|critical|failed"`

### Step 4: Log Correlation

Query Loki for device logs around the alert time:

```
{hostname="<device_name>"} |~ "(?i)(error|critical|warning|down|fail)"
```

Time window: alert start time ± 5 minutes.

### Step 5: Root Cause Classification

| Class | Evidence |
|-------|----------|
| **unreachable** | `up==0`, no response to ping/SSH, interface down |
| **resource-exhaustion** | CPU > 90%, memory > 95%, disk > 95% |
| **service-failure** | Specific service down while host is up |
| **network-issue** | Interface errors, packet loss, routing change |
| **configuration-error** | Recent config change correlating with failure |
| **external** | Upstream dependency down affecting this device |

### Step 6: Triage Report

```
╔══════════════════════════════════════════════════════════════╗
║              ALERT TRIAGE — <alertname>                      ║
╠══════════════════════════════════════════════════════════════╣
║ Device: <name> (<ip>)                                       ║
║ Platform: <platform> | Role: <role>                         ║
║ Severity: <severity> | Status: <firing|resolved>            ║
╠══════════════════════════════════════════════════════════════╣
║ FINDINGS:                                                   ║
║   • <metric evidence>                                       ║
║   • <device command output summary>                         ║
║   • <log evidence>                                          ║
╠══════════════════════════════════════════════════════════════╣
║ ROOT CAUSE: <classification>                                ║
║ DETAIL: <plain language explanation>                         ║
║ RECOMMENDATION: <specific action>                           ║
║ REMEDIATION SAFE? <yes — auto-fixable | no — needs human>   ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 6b: Enrich external IPs (threat intelligence)

For any **external/public** source IP in the alert (port scans, WAN blocks,
suspicious inbound), enrich before concluding. Skip private/RFC1918 addresses.

- `greynoise_community_lookup(ip)` — free, no key. Is it benign internet noise /
  a known scanner (Censys, Shodan) or targeted? Best first signal for scans.
- `threatintel_lookup_ip(ip)` / `abuseipdb_check` / `otx_get_pulses` — reputation,
  abuse confidence score, and threat-pulse membership.
- gtrace `asn_lookup(ip)` / `geo_lookup(ip)` — ownership (org/ASN) and location.

Fold the verdict into ROOT CAUSE (e.g. "EXTERNAL — benign scanner (Censys)").

### Step 7: Deliver findings to Discord (native bridge)

Post the completed triage report to the alerts channel using NetClaw's native
Discord bridge (not a script):

```bash
openclaw message send --channel discord --target <ALERT_CHANNEL_ID> --message "<triage report>"
```

The alert receiver passes the channel id in the investigation prompt. The
investigation is not complete until the report is posted.

## Autonomous Mode

When triggered by the alert receiver webhook:
1. Execute the full procedure without asking for permission
2. Do NOT remediate — investigation and reporting only
3. Always produce the Step 6 triage report
4. If alert status is "resolved", post a brief all-clear

## Interactive Follow-ups

After a triage, the user often asks follow-up questions ("what port is X connecting
to?", "what's the DHCP range?", "look at the ARP table"). The Investigation
Principles apply here too:
- Answer with the MCP tool that fits the question (see the table above), don't
  default to "SSH in and run this command."
- If the user says "we already have X configured, why aren't you using it?" —
  they're right. Stop recommending, query the existing data source, and answer.

## Escalation

| Finding | Action |
|---------|--------|
| pfSense unreachable | Check upstream connectivity, physical link |
| Switch interface down | Check cable, negotiate settings, SFP |
| Proxmox node high memory | Identify top VMs, check for memory leaks |
| Multiple devices down | Likely upstream/power issue — investigate in order |
| Root cause unclear | Gather more data, ask human for guidance |

## Example PromQL

```promql
# Is the device up?
up{instance="pfsense"}

# CPU usage over last 15m
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle",instance="local-ai"}[5m])) * 100)

# Memory usage
1 - (node_memory_MemAvailable_bytes{instance="local-ai"} / node_memory_MemTotal_bytes{instance="local-ai"})

# Network traffic
rate(node_network_receive_bytes_total{instance="local-ai",device="enp97s0f0np0"}[5m]) * 8

# GPU temperature (AI box)
amdgpu_temperature_celsius{instance="local-ai"}
```
