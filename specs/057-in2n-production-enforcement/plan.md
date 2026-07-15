# Implementation Plan: iN2N Production-Mode Enforcement & Durable Runtime

**Branch**: `057-in2n-production-enforcement` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/057-in2n-production-enforcement/spec.md`

## Summary

Make `N2N_RISK_MODE=production` actually enforce three controls and make the risk runtime durable, without touching the eN2N core or the iN2N wire protocol. Concretely: (1) a **posture aggregator** the Border reports truthfully (`testing` / `production — enforced` / `production — degraded (<controls>)`), computed from live probes of the three controls; (2) **OpenShell sandbox** wrapping every member launch in production, fail-closed; (3) **DefenseClaw** guarding member model I/O + a component scan before a member runs, fail-closed; (4) **GAIT-git** immutable emit for federation events, complementing the existing SQLite audit; (5) **durable runtime** — a service generator that emits one systemd `--user` unit for the mesh daemon (formalizing the hotfix) and one per always-on member, plus single-owner-vs-cold-start reconciliation; (6) **fault isolation** in health/heartbeat (daemon vs member vs backend). All controls are verified by a **synchronous preflight before each delegation** (authoritative fail-closed) plus a **background poll** that keeps displayed posture fresh.

Technical approach: extend the existing `bgp/federation/*` package (new `posture.py`, `controls.py`, `gait.py`; edits to `service.py`, `risk.py`, `audit.py`, `gateway.py`) and the `scripts/in2n-*` tooling (new `scripts/in2n-services.py` generator + `scripts/lib` installer wiring). Reuse the already-installed `defenseclaw` and `openshell` CLIs. No new third-party packages.

## Technical Context

**Language/Version**: Python 3.10+ (daemon + federation package + tooling), Bash (installer/service generator glue), Node.js 18+/ES2022 (HUD posture render only)
**Primary Dependencies**: Existing `bgp-daemon-v2.py` + `bgp/federation/*` (service, risk, router, internal_channel, audit, gateway, manager, invocation, tasks); the installed `defenseclaw` CLI (`~/.local/bin/defenseclaw`, `docs/DEFENSECLAW.md`); the installed `openshell` CLI (`~/.local/bin/openshell`); `git` (GAIT trail); systemd `--user`. Python stdlib only (`asyncio`, `subprocess`, `sqlite3`, `json`, `pathlib`, `shutil`, `time`). No new third-party packages.
**Storage**: Extend existing SQLite `~/.openclaw/n2n/federation.db` (member health fields, per-member service binding); new **GAIT git repo** at `~/.openclaw/n2n/gait/` (unbounded, FR-012a); systemd units under `~/.config/systemd/user/`; env under `~/.openclaw/mesh.systemd.env` + per-member env files (existing pattern).
**Testing**: `pytest` under `tests/n2n/` (matches 056's 89-test suite: 44 eN2N regression frozen + 45 iN2N); posture/control/service-generator/GAIT unit tests stub the external CLIs (as `test_member_delegation.py` stubs `gateway.run_agent_turn`).
**Target Platform**: Linux + systemd `--user` (primary; matches `openclaw-gateway.service`). Non-systemd hosts: documented graceful fallback (posture reports the durability control degraded; members still cold-start).
**Project Type**: Single project — Python federation daemon/package + Bash tooling + a Three.js HUD panel. No web/mobile split.
**Performance Goals**: Recovery after daemon/member kill < 60s with no operator action (SC-005). Control preflight adds < ~1s to a delegation (three local CLI probes, cached briefly). Sandbox cold-start latency budgeted into the cold-start timeout (edge case).
**Constraints**: Fail-closed on containment controls; no wire-protocol change (SC-007); eN2N core frozen (052/053 + 056 regression suites must stay green); hub-and-spoke only (no member-to-member). Credentials stay in per-member `.env` (Constitution XIII).
**Scale/Scope**: One risk = 1 Border + up to ~27 members (4 always-on, 23 cold) on the live system; the design is per-risk and does not assume more.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Relevance | Status |
|-----------|-----------|--------|
| **IV. Immutable Audit Trail** | This spec **wires GAIT-git** (US4/FR-010..012a), the exact gap called out. Complements the working SQLite audit; corrections are new entries; never rewritten. | ✅ Directly satisfied (this is a fix toward IV) |
| **IX. Security by Default** | OpenShell sandbox = least-privilege containment; DefenseClaw guard + component scan; fail-closed default. | ✅ Strengthened |
| **X. Observability First-Class** | Posture + fault-isolated health surfaced via status tool, heartbeat, and a **HUD** posture panel. | ✅ HUD update included (Phase 1) |
| **XI. Full-Stack Artifact Coherence (NON-NEGOTIABLE)** | New tooling (`scripts/in2n-services.py`) + installer step (`scripts/lib/catalog.sh` + `install-steps.sh`), README/TOOLS/SOUL, `.env.example` (new `N2N_*` vars), HUD, SKILL docs, `verify-catalog-coverage.py`. | ✅ Enumerated in Project Structure; enforced at implement/PR |
| **XIII. Credential Safety** | No new hardcoded secrets; per-member `.env` least-privilege preserved; new env vars documented in `.env.example` with no values. | ✅ |
| **XV. Backwards Compatibility** | eN2N core frozen; iN2N wire unchanged; `testing` mode unchanged (fast, guards off); 89-test 056 suite + 44 eN2N regression must pass (SC-007). Degraded policy is additive. | ✅ Regression-gated |
| **XVI. Spec-Driven Development** | specify → clarify (done) → **plan (this)** → tasks → implement. | ✅ On track |
| **V. MCP-Native** | Posture exposed via the existing `n2n-mcp` FastMCP server (a new/extended status tool), not a bespoke channel. | ✅ |

**No violations.** Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/057-in2n-production-enforcement/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (internal control interfaces + MCP tool + service unit template)
│   ├── posture.md
│   ├── controls.md
│   ├── gait-events.md
│   └── durable-services.md
├── checklists/
│   └── requirements.md  # (exists, passing)
└── tasks.md             # /speckit.tasks (NOT created here)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/
├── bgp-daemon-v2.py                    # EDIT: start background control poller; expose posture on status routes
└── bgp/federation/
    ├── posture.py                      # NEW: aggregate the 3 controls → RiskPosture (testing/enforced/degraded)
    ├── controls.py                     # NEW: EnforcementControl probes (openshell_available, defenseclaw_available, gait_recording) + brief cache
    ├── gait.py                         # NEW: GAIT git emit (init repo, commit federation event, read-only trail)
    ├── audit.py                        # EDIT: replace _gait_ref stub → call gait.emit(); keep SQLite authoritative
    ├── service.py                      # EDIT: preflight gate in route_and_delegate/delegate_to_member (FR-003a/019);
    │                                   #       fault-isolated health (daemon/member/backend, FR-017); single-owner vs cold-start
    ├── risk.py                         # EDIT: member 'managed_by' (service|cold) binding; posture-aware launch
    ├── gateway.py                      # EDIT: production → wrap member run under `openshell` + route model I/O via DefenseClaw; fail-closed
    └── invocation.py                   # (reuse existing DefenseClaw tool-inspect; no wire change)

scripts/
├── in2n-services.py                    # NEW: generator — emit netclaw-mesh.service + netclaw-member-<id>.service (repeatable, FR-015)
├── in2n-member.py                      # EDIT: honor production (sandbox/guard already applied at gateway); idle-exit unchanged
├── in2n-profiles.py                    # EDIT: mark always-on members as service-managed vs cold
└── lib/
    ├── catalog.sh                      # EDIT: catalog entry for the durable-runtime/enforcement component
    └── install-steps.sh                # EDIT: component_install_<id>() — generate + enable services, verify CLIs

ui/netclaw-visual/                      # EDIT: HUD posture panel (enforced/degraded + missing controls; member service state)

tests/n2n/
├── test_posture.py                     # NEW: posture matrix (each control missing → degraded naming it; all → enforced)
├── test_controls_failclosed.py         # NEW: sandbox/guard unavailable → delegation refused (FR-005/009/019)
├── test_gait_emit.py                   # NEW: event → git commit + SQLite row; immutable; unbounded
├── test_durable_services.py            # NEW: generator emits valid units; single-owner vs cold-start no double-launch
├── test_fault_isolation.py            # NEW: daemon/member/backend distinct causes (FR-017/018)
└── (existing 056 + eN2N suites)        # REGRESSION: must stay green (SC-007)

docs/, README.md, TOOLS.md, SOUL.md, .env.example   # EDIT: Constitution XI coherence
```

**Structure Decision**: Single-project extension of the existing `bgp/federation` package plus `scripts/` tooling — the same shape 056 used. New logic is isolated in three new modules (`posture.py`, `controls.py`, `gait.py`) so the enforcement/audit/durability concerns are individually testable and the edits to existing files (`service.py`, `gateway.py`, `audit.py`, `risk.py`) stay small and reviewable. No wire/protocol files are touched, keeping the eN2N freeze and SC-007 intact.

## Complexity Tracking

> No Constitution violations — table intentionally empty.
