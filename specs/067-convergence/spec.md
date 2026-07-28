# Feature Specification: NetClaw Home (HUD Home tab + productized home NOC)

**Feature Branch**: `067-convergence`  
**Created**: 2026-07-24  
**Status**: Draft (Phases 1–7 implemented; Phase 8 greenfield telemetry plumbing shipped; Phase 9 investigation policy + thin T2 agent implemented; Phase 10 PR1–PR3 shipped — inventory/apply/wizard + holistic Network·Security·NetClaw board suite; **open**: vendor-default syslog ingest → Security log panels, pfSense security-depth collector)  
**Input**: Productize the Convergence pipeline (metrics → alerts → NetClaw investigate → diary/triage → Discord → RAG) as a top-level HUD tab with Docker or K3s install, adapter wizard (firewall / SoT / wireless / **device SNMP** / **agent observability**), full-stack NetClaw framework coherence, and universal iN2N risk + guardian-claw ensure.

**Greenfield optional PR (Phase 8)**: Campus switch SNMP, device syslog, NetClaw
agent metrics/logs, and Grafana dashboards as **installable components** — not a
migration from any pilot observability repo. Detail:
[`device-telemetry-greenfield.md`](./device-telemetry-greenfield.md).

**Investigation policy (Phase 9)**: Operator-configurable **when** the alert path
spends LLM tokens (T0 observe / T1 summarize / T2 investigate allowlist + budgets).
Default cheap/safe; easy to open as alert hygiene improves. Detail:
[`investigation-policy.md`](./investigation-policy.md).

**Telemetry setup (Phase 10)**: Productize **how** operators declare inventory
(manual or SoT), apply vendor SNMP templates, get named-interface metrics,
curated Grafana boards, safe alerts, and device config checklists — without
hand-editing Prometheus or cloning the pilot OBS stack. Detail:
[`telemetry-setup.md`](./telemetry-setup.md).

**Telemetry hub (Phase 11)**: Device ingest converges on a single **OpenTelemetry
Collector** — structured syslog → Loki (14d) + VictoriaLogs (365d), SNMP →
Prometheus (15d) + VictoriaMetrics (365d). Supersedes the syslog-gateway and
snmp_exporter. **promtail is retained for host/agent sources only** (OpenClaw files,
systemd journal) — see the T150 decision. Decision record:
[`otel-convergence.md`](./otel-convergence.md).

**Board suite (Phase 10 PR3+)**: The provisioned Grafana suite is **three**
narrative boards — **Network**, **Security**, **NetClaw** — not the ported pilot
board set (parked unloaded under `grafana/provisioning/dashboards/legacy/`).
Reference: [`deploy/convergence/grafana/README.md`](../../deploy/convergence/grafana/README.md).

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

### User Story 9 - Greenfield telemetry setup from inventory (Priority: P2)

An operator installing Convergence can declare a device inventory (**manual**
list or **Nautobot/NetBox select**), apply **vendor SNMP templates** (Cisco and
pfSense first), enable scrapes and recording rules that expose **human interface
names**, provision a **curated** Grafana suite, and receive a **site-specific
device config checklist** for SNMP/syslog — without hand-editing Prometheus or
cloning `k3s-observability-stack`.

**Why this priority**: Phase 8 shipped collectors and partial boards; operators
still cannot easily go from empty site → named interfaces + usable dashboards.
Productizing setup closes the greenfield day-1 gap and feeds Phase 9
investigation with better signals.

**Independent Test**: From empty `device_snmp` targets, run setup wizard with ≥2
Cisco lab switches, apply; within 5 minutes Prometheus shows healthy
`device_snmp` scrapes and `interface_status` (or `ifOperStatus`) with non-empty
interface name labels; the Grafana **Network** board (`convergence-network`,
**:3300**) campus switching section legends are not ifIndex-only.

**Acceptance Scenarios**:

