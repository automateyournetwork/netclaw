# Tasks — Arista ANTA validation (R25)

**Branch**: `098-arista-anta-validation` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Dependency-ordered. `[P]` = parallelisable.

---

## Phase 1 — Feasibility and hazards (BLOCKING)

- [X] **T001** Confirm licence: Apache-2.0, Copyright 2022 Arista Networks — licence-identical to
      NetClaw (FR none; gates adoptability)
- [X] **T002** **Dry-run the install before installing** — found `cryptography` 46.0.5 → 50.0.0 with
      four unbounded dependents including the federation TLS stack (FR-011)
- [X] **T003** Create the dedicated virtualenv with `virtualenv` (`python3 -m venv` fails on this
      host — no `ensurepip`)
- [X] **T004** Install `anta==1.9.0` + `mcp`, then **verify system `cryptography` is still 46.0.5**
      (SC-008)
- [X] **T005** Enumerate the catalogue: **208 tests / 33 modules** — quantifies the manifest risk
- [X] **T006** Prove ANTA runs live against `clab-mandible-veos1` — pass, fail, and error paths all
      exercised (SC-007)
- [X] **T007** Confirm `error` on an unreachable device is native, not something NetClaw must build
      (FR-005)
- [X] **T008** **Find the trap**: `VerifyBGPPeerCount` returns `failure` — not `skipped` — when BGP
      is simply not configured

## Phase 2 — The verdict model (this is the feature)

- [X] **T009** `verdict.py`: five outcomes — `pass`, `fail`, `not_applicable`, `skipped`, `error`
- [X] **T010** Reclassify an ANTA `failure` that indicates an inactive feature or unsupported command
      to `not_applicable`, **preserving the original message**, with a deliberately narrow rule so a
      real failure is never hidden (FR-004)
- [X] **T011** `verdict.health_percentage()` raises rather than computing one — `passed / total` is
      meaningless with `not_applicable` in the denominator
- [X] **T012** Five separate counts in every summary; no merging (FR-004, SC-003)
- [X] **T013** Device and `observed_at` on every result (FR-012)
- [X] **T014** `tls_verified` disclosed always, never a silent downgrade (spec 094 discipline)

## Phase 3 — Server

- [X] **T015** `anta_list_tests` and `anta_describe_test` — work with **no device configured**
      (FR-008, SC-005)
- [X] **T016** `anta_run_tests` — per-call `host`, credentials from environment only (FR-009,
      FR-013). Returns **structured per-test results**: test, category, device, verdict, and for
      failures the observed **and** expected values ANTA supplies natively (**FR-001, SC-001**)
- [X] **T017** `anta_status` — ANTA version, catalogue size, whether credentials are set
- [X] **T018** Unreachable device → `error`, no test results (FR-005), **verified live against a dead
      address** rather than mocked (**SC-004**)
- [X] **T019** Empty selection → "no tests selected", never all-pass (FR-006)
- [X] **T020** Missing required inputs → report what is required (FR-007)
- [X] **T021** No configuration path anywhere in the server (FR-003)
- [X] **T022** **Measure the manifest with a token counter** — must be ≤5,000 (FR-002, SC-002)

## Phase 4 — Tests

- [X] **T023** `tests/anta/run-tests.sh` — stdlib assertions that run **without** a device, so CI
      stays useful (spec 075 SC-013)
- [X] **T024** Assert `not_applicable` is not counted as `fail`
- [X] **T025** Assert `skipped` is not counted as `pass`
- [X] **T026** Assert a health percentage cannot be emitted
- [X] **T027** Assert no credential appears in any output (SC-006)
- [X] **T028** Assert the source contains no configuration verb (FR-003)
- [X] **T029** Live tests that skip themselves when the device is absent (SC-007)

## Phase 5 — Integration (docs/ADDING-AN-MCP.md in full)

- [X] **T030** `config/openclaw.json` — register with the venv interpreter, repo-relative
- [X] **T031** [P] `scripts/lib/catalog.sh` entry + profile membership
- [X] **T032** [P] `scripts/lib/install-steps.sh` — `component_install_anta()` creating the venv via
      the helper, with the `cryptography` reason stated in a comment
- [X] **T033** [P] `workspace/skills/anta-validation/SKILL.md` carrying the verdict rules
- [X] **T033a** **State the plane boundary explicitly** in the skill and in SOUL.md (**FR-010**):
      `arista-cvp-mcp` is the *management* plane, pyATS and the multivendor CLI driver are the
      *device-CLI* plane, ANTA is the *validation* plane. It reads state to assert on it and must not
      be used to fetch state for its own sake — that is the CLI plane's job. Without this the agent
      has three servers that all touch Arista and no rule for choosing
- [X] **T034** [P] `.env.example` — names only
- [X] **T035** [P] `TOOLS.md`, `README.md`, `SOUL.md` counts + capability paragraph
- [X] **T036** [P] HUD — **two** entries (node list + annotation map)
- [X] **T037** `mcp-servers/anta-mcp/README.md`
- [X] **T038** `.gitignore` negation for the new server dir; `.venv` excluded

## Phase 6 — Gates

- [X] **T039** `check-server-startup.py --only anta-mcp` (timeout is success)
- [X] **T040** `reconcile-mcp.py` exits 0
- [X] **T041** `verify-spec-artifacts.py` exits 0
- [X] **T042** `/speckit.analyze` run and **all findings fixed**
- [X] **T043** Roadmap: R25 → `DONE`

---

## Dependencies

```
T002 gates T003        (never install before measuring the blast radius)
T005 gates T022        (208 tests is why the manifest shape is what it is)
T008 gates T009–T012   (the trap must be characterised before it can be blocked)
T009–T014 → T015–T021
T022 gates T030        (over ceiling ⇒ redesign, as it did for 087 and R5)
T023–T029 → T039–T041
```

## Out of scope

Writing device configuration; authoring new tests; multivendor validation; CloudVision inventory
(overlaps `arista-cvp-mcp`); scheduled/continuous validation.
