# Feature Specification: iN2N Production-Mode Enforcement & Durable Runtime

> **Channel trust superseded by [feature 060](../060-claw-cert-security/spec.md):** the cleartext/pinned channel behavior described here is upgraded to TLS + certificate authentication (eN2N mutual auth, iN2N hub attestation) by claw certification. This spec is unchanged for historical accuracy.


**Feature Branch**: `057-in2n-production-enforcement`
**Created**: 2026-07-13
**Status**: Draft
**Input**: User description: "Make N2N_RISK_MODE=production actually enforce (OpenShell sandbox, DefenseClaw fail-closed, GAIT git trail) and make the risk runtime durable (services + watchdog); the Border must report an honest production vs degraded posture."

## Context & Background

Spec 056 delivered iN2N — a "risk" of NetClaws (one Border + focused members), live-proven with real infrastructure calls. It shipped a `N2N_RISK_MODE` setting (`testing` | `production`), but during the live migration we verified on the running system that **production mode is a flag that does not enforce anything**, and the runtime is **not durable**:

1. **OpenShell (NVIDIA sandbox)** is installed and connected, but member claws run as **plain host processes** — not sandboxed.
2. **DefenseClaw (Cisco)** does **not** guard model input/output — when its local proxy was down, calls silently fell back to a direct provider, bypassing guardrails.
3. **GAIT-proper** (the git-based immutable audit trail, Constitution IV) is **not wired** — the emit hook is a stub. A SQLite audit trail does exist and centralizes at the Border, but the git trail does not.
4. The mesh daemon and member processes were **shell-detached, not services**, so they died on session/terminal churn and never came back — repeatedly taking the whole federation layer down and breaking the Border's operator heartbeat while the gateway (a real service) stayed up. (Hotfixed during 056 by making the mesh daemon a durable service; this spec formalizes and completes that.)

This feature makes production mode **real and honest** (enforce, or clearly declare degraded — never a false claim) and makes the risk **resilient** (survives reboots and session churn). It changes no wire protocol.

## Clarifications

### Session 2026-07-13

- Q: How is each enforcement control (sandbox / model-guard / GAIT) verified so posture and fail-closed stay accurate? → A: **Preflight + background poll** — a synchronous preflight gates every delegation (fail-closed at the moment it matters), and a background poll keeps the displayed posture (HUD/heartbeat/status) fresh between delegations.
- Q: How are always-on members made durable? → A: **One durable service per always-on member** (mirrors `netclaw-mesh.service`) — independent auto-restart, per-member status feeds fault isolation, and single-owner lifecycle (a member with a running unit is skipped by the cold-start path, so no double-launch).
- Q: What retention/rotation policy for the GAIT immutable git trail? → A: **Unbounded + git gc** — never rotate; rely on git's own packing/gc, manual archival only. Federation-event volume is low, and not rotating gives the cleanest immutability guarantee (history is never rewritten).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Honest production posture (Priority: P1)

An operator sets their risk to production. The Border reports a **truthful posture**: either **"production — enforced"** (all of sandboxing, model-guarding, and audit are actually active) or **"production — DEGRADED"** with the specific missing control(s) named. It **never** claims full production while a control is missing.

**Why this priority**: The single most important property. A false "production" claim is worse than an honest "degraded" — it's the trust foundation for everything else. It's also the MVP: even before every control is wired, the risk telling the truth about its own posture is immediately valuable.

**Independent Test**: With one enforcement control deliberately unavailable, ask the Border its posture; confirm it reports `production — degraded (<control> missing)`, not `production`. With all controls active, it reports `production — enforced`.

**Acceptance Scenarios**:

1. **Given** production mode with OpenShell, DefenseClaw, and GAIT all active, **When** the operator queries risk posture, **Then** it reports `production — enforced` and lists all three as active.
2. **Given** production mode with DefenseClaw unavailable, **When** the operator queries posture, **Then** it reports `production — DEGRADED` naming DefenseClaw, and this is surfaced in the operator heartbeat.
3. **Given** testing mode, **When** the operator queries posture, **Then** it reports `testing` (guards intentionally off) with no false production claim.

---

### User Story 2 - Members run kernel-confined (Priority: P1)

In production mode, every member claw executes **kernel-confined** — via host-level systemd sandboxing (see FR-004; OpenShell containers were evaluated and found unsuitable for live-infrastructure members). A member that cannot be confined does not run in production.

