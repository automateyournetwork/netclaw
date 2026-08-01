# Implementation Plan: Dependency-Pin Hazards

**Branch**: `077-dependency-pin-hazards` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)
**Roadmap**: R0a · **Builds on**: R0 / spec 075 (gate extended), R1 / spec 076 (where all hazards were found)

## Summary

NetClaw installs today and would fail tomorrow. Three classes of dependency breakage are invisible to
every existing check, and all three break only *new* installs — which is why none was noticed.

Repair 7 exposed servers, route 188 bare pip calls through one helper, fix 2 broken venv creations, and
extend R0's gate so none of it can silently return.

**Read the spec's PREMISE CORRECTION first.** `n2n-mcp` needs no migration — it imports
`mcp.server.fastmcp` like the other six, so it gets the same bounded pin plus removal of an unused
`fastmcp` declaration. The approved migration would not have fixed it.

## Technical Context

**Language**: Python 3.10+ (gate checks, stdlib only per repo convention), Bash (installer helper).
**Dependencies**: none new. The gate must not require a package index for its static checks.
**Testing**: extend `tests/reconcile/run-tests.sh` with fixture-based exit-code assertions. No framework.
**Constraints**: gate runs in CI with no credentials, no network, no agent. Must not regress 202 skills /
150 integrations. Hosts where `pip3` and `python3` agree must keep working.
**Scale**: 7 pin repairs, 188 call sites, 2 venv sites, ~90 servers scanned.

## Constitution Check

| Principle | Assessment |
|---|---|
| **IV — Audit trail** | GAIT's own venv is one of the two broken creations. Fixing it is Principle IV infrastructure, not housekeeping |
| **V — MCP-native** | The 7 repairs are what let these servers start at all |
| **XI — Artifact coherence** | Gate extension + `docs/ADDING-AN-MCP.md` pinning rule so R2–R24 inherit it. No capability added, so most touchpoints are N/A |
| **XII — Docs-as-code** | Pinning rule documented in the same change |
| **XV — Backwards compatibility** | **Central.** This feature exists because dependency drift broke compatibility silently |
| **XVI — SDD** | Spec ratified, 3 clarifications resolved (one premise corrected) |
| XVII — Milestone blog | **Waived by the maintainer for this item** |

**Gate: PASS.** No violations. Principle XV is the whole subject.

## Structure

```text
scripts/
├── lib/pip-helper.sh          # NEW — netclaw_pip_install(), single install path
├── lib/install-steps.sh       # EDIT — 188 bare calls routed through the helper; venv fix
├── gait-venv-setup.sh         # EDIT — virtualenv fallback where ensurepip is absent
├── check-dependency-pins.py   # NEW — static import scan, bare-pip scan, venv scan
└── reconcile-mcp.py           # EDIT — new "dependencies" surface

mcp-servers/{claroty,protocol,suzieq,nautobot-mcp-v2,uml,thousandeyes-mcp-community,n2n}-*/requirements.txt
docs/ADDING-AN-MCP.md          # EDIT — the pinning rule
tests/reconcile/run-tests.sh   # EDIT — contract tests for all three hazards
```

## Ordering — repair before enforce

```
1  Six pin repairs + verify each imports              (FR-001, FR-002)
2  n2n-mcp: bound mcp, delete unused fastmcp, verify federation  (FR-001a/b/c)
3  pip helper + route all 188 call sites               (FR-003/003a/003b)
4  venv fix in both places, GAIT included              (FR-004, FR-005)
5  check-dependency-pins.py — the three scans          (FR-006..FR-009, FR-012)
6  Wire into reconcile-mcp.py as a surface + CI        (FR-011)
7  Contract tests + ADDING-AN-MCP.md pinning rule
```

Same discipline as R0: **the gate goes on last**, because turning it on before the repairs land would
make CI red on `main` and block everything behind pre-existing debt.

## Key decisions

**One helper, not 188 edits** (clarified). The hazard is bare pip *on a split-toolchain host*; a helper
gives one place to fix. The 1 already-scoped call proves hand-writing works only when the author has just
been burned.

**Static scan, not a curated list** (clarified). Derived from source so it cannot rot the way
`EXTERNAL_INTEGRATIONS` did. Catches 7 of 7 here.

**Also flag unused declared dependencies** (FR-006c). `n2n-mcp`'s dead `fastmcp` pin is what produced this
feature's own misdiagnosis — worth catching mechanically.

**`virtualenv` for venv creation**, matching spec 076, with a clear failure naming the one-line remedy.

## Complexity Tracking

| Item | Note |
|---|---|
| Touching 188 call sites | Mechanical and identical per edit; the alternative leaves the hazard live |
| New gate surface | Extends R0's single entry point rather than adding a second checker |

## Phase 2 preview

`/speckit.tasks` will order these. Stages 1–4 are independent of each other and parallelisable; stage 5
depends on nothing but is only *useful* after 1–4; stage 6 must be last.
