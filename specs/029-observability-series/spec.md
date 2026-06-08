# Feature Specification: Observability Series (Parts 13-18)

**Feature Branch**: `029-observability-series`
**Created**: 2026-05-02
**Status**: In Progress (Week 1 complete)
**Input**: Blog series roadmap — 6-week observability pipeline from telemetry collection through AI-driven operations, built on the Nautobot Workshop ContainerLab topology.

## Overview

Deploy a complete observability pipeline on the reproducible Nautobot Workshop lab (18 ContainerLab devices), integrate it with NetClaw's existing MCP servers (Grafana, Prometheus), and build skills for AI-driven NOC operations, failure detection, threat intelligence, and compliance monitoring — all managed through source-of-truth-driven automation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deploy Observability Stack (Priority: P1, Week 1)

As a network engineer, I want to deploy a monitoring pipeline (OTEL Collector, VictoriaMetrics, Loki, Grafana) alongside my ContainerLab topology so that SNMP metrics and syslog from all 18 lab devices are collected, stored, and visualized without manual device configuration.

**Why this priority**: Foundation for all subsequent stories. No observability capabilities exist without the collection/storage/visualization pipeline running.

**Independent Test**: Deploy the stack, wait 90 seconds, query VictoriaMetrics for `interface_status` metric — must return > 0 series.

**Acceptance Scenarios**:

1. **Given** the ContainerLab topology is running with `clab-mgmt` network,
   **When** the operator says "deploy the observability stack",
   **Then** NetClaw deploys 4 containers (OTEL, VictoriaMetrics, Loki, Grafana) on static IPs (.200-.203) and validates all health endpoints.

2. **Given** devices have SNMP + syslog configured via golden config pipeline,
   **When** the OTEL Collector starts polling,
   **Then** CPU, memory, interface octets/packets/errors/status metrics appear in VictoriaMetrics within 90 seconds.

3. **Given** the stack is deployed,
   **When** the operator asks to register the containers in Nautobot,
   **Then** NetClaw creates 4 VMs in an "Observability" cluster with correct IPs via Nautobot MCP v2 virtualization tools.

4. **Given** Grafana is running with provisioned datasources,
   **When** the operator opens the Network Device Health dashboard,
   **Then** all 18 devices show CPU/memory metrics with threshold coloring.

---

### User Story 2 - AI-Driven NOC Monitoring (Priority: P2, Week 2)

As a NOC operator, I want to ask NetClaw about network health and have it query Grafana/Prometheus metrics, correlate with device state, and synthesize a report — so I don't need to manually check dashboards or run CLI commands.

**Why this priority**: This is the primary value proposition — AI consuming telemetry data and providing actionable insights through natural language.

**Independent Test**: Ask "what's the health of the SP core?" and verify NetClaw queries PromQL for CPU/memory/interface metrics and returns a structured report.

**Acceptance Scenarios**:

1. **Given** the observability stack is running and metrics are flowing,
   **When** the operator asks "are there any interface errors in the last hour?",
   **Then** NetClaw queries `increase(interface_errors_in[1h]) > 0` via Prometheus MCP and reports affected interfaces.

2. **Given** a device has elevated CPU,
   **When** the operator asks "what's wrong with P1?",
   **Then** NetClaw queries Grafana for P1 metrics, cross-references with pyATS device state, and synthesizes a diagnosis.

3. **Given** Grafana alerts are configured,
   **When** an alert fires,
   **Then** the `lab-alert-triage` skill queries the alert details, correlates with metrics and device state, and reports root cause.

---

### User Story 3 - Failure Detection and Diagnosis (Priority: P3, Week 3)

As a network engineer, I want NetClaw to detect failures (link down, BGP session drop, high CPU) from telemetry data and automatically diagnose the root cause by correlating metrics, logs, and device state.

**Why this priority**: Moves from passive monitoring to active detection — the AI notices problems before the human does.

**Architecture note (2026-06-05, complete 2026-06-06)**: Part 15 BGP route stability is implemented via **`specs/031-bgp-route-observability`** (Phases 1–6 complete) — router-native telemetry (BMP + gNMI + SNMP + syslog), normalized `netclaw_*` metrics, Grafana alerts, and Nautobot golden config. Protocol MCP is demo-only for injection scenarios (Scenario D), not the monitoring plane. Validation: `bash scripts/observability/validate-bgp-metrics.sh --phase 1` through `--phase 6`.

