# Feature Specification: NetClaw Home (HUD Home tab + productized home NOC)

**Feature Branch**: `067-convergence`  
**Created**: 2026-07-24  
**Status**: Draft (Phases 1–7 implemented; Phase 8 greenfield telemetry largely shipped; Phase 9 investigation policy + thin T2 agent implemented)  
**Input**: Productize the Convergence pipeline (metrics → alerts → NetClaw investigate → diary/triage → Discord → RAG) as a top-level HUD tab with Docker or K3s install, adapter wizard (firewall / SoT / wireless / **device SNMP** / **agent observability**), full-stack NetClaw framework coherence, and universal iN2N risk + guardian-claw ensure.

**Greenfield optional PR (Phase 8)**: Campus switch SNMP, device syslog, NetClaw
agent metrics/logs, and Grafana dashboards as **installable components** — not a
migration from any pilot observability repo. Detail:
[`device-telemetry-greenfield.md`](./device-telemetry-greenfield.md).

**Investigation policy (Phase 9)**: Operator-configurable **when** the alert path
spends LLM tokens (T0 observe / T1 summarize / T2 investigate allowlist + budgets).
Default cheap/safe; easy to open as alert hygiene improves. Detail:
[`investigation-policy.md`](./investigation-policy.md).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Switch to HOME tab in the Visual HUD (Priority: P1)

An operator running the NetClaw Visual HUD opens a **HOME** top-level tab next to **COMMAND**. The Home surface uses the same HUD look and feel (typography, glass panels, accents). Command continues to show the Three.js risk/integration universe. Chat remains available on both tabs.

**Why this priority**: Demonstrable product surface without requiring OBS migration; unblocks all later Home UI work.

**Independent Test**: Start `netclaw-hud` on :3001; click HOME; see styled Overview shell; click COMMAND; scene still works; no console errors.

**Acceptance Scenarios**:

1. **Given** the HUD is loaded, **When** the operator selects HOME, **Then** main content shows the Home view (not an iframe of an external site) styled with HUD design tokens.
2. **Given** HOME is active, **When** the operator selects COMMAND, **Then** the Three.js scene, sidebars, and filters behave as before.
3. **Given** either tab, **When** the operator uses chat, **Then** messages still reach the OpenClaw gateway.

---

### User Story 2 - See live home health without leaving NetClaw (Priority: P2)

From the HOME tab Overview (and Wi‑Fi / Devices / Diary sub-views), the operator sees health score, WAN, Wi‑Fi, and investigation diary data via NetClaw-hosted APIs (`/api/home/*` proxy → convergence-api), not by browsing a separate product origin.

**Why this priority**: Core value of embedding Network Guardian into NetClaw.

**Independent Test**: With pilot Prometheus/Guardian reachable, Overview KPIs match known live values for site `home`.

**Acceptance Scenarios**:

1. **Given** `HOME_API_URL` (or equivalent) points at a live convergence-api, **When** Overview loads, **Then** health/latency/loss/alert counts render from API data.
2. **Given** convergence-api is down, **When** Overview loads, **Then** the UI shows a clear degraded state (not a blank crash).

---

### User Story 3 - Install Home OBS stack with Docker or K3s (Priority: P2)

An operator chooses **Docker Compose** or **K3s** for metrics + convergence-api (+ exporters). Agent plane defaults to host NetClaw. Env and adapter config are shared between modes.

**Why this priority**: Upstream installability without requiring the internal observability-stack repo.

**Independent Test**: `docker compose -f deploy/convergence/docker-compose.yml up` (minimal) reaches convergence-api `/healthz` and Prometheus targets up.

**Acceptance Scenarios**:

1. **Given** Docker mode and UniFi adapter selected, **When** compose starts, **Then** unifi-exporter and Prometheus scrape succeed with configured key.
2. **Given** K3s mode, **When** manifests apply, **Then** the same logical services run and HUD can proxy to them.

---

### User Story 4 - Setup preserves any existing risk and ensures guardian-claw (Priority: P1)

