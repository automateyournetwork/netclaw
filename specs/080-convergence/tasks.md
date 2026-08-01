# Tasks: NetClaw Home (080-convergence)

**Input**: Design documents from `/specs/080-convergence/`  
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

- [x] T001 Create `specs/080-convergence/` with spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md, contracts/, checklists/
- [x] T002 [P] Author FR/user stories including risk preserve + guardian-claw ensure (any operator)
- [x] T003 [P] Author contracts for convergence-api, adapters, install wizard
- [x] T004 Constitution Check recorded in plan.md
- [x] T005 Checklist requirements.md pass — signed off 2026-07-27 with a review log
      and a pre-PR drift guard (see `checklists/requirements.md`)

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
- [x] T142 Log-panel selectors (FR-034) — all Loki panels now select streams by
      label, never by message-content regex. Confirmed the journal relabel chain
      was never broken: `job=netclaw-mesh` / `unit=netclaw-mesh.service` resolve
      correctly, so the regex workaround was covering for **idle units**, not
      mislabelling.
      · NetClaw: gateway `{job="openclaw-gateway"}`; N2N/mesh
        `{job=~"netclaw-mesh|netclaw-member"}`; errors panel keeps a line filter
        (content filtering is its purpose) but selects streams by job
      · Security: block + auth panels move onto the `app` label published by the
        T141 gateway (`filterlog|snort|suricata`, `sshd|sudo|su|login|nginx|openvpn`)
      · New Security rate panels — firewall block rate by device, unbound DNS
        activity — the log-shaped half of the T143 gap
      · promtail journal `max_age` 24h → 168h so event-driven mesh/member units
        keep recent history across a collector restart (unit keep list bounds
        volume; positions file prevents re-ship)
      · `deploy/convergence/smoke-log-panels.sh` asserts every board query is
        valid LogQL and reports OK / **EMPTY** / FAIL per panel, so "empty" is
        always attributable — 8/8 queries valid, 0 failures
      · patch script retained at `grafana/patch-t142.py` (idempotent)
- [x] T143 Security depth collector (FR-031/FR-033) — closed **without** writing a
      pfSense exporter. The events were already in Loki as structured fields
      (T157), so the Loki **ruler** derives metrics from them and remote-writes to
      Prometheus, where the existing alerting engine and boards use them like any
      other series.
      · `loki-config.yaml`: ruler with local file store (rules read-only,
        GitOps-managed, API off) + `remote_write` → `prometheus:9090/api/v1/write`
      · `prometheus`: `--web.enable-remote-write-receiver`
      · 7 recording rules live: `pfsense:filterlog_blocks:rate5m`,
        `..._pass:rate5m`, `..._blocks_by_interface:rate5m`,
        `..._blocks_by_protocol:rate5m`, `pfsense:dns_{queries,nxdomain,servfail}:rate5m`
      · `| label_format` renames Loki's `attributes_*` fields to clean Prometheus
        labels (`interface`, `direction`, `protocol`) **before** anything depends
        on them — renaming a series' labels after alerts reference it is breaking
      · gotcha: the ruler's remote-write WAL defaults to a *relative* path
        (`ruler-wal`) in a non-writable CWD and crash-loops with "permission
        denied"; pinned to `/loki/ruler-wal` on the data volume
      · verified: 14 clean series in Prometheus (blocks 6.18/s, pass 11.32/s,
        per-interface and per-protocol breakdowns), 0 WAL errors
      · still open (T152): nothing remote-writes to **VictoriaMetrics** yet, so
        long-term retention of these series is not real until the SNMP cutover

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


---

## Phase 11: OTel Collector as the telemetry hub (optional PR) — US11

**Purpose**: Replace the promtail + syslog-gateway + snmp_exporter trio with a
single OpenTelemetry Collector: structured syslog dual-exported to Loki +
VictoriaLogs, SNMP remote-written to VictoriaMetrics. Matches the pilot design.

**Decision record**: [`otel-convergence.md`](./otel-convergence.md) ·
spec US11 / FR-036–FR-042 / SC-017–SC-019

