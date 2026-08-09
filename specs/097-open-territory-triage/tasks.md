# Tasks — Open-territory triage (R24)

**Branch**: `097-open-territory-triage` | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Dependency-ordered. `[P]` = parallelisable (touches a different file, no shared prerequisite).

> **Phase numbering.** `plan.md` uses the speckit convention (Phase 0 research, Phase 1 design,
> Phase 2 tasks). The phases below are execution phases within that Phase 2. Mapping: plan Phase 0 =
> tasks Phases 1–2; plan Phase 1 = tasks Phase 3; the rest are verification and integration.

---

## Phase 1 — Establish the baseline (BLOCKING — every disposition depends on it)

- [X] **T001** Extract R1's **claimed** platform list from `specs/076-multivendor-cli-driver/spec.md`
- [X] **T002** Extract R1's **verified** subset and the amendment that explains it (2 families: Nokia
      SR Linux, FRR) — this is what splits `COVERED (verified)` from `COVERED (claimed)`
- [X] **T003** Inventory registered servers bearing on candidates (`arista-cvp-mcp`, `gnmi-mcp`,
      `nautobot-golden-config-mcp`, the four lab controllers)
- [X] **T004** Inventory lab access actually on disk — vEOS image, SR Linux, containerlab, GNS3,
      EVE-NG, CML, Docker — the concrete list FR-006 and SC-007 are tested against

## Phase 2 — Close the two open questions the list depends on

- [X] **T005** [P] Megaport — check whether the "genuinely unclaimed" premise still holds.
      **It does not**: an official MCP server exists, open beta, read-only, staging environment
      documented
- [X] **T006** [P] Arista ANTA — check whether an MCP exists. **None found**; the CVP servers are
      the management plane, already covered
- [X] **T007** [P] gNOI — establish what it adds over `gnmi-mcp` and whether its RPCs fit a
      read-first posture

## Phase 3 — Assess all 22 candidates (the deliverable)

- [X] **T008** Networking platforms — **7 R24 entries, 8 platform names**: "Nokia SR Linux / SR OS"
      is one entry covering two NOSes with different verification status, so it gets two rows and one
      disposition. Plus SONiC, VyOS, ANTA, netlab, Oxidized/Netpicker, gNOI
- [X] **T009** [P] Service provider / optical / mobile (5): Ciena, Infinera, Nokia NSP, Open5GS,
      free5GC
- [X] **T010** [P] SASE / cloud / NaaS (6): Netskope, Cato, Versa, Aviatrix, Alkira, Megaport
- [X] **T011** [P] Wireless design (2): Ekahau, Hamina
- [X] **T012** [P] Adopt-don't-build (2): MikroTik RouterOS, UniFi
- [X] **T013** Select **at most two**, each with a documented access check (FR-006), what it does
      that nothing else does, what would verify it, and its manifest-cost risk (FR-007)
- [X] **T014** Write `TRIAGE.md` with all 22 dispositions

## Phase 4 — Self-check against the success criteria

- [X] **T015** Assert every candidate has exactly one disposition — 22 assessed, 0 unassessed, no
      doubles (FR-001, SC-001)
- [X] **T016** Assert `SELECTED` ≤ 2 (FR-005, SC-002)
- [X] **T017** Assert every `COVERED` names its coverer **and** its confidence (FR-003, SC-003)
- [X] **T018** Assert every `DEFERRED` names its unblocking condition (FR-004, SC-004)
- [X] **T019** Assert nothing reachable today is `DEFERRED` (FR-008)
- [X] **T020** Assert every claim is traceable to repository state or named desk research (FR-006a,
      FR-010)
- [X] **T020a** Assert every reason **names a blocker, a covering server, or a measurement** — and
      that no disposition rests on a bare judgement such as "low value" or "not interesting"
      (**FR-002**). This is the requirement that stops the document degrading into opinion, and it
      had no check until analysis found the gap
- [X] **T020b** Assert the single-entry readability criterion: for each disposition, the entry alone
      answers "should I build this, and if not why not" without opening another file (SC-005). Spot-
      check the three hardest cases — one `COVERED (claimed)`, one `DEFERRED`, one `DROPPED`
- [X] **T020c** Assert each `SELECTED` candidate carries what its spec needs to start: unique
      capability, access check, and manifest-cost risk (FR-007, SC-006)

## Phase 5 — Roadmap integration

- [X] **T021** Rewrite `docs/COVERAGE-ROADMAP.md` R24 section as a **summary + link**, not a
      duplicate table (FR-009, SC-008)
- [X] **T022** Update the R24 status-board row and the "Where we are" tally — R24 leaves
      `NOT STARTED`, and Tier A loses an item
- [X] **T023** Record any `SELECTED` candidate as a new roadmap item so it is schedulable

## Phase 6 — Gates

- [X] **T024** `python3 scripts/verify-spec-artifacts.py` exits 0 (this feature's own artifacts)
- [X] **T025** `python3 scripts/reconcile-mcp.py` exits 0 — **unchanged**, since nothing is
      registered
- [X] **T026** `/speckit.analyze` run and **all findings fixed**, not merely listed

---

## Dependencies

```
T001–T004 gate everything      (dispositions rest on what is actually reachable)
T002 gates T017                (the verified/claimed split cannot be asserted without it)
T005–T007 gate T008–T012       (two candidates' categories change on these findings)
T004 gates T013                (selection requires the concrete access list)
T008–T013 → T014 → T015–T020
T014 → T021 → T022 → T023
T024–T026 last
```

`[P]` groups: T005/T006/T007 are independent lookups; T009/T010/T011/T012 are independent category
assessments once the baseline exists.

## Out of scope (not tasks)

Building any selected candidate; standing up any lab (clarified 2026-08-05); re-assessing R10, R22
or R5; expanding the candidate list beyond the 22.
