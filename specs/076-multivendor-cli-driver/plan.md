# Implementation Plan: Generic Multivendor CLI Driver

**Branch**: `076-multivendor-cli-driver` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/076-multivendor-cli-driver/spec.md`
**Research**: [research.md](./research.md) — **read R7 first**; it invalidates an earlier conclusion
**Stacked on**: R0 / spec 075 (unmerged). Inherits `docs/ADDING-AN-MCP.md` and `scripts/reconcile-mcp.py`

## Summary

Give NetClaw a general "connect to this device and ask it something" capability. Today all four
device-facing servers are platform-bound (`pyATS` Cisco, `junos-mcp` Juniper, `gnmi-mcp` telemetry
only, `radkit-mcp` cloud-relayed), so roughly ninety platforms — MikroTik, VyOS, SONiC, SR Linux,
Extreme, Huawei, Dell, EdgeOS — are unreachable.

Build a new MCP server on `nornir` + `napalm` + `netmiko`, deliberately porting the safety model from
the archived `sydasif/nornir-mcp-server` (prefix allowlist, destructive-first-token denylist, chaining
prevention, Pydantic validation, path sandboxing) while replacing its inventory and credential layers
with NetClaw-native ones.

**Read-only first.** US1–US4 (reach, normalization, fleet fan-out, inventory/credentials) are P1/P2;
gated configuration change is P3, so the capability is useful long before it is dangerous.

## Technical Context

**Language/Version**: Python — **interpreter choice is a live decision, not a default** (see R7).
Target `/usr/bin/python3` (3.14.4) as the venv base, since that is what NetClaw's servers actually run
under. `nornir-netmiko` declares `Requires-Python >=3.8,<4.0`, so 3.14 is nominally in range, but wheel
availability on 3.14 must be confirmed at implementation rather than assumed.

**Primary Dependencies**: `nornir` 3.5.0, `napalm` 5.2.0, `netmiko` (>=4,<5 per `nornir-netmiko`),
`nornir-netmiko` 1.0.1, `nornir_napalm` 0.5.0, `nornir-netbox` 0.3.0, `nornir-nautobot` 4.3.0,
`pynautobot` 3.1.1, `jdiff` 1.0.2 (change verification, R9), plus the scrapli family pulled
transitively by NAPALM 5.x (R8). ~21 packages. **All into a dedicated virtualenv** (FR-030a).

**Storage**: No database. A generated inventory cache on disk (regenerable, credential-free); an
operator-authored inventory file (never written by the server); change baselines under a path-sandboxed
directory.

**Testing**: Contract tests for command-filter and inventory-source logic, runnable with no device
(pure functions over inputs). Integration tests against containerlab-hosted SR Linux / SONiC / VyOS
(R4). Harness style follows spec 075's `tests/reconcile/run-tests.sh` — bash + stdlib, no new test
framework in the shared environment.

**Target Platform**: Linux. Must install on a host with the split toolchain described in R7 without
silently landing packages where the server cannot import them.

**Project Type**: New MCP server (`mcp-servers/`) + skills (`workspace/skills/`) + installer catalog
entry. First NetClaw feature to require a dedicated venv by specification.

**Performance Goals**: A fleet query of N devices materially faster than N sequential queries (SC-005).
Default 10 concurrent workers and a 30s per-device timeout, both operator-overridable (R11).

**Constraints**: Read-only by default (FR-022). No credential on disk outside a gitignored `.env`
(FR-019). Must not perturb the system `cryptography` used by the NCFED X.509 stack (FR-030c). Must not
regress the 18 pyATS skills or the Junos skill (FR-032).

**Scale/Scope**: ≥90 platform families driver-supported (≥5 live-verified), 3 inventory sources, 44 FRs, 17 SCs, 5 user stories.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Applies | Assessment |
|---|---|---|
| **I — Safety-First (NON-NEGOTIABLE)** | **Yes — central** | Read-only default (FR-022); server-side command filtering (FR-029); unreachable devices halt rather than return assumed state (FR-004); writes require approval (FR-025). This is the principle the entire safety design serves |
| **II — Read-Before-Write** | **Yes** | FR-024 requires a captured baseline before any modification |
| **III — ITSM-Gated Changes** | **Yes** | **Corrected after `/speckit.analyze`**, which found this had zero task coverage. It had been marked "Partially — inherited", but that was an assertion rather than an implementation: FR-025's human approval and a ServiceNow Change Request are distinct gates. Now FR-025a/b/c and T070a–T070d, via the existing `servicenow-mcp` and `servicenow-change-workflow`. Unclassified devices are treated as production |
| **IV — Immutable Audit Trail** | **Yes** | FR-028: every device interaction GAIT-logged |
| **V — MCP-Native** | **Yes** | Delivered as an MCP server with proper JSON-RPC lifecycle; stdio transport declared |
| **VI — Multi-Vendor Neutrality** | **Yes — this feature *is* the principle** | Vendor-neutral where the operation is generic (NAPALM getters); vendor-specific logic stays in vendor servers. FR-009/FR-010 keep the boundary explicit |
| **VII — Skill Modularity** | Yes | Three focused skills (FR-031): normalized facts, safe raw command, fleet fan-out. Must not duplicate pyATS skills |
| **VIII — Verify After Every Change** | **Yes** | FR-026 compares actual against expected state; `jdiff` adopted for this (R9) rather than hand-rolled |
| **IX — Security by Default** | **Yes** | Least privilege; read-only preferred per MCP Server Standards; no elevated permissions requested |
| X — Observability | Partially | Per-device results and per-source attribution (FR-017c, FR-018a). HUD node required by XI |
| **XI — Artifact Coherence (NON-NEGOTIABLE)** | **Yes — every touchpoint** | Genuinely adds capability, so unlike R0 all artifacts apply: README, `catalog.sh`, `install-steps.sh`, HUD, `SOUL.md`, 3× `SKILL.md`, `.env.example`, `TOOLS.md`, `config/openclaw.json`, server README. Enforced by R0's gate |
| XII — Documentation-as-Code | Yes | Server README (tools, env vars, transport, install) plus 3 SKILL.md, same PR |
| **XIII — Credential Safety** | **Yes — clarified** | Vault preferred, env fallback, never in any inventory source (FR-018/019, FR-017d) |
| XIV — Human-in-the-Loop | Yes | Writes gated (FR-025); no external communications otherwise |
| **XV — Backwards Compatibility** | **Yes — highest risk** | 21 new packages. R7 found a split toolchain carrying two `cryptography` versions. Dedicated venv (FR-030a) is the mitigation; FR-030c asserts no perturbation |
| XVI — Spec-Driven Development | Yes | Spec ratified, 4 clarifications resolved, this plan precedes implementation |
| XVII — Milestone Documentation | Yes | Blog post at completion |

**Gate result: PASS** — after correction. `/speckit.analyze` found Principle III (a MUST) with zero task
coverage, which would have been a CRITICAL violation at implementation time. Now covered. Two tracked
high-risk areas remain (Principles I and XV), both with mitigations reflected in the task ordering.

**Note on Principle VI**: this is the first feature where multi-vendor neutrality is the deliverable
rather than a constraint. The routing rule (FR-009–FR-012) is what stops "neutral" degrading into
"ambiguous".

## Project Structure

### Documentation (this feature)

```text
specs/076-multivendor-cli-driver/
├── spec.md              # Ratified, 4 clarifications resolved
├── plan.md              # This file
├── research.md          # Phase 0 — R7 is critical, read first
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1 — operator onboarding for all 3 inventory sources
├── contracts/
│   └── mcp-tools.md     # Phase 1 — tool surface and error semantics
├── checklists/
│   └── requirements.md  # Spec quality (PASS)
└── tasks.md             # Phase 2 — /speckit.tasks
```

### Source Code (repository root)

```text
mcp-servers/multivendor-cli-mcp/
├── server.py                  # MCP entry point (FastMCP, stdio)
├── inventory/
│   ├── sources.py             # 3-source resolution + attribution (FR-017, FR-017c)
│   ├── live_sot.py            # nornir-netbox / nornir-nautobot / Infrahub
│   ├── generated.py           # render + refresh cache; never touches operator files
│   └── operator.py            # read-only consumer of operator-authored YAML
├── credentials.py             # Vault preferred, env fallback, path reported (FR-018/018a)
├── policy/
│   ├── filter.py              # allowlist / denylist / chaining prevention (FR-023, FR-029)
│   └── platform_deny.py       # per-platform destructive syntax (R6)
├── tools/
│   ├── facts.py               # NAPALM getters + explicit gap reporting (FR-006/007)
│   ├── raw.py                 # netmiko raw command execution (FR-002)
│   ├── fleet.py               # concurrent fan-out, per-device results (FR-013–016)
│   └── change.py              # baseline → approve → apply → verify → rollback (P3)
├── routing.py                 # platform-first rule; refuses Cisco/Junos writes (FR-009–011)
├── requirements.txt           # pinned
└── README.md

