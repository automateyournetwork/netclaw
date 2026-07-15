# Tasks: Documentation Inventory Reconciliation

**Input**: Design documents from `/specs/047-docs-inventory-reconciliation/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/verify-inventory-counts-cli.md, quickstart.md

**Tests**: Not requested for this feature. Verification is instead performed by running `scripts/verify-inventory-counts.py` itself (per its own acceptance scenarios in spec.md User Story 3) rather than a separate pytest suite, since there is no product code to unit test — the script's own successful pass/fail report against the live repo *is* the verification.

**Organization**: Tasks are grouped by user story from spec.md so each can be delivered and checked independently: US1 = consistent counts everywhere, US2 = complete inventory tables + fact-check, US3 = durable repeatable verification.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps task to US1, US2, or US3
- All file paths are relative to the repository root (`/home/johncapobianco/netclaw`)

---

## Phase 1: Setup

**Purpose**: Create the skeleton of the new verification script that every later phase depends on.

- [X] T001 Create `scripts/verify-inventory-counts.py` with a shebang (`#!/usr/bin/env python3`), a module docstring pointing to `specs/047-docs-inventory-reconciliation/contracts/verify-inventory-counts-cli.md` for the contract, imports (`os`, `json`, `re`, `sys` only — stdlib), and an empty `main()` guarded by `if __name__ == "__main__": sys.exit(main())` that currently just returns `0`. No counting logic yet.

**Checkpoint**: Script file exists and runs (`python3 scripts/verify-inventory-counts.py` exits 0 with no output) — ready for Foundational logic.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the counting/verification logic that produces the ground-truth numbers every documentation-editing user story (US1, US2) depends on. Per data-model.md and contracts/verify-inventory-counts-cli.md.

**⚠️ CRITICAL**: No documentation edit task (Phase 3 or Phase 4) may start until T006 produces the authoritative current counts — editing docs against guessed or stale numbers would repeat the exact failure this feature exists to fix.

