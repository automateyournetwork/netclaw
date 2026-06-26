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

| Service | Address | Use |
|---------|---------|-----|
| Prometheus | http://192.168.3.250:9090 | Query metrics, check targets |
| Grafana | http://192.168.3.250:3000 | Dashboards (anonymous viewer) |
| Loki | http://192.168.3.250:3100 | Query logs |
| Alertmanager | http://192.168.3.250:9093 | Check firing alerts |

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

Use pfSense MCP tools:
- `get_system_status` — uptime, CPU, memory, disk
- `get_interfaces` — interface states, IPs, traffic
- `get_firewall_rules` — recent rule changes
- `get_services` — service states (DNS, DHCP, OpenVPN)
- `get_system_logs` — recent system/firewall logs

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

### Step 7: Discord Notification (if configured)

If `DISCORD_WEBHOOK_URL` is set, post the triage report:

```bash
bash scripts/alert-receiver/post-discord.sh "<triage report>"
```

## Autonomous Mode

When triggered by the alert receiver webhook:
1. Execute the full procedure without asking for permission
2. Do NOT remediate — investigation and reporting only
3. Always produce the Step 6 triage report
4. If alert status is "resolved", post a brief all-clear

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
