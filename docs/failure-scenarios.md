# Lab Failure Scenarios

Injectable failures for the Nautobot Workshop lab observability demos (Part 14–15). Each scenario lists the trigger, expected telemetry, and the NetClaw skill to run for triage.

**Prerequisites:** Observability stack running (`observability/docker-compose.observability.yml` + BMP/gNMI overlays), SNMP/syslog on devices, Grafana alerts provisioned under folder **Lab Network**.

**Environment:** Nautobot Workshop ContainerLab on `clab-mgmt` (192.168.220.0/24). pyATS via project venv: `bash scripts/observability/run-all-scenarios.sh --all` (uses `testbed/testbed.yaml`).

**Metrics plane:** Router-native `netclaw_*` from `bgp-snmp-exporter` (`job=netclaw-bgp-snmp`), BMP, gNMI. Cisco `interface_status` is **not** polled by OTEL (parallel SNMP timed out on IOL). Protocol MCP is **demo-only** (Scenario D).

**Automated validation:**

```bash
bash scripts/observability/validate-alert-scenarios.sh    # prerequisites + PromQL would-fire map
bash scripts/observability/run-all-scenarios.sh --all     # pyATS inject + Grafana alert gates
```

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

- `interface_status{device_name="pe1",interface="GigabitEthernet2",job="netclaw-bgp-snmp"} == 2`
- `changes(interface_status{device_name="pe1",job="netclaw-bgp-snmp"}[5m]) > 0`
- Grafana **Lab Interface Down** within ~3 minutes (`for: 2m` + 60s SNMP/scrape)
- Syslog: `%LINEPROTO-5-UPDOWN` in Loki `{device_name="pe1"}`

**NetClaw:** `lab-alert-triage` → `lab-troubleshoot`

**Run:** `bash scripts/observability/run-scenario-a.sh`

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
- ALERT-007 only if BGP UPDATE rate > 0 (often **absent** on dual-homed PE — peers stay Established)

**Run:** `bash scripts/observability/run-scenario-b.sh`

**NetClaw:** `bgp-route-stability-watch` → `lab-troubleshoot`

**Restore:** `no shutdown` on the interface.

---

## C. Dual link loss (L3)

**Trigger:** Shut **both** core-facing interfaces on a PE (e.g. PE1 Gi2 + Gi3).

**Expected telemetry**

- `netclaw_bgp_peer_state{device_name="pe1"} != 6` on affected neighbors (ALERT-001)
- `netclaw_bgp_peer_prefixes_received` drop ≥20% from 1h avg (ALERT-002)
- Syslog: ADJCHANGE + UPDOWN storm

**Timing:** RR peer shows `!= 6` in SNMP ~200s after dual shutdown; Grafana ALERT-001 ~2m after that.

**Run:** `bash scripts/observability/run-scenario-c.sh`

**NetClaw:** `bgp-route-stability-watch` (root cause: **physical-layer**)

**Restore:** `no shutdown` on both interfaces.

---

## D. Route flap via Protocol MCP (demo only)

> **Not part of the production monitoring plane.** Protocol MCP injects routes into NetClaw's synthetic BGP speaker (AS 65099). Router-native metrics (`netclaw_bgp_*` from SNMP/gNMI/BMP) do **not** reflect these withdrawals unless correlated interface events occur.

**Trigger:** Use `scripts/scenarios/scenario-d-flap.py` or Protocol MCP inject/withdraw loop.

**Expected telemetry (demo path only)**

- Legacy `bgp_route_*` metrics from Protocol MCP scrape (if gateway running)
- BGP Route Stability dashboard may show injection panels
- **No** `interface_status` correlation; **no** RR1 BMP withdrawal storm from injection alone

**NetClaw:** `bgp-route-stability-watch` should classify as **synthetic-demo** if only Protocol MCP signals present.

**Restore:** Stop flap script; clear lab BGP session.

**Run:**

```bash
bash scripts/observability/run-scenario-d.sh
```

---

## E. Rapid interface flaps (L2)

**Trigger:** Repeated shutdown/no shutdown on a non-core interface (lab: PE1 Gi4), paced with 60s SNMP scrape.

**Expected telemetry**

- `changes(interface_status{device_name="pe1",job="netclaw-bgp-snmp"}[5m]) > 4`
- Grafana **Lab Interface Rapid Flaps**

**Run:** `bash scripts/observability/run-scenario-e.sh`

**NetClaw:** `lab-alert-triage` → `lab-troubleshoot`

---

## F. Path quality degradation (IP SLA)

**Trigger:** ContainerLab netem on **P1 eth2** (PE1→PE2 probe path) — delay + jitter + loss while interfaces stay up.

```bash
containerlab tools netem set -t ~/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml \
  -n clab-nautobot_workshop-P1 -i eth2 --delay 120ms --jitter 100ms --loss 10
```

**Alternate trigger (validated):** netem on **PE1 Gi2** also drives **ALERT-006** on **pe3** — IP SLA probe 10 (udp-jitter to `100.0.254.11`/PE1) shows elevated jitter/RTT while probe 20 to PE2 stays ~1 ms. Useful asymmetric pattern for `lab-alert-triage` RCA (impairment on PE1 uplink, not a sensor fault on PE3).

**Expected telemetry**

- `netclaw_path_jitter_ms` > 20 ms and/or `netclaw_path_rtt_ms` > 60 ms on the affected probe path (PE1 for scripted F; **pe3** probe 10 when PE1 Gi2 is impaired)
- ALERT-006 **netclaw-path-jitter-high** (`for: 3m` in lab)

**Run:** `bash scripts/observability/run-scenario-f.sh` (automated netem via pyATS runner)

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