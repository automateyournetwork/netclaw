# Tasks: Observability Series (Parts 13-18)

**Input**: Design documents from `/specs/029-observability-series/`
**Prerequisites**: spec.md (required)

## Format: `[ID] [P?] [Week] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Week]**: Which week/blog part this task belongs to

---

## Phase 1: Week 1 — Observability Stack Deployment (Part 13) ✅ COMPLETE

- [X] T001 [W1] Create docker-compose.observability.yml with OTEL Collector, VictoriaMetrics, Loki, Grafana on clab-mgmt network
- [X] T002 [W1] Create OTEL Collector config with SNMP receivers (Cisco + Arista) and syslog receiver
- [X] T003 [W1] Create Loki config
- [X] T004 [P][W1] Create Grafana datasource provisioning (VictoriaMetrics + Loki)
- [X] T005 [P][W1] Create Grafana dashboard: Network Device Health
- [X] T006 [P][W1] Create Grafana dashboard: Interface Status
- [X] T007 [W1] Create observability config context (config_contexts/observability.yml)
- [X] T008 [W1] Create observability schema (config_context_schemas/observability_schema.yaml)
- [X] T009 [P][W1] Create ios/observability.j2 Jinja template (Ansible + golden config)
- [X] T010 [P][W1] Create eos/observability.j2 Jinja template (Ansible + golden config)
- [X] T011 [W1] Add observability include to all 7 platform templates (both Ansible and golden config repos)
- [X] T012 [W1] Sync Nautobot-Workshop-Datasource repo with config contexts and schemas
- [X] T013 [W1] Create deploy-observability skill (SKILL.md with 9 gated steps)
- [X] T014 [W1] Add Nautobot MCP v2 virtualization tools (get_virtual_machines, create_virtual_machine, create_vm_interface, assign_ip_to_vm)
- [X] T015 [W1] Add cluster and virtual_machine to nautobot_client.py resolve_id
- [X] T016 [W1] Create observability/README.md with full setup guide
- [X] T017 [W1] Write blog Part 13

**Checkpoint**: Stack deploys, metrics flow, dashboards render, VMs registered in Nautobot. ✅

---

## Phase 2: Week 2 — NetClaw ↔ Grafana/Prometheus Integration (Part 14)

- [ ] T018 [W2] Create lab-noc-watch skill (SKILL.md) — queries Grafana for interface errors, CPU, memory, BGP state
- [ ] T019 [W2] Create lab-alert-triage skill (SKILL.md) — reads Grafana alerts, correlates with pyATS device state
- [ ] T020 [W2] Configure Grafana alert rules for: interface down, CPU > 85%, interface errors > 0
- [ ] T021 [P][W2] Document example PromQL queries for lab metrics in skill procedures
- [ ] T022 [P][W2] Document example LogQL queries for device syslog in skill procedures
- [ ] T023 [W2] Validate Grafana MCP connectivity (search_dashboards, query_prometheus, query_loki_logs)
- [ ] T024 [W2] Validate Prometheus MCP connectivity (execute_query, get_metrics)
- [ ] T025 [W2] Write blog Part 14

**Checkpoint**: NetClaw answers health queries via PromQL/LogQL. Alert triage works end-to-end.

---

## Phase 3: Week 3 — Failure Detection + pfSense MCP (Part 15)

- [ ] T026 [W3] Create lab-troubleshoot skill (SKILL.md) — combines observability data with device state for diagnosis
- [ ] T027 [W3] Create pfSense MCP server spec (spec within this spec or separate 030-pfSense-mcp?)
- [ ] T028 [W3] Implement pfSense MCP server: read tools (get_rules, get_interfaces, get_states, get_dhcp_leases, get_arp, get_system_info, get_gateways, get_logs)
- [ ] T029 [W3] Implement pfSense XML-RPC client with auth handling
- [ ] T030 [W3] Deploy pfSense (mock service or VM) on clab-mgmt network
- [ ] T031 [P][W3] Create pfsense-firewall-ops skill (SKILL.md) — read operations
- [ ] T032 [W3] Write blog Part 15

**Checkpoint**: Failure detection works. pfSense MCP reads live firewall state.

---

## Phase 4: Week 4 — Firewall Policy Reconciliation (Part 16)