Full Home pipeline setup **detects any existing iN2N risk** and keeps it. It **creates or ensures** a `guardian-claw` member (profile `network-guardian`) for investigations. Re-runs are idempotent.

**Why this priority**: Full Convergence pipe requires an investigator; must not destroy operators’ risks.

**Independent Test**: (a) Greenfield: after setup, `{risk}/guardian-claw` is active and `n2n_route(alert-triage)` resolves. (b) Existing risk with other members: members unchanged; guardian created only if missing.

**Acceptance Scenarios**:

1. **Given** no risk exists, **When** full Home setup runs, **Then** a risk is created and `guardian-claw` is enrolled with home skills.
2. **Given** risk `R` exists with members but no guardian, **When** setup runs, **Then** `R/guardian-claw` is added and other members remain.
3. **Given** `R/guardian-claw` already exists, **When** setup re-runs, **Then** no duplicate member and no secret wipe.
4. **Given** Alertmanager fires WifiDegraded, **When** the pipe runs, **Then** investigation is delegated to the guardian member and a diary event is written.

---

### User Story 5 - Adapter wizard (firewall, SoT, wireless) (Priority: P3)

Installer/setup asks which firewall, SoT (none/Nautobot/NetBox), and wireless vendor (none/UniFi/…); only prompts for selected credentials; writes `convergence.yaml` + `.env` keys documented in `.env.example`.

**Why this priority**: Multi-home productization; UniFi first implementation.

**Independent Test**: Select UniFi + pfSense + no SoT; setup writes config; Home Wi‑Fi view uses UniFi metrics path.

**Acceptance Scenarios**:

1. **Given** wireless=unifi, **When** setup completes, **Then** `UNIFI_*` keys are requested and unifi-exporter (or equivalent) is enabled in deploy generation.
2. **Given** sot=none, **When** setup completes, **Then** no Nautobot/NetBox credentials are prompted.

---

### User Story 6 - Greenfield campus switch SNMP + agent observability (Priority: P2)

An operator deploying **Convergence only** (no pilot observability stack) enables
optional components for **wired device SNMP** (e.g. Cisco Catalyst access/core
switches), **device syslog**, and **NetClaw agent** token metrics + log ship.
Prometheus, Loki, and Grafana on the Convergence deploy surface the same class of
signals used for switch monitoring and agent health — fully greenfield and
documented for an upstream PR.

**Why this priority**: Switch interface health and agent cost/logs are major
operational surfaces; they must not require a second private OBS repo.

**Independent Test**: On a clean host, install `convergence-core` +
`convergence-device-snmp` + `convergence-agent-metrics` with lab or mock SNMP;
Prometheus shows labeled switch metrics and `netclaw_model_*` without namespace
`observability` from any other project.

**Acceptance Scenarios**:

1. **Given** device SNMP targets in `convergence.yaml` and the device-snmp
   profile/component is enabled, **When** the stack starts, **Then** interface
   status/octets/errors (or documented equivalents) exist per `device_name`.
2. **Given** agent metrics component is enabled, **When** the host exporter runs,
   **Then** Convergence Prometheus scrapes it and a provisioned Grafana board
   (or Prom UI) shows token counters.
3. **Given** agent/device log forward is enabled and Loki is up, **When** a test
   log line is emitted, **Then** it is queryable with stable labels
   (`device_name` / `service`).
4. **Given** only minimal WAN+UniFi components, **When** device/agent options are
   off, **Then** install and runtime behave as today (no extra containers).

**Detail**: [`device-telemetry-greenfield.md`](./device-telemetry-greenfield.md) ·
tasks T080–T095.

---

### User Story 7 - Triage and feedback loop in HOME (Priority: P3)

Operators review escalated investigations in HOME → Triage, submit feedback, and trigger reinvestigate without leaving the HUD.

**Why this priority**: Closes the human-in-the-loop Convergence story.

**Independent Test**: Escalated event appears; Need More triggers reinvestigate; status moves to investigating.

---

### User Story 8 - Control investigation spend without code changes (Priority: P2)

