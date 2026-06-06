# BGP Route Observability — Production Architecture

**Status**: Approved design (2026-06-05)  
**Spec**: [specs/031-bgp-route-observability/spec.md](../../specs/031-bgp-route-observability/spec.md)  
**Workflow**: [GitHub spec-kit](https://github.com/github/spec-kit) — phased implementation via `tasks.md`

## Problem Statement

NOC agents need router-perspective BGP data to investigate route instability, correlate with physical-layer and path-quality signals, and act on threshold-based alerts. Protocol MCP metrics (NetClaw as a BGP speaker) do not represent the network RIB, are ephemeral, and do not scale.

## Design Goals

1. **Production scalability** — BMP for prefix-level events; gNMI for push state; SNMP for legacy fallback
2. **Agent experience (AX)** — One PromQL vocabulary (`netclaw_*`) for dashboards, alerts, and skills
3. **Lab validates production** — Same docker services; platform adapters differ (IOL = SNMP, cEOS = gNMI)
4. **Data before thresholds** — Baselining window before paging rules go live
5. **Spec-driven delivery** — Six phases, each with independent checkpoint

## Three Telemetry Planes

### Plane 1: BMP (BGP events)

Routers stream BGP UPDATEs to a collector. This is the production source of truth for per-prefix announcements and withdrawals.

```text
RR/PE ──BMP──> gobmp ──> Redpanda ──> bgp-normalizer ──> VictoriaMetrics
```

**Metrics**: `netclaw_bgp_prefix_announcements_total`, `netclaw_bgp_prefix_withdrawals_total`

**Lab**: IOL does not support BMP. Collector runs; metrics populate when production peers connect.

### Plane 2: State streaming (peer + prefix counts)

| Source | Platforms | Signals |
|--------|-----------|---------|
| gNMI Subscribe | Arista cEOS, prod IOS-XE/XR | peer state, prefixes received, ON_CHANGE |
| SNMP poll | Cisco IOL (lab), backup everywhere | BGP4-MIB, CISCO-BGP4-MIB |

**Metrics**: `netclaw_bgp_peer_state`, `netclaw_bgp_peer_prefixes_received`, `netclaw_bgp_peer_in_updates_total`, …

### Plane 3: Narrative (syslog + traps)

Syslog provides device-native context (`%BGP-5-ADJCHANGE`, `%LINEPROTO-5-UPDOWN`). SNMP traps (future) give immediate peer-down signals.

**Store**: Loki with `device_name` label

## Normalized Metric Schema

All consumers query `netclaw_*` only. See [contracts/metrics-schema.md](../../specs/031-bgp-route-observability/contracts/metrics-schema.md).

| Category | Example |
|----------|---------|
| Peer health | `netclaw_bgp_peer_state{device_name="rr1",neighbor="100.0.254.13"}` |
| Prefix count | `netclaw_bgp_peer_prefixes_received` |
| Prefix events (BMP) | `rate(netclaw_bgp_prefix_withdrawals_total[5m])` |
| Path quality | `netclaw_path_jitter_ms{device_name="pe2",probe_id="20"}` |

## Platform Adapter Matrix

| Platform | BMP | gNMI | SNMP BGP | Syslog |
|----------|-----|------|----------|--------|
| Cisco IOL (lab) | — | — | primary | primary |
| Arista cEOS (lab) | — | primary | backup | primary |
| Cisco IOS-XE/XR (prod) | primary | primary | backup | primary |

## NOC Agent Investigation Flow

```text
Grafana alert (netclaw_*)
    │
    ├─ PromQL: which device, neighbor, prefix?
    ├─ Loki: ADJCHANGE / UPDOWN on same device
    ├─ Correlate: interface_status + path jitter same window
    └─ Drill-down: pyATS show ip bgp / gNMI get (on-demand)
           │
           └─ gait_record + recommendation
```

Protocol MCP is **not** in this path. It remains for Scenario D injection demos only.

## Stack Components

| Component | Image / path | Role |
|-----------|--------------|------|
| OTEL Collector | `observability/otel-collector/` | SNMP, syslog, gNMI |
| VictoriaMetrics | existing compose | Metrics TSDB |
| Loki | existing compose | Syslog |
| Grafana | existing compose | Dashboards + alerts |
| Redpanda | `docker-compose.bmp.yml` | Event bus |
| gobmp | `docker-compose.bmp.yml` | BMP collector |
| bgp-normalizer | `observability/exporters/` | Kafka → VM write |

## Implementation Phases

| Phase | Deliverable | Checkpoint |
|-------|-------------|------------|
| 1 | SNMP → `netclaw_bgp_*` | RR1 prefix count = 4 |
| 2 | IP SLA + Loki labels | Jitter + syslog panels |
| 3 | BMP pipeline | Services healthy |
| 4 | gNMI Arista stream | gnmi-sourced peer metrics |
| 5 | Alerts + skills + baselines | Agent RCA without Protocol MCP |
| 6 | Golden config BMP/gNMI | Prod templates in Nautobot |

Execute via [tasks.md](../../specs/031-bgp-route-observability/tasks.md) and `/speckit.implement`.

## Alerting Strategy

1. **Collect only** — Phases 1–4, no paging
2. **Baseline** — 7 days prod / 48h lab with scenarios ([baselines doc](../baselines/bgp-route-stability.md) — Phase 5)
3. **Enable rules** — Per [alert-rules.md](../../specs/031-bgp-route-observability/contracts/alert-rules.md)

## Related Artifacts

- Blog Part 15: [blog-part15-route-stability-observability.md](../blogs/blog-part15-route-stability-observability.md)
- Failure scenarios: [failure-scenarios.md](../failure-scenarios.md)
- Parent series: [specs/029-observability-series](../../specs/029-observability-series/spec.md)