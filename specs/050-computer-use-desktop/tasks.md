# Tasks: Computer Use — Full-Desktop Automation via OpenClaw's Native Skill

**Input**: Design documents from `/specs/050-computer-use-desktop/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/skill-interface.md, quickstart.md

**Tests**: Not explicitly requested beyond `bash -n` on the new install function and live functional validation, matching specs 048/049's own bar.

**Organization**: Tasks are grouped by user story per spec.md's priorities. This is a configuration/skill-authoring integration on top of OpenClaw's own ClawHub `computer-use` skill — no server code is authored by NetClaw.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Directory scaffolding

- [X] T001 Create skill directory: `workspace/skills/desktop-gui-inspect/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The installer catalog entry and coverage-tracking updates every user story depends on

**CRITICAL**: No user story work can be demonstrated until the component is installable

- [X] T002 Add `computer-use` catalog entry to `scripts/lib/catalog.sh` (category: `Analysis & Diagrams`, per research.md R3), formatted per spec 049's `contracts/catalog-entry-format.md`
- [X] T003 Write `component_install_computer_use()` in `scripts/lib/install-steps.sh`: install `xvfb`, `xfce4`, `xfce4-terminal`, `xdotool`, `scrot`, `imagemagick`, `dbus-x11`, `x11vnc`, `novnc`, `websockify` via the host's package manager, then run `openclaw skills install --global computer-use`, then verify (not assume — research.md R5) the live-viewing service is bound to loopback only and print a clear warning if it is not
- [X] T004 [P] Add `"Computer Use"` to `scripts/verify-inventory-counts.py`'s `EXTERNAL_INTEGRATIONS` list (research.md R3)
- [X] T005 [P] Add `"computer-use": ["Computer Use"]` to `scripts/verify-catalog-coverage.py`'s `GROUPED_EXTERNAL_COVERAGE` (research.md R3)
- [X] T006 Run `scripts/verify-catalog-coverage.py` and `scripts/verify-inventory-counts.py`; confirm both report zero unexplained gaps/discrepancies with the new entry in place

**Checkpoint**: Component is a real, trackable catalog entry. Live install validation and skill authoring can proceed.

---

## Phase 3: User Story 1 — Install Computer Use Through the Modular Installer (Priority: P1) 🎯 MVP

**Goal**: An operator can select Computer Use through the installer and end up with a working, connectable virtual desktop, no manual follow-up.

**Independent Test**: Select the component through the installer; confirm the virtual desktop and its live-viewing service come up with no errors and no credential prompt.

**⚠️ Note before running**: T008 installs a full XFCE desktop environment plus several other packages — a real, multi-hundred-MB system change, heavier than any prior spec's live-validation step. Confirm with the operator before running it if executing this outside a context where that's already been agreed.

### Implementation for User Story 1

- [X] T007 [US1] Run `bash -n` on `scripts/lib/catalog.sh` and `scripts/lib/install-steps.sh` to confirm syntax before live testing
- [X] T008 [US1] Live validation: run `./scripts/install.sh --components computer-use`; confirm the required packages install, `openclaw skills install --global computer-use` succeeds, and the result is idempotent on a second run
- [X] T009 [US1] Verify the live-viewing service's actual bind address (e.g. via `ss -tlnp` or equivalent) per research.md R5/FR-004; record the finding — if it is not loopback-only by default, document the gap and the operator-facing mitigation (SSH tunnel requirement) prominently rather than silently noting it

**Checkpoint**: Computer Use is installable and its virtual desktop is confirmed working — this alone is the MVP deliverable (a demonstrable, working capability, even before `desktop-gui-inspect` exists).

---

## Phase 4: User Story 2 — Operate a Desktop-Only Tool With No Browser or API Path (Priority: P2)

**Goal**: `desktop-gui-inspect` can read/confirm information from a desktop-only application via the virtual desktop.

**Independent Test**: Ask the skill to open a desktop application already available in the virtual desktop and read back a specific piece of visible information; confirm the answer is correct and no configuration change occurred.

### Implementation for User Story 2

- [X] T010 [US2] Create skill documentation in `workspace/skills/desktop-gui-inspect/SKILL.md` with YAML front matter (name, description per contracts/skill-interface.md, tags, metadata) and a Purpose section explaining the desktop-only gap this fills, directly parallel to `browser-gui-inspect`
- [X] T011 [US2] Add the Golden Rule section to `desktop-gui-inspect/SKILL.md`: the 17 desktop actions are for reading/navigating/confirming state only — never for submitting/applying/committing a real configuration change, which belongs to the relevant API-based skill's baseline→apply→verify + ITSM-gated workflow (research.md R4)
- [X] T012 [US2] Add "Workflow 1: Operate a Legacy Desktop-Only Tool" to `desktop-gui-inspect/SKILL.md`: locate/open the target application on the virtual desktop, perform the read/navigate actions needed to satisfy the operator's `intent`, capture a screenshot as supporting evidence, return the result — per contracts/skill-interface.md's behavior steps
- [X] T013 [US2] Add an error-handling section to `desktop-gui-inspect/SKILL.md` documenting `manual_setup_required`, `virtual_desktop_unavailable`, and `conflict` statuses (contracts/skill-interface.md, data-model.md)
- [X] T014 [US2] Live test: use `desktop-gui-inspect` against a simple bundled application (e.g. `xfce4-terminal`) already available on the virtual desktop and confirm it can read back a specific value correctly