**Why this priority**: Confinement is the containment guarantee behind the least-privilege promise — a compromised member is contained (no privilege escalation, read-only system, the operator's master secrets hidden). Without it, "production" is hollow.

**Independent Test**: Stand up a member in production; confirm its process runs under the systemd confinement directives (observably: `NoNewPrivileges`, `ProtectSystem=strict`, master `.env` inaccessible), and that forcing the confinement mechanism unavailable prevents the member from running in production (fail-closed) while surfacing a degraded posture.

**Acceptance Scenarios**:

1. **Given** production mode, **When** a member is launched (hot or cold-started), **Then** its process runs kernel-confined (hardened systemd unit / transient `systemd-run` unit).
2. **Given** production mode and the confinement mechanism unavailable (no systemd user manager), **When** a member would launch, **Then** it does **not** run unconfined; the posture goes degraded and the operator is told why.
3. **Given** testing mode, **When** a member launches, **Then** it may run without confinement (fast iteration).

---

### User Story 3 - Model I/O guarded by DefenseClaw, fail-closed (Priority: P1)

In production mode, member and Border model calls are routed **through DefenseClaw guardrails**, and member skill/MCP sets are **scanned by DefenseClaw before they run**. If DefenseClaw (or its guard path) is unavailable, production **fails closed** — it does not silently bypass to an unguarded provider.

**Why this priority**: This is the guardrail that inspects prompts/completions and tool calls. The 056 live run proved the dangerous default (silent bypass to direct provider). Fail-closed is the correction.

**Independent Test**: In production, run a delegated task and confirm the model call traversed DefenseClaw (guard record present). Then make DefenseClaw unavailable and confirm the task is refused/degraded rather than run through an unguarded path.

**Acceptance Scenarios**:

1. **Given** production mode with DefenseClaw available, **When** a member executes a delegated task, **Then** the model I/O is guarded by DefenseClaw and the member's skills/MCPs were scanned first.
2. **Given** production mode with DefenseClaw unavailable, **When** a task would run, **Then** it is **not** executed through an unguarded provider — it fails closed with a clear reason, and posture goes degraded.
3. **Given** a component scan flags a member's skill/MCP, **When** that member would run in production, **Then** it is blocked and reported.

---

### User Story 4 - GAIT git audit trail for federation events (Priority: P2)

In production mode, every federation security event — delegation, enrollment, member removal, quarantine — is recorded to the **GAIT git-based immutable trail**, in addition to the existing SQLite audit. Production requires GAIT to be recording.

**Why this priority**: Constitution IV mandates an immutable audit trail. SQLite is queryable but mutable; GAIT-git is the immutable record. It complements (does not replace) the working SQLite audit, so it's P2 relative to containment/guarding.

**Independent Test**: In production, perform a delegation + an enrollment + a quarantine; confirm each appears as a GAIT git commit as well as a SQLite audit row. With GAIT unavailable, posture goes degraded.

**Acceptance Scenarios**:

1. **Given** production mode, **When** the Border delegates a task, enrolls, removes, or quarantines a member, **Then** the event is committed to the GAIT git trail (and the SQLite audit row still exists).
2. **Given** production mode and GAIT unavailable, **When** the operator queries posture, **Then** it reports degraded naming GAIT.
3. **Given** the GAIT trail, **When** an operator reviews it, **Then** the federation events are attributable and time-ordered.

---

### User Story 5 - Durable runtime: daemon + always-on members survive churn (Priority: P1)

The mesh daemon and the always-on member claws run as **durable services** that auto-start, auto-restart on failure, and survive session/terminal churn and reboots — the way the gateway already does. Standing up a risk registers these services repeatably (not a hand-made one-off).

**Why this priority**: In 056 the recurring outage was the federation layer silently dying while the gateway stayed up — breaking the operator heartbeat. A risk that isn't durably running isn't production. Co-equal P1 with the enforcement controls.

**Independent Test**: Kill the mesh daemon and an always-on member; confirm both are automatically restarted within a bounded time and federation recovers with no manual action. Simulate a session/terminal exit; confirm neither dies.

**Acceptance Scenarios**:

1. **Given** a running risk, **When** the mesh daemon process is killed, **Then** it is automatically restarted and federation recovers within a bounded window, with no operator action.
2. **Given** a running risk, **When** an always-on member process dies, **Then** it is automatically restarted (or reliably cold-started on the next route), and the Border reflects it returning to live.
3. **Given** the host reboots or the launching session/terminal exits, **When** the system comes back, **Then** the daemon and always-on members are running again.
4. **Given** a fresh risk is stood up, **When** the operator provisions it, **Then** the durable services are created repeatably by the tooling (not hand-authored).

---

### User Story 6 - Truthful health & fault isolation (Priority: P2)

The Border's health/status distinguishes **daemon-down** vs **member-down** vs **backend-unreachable**, so the operator heartbeat gives an accurate diagnosis instead of a misleading one.

**Why this priority**: In 056 the Border misdiagnosed a poll bug as a "member flap." Accurate fault isolation is what makes the heartbeat trustworthy, but it refines the other stories rather than enabling them.

**Independent Test**: Induce each fault class (daemon down; member down; member up but its backend unreachable) and confirm the Border's health reports the correct, distinct cause each time.

**Acceptance Scenarios**:

1. **Given** the daemon is down, **When** the heartbeat runs, **Then** it reports a daemon/federation-layer fault (not a member fault).
2. **Given** a member is down but the daemon is up, **When** the heartbeat runs, **Then** it reports that specific member down (and whether it will cold-start).
3. **Given** a member is up but its backend (e.g. a device/API) is unreachable, **When** a task runs, **Then** the fault is reported as a backend-reachability issue, not a federation fault.

---

### Edge Cases

- **Partial enforcement**: one control active, others not → posture degraded, naming exactly which are missing.
- **Control drops mid-operation** (e.g. DefenseClaw proxy dies while members are running) → the background poll flips the displayed posture to degraded promptly, and the very next delegation's preflight (FR-003a) refuses/degrades it per FR-019; no new task runs against the dropped control.
- **Sandbox overhead**: OpenShell adds startup latency to cold-started members → cold-start timeout accounts for sandbox spin-up so a sandboxed cold member isn't falsely marked unreachable.
- **Service vs cold-start overlap**: an always-on member managed by a service must not be double-launched by the cold-start path (single-owner of a member's lifecycle at a time).
- **Non-systemd hosts**: the durable-runtime mechanism degrades gracefully (documented) where the platform service manager differs.
- **GAIT repo growth**: the immutable trail grows unbounded by design (FR-012a) → git packing/gc keeps it compact; no automated rotation, so the never-rewritten guarantee is preserved. Archival, if ever needed, is manual and out-of-band.

## Requirements *(mandatory)*

### Functional Requirements

#### Honest posture (US1)

- **FR-001**: The system MUST expose a **risk posture** with distinct values: `testing`, `production — enforced`, `production — degraded`. The degraded value MUST name each missing control (sandbox / model-guard / audit).
- **FR-002**: In production mode the system MUST **never** report `enforced` unless OpenShell sandboxing, DefenseClaw guarding, and GAIT recording are all verified active.
- **FR-003**: The posture MUST be surfaced to the operator via the Border (status tool + the operator heartbeat + the HUD).
- **FR-003a**: Enforcement controls MUST be verified two ways: (a) a **synchronous preflight** immediately before every delegation that gates the task (this is the authoritative fail-closed check — a control that is unavailable at preflight blocks/degrades that task per FR-019), and (b) a **background health poll** that keeps the displayed posture (status tool, heartbeat, HUD) current between delegations. The displayed posture MAY briefly lag a control drop, but a delegation's own preflight MUST NOT rely on stale poll state.

#### Member sandbox / confinement (US2)

- **FR-004**: In production mode, every member claw MUST execute **confined**. The confinement mechanism is **host-level kernel sandboxing via systemd sandboxing directives** applied to the member's unit (and to on-demand members via a transient `systemd-run` unit): `NoNewPrivileges`, read-only system (`ProtectSystem=strict`), the operator's master secrets hidden (`InaccessiblePaths` on `~/.openclaw/.env`), private `/tmp`, and — on a native-Linux manager — syscall/namespace/address-family restrictions. *(Rationale: the OpenShell container was evaluated and rejected for live-infrastructure members — its sandboxes are empty, network-egress-denied containers with none of the member's tools; a member that must reach live devices/APIs cannot run in one without a custom image + per-member egress policy. Host-level confinement keeps the member's real home/tools/network while confining it. OpenShell remains available for isolated code execution but is not the member sandbox.)*
- **FR-005**: In production mode, a member that cannot be confined MUST NOT run (fail-closed); the failure MUST be reported and drive the degraded posture. (E.g. no systemd user manager → sandbox control unavailable → degraded.)
- **FR-006**: In testing mode, members MAY run without confinement.
- **FR-006a**: Where the systemd user manager cannot apply the capability/namespace directives (e.g. WSL2 → `218/CAPABILITIES`), the portable filesystem + no-new-privileges set is applied and the full kernel set is added automatically on managers that support it. Per-member filesystem isolation (hiding sibling member homes via `ProtectHome=tmpfs` + binds) is a defined tightening.

#### DefenseClaw guarding (US3)

- **FR-007**: In production mode, model input/output MUST be guarded by DefenseClaw. DefenseClaw guards model I/O via its **LLM guardrail proxy** (a Go proxy, default `:4000`, enabled by `defenseclaw setup guardrail` which patches OpenClaw to route the model through it) — every prompt/response is routed through it for inspection. This is NOT a per-call CLI command (there is **no** `defenseclaw tool inspect`; that was a latent bug in 056/early-057, corrected to `defenseclaw tool status` for the per-tool block-list gate). "model-guard available" therefore requires the `defenseclaw` CLI present AND the **guardrail proxy reachable**; a merely-installed CLI with the proxy down is NOT available (no false enforced — this is the correction for 056's silent bypass). The Border's own model turns are guarded because the OpenClaw gateway routes through the proxy; routing each member's model provider through the proxy is a defined tightening.
- **FR-008**: In production mode, a member's skill/MCP set MUST be scanned by DefenseClaw before the member runs; a flagged component blocks that member and is reported. The set scanned is the member's **scoped** skill/MCP list (from its registered scope/profile), evaluated at (cold-)start where that scope is known — not the full catalog.
- **FR-009**: In production mode, if DefenseClaw (or its guard path) is unavailable, model calls MUST **fail closed** — the system MUST NOT silently route to an unguarded provider. "Available" for the model-guard control means the `defenseclaw` guard is actually reachable AND `security.mode=defenseclaw` is in effect — a merely-installed CLI with guarding disabled MUST NOT be reported as enforced.

#### GAIT audit (US4)

- **FR-010**: In production mode, federation security events (delegation, enrollment, member removal, quarantine) MUST be recorded to the GAIT git immutable trail, in addition to the existing SQLite audit.
- **FR-011**: In production mode, if GAIT is not recording, the posture MUST report degraded naming GAIT.
- **FR-012**: The GAIT trail MUST be attributable (which claw/operator) and time-ordered, and MUST NOT be modifiable after commit (corrections are new entries).
- **FR-012a**: The GAIT trail is **unbounded** (never rotated); storage efficiency relies on git's own packing/gc, and any archival is a manual, out-of-band operation. No automated rotation is performed, preserving the guarantee that history is never rewritten.

#### Durable runtime (US5)

- **FR-013**: The mesh daemon MUST run as a durable service that auto-starts, auto-restarts on failure (bounded), and survives session/terminal churn and host reboot.
- **FR-014**: Each always-on member claw MUST run as its **own durable service** (one service per member, mirroring the mesh daemon's service), auto-restarting on failure. Single-owner lifecycle MUST hold: a member with a running service is NOT eligible for cold-start launch (no double-launch); a non-always-on member continues to cold-start on next route.
- **FR-015**: The durable services (the mesh daemon service and the per-member services) MUST be created **repeatably by the tooling/installer** (a generator), not hand-authored one-offs, and captured in the repo.
- **FR-016**: Recovery MUST require no operator action and complete within a bounded window after a fault.

#### Health & fault isolation (US6)

- **FR-017**: Health/status MUST distinguish and report **daemon-down**, **member-down**, and **backend-unreachable** as separate causes.
- **FR-018**: The operator heartbeat MUST use this fault isolation so its diagnosis matches the actual cause.

#### Degraded-operation policy (cross-cutting)

- **FR-019**: When production is degraded, the system MUST apply a **per-control policy** based on the nature of the missing control:
  - **Containment controls missing** (OpenShell sandbox OR DefenseClaw model-guard/component-scan) → **BLOCK delegations (fail-closed)**. No unsandboxed or unguarded execution is permitted; the delegation is refused with a clear reason.
  - **Audit control missing** (GAIT git trail) → **ALLOW delegations but loudly flag** every result as `audit-degraded` (execution is still sandboxed + guarded; only the immutable trail is missing), and surface it in posture + heartbeat + result.
  - The operator MAY override to **strict-all** (block on any missing control, including audit).
- **FR-020**: The blocked-vs-warned decision MUST be reflected in the posture and in each affected delegation's result (an operator always knows whether a result was refused, ran audit-degraded, or ran fully enforced).

#### Posture & security visibility (US1 cross-cutting)

- **FR-021**: The risk's posture (mode, state, per-control availability) and the claw's **LLM capability** (primary model + whether it is guardrail-routed) MUST be visible to the operator in the **HUD** and MUST be advertised in the **A2A capability card** (the federation inventory) so a federated peer — and members — understand the neighbouring claw's security posture and reasoning capability. No credentials are ever included; a Border advertises its own reasoning model and notes members run their own tiered models without exposing per-member topology.

### Key Entities

- **Risk Posture**: the enforced/degraded/testing state + which controls (sandbox, model-guard, audit) are active. Surfaced by the Border.
- **Enforcement Control**: a named production requirement (OpenShell sandbox, DefenseClaw guard, GAIT audit) with an availability/health state the posture aggregates.
- **Durable Service**: the run definition for the mesh daemon or an always-on member (auto-start/restart, survives churn) — generated and registered by tooling.
- **GAIT Federation Event**: an immutable git-committed audit record of a delegation/enrollment/removal/quarantine, complementing the SQLite audit row.
- **Health/Fault Report**: the Border's truthful status distinguishing daemon vs member vs backend faults.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With any one enforcement control unavailable, the Border reports `production — degraded` naming that control **100% of the time**, and never reports `enforced`.
- **SC-002**: In production, **100% of member executions** run kernel-confined (hardened systemd unit); a member that cannot be confined is refused 100% of the time.
- **SC-003**: In production, **100% of model calls** traverse DefenseClaw; when DefenseClaw is unavailable, **0%** of calls run through an unguarded provider (fail-closed).
- **SC-004**: In production, **100% of** delegations/enrollments/removals/quarantines appear in the GAIT git trail (as well as SQLite).
- **SC-005**: After the mesh daemon or an always-on member is killed, federation recovers with **no operator action** within a bounded window (target: under 60 seconds), and both survive a session/terminal exit and a host reboot. *(This is a systemd `Restart=always` behavior; it is verified by the live quickstart run — the authoritative SC-005 gate — not by a stubbed unit test.)*
- **SC-006**: For each induced fault class (daemon / member / backend), the operator heartbeat reports the **correct distinct cause** 100% of the time.
- **SC-007**: The eN2N mesh and iN2N wire protocol show **no regression** (056/052/053 suites still pass); the production controls add no change to the wire.
- **SC-008**: In production-degraded, delegations behave per the per-control policy 100% of the time: containment-control gap → refused; audit-only gap → runs but flagged `audit-degraded`; strict-all override → refused on any gap.

## Assumptions

- **Reuse, not reinvent**: builds on the 056 runtime (risk/router/internal_channel/service, the member scoped-home + Border-persona generators, the systemd `netclaw-mesh.service` hotfix as the starting point). Model-guard uses the installed **DefenseClaw** guardrail proxy (`defenseclaw setup guardrail` + `defenseclaw-gateway start`); component scan uses `defenseclaw skill scan`. **Sandbox uses host-level systemd confinement** (OpenShell containers were evaluated and found unsuitable for live-infrastructure members — see FR-004). The DefenseClaw sidecar must be running for model-guard to be enforced (a documented install/runtime step; if down, posture is honestly degraded).
- **Linux/systemd primary target**: durable runtime uses systemd user services (matching the existing gateway service). Other platforms degrade gracefully with a documented fallback.
- **DefenseClaw guard path**: production requires a reachable DefenseClaw guard (its proxy and/or CLI inspection); "guarding" means model I/O and component scans actually pass through it.
- **GAIT complements SQLite**: the SQLite audit (already centralized at the Border, `channel_kind=in2n`) stays; GAIT-git is added as the immutable trail, not a replacement.
- **Frozen boundaries**: no changes to the eN2N core (052/053) or the iN2N wire protocol; hub-and-spoke retained.

## Out of Scope

- **Member-to-member mesh** — settled decision; the single Border audit/policy/routing boundary is what makes centralized guardrails + auditing possible. iN2N stays hub-and-spoke; mesh remains eN2N Border-to-Border only.
- **Changing the eN2N protocol or the iN2N wire framing.**
- **Splitting N2N/NCFED into its own repository** — still deferred.
- **New security vendors** beyond the already-integrated DefenseClaw and OpenShell.
- **Non-Linux service managers** as a first-class target (documented graceful fallback only).