**Supersedes**: T141 syslog-gateway (rfc3164 front-end becomes unnecessary — the
OTel syslog receiver speaks rfc3164 natively) and the snmp_exporter path from
T126/T128. Both remain in place until the phase that retires them.

### Spec & measurement (PR0)

- [x] T145 Author `otel-convergence.md`; extend `spec.md` US11 + FR-036–FR-042 +
      SC-017–SC-019; probe the real metric names/labels rather than assuming
      (`deploy/convergence/otel/probe-snmp-names.yaml`).
      **Measured**: OTel emits `interface_status`,
      `interface_octets_in_bytes_total`, `interface_errors_in_total` — byte-for-byte
      the names the Phase 10 recording rules already synthesise, so **no metric
      rename is required**; labels reduce to `device_name` + `interface_name` +
      `site` (no ifIndex/ifName/ifDescr); `interface_admin_status` comes free.

### Logs (PR1) — smallest blast radius, retires the newest component

- [x] T146 `deploy/convergence/otel/otel-config.yaml` — `syslog` receiver
      (`protocol: rfc3164`, udp+tcp :1514), device identity from sender IP →
      message hostname → IP, receive-time stamping, clean parsed body,
      bounded label promotion via `groupbyattrs` (FR-042).
      **Two defects found and fixed while building:**
      (a) writing `resource.attributes` from a log-context transform smears the
      resource across a batch — one record from 172.19.0.1 came out carrying
      resource `device_ip=192.168.3.1`, i.e. one device's logs mislabelled as
      another's. `groupbyattrs/device` re-partitions per attribute set and is the
      correct primitive.
      (b) Cisco IOS syslog is **not RFC3164-compliant** (`<189>1834: *Jul 27
      22:12:00.456: %LINK-3-UPDOWN: ...`) so the rfc3164 parser fails and forwards
      it raw — not dropped, but not structured. Added a `regex_parser` operator
      extracting `priority`/`sequence`/`device_time`/`mnemonic`/`sev_level`/`message`.
      This is why the pilot used raw `udplog`.
      Note: `on_error` is not a valid top-level key on this receiver in 0.104.0;
      default behaviour already forwards unparsed entries (FR-035 holds).
- [x] T147 Compose services `otel-collector` + `victorialogs` (v1.52.0 pinned,
      365d) on profiles `full`|`device-syslog`; exporters `loki` +
      `otlphttp/victorialogs`, both with persistent file-storage send queues.
      `otel-queue-init` one-shot fixes named-volume ownership so the collector
      runs unprivileged (UID 10001) rather than as root on a network listener.
      Prometheus scrape job `otel-collector` added.
- [x] T148 Retired syslog-gateway (container removed, compose service deleted)
      and the promtail `device-syslog` job; promtail keeps host files + journal.
      Repointed the ingest alert pack off promtail counters onto
      `otelcol_*` — `SyslogIngestRefusing`, `LogExportFailing`,
      `SyslogIngestNoEntries`, `LogIngestDown`, plus `HostLogShipDown` for
      promtail. The old promtail-based rules would have sat flat at zero forever;
      an alert that cannot fire is worse than no alert.
- [x] T149 Security board queries structured fields
      (`| json | attributes_appname=~...`, `attributes_mnemonic=~...`) instead of
      the retired `app` label; `grafana/patch-t149.py` (idempotent).
      `smoke-log-panels.sh` now counts lines via `count_over_time` instead of
      asking `/series` — an idle source reported 0 streams while the same
      selector returned real lines, so the verification tool was itself
      misleading. **SC-017 verified**: the same line is queryable in Loki
      (bounded labels) and VictoriaLogs (full structured fields).

### Agent logs (PR2)