An operator running Convergence can set **default investigation tier** (observe /
cheap summarize / allowlisted multi-tool investigate) and **open or close**
specific alertnames as alert hygiene improves, via a versioned policy file (and
optional setup mode preset). Auto multi-tool investigation is **not** required for
every alert; the observe plane (metrics, Alertmanager, diary) keeps working when
LLM budget is exhausted or OpenClaw is down.

**Why this priority**: Unbounded auto-investigation on every alert is economically
unsustainable (tool-schema tax + multi-turn sessions). Productizing the pipe
without productizing *when* the pipe spends tokens leaves operators broke or forced
to disable agents entirely.

**Independent Test**: With `default_tier: T0` and empty `allow_t2`, a synthetic
warning alert does not open a multi-tool OpenClaw investigation; adding one
`allow_t2` rule enables T2 for that alertname only after policy reload.

**Acceptance Scenarios**:

1. **Given** policy `default_tier: T0` and empty `allow_t2`, **When** a non-allowlisted
   warning fires to alert-receiver, **Then** no multi-tool hook investigation runs
   (T0: metrics/Discord/diary-only as configured).
2. **Given** operator adds `allow_t2: [{ alertname: TestCritical }]`, **When** policy
   reloads and that alert fires, **Then** T2 may run subject to budgets.
3. **Given** T2 hourly or concurrency budget is exhausted, **When** another T2-eligible
   alert fires, **Then** the system clamps to T0/T1 and records a budget-trip signal;
   Prometheus and convergence-api remain up.
4. **Given** setup mode preset `observe-only` or `investigate-critical`, **When** setup
   completes, **Then** a seeded policy file matches that posture and is documented in
   quickstart.
5. **Given** Prom label `investigate=false` or force_t0 rules, **When** such an alert
   fires, **Then** it never opens T2 even if default were higher.

**Detail**: [`investigation-policy.md`](./investigation-policy.md) · tasks T096–T110.

---

### Edge Cases

- Home-api unreachable: degraded banners, no uncaught exceptions.
- Risk exists but mesh down: setup reports clear error; does not delete member units.
- UniFi API key invalid: Wi‑Fi panel shows adapter error; other Overview KPIs still load.
- Docker resource constrained: minimal profile without Loki/Grafana still runs.
- Operator has non-standard investigator name: if it matches network-guardian profile skills, reuse rather than force rename (document policy).
- Investigation policy file missing: alert-receiver MUST fail safe to T0 (no multi-tool auto) and log a clear warning.
- Policy reload mid-flight: in-flight T2 may complete; new alerts use new policy within documented cache TTL (≤60s) or on SIGHUP.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: HUD MUST provide top-level tabs **COMMAND** and **HOME** without removing Command capabilities.
- **FR-002**: HOME UI MUST use existing HUD design tokens (CSS variables, typography, panel language).
- **FR-003**: Browser MUST call only HUD-origin APIs for Home data (`/api/home/*`); secrets stay server-side.
- **FR-004**: System MUST support deploy modes **docker** and **k3s** for OBS + convergence-api with shared adapter config.
- **FR-005**: Full pipeline setup MUST ensure an investigator member (`guardian-claw` / `network-guardian` profile) exists on the operator’s risk.
- **FR-006**: Setup MUST NOT destroy or rename an existing risk or non-Home members.
- **FR-007**: Setup MUST be idempotent for guardian-claw ensure and config generation.
- **FR-008**: Adapter config MUST model firewall, wireless, and SoT types; UniFi wireless is required for v1 path; others may be stubs.
- **FR-009**: Alert path MUST remain Alertmanager → alert-receiver → Border → guardian → convergence-api events → optional Discord/RAG.
- **FR-010**: Installer integration MUST use `scripts/lib/catalog.sh` + `install-steps.sh` + `.env.example` (no parallel framework).
- **FR-011**: Feature work MUST be tracked in `specs/067-convergence/tasks.md` with PR-aligned phases.
- **FR-012**: Skills and scripts introduced for Home MUST follow NetClaw conventions (GCF, skill scoping, no invented metrics).
- **FR-013**: System MUST support operator-configurable **investigation tiers** (at least T0 observe, T1 summarize, T2 multi-tool investigate) resolved from a versioned policy file (not hard-coded only in source).
- **FR-014**: Default posture MUST be **cheap/safe** (no unbounded multi-tool investigation on every alert); T2 MUST require explicit allow rules and/or critical allowlist semantics documented in quickstart.
- **FR-015**: Policy changes that open or close alertnames for T1/T2 MUST be possible without a code deploy (edit/reload policy file or documented CLI).
- **FR-016**: Alert-receiver MUST enforce investigation **budgets** (at least max concurrent T2 and max T2 per hour or equivalent) and fail soft (clamp tier) when exceeded.
- **FR-017**: Observe plane (Prometheus, Alertmanager, convergence-api diary read path) MUST remain available when LLM/OpenClaw is down or investigation budget is exhausted.
- **FR-018**: Auto T2 path MUST use a **thin tool profile** (or equivalent deny-list) distinct from the full interactive MCP set; deep device work SHOULD escalate to domain members (e.g. pyATS / guardian) rather than loading every MCP on the border for every alert.
- **FR-019**: Prom labels such as `investigate=false` and high-cardinality inventory alerts MUST be forceable to T0 even if default_tier is higher.
- **FR-020**: Setup MUST seed or document an example investigation policy and optional mode presets (`observe-only`, `triage-cheap`, `investigate-critical`).

