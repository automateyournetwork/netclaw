# Feature Specification: NetClaw Home (HUD Home tab + productized home NOC)

**Feature Branch**: `067-convergence`  
**Created**: 2026-07-24  
**Status**: Draft  
**Input**: Productize the home Convergence pipeline (metrics → alerts → NetClaw investigate → diary/triage → Discord → RAG) as a top-level HUD tab with Docker or K3s install, adapter wizard (firewall / SoT / wireless), full-stack NetClaw framework coherence, and universal iN2N risk + guardian-claw ensure.

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

### User Story 6 - Triage and feedback loop in HOME (Priority: P3)

Operators review escalated investigations in HOME → Triage, submit feedback, and trigger reinvestigate without leaving the HUD.

**Why this priority**: Closes the human-in-the-loop Convergence story.

**Independent Test**: Escalated event appears; Need More triggers reinvestigate; status moves to investigating.

---

### Edge Cases

- Home-api unreachable: degraded banners, no uncaught exceptions.
- Risk exists but mesh down: setup reports clear error; does not delete member units.
- UniFi API key invalid: Wi‑Fi panel shows adapter error; other Overview KPIs still load.
- Docker resource constrained: minimal profile without Loki/Grafana still runs.
- Operator has non-standard investigator name: if it matches network-guardian profile skills, reuse rather than force rename (document policy).

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

### Key Entities

- **Risk**: iN2N risk identity (`N2N_RISK_NAME`), Border, members.
- **Guardian member**: Scoped claw running home investigation skills.
- **Home site**: Logical site id (e.g. `home`) with thresholds and adapter bindings.
- **Home event**: Investigation diary row (status, root_cause, notes, feedback, rag id).
- **Adapter binding**: firewall | wireless | sot type + connection env refs.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operator switches COMMAND↔HOME in under 1s on a warm HUD load; Command scene remains interactive.
- **SC-002**: Greenfield full Home setup produces a live guardian member without manual member authoring.
- **SC-003**: Existing multi-member risk loses zero members after Home setup re-run.
- **SC-004**: Synthetic or real WifiDegraded produces a diary event visible in HOME within investigation SLA (same order as pilot, not worse).
- **SC-005**: Docker minimal stack reaches healthy convergence-api + Prometheus without external k3s-observability-stack checkout.
- **SC-006**: `.env.example` documents every new Home env key with comments and empty/safe defaults.

## Assumptions

- Host NetClaw (OpenClaw/Hermes) remains the default agent runtime; Docker agent profile is optional greenfield only.
- Pilot k3s-observability-stack continues to run until Home deploy packages reach parity; dual-run is allowed during migration.
- UniFi Integration API + unifi-exporter remain the first wireless implementation.
- Channel AI / radio Optimize remains human UI MoP (no auto-apply requirement in 067).

## Out of Scope (v1)

- Additional wireless vendors beyond UniFi (stubs/contracts only).
- Auto radio mutation APIs.
- Replacing Grafana operator dashboards.
- Multi-tenant SaaS control plane.