- [x] T150 **Decision: host/agent logs stay on promtail.** OTel owns devices,
      promtail owns host sources. Measured, not assumed.
      · decisive: OTel's `journald` receiver shells out to `journalctl`, and the
        collector image is distroless — no shell, no coreutils
        (`/bin/ls` does not exist). Journal collection would need a **custom
        collector image** maintained across every version bump, for zero functional
        gain.
      · a partial move (only `filelog` for OpenClaw files) does not remove promtail,
        because the journal still needs it — so both processes keep running and
        nothing is simplified
      · footprint measured: promtail 28 MiB / 2 targets vs collector 79 MiB. The
        28 MiB is only recoverable by removing promtail entirely, which the journal
        constraint blocks.
      · promtail's journal relabelling is already correct (T142 verified
        `job=netclaw-mesh` / `unit=netclaw-mesh.service`);
        `promtail_journal_target_parsing_errors_total` is the unit keep-filter
        dropping non-NetClaw units, not a fault
      · revisit triggers documented in `otel-convergence.md`: a custom image needed
        for another reason, a native OTel journal reader, or host log volume growing
        enough to make promtail the constraint
      · note: no K3s equivalent exists for host/agent logs — the K3s collector is
        device-only, and agent logs live on the NetClaw host

### SNMP (PR3) — the rename-free cutover

- [x] T151 OTel `snmp/<device>` receivers per inventory target with
      `service.name: device_snmp` + `service.instance.id: <ip>` so `job`/`instance`
      selectors survive (FR-040). Reference shape documented in
      `deploy/convergence/otel/snmp-receivers.md` (T154 generates it).
      **Staged first** under `service.name: device_snmp_otel` and run alongside
      snmp_exporter to prove parity: identical series counts (interface_status 300,
      octets 172, errors 190), **0 set differences** in either direction, **0 value
      mismatches**. Then flipped.
- [x] T152 `interface.admin.status` (ifAdminStatus) added — 300 series, and 79
      interfaces are administratively shut, which was previously indistinguishable
      from link-failed. `prometheusremotewrite` wired to **both** Prometheus (15d,
      what boards and alerts query) and **VictoriaMetrics** (365d). VictoriaMetrics
      had **zero series ever written** before this; the 365d retention claim in the
      docs was fiction until now — 2,648 series present.
- [x] T153 Retired `snmp_exporter` (service + container), the `device_snmp` scrape
      job, and `device-recording.rules.yml` — OTel emits the final metric names
      directly, so the `label_replace` chain that synthesised them is redundant.
      **The T145 risk assessment about `ifIndex` was wrong** and this task found it:
      `SwitchIdlePortsPresent` and `SwitchLinkLost` joined on
      `on(instance, ifIndex, device_name)` *and* selected the raw
      `ifOperStatus`/`ifAdminStatus` names; `SwitchInterfaceErrorsHigh` used
      `ifInErrors`/`ifOutErrors`; two board panels selected `up{job="device_snmp"}`,
      which ceases to exist without a scrape job. All rewritten:
      · joins → `on(instance, interface_name, device_name)`
      · raw names → `interface_status` / `interface_admin_status` / `interface_errors_*`
      · `DeviceSnmpExporterDown` → `DeviceSnmpStale` (freshness via `timestamp()`,
        device-agnostic, no exporter to watch)
      · `SwitchLinkLost` annotations use `interface_name`; the admin-status term is
        now authoritative rather than inferred from a 15m offset heuristic
      · board panels → `count(count by (device_name) (interface_status))`, which
        measures data arriving rather than a scrape target being up
      Verified: 10 rules load, all four rewritten rules `health=ok`; 3 devices
      reporting; up/down counts 58/63/35; 12/12 log-panel queries pass.
      Lesson recorded in the decision record: grep for the **raw metric names**,
      not just the label, before claiming a label is display-only.

### Wizard & K3s (PR4)

- [x] T154 `render-convergence-telemetry.py` emits the OTel Collector's managed
      sections from `convergence.yaml` inventory; schema unchanged for SNMP targets.
      Four generated blocks, each with BEGIN/END markers: `snmp/<device>` receivers,
      per-device `resource/<device>` processors (service.name → `job`,
      service.instance.id → `instance`), `metrics/<device>` pipelines, and the
      syslog sender-IP → `device_name` map.
      · `--otel-job` stages a distinct job label (e.g. `device_snmp_otel`) so a
        future cutover can prove parity before flipping, the same way T151 did
      · **inventory gap found by round-tripping**: generating the device map from
        SNMP targets alone silently dropped pfSense, HomeSwitch03 and the NetClaw
        host — all send syslog, none are SNMP targets. Added optional
        `device_telemetry.syslog.devices`, and the map is now the **union** of both
        lists. Documented in `config/convergence.example.yaml` with the reason.
      · round-trip verified: generated output reproduces the hand-written config
        (differences are comments only), a second run is byte-identical
        (idempotent), and the result passes `otelcol validate`
