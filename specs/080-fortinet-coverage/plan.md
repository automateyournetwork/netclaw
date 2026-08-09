# Implementation Plan: Fortinet Coverage (FortiOS / FortiManager / FortiAnalyzer)

**Branch**: `080-fortinet-coverage` | **Date**: 2026-08-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/080-fortinet-coverage/spec.md`
**Research**: [research.md](./research.md) — **read R1 and R6 first**
**Roadmap**: R3 — largest single-vendor absence

## Summary

`workspace/skills/fortimanager-ops/SKILL.md` is `user-invocable: true`, declares three environment
variables, and names a server that is **not vendored, not registered, and not installable**. NetClaw
advertises Fortinet coverage it does not have. That is worse than a gap: an agent routes a firewall-policy
question to the skill and discovers the truth inside an operator's real question.

Build `mcp-servers/fortinet-mcp/` — a NetClaw-authored server covering three planes: **FortiManager**
(intent), **FortiGate/FortiOS** (observed state), **FortiAnalyzer** (observed traffic). Back-fill
`fortimanager-ops` against it and add `fortigate-ops` and `fortianalyzer-ops`.

Four community servers were evaluated and all rejected for adoption (R1) on four independent grounds:
none emits the `plane` field FR-005 requires; their manifests are 69–204 tools each against a 5,000-token
ceiling; only one enforces read-only; none has any concept of a change record. They are used as **endpoint
reference under MIT**, exactly as spec 076 used `sydasif/nornir-mcp-server`.

**Read-only first.** US1/US2/US4 are read paths; US3 (gated writes) is last and independently deferrable.

## Technical Context

**Language/Version**: Python 3.10+, system interpreter. Unlike spec 076 this needs **no dedicated venv** —
two pure-HTTP packages move nothing shared (R4).

**Primary Dependencies**: `mcp>=1.2.0,<2` and `httpx>=0.27.0,<1`. Two packages, identical to spec 078's
`cisco-psirt-mcp`. The `mcp` upper bound is load-bearing: 2.0.0 removed `mcp.server.fastmcp`, which this
server imports (spec 077). No Fortinet SDK — `pyFMG`, `fortiosapi` and `fortigate-api` were all evaluated
and rejected (R4).

**Storage**: None. Stateless proxy to three appliance APIs. Change baselines (US3) write under a
path-sandboxed directory, following spec 076.

**Testing**: Contract tests over pure functions — `plane` envelope, scope validation, gate refusals,
manifest token count — all runnable with **no appliance**. Integration tests against the lab. Harness
follows spec 075's `tests/reconcile/run-tests.sh`: bash + stdlib, no new framework.

**Target Platform**: Linux (WSL2 confirmed). Lab is **three Hyper-V VMs** — containerlab was dropped once
the FortiGate was deployed on Hyper-V (research R6). The live device runs **FortiOS v8.0.0** at
`192.168.2.130`, newer than any community server targets.

**Project Type**: New vendored MCP server + 3 skills + installer catalog entry + lab topology.

**Performance Goals**: None specified. Analyzer log queries must paginate rather than return unbounded
history (FR-018c).

**Constraints**: Read-only default (FR-019). Manifest **≤ 5,000 tokens**, measured (FR-026). Every
response carries `plane` + scope (FR-005/FR-009). TLS verification on by default (FR-030). No credential
in any committed file (FR-028). Must not regress spec 076's FortiOS CLI reach (FR-031).

**Scale/Scope**: 3 planes, ~20 tools, 3 skills, 4 user stories, 51 FRs, 23 SCs.

**Licence clocks — binding on task order**: FortiGate permanent; FortiManager and FortiAnalyzer **15 days
from first boot**. The lab is staged so trial VMs boot only at verification time.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Applies | Assessment |
|---|---|---|
| **I — Safety-First (NON-NEGOTIABLE)** | **Yes — central** | Read-only default (FR-019); package install treated as production change (FR-021); unreachable device reports non-response rather than substituting manager intent (US2 AS3, FR-007) — the plane discipline *is* the safety property here |
| **II — Read-Before-Write** | **Yes** | FR-021: baseline captured, revision identified as rollback context before any install |
| **III — ITSM-Gated Changes** | **Yes — explicitly, not by inheritance** | FR-020/FR-020a: human approval **and** an approved CR are distinct gates, each refusal naming the missing one. Logic ported from spec 076's `tools/change.py` (R7) — the module that exists *because* `/speckit.analyze` caught this exact conflation. Unclassified device ⇒ production |
| **IV — Immutable Audit Trail** | **Yes** | FR-023: every operation, read or write, permitted or refused, GAIT-logged |
| **V — MCP-Native** | **Yes** | FastMCP, stdio, proper JSON-RPC lifecycle |
| **VI — Multi-Vendor Neutrality** | **Yes** | Vendor-specific logic stays in this vendor server. FR-031 keeps the boundary against spec 076's generic CLI driver explicit in both directions |
| **VII — Skill Modularity** | **Yes — drove a clarification** | One skill per plane (FR-002a). A single skill spanning manager + device + analyzer would breach this; three appliances with three credential sets are three functions |
| **VIII — Verify After Every Change** | **Yes** | FR-021: state verified after install, against the captured baseline |
| **IX — Security by Default** | **Yes** | Read-only default; token auth; TLS verify on with explicit opt-out (FR-030); least-privilege admin profile documented |
| **X — Observability** | **Yes** | Analyzer plane is observability. HUD node + annotation required by XI |
| **XI — Artifact Coherence (NON-NEGOTIABLE)** | **Yes — every touchpoint** | FR-037: registration, catalog, profiles, install fn, **both** HUD entries, README/SOUL counts **and** a SOUL capability section, 3× SKILL.md, `.env.example`, `TOOLS.md`, server README. Gated by `reconcile-mcp.py` (FR-038) |
| XII — Documentation-as-Code | Yes | Server README + 3 SKILL.md, same PR |
| **XIII — Credential Safety** | **Yes** | Env only; `.env.example` names without values; missing var reported **by name** (FR-029); no token in output, log or GAIT record |
| XIV — Human-in-the-Loop | **Yes** | FR-020's approval gate is precisely this |
| **XV — Backwards Compatibility** | Yes — low risk | Two pure-HTTP packages, no shared-tree movement (R4). Must not regress 076's FortiOS CLI reach (FR-031) |
| XVI — Spec-Driven Development | Yes | Spec ratified, 6 clarifications resolved (one of which reversed an earlier cut), plan precedes implementation |
| XVII — Milestone Documentation | Yes | Blog post at completion |

**Gate result: PASS.** No violations requiring justification.

**Post-Phase-1 re-check (2026-08-01): still PASS**, with three principles strengthened by the design
rather than merely satisfied:

- **Principle I / FR-005** — `envelope.py` as a chokepoint converts plane attribution from a convention
  into a structural property. A future tool cannot omit it.
- **Principle III** — `contracts/mcp-tools.md` gives the two gates *distinct outcome values*
  (`refused_no_approval`, `refused_no_change_record`). A caller cannot conflate them even by accident,
  which is a stronger guarantee than prose.
- **Principle VII** — the three-skill split survived design: each plane maps to one tool module, one
  credential set, one skill.

One risk raised by Phase 1 and tracked rather than resolved: the 20-tool surface is a **design target**,
not a measurement. If the measured manifest exceeds 5,000 tokens the surface shrinks — the ceiling wins.

**Principle III is the one to watch.** Spec 076 recorded it as "inherited" and `/speckit.analyze` found
zero task coverage behind the claim. This plan therefore names the gates as separate requirements with
separate refusal messages, and Stage 8 carries explicit tasks for each. An "inherited" claim here would be
the same failure repeated with the same words.

## Project Structure

### Documentation (this feature)

```text
specs/080-fortinet-coverage/
├── spec.md              # Ratified; 6 clarifications, incl. one reversal
├── plan.md              # This file
├── research.md          # Phase 0 — R1 (build-vs-adopt), R6 (lab feasibility)
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1 — operator lab build + credential setup
├── contracts/
│   └── mcp-tools.md     # Phase 1 — tool surface, response envelope, error semantics
├── checklists/
│   └── requirements.md  # Spec quality (PASS, revalidated after restore)
└── tasks.md             # Phase 2 — /speckit.tasks
```

### Source Code (repository root)

```text
mcp-servers/fortinet-mcp/
├── server.py                # FastMCP entry point, stdio; tool registration
├── transport/
│   ├── jsonrpc.py           # ONE client for FortiManager AND FortiAnalyzer (R2 — same /jsonrpc)
│   └── rest.py              # FortiOS REST, httpx bearer token (R3)
├── envelope.py              # plane + scope stamping (FR-005/FR-009) — every response passes through
├── planes/
│   ├── manager.py           # ADOMs, packages, rules, objects, revisions   (FR-010–014)
│   ├── device.py            # status, interfaces, routes, VPN, HA, VDOM    (FR-015–018)
│   └── analyzer.py          # log query, bounded window, offset pagination (FR-018a–c)
├── gates.py                 # human approval + ServiceNow CR — ported from 076 (R7)
├── credentials.py           # per-plane env vars; missing reported by name  (FR-028/029)
├── requirements.txt         # mcp>=1.2.0,<2 · httpx>=0.27.0,<1
└── README.md

