# Implementation Plan: MCP Config Reconciliation

**Branch**: `075-mcp-config-reconciliation` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/075-mcp-config-reconciliation/spec.md`
**Research**: [research.md](./research.md) — read this first; it corrects three spec claims

## Summary

Make NetClaw's existing reconciliation machinery enforcing, and fix the drift it already reports
into the void. The goal, per the maintainer's clarification, is that **all 89 registered integrations
are genuinely obtainable by someone installing their own risk** — no live-gateway work, no running
agent required.

The approach is deliberately small: **extend two existing verifiers rather than build a third**. Both
already encode domain knowledge from prior features (047, 049) and already compose via `importlib`.
The work is (1) add non-zero exits, (2) declare 8 missing mapping rules, (3) repair 3 malformed
registrations, (4) add a portability check, (5) correct 9 documentation counts, (6) add one thin
orchestrator, (7) wire CI.

Phase 0 research materially reduced the scope: the "19 servers with no installer coverage" turned out
to be 8 missing declarations against catalog components that already exist, not 19 install functions
to write. The genuine user-facing breakage is 3 Nautobot registrations hardcoded to `/home/ubuntu`.

## Technical Context

**Language/Version**: Python 3.10+ (all `scripts/*.py`), Bash (CI wiring, catalog is a Bash array)
**Primary Dependencies**: None — Python standard library only, per the convention every existing
script in `scripts/` states in its docstring. No pytest, no third-party YAML/JSON libraries.
**Storage**: N/A — all state is existing repository files; this feature adds no datastore
**Testing**: Fixture-based exit-code assertions. Copy real `config/openclaw.json`, `catalog.sh`,
`README.md` into a temp directory, mutate to introduce one defect, assert non-zero exit and that the
message names the offending item. Driven from a shell script; no test framework dependency.
**Target Platform**: Linux; must run in a bare CI container with no NetClaw agent installed (FR-029,
SC-013)
**Project Type**: Repository tooling / CI checks — not an MCP server, not a skill
**Performance Goals**: Full reconciliation under 5 seconds so it is cheap enough to run pre-push.
Current verifiers each complete in well under 1 second over 89 entries and 199 skills.
**Constraints**: No running agent. No network. No new third-party dependencies. Must not break the
existing callers of either verifier that today rely on exit 0 — hence a `--warn-only` escape hatch.
**Scale/Scope**: 89 registered integrations, 60 external, 59 vendored directories, 199 skills, 88
catalog entries, 88 install functions. Four registration surfaces to reconcile.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | Applies | Assessment |
|---|---|---|
| I — Safety-First Operations | No | No device interaction |
| II — Read-Before-Write | Partially | The verifiers are read-only; the remediation edits config and docs. Baseline is git itself |
| III — ITSM-Gated Changes | No | Repository tooling, not a production change |
| IV — Immutable Audit Trail | Yes | Session GAIT-logged as normal |
| V — MCP-Native Integration | N/A | Adds no capability, so nothing to expose as MCP (FR-027) |
| VI — Multi-Vendor Neutrality | N/A | No vendor logic |
| VII — Skill Modularity | N/A | No skills added |
| VIII — Verify After Every Change | **Yes — central** | This feature *is* verification infrastructure. Its own tests assert the verify step works |
| IX — Security by Default | Yes | Read-only checks; no new privileges. `register-all-mcps.py`'s DefenseClaw path is reused unchanged, not extended |
| X — Observability | Partially | Reconciliation result is the observable output. HUD update not applicable — no new integration |
| XI — Full-Stack Artifact Coherence | **Yes — central** | This feature is partly the *enforcement mechanism* for XI. Its own compliance is limited: no new capability, so most touchpoints are N/A. `README.md`/`SOUL.md` are updated (count corrections, FR-020) |
| XII — Documentation-as-Code | Yes | The add-an-integration procedure (FR-023) is the deliverable doc, updated in this PR |
| XIII — Credential Safety | Yes | No credentials touched. Portability check must not print credential-bearing env values in failure messages |
| XIV — Human-in-the-Loop | No | No external communication |
| XV — Backwards Compatibility | **Yes — risk** | Adding non-zero exits changes the contract of two scripts other callers may invoke. Mitigated by `--warn-only` and by auditing callers (T-series task) |
| XVI — Spec-Driven Development | Yes | Spec ratified, clarifications resolved, this plan precedes implementation |
| XVII — Milestone Documentation | Yes | R0 completion is a milestone; blog post drafted at the end |

**Gate result: PASS.** No violations requiring justification. One tracked risk (XV) with a stated
mitigation.

**Note on XI**: this feature deliberately does *not* add catalog entries, install functions, HUD
nodes, or `.env.example` variables, because FR-027 forbids adding capability. Its coherence
obligation is limited to the documentation surfaces it corrects.

## Project Structure

### Documentation (this feature)

```text
specs/075-mcp-config-reconciliation/
├── spec.md              # Ratified, clarifications resolved
├── plan.md              # This file
├── research.md          # Phase 0 — corrects three spec claims
├── data-model.md        # Phase 1 — integration state model
├── quickstart.md        # Phase 1 — the add-an-integration procedure (FR-023)
├── contracts/
│   └── reconcile-cli.md # Phase 1 — exit codes and output contract
├── checklists/
│   └── requirements.md  # Spec quality checklist (PASS)
└── tasks.md             # Phase 2 — /speckit.tasks, not created here
```

### Source Code (repository root)

```text
scripts/
├── reconcile-mcp.py              # NEW — thin orchestrator, single entry point (FR-009)
├── verify-inventory-counts.py    # EXTEND — non-zero exit, unlocatable-claim = failure
├── verify-catalog-coverage.py    # EXTEND — 8 mapping declarations, non-zero exit
├── check-mcp-portability.py      # NEW — machine-specific path detection (FR-003..FR-006)
├── trace-skill.py                # NEW — skill → integration → state chain (FR-025, FR-026)
├── normalize-mcp-cwd.py          # UNCHANGED — reused; its behaviour is why the Nautobot fix works
├── register-all-mcps.py          # UNCHANGED — its discovery logic is reused by reconcile-mcp.py
└── lib/
    ├── catalog.sh                # UNCHANGED — 88 entries already sufficient
    └── install-steps.sh          # UNCHANGED — 88 functions already sufficient

config/openclaw.json              # EDIT — repair 3 Nautobot entries, verify cml-mcp
README.md                         # EDIT — correct 6 count claims
SOUL.md                           # EDIT — correct 3 count claims
docs/ADDING-AN-MCP.md             # NEW — the one procedure R1–R24 will follow (FR-023)
docs/COVERAGE-ROADMAP.md          # EDIT — mark R0 done, correct the R0 premise note

.github/workflows/                # EDIT/NEW — CI hard-fail wiring (FR-010)
tests/reconcile/                  # NEW — fixture harness (SC-002)
    ├── run-tests.sh
    └── fixtures/
```

**Structure Decision**: Repository tooling lives in `scripts/`, matching all existing verifiers.
Four small single-purpose scripts plus one orchestrator, rather than one large script — mirroring the
existing separation and keeping each independently runnable. Tests live under `tests/reconcile/`
because the repo has no Python test convention for `scripts/` and introducing pytest for CI tooling
would violate the stdlib-only constraint.

## Implementation ordering — this matters

**Fix the drift before turning on enforcement.** Both verifiers currently report real failures. If
non-zero exits land first, CI goes red on `main` immediately and every subsequent commit is blocked
by pre-existing debt. Research R5 flagged this explicitly.

```
Stage 1  Declare the 8 mapping rules            → catalog coverage check reaches clean
Stage 2  Repair 3 Nautobot entries; verify cml  → portability baseline clean
Stage 3  Correct 9 documentation counts         → count check reaches clean
Stage 4  Add portability + state-completeness checks, with their own fixes
Stage 5  Add non-zero exits + --warn-only       → enforcement becomes real, on a clean tree
Stage 6  Add orchestrator + CI wiring           → single entry point, hard-fail
Stage 7  Add trace-skill, the procedure doc, roadmap update
```

Stages 1–3 are each independently verifiable by re-running the existing verifier and watching one
`FAIL` become clean. Stage 5 is the point of no return and must be last among the enforcement work.

## Key design decisions

**One orchestrator, not one merged script.** `verify-catalog-coverage.py` already imports
`verify-inventory-counts.py` via `importlib.util`, so composition is the established direction.
Merging would risk the grouping rules and external-integration rationale that features 047 and 049
established.

**Portability check keys on home directories, not absoluteness.** `/usr/bin/python3` is portable;
`/home/ubuntu/netclaw/...` is not. Banning all absolute paths would flag legitimate system
interpreters and push people toward suppressions (research R6).

**Unexplained vendored directories fail loudly.** Today, forgetting to add a name to
`EXTERNAL_INTEGRATIONS` causes silent undercounting. Inverting this so it fails naming the directory
is the single change that stops the list rotting (research R8).

**The host/sandbox `cwd` conflict is recorded, not solved.** One of four Ring-1 blockers; solving one
does not produce a working cutover, and it does not affect the stated goal because a fresh install
gets a correct `cwd` for its own machine (research R7, FR-007's escape clause).

## Complexity Tracking

> No Constitution Check violations require justification.

| Item | Note |
|---|---|
| Four new scripts rather than one | Matches existing `scripts/` convention of small single-purpose verifiers; each independently runnable, orchestrator provides the single entry point FR-009 requires |
| `--warn-only` flag | Required by Principle XV — two scripts' exit contracts change, and callers may exist. Audited as a task rather than assumed |

## Phase 2 preview

`/speckit.tasks` will generate the dependency-ordered task list. Expected shape: stages 1–3 are
independent and parallelizable; stage 5 blocks on all of 1–4; stage 6 blocks on 5; stage 7 is
independent of 5–6 and can run in parallel with them.
