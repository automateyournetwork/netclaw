---
name: bgp-route-stability-watch
description: "Investigate BGP route stability using router-native netclaw_* metrics — peer state, prefix counts, BMP withdrawals, path quality, and syslog correlation. Use when routes flap, prefixes drop, BGP alerts fire, or path quality degrades. Does NOT use Protocol MCP RIB."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["GRAFANA_URL", "PROMETHEUS_URL", "PYATS_TESTBED_PATH"] } } }
---

# BGP Route Stability Watch

Router-native observability for BGP instability. All queries use **`netclaw_*`** metrics from VictoriaMetrics — SNMP, gNMI, and BMP adapters. **Protocol MCP is not used** for monitoring (injection demos only — see Scenario D in `docs/failure-scenarios.md`).

## When to Use

- Grafana alert `netclaw-bgp-*` or `netclaw-path-jitter-high` is firing
- User asks "are routes flapping?" or "why did prefixes drop?"
- Follow-up from `lab-alert-triage` on BGP-related alerts
- Heartbeat check for Part 15 route stability observability

## Data Sources

| Source | What It Provides | How to Query |
|--------|-----------------|--------------|
| VictoriaMetrics | `netclaw_bgp_*`, `netclaw_path_*`, `interface_status` | Grafana MCP `query_prometheus` or Prometheus MCP `execute_query` |
| Loki | `%BGP-5-ADJCHANGE`, `%LINEPROTO-5-UPDOWN`, `%BGP-3-NOTIFICATION` | Grafana MCP `query_loki_logs` with `{device_name="..."}` |
| pyATS MCP | `show ip bgp summary`, `show ip bgp neighbors`, `show interfaces` | Device drill-down on Cisco CSR |
| gNMI MCP | OpenConfig BGP neighbor state (Arista spines/leaves) | `gnmi_get` / `gnmi_compare_with_cli` when device is cEOS |

## Decision Tree

```text
1. BGP signal     → peer down? prefix drop? BMP withdrawals? UPDATE spike?
2. Interface      → changes(interface_status[5m]) on same device?
3. Syslog         → ADJCHANGE / UPDOWN in same window?
4. Path quality   → netclaw_path_jitter_ms / loss elevated?
5. Verdict        → physical layer | peer/session | upstream | synthetic demo
```

## Procedure

### Step 1: Fleet BGP Health Snapshot

```
query_prometheus(expr="netclaw_bgp_peer_state{device_name=~\"rr1|pe.*\"} != 6", time_range="15m")
query_prometheus(expr="netclaw_bgp_peer_state{source=\"gnmi\"} != 6", time_range="15m")
```

**GATE:** If no non-established peers AND no other signals in Steps 2–4 → report **HEALTHY**, stop.

Record any peers with state ≠ 6 (1=IDLE … 6=ESTABLISHED per BGP4-MIB mapping).

### Step 2: Prefix Count Stability

Detect drops ≥20% from 1h baseline (matches ALERT-002):

```
query_prometheus(expr="""
  (netclaw_bgp_peer_prefixes_received
   < 0.8 * avg_over_time(netclaw_bgp_peer_prefixes_received[1h]))
  and netclaw_bgp_peer_prefixes_received > 0
""", time_range="1h")
```

Also check RR1 service prefix count:

```
query_prometheus(expr='netclaw_bgp_peer_prefixes_received{device_name="rr1",neighbor="100.0.254.13"}', time_range="1h")
```

**GATE:** Prefix drop without peer down → suspect upstream withdrawal or RR path change; proceed to Step 4 (BMP).

### Step 3: Session Flap Detection

```
query_prometheus(expr="increase(netclaw_bgp_peer_established_transitions_total[15m]) > 0", time_range="30m")
```

If transitions increased, note `device_name` and `neighbor` labels.

### Step 4: BMP Withdrawal Rate (when BMP stack running)

```
query_prometheus(expr='sum by (device_name, prefix) (rate(netclaw_bgp_prefix_withdrawals_total[5m])) > 0', time_range="30m")
query_prometheus(expr='rate(netclaw_bgp_prefix_announcements_total[5m])', time_range="30m")
```

Lab RR1 BMP is live when `netclaw_bgp_prefix_announcements_total{device_name="rr1"}` has series.

**GATE:** BMP withdrawal spike without interface change → upstream or policy change; check syslog NOTIFICATION.

### Step 5: Correlate Interface Changes

For each affected `device_name`:

```
query_prometheus(expr="changes(interface_status{device_name=\"<device>\",job=\"netclaw-bgp-snmp\"}[5m])", time_range="30m")
query_prometheus(expr="interface_status{device_name=\"<device>\",job=\"netclaw-bgp-snmp\"} == 2", time_range="15m")
```

ALERT-007 combined signal:

```
query_prometheus(expr="""
  changes(interface_status{device_role=~\"pe|p\",job=\"netclaw-bgp-snmp\"}[5m]) > 0
  and on(device_name) rate(netclaw_bgp_peer_in_updates_total{job=\"netclaw-bgp-snmp\"}[5m]) > 0
""", time_range="15m")
```

**GATE:** Interface flap + BGP UPDATE activity → physical/link root cause (Scenario B).

### Step 6: Syslog Confirmation

```
query_loki_logs(query='{device_name="<device>"} |~ "(?i)(ADJCHANGE|UPDOWN|LINEPROTO|NOTIFICATION)"', time_range="30m")
```

Match log timestamps to metric transitions from Steps 1–5.

### Step 7: Path Quality

