# Lab Failure Scenarios

Injectable failures for the Nautobot Workshop lab observability demos (Part 14–15). Each scenario lists the trigger, expected telemetry, and the NetClaw skill to run for triage.

**Prerequisites:** Observability stack running (`observability/docker-compose.observability.yml` + BMP/gNMI overlays), SNMP/syslog on devices, Grafana alerts provisioned under folder **Lab Network**.

**Metrics plane:** Router-native `netclaw_*` only. Protocol MCP is **demo-only** (Scenario D).

---

## A. Interface shutdown (L1/L2)

**Trigger:** On a PE or P router, shut a core-facing interface.

CSR lab (PE1 example):

```text
configure terminal
interface GigabitEthernet2
 shutdown
end
```

**Expected telemetry**

- `changes(interface_status{device_name="pe1"}[5m]) > 0`
- Grafana alert **Lab Interface Down** or **netclaw-interface-bgp-correlation** (ALERT-007) within ~2 minutes
- Syslog: `%LINEPROTO-5-UPDOWN` in Loki `{device_name="pe1"}`

**NetClaw:** `lab-alert-triage` → `lab-troubleshoot`

**Restore:** `no shutdown` on the interface.

---

## B. BGP peer loss — single link flap (L3)

**Trigger:** Shut one PE uplink (Scenario B in Part 15 blog). PE may stay established on alternate path if dual-homed.

```text
interface GigabitEthernet2
 shutdown
```

**Expected telemetry**

- `changes(interface_status{device_name="pe1"}[5m])` on affected link
- `rate(netclaw_bgp_peer_in_updates_total{device_name="pe1"}[5m])` may spike briefly
- Syslog: `%LINEPROTO-5-UPDOWN`; `%BGP-5-ADJCHANGE` if session drops
- ALERT-007 if interface change coincides with BGP UPDATE activity

**NetClaw:** `bgp-route-stability-watch` → `lab-troubleshoot`

**Restore:** `no shutdown` on the interface.

---

## C. Dual link loss (L3)

**Trigger:** Shut **both** core-facing interfaces on a PE (e.g. PE1 Gi2 + Gi3).

**Expected telemetry**

- `netclaw_bgp_peer_state{device_name="pe1"} != 6` on affected neighbors (ALERT-001)
- `netclaw_bgp_peer_prefixes_received` drop ≥20% from 1h avg (ALERT-002)
- Syslog: ADJCHANGE + UPDOWN storm

**NetClaw:** `bgp-route-stability-watch` (root cause: **physical-layer**)

**Restore:** `no shutdown` on both interfaces.

---

## D. Route flap via Protocol MCP (demo only)

> **Not part of the production monitoring plane.** Protocol MCP injects routes into NetClaw's synthetic BGP speaker (AS 65099). Router-native metrics (`netclaw_bgp_*` from SNMP/gNMI/BMP) do **not** reflect these withdrawals unless correlated interface events occur.

**Trigger:** Use `scripts/scenario-d-flap.py` or Protocol MCP inject/withdraw loop.

**Expected telemetry (demo path only)**

- Legacy `bgp_route_*` metrics from Protocol MCP scrape (if gateway running)
- BGP Route Stability dashboard may show injection panels
- **No** `interface_status` correlation; **no** RR1 BMP withdrawal storm from injection alone

**NetClaw:** `bgp-route-stability-watch` should classify as **synthetic-demo** if only Protocol MCP signals present.

**Restore:** Stop flap script; clear lab BGP session.

**Run:**

```bash
bash scripts/run-scenario-d.sh
```

---

## E. Interface error storm (L2)

**Trigger:** Flap an interface repeatedly or induce errors on a test port.

**Expected telemetry**

- `rate(interface_errors_in_total[5m]) > 0`
- Grafana alert **Lab Interface Errors**
- Possible `changes(interface_status[10m]) > 0`

**NetClaw:** `lab-alert-triage` → `lab-troubleshoot`

---

## F. Path quality degradation (IP SLA)

**Trigger:** Blackhole or rate-limit path between PE probes.

**Expected telemetry**

- `netclaw_path_jitter_ms` / `netclaw_path_rtt_ms` elevated
- ALERT-006 **netclaw-path-jitter-high** if > 30 ms for 10m

**NetClaw:** `bgp-route-stability-watch` (path-quality class) → `lab-troubleshoot`

---

## Demo script (Part 14)

1. Run `lab-noc-watch` — baseline HEALTHY.
2. Execute scenario **A** on PE1 `GigabitEthernet2`.
3. Run `lab-alert-triage` — confirm interface alert.
4. Run `lab-troubleshoot` — correlate metrics, Loki, `show ip interface brief`.
5. Restore interface; re-run `lab-noc-watch`.

## Demo script (Part 15)

1. Execute scenario **B** (PE1 single link flap).
2. Ask: "Are any routes unstable?" — use `bgp-route-stability-watch`.
3. Correlate `netclaw_bgp_*` + `interface_status` + Loki (no Protocol MCP RIB).
4. Optional: scenario **D** to contrast synthetic injection vs router-native signals.

See [`docs/blogs/blog-part15-route-stability-observability.md`](blogs/blog-part15-route-stability-observability.md) and [`docs/baselines/bgp-route-stability.md`](baselines/bgp-route-stability.md).