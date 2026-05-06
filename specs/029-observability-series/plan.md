# Implementation Plan: Observability Series (Parts 13-18)

**Branch**: `029-observability-series` | **Date**: 2026-05-02 | **Spec**: `specs/029-observability-series/spec.md`

## Summary

Six-week project delivering a complete observability pipeline on the Nautobot Workshop ContainerLab topology, integrated with NetClaw for AI-driven network operations. Covers telemetry collection (OTEL/SNMP/syslog), metric storage (VictoriaMetrics), log aggregation (Loki), visualization (Grafana), firewall management (pfSense MCP), security monitoring (threat intel enrichment), and compliance correlation (golden config + observability).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: FastMCP, httpx, docker compose, OpenTelemetry Collector Contrib
**Storage**: VictoriaMetrics (metrics), Loki (logs), Nautobot (SoT)
**Target Platform**: Ubuntu 22.04/24.04 with Docker, ContainerLab
**Project Type**: MCP server (pfSense) + 8 skills + infrastructure (docker-compose)
**Constraints**: All on clab-mgmt network (192.168.220.0/24); ITSM-gated writes; GAIT audit

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | All monitoring is read-only. pfSense writes are ITSM-gated. |
| II. Read-Before-Write | PASS | pfSense MCP captures baseline before rule changes. |
| III. ITSM-Gated Changes | PASS | pfSense rule changes, Nautobot updates, IP blocking all require CR. |
| IV. Immutable Audit Trail | PASS | All operations logged to GAIT. |
| V. MCP-Native Integration | PASS | pfSense MCP follows standard FastMCP stdio pattern. |
| VI. Multi-Vendor Neutrality | PASS | OTEL polls both Cisco IOL and Arista cEOS. |
| VII. Skill Modularity | PASS | 8 independent skills, each with clear trigger patterns. |
| VIII. Verify After Every Change | PASS | pfSense writes verify rule applied after Set. |
| IX. Security by Default | PASS | Credentials from env vars. No hardcoded secrets. |
| X. Observability | PASS | This IS the observability feature. |
| XI. Artifact Coherence | PASS | README, skills, openclaw.json, .env.example all updated. |
| XII. Documentation-as-Code | PASS | Blog series documents everything. |
| XIII. Credential Safety | PASS | pfSense creds, API keys from env vars. |
| XIV. Human-in-the-Loop | PASS | Write operations gated. Threat blocking requires approval. |
| XV. Backwards Compatibility | PASS | New capabilities only. No changes to existing MCP servers. |
| XVI. Spec-Driven Development | PASS | This spec. |

**Gate Result**: ALL PASS.

## Project Structure

### Documentation

```text
specs/029-observability-series/
├── spec.md              # This feature specification
├── plan.md              # This file
├── tasks.md             # Phased task breakdown
├── checklists/
│   └── requirements.md  # Artifact coherence checklist
└── contracts/
    └── pfsense-mcp-tools.md  # pfSense MCP tool contracts (Week 3)
```

### Source Code

```text
observability/                          # Week 1 ✅
├── docker-compose.observability.yml
├── otel-collector/otel-config.yaml
├── loki/loki-config.yaml
├── grafana/provisioning/
└── grafana/dashboards/

mcp-servers/pfsense-mcp/               # Week 3-4
├── server.py
├── pfsense_client.py
├── requirements.txt
└── README.md

workspace/skills/
├── deploy-observability/SKILL.md       # Week 1 ✅
├── lab-noc-watch/SKILL.md              # Week 2
├── lab-alert-triage/SKILL.md           # Week 2
├── lab-troubleshoot/SKILL.md           # Week 3
├── pfsense-firewall-ops/SKILL.md       # Week 3-4
├── firewall-reconcile/SKILL.md         # Week 4
├── lab-threat-intel/SKILL.md           # Week 5
└── compliance-watch/SKILL.md           # Week 6
```

## Weekly Delivery Cadence

Each week produces:
1. Working code (MCP server, skill, infrastructure)
2. Blog post documenting the work
3. Tasks marked complete in this spec
4. Commit(s) pushed to relevant repos

## Current Status

- **Week 1**: ✅ COMPLETE — Stack deployed, templates synced, VMs registered, skill written
- **Week 2**: NOT STARTED
- **Week 3**: NOT STARTED
- **Week 4**: NOT STARTED
- **Week 5**: NOT STARTED
- **Week 6**: NOT STARTED