```
query_prometheus(expr='netclaw_path_jitter_ms{device_name=~"pe.*|ce.*"}', time_range="30m")
query_prometheus(expr='netclaw_path_rtt_ms{device_name=~"pe.*|ce.*"}', time_range="30m")
query_prometheus(expr='netclaw_path_loss_sd{device_name=~"pe.*|ce.*"}', time_range="30m")
```

| Metric | HEALTHY | WARNING | CRITICAL |
|--------|---------|---------|----------|
| Jitter | < 10 ms | 10–30 ms | > 30 ms (ALERT-006) |
| RTT | < 50 ms | 50–200 ms | > 200 ms |
| Loss (sd) | 0 | 1–5 pkts | sustained > 0 with jitter |

### Step 8: Device Drill-Down

**Cisco CSR (PE, RR, P):**

```
pyats_run_command(device="<device>", command="show ip bgp summary")
pyats_run_command(device="<device>", command="show ip bgp neighbors <neighbor>")
pyats_run_command(device="<device>", command="show ip interface brief")
pyats_run_command(device="<device>", command="show logging last 30")
```

**Arista cEOS (spine/leaf):**

```
gnmi_get(target="west-spine01", paths=["/network-instances/network-instance/protocols/protocol/bgp/neighbors"])
# or
gnmi_compare_with_cli(target="west-spine01", data_type="bgp_neighbors")
```

Do **not** call `bgp_get_rib`, `protocol_summary`, or other Protocol MCP tools for production RCA.

### Step 9: Root Cause Classification

| Class | Evidence |
|-------|----------|
| **physical-layer** | `interface_status` change + UPDOWN syslog + BGP UPDATE spike on same device |
| **peer-session** | `netclaw_bgp_peer_state != 6` + ADJCHANGE, no interface flap |
| **prefix-upstream** | BMP withdrawals or prefix drop without local interface/peer issues |
| **path-quality** | Elevated `netclaw_path_jitter_ms` / loss before peer flap |
| **synthetic-demo** | Protocol MCP injection only — BMP/SNMP show no correlated interface event (Scenario D) |

### Step 10: Generate Report

```
╔══════════════════════════════════════════════════════════════╗
║           BGP ROUTE STABILITY REPORT (netclaw_*)            ║
╠══════════════════════════════════════════════════════════════╣
║ Time Window: <start> — <end>                                ║
║ Status: <HEALTHY | WARNING | HIGH | CRITICAL>              ║
╠══════════════════════════════════════════════════════════════╣
║ BGP PEERS                                                   ║
║   Down / not established: <count> (<device:neighbor list>)  ║
║   Session flaps (15m): <count>                              ║
║   Prefix drops (>20%): <device:neighbor → before/after>     ║
╠══════════════════════════════════════════════════════════════╣
║ BMP (if available)                                          ║
║   Withdrawal rate (5m): <top prefixes>                      ║
║   Announcement rate (5m): <summary>                         ║
╠══════════════════════════════════════════════════════════════╣
║ CORRELATION                                                 ║
║   Interface changes: <device → count>                       ║
║   Syslog: <key ADJCHANGE/UPDOWN lines>                      ║
║   Path jitter max: <device> <X> ms                          ║
╠══════════════════════════════════════════════════════════════╣
║ ROOT CAUSE: <physical-layer | peer-session | upstream |    ║
║              path-quality | synthetic-demo>                 ║
║ RECOMMENDATION: <action>                                    ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 11: GAIT Audit Trail

```
gait_record(
  operation="bgp-route-stability-watch",
  result=<HEALTHY|WARNING|HIGH|CRITICAL>,
  root_cause_class=<classification>,
  devices_affected=<list>,
  recommendation=<action>
)
```

## Alert → First Query Mapping

| Alert ID | First PromQL | LogQL | Drill-down |
|----------|--------------|-------|------------|
| ALERT-001 | `netclaw_bgp_peer_state{device_name="X"} != 6` | `{device_name="X"} \|~ "ADJCHANGE"` | `show ip bgp summary` |
| ALERT-002 | `netclaw_bgp_peer_prefixes_received{device_name="X"}` | same | `show ip bgp neighbors X received` |
| ALERT-003 | `increase(netclaw_bgp_peer_established_transitions_total[15m])` | ADJCHANGE | `show ip bgp neighbors X` |
| ALERT-004 | `rate(netclaw_bgp_prefix_withdrawals_total[5m])` | BMP + syslog | `show ip bgp <prefix>` |
| ALERT-005 | `rate(netclaw_bgp_peer_in_updates_total[5m])` | — | `show ip bgp summary` |
| ALERT-006 | `netclaw_path_jitter_ms{device_name="X"}` | — | `show ip sla statistics` |
| ALERT-007 | `changes(interface_status{device_name="X"}[5m])` | UPDOWN | `show interfaces` |

## Severity Levels

| Level | Criteria |
|-------|----------|
| HEALTHY | All peers state=6, no prefix drops, jitter < 10 ms, no BMP withdrawal storm |
| WARNING | ALERT-003/005/006 fired, or single prefix drop < 50% |
| HIGH | ALERT-002/004/007 fired, or multiple peers affected |
| CRITICAL | ALERT-001 fired on RR1 or ≥2 PE peers simultaneously |

## Integration

| Skill | When |
|-------|------|
| `lab-alert-triage` | Alert fired — confirm before deep RCA |
| `lab-troubleshoot` | Multi-symptom or unclear root cause |
| `pyats-health-check` | Device-side verification |
| `gnmi-telemetry` | Arista spine/leaf drill-down |
| `servicenow-change-workflow` | Remediation requires CR |