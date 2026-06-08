---
name: lab-alert-triage
description: "Investigate firing Grafana alerts on the lab network. Lists active alert rules, correlates each alert with netclaw_* PromQL/Loki evidence, and confirms or refutes with pyATS/gNMI live device state. Use when alerts fire autonomously (Grafana webhook → OpenClaw hook), on cron lab-alert-watch, when the user asks about a Grafana notification, or lab-noc-watch reports WARNING/CRITICAL."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["uvx", "python3"], "env": ["GRAFANA_URL", "PROMETHEUS_URL", "PYATS_TESTBED_PATH"] } } }
---

# Lab Alert Triage

## When to Use

- **Autonomous trigger:** Grafana fires a `team=lab-noc` alert → webhook hits OpenClaw `/hooks/grafana-alert` → run this skill immediately without waiting for the user
- Grafana alert rules are firing or pending (folder **Lab Network**)
- User asks "what's alerting?" or "triage the NOC alert"
- Follow-up after `lab-noc-watch` returns WARNING or CRITICAL
- Discord/Slack notification from the lab observability stack

## Autonomous Mode

When the hook message starts with `AUTONOMOUS ALERT TRIAGE`:

1. Do **not** ask the user for permission to investigate — execute the full procedure
2. Do **not** remediate (no `shutdown`, no config push, no ticket creation) unless the user explicitly approves in the same thread
3. **Always** emit the Step 6 box in the session even if pyATS/Loki fail; then post to Discord:
   - **Webhook (preferred):** `bash scripts/observability/post-discord-webhook.sh "<Step 6 report>"` when `DISCORD_WEBHOOK_URL` is set
   - **Bot fallback:** `message` tool to `channel:<id>` only if webhook is unset and `deliver` is enabled
4. If `Alert status: resolved`, post a one-line all-clear and skip deep drill-down
5. **Never use Protocol MCP** for router RCA — it is NetClaw's synthetic speaker (AS 65099), not PE/RR/P devices
6. **Finish within ~8 tool calls** — skip `memory_search`, `list_alert_groups`, `list_incidents`, and broad instant queries like `{device_name="pe3"}`
7. Use metric `netclaw_path_jitter_ms` (not `ipsla_jitter_ms`) and Loki label `device_name` (not `device`)
8. Loki `startRfc3339`/`endRfc3339` must be RFC3339 timestamps (e.g. `2026-06-07T03:00:00Z`), not `now-30m`
9. After **one** Loki query returns zero streams, skip further log correlation and proceed to pyATS or the report

### Autonomous fast path (ALERT-006 example)

```
alerting_manage_rules(operation="list", search_rule_name="<alertname>")
query_prometheus(expr="netclaw_path_jitter_ms{device_name='<device>'}", queryType="range", startTime="now-30m")
pyats_run_command(device="<device>", command="show ip sla statistics")   # if pyATS available
→ Step 6 triage report (CONFIRMED if jitter > 20ms on any probe)
```

## Data Sources

| Source | Tool | Purpose |
|--------|------|---------|
| Grafana alerts | Grafana MCP `list_alert_rules` | Which rules exist and their state |
| Metrics | Grafana MCP `query_prometheus` or Prometheus MCP `execute_query` | Confirm `netclaw_*` condition |
| Logs | Grafana MCP `query_loki_logs` | Syslog around alert time |
| Device state | pyATS MCP (Cisco CSR) / gNMI MCP (Arista cEOS) | Authoritative interface/BGP state |

Prefer **Grafana MCP** for alert listing and correlated queries.

## Procedure

### Step 1: List Active Alerts

```
list_alert_rules()
```

Filter to folder **Lab Network** with state `firing` or `pending`. Record: rule title, `alert_id` label, severity, annotation summary.

**GATE:** If no firing/pending rules → report "No active Grafana alerts"; optionally run `lab-noc-watch`.

### Step 2: Map Alert to Investigation

#### General lab alerts (`lab-network-evaluation`)

| Alert rule | PromQL confirmation | Drill-down |
|------------|---------------------|------------|
| Lab Interface Down | `interface_status{device_name="<d>",job="netclaw-bgp-snmp"} == 2` | `show ip interface brief` |
| Lab Interface Errors | `rate(interface_errors_in_total{device_name="<d>"}[5m])` | `show interfaces` (errors/CRC) |
| Lab CPU High | `system_cpu_utilization{device_name="<d>"}` | `show processes cpu` |

#### BGP route stability alerts (`bgp-stability-evaluation`)

