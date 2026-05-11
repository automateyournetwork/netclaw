---
name: lab-noc-watch
description: "Quick fleet health check via observability metrics. Reports interface status, error rates, traffic anomalies, and routing state across all lab devices. Use for periodic NOC monitoring or when asked about overall network health."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["GRAFANA_URL"] } } }
---

# Lab NOC Watch

## When to Use

- User asks "how's the network?" or "any issues?"
- Periodic heartbeat health check
- Before/after a maintenance window
- Quick sanity check after deploying config changes

## Procedure

### Step 1: Fleet Interface Status

Query for down interfaces (excluding known-unused ports):

```
query_prometheus(expr="interface_status == 2")
```

Filter out expected-down interfaces (Ethernet1/1, 1/2, 1/3 on P routers are unused).

Report: `<N>` interfaces down across `<M>` devices. Flag any unexpected downs.

### Step 2: Error Rate Check

```
query_prometheus(expr="sum(rate(interface_errors_in_total[5m])) by (device_name) > 0")
query_prometheus(expr="sum(rate(interface_errors_out_total[5m])) by (device_name) > 0")
```

**Thresholds:**
- 0 errors/s → HEALTHY
- < 1 error/s → WARNING (monitor)
- > 1 error/s → HIGH (investigate)

### Step 3: Interface Flaps

```
query_prometheus(expr="changes(interface_status[10m]) > 0")
```

Any interface that changed state in the last 10 minutes is flagged.

### Step 4: Traffic Summary

```
query_prometheus(expr="sum(rate(interface_octets_in_bytes_total[5m])) by (device_name) * 8")
```

Report top 5 busiest devices by inbound traffic.

### Step 5: BGP State (if Protocol MCP active)

```
query_prometheus(expr="bgp_rib_size")
query_prometheus(expr="bgp_peer_state")
query_prometheus(expr="bgp_route_flap_penalty > 0")
```

### Step 6: Generate Summary

```
╔══════════════════════════════════════════════════════════════╗
║              NOC WATCH — FLEET HEALTH SUMMARY               ║
╠══════════════════════════════════════════════════════════════╣
║ Devices monitored: <N>                                      ║
║ Interfaces up/down: <up>/<down>                             ║
║ Error rate (fleet): <X> errors/s                            ║
║ Interface flaps (10m): <N>                                  ║
║ BGP RIB size: <N> routes                                    ║
║ BGP peers: <up>/<total>                                     ║
║                                                             ║
║ Status: <HEALTHY | WARNING | CRITICAL>                      ║
╠══════════════════════════════════════════════════════════════╣
║ ISSUES (if any):                                            ║
║   • <device> <interface>: <issue>                           ║
╚══════════════════════════════════════════════════════════════╝
```

### Step 7: GAIT Audit Trail

```
gait_record(
  operation="lab-noc-watch",
  status=<HEALTHY|WARNING|CRITICAL>,
  devices_monitored=<count>,
  issues_found=<list>
)
```

## Severity Levels

| Level | Criteria |
|-------|----------|
| HEALTHY | All expected interfaces up, zero errors, no flaps, BGP stable |
| WARNING | Minor errors (<1/s), or 1-2 interface flaps, or BGP penalty > 0 |
| CRITICAL | Unexpected interface down, errors > 1/s, multiple flaps, or BGP routes suppressed |
