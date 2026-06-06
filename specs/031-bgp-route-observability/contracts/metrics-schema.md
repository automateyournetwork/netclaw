# Contract: netclaw BGP Metrics Schema

**Feature**: `031-bgp-route-observability` | **Version**: 1.0.0

## Prometheus Naming Rules

- Prefix: `netclaw_`
- Counters: `_total` suffix
- Units in name: `_seconds`, `_ms` (not `_milliseconds` — cleaner agent parsing)
- No high-cardinality labels: **never** label per-prefix gauges at steady state; per-prefix counters from BMP only

## Required Labels (all BGP metrics)

```yaml
required:
  - device_name   # lowercase nautobot device slug: rr1, pe2, west-spine01
optional:
  - neighbor      # peer IP string
  - peer_as       # string or int
  - vrf           # default if empty
  - afi           # ipv4 | ipv6
  - safi          # unicast | ...
  - source        # snmp | gnmi | bmp (debug)
```

## Metric Catalog

### Peer state

```promql
netclaw_bgp_peer_state{device_name="rr1", neighbor="100.0.254.13", peer_as="65000"}
# Values: BGP4-MIB enum (6 = established)
# Agent helper: netclaw_bgp_peer_state == 6
```

### Prefix count per peer

```promql
netclaw_bgp_peer_prefixes_received{device_name="rr1", neighbor="100.0.254.13", afi="ipv4", safi="unicast"}
```

### Session instability

```promql
rate(netclaw_bgp_peer_established_transitions_total[1h]) > 0
```

### UPDATE activity (SNMP proxy for flap)

```promql
rate(netclaw_bgp_peer_in_updates_total[5m])
```

### Per-prefix withdrawals (BMP — production)

```promql
rate(netclaw_bgp_prefix_withdrawals_total{prefix="192.168.99.0/24"}[5m])
```

### Path quality

```promql
netclaw_path_jitter_ms{device_name="pe2", probe_id="20"}
netclaw_path_rtt_ms{device_name="pe2", probe_id="10"}
```

## Adapter Mapping

### SNMP → netclaw (Cisco IOL)

| SNMP OID / object | netclaw metric |
|-------------------|----------------|
| bgpPeerState | netclaw_bgp_peer_state |
| cbgpPeerPrefixAccepted | netclaw_bgp_peer_prefixes_received |
| bgpPeerInUpdates | netclaw_bgp_peer_in_updates_total |
| bgpPeerOutUpdates | netclaw_bgp_peer_out_updates_total |
| bgpPeerFsmEstablishedTransitions | netclaw_bgp_peer_established_transitions_total |
| bgpPeerFsmEstablishedTime | netclaw_bgp_peer_uptime_seconds |
| rttMonJitterStatsAvgJitter (.1.5.2.1.4.{id}) | netclaw_path_jitter_ms |
| rttMonLatestRtt (.1.2.10.1.1.{id}) | netclaw_path_rtt_ms |

### gNMI OpenConfig → netclaw (Arista)

| YANG path | netclaw metric |
|-----------|----------------|
| `.../neighbors/neighbor/state/session-state` | netclaw_bgp_peer_state |
| `.../afi-safis/afi-safi/state/prefixes/received` | netclaw_bgp_peer_prefixes_received |

### BMP Kafka → netclaw

| BMP message | netclaw metric |
|-------------|----------------|
| Route Monitor ADD | netclaw_bgp_prefix_announcements_total |
| Route Monitor DEL | netclaw_bgp_prefix_withdrawals_total |
| Stats report | netclaw_bgp_rib_routes_total |

## VictoriaMetrics Remote Write

All adapters write via:

```text
POST http://192.168.220.201:8428/api/v1/write
Content-Type: application/x-protobuf (OTEL prometheusremotewrite)
```

Or Prometheus text exposition scraped from `bgp-normalizer:9100/metrics`.

## Validation Queries (checkpoint)

```bash
# Phase 1
curl -sf 'http://localhost:8428/api/v1/query?query=netclaw_bgp_peer_state{device_name="rr1"}'

# Phase 2
curl -sf 'http://localhost:8428/api/v1/query?query=netclaw_path_jitter_ms'

# Phase 3
curl -sf 'http://localhost:8428/api/v1/query?query=netclaw_bgp_prefix_withdrawals_total'
```