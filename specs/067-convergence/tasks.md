# Tasks: NetClaw Home (067-convergence)

**Input**: Design documents from `/specs/067-convergence/`  
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/  
**Tests**: Manual HUD smoke + compose smoke scripts; unit tests where noted  
**Organization**: Phases align to upstream PRs / user stories

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable  
- **[Story]**: US1–US6 from spec.md  
- **[PR#]**: Target pull request

---

## Phase 0: Spec Kit (PR0) — COMPLETE when checklist green

**Purpose**: Track work in-repo via specify

- [x] T001 Create `specs/067-convergence/` with spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md, contracts/, checklists/
- [x] T002 [P] Author FR/user stories including risk preserve + guardian-claw ensure (any operator)
- [x] T003 [P] Author contracts for convergence-api, adapters, install wizard
- [x] T004 Constitution Check recorded in plan.md
- [ ] T005 Checklist requirements.md pass (self-review before PR1 code)

---

## Phase 1: Foundational HUD shell (PR1) — US1

**Purpose**: COMMAND | HOME tabs; Home mock; no backend move

- [x] T010 Add top-level tab strip to `ui/netclaw-visual/index.html` (COMMAND | HOME)
- [x] T011 [P] Add `ui/netclaw-visual/src/styles/home.css` reusing CSS variables from `styles.css`
- [x] T012 Implement `ui/netclaw-visual/src/app-shell/tab-router.js` (show/hide command vs home roots)
- [x] T013 Implement `ui/netclaw-visual/src/views/home/HomeView.js` with sub-nav: Overview, Wi‑Fi, Devices, Diary, Triage (Overview mock metrics only)
- [x] T014 Wire tab router from `main.js` without breaking Three.js boot, filters, chat, KnowledgePanel
- [x] T015 Pause/resume or hide WebGL canvas when HOME active (perf: no needless GPU work)
- [x] T016 Rebuild `ui/netclaw-visual/dist` and verify `netclaw-hud.service` serves new UI
- [x] T017 Manual smoke: dist serves app-tabs + HomeView strings; netclaw-hud restarted active

**Checkpoint**: Demoable Home tab on :3001 ✅

---

## Phase 2: convergence-api + live data (PR2) — US2

- [x] T020 Create `ui/convergence-api/` (or `services/convergence-api/`) by lifting `network-guardian-web` Express API routes
- [x] T021 Prefer API-first; document deprecation path for EJS pages
- [x] T022 [P] Add `HOME_API_URL`, `NETWORK_GUARDIAN_*` aliases to `.env.example` with comments
- [x] T023 HUD `server.js`: proxy `/api/home/*` → convergence-api with auth forwarding
- [x] T024 Home Overview/Wi‑Fi/Devices/Diary fetch live pilot endpoints
- [x] T025 Degraded UI when convergence-api unreachable
- [x] T026 Dual-run doc: point at existing K3s Guardian during transition

---

## Phase 3: Docker minimal (PR3) — US3

- [x] T030 `deploy/convergence/docker-compose.yml` (postgres, prom, am, blackbox, convergence-api; unifi profile)
- [x] T031 Alertmanager receiver → host alert-receiver URL configurable (`render-config.sh` + `ALERT_RECEIVER_URL`)
- [x] T032 [P] `deploy/convergence/adapters/unifi/` fragment (exporter.py + profile + README)
- [x] T033 Smoke script `deploy/convergence/smoke-docker.sh`
- [x] T034 quickstart.md Docker path

---

## Phase 4: K3s minimal (PR4) — US3

- [x] T040 `deploy/convergence/k8s/` kustomize base for same services
- [x] T041 Overlay notes for existing pilot cluster
- [x] T042 Smoke checklist for kubectl apply

---

## Phase 5: Installer + risk/guardian ensure (PR5) — US4, US5

- [x] T050 Catalog ids: `convergence-core`, `convergence-metrics`, `convergence-unifi`, `convergence-pfsense`, `visual-hud`, SoT stubs
- [x] T051 Profile `convergence` in `catalog.sh`
- [x] T052 `component_install_*` in `install-steps.sh`
- [x] T053 setup.sh / home-noc-setup: adapter prompts only for selected components
- [x] T054 **Risk detect + ensure guardian-claw** via `in2n-profiles` / member generators (idempotent)
- [x] T055 Check in `scripts/systemd/netclaw-hud.service` template
- [x] T056 config/convergence.example.yaml
- [x] T057 Framework cleanup: remove pilot-only hardcodes from skills where possible; document external-stack deprecation path
- [x] T058 Print setup summary `risk=` `investigator=` `convergence-api=` `deploy=`

---

## Phase 6: Triage loop in HOME (PR6) — US6

- [x] T060 Triage sub-view: escalated list, notes, feedback buttons
- [x] T061 Need More → reinvestigate API
- [x] T062 RAG document id display when present
- [x] T063 Skill wording: multi-vendor / adapter language in alert-triage + wifi-diagnosis

---

## Phase 7+: Adapters (PR7+)

- [x] T070 Nautobot SoT adapter + optional install component
- [x] T071 Second wireless vendor (generic-snmp) stub in contracts + config
- [x] T072 docker-compose.full.yml (Loki, VM, Grafana, speedtest)
- [x] T073 K3s equivalents of T070/T071/T072 (`deploy/convergence/k8s/components/`, `overlays/greenfield-full/`)

**Suggested next**: Phase 8 greenfield device telemetry + agent observability
(optional PR feature) — **not** a pilot migration. Spec:
[`device-telemetry-greenfield.md`](./device-telemetry-greenfield.md).

---

## Phase 8: Greenfield device SNMP + agent observability (optional PR)

**Purpose**: Ship campus switch SNMP, device syslog, NetClaw agent metrics/logs,
and Grafana dashboards as **optional greenfield** install components so a new
site does not depend on `k3s-observability-stack`.

**PR framing**: multi-PR optional feature (`convergence-device-snmp`,
`convergence-agent-metrics`, …). Default install remains minimal WAN + UniFi.

### Spec & contracts

- [x] T080 Author `device-telemetry-greenfield.md` (goals, US, architecture, config)
- [x] T081 Extend `contracts/adapters.md` with `device_telemetry` + `agent_observability`
- [x] T082 Catalog IDs + profile bits in `scripts/lib/catalog.sh` / `.env.example` docs
- [x] T083 Setup wizard prompts only when components selected (SNMP targets, community)

### Device SNMP (switches / wired)

- [x] T084 Docker: snmp_exporter profile `device-snmp`
      with example switch targets from `convergence.yaml`
- [x] T085 Prometheus scrape + alert rules (device.rules.yml) (interface down, exporter down)
- [x] T086 K3s component `deploy/convergence/k8s/components/device-snmp/` `deploy/convergence/k8s/components/device-snmp/`
- [x] T087 HOME Devices / optional Overview KPI when metrics present
- [x] T088 Smoke: mock SNMP or lab switch → metrics labeled `device_name`
      (`deploy/convergence/smoke-device-snmp.sh`; live: HomeSwitch01/02/04)

### Device syslog

- [x] T089 Syslog/UDP receiver → Loki (promtail profile full|device-syslog) (depends on full Loki or slim log service)
- [x] T090 hostname/app labels via promtail syslog relabel (tune per site); docs for switch syslog destination
- [x] T091 K3s parity for syslog receiver (promtail component)

### NetClaw agent observability

- [x] T092 Package openclaw-metrics install-step + Prom scrape job netclaw-openclaw as `convergence-agent-metrics` (systemd unit
      under `scripts/systemd/` or `services/`) + Prometheus scrape from stack
- [x] T093 Agent log forward template rsyslog-netclaw-convergence.conf → Promtail :1514 (rsyslog/journal) → Convergence Loki; template from
      `scripts/rsyslog-netclaw-forward.conf` rewritten for greenfield Loki URL
- [x] T094 Provision Grafana dashboards path (netclaw-quota JSON under full profile): network (switches) + NetClaw quota JSON
- [x] T095 Quickstart section: greenfield device-snmp path: greenfield “switches + agent metrics” path
      (Docker and K3s); no pilot repo required

**Independent test**: empty machine → install profile with device-snmp +
agent-metrics → Prom has switch series and `netclaw_model_*` without applying
anything to namespace `observability`.

**Suggested next (product)**: Phase 9 investigation policy — or finish T088 smoke.

---

## Phase 9: Investigation policy & token economics (optional PR)

**Purpose**: Productize **when** the Convergence alert path spends LLM tokens so
Agentic NOC stays operable and affordable. Default cheap/safe (T0); operators open
T1/T2 as alert hygiene improves without code deploys.

**PR framing**: `convergence-investigation-policy` (alert-receiver + seed config +
setup/quickstart). Does **not** block Phase 8 telemetry ship.

**Detail**: [`investigation-policy.md`](./investigation-policy.md)

### Spec & contracts

- [x] T096 Author `investigation-policy.md` (tiers, policy file, thin T2 profile, budgets)
- [x] T097 Extend `spec.md` US8 + FR-013–FR-020 + SC-007–SC-009
- [x] T098 Contract: alert-receiver policy path, resolution order, metrics names
      (`contracts/investigation-policy.md`)

### Policy engine (alert-receiver)

- [x] T099 Load `~/.openclaw/investigation-policy.yaml` (seed from
      `deploy/convergence/config/investigation-policy.example.yaml`); cache TTL (~30s)
- [x] T100 Resolve tier T0/T1/T2 per alert (force_t0, allow_t2, allow_t1, default_tier,
      Prom `investigate=false`)
- [x] T101 Fail-safe: missing/invalid policy → T0 + clear log warning
- [x] T102 Budgets: max concurrent T2 + max T2 per hour (or equivalent); clamp tier on trip
- [x] T103 Metrics: `netclaw_investigations_by_tier` (+ budget trip counter); log
      `tier=… rule=…` per decision
- [x] T104 T0 path: no multi-tool OpenClaw hook (diary/Discord only as configured)
- [x] T105 T1 path: one-shot summarize (0–1 tools) — diary + Discord notify; no multi-tool hook
- [x] T106 T2 path: existing hook only when allowlisted; wire thin tool profile or agent id
      (prometheus-centric; escalate domain claws — no full interactive zoo)
      `deploy/convergence/config/alert-agent.example.json` +
      `scripts/netclaw-alert-agent-profile.sh apply` → agents.list id=`alert`
      tools.allow (prom/rag/memory/pfsense/unifi/…) + hooks.mappings path=alert
      `agentId=alert`

### Installer / operator UX

- [x] T107 Seed example policy (`deploy/convergence/config/investigation-policy.example.yaml` +
      `scripts/netclaw-investigation-policy.sh seed-observe-only`)
- [x] T108 CLI: `scripts/netclaw-investigation-policy.sh show|seed-observe-only` + `GET /policy/status`
- [x] T109 Quickstart: nuclear start (T0 empty allow_t2) → open one T2 alertname
- [x] T110 `.env.example` notes (`INVESTIGATION_POLICY_PATH`, cache TTL)

**Phase 8 checkpoint**: T080–T095 + T088 smoke green on lab switches.

**Phase 9 checkpoint**: policy engine (T0 default, budgets, metrics) + thin T2
agent profile live. Nuclear posture: empty `allow_t2` until operator opens names.
Optional follow-ups: first real `allow_t2` row (e.g. `SwitchLinkLost` / `WanHardDown`)
after hygiene; dual-stack Docker vs k3s-obs choice.

### Independent test

default_tier T0 + empty allow_t2 → synthetic warning does not multi-tool investigate;
add allow_t2 rule → that alertname can T2; budget trip → clamp; Prom/API stay up.

---

## Phase 10: Telemetry setup productization (optional PR)

**Purpose**: Productize **how** operators go from empty site → inventory
(manual or SoT) → vendor SNMP templates → apply → named-interface metrics →
curated Grafana → safe alerts → device config checklists. Phase 8 plumbing stays
complete; do not re-open T080–T095.

**PR framing**: multi-PR optional feature after Spec Kit (PR0). Default install
remains minimal WAN + UniFi until device-snmp / telemetry setup is selected.

**Detail**: [`telemetry-setup.md`](./telemetry-setup.md) ·
[`contracts/telemetry-setup.md`](./contracts/telemetry-setup.md)

### Spec & contracts (PR0 — Spec Kit)

- [x] T120 Author `telemetry-setup.md` (inventory, templates, apply, metrics,
      dashboards, alerts, checklist, acceptance)
- [x] T121 Extend `spec.md` US9 + FR-021–FR-029 + SC-010–SC-013
- [x] T122 Contract: inventory schema, render/apply, metric labels, managed
      sections (`contracts/telemetry-setup.md`)
- [x] T123 Update `device-telemetry-greenfield.md` (Phase 8 plumbing vs Phase 10
      setup productization)
- [x] T124 Quickstart + `plan.md` Phase 10 pointers

### Inventory & templates (PR1)

- [x] T125 `convergence.yaml` inventory schema + example (`vendor` / `template`
      on targets; secrets stay in env)
- [x] T126 snmp module templates: `cisco`, `pfsense`, `generic` (per-metric
      lookups for `ifDescr`/`ifName`)
- [x] T127 `scripts/render-convergence-telemetry.py` (scrape + modules +
      checklist; extends/supersedes scrape-only renderer as needed)
- [x] T128 `scripts/convergence-telemetry-apply.sh` (managed Prometheus sections,
      compose profiles, reload)
- [x] T135 Recording rules `interface_*` kept in sync with templates
      (`interface_name` from ifDescr else ifName)
- [x] T136 Smoke: apply lab inventory → named interfaces in Prom
      (`smoke-device-snmp.sh` named-interface checks; Grafana :3300 already
      provisioned — full board curation is T132–T133)

### Wizard & SoT (PR2)

- [x] T129 `scripts/convergence-telemetry-setup.sh` wizard
      (`manual` | `nautobot` | `netbox` | `yaml`) +
      `scripts/convergence-telemetry-setup.py` /
      `scripts/lib/convergence_telemetry_inventory.py`
- [x] T130 Wire catalog install-step `convergence-device-snmp` → setup/apply
      (prompt or `CONVERGENCE_TELEMETRY_SETUP=yes`); `setup.sh` Convergence
      section uses wizard
- [x] T131 Device config markdown generator (Cisco + pfSense SNMP/syslog) —
      checklist via render + `device-config-snippets.md` MoP
- [x] T137 Smoke: Nautobot select dry-run → yaml
      (`deploy/convergence/smoke-telemetry-setup.sh`; also MODE=yaml|manual)

### Dashboards & alerts (PR3)

- [x] T132 First curated dashboard pass — ported pilot boards
      (`network-guardian` (convergence:*), `network-interfaces`,
      `device-snmp-switches`, `wan-speedtest`, `netclaw-tokens`).
      **Superseded by T139** (consolidated into 3 boards; these now sit unloaded
      in `grafana/provisioning/dashboards/legacy/`)
- [x] T133 Retire/tag empty boards; Grafana README with datasource UIDs and
      **:3300**. **Superseded by T139** — strategy changed from `[optional]`
      tagging to wholesale consolidation + `legacy/` parking
- [x] T134 Alert pack expansion (safe cardinality) + interface names in
      annotations; `investigate` labels on home + device rules; `WanHardDown`,
      `SwitchInterfaceErrorsHigh`, `EdgeMgmtUnreachable`
- [x] T138 Independent test steps in quickstart (SC-010–SC-013)

### Holistic board suite + log ingest (PR4) — US10

**Purpose**: Replace scattered ported boards with three narrative boards, and make
every provisioned panel traceable to an installable collector.
**Detail**: [`deploy/convergence/grafana/README.md`](../../deploy/convergence/grafana/README.md)
· spec US10 / FR-030–FR-035 / SC-014–SC-016.

- [x] T139 Consolidate to three provisioned boards — `convergence-network`,
      `convergence-security`, `convergence-netclaw` under
      `grafana/provisioning/dashboards/json/`; park ported pilot boards in
      `legacy/` with README; document data dependencies per board
      (commits `4bed668`, `45c22f1`)
- [x] T140 Wire supporting scrapes/log sources: Prom job
      `netclaw-alert-receiver` (investigation tiers/suppressions/budget trips);
      promtail `/tmp/openclaw/*.log` + systemd journal (mesh / members / gateway)
- [x] T141 **Vendor-default syslog ingest** (FR-035, SC-016) — chose option (a):
      `syslog-gateway` (syslog-ng 4.8.1, multi-arch) accepts RFC3164/BSD on
      **:1514 udp+tcp** and re-emits RFC5424 octet-framed to promtail **:1601**.
      Devices need no reconfiguration and the operator-facing port is unchanged,
      so generated checklists stay valid.
      · `deploy/convergence/syslog-gateway/syslog-ng.conf` + compose service
      (profiles `full`|`device-syslog`)
      · promtail syslog target → tcp :1601, `+level` label, no `peer_ip`
        (the TCP peer is now the gateway, not the device)
      · **Timestamps**: gateway stamps receive time — RFC3164 has no timezone, and
        trusting it put live pfSense lines ~6h in the past (outside every "last
        15m" panel) while ingest metrics looked healthy
      · Observability: Prom job `promtail` + alerts `SyslogIngestParseFailing`,
        `SyslogIngestNoEntries`, `LogShipDown` — the original bug was a *silent*
        drop, so parse failures are now loud
      · K3s parity: syslog-ng sidecar in `components/device-syslog` (hostPort
        1514 udp+tcp, promtail on pod-local 1601)
      · Verified live: 0 parse errors, ~1.1k lines/2m from pfSense with
        `device_name`/`app`/`level` labels (`filterlog`, `unbound`, `kea-dhcp4`,
        `nginx`), stamped at real time
      · Operator follow-up (device side, not code): switches are not sending
        syslog yet; add `logging host <host> transport udp port 1514` +
        `logging origin-id hostname` per the generated checklist
- [ ] T142 Log-panel selectors: replace message-content regex on the NetClaw
      board mesh/N2N panels with `job` / `unit` selectors (FR-034). Note: the
      journal relabel chain is correct — `unit=openclaw-gateway.service` proves
      user units resolve; mesh/member panels are empty because those units are
      idle beyond `max_age`, not mislabelled. Stale pre-restart
      `job=netclaw-journal` streams (no `unit` label) are an artifact, not a bug.
- [ ] T143 Security depth collector (FR-031/FR-033) — pfSense block/DNS/filterlog
      signals currently have **no** installable exporter, so Security is posture +
      alerts + logs only. Either add the collector or remove/annotate the panels
      that assume it. **Partially relieved by T141**: `filterlog` (block/pass) and
      `unbound` (DNS) now land in Loki with `app` labels, so Security's log-based
      block/DNS panels have real data — what is still missing is *metric*-shaped
      block/DNS series for alerting and long-term trend.
- [x] T144 Spec realignment (drift close-out) — US10 + FR-030–FR-035 +
      SC-014–SC-016; FR-027 / SC-010 / SC-012 retargeted off retired board names;
      `plan.md` PR4 row; `telemetry-setup.md` + `contracts/telemetry-setup.md`
      board + log-ingest contracts; quickstart SC-012/014/016 steps;
      `checklists/requirements.md` sign-off + drift guard

**Phase 10 checkpoint**: Spec Kit green (T120–T124); PR1 re-applyable lab
without hand-editing Prometheus; PR2 SoT wizard; PR3 curated boards + safe alerts;
PR4 three-board suite (T139–T140 done; T141–T143 open).

### Independent test

empty targets → wizard ≥2 Cisco switches → apply → `device_snmp` up + non-empty
interface name labels within 5m; Nautobot mode writes selection to yaml; Grafana
**Network** board campus switching shows named legends on :3300; checklist has
syslog host:port + `SNMP_COMMUNITY` env name only; folder Convergence provisions
exactly three boards with `legacy/` unloaded.

---

## Phase H: HUD polish backlog (deferred — not blocking PR3+)

**Purpose**: Capture Visual HUD UX / mobile follow-ups so they survive context switches.  
**Detail doc**: [`hud-polish-backlog.md`](./hud-polish-backlog.md) (acceptance criteria, files, resume steps).  
**Default priority**: After Phase 3+ product path unless operator asks for HUD UX next.

### Already shipped (HUD shell hardening, 2026-07-24+)

- [x] H000a Home Overview KPI headers centered (no global `.label` transform leak)
- [x] H000b Left/right/footer panel collapse + edge reopen chips; z-index vs taller topbar
- [x] H000c NetClaw Terminal drag / resize / collapse + desktop geometry persistence
- [x] H000d Mobile layout v1 (`mobile-layout.js`, bottom sheets, FOCUS/DPR, visualViewport, Home 2-col)
- [x] H001 Landscape mode chrome (`#app.landscape-layout`, compact topbar, short terminal sheet)
- [x] H002 `prefers-reduced-motion` (scan-beam off, GSAP timeScale, auto FOCUS)
- [x] H003 Touch long-press → node detail (cancel on orbit drag; optional haptic; opens DETAIL)
- [x] H004 PWA shell (manifest, icons, service worker shell+graph cache)
- [x] H005 Offline / stale graph boot banner + localStorage last-good graph
- [x] H006 Mobile / landscape smoke checklist in HUD README
- [x] H007 Knowledge panel mobile bottom-sheet + collapsed pill chip
- [x] H008 Dynamic `--topbar-height` via ResizeObserver
- [x] H009 Persist quality mode + user pin in localStorage
- [x] H010 Mobile terminal snap points (collapsed / peek / expanded)

### Worth doing next

- Phase H complete for tracked items — optional polish only.
- Product path: **Phase 3 Docker** (`T030+`) when leaving HUD work.

---

## Dependencies

- Phase 1 blocks on Phase 0  
- Phase 2 blocks Phase 3–4 for real data but Phase 1 can demo alone  
- Phase 5 can start after Phase 0; ideally after Phase 2–3 for real components  
- Phase 6 needs Phase 2  
- Phase 8 plumbing complete before Phase 10 productization (collectors exist)  
- Phase 9 independent of Phase 10 (policy consumes better alerts when ready)  
- Phase 10 PR1 (T125–T128) blocks PR2 wizard apply chain; PR3 dashboards can
  start after metric contract (T126/T135) is stable  
- Phase H does **not** block Phases 3–7; can interleave after Phase 1  

## Parallel opportunities

- T011, T012 after T010  
- T022 parallel with T020  
- T032 parallel with T030  
- T050–T052 parallel with deploy work once contracts stable  
- H001 ∥ H002 ∥ H007 once mobile-layout.js is baseline (shipped)  
- T126 ∥ T125 after T124; T132 can draft against recording-rule contract while
  T128 lands  