- [x] T155 `convergence-telemetry-apply.sh` manages the collector config section
      idempotently and **validates before restarting** — a bad collector config
      takes device telemetry down entirely, because the collector exits rather than
      running degraded. Invalid config aborts the apply with the validator output
      and leaves the running collector alone.
      · restarts `otel-collector` instead of `snmp-device-exporter`; the config is
        bind-mounted and read only at start, and there is no reload endpoint
      · `--dry-run` prints the generated collector blocks alongside the snmp module
        keys
      · `snmp.yml` is still rendered — the wireless exporter uses it and it is the
        OID/vendor reference the generator reads
      · `.env.example`: `SNMP_COMMUNITY` is now consumed for real via
        `${env:SNMP_COMMUNITY}`, not just documented
      · end-to-end apply against the live stack: config valid → collector restarted
        → Prometheus reloaded → 3 devices reporting within ~1 minute

- [x] T156 K3s parity — the overlay was shipping a **broken** stack, three
      generations behind Docker. Fixed rather than deferred.
      · new `components/otel-collector`: syslog + SNMP in one Deployment, hostPort
        1514 udp+tcp, unprivileged (runAsUser 10001, fsGroup for the send queue),
        health/readiness probes
      · new `components/full-stack/victorialogs.yaml` (v1.52.0, 365d, 20Gi PVC)
      · **deleted** `components/device-syslog` (syslog-ng + promtail — promtail
        parses RFC5424 only, so it silently discarded every RFC3164 device log) and
        `components/device-snmp` (snmp_exporter)
      · **`--web.enable-remote-write-receiver` was missing on the K8s Prometheus.**
        Both the collector's SNMP metrics and the Loki ruler's derived metrics
        arrive by remote-write, so without it K3s would have had **no device
        metrics at all** — the cutover would have looked applied and produced
        nothing.
      · Loki ruler + `loki-rules` ConfigMap + `/loki/rules/fake` mount: T143's
        log-derived pfSense metrics existed only on Docker
      · `base/configs/device.rules.yml` had **drifted 210 lines** from its Docker
        original — despite a "keep in sync" comment — and still selected retired
        names (`ifOperStatus`, `ifInErrors`), so those alerts could never fire.
        Re-synced.
      · `check-config-drift.sh` (+ `--fix`): the copies are now machine-checked.
        A symlink would be better but Kustomize refuses files outside its root and
        requiring `--load-restrictor LoadRestrictionsNone` is worse than a copy.
      · `base/configs/prometheus.yml`: `device_snmp` scrape job removed,
        `otel-collector` health scrape added
      · verified: all three overlays build and pass `kubectl apply --dry-run`;
        `promtool check rules` clean; no retired image (promtail / syslog-ng /
        snmp-exporter) present in any rendered workload; drift guard clean.
        `HostLogShipDown` remains but is inert on K3s (no promtail scrape job) —
        kept so the rules stay byte-identical and the drift guard keeps working.

### Independent test

Cisco + pfSense syslog → structured fields in Loki **and** VictoriaLogs, no
message regex; SNMP cutover leaves every board and alert query unchanged;
`interface_admin_status` present; Loki stream count stays bounded as new Cisco
mnemonics appear.

---

## Phase 12: SuzieQ state-history plane (optional PR, scale tier) — US12

**Purpose**: Add a **state-history** plane for larger-scale deployments so
investigations can ask "what was the BGP/route/MAC/ARP/LLDP state 15 minutes
before this alert fired" without SSHing to devices at investigation time.
Complements the OTel ingest hub — does **not** replace it.

