# Tasks: Chrome DevTools Browser Automation & Inspection Skill

**Input**: Design documents from `/specs/048-chrome-devtools-browser-inspection/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/mcp-tools.md, contracts/skill-interfaces.md, quickstart.md

**Tests**: Not explicitly requested in the feature specification. Test tasks are omitted; quickstart.md's verification steps serve as the manual acceptance check per user story.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. This is a configuration integration — no MCP server code is authored by NetClaw. The official `chrome-devtools-mcp` package (Node.js, Chrome DevTools team) is installed via `npx` and spawned as a local stdio process. Tasks focus on registration, a small setup script, documentation, skill authoring across two skills, and artifact coherence.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Directory structure creation and MCP server registration

- [X] T001 Create MCP server directory: `mcp-servers/chrome-devtools-mcp/`
- [X] T002 [P] Create skill directory: `workspace/skills/browser-viz-verify/`
- [X] T003 [P] Create skill directory: `workspace/skills/browser-gui-inspect/`
- [X] T004 [P] Register `chrome-devtools-mcp` server in `config/openclaw.json` under `mcpServers` with command `npx`, args `["-y", "chrome-devtools-mcp@latest", "--userDataDir=${CHROME_DEVTOOLS_PROFILE_DIR}", "--channel=${CHROME_DEVTOOLS_CHANNEL:-stable}"]`, env `CHROME_DEVTOOLS_HEADLESS` (default `true`) per research.md R2/R3 and quickstart.md step 2

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The setup script, environment variables, and MCP server README that both skills depend on

**CRITICAL**: No user story skill work can begin until this phase is complete

- [X] T005 Write `scripts/chrome-devtools-enable.sh` (mirroring the `defenseclaw-enable.sh` / `forward-enable.sh` convention): check Node.js 18+ is present, check a Chrome/Chromium binary is discoverable, create `$CHROME_DEVTOOLS_PROFILE_DIR` (default `~/.openclaw/chrome-devtools/profile`) if missing, append `CHROME_DEVTOOLS_PROFILE_DIR`, `CHROME_DEVTOOLS_HEADLESS` (default `true`), `CHROME_DEVTOOLS_CHANNEL` (default `stable`) to `.env` if not already set, and print both sign-in patterns (Pattern A: headed-on-host; Pattern B: remote-debugging SSH tunnel) from research.md R3 with the operator's actual profile path substituted in. Make the script executable.
- [X] T006 [P] Update `.env.example` with `CHROME_DEVTOOLS_PROFILE_DIR`, `CHROME_DEVTOOLS_HEADLESS`, `CHROME_DEVTOOLS_CHANNEL` — descriptions only, no values, noting these are non-secret configuration (no credential-bearing env var exists for this integration per FR-005)
- [X] T007 Create MCP server README in `mcp-servers/chrome-devtools-mcp/README.md` with: server overview (official Chrome DevTools team package, npm `chrome-devtools-mcp`, ~50+ tools upstream, subset used by NetClaw documented per contracts/mcp-tools.md), transport protocol (stdio via `npx -y chrome-devtools-mcp@latest`), environment variables table, least-privilege note (Constitution IX — this integration's only privilege is spawning/controlling a local Chrome process and reading/writing one designated profile directory; no API keys, no elevated host permissions), both sign-in patterns from research.md R3, and an explicit statement that this integration is read/observation-oriented (Research R8) — it is not a mechanism for submitting or committing configuration changes to network infrastructure.

**Checkpoint**: Foundation ready — MCP server registered and documented, setup script in place. Skill authoring can begin.

---

## Phase 3: User Story 1 — Verify a Generated Visualization Actually Renders (Priority: P1) 🎯 MVP

**Goal**: Skill that opens a NetClaw-generated visualization HTML file in a browser session, screenshots it, checks the console for errors, and optionally runs a Lighthouse audit — closing the manual "open the file yourself" QA gap.

**Independent Test**: Run the skill against a known-good visualization HTML file and confirm it returns `verdict: "rendered_clean"` with a screenshot artifact; run it against a deliberately broken HTML file (bad script `src`) and confirm it returns `verdict: "rendered_with_errors"` with the console error text included (quickstart.md verification steps 1-2).

### Implementation for User Story 1

- [X] T008 [US1] Create skill documentation in `workspace/skills/browser-viz-verify/SKILL.md` with YAML front matter (name: `browser-viz-verify`, description, `mcp_servers: [chrome-devtools-mcp]`, `tools_used`: navigate_page/new_page, wait_for, take_screenshot, list_console_messages, get_console_message, lighthouse_audit, close_page). Purpose section: closes the QA gap for generated visualization outputs (threejs-network-viz, canvas-network-viz, drawio-diagram, uml-diagram, markmap-viz). State plainly that this skill never touches an external site or the authenticated browser profile.
- [X] T009 [US1] Add core verify workflow section to `workspace/skills/browser-viz-verify/SKILL.md`: the step-by-step behavior from contracts/skill-interfaces.md's `browser-viz-verify` contract — verify `file_path` exists, open the file (headless, local file only), wait for the page to settle (bounded timeout), capture a screenshot, read console messages and classify clean vs. errored, close the page. Document the output shape (`verdict`, `screenshot_path`, `console_errors`).
- [X] T010 [US1] Add optional Lighthouse audit section to `workspace/skills/browser-viz-verify/SKILL.md`: the `run_audit` input flag, invocation of `lighthouse_audit`, and the `audit_summary` output field (FR-003).
- [X] T011 [US1] Add error-handling section to `workspace/skills/browser-viz-verify/SKILL.md` documenting the `file_not_found` and `timed_out` verdicts (Edge Cases; data-model.md `TargetPage.load_state`).
- [X] T012 [US1] Add an "Invoking from other skills" section to `workspace/skills/browser-viz-verify/SKILL.md` describing how `threejs-network-viz`, `canvas-network-viz`, `drawio-diagram`, `uml-diagram`, and `markmap-viz` should call this skill automatically right after generating an HTML output, to satisfy SC-001's under-30-seconds QA loop.

**Checkpoint**: User Story 1 complete and independently testable — this is the MVP deliverable.

---

## Phase 4: User Story 2 — Fill a Gap in an Existing Controller Skill (Priority: P2)

**Goal**: Skill that navigates an already-authenticated controller dashboard (via the persistent profile) and retrieves a GUI-only report or value that the vendor's REST API doesn't expose.

**Independent Test**: Against a controller dashboard the operator has manually signed into, ask for a specific GUI-only report (e.g., "get the bridge domain list from this ACI tenant page") and confirm the result is returned without NetClaw ever requesting credentials; against a dashboard with an expired/absent session, confirm a distinct `sign_in_required` status is returned instead of an empty or misleading result (quickstart.md verification steps 3-4).

### Implementation for User Story 2

- [X] T013 [US2] Create skill documentation in `workspace/skills/browser-gui-inspect/SKILL.md` with YAML front matter (name: `browser-gui-inspect`, description, `mcp_servers: [chrome-devtools-mcp]`, `tools_used` listing the "Tools Used by browser-gui-inspect" table from contracts/mcp-tools.md). Purpose section: controller-agnostic GUI augmentation, undocumented-API discovery, and general web-GUI automation — explicitly stated as read/observation-oriented, not a configuration-change mechanism (Research R8).
- [X] T014 [US2] Add controller-gap-fill workflow section to `workspace/skills/browser-gui-inspect/SKILL.md`: navigate to the operator-supplied `target` URL using the persistent profile, detect and distinctly report a `sign_in_required` state (FR-008) rather than proceeding, perform only read/filter/search/confirm actions to satisfy the operator's `intent`, capture screenshot/console/extracted text as requested, and return the result. Include the ACI APIC bridge-domain example from the Clarifications session as a worked example.
- [X] T015 [US2] Add a safety-scoping section to `workspace/skills/browser-gui-inspect/SKILL.md` documenting Research R8 verbatim in spirit: `click`/`fill_form`/`handle_dialog`/`upload_file` are for reading, filtering, searching, and confirming state only — never for submitting, applying, or committing a configuration change to network infrastructure. State plainly that any real config change belongs to the relevant API-based skill's baseline→apply→verify + ITSM-gated workflow (Constitution I/II/III/VIII), never to this skill.
- [X] T016 [US2] Add a headless/headed mode section to `workspace/skills/browser-gui-inspect/SKILL.md` documenting the `CHROME_DEVTOOLS_HEADLESS` flag (FR-015) and both sign-in patterns (A: headed-on-host; B: remote-debugging SSH tunnel via `--browserUrl`/`--autoConnect`) from research.md R3, cross-referencing `specs/048-chrome-devtools-browser-inspection/quickstart.md`.

**Checkpoint**: User Stories 1 AND 2 both work independently.

---

## Phase 5: User Story 3 — Discover an Undocumented Vendor API (Priority: P3)

**Goal**: Extend `browser-gui-inspect` with a network-request inspection workflow so a NetClaw contributor can identify the API endpoint(s) backing a vendor dashboard feature before writing a new API-based skill.

**Independent Test**: Load any authenticated dashboard page, trigger an action on it (e.g., a filter or refresh), and confirm the skill returns the list of network requests that action produced (method, URL, status), plus the full request/response detail for any one of them, in a single session (quickstart.md's Meraki dashboard example).

### Implementation for User Story 3

- [X] T017 [US3] Add an API-discovery workflow section to `workspace/skills/browser-gui-inspect/SKILL.md`: (1) navigate to the target dashboard page, (2) perform the operator-specified action that triggers the network activity of interest, (3) call `list_network_requests` to enumerate what was observed since the page loaded, (4) call `get_network_request` for full method/URL/status/request-response detail on a specific call of interest, (5) summarize the discovered endpoint and payload shape for use in a future API-based skill. Document the `capture: ["network_requests"]` input option from contracts/skill-interfaces.md.

**Checkpoint**: User Stories 1, 2, AND 3 all work independently.

---

## Phase 6: User Story 4 — General-Purpose Web GUI Automation (Priority: P4)

**Goal**: Extend `browser-gui-inspect` with a documented pattern for ad hoc navigation/reading/interaction against any browser-based tool with no existing NetClaw integration.

**Independent Test**: Point the skill at a web page unrelated to any existing NetClaw skill (e.g., a classic SDN controller GUI), describe what should be read or done, and confirm it performs the requested navigation/interaction and reports the resulting page state or extracted value (quickstart.md's ONOS GUI example).

### Implementation for User Story 4

- [X] T018 [US4] Add a general-purpose automation section to `workspace/skills/browser-gui-inspect/SKILL.md`: how to handle a free-form `intent` against an arbitrary `target` with no assumed page structure, using `take_snapshot`/`take_screenshot` to read page content and `evaluate_script` for read-only value extraction (never for submitting a change — reiterate T015's safety scoping). Include the classic SDN controller GUI (OpenDaylight/ONOS) and vendor support/TAC portal examples from spec.md's User Story 4.

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Artifact Coherence

**Purpose**: Artifact coherence checklist completion (Constitution XI) and cross-cutting documentation updates

- [X] T019 [P] Update `TOOLS.md` with a `chrome-devtools-mcp` entry: server name, brief description, the subset of tools used (navigation, input, network inspection, console/debugging, performance) per contracts/mcp-tools.md
- [X] T020 [P] Update `SOUL.md` with the `browser-viz-verify` and `browser-gui-inspect` skill definitions and a one-line capability summary for each
- [X] T021 [P] Update `README.md` with the `chrome-devtools-mcp` description, updated skill/MCP server counts, and an architecture reference
- [X] T022 [P] Update `scripts/install.sh` with `chrome-devtools-mcp` dependency notes (Node.js 18+, a Chrome/Chromium binary on the host) and a pointer to `scripts/chrome-devtools-enable.sh` for first-run setup
- [X] T023 [P] Update `ui/netclaw-visual/` Three.js HUD with a new node representing the `chrome-devtools-mcp` integration and its operational status
- [X] T024 Validate `specs/048-chrome-devtools-browser-inspection/quickstart.md` end-to-end: run the setup script, register the server, complete both sign-in patterns against a real target, and execute all 5 verification steps
- [X] T025 Verify backwards compatibility — confirm all existing MCP servers and skills remain functional after these additions (Constitution XV)
- [X] T026 Draft a WordPress blog post documenting this milestone (Constitution XVII) — submit to John for review before publishing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phases 3-6)**: All depend on Foundational phase completion
  - US1 (Phase 3): No dependencies on other stories — MVP target
  - US2 (Phase 4): Independent of US1 (different file section, different code path — external site + authenticated profile vs. local file)
  - US3 (Phase 5): Extends the same `browser-gui-inspect/SKILL.md` file as US2 — same skill, additive section; can start once T013 (skill file created) exists
  - US4 (Phase 6): Extends the same `browser-gui-inspect/SKILL.md` file as US2/US3 — same skill, additive section; can start once T013 exists
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **US1 (P1)**: Foundational only. MVP target. Fully independent — never touches the authenticated profile.
- **US2 (P2)**: Foundational only, plus T013 (creates the shared `browser-gui-inspect/SKILL.md` file). Independently testable.
- **US3 (P3)**: Foundational + T013. Additive section in the same file as US2 — sequenced after T013 but not functionally dependent on US2's content.
- **US4 (P4)**: Foundational + T013. Additive section in the same file as US2/US3 — sequenced after T013 but not functionally dependent on US2/US3's content.

### Within Each User Story

- Read existing skill content before extending (US2/US3/US4 share one file)
- Core workflow documentation before edge-case/safety-scoping documentation
- Story complete before moving to next priority

### Parallel Opportunities

- T001, T002, T003, T004 (Setup) can all run in parallel
- T006 (Foundational) can run in parallel with T005/T007 (different files)
- Once Foundational completes, US1 (Phase 3) can run fully in parallel with the start of US2 (Phase 4) — they touch different skill files
- US3 (T017) and US4 (T018) both depend on T013 existing but are otherwise independent additive sections — write sequentially to avoid edit conflicts in the same file, or hand off cleanly between them
- All Phase 7 tasks marked [P] can run in parallel

---

## Parallel Example: Phase 1 (Setup)

```bash
# All setup tasks are independent:
Task: "T001 Create mcp-servers/chrome-devtools-mcp/ directory"
Task: "T002 Create workspace/skills/browser-viz-verify/ directory"
Task: "T003 Create workspace/skills/browser-gui-inspect/ directory"
Task: "T004 Register chrome-devtools-mcp in config/openclaw.json"
```

## Parallel Example: Phase 7 (Polish)

```bash
# All documentation updates can run in parallel:
Task: "T019 Update TOOLS.md"
Task: "T020 Update SOUL.md"
Task: "T021 Update README.md"
Task: "T022 Update scripts/install.sh"
Task: "T023 Update ui/netclaw-visual/ HUD"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T007)
3. Complete Phase 3: User Story 1 (T008-T012)
4. **STOP and VALIDATE**: Run `browser-viz-verify` against a known-good and a known-broken visualization file; confirm both verdicts are correct
5. Deploy/demo if ready — this alone closes the visualization QA gap with zero external-site risk