- [ ] T033 [W4] Implement pfSense MCP write tools (add_rule, delete_rule, modify_rule, apply_changes, manage_aliases, block_ip) — all ITSM-gated
- [ ] T034 [W4] Add Nautobot Firewall plugin write tools to nautobot-mcp-v2 (create rules, address objects, service objects, zones)
- [ ] T035 [W4] Implement firewall reconciliation tool (compare Nautobot policy vs pfSense live rules)
- [ ] T036 [W4] Create firewall-reconcile skill (SKILL.md) — SoT vs live drift detection
- [ ] T037 [P][W4] Update pfsense-firewall-ops skill with write operations
- [ ] T038 [W4] Write blog Part 16

**Checkpoint**: Full firewall lifecycle — SoT defines policy, pfSense enforces it, NetClaw detects drift, ITSM gates changes.

---

## Phase 5: Week 5 — Security Monitoring (Part 17)

- [ ] T039 [W5] Create lab-threat-intel skill (SKILL.md) — analyzes Loki security events, enriches with external APIs
- [ ] T040 [W5] Implement AbuseIPDB enrichment (HTTP client, API key from env var)
- [ ] T041 [P][W5] Implement GreyNoise enrichment (HTTP client, API key from env var)
- [ ] T042 [W5] Configure pfSense syslog export to OTEL Collector (filterlog format)
- [ ] T043 [W5] Add pfSense log parsing to OTEL Collector config (filterlog → Loki with structured labels)
- [ ] T044 [W5] Write blog Part 17

**Checkpoint**: Security events detected in Loki, enriched with threat intel, AI generates threat narratives.

---

## Phase 6: Week 6 — Compliance + Observability Correlation (Part 18)

- [ ] T045 [W6] Create compliance-watch skill (SKILL.md) — ties golden config compliance to observability data
- [ ] T046 [W6] Implement unified health scorecard (compliance status + metric health per device)
- [ ] T047 [W6] Create one-prompt deployment skill that deploys entire stack (lab + observability + registration)
- [ ] T048 [P][W6] Update deploy-observability skill to chain with demo-lab-setup
- [ ] T049 [W6] Final validation: clone → deploy → monitor in < 15 minutes
- [ ] T050 [W6] Write blog Part 18 (series finale)

**Checkpoint**: Complete stack operational. One prompt deploys everything. Series complete.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Week 1)**: No dependencies — COMPLETE ✅
- **Phase 2 (Week 2)**: Depends on Phase 1 (stack must be running)
- **Phase 3 (Week 3)**: Depends on Phase 2 (skills pattern established); pfSense MCP is independent
- **Phase 4 (Week 4)**: Depends on Phase 3 (pfSense MCP read tools must exist)
- **Phase 5 (Week 5)**: Depends on Phase 3 (pfSense deployed) and Phase 4 (write tools for blocking)
- **Phase 6 (Week 6)**: Depends on all previous phases

### Cross-Cutting Concerns

- GAIT audit logging: every new skill and MCP tool
- ITSM gating: all write operations (pfSense rules, Nautobot updates)
- TOON serialization: tabular responses from new tools
- Blog documentation: one post per week

---

## New MCP Servers (to build)

| # | Server | Transport | Tools | Week |
|---|--------|-----------|-------|------|
| 1 | pfSense MCP | stdio (Python) | ~14 (8 read + 6 write) | 3-4 |

## New Skills (to build)

| # | Skill | Purpose | Week |
|---|-------|---------|------|
| 1 | deploy-observability | Deploy OTEL/VM/Loki/Grafana stack | 1 ✅ |
| 2 | lab-noc-watch | Query Grafana for fleet health | 2 |
| 3 | lab-alert-triage | Investigate firing alerts | 2 |
| 4 | lab-troubleshoot | Failure diagnosis with metric + log + CLI correlation | 3 |
| 5 | pfsense-firewall-ops | Read/write pfSense rules | 3-4 |
| 6 | firewall-reconcile | Nautobot vs pfSense drift detection | 4 |
| 7 | lab-threat-intel | Security event analysis + enrichment | 5 |
| 8 | compliance-watch | Golden config + observability correlation | 6 |

## Existing Tools Extended

| Tool | Addition | Week |
|------|----------|------|
| Nautobot MCP v2 | Virtualization tools (4 new) | 1 ✅ |
| Nautobot MCP v2 | Firewall plugin write tools | 4 |