workspace/skills/
├── fortimanager-ops/        # BACK-FILLED — keeps its name (6 documents reference it)
├── fortigate-ops/           # NEW — device plane
└── fortianalyzer-ops/       # NEW — analyzer plane

labs/fortinet-r3/
├── README.md                # 3 Hyper-V VMs; image acquisition (operator action; nothing committed)
├── topology.md              # addressing, vSwitch choice, allowaccess, the Default Switch trap
└── verify-lab.sh            # reachability + version + licence preflight, no credentials embedded

config/openclaw.json         # + fortinet-mcp, repo-relative paths
scripts/lib/catalog.sh       # + one entry, + PROFILE_SECURITY / PROFILE_MULTIVENDOR
scripts/lib/install-steps.sh # + component_install_fortinet()
ui/netclaw-visual/server.js  # + node list entry AND annotation map entry (TWO edits)
tests/fortinet/              # envelope, gates, manifest-size contract tests (no appliance)
```

**Structure Decision**: a vendored server under `mcp-servers/`, matching every existing NetClaw server.
The internal split follows the spec's own axes — one module per plane, with `envelope.py` as a
**chokepoint** every response passes through. That placement is deliberate: FR-005 is only a guarantee if
attribution cannot be forgotten in a new tool, and a chokepoint makes omission structurally impossible
rather than a review item.

`transport/` splits by *protocol*, not by plane, because manager and analyzer share one (R2).

## Implementation ordering

**Envelope before tools; reads before writes; permanent licence before trial clocks.**

```
Stage 1  Server skeleton, deps, credentials, envelope.py + contract tests   (FR-005/009/028/029)
Stage 2  JSON-RPC + REST transports, auth, TLS posture, session expiry      (R2/R3/R8/R9, FR-030)
Stage 3  FortiGate lab documented + preflight; licence activated, token cut (R6)
Stage 4  Device plane: status, interfaces, routes, VPN phase1/2, HA, VDOM   (US2: FR-015–018)
Stage 5  Manifest measurement against the 5,000-token ceiling               (FR-025–027)
Stage 6  Artifact coherence: registration, catalog, installer, HUD, docs    (FR-037–041)
Stage 7  ── boot FMG + FAZ (15-day clocks start) ──
         Manager plane + analyzer plane                    (US1: FR-010–014, US4: FR-018a–c)
