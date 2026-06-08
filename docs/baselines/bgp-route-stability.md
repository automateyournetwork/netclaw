# BGP Route Stability Baselines

Baseline collection procedure and lab samples for **spec 031 Phase 5** alert thresholds.

**Contract**: [`specs/031-bgp-route-observability/contracts/alert-rules.md`](../../specs/031-bgp-route-observability/contracts/alert-rules.md)

---

## Procedure

1. Deploy Phases 1–4 (SNMP exporter, BMP stack, gNMI exporter, syslog VRF fix).
2. Collect steady state ≥48h (production: ≥7 days).
3. Run failure scenarios **B** and **C** (see below); record metric deltas.
4. Set ALERT-005 multiplier from measured p95 UPDATE rate (default: 3×).
5. Enable CRITICAL/HIGH rules first; WARNING after false-positive review.

### Queries to record (Grafana Explore or VM API)

```promql
# Peer prefix counts (steady state)
netclaw_bgp_peer_prefixes_received{device_name="rr1",neighbor="100.0.254.13"}

# UPDATE rate p50/p95 per peer
quantile_over_time(0.95, rate(netclaw_bgp_peer_in_updates_total[5m])[1d:])

# Path jitter p95 per PE
max_over_time(netclaw_path_jitter_ms{device_name=~"pe.*"}[1d])

# gNMI peer state (Arista)
netclaw_bgp_peer_state{source="gnmi",device_name="west-spine01"}
```

---

## Steady-State Samples (2026-06-06, CSR + cEOS lab)

Collected after Phases 1–4 PASS; stack uptime ~4h (lab abbreviated window — re-run after 48h for production tuning).

| Metric | Device | Value | Notes |
|--------|--------|-------|-------|
| `netclaw_bgp_peer_prefixes_received` | rr1 → 100.0.254.13 | **4** | Service prefix count via SNMP |
| `netclaw_bgp_peer_state` | rr1 peers | **6** | All established |
| `netclaw_bgp_peer_state` | west-spine01 → 100.2.11.1 | **6** | gNMI, AS 65200 |
| `netclaw_bgp_peer_prefixes_received` | west-spine01 → 100.2.11.1 (ipv4) | **4** | gNMI OpenConfig |
| `netclaw_path_jitter_ms` | pe1, pe2, pe3 probes | **1** ms | IP SLA probe 10/20 |
| `netclaw_path_jitter_ms` | ce1, ce2 | **0** ms | |
| `rate(netclaw_bgp_peer_in_updates_total[5m])` | fleet p95 | **0** | Quiet steady state |
| `netclaw_bgp_prefix_announcements_total` | rr1 (BMP live) | increasing | RR1 BMP TCP Up |

### Recommended thresholds (from steady state)

| Alert | Threshold | Rationale |
|-------|-----------|-----------|
| ALERT-001 | `!= 6` for 2m | Direct BGP4-MIB / OpenConfig mapping |
| ALERT-002 | `< 0.8 × 1h avg` for 5m | 20% drop catches Scenario C |
| ALERT-006 | `> 30` ms for 10m | Steady state 1 ms → 30× headroom |
| ALERT-005 | `> 3× 1d avg` | No UPDATE activity at rest; 3× safe for lab |

---

## Scenario B — PE1 link flap (single uplink)

**Trigger** (CSR lab):

```text
configure terminal
interface GigabitEthernet2
 shutdown
end
```

**Expected signals** (within 2–5 min):

| Signal | Query | Expected |
|--------|-------|----------|
| Interface down | `interface_status{device_name="pe1",interface="GigabitEthernet2",job="netclaw-bgp-snmp"}` | → 2 (down) |
| Interface change | `changes(interface_status{device_name="pe1",job="netclaw-bgp-snmp"}[5m])` | > 0 |
| Grafana | Lab Interface Down | Fires ~3 min after shutdown |
| Syslog | `{device_name="pe1"} \|~ "UPDOWN"` | LINEPROTO UPDOWN |
| BGP activity | `rate(netclaw_bgp_peer_in_updates_total{device_name="pe1"}[5m])` | May spike briefly |
| Correlation alert | ALERT-007 | Fires if UPDATE rate > 0 |

**Restore:**

```text
configure terminal
interface GigabitEthernet2
 no shutdown
end
```

**Scenario B run (2026-06-06, automated)**: `bash scripts/observability/run-scenario-b.sh`:

- Loki: `%LINEPROTO-5-UPDOWN` within 2 min
- `interface_status` → **2** via `bgp-snmp-exporter` (~90s after shutdown)
- **Lab Interface Down** Grafana alert fires (~3 min)
- `netclaw_bgp_peer_state != 6` → **0** (dual-homed; expected)
- ALERT-007 did not fire (no BGP UPDATE spike — expected)

**Scenario C run (2026-06-06, automated)**: `bash scripts/observability/run-scenario-c.sh`:

- Gi2 + Gi3 shutdown → RR peer Idle in SNMP ~**200s**
- **ALERT-001** + **ALERT-003** fire after `for: 2m`
- Loki ADJCHANGE/UPDOWN storm present

---

## Scenario C — PE1 dual link loss

**Trigger**: Shut **GigabitEthernet2** and **GigabitEthernet3** on PE1.

**Expected signals**:

| Signal | Expected |
|--------|----------|
| ALERT-001 | `netclaw_bgp_peer_state{device_name="pe1"} != 6` on core-facing peers |
| ALERT-002 | Prefix count drop on affected neighbors |
| Syslog | Multiple ADJCHANGE / UPDOWN |
| Skill | `bgp-route-stability-watch` classifies **physical-layer** |

**Note**: Run during maintenance window; restore both interfaces after validation.

---

## Scenario D — Protocol MCP injection (demo only)

Synthetic flap via Protocol MCP does **not** produce interface correlation or router-native BMP/SNMP signals. Use only for injection blog demos — not for alert baselining.

See [`docs/failure-scenarios.md`](../failure-scenarios.md#4-route-flap-via-protocol-mcp-demo-only).

---

## Re-baseline Checklist

- [ ] After golden-config redeploy (Phase 6)
- [ ] After CSR → new image migration
- [ ] After BMP collector IP change
- [ ] Quarterly in production NOC