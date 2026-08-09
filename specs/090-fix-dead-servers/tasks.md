# Tasks — Fix the dead servers (reconstruction)

**Branch**: `090-fix-dead-servers` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

> **Reconstruction.** Written after merge from the spec and the delivered change. All items `[X]`,
> ordered by dependency rather than chronology.

---

## Phase 1 — Fix the root cause (BLOCKING — everything else depends on it)

- [X] **T001** `netclaw_pip_install` detects `externally-managed-environment`, announces the retry,
      and retries with `--break-system-packages` (FR-001)
- [X] **T002** It no longer swallows failures — prints what it was installing plus the real pip
      output, and returns non-zero (FR-002)
- [X] **T003** Remove the redundant per-call-site retry: **53 sites collapsed**;
      `netclaw_pip_install` calls 129 → 80; stderr-discarding pip calls 120 → 21 (FR-003)
- [X] **T004** Confirm the 94 `component_install_*` functions are unchanged

## Phase 2 — Install the three obtainable SDKs, without moving a shared pin

- [X] **T005** `pygnmi` 0.8.15 → fixes `gnmi-mcp`
- [X] **T006** `junos-eznc` 2.8.2 → fixes `junos-mcp`'s import
- [X] **T007** `prisma-sase` 6.8.1b1 → fixes `prisma-sdwan-mcp` (**correcting 088's wrong claim**)
- [X] **T008** Verify shared pins unmoved — `fastmcp` 2.14.7 → 2.14.7; `junos-eznc`'s paramiko 5.0.0
      cannot reach `multivendor-cli-mcp`'s own `.venv` (FR-004)

## Phase 3 — The second defects hidden behind the first

- [X] **T009** `junos-mcp`: installer seeds an **empty `{}`** inventory — never the template, whose
      placeholder credentials and literal `"ip"` device would plant fakes. Server starts and reports
      `0 device(s)`
- [X] **T010** `arista-cvp-mcp`: extend the `uv run --with` list (`urllib3`, `python-dotenv`) —
      host-wide installs are irrelevant, `uv run` never sees system site-packages
- [X] **T011** `arista-cvp-mcp`: patch upstream's hardcoded `/home/admin/app.log` **at install
      time**, idempotently, re-applied after every `git pull` (the clone is gitignored)
- [X] **T012** Verify that patch against a **pristine upstream download**, not the local copy —
      the committed artifact is the patch, not the edit
- [X] **T013** `aruba-cx-mcp`: fix the **registration path** — nothing was missing (FR-005)
- [X] **T014** Add explicit `--transport stdio` to the one `fastmcp run` registration; sweep the
      config to confirm it is the only one

## Phase 4 — Exceptions and checker correction

- [X] **T015** Except `radkit-mcp` with a reason precise enough that nobody retries `pip`:
      `radkit-client` 404s, `cisco-radkit-client` is a relocation stub, wheels are code-signed and
      distributed by Cisco only (FR-006)
- [X] **T016** Teach the checker to distinguish *a data file the server loads* from *a missing entry
      point* — 088 reported `devices.json` as an entry-point failure (FR-008)

## Phase 5 — Promote the gate

- [X] **T017** Remove `startup` from `ALWAYS_WARN` — **a dead server now fails the build** (FR-007)
- [X] **T018** Confirm 088's written exit condition is met
- [X] **T019** `reconcile-mcp.py` exits 0 with `startup` hard-failing

---

## Dependencies

```
T001–T003 gate T005–T007   (nothing installs until the helper works)
T005 → T009                (the import must succeed before the data-file defect appears)
T006 → T010 → T011 → T012  (each defect was only visible once the previous was fixed)
T009–T016 → T017           (the gate can only harden once six are green and one is excepted)
```

## Deliberately not done

Obtaining RADKit (not publicly distributable), and verifying that a started server serves a **valid
tool manifest** — that needs a full MCP handshake and remains open from 088.
