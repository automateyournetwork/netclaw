# Tasks: NetClaw Home (067-home-noc)

**Input**: Design documents from `/specs/067-home-noc/`  
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

- [x] T001 Create `specs/067-home-noc/` with spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md, contracts/, checklists/
- [x] T002 [P] Author FR/user stories including risk preserve + guardian-claw ensure (any operator)
- [x] T003 [P] Author contracts for home-api, adapters, install wizard
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

## Phase 2: home-api + live data (PR2) — US2

- [x] T020 Create `ui/home-api/` (or `services/home-api/`) by lifting `network-guardian-web` Express API routes
- [x] T021 Prefer API-first; document deprecation path for EJS pages
- [x] T022 [P] Add `HOME_API_URL`, `NETWORK_GUARDIAN_*` aliases to `.env.example` with comments
- [x] T023 HUD `server.js`: proxy `/api/home/*` → home-api with auth forwarding
- [x] T024 Home Overview/Wi‑Fi/Devices/Diary fetch live pilot endpoints
- [x] T025 Degraded UI when home-api unreachable
- [x] T026 Dual-run doc: point at existing K3s Guardian during transition

---

## Phase 3: Docker minimal (PR3) — US3

- [ ] T030 `deploy/home/docker-compose.yml` (postgres, prom, am, blackbox, home-api, unifi-exporter)
- [ ] T031 Alertmanager receiver → host alert-receiver URL configurable
- [ ] T032 [P] `deploy/home/adapters/unifi/` fragment
- [ ] T033 Smoke script `deploy/home/smoke-docker.sh`
- [ ] T034 quickstart.md Docker path

---

## Phase 4: K3s minimal (PR4) — US3

- [ ] T040 `deploy/home/k8s/` kustomize base for same services
- [ ] T041 Overlay notes for existing pilot cluster
- [ ] T042 Smoke checklist for kubectl apply

---

## Phase 5: Installer + risk/guardian ensure (PR5) — US4, US5

- [ ] T050 Catalog ids: `home-noc-core`, `home-noc-metrics`, `home-noc-unifi`, `home-noc-pfsense`, `visual-hud`, SoT stubs
- [ ] T051 Profile `home` in `catalog.sh`
- [ ] T052 `component_install_*` in `install-steps.sh`
- [ ] T053 setup.sh / home-noc-setup: adapter prompts only for selected components
- [ ] T054 **Risk detect + ensure guardian-claw** via `in2n-profiles` / member generators (idempotent)
- [ ] T055 Check in `scripts/systemd/netclaw-hud.service` template
- [ ] T056 config/home-noc.example.yaml
- [ ] T057 Framework cleanup: remove pilot-only hardcodes from skills where possible; document external-stack deprecation path
- [ ] T058 Print setup summary `risk=` `investigator=` `home-api=` `deploy=`

---

## Phase 6: Triage loop in HOME (PR6) — US6

- [ ] T060 Triage sub-view: escalated list, notes, feedback buttons
- [ ] T061 Need More → reinvestigate API
- [ ] T062 RAG document id display when present
- [ ] T063 Skill wording: multi-vendor / adapter language in alert-triage + wifi-diagnosis

---

## Phase 7+: Adapters (PR7+)

- [ ] T070 NetBox SoT adapter stub + optional install component
- [ ] T071 Second wireless vendor stub in contracts + config
- [ ] T072 docker-compose.full.yml (Loki, VM, Grafana, speedtest)

---

## Phase H: HUD polish backlog (deferred — not blocking PR3+)

**Purpose**: Capture Visual HUD UX / mobile follow-ups so they survive context switches.  
**Detail doc**: [`hud-polish-backlog.md`](./hud-polish-backlog.md) (acceptance criteria, files, resume steps).  
**Default priority**: After Phase 3+ product path unless operator asks for HUD UX next.

### Already shipped (HUD shell hardening, 2026-07-24)

- [x] H000a Home Overview KPI headers centered (no global `.label` transform leak)
- [x] H000b Left/right/footer panel collapse + edge reopen chips; z-index vs taller topbar
- [x] H000c NetClaw Terminal drag / resize / collapse + desktop geometry persistence
- [x] H000d Mobile layout v1 (`mobile-layout.js`, bottom sheets, FOCUS/DPR, visualViewport, Home 2-col)

### Worth doing next

- [ ] H001 [P] Landscape mode chrome (compact topbar, taller usable graph/Home)
- [ ] H002 [P] `prefers-reduced-motion` (scan-beam / GSAP / auto FOCUS)
- [ ] H003 Touch long-press → node detail (cancel on orbit drag; optional haptic)
- [ ] H004 PWA shell (manifest, icons, optional shell+graph cache SW)
- [ ] H005 Offline / stale graph boot banner when `/api/graph` fails
- [ ] H006 Mobile smoke checklist in HUD README or 067 quickstart
- [ ] H007 [P] Knowledge panel mobile bottom-sheet + default collapsed
- [ ] H008 Dynamic `--topbar-height` via ResizeObserver (replace hard-coded offsets)
- [ ] H009 Persist quality mode + user pin in localStorage
- [ ] H010 Mobile terminal snap points (collapsed / peek / expanded)

**Suggested HUD-only session order**: H001+H002 → H003 → H006 → H004/H005 → H007–H010.

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

