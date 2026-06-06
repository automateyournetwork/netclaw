# Implementation Plan: BGP Route Observability

**Branch**: `031-bgp-route-observability` | **Date**: 2026-06-05 | **Spec**: [spec.md](./spec.md)

## Summary

Replace Protocol-MCP-centric BGP monitoring with a **production three-plane architecture**: BMP events, gNMI/SNMP state, and syslog narrative — unified under `netclaw_*` metrics for NOC agents, Grafana alerts, and skills. Delivered in six spec-driven phases; lab validates pipeline with SNMP/gNMI adapters where BMP is unavailable.

## Technical Context

| Item | Choice |
|------|--------|
| Metrics TSDB | VictoriaMetrics (Mimir-compatible path later) |
| Logs | Loki |
| Visualization / alerts | Grafana 11 (provisioned) |
| SNMP/state ingest | OTEL Collector Contrib 0.104+ |
| gNMI ingest | OTEL `gnmi` receiver + existing `gnmi-mcp` for drill-down |
| BMP ingest | gobmp → Redpanda → `bgp-metrics-exporter` Python service |
| Event bus | Redpanda (Kafka API) |
| Normalization | `observability/exporters/bgp-normalizer.py` |
| SoT config | Nautobot Datasource `observability.yml` + golden config Jinja |
| Agent interface | Grafana MCP, Prometheus MCP, pyATS MCP, gNMI MCP |
| Spec workflow | [spec-kit](https://github.com/github/spec-kit) — `/speckit.specify` → `plan` → `tasks` → `implement` per phase |

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         TELEMETRY PLANES                                 │
├──────────────────┬──────────────────────┬───────────────────────────────┤
│ Plane 1: BMP     │ Plane 2: State       │ Plane 3: Narrative            │
│ (prefix events)  │ (peer/prefix counts) │ (why it happened)             │
├──────────────────┼──────────────────────┼───────────────────────────────┤
│ RR/PE → gobmp    │ gNMI Subscribe       │ Syslog UDP :1514              │
│ → Redpanda       │ (Arista, prod IOS)   │ → Loki (device_name label)    │
│ → normalizer     │ SNMP BGP4/CISCO-BGP4 │ SNMP traps (Phase 2+)         │
│                  │ (IOL lab)            │                               │
└────────┬─────────┴──────────┬───────────┴───────────────┬───────────────┘
         │                    │                           │
         └────────────────────┼───────────────────────────┘
                              ▼
                    netclaw_* metrics (VM)
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
    Grafana dashboards   Grafana alerts    NOC agent skills
         │                    │                    │
         └────────────────────┴────────────────────┘
                              ▼
              pyATS / gNMI on-demand drill-down
```

## Platform Adapter Matrix

| Platform | BMP | gNMI stream | SNMP BGP | Syslog |
|----------|-----|-------------|----------|--------|
| Cisco IOL (lab) | — | — | **primary** | **primary** |
| Arista cEOS (lab) | — | **primary** | backup | **primary** |
| Cisco IOS-XE/XR (prod) | **primary** | **primary** | backup | **primary** |
| Arista EOS (prod) | optional | **primary** | backup | **primary** |

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First | PASS | Monitoring read-only; BMP/gNMI config via ITSM in prod |
| V. MCP-Native | PASS | Agents use Grafana/Prometheus/pyATS/gNMI MCP |
| VI. Multi-Vendor | PASS | Per-platform adapter priority |
| X. Observability | PASS | Core feature |
| XVI. Spec-Driven | PASS | This spec + phased tasks |
| XII. Documentation-as-Code | PASS | Blog Part 15 + architecture doc |

**Gate Result**: PASS

## Project Structure

```text
specs/031-bgp-route-observability/
├── spec.md
├── plan.md                    # this file
├── research.md
├── data-model.md
├── tasks.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/
    ├── metrics-schema.md
    └── alert-rules.md

docs/architecture/
└── bgp-route-observability.md

observability/
├── docker-compose.observability.yml      # extend: redpanda, gobmp, exporter
├── docker-compose.bmp.yml                # optional overlay
├── bmp/                                  # gobmp config
├── gnmi/
│   └── subscriptions.yaml                # OpenConfig paths
├── exporters/
│   └── bgp-normalizer.py                 # Kafka + SNMP adapter → VM write
├── otel-collector/
│   └── generate-config.py                # + BGP MIBs, fixed IP SLA OIDs
└── grafana/
    ├── dashboards/bgp-route-stability.json  # netclaw_* only
    └── provisioning/alerting/bgp-route-stability.yaml

workspace/skills/
├── bgp-route-stability-watch/SKILL.md    # rewrite
└── lab-alert-triage/SKILL.md             # netclaw_* alert mapping
```

## Phase Overview

| Phase | Goal | Spec-kit checkpoint |
|-------|------|-------------------|
| **1** | `netclaw_bgp_*` via SNMP + gNMI adapter skeleton | RR1 peer metrics in VM |
| **2** | IP SLA + Loki labels + dashboard LogQL | Jitter + syslog panels populated |
| **3** | Redpanda + gobmp + BMP consumer | Pipeline healthy; metrics on BMP connect |
| **4** | OTEL gNMI receiver for Arista lab | Streaming peer state in VM |
| **5** | Alerts + skill rewrite + baseline doc | Agent RCA without Protocol MCP |
| **6** | Golden config BMP/gNMI templates | Rendered config for prod RR/PE |

## Spec-Kit Workflow per Phase

```bash
# From repo root (spec-kit already initialized in .specify/)
cd /home/ubuntu/netclaw

# Phase N implementation
/speckit.implement   # executes tasks.md for current phase checkpoint

# Or manually:
# 1. Read specs/031-bgp-route-observability/tasks.md Phase N
# 2. Implement tasks
# 3. Run checkpoint validation commands in quickstart.md
# 4. Mark tasks complete
```

## Risk Register

| Risk | Mitigation |
|------|------------|
| IOL lacks BMP | SNMP peer/prefix metrics + syslog; BMP collector idle OK |
| IP SLA SNMP partial on IOL | pyATS fallback in skill; fix OIDs for jitter column |
| gNMI TLS in lab | `tls_skip_verify` in gnmi config (lab only) |
| Per-prefix table SNMP load | Poll prefix **counts** only; BMP for prefix events in prod |
| Alert noise before baseline | Phase 5 starts collect-only; enable paging after baseline window |

## Dependencies

- Phase 1 before 5 (metrics exist before alerts)
- Phase 2 can parallel Phase 1 after OTEL generator split
- Phase 3 independent of 1–2 (pipeline ready before prod BMP peers)
- Phase 4 requires Arista gNMI reachable
- Phase 6 after 1–3 (config templates reference collector endpoints)