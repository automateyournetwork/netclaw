# Research: BGP Route Observability

**Feature**: `031-bgp-route-observability` | **Date**: 2026-06-05

## Decision Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Primary BGP event plane | BMP → Kafka/Redpanda → metrics exporter | Industry standard for per-prefix UPDATE visibility at scale |
| Primary state plane | gNMI OpenConfig Subscribe (Arista/prod) + SNMP fallback (IOL) | Push model scales; IOL lacks BMP/gNMI BGP |
| Narrative plane | Syslog → Loki + SNMP traps (future) | Device-native event text for agent RCA |
| Metric vocabulary | `netclaw_bgp_*` / `netclaw_path_*` normalized schema | Agents query one PromQL surface |
| Protocol MCP role | Injection demos only | Not router RIB; ephemeral metrics; GRE/session fragility |
| Event bus | Redpanda (lab/prod compatible) | Kafka API without full Kafka ops burden |
| BMP collector | gobmp | Active Go implementation, Kafka integration |
| Lab degradation | SNMP BGP4 + CISCO-BGP4 on IOL; gNMI on cEOS | Same pipeline, different adapter priority |

## SNMP MIB Research (Verified on Lab)

### BGP4-MIB (`1.3.6.1.2.1.15`) — RR1, PE2, Arista cEOS

| Column | OID suffix | Name | RR1 example (100.0.254.13) |
|--------|------------|------|------------------------------|
| 2 | `.3.1.2` | bgpPeerState | 6 (established) |
| 10 | `.3.1.10` | bgpPeerInUpdates | Counter32: 5 |
| 11 | `.3.1.11` | bgpPeerOutUpdates | Counter32: 34 |
| 15 | `.3.1.15` | bgpPeerFsmEstablishedTransitions | Counter32: 1 |
| 16 | `.3.1.16` | bgpPeerFsmEstablishedTime | Gauge32: 13714s |

**Limits**: No per-prefix withdrawal counter. `rate(bgpPeerInUpdates)` is a flap *proxy*, not ground truth.

### CISCO-BGP4-MIB (`1.3.6.1.4.1.9.9.187`) — Cisco IOL

| Table | OID | Metric |
|-------|-----|--------|
| cbgpPeerAddrFamilyPrefixTable | `.1.2.4.1.1.{peer}.{afi}.{safi}` | Prefixes accepted per peer |
| cbgpRouteTable | `.1.1.1.1` | Per-prefix entries (expensive at scale) |

**Verified**: `cbgpPeerPrefixAccepted` for peer `100.0.254.13` = **4**, matching `show ip bgp summary`.

### RTTMON-MIB (`1.3.6.1.4.1.9.9.42`) — PE2 IP SLA

| Metric | Wrong OID (current) | Correct OID | PE2 value |
|--------|---------------------|-------------|-----------|
| RTT | `.1.2.10.1.1.{probe}` | same | 0 (gauge; CLI shows RTT=1) |
| Avg jitter | `.1.5.2.1.46.{probe}.1` | **`.1.5.2.1.4.{probe}`** | probe 20 = 1 ms |
| Loss SD | `.1.5.2.1.26.{probe}.1` | **`.1.5.2.1.26.{probe}`** | 0 |

OTEL logs confirm `.46.*` returns "data not found" on every PE scrape.

## BMP Research

- **RFC 7854**: Routers stream BGP UPDATEs to collector (initiation, peer up/down, route monitor, statistics).
- **gobmp**: Parses BMP → Kafka topics; suitable for containerized deploy.
- **Lab constraint**: Cisco IOL — `show bmp` unavailable. Collector runs idle until production IOS-XE/XR peers connect.
- **Production**: RR/PE enable `router bmp` → collector IP; per-prefix counters exported via consumer.

## gNMI Research

- Arista cEOS: gNMI **running on port 6030** (`show management api gnmi`).
- OpenConfig paths for BGP neighbors, session-state, prefixes-received.
- NetClaw `gnmi-mcp` already supports Arista vendor dialect.
- OTEL Collector contrib `gnmi` receiver can remote_write to VictoriaMetrics (Phase 4).

## Syslog Research

- Loki receives OTLP-formatted logs with `service_name=network-devices`.
- BGP `%BGP-5-ADJCHANGE` events present in log body from East-Spine02.
- `device_name` transform runs but is **not** promoted to Loki index labels — breaks skill queries and dashboard.
- Dashboard LogQL `| json` is incompatible with OTLP log structure.

## Protocol MCP Post-Mortem

| Issue | Impact |
|-------|--------|
| Lazy start via OpenClaw gateway | Metrics absent unless MCP invoked |
| Monitors NetClaw speaker, not router RIB | Dashboard shows wrong perspective |
| Port 179 / GRE dependency | Session fragile; RR1 peer often Idle |
| Per-prefix withdrawals only on inject | Not representative of network failures |

**Conclusion**: Retain for Scenario D injection blog demo; remove from monitoring critical path.

## Alternatives Considered

| Alternative | Rejected because |
|-------------|------------------|
| SNMP-only forever | No per-prefix withdrawals; poll latency at scale |
| pyATS poll entire RIB every 60s | Does not scale; fragile CLI parsing |
| Protocol MCP as primary | Wrong data source; not production pattern |
| Full OpenBMP + MySQL | Heavier than gobmp + VM for initial deploy |
| Mimir day-one | VictoriaMetrics sufficient for lab; Mimir when multi-tenant |

## References

- [BGP4-MIB RFC 4273](https://www.rfc-editor.org/rfc/rfc4273)
- [BMP RFC 7854](https://www.rfc-editor.org/rfc/rfc7854)
- [gobmp](https://github.com/sbezverk/gobmp)
- [OpenConfig BGP YANG](https://openconfig.net/projects/models/schemadocs/tree/master/doc/openconfig_bgp)
- [GitHub spec-kit](https://github.com/github/spec-kit) — Spec-Driven Development workflow
- Live lab validation: 2026-06-05 on RR1 (192.168.220.11), PE2 (192.168.220.7), East-Spine02 syslog