**Independent Test**: Shut an interface on a lab device, verify NetClaw detects the state change via metrics and correlates with syslog in Loki.

**Acceptance Scenarios**:

1. **Given** an interface goes down on a lab device,
   **When** the OTEL Collector reports `interface_status == 2`,
   **Then** the `lab-troubleshoot` skill detects the change, queries Loki for related syslog, and reports the event with timeline.

2. **Given** a BGP session drops on RR1,
   **When** `netclaw_bgp_peer_state` changes from established,
   **Then** NetClaw correlates with interface status, `netclaw_path_*` metrics, and syslog to determine if it's a link failure, config change, or peer-side issue (see `031` spec).

---

### User Story 4 - pfSense Firewall Integration (Priority: P4, Week 3-4)

As a security engineer, I want NetClaw to read firewall rules from pfSense, compare them against the intended policy in Nautobot Firewall plugin, and detect drift — so I can enforce policy-as-code for the lab firewall.

**Why this priority**: Extends the SoT reconciliation pattern (already proven for interfaces/IPs) to firewall policy. Demonstrates the full loop: SoT → live state → drift detection → ITSM-gated enforcement.

**Independent Test**: Add a rule to pfSense that doesn't exist in Nautobot, run reconciliation, verify it's flagged as "undocumented."

**Acceptance Scenarios**:

1. **Given** pfSense is running with firewall rules,
   **When** the operator asks "reconcile firewall policy",
   **Then** NetClaw queries Nautobot Firewall plugin for intended rules, queries pfSense MCP for live rules, and reports drift (unenforced + undocumented).

2. **Given** a rule exists in Nautobot but not on pfSense,
   **When** the operator approves enforcement with a CR number,
   **Then** NetClaw adds the rule to pfSense via pfSense MCP (ITSM-gated).

---

### User Story 5 - Security Monitoring and Threat Intelligence (Priority: P5, Week 4-5)

As a security analyst, I want NetClaw to analyze security events from Loki (pfSense filterlog, device syslog), enrich with external threat intelligence (AbuseIPDB, GreyNoise), and generate threat narratives — so I can respond to suspicious activity faster.

**Why this priority**: Combines observability (Loki logs) with external enrichment and AI synthesis for security operations.

**Independent Test**: Inject a simulated blocked connection in pfSense logs, verify NetClaw detects it, enriches the source IP, and generates a threat narrative.

**Acceptance Scenarios**:

1. **Given** pfSense logs show blocked connections from an external IP,
   **When** the `lab-threat-intel` skill runs,
   **Then** it queries Loki for the events, enriches the IP via AbuseIPDB/GreyNoise, and reports confidence level + recommended action.

2. **Given** a confirmed malicious IP is identified,
   **When** the operator approves blocking with a CR number,
   **Then** NetClaw adds a block rule to pfSense via MCP (ITSM-gated).

---

### User Story 6 - Compliance + Observability Correlation (Priority: P6, Week 5-6)

As a compliance engineer, I want NetClaw to correlate golden config compliance status with observability data — so I can see not just "what's non-compliant" but "what's non-compliant AND causing operational issues."

**Why this priority**: Ties together the two major NetClaw capabilities (golden config compliance + observability) into a unified operational view.

**Independent Test**: Create a compliance violation (remove SNMP config from a device), verify NetClaw detects both the compliance failure AND the missing metrics.

**Acceptance Scenarios**:

1. **Given** a device fails golden config compliance for SNMP configuration,
   **When** the `compliance-watch` skill runs,
   **Then** it correlates the compliance failure with missing metrics in VictoriaMetrics and reports "device X is non-compliant AND unmonitored."

2. **Given** all devices are compliant and monitored,
   **When** the operator asks for a compliance + observability report,
   **Then** NetClaw generates a unified health scorecard showing compliance status alongside metric health.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST deploy OTEL Collector, VictoriaMetrics, Loki, and Grafana on the clab-mgmt Docker network with static IPs.