### Key Entities

- **Risk**: iN2N risk identity (`N2N_RISK_NAME`), Border, members.
- **Guardian member**: Scoped claw running home investigation skills.
- **Home site**: Logical site id (e.g. `home`) with thresholds and adapter bindings.
- **Home event**: Investigation diary row (status, root_cause, notes, feedback, rag id).
- **Adapter binding**: firewall | wireless | sot type + connection env refs.
- **Investigation policy**: Versioned rules mapping alerts → tier (T0/T1/T2) + budgets + degrade.
- **Investigation tier**: Observe / summarize / multi-tool investigate / human-gated deep work.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operator switches COMMAND↔HOME in under 1s on a warm HUD load; Command scene remains interactive.
- **SC-002**: Greenfield full Home setup produces a live guardian member without manual member authoring.
- **SC-003**: Existing multi-member risk loses zero members after Home setup re-run.
- **SC-004**: Synthetic or real WifiDegraded produces a diary event visible in HOME within investigation SLA (same order as pilot, not worse).
- **SC-005**: Docker minimal stack reaches healthy convergence-api + Prometheus without external k3s-observability-stack checkout.
- **SC-006**: `.env.example` documents every new Home env key with comments and empty/safe defaults.
- **SC-007**: With default policy (T0, empty T2 allowlist), a synthetic non-allowlisted warning does **not** start a multi-tool OpenClaw investigation.
- **SC-008**: Operator can enable T2 for one alertname by editing policy (or documented CLI) and reloading within ≤60s without rebuilding alert-receiver.
- **SC-009**: Budget trip is observable (log and/or metric) and does not take down Prometheus or convergence-api.

## Assumptions

- Host NetClaw (OpenClaw/Hermes) remains the default agent runtime; Docker agent profile is optional greenfield only.
- Pilot k3s-observability-stack continues to run until Home deploy packages reach parity; dual-run is allowed during migration.
- UniFi Integration API + unifi-exporter remain the first wireless implementation.
- Channel AI / radio Optimize remains human UI MoP (no auto-apply requirement in 067).
- Selective auto-investigation (not “every alert”) is an acceptable and preferred product posture for sustainable Agentic NOC.
- Local small models may serve T1 / interactive light / offline fallback; capable models (cloud or larger local) remain appropriate for T2 when allowlisted.

## Out of Scope (v1)

- Additional wireless vendors beyond UniFi (stubs/contracts only).
- Auto radio mutation APIs.
- Replacing Grafana operator dashboards.
- Multi-tenant SaaS control plane.
- Full GUI CRUD for investigation policy (file + optional CLI sufficient for Phase 9).
- One OpenClaw member process per MCP tool.
- Mandating a specific local 9B model as the sole T2 brain.