**Checkpoint**: `desktop-gui-inspect` can genuinely answer a question about a desktop-only application.

---

## Phase 5: User Story 3 — Watch NetClaw Operate the Virtual Desktop Live (Priority: P3)

**Goal**: An operator can watch or take over the virtual desktop live via VNC/noVNC while NetClaw works, or to complete a step that needs a human.

**Independent Test**: Open a live viewer connection while a task runs and confirm real-time visibility and the ability to take control.

### Implementation for User Story 3

- [X] T015 [US3] Add "Workflow 2: Watch Mode via Live Viewer" to `desktop-gui-inspect/SKILL.md`: how to connect locally, and the SSH-tunnel pattern for viewing from a different machine (mirroring spec 048's remote-debugging-over-SSH-tunnel pattern for headless hosts, per quickstart.md step 4)
- [X] T016 [US3] Live test: open a live viewer connection (locally) while `desktop-gui-inspect` performs a task from T014, and confirm the operator can see the actions in real time and take control when desired

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Artifact Coherence

**Purpose**: Constitution Principle XI checklist completion

- [X] T017 [P] Update `TOOLS.md` with a `computer-use` entry: capability summary, the 17-action category breakdown, no-credential note, loopback-only live-viewing note
- [X] T018 [P] Update `SOUL.md` with the `desktop-gui-inspect` skill definition and a one-line capability summary
- [X] T019 [P] Update `README.md` with the Computer Use capability description and updated skill/component counts
- [X] T020 [P] Update `ui/netclaw-visual/server.js` with a new HUD catalog entry for this integration
- [X] T021 Re-run `scripts/verify-inventory-counts.py` and `scripts/verify-catalog-coverage.py` after all doc/count updates; confirm both pass
- [X] T022 Verify backwards compatibility — confirm `browser-viz-verify` and `browser-gui-inspect` are unaffected and every existing installer component still lists correctly via `./scripts/install.sh --list`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phases 3-5)**: All depend on Foundational
  - US1 (Phase 3): No dependencies on US2/US3 — MVP target, and a real prerequisite for both (nothing in US2/US3 works without a running virtual desktop)
  - US2 (Phase 4): Depends on US1 being validated (needs a working virtual desktop to test against)
  - US3 (Phase 5): Depends on US1; independent of US2's specific content, though both extend the same `SKILL.md` file (sequence to avoid edit conflicts)
- **Polish (Phase 6)**: Depends on all three user stories being complete

### Within Each User Story

- US2 and US3 both extend `desktop-gui-inspect/SKILL.md` — write US2's sections (T010-T013) before US3's (T015) to avoid overlapping edits, even though the underlying capabilities are independent

### Parallel Opportunities

- T004 and T005 (Foundational) can run in parallel — different files
- T017-T020 (Polish) can all run in parallel — different files

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002-T006)
3. Complete Phase 3: User Story 1 (T007-T009) — **confirm with the operator before T008's live system-package install**
4. **STOP and VALIDATE**: A working, connectable virtual desktop exists, confirmed loopback-only
5. This alone is a legitimate, demonstrable capability even before `desktop-gui-inspect` exists as a skill

### Incremental Delivery

1. Setup + Foundational → catalog entry exists, tracked by coverage tooling
2. Add US1 (installable virtual desktop) → verify → MVP
3. Add US2 (`desktop-gui-inspect` reads a legacy app) → verify → real operational value
4. Add US3 (Watch Mode) → verify → full parity with spec 048's browser experience
5. Phase 6 (Polish + Artifact Coherence) → feature complete

### Suggested MVP Scope

User Story 1 is the MVP — a working, connectable virtual desktop, confirmed secure-by-default (loopback-only), installable through the modular installer in one selection. US2 delivers the feature's actual value proposition (reading desktop-only targets); US3 completes the Watch Mode parity with spec 048.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- No `.env.example` changes are needed — research.md R6 confirms no credentials or environment variables apply to this capability
- This install function's shape genuinely differs from every prior catalog entry (OS packages + OpenClaw's own skill-marketplace command, not a vendored clone + `config/openclaw.json` entry) — this is expected and documented in research.md R3, not an inconsistency to "fix"
- T008's live install is the heaviest system change any spec in this project has made during validation — flagged explicitly in-line, not buried
- T009's loopback-only verification is a hard requirement (FR-004), not optional polish — do not mark US1 complete without actually checking it