**Decision record**: [`suzieq-state-observability.md`](./suzieq-state-observability.md) ·
spec US12 / FR-043–FR-050 / SC-020–SC-023

**Ships off by default.** Component `convergence-suzieq` is excluded from
`PROFILE_CONVERGENCE`; recommended only above the documented scale threshold
(>~25 devices, or any BGP/EVPN/VXLAN/MLAG fabric, or multi-site).

**Reuses, does not duplicate**: the Phase 10 inventory
(`device_telemetry.snmp.targets`), `render-convergence-telemetry.py`,
`convergence-telemetry-apply.sh`, `check-config-drift.sh`, and the Phase 9 thin
`alert` agent profile. No second inventory, no second apply path.

**Prior work already shipped** (spec `001-suzieq-mcp-server`, 28/28): the MCP
server, `suzieq-observability` skill, `openclaw.json` registration, iN2N member,
and catalog entry all exist. What was missing is a deployed poller and any
convergence integration.

### Spec, hardening & measurement (PR0) — blocks everything else

- [ ] T158 [P] **Harden `mcp-servers/suzieq-mcp` for scale.** Measured defect:
      there is **no row limit, no response-size ceiling, and `columns` defaults
      to all columns** (`server.py:256`); the only `[:200]` slices in the repo
      are on HTTP error strings (`suzieq_client.py:191,264`). At target scale
      `suzieq_show table=route` (or `mac` / `arpnd`) returns an unbounded payload
      that consumes the context window in one call, bypassing Phase 9's
      `budgets.max_tokens`. Add:
      · `max_rows` parameter, default ~200, applied server-side
      · hard byte ceiling on the serialized response
      · per-table default column sets (never all-columns by default)
      · **explicit truncation metadata** — `truncated`, `rows_returned`,
        `rows_available` — so a subset is never mistaken for a small table
        (same no-silent-loss principle as FR-035)
      · **data-freshness stamps** — newest timestamp per table/device in the
        response envelope, so the model can see it is reasoning over stale data
- [ ] T159 [P] **Fix the broken-client-in-a-profile defect.** `suzieq` is in
      `PROFILE_RECOMMENDED` today with no server deployed and
      `SUZIEQ_API_URL` commented out, so a recommended install advertises 5 tools
      that can only return connection errors. Either gate registration on
      `SUZIEQ_API_URL` being set or remove it from `PROFILE_RECOMMENDED`.
      Independent of the rest of this phase.
- [ ] T160 **Measure before scoping** (do not treat as known):
      · IOS-XE table coverage for `bgp`/`route`/`mac`/`arpnd`/`lldp`/`vlan`/
        `interface` against ≥2 lab Catalysts — diff completeness vs `pyats`
        parsed output. SuzieQ's strongest support is Cumulus/SONiC/Arista/Junos/
        NXOS; if IOS-XE is thin, this phase becomes vendor-conditional and the
        docs must say so.
      · pfSense/FreeBSD support — believed out of scope entirely. If so, record
        that the firewall stays a metrics/logs-only citizen and set
        `exclude_roles: [firewall]` in the example config.
      · Upstream health — check real commit/issue activity on
        `netenglabs/suzieq`, not search snippets. OSS PyPI/stable-release signals
        cluster around May 2025 (~14 months stale) while differentiated work
        moves into SuzieQ **Enterprise**. If dormant, pin a known-good version
        and record accepted risk.
      · Poller RSS + parquet growth/day at N devices, for the sizing table.

### Inventory render (PR1)

- [ ] T161 Extend `render-convergence-telemetry.py` with a **fourth output**:
      SuzieQ `inventory.yml` + namespace map, rendered from the existing
      `device_telemetry.snmp.targets` list. Same managed-section markers, same
      idempotency contract. Nautobot/NetBox modes feed it for free.
      Add the additive `device_telemetry.state.suzieq` block to
      `config/convergence.example.yaml` (`enabled: false` default, namespace,
      poll_period, retention_days, `exclude_roles`, credential **env refs only**).
      **No secret may appear in the rendered inventory** — same rule as
      `SNMP_COMMUNITY`.