- [X] T002 Implement `count_skills()` in `scripts/verify-inventory-counts.py`: walk `workspace/skills/`, count each subdirectory that contains a `SKILL.md` file (per data-model.md Entity: Skill validation rule), explicitly excluding the top-level `SKILL-SCHEMA.md` file (not a directory). Return the integer count.
- [X] T003 Implement `count_mcp_integrations()` in `scripts/verify-inventory-counts.py`: load `config/openclaw.json`, read the `mcpServers` object, count top-level entries; expand the single Check Point bundle entry into its 15 documented `chkp-*` sub-servers per data-model.md Entity: MCP Integration (subtract 1 for the parent entry, add 15 for the members); add a hardcoded, clearly-commented `EXTERNAL_INTEGRATIONS` list at the top of the file for servers documented in README's MCP Servers table but absent from `config/openclaw.json` (seed it with the names confirmed during this session's audit: GitHub, Microsoft Graph, Itential, Cisco NSO, Cisco CML — verify and adjust against the current README table content as of implementation time). Return the integer count and a breakdown dict (`{"config_entries": N, "checkpoint_bundle_expansion": N, "external_documented": N}`).
- [X] T004 Implement `check_doc_claims(skill_count, mcp_count)` in `scripts/verify-inventory-counts.py`: read `README.md` and `SOUL.md`, use regex to find numeric claims adjacent to the words "skill(s)" and "MCP" (e.g. patterns like `\d+ skills`, `\d+ MCP`), compare each found claim against the computed counts, and return a list of discrepancies as `{file, matched_text, claimed_value, computed_value}` dicts. Treat parsing misses as informational (log, don't fail) per contracts/verify-inventory-counts-cli.md Non-goals.
- [X] T005 Implement report printing and exit-code logic in `main()` in `scripts/verify-inventory-counts.py`: call `count_skills()`, `count_mcp_integrations()`, `check_doc_claims()`; print the report format specified in contracts/verify-inventory-counts-cli.md (headline skill count, MCP count with breakdown, PASS/FAIL with discrepancy lines); return exit code 0 if no discrepancies, 1 if discrepancies found, 2 if `workspace/skills/` or `config/openclaw.json` cannot be read.
- [X] T006 Run `python3 scripts/verify-inventory-counts.py` against the current repository state and record the printed skill count and MCP integration count — these are the authoritative ground-truth numbers used by every task in Phase 3 and Phase 4 below (they supersede the specific numbers noted in spec.md's Assumptions section, which may be stale if branches merged between spec-writing and now).

**Checkpoint**: Foundational verification tool works end-to-end and has produced this session's ground-truth numbers. All documentation-editing user stories can now begin.

---

## Phase 3: User Story 1 - Trustworthy Skill/Integration Counts (Priority: P1) 🎯 MVP

**Goal**: Every place a skill or MCP count appears across the five canonical documentation files states the same number, and that number matches T006's computed ground truth.

**Independent Test**: Grep every numeric skill/MCP claim in README.md and SOUL.md; confirm all agree with each other and with `python3 scripts/verify-inventory-counts.py`'s output.

### Implementation for User Story 1

- [X] T007 [US1] Update the skill/MCP counts in `README.md`'s top prose (the header sentence near line 7 and the "That's it. The installer deploys..." sentence near line 19) to T006's ground-truth numbers.
- [X] T008 [US1] Update `README.md`'s Visual HUD paragraph (near line 96, currently "48 integrations, 103 skills") to T006's ground-truth numbers, and rephrase the sentence to note the HUD computes these counts live from the codebase (supports FR-012 and avoids re-drifting the next time a skill is added — do not hardcode a number that isn't already true today).
- [X] T009 [US1] Update the `## MCP Servers (N)` heading (near line 375) and `## Skills (N)` heading (near line 454) in `README.md` to T006's ground-truth numbers.
- [X] T010 [P] [US1] Update the two skill/MCP count mentions in `SOUL.md` (near line 15: "N skills backed by M MCP servers", and near line 328: "N skills") to T006's ground-truth numbers.
- [X] T011 [US1] Run `python3 scripts/verify-inventory-counts.py` again; confirm the `check_doc_claims()` discrepancy report shows zero discrepancies for README.md and SOUL.md (depends on T007-T010 being complete).

**Checkpoint**: All headline count claims across README.md and SOUL.md are internally consistent and match the codebase. This alone is a shippable, valuable increment even before Phase 4's table-completeness work.

---

## Phase 4: User Story 2 - Complete MCP Server and Skill Inventory Tables (Priority: P1)

**Goal**: The README's MCP Servers table, README's Skills section, and mcp-servers/README.md's table each contain a row for every integration/skill the codebase actually has — and specifically confirm Azure, Batfish, GitLab, and NetFlow/IPFIX as already-shipped, correcting the external review's incorrect gap claims.

**Independent Test**: Cross-reference every entry from T003's MCP integration set and T002's skill set against the README/mcp-servers/README.md tables; confirm zero omissions. Search README.md for "Azure", "Batfish", "GitLab", "NetFlow" and confirm each is documented as existing.

### Implementation for User Story 2

- [X] T012 [US2] Add rows to `README.md`'s MCP Servers table (the table starting near line 377) for every MCP integration counted in T003 that isn't already listed — including explicit confirmation that Azure (`azure-network-mcp`), Batfish (`batfish-mcp`), GitLab (`gitlab-mcp`), and NetFlow/IPFIX (`ipfix-mcp`) are present and described as already-shipped capabilities, not new additions.
- [X] T013 [US2] Add entries to `README.md`'s Skills section (the tables starting near line 454) for every skill directory counted in T002 that isn't already listed.
- [X] T014 [P] [US2] Rewrite `mcp-servers/README.md`'s "Available Servers" table to list every vendored directory under `mcp-servers/` (currently only 12 of 54+ are listed), matching the format of its existing table (Server / Description / Type columns).
- [X] T015 [P] [US2] Review `SOUL-SKILLS.md` against T002's computed skill set; add any missing skill sections so every skill directory is represented (this file does not currently make a headline count claim, so no numeric edit is expected here — only content completeness).
- [X] T016 [US2] Run `python3 scripts/verify-inventory-counts.py` again to confirm counts still match after table edits, and manually grep `README.md` for "Azure", "Batfish", "GitLab", and "NetFlow" to confirm each returns a hit describing it as a current, shipped capability (depends on T012-T015).

**Checkpoint**: Every skill and MCP integration in the codebase is discoverable in the README/mcp-servers/README.md tables. The specific false-negative that caused the external review's incorrect gap claims (Azure/Batfish/GitLab/NetFlow) is eliminated.

---

## Phase 5: User Story 3 - Repeatable Verification Instead of Manual Recount (Priority: P2)

**Goal**: Confirm the verification script actually detects drift when the codebase changes, and make sure future contributors know it exists.

**Independent Test**: Add a throwaway skill directory (or config entry), run the script, confirm the count increments; remove the throwaway artifact and confirm the count reverts.

### Implementation for User Story 3

- [X] T017 [P] [US3] Validate skill-count sensitivity: create a temporary `workspace/skills/_tmp-verify-test/SKILL.md` file, run `python3 scripts/verify-inventory-counts.py`, confirm the reported skill count is exactly one higher than T006's baseline, then delete `workspace/skills/_tmp-verify-test/` entirely.
- [X] T018 [P] [US3] Validate MCP-count sensitivity: temporarily add a dummy entry under `mcpServers` in `config/openclaw.json` (e.g. `"_tmp_verify_test": {}`), run `python3 scripts/verify-inventory-counts.py`, confirm the reported MCP integration count is exactly one higher than T006's baseline, then remove the dummy entry and confirm the count reverts to baseline on a final run.
- [X] T019 [US3] Add a short note near the `## MCP Servers (N)` and `## Skills (N)` headings in `README.md` pointing contributors at `python3 scripts/verify-inventory-counts.py` as the way to re-verify these numbers before submitting a future PR that adds a skill or MCP server (references quickstart.md's contributor workflow).
- [X] T020 [US3] Add a one-line note in `README.md`'s mission/history log section (near the existing "## Missions for reference" content around line 2509, or the nearest equivalent historical-record section) noting that spec `038-docs-hud-refresh` was an earlier attempt at this reconciliation, now superseded by spec `047-docs-inventory-reconciliation`, per FR-011. Do not modify any files under `specs/038-docs-hud-refresh/`.

**Checkpoint**: The verification script is proven to detect drift in both directions (skills and MCP servers), and future contributors have a documented, discoverable path to use it — closing the loop that caused two reconciliation specs (038 and this one) to be needed.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final consistency sweep and closing out the feature.

- [X] T021 [P] Full read-through of `README.md` and `SOUL.md` to confirm none of the previously-conflicting stale numbers (113, 66, 48, 103, 74, 69, 127, 145, 188, 47, 183, or whatever was actually stale at implementation time per T006) remain anywhere outside explicitly historical, dated mission-log entries (e.g., "MISSION02... 78 skills" is a past-state record and must NOT be changed).
- [X] T022 Run `python3 scripts/verify-inventory-counts.py` one final time and confirm exit code `0`.
- [X] T023 [P] Per Constitution Principle XVII, draft a short milestone note (not a full blog post — this is a documentation-accuracy fix, not a new capability) and present it to the user for review before deciding whether it warrants a WordPress publish.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 (script file must exist). BLOCKS Phase 3 and Phase 4 entirely (both need T006's ground-truth numbers) and BLOCKS Phase 5 (needs a working script to validate).
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion. Independently shippable once T011 passes.
- **User Story 2 (Phase 4)**: Depends on Phase 2 completion. Does not depend on Phase 3, but in practice both target README.md, so completing Phase 3 first avoids merge conflicts within the same file.
- **User Story 3 (Phase 5)**: Depends on Phase 2 completion (needs the finished script). Independent of Phase 3/4 content, though T019/T020 touch README.md so should follow Phase 3/4's README edits to avoid conflicts.
- **Polish (Phase 6)**: Depends on all prior phases.

### Within Each Phase

- Phase 2: T002 → T003 → T004 → T005 → T006 (all edit the same file, sequential; each function depends on the file/imports from the previous task).
- Phase 3: T007 → T008 → T009 (sequential, same file: README.md) with T010 (SOUL.md) parallel to all three; T011 depends on T007-T010.
- Phase 4: T012 → T013 (sequential, same file: README.md) with T014 (mcp-servers/README.md) and T015 (SOUL-SKILLS.md) parallel to both and to each other; T016 depends on T012-T015.
- Phase 5: T017 and T018 are independent of each other (different files/actions) and can run in parallel; T019 → T020 sequential (both edit README.md).

### Parallel Opportunities

- T010 can run parallel to T007-T009 (different file).
- T014 and T015 can run parallel to each other and to T012-T013 (three different files).
- T017 and T018 can run parallel to each other (different files: workspace/skills/ vs config/openclaw.json).
- T021 and T023 in Polish can run parallel to each other.

---

## Parallel Example: Phase 4 (User Story 2)

```bash
# After T012-T013 (README.md) are underway, these can run alongside them:
Task: "Rewrite mcp-servers/README.md's Available Servers table to list every vendored directory"
Task: "Review SOUL-SKILLS.md against the computed skill set and add any missing skill sections"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001).
2. Complete Phase 2: Foundational (T002-T006) — this is the critical path; it produces the numbers every later task needs.
3. Complete Phase 3: User Story 1 (T007-T011).
4. **STOP and VALIDATE**: Run the script, confirm PASS, spot-check README.md and SOUL.md by eye.
5. This alone fixes the most visible credibility problem (disagreeing headline numbers) and is shippable on its own.

### Incremental Delivery

1. Setup + Foundational → verification tool exists and ground truth is known.
2. Add User Story 1 → headline numbers agree everywhere → demo/ship.
3. Add User Story 2 → tables are complete, Azure/Batfish/GitLab/NetFlow confirmed shipped → demo/ship.
4. Add User Story 3 → script's drift-detection is proven and discoverable for future contributors → demo/ship.
5. Polish → final sweep and exit-code confirmation.

---

## Notes

- [P] tasks touch different files and have no ordering dependency on each other.
- [Story] labels map every Phase 3+ task back to spec.md's US1/US2/US3 for traceability.
- No test framework is introduced; the verification script's own PASS/FAIL output is this feature's test signal, per spec.md's Testing note in plan.md's Technical Context.
- Commit after each phase checkpoint, not after every individual task — these are fine-grained edits to a small number of files and squashing noisy intermediate commits keeps the PR history readable.
- Do not touch `specs/038-docs-hud-refresh/` files (T020 references it but must not modify it) — it remains as historical record per FR-011.