1. **Given** empty device targets and wizard mode `manual` with ≥2 Cisco switches,
   **When** apply runs, **Then** Prometheus has `device_snmp` up and interface
   series with `ifDescr`/`ifName`/`interface_name` labels within 5 minutes.
2. **Given** `sot.type=nautobot` and mode `nautobot`, **When** the operator selects
   devices from the list, **Then** selected devices are written into
   `convergence.yaml` targets without manual IP typing.
3. **Given** apply completed for lab switches, **When** the operator opens Grafana
   folder Convergence on **:3300**, **Then** the **Network** board campus
   switching section shows named interfaces (not ifIndex-only legends).
4. **Given** apply completed, **When** the operator opens the generated checklist,
   **Then** it includes site-specific syslog host:port and the SNMP community
   **env name** (not a committed secret).
5. **Given** device telemetry options off, **When** install/runtime runs, **Then**
   minimal WAN+UniFi behavior is unchanged (no extra containers).
6. **Given** a second apply with the same inventory, **When** apply re-runs,
   **Then** managed Prometheus sections are updated idempotently (no duplicate jobs).

**Detail**: [`telemetry-setup.md`](./telemetry-setup.md) · tasks T120–T138.

---

### User Story 10 - Three holistic boards instead of scattered stats (Priority: P2)

An operator opening Grafana folder Convergence finds **three** narrative boards —
**Network**, **Security**, **NetClaw** — each telling one story end to end, rather
than a pile of ported single-subject boards that are half empty because no
matching collector is installed. Every panel on a provisioned board must be
backed by a collector that the Convergence deploy can actually install, and each
board must state its data dependencies so an operator can tell "not deployed"
from "broken".

**Why this priority**: Phase 8/10 PR1–PR2 shipped collectors and ported ~13 pilot
boards. Scattered, mostly-empty boards are worse than fewer complete ones: they
train operators to ignore Grafana and they hide genuine collector gaps (e.g. no
pfSense block/DNS exporter) behind panels that merely look unpopulated.

**Independent Test**: On a Docker install with device-snmp + UniFi + agent
metrics, Grafana **:3300** folder Convergence lists exactly Network, Security,
NetClaw; every panel on Network and NetClaw returns data; Security's Prometheus
panels return data and its log panels are documented as requiring device syslog.

**Acceptance Scenarios**:

1. **Given** a provisioned Convergence deploy, **When** the operator opens folder
   Convergence, **Then** exactly the three primary boards are provisioned and
   pilot/ported boards are parked unloaded under
   `grafana/provisioning/dashboards/legacy/`.
2. **Given** the Network board, **When** it loads with device-snmp + UniFi +
   blackbox up, **Then** it shows site health, WAN, named campus interfaces,
   Wi‑Fi, and edge without empty panels.
3. **Given** the Security board, **When** device syslog is **not** yet ingesting,
   **Then** posture/alert/edge/wireless panels still render from Prometheus and
   the board (or its README) states that log panels require syslog → promtail.
4. **Given** the NetClaw board, **When** the token exporter and alert-receiver
   scrapes are up, **Then** cost/token by provider and T0/T1/T2 investigation
   counters render, and log panels select on `job`/`unit` labels (not message
   regex).
5. **Given** a board panel whose metric has no installable collector in this
   repo, **When** the suite is reviewed, **Then** that panel is removed or the
   collector is added — a provisioned board MUST NOT depend on the pilot
   `k3s-observability-stack`.

**Detail**: [`deploy/convergence/grafana/README.md`](../../deploy/convergence/grafana/README.md)
· tasks T139–T144.

---

### User Story 11 - One OTel ingest hub with structured logs (Priority: P2)

An operator running Convergence gets device telemetry through a **single
OpenTelemetry Collector**: syslog parsed into structured fields at ingest and
dual-exported to **Loki** (14d) and **VictoriaLogs** (365d), and SNMP polled by
the same collector and remote-written to **VictoriaMetrics** — instead of a
promtail + syslog-gateway + snmp_exporter trio, each with its own config
language and failure modes.

