---
name: lab-troubleshoot
description: "Detect and diagnose network failures by correlating observability metrics (Grafana/Prometheus), syslog (Loki), and live device state (pyATS). Use when investigating connectivity issues, interface flaps, routing instability, or performance degradation in the lab."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["GRAFANA_URL", "PYATS_TESTBED_PATH"] } } }
---

# Lab Troubleshoot

## When to Use

- A user reports connectivity loss between two devices
- Grafana alerts fire for interface errors, flaps, or traffic drops
- BGP route withdrawals detected by bgp-route-stability-watch
- IP SLA jitter/loss exceeds thresholds
- You need to correlate metrics + logs + device state for root cause

## Data Sources

| Source | What It Provides | Tool |
|--------|-----------------|------|
| VictoriaMetrics | Interface status, traffic rates, errors, IP SLA | Grafana MCP `query_prometheus` |
| Loki | Device syslog (%LINEPROTO, %BGP, %OSPF events) | Grafana MCP `query_loki_logs` |
| pyATS | Live show commands (interfaces, routing, BGP, OSPF) | pyATS MCP |
| Protocol MCP | BGP RIB, peer state, flap penalties | `bgp_get_rib`, `protocol_summary` |

## Procedure

### Step 1: Identify the Symptom

Determine what's broken. Query for anomalies across all devices:

```
query_prometheus(expr="changes(interface_status[5m]) > 0")
query_prometheus(expr="rate(interface_errors_in_total[5m]) > 0")
query_prometheus(expr="rate(bgp_route_withdrawals_total[5m]) > 0")
```

**GATE:** If all queries return empty → report HEALTHY, stop.

### Step 2: Classify the Failure Type

Based on Step 1 results, classify:

| Symptom | Classification | Next Step |
|---------|---------------|-----------|
| Interface status changes | Physical layer (L1) | Step 3a |
| Error rate climbing | Data link (L2) | Step 3b |
| Route withdrawals | Routing (L3) | Step 3c |
| IP SLA jitter/loss spike | Path quality | Step 3d |
| No metrics anomaly but user reports issue | Silent failure | Step 3e |

### Step 3a: Physical Layer (Interface Flap)

```
query_prometheus(expr="changes(interface_status{device_name='<device>'}[10m])")
```

For each bouncing interface:
1. Get syslog confirmation:
   ```
   query_loki_logs(query='{service_name="network-devices"} |~ "<device>.*UPDOWN"', time_range="30m")
   ```
2. Check error counters on the device:
   ```
   pyats_run_command(device="<device>", command="show interfaces <interface>")
   ```
3. Check the remote end:
   ```
   pyats_run_command(device="<remote_device>", command="show interfaces <remote_interface>")
   ```

**Verdict template:** "`<device>` `<interface>` bouncing (`<N>` transitions in 10m). Error counters: `<CRC>` CRC, `<input_errors>` input errors. Likely cause: `<bad optic | cable | far-end down>`"

### Step 3b: Data Link Errors

```
pyats_run_command(device="<device>", command="show interfaces <interface> | include CRC|error|collision")
```

Correlate error type with likely cause:
- CRC errors → bad optic, cable, or duplex mismatch
- Input errors → oversized frames or encoding errors
- Output errors → congestion or buffer exhaustion
- Collisions → half-duplex (shouldn't exist in modern networks)

### Step 3c: Routing Instability

```
bgp_get_rib(prefix="<affected_prefix>")
query_prometheus(expr="bgp_route_flap_penalty")
pyats_run_command(device="<device>", command="show ip bgp <prefix>")
pyats_run_command(device="<device>", command="show ip route <prefix>")
```

Determine if the withdrawal is caused by:
1. Local interface flap (→ go to Step 3a)
2. Upstream peer instability (check AS_PATH changes)
3. Hold-timer expiry from path quality degradation (→ go to Step 3d)
4. Administrative action (check syslog for config changes)

### Step 3d: Path Quality Degradation

```
query_prometheus(expr="ip_sla_jitter_avg{device_name=~'pe.*|ce.*'}")
query_prometheus(expr="ip_sla_rtt{device_name=~'pe.*|ce.*'}")
query_prometheus(expr="rate(ip_sla_packet_loss_sd_total[5m])")
```

If degraded, trace the path hop-by-hop:
```
pyats_run_command(device="<source>", command="traceroute <destination>")
```

Check each hop's interface for errors or congestion.

### Step 3e: Silent Failure (No Metrics Anomaly)

When metrics look clean but connectivity is broken:
```
pyats_run_command(device="<source>", command="ping <destination>")
pyats_run_command(device="<source>", command="show ip route <destination>")
pyats_run_command(device="<source>", command="show ip cef <destination>")
```

Check for:
- Missing route (routing protocol issue)
- Blackhole route (null0)
- ACL blocking traffic
- MTU mismatch (ping with df-bit and various sizes)

### Step 4: Impact Assessment

Determine blast radius:
```
query_prometheus(expr="interface_status{device_name='<affected_device>'} == 2")
query_prometheus(expr="count(interface_status{device_name='<affected_device>'} == 1)")
```

Check if traffic is rerouting:
```
query_prometheus(expr="rate(interface_octets_in_bytes_total{device_name='<alternate_path_device>'}[5m])")
```

### Step 5: Generate Report

```
╔══════════════════════════════════════════════════════════════╗
║           NETWORK TROUBLESHOOTING REPORT                    ║
╠══════════════════════════════════════════════════════════════╣
║ Time: <timestamp>                                           ║
║ Status: <HEALTHY | DEGRADED | DOWN>                         ║
╠══════════════════════════════════════════════════════════════╣
║ SYMPTOM                                                     ║
║   <what was detected>                                       ║
╠══════════════════════════════════════════════════════════════╣
║ ROOT CAUSE                                                  ║
║   Device: <device>                                          ║
║   Interface: <interface>                                    ║
║   Failure type: <L1/L2/L3/path quality>                     ║
║   Evidence: <metrics + syslog + show command output>        ║
╠══════════════════════════════════════════════════════════════╣
║ IMPACT                                                      ║
║   Affected prefixes: <list>                                 ║
║   Traffic rerouting: <yes/no, via which path>               ║
║   Customer impact: <jitter/loss/outage>                     ║
╠══════════════════════════════════════════════════════════════╣
║ RECOMMENDATION                                              ║
║   Immediate: <action>                                       ║
║   Long-term: <action>                                       ║
║   ITSM: <CR required? yes/no>                               ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 6: GAIT Audit Trail

```
gait_record(
  operation="lab-troubleshoot",
  symptom=<description>,
  root_cause=<description>,
  impact=<description>,
  recommendation=<action>,
  devices_checked=<list>
)
```

## Severity Levels

| Level | Criteria |
|-------|----------|
| HEALTHY | No anomalies detected across all data sources |
| DEGRADED | Errors present but traffic flowing via alternate path, jitter elevated |
| DOWN | Interface down with no alternate path, or routes suppressed/missing |

## Integration with Other Skills

| Skill | When to Hand Off |
|-------|-----------------|
| **bgp-route-stability-watch** | If routing instability is the primary symptom |
| **pyats-health-check** | For comprehensive device health after root cause identified |
| **servicenow-change-workflow** | If remediation requires a change (shut/no shut, config fix) |
| **slack-network-alerts** | Send alert when DEGRADED or DOWN detected |
| **grafana-observability** | For deeper metric exploration during diagnosis |
