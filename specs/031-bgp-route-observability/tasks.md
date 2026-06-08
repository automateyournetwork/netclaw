# Tasks: BGP Route Observability (Production Architecture)

**Input**: [spec.md](./spec.md) | [plan.md](./plan.md) | [research.md](./research.md)
**Workflow**: [GitHub spec-kit](https://github.com/github/spec-kit) — implement phase-by-phase; validate checkpoint before next phase.

## Format: `[ID] [P?] [Phase] Description`

- **[P]**: Can run in parallel
- **[Phase]**: 1–6 per plan.md

---

## Phase 1: Normalized BGP Metrics (SNMP + schema)

**Goal**: `netclaw_bgp_*` peer metrics from routers in VictoriaMetrics.
**Checkpoint**: `netclaw_bgp_peer_prefixes_received{device_name="rr1",neighbor="100.0.254.13"} == 4`

- [x] T001 [P] [1] Add BGP4-MIB + CISCO-BGP4-MIB metric definitions to `observability/otel-collector/generate-config.py` for roles `rr`, `pe`
- [x] T002 [1] Map SNMP columns to `netclaw_bgp_peer_state`, `netclaw_bgp_peer_prefixes_received`, `netclaw_bgp_peer_in_updates_total`, `netclaw_bgp_peer_out_updates_total`, `netclaw_bgp_peer_established_transitions_total`, `netclaw_bgp_peer_uptime_seconds` via OTEL metric rename transform or exporter-side naming
- [x] T003 [1] Regenerate `otel-config.yaml`; restart otel-collector
- [x] T004 [P] [1] Create `observability/exporters/bgp-normalizer.py` skeleton (SNMP label normalization if OTEL cannot emit `netclaw_` prefix directly)
- [x] T005 [1] Update `observability/grafana/dashboards/bgp-route-stability.json` peer/RIB panels to `netclaw_*` queries
- [x] T006 [1] Add `scripts/observability/validate-bgp-metrics.sh` checkpoint script
- [x] T007 [1] Document Phase 1 in `quickstart.md` validation section

**Checkpoint command**:
```bash
bash scripts/observability/validate-bgp-metrics.sh --phase 1
```

---

## Phase 2: Path Quality + Syslog Correlation

**Goal**: Jitter metrics and Loki `device_name` labels; syslog panel populated.
**Checkpoint**: `netclaw_path_jitter_ms{device_name="pe2"}` exists; Loki `{device_name=~".+"}` returns BGP lines

- [x] T010 [1] [2] Fix IP SLA OIDs in `generate-config.py`: jitter `.1.5.2.1.4.{probe}`, loss `.1.5.2.1.26.{probe}`, map to `netclaw_path_*`
- [x] T011 [P] [2] Promote `device_name` to Loki label in OTEL logs pipeline (`attributes` → `resource` + loki exporter label hints)
- [x] T012 [2] Fix Grafana syslog panel LogQL: `{service_name="network-devices"} |~ "(?i)(BGP|LINEPROTO|UPDOWN|ADJCHANGE)"`
- [x] T013 [P] [2] Update `bgp-route-stability.json` path quality panels to `netclaw_path_jitter_ms`, `netclaw_path_rtt_ms`
- [x] T014 [2] Push IP SLA + `logging host` via golden config / Ansible for PE1–PE3 (fix PE1 reachability)
- [x] T015 [2] Extend `scripts/observability/validate-bgp-metrics.sh --phase 2`

---

## Phase 3: BMP Event Plane

**Goal**: Redpanda + gobmp + consumer → `netclaw_bgp_prefix_*` metrics.
**Checkpoint**: `docker compose` BMP services healthy; consumer ready (metrics appear when BMP peer connects)

- [x] T020 [P] [3] Create `observability/docker-compose.bmp.yml` (Redpanda, gobmp, bgp-normalizer)
- [x] T021 [3] Configure gobmp to publish to Redpanda topic `openbmp.parsed`
- [x] T022 [3] Implement BMP message handler in `bgp-normalizer.py` → `netclaw_bgp_prefix_announcements_total`, `netclaw_bgp_prefix_withdrawals_total`
- [x] T023 [P] [3] Add BMP statistics → `netclaw_bgp_rib_routes_total`
- [x] T024 [3] Wire compose overlay into `observability/README.md` and `quickstart.md`
- [x] T025 [3] Add dashboard panels for BMP withdrawal rate (show "no data" gracefully in lab)
- [x] T026 [3] Extend `scripts/observability/validate-bgp-metrics.sh --phase 3`

---

## Phase 4: gNMI Streaming (Arista lab)

**Goal**: OTEL gnmi receiver streams OpenConfig BGP to VM for cEOS devices.
**Checkpoint**: `netclaw_bgp_peer_state` series with `source="gnmi"` for west-spine01

- [x] T030 [P] [4] Create `observability/gnmi/subscriptions.yaml` — OpenConfig BGP neighbor paths
- [x] T031 [4] Add `bgp_gnmi_exporter.py` + `docker-compose.gnmi.yml` (pygnmi → :9103; VM scrape)
- [x] T032 [4] Map gNMI updates to `netclaw_*` (reuse normalizer or OTEL transform)
- [x] T033 [P] [4] Add Arista targets to gnmi config (192.168.220.12–19, port 6030, lab TLS skip)
- [x] T034 [4] Validate against `gnmi-mcp` `gnmi_compare_with_cli` for one spine
- [x] T035 [4] Extend `scripts/observability/validate-bgp-metrics.sh --phase 4`

---

## Phase 5: Alerts, Skills, Baselining

**Goal**: Agents act on thresholds; skills use router-native sources only.
**Checkpoint**: Scenario B/C produces alert + `bgp-route-stability-watch` report without Protocol MCP

- [x] T040 [P] [5] Rewrite `observability/grafana/provisioning/alerting/bgp-route-stability.yaml` per `contracts/alert-rules.md`
- [x] T041 [5] Rewrite `workspace/skills/bgp-route-stability-watch/SKILL.md` — netclaw PromQL + Loki + pyATS/gNMI
- [x] T042 [P] [5] Update `workspace/skills/lab-alert-triage/SKILL.md` alert → runbook mapping
- [x] T043 [5] Create `docs/baselines/bgp-route-stability.md` — baseline collection procedure
- [x] T044 [5] Run failure scenarios B/C; record baseline samples in baselines doc
- [x] T045 [5] Mark Protocol MCP as demo-only in `docs/failure-scenarios.md` Scenario D
- [x] T046 [5] Rewrite `docs/blogs/blog-part15-route-stability-observability.md` (final editorial pass)

**Checkpoint command**:
```bash
bash scripts/observability/validate-bgp-metrics.sh --phase 5
# Live alert fire: Scenario B (PE1 Gi2 shutdown) — see docs/baselines/bgp-route-stability.md
```

---

## Phase 6: Production Golden Config

**Goal**: Nautobot templates enable BMP + gNMI on prod RR/PE; skip on IOL.
**Checkpoint**: Rendered RR template includes BMP server stanza when `observability.bmp.enabled`

- [x] T050 [P] [6] Extend Datasource `config_contexts/observability.yml` with `bmp`, `gnmi` blocks
- [x] T051 [6] Create `ios/bmp.j2` and `ios/gnmi-telemetry.j2` (or extend observability.j2)
- [x] T052 [P] [6] Create `eos/gnmi-telemetry.j2` for Arista
- [x] T053 [6] Platform conditionals: skip BMP on `cisco_iol`, enable on `iosxe` template variant
- [x] T054 [6] Ansible deploy test on RR1 (BMP skip) + west-spine01 (gNMI verify)
- [x] T055 [6] Update Nautobot-Workshop-Datasource sync docs

**Checkpoint command**:
```bash
bash scripts/observability/validate-bgp-metrics.sh --phase 6
python3 scripts/observability/nautobot-push-observability.py
```

---

## Cross-Cutting

- [x] T060 [P] Update `specs/029-observability-series/spec.md` — reference 031 for Part 15 pivot
- [x] T061 [P] Update `docs/blogs/roadmap-observability-series.md` Week 3 section
- [x] T062 [P] Update `observability/README.md` architecture section
- [x] T063 Run `/speckit.analyze` consistency check across 031 artifacts before Phase 5 merge

**T063 analyze (2026-06-06)**: Metrics schema (`contracts/metrics-schema.md`), alert rules (`contracts/alert-rules.md`), dashboard queries (`netclaw_*`), skills, and golden config templates are aligned. Legacy `ip_sla_*` / `bgp_route_*` names removed from active panels. Protocol MCP demoted to Scenario D only in `docs/failure-scenarios.md`. Dashboard `$device` variable fixed (`allValue: ".*"`) for IP SLA panels.

---

## Dependency Graph

```text
Phase 1 ──┬──> Phase 5
Phase 2 ──┤
Phase 3 ──┤ (parallel OK after Phase 1 started)
Phase 4 ──┘
Phase 6 (after 1 + 3 endpoints known)
```

## Parallel Example (Phase 1 + 2)

```bash
# Agent A: T001–T003 (SNMP BGP MIBs)
# Agent B: T010–T011 (IP SLA + Loki labels)
# Merge → T005, T013 dashboard updates
```