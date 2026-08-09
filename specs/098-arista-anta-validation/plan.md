# Implementation Plan: Arista ANTA — structured network-state validation

**Branch**: `098-arista-anta-validation` | **Date**: 2026-08-05 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/098-arista-anta-validation/spec.md`
**Roadmap**: R25, created by [R24's triage](../097-open-territory-triage/TRIAGE.md)

## Summary

Add the **assertion layer** NetClaw lacks: run ANTA's declarative network-state tests against Arista
EOS devices over eAPI and return structured pass / fail / skipped / error verdicts.

Two constraints shape everything, and both were measured before this plan was written:

1. **ANTA's catalogue is large.** Exposing one tool per test would repeat Catalyst Center's 12.9×
   ceiling breach. Shape is **dispatcher + discovery** (the 087 pattern).
2. **ANTA moves `cryptography` 46.0.5 → 50.0.0** on a system-interpreter install, and four installed
   distributions depend on it — including NetClaw's own federation TLS stack — none with an upper
   bound. It runs from a **dedicated virtualenv** (the 076/083 pattern).

## Technical Context

**Language/Version**: Python 3.10+ (ANTA requires ≥3.10)
**Primary Dependencies**: `anta` 1.9.0 (**Apache-2.0, Copyright 2022 Arista Networks** — licence-
identical to NetClaw), plus its tree: `asyncssh`, `cvprac`, `pydantic-extra-types`, `PySocks`, and a
`cryptography` bump. MCP layer uses the repo-standard `mcp`/`fastmcp` in the venv
**Storage**: None. Stateless — a run is executed and returned, nothing persisted
**Testing**: Live against `clab-mandible-veos1` (vEOS-lab 4.36.1F, eAPI at `172.20.20.4:443`), plus
stdlib-only assertions that run without a device so CI stays useful (spec 075 SC-013)
**Target Platform**: Linux
**Project Type**: MCP integration — **built** thin server over an adopted Apache-2.0 framework
**Performance Goals**: Manifest ≤ 5,000 tokens, counted
**Constraints**: Read-only; no configuration path may exist; no credential in output; must not move
any package another component depends on
**Scale/Scope**: One server, a dispatcher plus discovery tools, one skill

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| **I. Safety-First (NON-NEGOTIABLE)** | No device change | **PASS** — ANTA tests only; FR-003 forbids adding any configuration path |
| **II. Read-Before-Write** | Read-only | **PASS** |
| **III. ITSM-Gated Changes** | Writes need CR gating | **N/A** — there are no writes |
| **VI. Multi-Vendor Neutrality** | No lock-in | **PASS with a stated limit** — ANTA is EOS-specific and the spec says so rather than implying multivendor validation |
| **VIII. Verify After Every Change** | Verdicts must be trustworthy | **PASS** — this feature *is* that principle as a capability; FR-004/005/006 stop absence being read as health |
| **IX. Security by Default** | Least privilege, no secret leakage | **PASS** — FR-009: credentials from environment, never in arguments or output |
| **XI. Full-Stack Artifact Coherence** | Every touchpoint | **PLANNED** — config, catalog, install step, profile, skill, `.env.example`, TOOLS.md, README/SOUL counts, HUD's two entries |
| **XV. Backwards Compatibility** | Must not disturb existing components | **PASS by design** — the venv exists precisely so `cryptography` does not move (FR-011, SC-008) |
| **XVI. Spec-Driven Development** | Full cycle | **PASS** — specify → clarify → plan → tasks → analyze → implement |

### Post-Phase-1 re-check

No new violations. The venv keeps the dependency surface isolated, so spec 077's pinning rules apply
within `requirements.txt` but cannot reach other components.

## Project Structure

### Documentation (this feature)

```text
specs/098-arista-anta-validation/
├── spec.md · checklists/requirements.md
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/tools.md
└── tasks.md
```

### Source Code (repository root)

```text
mcp-servers/anta-mcp/
├── server.py           # dispatcher + discovery tools
├── runner.py           # ANTA invocation, result normalisation
├── verdict.py          # the four-outcome model and its chokepoint
├── requirements.txt    # anta + mcp, bounded pins (spec 077)
└── README.md
mcp-servers/anta-mcp/.venv/          # dedicated, created at install (gitignored)
workspace/skills/anta-validation/SKILL.md
tests/anta/run-tests.sh              # stdlib assertions + live tests that skip without a device
```

**Structure Decision**: A thin NetClaw-authored server over the upstream framework, in its own
virtualenv. ANTA is a **library**, not an MCP server, so there is nothing to adopt directly — the
question is only how much NetClaw writes around it, and the answer is: as little as possible beyond
the verdict discipline and the manifest shape.

## The two design centres

### 1. The four-outcome verdict, enforced at a chokepoint

`pass` / `fail` / `skipped` / `error` are distinct, and the failure modes this repo keeps
rediscovering all come from collapsing them:

- **skipped ≠ pass** — 40 tests where 30 skipped is not "75% healthy" (spec 091's inert Suricata).
- **error ≠ fail** — an unreachable device is not a broken one (spec 094's BMC, spec 095's empty Mist
  org).
- **empty selection ≠ pass** — no tests run is not a healthy device (spec 092's `0 datasets`).

`verdict.py` raises if a summary would merge them, following `envelope.emit()` (091),
`verdict.emit()` (094) and `_envelope()` (087). **Documentation is not the control.**

### 2. Manifest shape

Discovery (`anta_list_tests`, `anta_describe_test`) must work **without a device** (FR-008), so an
operator can explore before connecting — and so the manifest stays small by describing tests on
demand instead of enumerating them as tools.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **A dedicated virtualenv** — a second interpreter to maintain | ANTA's install moves `cryptography` 46.0.5 → **50.0.0**; `Authlib`, `pygnmi`, `service-identity` and `sshsig` all depend on it with **no upper bound**, and NetClaw's federation TLS stack (spec 060) is built on it | A system install was measured by dry-run first, exactly as spec 076's cryptography incident teaches. Pinning `cryptography` down instead would fight ANTA's own resolver on every install |
