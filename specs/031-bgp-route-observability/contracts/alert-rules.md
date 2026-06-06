# Contract: BGP Route Stability Alert Rules

**Feature**: `031-bgp-route-observability` | **Version**: 1.0.0

Alerts use **only** `netclaw_*` metrics. Enable paging after baseline window (see thresholds).

## Severity Model

| Severity | Response | Agent skill |
|----------|----------|-------------|
| CRITICAL | Page on-call | `bgp-route-stability-watch` + `lab-alert-triage` |
| HIGH | Ticket + notify | `bgp-route-stability-watch` |
| WARNING | Dashboard + digest | `lab-noc-watch` |

## Rules (Grafana provisioning)

### ALERT-001: BGP peer not established

```yaml
name: netclaw-bgp-peer-down
expr: netclaw_bgp_peer_state{device_name=~"rr1|pe.*"} != 6
for: 2m
severity: critical
annotations:
  summary: BGP peer {{ $labels.neighbor }} down on {{ $labels.device_name }}
```

### ALERT-002: Prefix count drop

```yaml
name: netclaw-bgp-prefix-drop
expr: |
  (
    netclaw_bgp_peer_prefixes_received
    < 0.8 * avg_over_time(netclaw_bgp_peer_prefixes_received[1h])
  ) and netclaw_bgp_peer_prefixes_received > 0
for: 5m
severity: high
```

### ALERT-003: Session re-establishment

```yaml
name: netclaw-bgp-session-flap
expr: increase(netclaw_bgp_peer_established_transitions_total[15m]) > 0
for: 0m
severity: warning
```

### ALERT-004: BMP withdrawal rate (production)

```yaml
name: netclaw-bgp-prefix-withdrawal-rate
expr: sum by (device_name, prefix) (rate(netclaw_bgp_prefix_withdrawals_total[5m])) > 0.05
for: 5m
severity: high
# Lab: may not fire until BMP peer connected
```

### ALERT-005: SNMP UPDATE storm (lab fallback)

```yaml
name: netclaw-bgp-update-rate-high
expr: |
  rate(netclaw_bgp_peer_in_updates_total[5m])
  > 3 * avg_over_time(rate(netclaw_bgp_peer_in_updates_total[5m])[1d:])
for: 5m
severity: warning
```

### ALERT-006: Path jitter elevated

```yaml
name: netclaw-path-jitter-high
expr: max by (device_name) (netclaw_path_jitter_ms{device_name=~"pe.*|ce.*"}) > 30
for: 10m
severity: warning
```

### ALERT-007: Interface oper change + BGP activity

```yaml
name: netclaw-interface-bgp-correlation
expr: |
  changes(interface_status{device_role=~"pe|p"}[5m]) > 0
  and on(device_name) rate(netclaw_bgp_peer_in_updates_total[5m]) > 0
for: 2m
severity: high
```

## Baselining Procedure (before enabling FOR durations)

1. Deploy Phases 1–2; run stack ≥7 days (lab: run Scenarios B/C + steady state 48h).
2. Record in Grafana:
   - p50/p95 `rate(netclaw_bgp_peer_in_updates_total[5m])` per peer
   - Steady `netclaw_bgp_peer_prefixes_received` per peer
   - p95 `netclaw_path_jitter_ms` per PE probe
3. Set ALERT-005 multiplier from measured p95.
4. Enable CRITICAL/HIGH rules first; WARNING after false-positive review.

## Agent Runbook Mapping

| Alert | Step 1 PromQL | Step 2 LogQL | Step 3 drill-down |
|-------|---------------|--------------|-------------------|
| ALERT-001 | peer_state | `{device_name="X"} \|~ "ADJCHANGE"` | pyATS `show ip bgp summary` |
| ALERT-002 | prefixes_received | same | pyATS `show ip bgp neighbors X received` |
| ALERT-004 | withdrawals by prefix | BMP-correlated syslog | pyATS `show ip bgp <prefix>` |
| ALERT-006 | jitter by probe | — | pyATS `show ip sla statistics` |
| ALERT-007 | interface_status changes | `UPDOWN` | pyATS `show interfaces` |