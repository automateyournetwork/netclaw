# Tasks — Server Startup Check (reconstruction)

**Branch**: `088-server-startup-check` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge from the spec, the delivered script and its tests. All
> items are `[X]` — a record of completed work. Ordering reflects dependency, not chronology.

---

## Phase 1 — Establish that the gap is real (BLOCKING)

- [X] **T001** Confirm all four existing surfaces validate declarations only, never behaviour
- [X] **T002** Attempt static import analysis — **11 findings, 5 false** (`netclaw_tokens` resolves
      at runtime via `sys.path`)
- [X] **T003** Launch the processes instead: **7 of 98 servers cannot start**, 22 skills routing
      to them
- [X] **T004** Record the false-positive result in the script docstring so the shortcut is not retried

## Phase 2 — Core semantics (get these wrong and the surface is worthless)

- [X] **T005** **A timeout is SUCCESS** — a clean import that then blocks on stdio is correct MCP
      behaviour (FR-002)
- [X] **T006** Distinguish missing module from absent entry point (FR-003) — different fixes, and
      installing packages would never have fixed `aruba-cx-mcp`
- [X] **T007** Skip remote/HTTP servers and absent interpreters (FR-004) — a missing `node` is an
      install gap, not a broken registration
- [X] **T008** Name both the server and the specific cause in every finding (FR-005)

## Phase 3 — Fit for CI

- [X] **T009** `--warn-only` exits 0 with findings, matching every other surface (FR-006)
- [X] **T010** `--config` so the check is testable against fixtures (FR-007)
- [X] **T011** Performance: `TIMEOUT` 25→6 + `ThreadPoolExecutor(8)` — **>10 min → 14 s** (FR-008)
- [X] **T012** Register as the fifth reconcile surface (FR-009)
- [X] **T013** `WARN` must not render as a bare `PASS` — summary reads `PASS (with warnings)` (FR-010)

## Phase 4 — Disposition of the seven

- [X] **T014** Classify each of the seven by remedy: gated SDK / absent entry point / wrong env /
      host-blocked
- [X] **T015** Record all seven in the script, visible on every run — **do not** silence into
      `STARTUP_EXCEPTIONS`
- [X] **T016** Add `startup` to `ALWAYS_WARN` with the exit condition written into the code
- [X] **T017** File the `netclaw_pip_install` PEP 668 gap as follow-up (not fixed here)

## Phase 5 — Tests

- [X] **T018** 9 new assertions in `tests/reconcile/run-tests.sh` (32 total with the 23 pre-existing)
- [X] **T019** Assert stdio-blocking is not a failure
- [X] **T020** Assert a missing module fails and is named
- [X] **T021** Assert an absent entry point is distinguished
- [X] **T022** Assert `--warn-only` exits 0
- [X] **T023** Assert remote servers are skipped
- [X] **T024** Assert `STARTUP_EXCEPTIONS` actually suppresses — an untested suppression list is how
      a check quietly stops checking
- [X] **T025** Every assertion captures the exit code **directly, never through a pipe**

---

## Dependencies

```
T002 → T003 → T004      (the false positives are why launching is required)
T005 gates all testing  (inverted semantics flags all 75 working servers)
T011 gates T012         (a surface too slow for CI gets disabled)
T014 → T015 → T016
T018–T025 → merge
```

## Deliberately not done

- Fixing the seven — four different fixes, two impossible without vendor access. **Taken by
  [spec 090](../090-fix-dead-servers/spec.md).**
- PEP 668 handling in `netclaw_pip_install` — its own change, its own blast radius.
- Verifying a started server serves a **valid tool manifest** — needs a full MCP handshake, not a
  launch. Still open.
