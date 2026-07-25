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
- [ ] T088 Smoke: mock SNMP or lab switch → metrics labeled `device_name`

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

**Phase 9 checkpoint**: policy engine (T0 default, budgets, metrics) + thin T2
agent profile live. Nuclear posture: empty `allow_t2` until operator opens names.
Optional follow-ups: first real `allow_t2` row after hygiene, T088 Phase 8 smoke.

### Independent test

default_tier T0 + empty allow_t2 → synthetic warning does not multi-tool investigate;
add allow_t2 rule → that alertname can T2; budget trip → clamp; Prom/API stay up.

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
- Phase H does **not** block Phases 3–7; can interleave after Phase 1  

## Parallel opportunities

- T011, T012 after T010  
- T022 parallel with T020  
- T032 parallel with T030  
- T050–T052 parallel with deploy work once contracts stable  
- H001 ∥ H002 ∥ H007 once mobile-layout.js is baseline (shipped)  