- [ ] T162 Extend `check-config-drift.sh` to cover the SuzieQ renders, and verify
      a second `convergence-telemetry-apply.sh` run is a no-op (no duplicate
      inventory entries, no clobbering of unrelated config).

### Docker adapter (PR2)

- [ ] T163 `deploy/convergence/adapters/suzieq/` following the `device-snmp`
      pattern — `README.md` (scale guidance, credential model, sizing),
      `inventory.yml.tmpl`, `suzieq-cfg.yml.tmpl`. Compose profile `["suzieq"]`:
      poller + REST API, named volume for the parquet lake, retention applied.
      **SuzieQ's own SNMP collection path pinned off** — exactly one thing polls
      SNMP in this architecture and it is the OTel Collector (FR-045).
- [ ] T164 Scrape the `sqPoller` table into Prometheus and add
      `SuzieQPollerDown` / `SuzieQPollerStale` to the alert pack per
      `docs/CONVERGENCE-ALERT-SAFETY.md` with `investigate` labels.
      **Rationale**: a stale lake is worse than no lake — the agent will report
      week-old adjacency state as current, write a wrong root cause to the diary,
      and seed RAG with a bad prior.
- [ ] T165 `smoke-suzieq.sh` — poller reaches devices, REST answers, tables
      populate, freshness stamps present, **SNMP path asserted off**, and a
      deliberately oversized query returns truncated-with-metadata rather than an
      unbounded payload.

### K3s parity (PR3)

- [ ] T166 `k8s/components/suzieq` — Deployment(s), PVC for the lake, Secret ref
      for device credentials, Service. Ship **with** Docker, not after it: T156
      found the overlay three generations behind and shipping a broken stack.
      All three overlays must build and pass `kubectl apply --dry-run`.

### Agent wiring (PR4) — gated on T158

- [ ] T167 Add `suzieq-mcp__*` to `tools.allow` in
      `deploy/convergence/config/alert-agent.example.json`. Fits the FR-018 thin
      profile (read-only, single-purpose, no config authority). Note in
      `investigation-policy.md` that this **removes** the pyATS-escalation cost
      for a class of questions rather than only adding capability.
- [ ] T168 Rewrite `workspace/skills/suzieq-observability` to **enforce** bounded
      queries, not merely permit them: always a relative `start_time`;
      `view=changes` preferred over `latest` over full dumps; explicit `columns`
      on every call; `summarize` to size before `show` to inspect. Document the
      **T1 state-context path** — a single bounded
      `suzieq_show view=changes start_time=-15m columns=<pinned>` fits inside
      T1's `max_tools: 0–1` / `max_completion_tokens: 4000`, which makes T1
      useful for the first time (today it is a summarizer with no data access).

### Wizard + installer (PR5)

- [ ] T169 Catalog component `convergence-suzieq` (Convergence category), **not**
      added to `PROFILE_CONVERGENCE`. Wizard prompt must **disclose the
      credential ask plainly** before prompting — SuzieQ needs device login
      credentials held by a long-running poller, a material escalation over
      today's read-only SNMP community and push-syslog. Require a dedicated
      read-only service account, env/Vault refs only, per-namespace separation.
      Add scale-threshold guidance to `quickstart.md`.

### Assert / change validation (PR6)

- [ ] T170 Document `suzieq_assert` paired with `nautobot-golden-config-mcp`
      remediation as a pre/post-change workflow: assert observed BGP/OSPF/
      interface health → push intended config → assert again. Closes a validation
      gap currently handled by hand. Assertions **inform only** — no
      auto-remediation from assert results.

### Independent test

On a fleet at or above the scale threshold: inventory declared once in
`convergence.yaml` produces both OTel SNMP receivers and a SuzieQ inventory; the
poller populates state tables; `sqPoller` staleness is alertable; a synthetic
allowlisted alert at T1 receives bounded state-change context without a device
login; an oversized query returns truncated-with-metadata rather than exhausting
the context window; and a second apply is a no-op.