- **FR-002**: SNMP and syslog configuration on devices MUST be managed via golden config pipeline (config context → Jinja template → Ansible/golden config).
- **FR-003**: Observability containers MUST be registered as VMs in Nautobot with IP assignments via Nautobot MCP v2 virtualization tools.
- **FR-004**: NetClaw MUST query metrics via Grafana MCP (75+ tools) and Prometheus MCP (6 tools).
- **FR-005**: NetClaw MUST query logs via Grafana MCP Loki integration (LogQL).
- **FR-006**: pfSense MCP server MUST support read operations (rules, interfaces, states) and ITSM-gated write operations (add/delete rules).
- **FR-007**: Firewall reconciliation MUST compare Nautobot Firewall plugin (SoT) against pfSense live rules.
- **FR-008**: Threat intelligence skill MUST enrich IPs via external APIs (AbuseIPDB, GreyNoise).
- **FR-009**: Compliance-watch skill MUST correlate golden config compliance with observability metrics.
- **FR-010**: All write operations (pfSense rule changes, IP blocking) MUST be ITSM-gated.
- **FR-011**: All operations MUST be logged to GAIT audit trail.

### Key Entities

- **Observability Stack**: 4 Docker containers (OTEL Collector, VictoriaMetrics, Loki, Grafana) on clab-mgmt network.
- **Metric**: Time-series data point collected via SNMP (CPU, memory, interface counters, status).
- **Log Entry**: Syslog message from a device or pfSense filterlog entry, stored in Loki.
- **Firewall Rule**: A policy entry in pfSense or Nautobot Firewall plugin (source, destination, action, protocol, port).
- **Compliance Violation**: A device whose running config doesn't match the golden config intended state.
- **Threat Indicator**: An IP address or pattern identified as suspicious, enriched with external intelligence.

## Success Criteria *(mandatory)*

- **SC-001**: Observability stack deploys in < 2 minutes and collects metrics from all 18 devices within 90 seconds.
- **SC-002**: NetClaw answers health queries using PromQL within 5 seconds.
- **SC-003**: Failure detection identifies link/BGP state changes within 60 seconds of occurrence.
- **SC-004**: pfSense MCP server provides read access to all rule tables and ITSM-gated write access.
- **SC-005**: Firewall reconciliation correctly identifies drift between Nautobot policy and pfSense live state.
- **SC-006**: Threat intelligence enrichment returns results for known malicious IPs within 3 seconds.
- **SC-007**: Compliance-watch correctly correlates compliance failures with missing observability data.
- **SC-008**: All new skills and MCP servers follow NetClaw conventions (GAIT, ITSM, TOON, error handling).
- **SC-009**: Entire series is reproducible — clone repos, deploy lab, run one prompt to get full stack.

## Assumptions

- Nautobot Workshop ContainerLab topology is the target environment (18 devices on 192.168.220.0/24).
- Cisco IOL devices support SNMPv2c with standard MIBs (IF-MIB, CISCO-PROCESS-MIB).
- Arista cEOS devices support SNMPv2c with standard MIBs.
- pfSense will be deployed as either a mock service (for demo reliability) or a real VM.
- Nautobot Firewall plugin is installed and configured in the workshop Nautobot instance.
- External threat intelligence APIs (AbuseIPDB, GreyNoise) are available with free-tier API keys.
- The `clab-mgmt` Docker network has available IPs in the .200-.210 range for observability services.

## Deliverables by Week

| Week | Blog Part | Deliverables |
|------|-----------|-------------|
| 1 | Part 13 | Observability stack (docker-compose, OTEL config, Grafana dashboards), golden config templates, Nautobot VM registration, deploy-observability skill |
| 2 | Part 14 | lab-noc-watch skill, lab-alert-triage skill, Grafana alert rules, NetClaw ↔ Grafana/Prometheus integration examples |
| 3 | Part 15 | lab-troubleshoot skill, failure detection workflows, pfSense MCP server (read tools) |
| 4 | Part 16 | pfSense MCP write tools (ITSM-gated), Nautobot Firewall plugin write tools, firewall reconciliation skill |
| 5 | Part 17 | lab-threat-intel skill, security monitoring, AbuseIPDB/GreyNoise enrichment |
| 6 | Part 18 | compliance-watch skill, unified health scorecard, one-prompt full deployment, series finale |