### Incremental Delivery

1. Setup + Foundational → registration, setup script, and README ready
2. Add US1 (Verify visualizations) → Test → MVP!
3. Add US2 (Controller GUI gap-fill) → Test → real operational value against authenticated dashboards
4. Add US3 (Undocumented API discovery) → Test → contributor productivity tool
5. Add US4 (General GUI automation) → Test → broadest fallback capability
6. Phase 7 (Polish + Artifact Coherence) → feature complete

### Suggested MVP Scope

User Story 1 (`browser-viz-verify`) is the MVP. It delivers immediate, low-risk value — automated QA on every NetClaw-generated visualization — with no external site, no authentication, and no exposure to Constitution I/III's safety/ITSM concerns. Once validated, US2 unlocks the feature's primary operational value proposition (GUI gap-filling for controllers), and US3/US4 add developer-productivity and general-purpose fallback value on top of the same authenticated-session machinery.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- This is a configuration integration — no server code is authored by NetClaw; the official `chrome-devtools-mcp` package handles all tool implementation
- Node.js 18+ and a local Chrome/Chromium binary are required host dependencies
- No bespoke audit trail is added (relies on DefenseClaw's existing generic tool-call inspection/logging — Clarification Q3, research.md R5)
- No bespoke domain allowlist is added (relies on DefenseClaw's existing tool-allow/tool-block controls — Clarification Q2, research.md R4)
- `browser-gui-inspect`'s interactive tools (click/fill_form/handle_dialog) are documented as read/confirm/search-only — never a path for submitting configuration changes (research.md R8) — this is the one place this feature intersects Constitution I/III/VIII, and it's resolved by scope/documentation rather than new enforcement code
- US2, US3, and US4 all extend the same `workspace/skills/browser-gui-inspect/SKILL.md` file with additive sections — sequence T014/T015/T016 (US2) before T017 (US3) and T018 (US4) to avoid overlapping edits, even though the underlying capabilities are independent

## Post-Implementation Correction (same day)

T004's original registration hardcoded a single `--headless=true` at the daemon level, which technically satisfied "headless by default" but failed FR-015's actual requirement — "the requester" must be able to select headless or headed **per request**, not just at initial setup. A single fixed-flag daemon can't do that. Corrected by registering `chrome-devtools-mcp-visible` (`--headless=false`) as a second, independent MCP server alongside the original `chrome-devtools-mcp` (`--headless=true`), so `browser-gui-inspect` can choose which server's tools to call per request based on whether the operator asked to watch ("Watch Mode"). Both share the tool's default persistent profile. This is host-agnostic (plain `--headless=false`, no WSL/OS-specific code) — verified live with a real headed Chrome launch (`DISPLAY=:0`/WSLg present) alongside the existing headless validation. Updated: `config/openclaw.json`, `mcp-servers/chrome-devtools-mcp/README.md`, `workspace/skills/browser-gui-inspect/SKILL.md`, `quickstart.md`, `TOOLS.md`, `README.md`, `SOUL.md` (counts now 188 skills / 110 MCP integrations). Also deployed to the live NetClaw instance via `openclaw mcp set` ×2, skill files copied to the live workspace, `openclaw mcp reload`, and `openclaw gateway restart` — confirmed via `openclaw mcp status` and a new gateway pid.

## Post-Implementation Correction #2 (same day)

Deploying to the live instance surfaced a second, real gap: `--channel=stable` (the implicit default when no `--executablePath` is given) looks for Chrome at an OS-standard install path (`/opt/google/chrome/chrome` on Linux) — and this dev box had Node.js/npx but no Chrome there. The live agent itself hit this first (via Slack, mid-`browser-gui-inspect` request against the NetBox demo) and correctly refused to patch its own MCP registration args (a protected-path guardrail), surfacing two options to the operator instead. Fixed properly rather than as a one-off symlink: `scripts/chrome-devtools-enable.sh` now (1) looks for a system browser on `PATH` or the macOS app bundle, (2) if none exists, provisions one deterministically via `npx @puppeteer/browsers install chrome@stable --path ~/.cache/chrome-devtools-mcp/browsers` — the same cross-platform, Node-based installer Puppeteer itself uses, so it's identical on Linux, macOS, and WSL2 with no OS package manager and no sudo — and (3) registers both `chrome-devtools-mcp` and `chrome-devtools-mcp-visible` with an explicit `--executablePath`, so neither ever depends on `--channel`'s path guess again. `scripts/install.sh`'s existing Step 52b now delegates to this script so the fix applies automatically on every future install, not just this one. Updated: `scripts/chrome-devtools-enable.sh` (rewritten), `scripts/install.sh`, `mcp-servers/chrome-devtools-mcp/README.md`, `quickstart.md`. Verified idempotent by running the rewritten script twice against the live instance (provisioned once, re-registered cleanly the second time with identical values); live registrations patched via `openclaw mcp set`, `openclaw mcp reload`, `openclaw gateway restart` (confirmed via `openclaw mcp show chrome-devtools-mcp` and a new gateway pid) so the in-flight Slack request could be retried immediately.
