# Tasks: Dependency-Pin Hazards

**Feature**: 077-dependency-pin-hazards | **Date**: 2026-07-31 | **Roadmap**: R0a
**Input**: [spec.md](./spec.md) · [plan.md](./plan.md)

> **Read the spec's PREMISE CORRECTION first.** `n2n-mcp` needs no migration to `fastmcp` 2.x — it
> imports `mcp.server.fastmcp` like the other six. The clarified answer was given on a premise I got
> wrong, and executing it would not have fixed anything.

**Ordering is repair-before-enforce**, as in R0: turning the gate on before the repairs land makes CI red
on `main` and blocks everything behind pre-existing debt.

---

## Phase 1: Setup

- [X] T001 Capture the pre-change baseline: for each of the 7 exposed servers record its current pins, and record the counts (188 bare pip, 1 scoped, 2 venv sites) into `specs/077-dependency-pin-hazards/baseline.txt`.
- [X] T002 Confirm each of the 7 servers' entry points currently import successfully in the *existing* environment, so a post-change failure is attributable to this feature rather than pre-existing.

---

## Phase 2: US1 — repair (P1)

**Goal**: a fresh install resolves dependencies whose APIs the code actually uses.

**Independent test**: resolve each repaired server's declared deps in a clean venv and import its entry point.

### Six `mcp>=` servers

- [X] T003 [P] [US1] Bound `claroty-mcp` — `mcp>=1.0.0,<2` in `mcp-servers/claroty-mcp/requirements.txt` (FR-001).
- [X] T004 [P] [US1] Bound `protocol-mcp` — `mcp>=1.0.0,<2`.
- [X] T005 [P] [US1] Bound `suzieq-mcp` — `mcp>=1.0.0,<2`.
- [X] T006 [P] [US1] Bound `nautobot-mcp-v2` — `mcp>=1.0.0,<2`.
- [X] T007 [P] [US1] Bound `uml-mcp` — `mcp>=1.2.0,<2`.
- [X] T008 [P] [US1] Bound `thousandeyes-mcp-community` — `mcp>=1.13,<2`.
- [X] T009 [US1] Add a comment to each of the six explaining *why* the upper bound is load-bearing: mcp 2.0.0 removed `mcp.server.fastmcp`. A bare `<2` with no reason invites a future maintainer to "tidy" it away (FR-001).

### `n2n-mcp` — same fix, extra care (federation)

- [X] T010 [US1] Bound `n2n-mcp`'s real dependency — `mcp>=1.0.0,<2` (FR-001a). **Not** a `fastmcp` migration; see the premise correction.
- [X] T011 [US1] Delete `n2n-mcp`'s unused `fastmcp>=0.1.0` declaration — nothing in the server imports `fastmcp`, and the dead pin is what produced this feature's own misdiagnosis (FR-001b, SC-002b).
- [X] T012 [US1] Verify the federation still functions after the change — exercise it, do not rely on the entry point importing (FR-001c, SC-002a).

### Verification

- [X] T013 [US1] For all 7, resolve declared deps in a clean venv and import the entry point; confirm the resolved `mcp` version provides `mcp.server.fastmcp` (FR-002, SC-001, SC-002).

---

## Phase 3: US1 — install-path repair (P1)

- [X] T014 [US1] Create `scripts/lib/pip-helper.sh` with `netclaw_pip_install()`: resolves the interpreter the target will run under, accepts an explicit venv, and **fails loudly rather than falling back to bare pip** (FR-003a, FR-003b).
- [X] T015 [US1] Route all 188 bare `pip`/`pip3` invocations in `scripts/lib/install-steps.sh` through the helper (FR-003, SC-003). Mechanical and identical per edit.
- [X] T016 [US1] Source the helper from wherever `install-steps.sh` is loaded so no step can bypass it (SC-003a).
- [X] T017 [US1] Fix venv creation in `scripts/lib/install-steps.sh` — `virtualenv` fallback where `ensurepip` is absent, with a failure naming the one-line remedy (FR-004).
- [X] T018 [US1] Fix venv creation in `scripts/gait-venv-setup.sh` (FR-005). GAIT is the audit trail Principle IV makes non-negotiable; its venv failing is not cosmetic.
- [X] T019 [US1] Verify both venv sites work on this host, where `python3 -m venv` fails outright (SC-004).

---