| Alert ID | Rule title | PromQL confirmation | LogQL | Drill-down |
|----------|------------|---------------------|-------|------------|
| ALERT-001 | netclaw-bgp-peer-down | `netclaw_bgp_peer_state{device_name="<d>",neighbor="<n>"} != 6` | `{device_name="<d>"} \|~ "ADJCHANGE"` | `show ip bgp summary` |
| ALERT-002 | netclaw-bgp-prefix-drop | `netclaw_bgp_peer_prefixes_received{device_name="<d>",neighbor="<n>"}` vs 1h avg | ADJCHANGE | `show ip bgp neighbors <n> received` |
| ALERT-003 | netclaw-bgp-session-flap | `increase(netclaw_bgp_peer_established_transitions_total{device_name="<d>"}[15m])` | ADJCHANGE | `show ip bgp neighbors <n>` |
| ALERT-004 | netclaw-bgp-prefix-withdrawal-rate | `rate(netclaw_bgp_prefix_withdrawals_total{device_name="<d>"}[5m])` | BMP-related syslog | `show ip bgp <prefix>` |
| ALERT-005 | netclaw-bgp-update-rate-high | `rate(netclaw_bgp_peer_in_updates_total{device_name="<d>"}[5m])` | — | `show ip bgp summary` |
| ALERT-006 | netclaw-path-jitter-high | `netclaw_path_jitter_ms{device_name="<d>"}` | — | `show ip sla statistics` |
| ALERT-007 | netclaw-interface-bgp-correlation | `changes(interface_status{device_name="<d>",job="netclaw-bgp-snmp"}[5m])` + `rate(netclaw_bgp_peer_in_updates_total{job="netclaw-bgp-snmp"}[5m])` | UPDOWN | `show interfaces` |

Extract `device_name`, `neighbor`, `prefix` from alert labels or query results.

### Step 3: Correlate Metrics (15m window)

For each firing alert:

```
query_prometheus(expr="interface_status{device_name='<device>',job='netclaw-bgp-snmp'}")
query_prometheus(expr="changes(interface_status{device_name='<device>',job='netclaw-bgp-snmp'}[15m])")
query_prometheus(expr="netclaw_bgp_peer_state{device_name='<device>'}")
query_prometheus(expr="netclaw_bgp_peer_prefixes_received{device_name='<device>'}")
query_prometheus(expr="rate(netclaw_bgp_peer_in_updates_total{device_name='<device>'}[5m])")
```

### Step 4: Correlate Syslog

```
query_loki_logs(
  query='{device_name="<device>"} |~ "(?i)(UPDOWN|LINEPROTO|ADJCHANGE|BGP|NOTIFICATION)"',
  time_range="30m"
)
```

Match log timestamps to metric transitions from Step 3.

### Step 5: Confirm with pyATS / gNMI

**Cisco CSR:**

```
pyats_run_command(device="<device>", command="show ip interface brief")
pyats_run_command(device="<device>", command="show ip bgp summary")
pyats_run_command(device="<device>", command="show logging last 20")
```

**Arista cEOS:**

```
gnmi_compare_with_cli(target="<device>", data_type="bgp_neighbors")
```

**Verdict:** **confirmed** (metrics + device agree), **stale** (alert firing but device healthy), or **symptom-only** (escalate to `bgp-route-stability-watch` or `lab-troubleshoot`).

### Step 6: Triage Report

```
╔══════════════════════════════════════════════════════════════╗
║              ALERT TRIAGE — <N> ACTIVE ALERT(S)             ║
╠══════════════════════════════════════════════════════════════╣
║ Alert: <rule title> (ALERT-<id>)                            ║
║ Severity: <critical|high|warning>                           ║
║ Device: <device>  Neighbor: <if any>  Prefix: <if any>      ║
║ Status: <CONFIRMED | STALE | INCONCLUSIVE>                  ║
║ Evidence: <1-line metric + 1-line log or show command>      ║
║ Likely cause: <plain language>                              ║
║ Next: <bgp-route-stability-watch | lab-troubleshoot | none> ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 6b: Discord delivery

```bash
bash scripts/observability/post-discord-webhook.sh "$(cat <<'EOF'
<paste Step 6 triage box here>
EOF
)"
```

Skip if `DISCORD_WEBHOOK_URL` is unset.

### Step 7: GAIT Audit

```
gait_record(
  operation="lab-alert-triage",
  alerts_triaged=<count>,
  confirmed=<list>,
  stale=<list>
)
```

## Escalation

| Finding | Skill |
|---------|-------|
| Any `netclaw-bgp-*` alert confirmed | `bgp-route-stability-watch` |
| Interface + BGP correlation (ALERT-007) | `bgp-route-stability-watch` → `lab-troubleshoot` |
| Multi-symptom or unclear root cause | `lab-troubleshoot` |
| Fleet-wide health snapshot | `lab-noc-watch` |

## Example PromQL

```promql
netclaw_bgp_peer_state{device_name=~"rr1|pe.*"} != 6
netclaw_bgp_peer_prefixes_received{device_name="rr1",neighbor="100.0.254.13"}
rate(netclaw_bgp_prefix_withdrawals_total[5m])
max by (device_name) (netclaw_path_jitter_ms{device_name=~"pe.*|ce.*"})
changes(interface_status{device_role=~"pe|p"}[5m]) > 0
```

## Example LogQL

```logql
{device_name="pe1"} |~ "(?i)(ADJCHANGE|UPDOWN|LINEPROTO)"
{device_name="rr1"} |~ "BGP.*(ADJCHANGE|NOTIFICATION)"
```