---
name: bgp-route-stability-watch
description: "Monitor BGP route stability — detect route flaps, correlate with interface bounces, check jitter/loss, and determine root cause. Use when investigating route instability, prefix flapping, or path quality degradation."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["GRAFANA_URL", "NETCLAW_BGP_PEERS"] } } }
---

# BGP Route Stability Watch

## When to Use

- BGP routes are being withdrawn and re-announced repeatedly (flapping)
- Interface error counters are climbing on SP core links
- IP SLA jitter or packet loss exceeds thresholds
- You suspect a physical layer issue (bad optic, flapping port) is causing routing instability
- Heartbeat check detects elevated withdrawal rates

## Data Sources

| Source | What It Provides | How to Query |
|--------|-----------------|--------------|
| Protocol MCP | Live RIB, flap penalties, peer state | `bgp_get_rib`, `bgp_get_peers`, `protocol_summary` |
| Prometheus/VictoriaMetrics | `bgp_route_withdrawals_total`, `interface_status`, `ip_sla.*` | Grafana MCP `query_prometheus` |
| Loki | `%LINEPROTO-5-UPDOWN`, `%BGP-5-ADJCHANGE` syslog | Grafana MCP `query_loki_logs` |
| pyATS | Device-side `show ip bgp summary`, `show interfaces` | pyATS MCP |

## Procedure

### Step 1: Check BGP Route Withdrawal Rate

Query Prometheus for elevated withdrawal rates across all prefixes:

```
query_prometheus(expr="rate(bgp_route_withdrawals_total[5m]) > 0", time_range="30m")
```

**GATE:** If no withdrawals in the last 30 minutes → report HEALTHY, stop.

### Step 2: Identify Affected Prefixes

From the withdrawal rate results, extract the prefix labels. Then query the Protocol MCP for current flap damping state:

```
protocol_summary()
bgp_get_rib(prefix="<affected_prefix>")
```

Record:
- Which prefixes are flapping
- Current penalty level (0-3000 scale)
- Whether any are suppressed (penalty ≥ 3000)

### Step 3: Correlate with Interface Status Changes

For each affected prefix, determine the next-hop device. Then check if that device's interfaces are bouncing:

```
query_prometheus(expr="changes(interface_status{device_name='<next_hop_device>'}[5m]) > 0", time_range="30m")
```

**GATE:** If interface flaps found on the next-hop device within the same time window as route withdrawals → proceed to Step 4 (port bounce is likely root cause).

If NO interface flaps → skip to Step 5 (external cause).

### Step 4: Confirm Port Bounce Root Cause

Query Loki for syslog messages confirming the interface state change:

```
query_loki_logs(query='{device_name="<device>"} |~ "UPDOWN|LINEPROTO"', time_range="30m")
```

Also check error counters on the bouncing interface:

```
query_prometheus(expr="rate(interface_errors_in{device_name='<device>',interface='<iface>'}[5m])")
query_prometheus(expr="rate(interface_errors_out{device_name='<device>',interface='<iface>'}[5m])")
```

**Verdict:** "Route flap on `<prefix>` caused by interface instability on `<device>` `<interface>`. Interface bounced `<N>` times in 5 minutes, causing `<M>` route withdrawals. Error rate: `<X>` errors/sec."

### Step 5: Check Path Quality (Jitter/Loss)

Even without interface bounces, path degradation can cause BGP hold-timer expiry:

```
query_prometheus(expr="ip_sla_jitter_avg{device_name=~'pe.*|ce.*'}", time_range="30m")
query_prometheus(expr="rate(ip_sla_packet_loss_sd[5m])", time_range="30m")
query_prometheus(expr="ip_sla_rtt{device_name=~'pe.*|ce.*'}", time_range="30m")
```

**Thresholds:**
| Metric | HEALTHY | WARNING | CRITICAL |
|--------|---------|---------|----------|
| Jitter (avg) | < 10ms | 10-50ms | > 50ms |
| Packet Loss | 0% | < 1% | > 1% |
| RTT | < 50ms | 50-200ms | > 200ms |

### Step 6: Check for External BGP Events

If no local interface or path quality issues, the flap may be from an external peer:

```
bgp_get_rib(prefix="<affected_prefix>")
```

Check the AS_PATH — if it changed between announcements, the instability is upstream (not our fault).

Query Loki for BGP NOTIFICATION messages:

```
query_loki_logs(query='{device_name="rr1"} |~ "BGP-5-ADJCHANGE|BGP-3-NOTIFICATION"', time_range="30m")
```

### Step 7: Generate Report

```
╔══════════════════════════════════════════════════════════════╗
║           BGP ROUTE STABILITY REPORT                        ║
╠══════════════════════════════════════════════════════════════╣
║ Time Window: <start> — <end>                                ║
║ Status: <HEALTHY | WARNING | CRITICAL>                      ║
╠══════════════════════════════════════════════════════════════╣
║ ROUTE FLAPS                                                 ║
║   Prefixes affected: <count>                                ║
║   Total withdrawals (5m): <count>                           ║
║   Suppressed routes: <count>                                ║
║   Max penalty: <value>/3000                                 ║
╠══════════════════════════════════════════════════════════════╣
║ ROOT CAUSE                                                  ║
║   <description>                                             ║
║   Device: <device>                                          ║
║   Interface: <interface>                                    ║
║   Bounces (5m): <count>                                     ║
║   Error rate: <X> errors/sec                                ║
╠══════════════════════════════════════════════════════════════╣
║ PATH QUALITY                                                ║
║   Jitter (avg): <X> ms                                      ║
║   Packet Loss: <X>%                                         ║
║   RTT (avg): <X> ms                                         ║
╠══════════════════════════════════════════════════════════════╣
║ RECOMMENDATION                                              ║
║   <action>                                                  ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 8: GAIT Audit Trail

Record the stability check in the audit trail:

```
gait_record(
  operation="bgp-route-stability-watch",
  result=<HEALTHY|WARNING|CRITICAL>,
  prefixes_affected=<list>,
  root_cause=<description>,
  recommendation=<action>
)
```

## Severity Levels

| Level | Criteria |
|-------|----------|
| HEALTHY | No withdrawals in 30m, all penalties at 0, jitter < 10ms, loss = 0% |
| WARNING | Withdrawals detected but penalty < 2000, OR jitter 10-50ms, OR loss < 1% |
| HIGH | Penalty approaching suppress (2000-3000), OR jitter > 50ms, OR loss > 1% |
| CRITICAL | Routes suppressed (penalty ≥ 3000), OR multiple prefixes flapping, OR loss > 5% |

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **protocol-participation** | Direct RIB access, flap penalty data, peer state |
| **grafana-observability** | PromQL queries for interface status, IP SLA metrics, Loki log correlation |
| **pyats-health-check** | Device-side verification of interface state and BGP neighbor status |
| **servicenow-change-workflow** | If remediation needed (shut/no shut, replace optic), gate via CR |
| **slack-network-alerts** | Send severity-formatted alert when CRITICAL threshold hit |
| **gait-session-tracking** | Immutable record of every stability check and finding |