## Phase 4: US2 — enforcement (P1)

> **Gate goes on only after Phases 2–3 are clean.**

- [X] T020 [US2] Create `scripts/check-dependency-pins.py` (stdlib only). Scan 1: for each server, statically parse its Python for submodule imports and cross-reference declared pins; fail on unbounded pin + submodule import (FR-006, FR-006a).
- [X] T021 [US2] Scan 2: fail on bare `pip`/`pip3` in install steps, naming file and line (FR-007, FR-009).
- [X] T022 [US2] Scan 3: flag `python3 -m venv` with the `ensurepip` caveat (FR-008).
- [X] T023 [US2] Scan 4: flag a declared dependency nothing imports — `n2n-mcp`'s dead `fastmcp` pin is the motivating case (FR-006c).
- [X] T024 [US2] Support recorded exceptions with a reason, matching R0's treatment of intentionally-external integrations (FR-010).
- [X] T025 [US2] Confirm the scan detects **7 of 7** exposed servers when run against the pre-repair state (SC-005a). Document that top-level API drift is a technique limitation with no instance here (FR-006b).
- [X] T026 [US2] Add a `dependencies` surface to `scripts/reconcile-mcp.py`, exiting non-zero on failure (FR-011).
- [X] T027 [US2] Verify the CI workflow picks it up — it invokes `reconcile-mcp.py` with no arguments, so a new surface is covered automatically.

---

## Phase 5: US3 — verifiability (P2)

- [X] T028 [US3] Add a resolution check reporting each server's resolved API-significant versions without installing, and confirm it completes inside SC-008's 5-minute budget (FR-012, SC-008).
- [X] T029 [US3] Ensure it needs no credentials, no agent, and degrades to "could not resolve" offline rather than passing vacuously (FR-013, SC-010).
- [X] T030 [US3] Confirm a server with no `requirements.txt` is not reported as a gap (FR-014).

---

## Phase 6: Tests and docs

- [X] T031 [P] Contract test: an unbounded pin on a submodule-imported package fails the gate, naming server and package (SC-005).
- [X] T032 [P] Contract test: a bare `pip3 install` fails the gate, naming file and line (SC-006).
- [X] T033 [P] Contract test: a clean repository passes and exits zero (SC-007).
- [X] T034 [P] Contract test: a recorded exception is accepted.
- [X] T035 Add the pinning rule to `docs/ADDING-AN-MCP.md` so R2–R24 inherit it: bound any pin on a package whose submodule you import, and never call bare pip.

---

## Phase 7: Close-out

- [X] T036 Verify SC-009 / FR-016: 202 skills and 150 integrations still available — no regression.
- [X] T037 Verify FR-017: a host where `pip3` and `python3` agree still installs correctly.
- [X] T037a Verify FR-015: no integration capability was added or removed — `git diff main` shows no new `mcp-servers/` server, no new catalog entry, and no new install function.
- [X] T038 Full run: R0 gate, R0 tests, R1 offline suites, new dependency surface — all green.
- [X] T039 Update `docs/COVERAGE-ROADMAP.md` — R0a `DONE` with outcome, including the premise correction.
- [X] T040 Record the GAIT session summary (Principle IV). **No blog post — waived by the maintainer.**

---

## Dependencies

```
Phase 1 (T001-T002)
      ↓
Phase 2 repairs (T003-T013) ── Phase 3 install path (T014-T019)   [parallel]
      ↓                              ↓
      └──────────────┬───────────────┘
                     ↓
      Phase 4 enforcement (T020-T027)   ← gate ON only after repairs are clean
                     ↓
      Phase 5 (T028-T030) ── Phase 6 (T031-T035)   [parallel]
                     ↓
      Phase 7 close-out (T036-T040)
```

**Parallel**: T003–T008 are six different files. T031–T034 are independent tests. Phases 2 and 3 do not
touch the same files.

## Summary

| Phase | Tasks | Count |
|---|---|---|
| 1 Setup | T001–T002 | 2 |
| 2 Pin repairs | T003–T013 | 11 |
| 3 Install path | T014–T019 | 6 |
| 4 Enforcement | T020–T027 | 8 |
| 5 Verifiability | T028–T030 | 3 |
| 6 Tests + docs | T031–T035 | 5 |
| 7 Close-out | T036–T040 | 5 |
| **Total** | | **40** |
