# Implementation Plan: Server Startup Check (fifth reconcile surface)

**Branch**: `088-server-startup-check` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

> ## ⚠ This is a reconstruction
>
> Written **2026-08-05** after merge, from `spec.md`, the delivered script and the git history.
> No `plan.md` existed during the build — a breach of Principle XVI, part of the 087–096 drift.
> Reconstructed so the artifact set is complete and the reasoning recoverable.

## Summary

`reconcile-mcp.py` had four surfaces, and **all four validate declarations against each other**.
None of them ran anything. So the gate exited 0 and CI passed while **7 of 98 registered servers
could not start at all**, with **22 skills routing to them**.

This adds a fifth surface that **launches every registered stdio server** and reports the ones that
die on import. It is deliberately generalised rather than a one-off fix for the seven.

## Technical Context

**Language/Version**: Python 3.10+, stdlib only (repo convention for `scripts/`)
**Primary Dependencies**: None — `subprocess`, `concurrent.futures`, `json`
**Storage**: None
**Testing**: `tests/reconcile/run-tests.sh` — 32 assertions (23 pre-existing, 9 new), bash + Python
stdlib, fixtures in a temp dir, repository never modified
**Target Platform**: Linux, and CI
**Project Type**: Repository tooling — a reconcile surface
**Performance Goals**: **CI-fast.** First working version took >10 minutes; `TIMEOUT` 25→6 plus
`ThreadPoolExecutor(8)` brought it to **14 s**
**Constraints**: Must not modify the repository; must be testable against fixtures, not only the live
config
**Scale/Scope**: 98 registered servers at the time of writing

## Constitution Check

| Principle | Gate | Status |
|---|---|---|
| **VIII. Verify After Every Change** | The repo must be able to detect its own breakage | **PASS** — this is that principle applied to the gate itself |
| **XI. Full-Stack Artifact Coherence** | Coherence must be *verified*, not asserted | **PASS** — adds the first dynamic surface |
| **XII. Documentation-as-Code** | Findings self-documenting | **PASS** — the seven are recorded in the script and visible on every run |
| **XVI. Spec-Driven Development** | specify → plan → task → implement | **VIOLATED** — see Complexity Tracking |

## Project Structure

```text
scripts/check-server-startup.py     # the surface
scripts/reconcile-mcp.py            # registers it; adds it to ALWAYS_WARN
tests/reconcile/run-tests.sh        # 9 new assertions
```

**Structure Decision**: A standalone script that `reconcile-mcp.py` calls, matching the four existing
surfaces. Standalone so it can be run alone (`--only <key>`) while iterating on a single server.

## The design constraint that shapes everything: a timeout is success

An MCP stdio server that imports cleanly then blocks reading stdin is **behaving correctly**. Getting
this backwards flags all 75 working servers and makes the surface worthless. FR-002 exists because
that is the obvious wrong implementation.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **Principle XVI breached** — implementation preceded plan/tasks | Nothing justified it; part of the 087–096 drift | Remedied by this reconstruction plus a gate against recurrence |
| **`startup` added to `ALWAYS_WARN`** — reports but never fails the build | Two of the seven need an SDK that is **not publicly distributable**, so nobody can make this surface green today | Hard-failing would force either reverting the check or papering the seven into `STARTUP_EXCEPTIONS`. Both defeat the check on the day it was written. **Exit condition is written into the code**: remove `"startup"` from `ALWAYS_WARN` once the seven resolve |
| **Not fixing the seven here** | Four different fixes, two impossible without vendor access | Bundling them would make an unmergeable change; spec 090 took them |

## Meta-pattern this feature generalises

Third instance in this repo of the same failure:

1. `check-dependency-pins.py` read only `requirements.txt`, never an installed version.
2. `verify-inventory-counts.py` checks headline arithmetic, never table membership.
3. Nothing checked whether a registered server can start.

**A check that validates declarations cannot detect a declaration that is uniformly, consistently
wrong.** Recorded because the same shape will recur.