**Why this priority**: Flat log lines force every consumer to regex the message
body, which is brittle and was already the root of two defects (RFC5424-only
parsing, and unbounded `app` label cardinality from guessing Cisco's TAG field).
One collector also matches the pilot design the operator already proved against
this fleet, so Convergence stops being a second, divergent architecture.

**Independent Test**: On a Docker install, point a Cisco switch and pfSense at
the collector's syslog port; log lines appear in **both** Loki and VictoriaLogs
with `device_name`/`severity`/`appname` as fields (not regex-extracted), and
`interface_status` / `interface_octets_in_bytes_total` arrive in VictoriaMetrics
with `device_name` + `interface_name` labels and no `ifIndex`/`ifName`.

**Acceptance Scenarios**:

1. **Given** a device sending vendor-default RFC3164 syslog, **When** the
   collector receives it, **Then** the log is stored with structured attributes
   (facility, severity, hostname, appname, message) and no message-body regex is
   needed to identify it.
2. **Given** the log pipeline is running, **When** a line is ingested, **Then** it
   is queryable in **both** Loki and VictoriaLogs.
3. **Given** OTel SNMP receivers replace snmp_exporter, **When** metrics arrive,
   **Then** existing alert rules and dashboards continue to work unchanged
   (`job="device_snmp"`, `device_name`, `interface_name` preserved).
4. **Given** the SNMP cutover, **When** interface metrics arrive, **Then**
   `interface_admin_status` is present so administratively-shut is
   distinguishable from link-failed.
5. **Given** the collector is the only syslog receiver, **When** cutover
   completes, **Then** the syslog-gateway (T141) and promtail device-syslog job
   are retired, and label cardinality from Cisco mnemonics is bounded.
6. **Given** a parse failure, **When** it occurs, **Then** the line is still
   ingested (`on_error: send`) and the failure remains countable — never a silent
   drop (FR-035).

**Detail**: [`otel-convergence.md`](./otel-convergence.md) · tasks T145–T156.

---

### Edge Cases

- Home-api unreachable: degraded banners, no uncaught exceptions.
- Risk exists but mesh down: setup reports clear error; does not delete member units.
- UniFi API key invalid: Wi‑Fi panel shows adapter error; other Overview KPIs still load.
- Docker resource constrained: minimal profile without Loki/Grafana still runs.
- Operator has non-standard investigator name: if it matches network-guardian profile skills, reuse rather than force rename (document policy).
- Investigation policy file missing: alert-receiver MUST fail safe to T0 (no multi-tool auto) and log a clear warning.
- Policy reload mid-flight: in-flight T2 may complete; new alerts use new policy within documented cache TTL (≤60s) or on SIGHUP.
- Nautobot/NetBox unreachable during wizard: clear error; allow fallback to manual inventory without wiping existing targets.
- snmp_exporter module-level lookups invalid for auth-split format: templates MUST use per-metric lookups for ifDescr/ifName.
- Empty ifDescr on some interfaces: recording rules SHOULD fall back to ifName; dashboards must not show blank legends when either is present.
- Apply with partial failure (Prom reload fails): report error; leave previous managed section intact when possible.
- Devices emit BSD syslog (RFC3164) while the log receiver only parses RFC5424: receiver MUST NOT silently discard the stream; the shipped receiver path MUST accept vendor-default syslog format (front-end reformat or an rfc3164-capable receiver) rather than requiring device reconfiguration.
- Security board with no log source: Prometheus-backed panels MUST still render; log panels MUST be identifiable as "source not deployed", not "network healthy".
- Quiet agent units (mesh/members idle beyond the log retention window): empty log panels are expected; boards MUST still select on `job`/`unit` labels so data reappears without dashboard edits.

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
- **FR-021**: Telemetry setup MUST support inventory entry via **manual** device list and via **Nautobot** (NetBox SHOULD when env present).
- **FR-022**: Inventory MUST record name, IP, vendor/template, and role for each SNMP target; secrets (community) MUST stay in env (`SNMP_COMMUNITY`), never in committed yaml.
- **FR-023**: System MUST provide vendor SNMP module templates for **Cisco** and **pfSense** (generic IF-MIB fallback allowed).
- **FR-024**: Apply MUST generate/update Prometheus scrape config and snmp_exporter config **idempotently** (managed section markers).
- **FR-025**: Interface metrics MUST expose human names (`ifDescr` and/or `ifName`; recording rules produce `interface_*` with `interface_name` for dashboards).
- **FR-026**: Setup MUST emit device-side config guidance for SNMP and syslog destination (Convergence host:port) without auto-pushing config in v1.
- **FR-027**: Grafana MUST provision a curated Convergence dashboard folder consisting of **three** primary boards — **Network** (`convergence-network`: site health, WAN, named campus interfaces, Wi‑Fi, edge), **Security** (`convergence-security`: posture, firing alerts, edge/guest access, syslog/auth), **NetClaw** (`convergence-netclaw`: token/cost by provider, T0/T1/T2 investigations, gateway/mesh logs); document host port **:3300**.
- **FR-028**: Alert rules for device/WAN MUST include interface identity in annotations where applicable and MUST honor investigation-policy labels (`investigate`).
- **FR-029**: Installer/catalog component for device SNMP MUST invoke or document the telemetry setup/apply path (not docs-only).
- **FR-030**: Ported pilot / single-subject boards MUST NOT be provisioned; they are retained unloaded under `grafana/provisioning/dashboards/legacy/` with a README pointing at the active suite.
- **FR-031**: Every panel on a provisioned board MUST be backed by a collector installable from this repo (Docker profile or K3s component). No provisioned panel may depend on the pilot `k3s-observability-stack`.
- **FR-032**: Each provisioned board MUST document its data dependencies (which collector/scrape/log source populates which section) so an unpopulated panel is attributable to "not deployed" rather than "healthy".
- **FR-033**: The **Security** board MUST render its Prometheus-backed posture (firing/critical alerts with `investigate` label, edge reachability, wireless/guest access) independently of log availability; log-backed sections MAY be empty until a log source is ingesting.
- **FR-034**: Log panels MUST select streams by stable labels (`job`, `unit`, `device_name`, `service`) rather than message-content regex.
- **FR-035**: The device/agent log receiver MUST ingest vendor-default syslog (RFC3164/BSD) as shipped — via a reformatting front-end or an rfc3164-capable receiver — and MUST surface parse-failure volume rather than dropping silently.
- **FR-036**: Device telemetry ingest MUST be a single **OpenTelemetry Collector** (syslog + SNMP), per [`otel-convergence.md`](./otel-convergence.md).
- **FR-037**: Syslog MUST be parsed into structured attributes at ingest (facility, severity, hostname, appname, message); consumers MUST NOT need message-body regex to identify a log's source or type.
- **FR-038**: Logs MUST be dual-exported to **Loki** (interactive retention) and **VictoriaLogs** (long-term retention).
- **FR-039**: SNMP metrics MUST be collected by the collector and remote-written to **VictoriaMetrics**; Prometheus remains the alerting engine and keeps its scrape-based collectors.
- **FR-040**: The SNMP cutover MUST preserve existing selectors (`job="device_snmp"`, `instance`, `device_name`, `interface_name`, `role`, `vendor`) via resource attributes, so no dashboard or alert rule changes are required.
- **FR-041**: Interface metrics MUST include `interface_admin_status` (ifAdminStatus) so administratively-shut is distinguishable from link-failed.
- **FR-042**: Promoted log labels MUST be a bounded, explicitly listed set (e.g. `device_name`, `site`, `service.name`, `severity`). Vendor message identifiers (e.g. Cisco mnemonics) MUST NOT become labels.

### Key Entities

- **Risk**: iN2N risk identity (`N2N_RISK_NAME`), Border, members.
- **Guardian member**: Scoped claw running home investigation skills.
- **Home site**: Logical site id (e.g. `home`) with thresholds and adapter bindings.
- **Home event**: Investigation diary row (status, root_cause, notes, feedback, rag id).
- **Adapter binding**: firewall | wireless | sot type + connection env refs.
- **Investigation policy**: Versioned rules mapping alerts → tier (T0/T1/T2) + budgets + degrade.
- **Investigation tier**: Observe / summarize / multi-tool investigate / human-gated deep work.
- **Device inventory**: List of SNMP targets (name, IP, vendor/template, role) under `device_telemetry.snmp`.
- **Vendor template**: snmp_exporter module pack (Cisco / pfSense / generic) with name lookups.
- **Telemetry apply**: Render + managed-section write + profile enable + reload pipeline.

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
- **SC-010**: From empty targets + wizard with ≥2 Cisco switches, apply → Prometheus has `device_snmp` up and `interface_status` (or `ifOperStatus`) with non-empty interface name labels within 5 minutes.
- **SC-011**: Nautobot mode lists devices and writes the selected set into `convergence.yaml` without manual IP typing.
- **SC-012**: Grafana folder Convergence shows the **Network** board campus switching section with named interfaces (not ifIndex-only legends) for lab switches (**:3300**).
- **SC-013**: Generated checklist includes site-specific syslog host:port and SNMP community env name (not a committed secret).
- **SC-014**: Grafana folder Convergence provisions exactly three boards (Network, Security, NetClaw); the `legacy/` directory is present and unloaded.
- **SC-015**: With device-snmp + UniFi + blackbox + agent metrics installed, every panel on Network and NetClaw returns a non-empty series (or an explicitly documented "requires X" note); Security's Prometheus panels return data with no log source deployed.
- **SC-016**: With a Cisco or pfSense device sending vendor-default syslog to the Convergence receiver, log lines are queryable within 5 minutes with `device_name` and `app` labels, and receiver parse-failure count for that stream is zero.
- **SC-017**: A single device syslog line is queryable in **both** Loki and VictoriaLogs, with severity and appname available as structured fields rather than regex extractions.
- **SC-018**: After the SNMP cutover, the provisioned boards and the full alert pack evaluate with zero query changes, and `interface_status` label sets contain `device_name` + `interface_name` with no `ifIndex`/`ifName`/`ifDescr`.
- **SC-019**: `interface_admin_status` is present for every polled interface, and total Loki stream count for `job=device-syslog` stays bounded as Cisco emits new mnemonics.

## Assumptions

- Host NetClaw (OpenClaw/Hermes) remains the default agent runtime; Docker agent profile is optional greenfield only.
- Pilot k3s-observability-stack continues to run until Home deploy packages reach parity; dual-run is allowed during migration.
- UniFi Integration API + unifi-exporter remain the first wireless implementation.
- Channel AI / radio Optimize remains human UI MoP (no auto-apply requirement in 067).
- Selective auto-investigation (not “every alert”) is an acceptable and preferred product posture for sustainable Agentic NOC.
- Local small models may serve T1 / interactive light / offline fallback; capable models (cloud or larger local) remain appropriate for T2 when allowlisted.
- Docker is the primary greenfield apply path for Phase 10; K3s uses existing components plus rendered config later.
- Nautobot is the primary SoT seed path; NetBox shares the same inventory field shape when configured.

## Out of Scope (v1)

- Additional wireless vendors beyond UniFi (stubs/contracts only).
- Auto radio mutation APIs.
- Replacing Grafana operator dashboards as the primary HOME surface (curated boards remain optional operator tools).
- Multi-tenant SaaS control plane.
- Full GUI CRUD for investigation policy (file + optional CLI sufficient for Phase 9).
- Full GUI inventory editor in HUD (CLI/wizard sufficient for Phase 10).
- Auto-push of SNMP/syslog configuration onto devices via MCP (checklist + optional verify only).
- Full NetFlow / AI-box / VPS dashboard suite and pilot PVC/TSDB migration.
- One OpenClaw member process per MCP tool.
- Mandating a specific local 9B model as the sole T2 brain.