workspace/skills/
├── multivendor-device-query/  # normalized facts + the routing rule (FR-012, FR-031)
├── multivendor-raw-cli/       # safe raw command execution
└── multivendor-fleet-ops/     # fan-out across a group

scripts/lib/catalog.sh         # + one entry (no generic-driver id exists today)
scripts/lib/install-steps.sh   # + component_install_multivendor_cli() — creates the venv
config/openclaw.json           # + registration, interpreter resolved at install (FR-030b)
tests/multivendor/             # filter + inventory contract tests; containerlab integration
```

**Structure Decision**: a new vendored server under `mcp-servers/`, matching every existing NetClaw
server. Internal packages split along the axes the spec's requirement groups already imply — inventory,
credentials, policy, tools, routing — so each requirement group maps to one module and the command
filter is independently testable without a device.

## Implementation ordering

**Safety and isolation before reach; reach before writes.**

```
Stage 1  Dedicated venv + dependency install + cryptography assertion    (FR-030a/b/c, R7)
Stage 2  Command filter + per-platform denylist, unit-tested no-device    (FR-022/023/029, R6)
Stage 3  Inventory: 3 sources + attribution; credentials Vault/env        (FR-017*, FR-018*, FR-019)
Stage 4  Raw command execution — first real device reach                  (US1: FR-001–005)
Stage 5  NAPALM normalized facts + explicit gap reporting                 (US2: FR-006–008)
Stage 6  Routing rule + refusals                                         (FR-009–012)
Stage 7  Fleet fan-out, concurrency bound, timeouts                       (US3: FR-013–016)
Stage 8  Registration, catalog, install fn, skills, XI artifacts          (FR-030–032)
Stage 9  Gated change: baseline → approve → apply → jdiff verify → rollback (US5, P3)
```

**Stage 2 before Stage 4 is deliberate.** The filter must exist and be tested before anything can
execute a command against a real device. Building reach first and adding safety later would create a
window in which the server can run arbitrary commands — precisely what Principle I forbids.

**Stage 1 first** because R7 showed the host toolchain is split; nothing else can be trusted until the
venv is proven to contain what the server will actually import.

**Stage 9 last** and independently deferrable — if it slips, Stages 1–8 still deliver ~90 platforms of
read-only reach.

## Key design decisions

**Build, don't adopt** (R1). Candidate A is archived and reloads `config.yaml` per call; candidate B has
no filtering at all. Port A's safety model under MIT; treat B's concurrency surface as design reference
only.

**Netmiko *and* scrapli, not either/or** (R8). NAPALM 5.x is scrapli-based, so scrapli arrives
regardless. Netmiko stays for raw-CLI platform reach; scrapli serves NAPALM's getters. The earlier
"reject scrapli" framing was wrong.

**Dedicated venv, explicit interpreter** (R7). Create with `/usr/bin/python3 -m venv`, install with
`<venv>/bin/python -m pip` — never bare `pip3`, which on this host targets a stranded 3.13 environment
the server cannot import from.

**`jdiff` for change verification** (R9), not hand-rolled comparison. FR-026 needs structured
actual-versus-expected diffing, and `jdiff` arrives in the tree anyway.

**TTP output is second-class.** Available for platforms lacking a NAPALM getter, but must be labelled
template-parsed and never presented as a normalized fact — FR-007 requires reporting the gap, not
papering over it.

**Generated and operator-authored inventories are different artifacts.** Generated files are caches and
are overwritten; operator files are never touched. Conflating them destroys operator work.

## Complexity Tracking

> No Constitution Check violations require justification.

| Item | Note |
|---|---|
| Dedicated venv (first spec to mandate one) | Required by Principle XV given R7's split toolchain and two `cryptography` versions. Precedent exists (`mcp-servers/mcp-nvd/.venv`, R10) |
| Three inventory sources rather than one | Ratified clarification. Each serves a real operator configuration; collapsing to one excludes either no-SoT or air-gapped operators |
| Both netmiko and scrapli present | Not a choice — NAPALM 5.x pulls scrapli (R8). Documented so it is not mistaken for redundancy |
| Server refuses work it is technically capable of (FR-010) | Deliberate. A single write path per platform is what keeps Principles I and VIII enforceable |

## Phase 2 preview

`/speckit.tasks` will generate the dependency-ordered task list. Expected shape: Stage 1 blocks
everything; Stage 2 blocks Stages 4, 5, 7 and 9; Stage 3 blocks Stage 4 onward; Stage 6 depends on 4
and 5; Stage 8 can proceed in parallel from Stage 4 onward; Stage 9 depends on 2, 3, 4 and 8.

Open item to resolve as a task rather than an assumption: **confirm wheel availability for the full tree
on Python 3.14.4.** `nornir-netmiko` allows `<4.0`, but 3.14 is recent and a missing wheel would force
the venv onto an older interpreter — changing FR-030a's base, though not the decision.
