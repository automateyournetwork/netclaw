# Feature Specification: BGP Route Observability (Production Architecture)

**Feature Branch**: `031-bgp-route-observability`
**Created**: 2026-06-05
**Status**: Draft
**Supersedes**: Part 15 approach in `029-observability-series` that relied on Protocol MCP metrics as the BGP telemetry plane
**Input**: Production-scalable BGP route stability observability for NOC agents — router-native telemetry (BMP + gNMI + SNMP + syslog), normalized `netclaw_bgp_*` metrics, threshold-based alerting, and spec-driven phased delivery per [GitHub spec-kit](https://github.com/github/spec-kit).

## Overview

NetClaw NOC agents need **actionable, router-perspective BGP data** to investigate route instability, correlate with physical-layer and path-quality signals, and respond to Grafana alerts. The lab validates a **production architecture** (three telemetry planes + normalized metric schema) even when individual lab devices lack BMP or gNMI.

Protocol MCP remains available for **controlled fault injection demos** only; it is **not** the observability source of truth.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Normalized BGP Metrics from Routers (Priority: P1, Phase 1)

As a NOC operator, I want BGP peer state, prefix counts, and session stability metrics collected from route reflectors and PE routers into VictoriaMetrics under a consistent `netclaw_bgp_*` schema — so agents and Grafana query one vocabulary regardless of whether data came from SNMP or gNMI.

**Why this priority**: Without labeled router-native metrics, there is no baseline for thresholds and no actionable alerts.

**Independent Test**: Query VictoriaMetrics for `netclaw_bgp_peer_state{device_name="rr1"}` and `netclaw_bgp_peer_prefixes_received` — values must match `show ip bgp summary` on RR1 within one poll interval.

**Acceptance Scenarios**:

1. **Given** RR1 is reachable via SNMP,
   **When** OTEL polls BGP4-MIB and CISCO-BGP4-MIB,
   **Then** `netclaw_bgp_peer_state` and `netclaw_bgp_peer_prefixes_received` appear with labels `device_name`, `neighbor`, `peer_as`.

2. **Given** Arista cEOS devices have gNMI enabled,
   **When** gNMI subscriptions stream OpenConfig BGP neighbor state,
   **Then** the same `netclaw_bgp_*` metric names are populated for Arista devices.

3. **Given** the Grafana BGP Route Stability dashboard,
   **When** an operator opens peer state and prefix panels,
   **Then** panels query only `netclaw_*` metrics (not Protocol MCP `bgp_route_*`).

---

### User Story 2 - Path Quality and Syslog Correlation (Priority: P2, Phase 2)

As a NOC agent investigating a BGP alert, I want IP SLA jitter/RTT metrics and device syslog (BGP adjacency changes, interface UPDOWN) labeled by `device_name` — so I can correlate withdrawal/update spikes with physical-layer or path-quality causes.

**Why this priority**: BGP symptoms without path and narrative context produce false or incomplete diagnoses.

**Independent Test**: After PE2 jitter probes are running, `netclaw_path_jitter_ms{device_name="pe2"}` is non-zero; Loki query `{device_name="east-spine02"} |~ "BGP"` returns adjacency events.

**Acceptance Scenarios**:

1. **Given** IP SLA udp-jitter probes on PE routers,
   **When** OTEL polls correct RTTMON-MIB OIDs,
   **Then** `netclaw_path_jitter_ms` and `netclaw_path_rtt_ms` series exist (not empty dashboard panels).

2. **Given** devices send syslog to OTEL `:1514`,
   **When** logs are exported to Loki,
   **Then** `device_name` is a queryable label and the Grafana syslog panel shows BGP/LINEPROTO events without broken JSON parsing.

---

### User Story 3 - BMP Event Plane (Priority: P3, Phase 3)

As a platform engineer, I want a BMP collector and event bus (Redpanda/Kafka) in the observability stack — so per-prefix announcements and withdrawals can be counted at production scale when routers export BMP.

**Why this priority**: Per-prefix flap detection at scale requires BMP; SNMP update counters are insufficient for prefix-level RCA.

**Independent Test**: BMP collector container is healthy; when a BMP-capable router is configured, `netclaw_bgp_prefix_withdrawals_total` increments on withdraw events.

**Acceptance Scenarios**:

1. **Given** Redpanda and gobmp run in docker-compose,
   **When** the stack starts,
   **Then** BMP collector accepts TCP sessions and publishes parsed messages to the event bus.

2. **Given** a BMP session from a production IOS-XE route reflector (out of lab),
   **When** a prefix is withdrawn,
   **Then** `rate(netclaw_bgp_prefix_withdrawals_total{prefix="..."}[5m])` increases within one scrape interval.

3. **Given** lab IOL devices without BMP,
   **When** Phase 3 is deployed,
   **Then** SNMP/gNMI adapters continue populating peer-level metrics (graceful degradation).

---

### User Story 4 - Threshold Alerts and Agent Investigation (Priority: P4, Phase 5)

As a NOC operator, I want Grafana alerts on `netclaw_*` metrics after a baselining period — and the `bgp-route-stability-watch` skill to walk agents through PromQL → Loki → pyATS/gNMI drill-down.

**Why this priority**: Data without thresholds and runbooks does not enable autonomous or human-on-the-loop operations.

**Independent Test**: Inject Scenario B (interface flap) or peer instability; an alert fires; agent skill produces a structured report with device, neighbor, and root-cause classification.

**Acceptance Scenarios**:

1. **Given** 7+ days of baseline metrics (or lab scenarios),
   **When** `netclaw_bgp_peer_prefixes_received` drops by ≥20% from 1h average,
   **Then** Grafana fires a WARNING alert with `device_name` and `neighbor` labels.

2. **Given** a fired alert,
   **When** `bgp-route-stability-watch` runs,
   **Then** it queries `netclaw_*` PromQL, Loki for ADJCHANGE/UPDOWN, and pyATS or gNMI for peer/rib detail — **not** Protocol MCP RIB.

3. **Given** Protocol MCP inject/withdraw demo (Scenario D),
   **When** used for blog/lab demo,
   **Then** it is documented as synthetic injection only, separate from production monitoring path.

---

### User Story 5 - Production Golden Config for BMP (Priority: P5, Phase 6)

As a network architect, I want Nautobot golden config templates to enable BMP export and gNMI streaming on production device roles — so the same observability stack works when lab IOL is replaced by production routers.

**Why this priority**: Closes the loop between SoT-driven config and telemetry plane.

**Independent Test**: Rendered IOS-XE template includes `router bmp` (or equivalent) pointing at collector IP; Arista template enables gNMI subscription targets.

**Acceptance Scenarios**:

1. **Given** observability config context in Nautobot Datasource,
   **When** golden config is built for RR/PE roles,
   **Then** BMP server IP and gNMI destination are parameterized from config context.

2. **Given** Ansible deploy to lab,
   **When** device platform lacks BMP (IOL),
   **Then** deploy skips BMP stanza without failure (platform conditional in Jinja).

---

## Functional Requirements

### FR-001: Normalized Metric Schema
All BGP and path-quality metrics exposed to VictoriaMetrics MUST use the `netclaw_` prefix and label set defined in `data-model.md`.

### FR-002: Source Adapters
The system MUST support pluggable adapters: SNMP (BGP4-MIB, CISCO-BGP4-MIB, RTTMON-MIB), gNMI OpenConfig BGP, BMP→Kafka consumer, with documented source priority per platform.

### FR-003: Agent Query Stability
Grafana dashboards, alert rules, and NOC skills MUST NOT depend on Protocol MCP metrics for steady-state monitoring.

### FR-004: Baselining Before Paging
Alert rules MUST document baseline methodology (percentile / absolute thresholds) and default to collect-only mode until baseline window is met.

### FR-005: Lab–Production Parity
Docker-compose and OTEL config MUST run the same services in lab and production; only device adapter availability differs by platform.

### FR-006: Spec-Driven Phases
Each implementation phase MUST be executable via `/speckit.implement` against `tasks.md` with independent checkpoint validation.

## Success Criteria

| ID | Criterion | Measurement |
|----|-----------|-------------|
| SC-001 | Router BGP metrics in VM | `count(netclaw_bgp_peer_state)` ≥ 1 per RR/PE device |
| SC-002 | Prefix count accuracy | SNMP `netclaw_bgp_peer_prefixes_received` matches CLI ±0 |
| SC-003 | Jitter visibility | `netclaw_path_jitter_ms` non-empty for ≥2 PE devices |
| SC-004 | Syslog correlation | Loki returns BGP events filterable by `device_name` |
| SC-005 | BMP pipeline ready | gobmp + Redpanda healthy; consumer writes `netclaw_bgp_prefix_*` when BMP peer connected |
| SC-006 | Agent end-to-end | `bgp-route-stability-watch` completes 4-source report without Protocol MCP |
| SC-007 | Blog/spec alignment | Part 15 blog and `031` spec describe same architecture |

## Assumptions

- VictoriaMetrics and Loki from Part 13 remain the metrics/log stores.
- Grafana MCP and Prometheus MCP remain the agent query interface.
- pyATS MCP and gNMI MCP provide on-demand drill-down (not continuous poll at scale).
- Cisco IOL in lab does not export BMP; Arista cEOS exports gNMI on port 6030.
- Nautobot Workshop Datasource remains SoT for observability config context.

## Out of Scope

- pfSense MCP (remains in `029` Week 3 original scope — may move to separate spec).
- Full ClickHouse/long-term BMP archive (optional Phase 3+ enhancement).
- Automated remediation without ITSM gate in production mode.
- Replacing Protocol MCP for BGP participation/injection demos.

## Dependencies

- `specs/029-observability-series` — OTEL, VM, Loki, Grafana foundation
- `specs/003-gnmi-mcp-server` — gNMI MCP for agent drill-down
- `mcp-servers/pyATS_MCP` — CLI verification on IOL
- Nautobot golden config pipeline — BMP/gNMI device config (Phase 6)

## Review & Acceptance Checklist

- [ ] User stories are independently testable per phase
- [ ] Protocol MCP demoted to demo-only in all artifacts
- [ ] Metric schema documented in `data-model.md` and `contracts/metrics-schema.md`
- [ ] Each phase has checkpoint in `tasks.md`
- [ ] Part 15 blog rewritten to match this spec
- [ ] Roadmap Week 3 updated to reference `031`