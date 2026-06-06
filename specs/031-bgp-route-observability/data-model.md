# Data Model: BGP Route Observability Metrics

**Feature**: `031-bgp-route-observability` | **Date**: 2026-06-05

## Design Principles

1. **Single vocabulary**: All dashboards, alerts, and skills use `netclaw_*` names only.
2. **Required labels**: Every series MUST include `device_name`; BGP series MUST include `neighbor` where applicable.
3. **Source-agnostic**: Adapters map SNMP, gNMI, and BMP into this schema; `source` label is optional debug metadata.
4. **Prometheus types**: Counters end with `_total`; gauges use base names.

## BGP Peer Metrics

### `netclaw_bgp_peer_state` (gauge)

| Label | Example | Description |
|-------|---------|-------------|
| device_name | rr1 | Collecting router |
| neighbor | 100.0.254.13 | Peer address |
| peer_as | 65000 | Remote AS |
| vrf | default | VRF name (if applicable) |

**Values**: Map BGP4-MIB `bgpPeerState` — 6=established (export as 1 for agent simplicity **or** raw enum; **decision: export raw enum, document in contract**).

**Adapter priority**: gNMI OpenConfig `session-state` > SNMP `bgpPeerState`

---

### `netclaw_bgp_peer_prefixes_received` (gauge)

Prefixes accepted from peer (Cisco: `cbgpPeerPrefixAccepted`; gNMI: `prefixes/received`).

| Label | Required |
|-------|----------|
| device_name, neighbor, peer_as, afi, safi | yes |

---

### `netclaw_bgp_peer_in_updates_total` (counter)

SNMP `bgpPeerInUpdates` or gNMI equivalent. Use `rate()` for UPDATE activity proxy.

---

### `netclaw_bgp_peer_out_updates_total` (counter)

SNMP `bgpPeerOutUpdates`.

---

### `netclaw_bgp_peer_established_transitions_total` (counter)

SNMP `bgpPeerFsmEstablishedTransitions` — session bounce detector.

---

### `netclaw_bgp_peer_uptime_seconds` (gauge)

SNMP `bgpPeerFsmEstablishedTime`.

---

## BGP Prefix Metrics (BMP plane)

### `netclaw_bgp_prefix_announcements_total` (counter)

| Label | Example |
|-------|---------|
| device_name | rr1 |
| prefix | 192.168.99.0/24 |
| peer | 100.0.254.13 |
| peer_as | 65000 |
| afi | ipv4 |

**Source**: BMP route monitor messages only.

---

### `netclaw_bgp_prefix_withdrawals_total` (counter)

Same labels as announcements. Primary signal for route flap detection at scale.

---

## RIB Aggregate Metrics

### `netclaw_bgp_rib_routes_total` (gauge)

| Label | Description |
|-------|-------------|
| device_name | Router |
| afi | ipv4 / ipv6 |

**Sources**: SNMP aggregate where available; pyATS poller `show ip bgp summary` networks count; BMP statistics message.

---

## Path Quality Metrics

### `netclaw_path_rtt_ms` (gauge)

| Label | Example |
|-------|---------|
| device_name | pe2 |
| probe_id | 10 |
| probe_type | udp-jitter |
| destination | 100.0.254.13 |

**SNMP OID**: `1.3.6.1.4.1.9.9.42.1.2.10.1.1.{probe_id}`

---

### `netclaw_path_jitter_ms` (gauge)

**SNMP OID**: `1.3.6.1.4.1.9.9.42.1.5.2.1.4.{probe_id}` (avg jitter — **not** `.46.{id}.1`)

---

### `netclaw_path_loss_packets` (gauge)

**SNMP OID**: `1.3.6.1.4.1.9.9.42.1.5.2.1.26.{probe_id}` (source-to-destination loss)

---

## Interface Metrics (existing — rename optional)

Existing `interface_status` series remain; skills correlate via `device_name` + `interface` labels. Phase 2 may add alias `netclaw_interface_oper_state` — **deferred** to avoid breaking Part 13 dashboards.

## Loki Label Model

| Label | Source | Required |
|-------|--------|----------|
| device_name | OTEL transform from `net.peer.ip` | yes |
| device_ip | OTEL transform | yes |
| service_name | network-devices | yes |
| job | network-devices | yes |

Log body retains raw syslog text for `|~ "BGP|UPDOWN"` filtering.

## Entity Relationships

```text
Device (rr1, pe1, …)
  └── BGPSession (neighbor, peer_as, vrf)
        ├── PeerMetrics (state, prefixes, updates, uptime)
        └── PrefixEvents (BMP only: prefix, announcement/withdrawal)
  └── IPSLAProbe (probe_id, destination)
        └── PathMetrics (rtt, jitter, loss)
  └── Interface (ifIndex, ifName)
        └── OperState (correlation)
```

## Deprecated Metrics (do not use in new artifacts)

| Old metric | Replacement |
|------------|-------------|
| `bgp_route_withdrawals_total` (Protocol MCP) | `netclaw_bgp_prefix_withdrawals_total` (BMP) or peer update rates (SNMP) |
| `bgp_rib_size` (Protocol MCP) | `netclaw_bgp_rib_routes_total` |
| `bgp_peer_state` (Protocol MCP) | `netclaw_bgp_peer_state` |
| `ip_sla_jitter_avg_milliseconds` (broken OID) | `netclaw_path_jitter_ms` |