Stage 8  Gated writes: approval + CR, baseline, verify, rollback            (US3: FR-019–024)
Stage 9  Skills ×3, migration-staging regeneration, verification table      (FR-002/002a/003, FR-035/036)
```

**Stage 1 before everything.** `envelope.py` is the feature's core guarantee. Building tools first and
adding attribution later produces exactly the tools that forget it.

**Stage 3 before Stage 7 is the licence-clock rule** and the single most consequential ordering decision
here. FortiGate's licence is permanent, so all transport, envelope and device work happens against it with
no time pressure. FortiManager and FortiAnalyzer are 15 days *from first boot* — booting them at Stage 1
would spend the verification window on implementation. They boot when the server is ready to be verified,
not before.

**Stage 5 before Stage 6** so registration never lands a manifest that breaches the ceiling.

**Stage 8 last and independently deferrable.** If gated writes slip, Stages 1–7 still deliver three planes
of read-only Fortinet reach — which is the roadmap's headline value.

## Key design decisions

**Build, don't adopt** (R1). Four independent disqualifications; see research. All four candidates remain
valuable as MIT endpoint reference.

**One transport for two planes** (R2). FortiManager and FortiAnalyzer both speak `/jsonrpc` with the same
envelope and the same `exec /sys/login/user` login. Treating them as two integrations would have duplicated
the client. This was not obvious from the roadmap, which lists them as separate line items.

**Parameterised tools, not enumerated ones** (R5). `paoloamato2` proves five generic tools can reach 1,536
endpoints; its error is shipping those *plus* 204 typed ones. NetClaw takes the insight without the
inflation, targeting ~20 tools.

**`envelope.py` as a chokepoint, not a convention.** FR-005 asked for a structural guarantee. A helper that
tools *may* call is a convention; a wrapper they *must* pass through is a guarantee.

**Port the gates, don't import them** (R7). Spec 076's `change.py` is the right logic in the wrong process
— separate server, separate deps, bound to its own `Device` type. Copy with attribution. A shared package
across MCP servers is real future work and is deliberately not invented here.

**Token auth only in v1** (R9). Username/password adds session lifecycle for no capability gain.

**Absence of logs is not absence of traffic** (FR-018b). The analyzer plane's whole value is answering "is
this rule dead?", and the wrong answer is cheap to give. Same error class as 078's "no advisories ≠ not
vulnerable" and 079's "no probes ≠ outage".

## Complexity Tracking

> No Constitution Check violations require justification.

| Item | Note |
|---|---|
| Three skills rather than one | Ratified clarification. Three appliances, three credential sets, three functions — Principle VII |
| Gate logic duplicated from spec 076 | Separate processes with separate dependency sets. Sharing needs a common package NetClaw lacks; noted as future work rather than invented mid-feature |
| Lab is one hypervisor, three VMs | Simplified 2026-08-01. containerlab has exactly one Fortinet kind (`fortinet_fortigate`, verified against the binary) and could never have hosted the other two planes. With the FortiGate on Hyper-V too, containerlab and the `vrnetlab` build step both disappear |
| A hard token ceiling on a manifest | Unusual for NetClaw, but the alternative is a 200-tool manifest taxing every unrelated conversation |

## Phase 2 preview

`/speckit.tasks` will produce the dependency-ordered list. Expected shape: Stage 1 blocks all; Stage 2
blocks 4 and 7; Stage 3 blocks 4; Stage 5 blocks 6; **Stage 7 must not start before Stage 6 completes**
(licence clock); Stage 8 depends on 2, 7 and the gate port; Stage 9 depends on 4 and 7.

Five items carried from research as **tasks, not assumptions** (research.md, "Still open"):

1. Measure the real manifest token count once the surface exists.
2. Confirm FortiAnalyzer-VM ships a Hyper-V image (only trial *terms* were verified, not the hypervisor
   matrix).
3. Confirm the FortiGate 3-policy cap does not block install verification — a package of >3 rules pushed to
   a capped device may fail, which would be a finding about the lab rather than the server.
4. **Activate the FortiGate evaluation licence** — currently `Invalid`. Gates device-plane *verification*
   only; Stages 1, 2 and 5 proceed without it.
5. **Re-verify community endpoint knowledge against FortiOS v8.0.0** — every reference repo targets 7.6.6
   or older.

**The licence is the only external dependency on the critical path**, and it blocks strictly less than it
appears: the envelope, gates, transports and manifest measurement are all device-free by design.
