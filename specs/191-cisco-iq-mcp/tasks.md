# Tasks: Cisco IQ Remote MCP Integration

**Input**: specs/191-cisco-iq-mcp/ (spec, plan, research, data-model, contracts, quickstart)
**Tests**: requested by spec (US4, FR-012); written alongside each story.

## Phase 1: Setup

- [X] T001 Create `tests/cisco-iq/` with `run-tests.sh` skeleton and `mock_server.py` (loopback Streamable HTTP mock: 401 on bad bearer, JSON-RPC initialize/tools/list, SSE variant, zero-tools variant)
- [X] T002 [P] Create `config/cisco-iq-policy.json` (deny-by-default, read_only, empty allow, deny_patterns) validated against `specs/191-cisco-iq-mcp/contracts/policy.schema.json`

## Phase 2: Foundational (blocks all stories)

- [X] T003 Create `scripts/cisco_iq.py` core: REGIONS table, region validation, `redact()`, argv secret-flag rejection, dotenv read/atomic private write (0600, symlink/newline refusal, backups with digest journal), openclaw.json load/save atomic with container detection
- [X] T004 [P] Create `scripts/cisco-iq-enable.sh` logic-free wrapper dispatching to `scripts/cisco_iq.py`

## Phase 3: US1 Connect in my region (P1)

**Independent test**: enable with dummy key, each region, fixture home.
- [X] T005 [US1] Implement `enable` and `status` (dry-run preview, idempotent, no-echo key prompt/stdin) in `scripts/cisco_iq.py`
- [X] T006 [P] [US1] Tests `tests/cisco-iq/test_enable.py`: three regions, missing/unknown region, no inference, header template literal, canary key absent from stdout/stderr/files other than .env, 0600, idempotence, argv key rejected

## Phase 4: US2 Operate without an AI (P1)

**Independent test**: diagnose/rotate/update/disable against fixture + mock.
- [X] T007 [US2] Implement `diagnose` (offline + `--live` initialize/tools/list, findings enum, `--endpoint-override` for loopback tests), `rotate`, `update`, `disable [--purge-credential]`
- [X] T008 [P] [US2] Tests `tests/cisco-iq/test_operate.py`: every finding status, rotate only changes key and keeps backup, update region switch, disable/purge/no-op rerun, redaction of 401 bodies and headers

## Phase 5: US3 Safe agent use (P2)

- [X] T009 [US3] Implement `policy-check` (allowed/denied/unlisted classification, DefenseClaw block commands) in `scripts/cisco_iq.py`
- [X] T010 [P] [US3] Write `workspace/skills/cisco-iq/SKILL.md` (assets, lifecycle/coverage, bugs, investigation correlation; discovery-first; no invented tool names; limits)
- [X] T011 [P] [US3] Tests `tests/cisco-iq/test_policy_docs.py`: policy schema, deny of mutating names, skill contains required disclaimers and no hardcoded tool names, docs/skill/catalog endpoint table equals code table

## Phase 6: US4 Offline validation and coherence (P2)

- [X] T012 [US4] Finish `tests/cisco-iq/run-tests.sh`; declare suite `cisco-iq` in `tests/contract-suites.json`; confirm `python3 scripts/run-contract-tests.py --suite cisco-iq` passes
- [X] T013 [US4] Catalog and installer: `scripts/lib/catalog.sh` entry, `component_install_cisco_iq()` in `scripts/lib/install-steps.sh`, `config/components/catalog.json` entry (access mode, settings CISCO_IQ_API_KEY secret / CISCO_IQ_REGION), `EXTERNAL_INTEGRATIONS` in `scripts/verify-inventory-counts.py`, coverage alias if required
- [X] T014 [P] [US4] Docs: `docs/CISCO-IQ.md`, README (description, counts), SOUL.md (summary, counts), TOOLS.md, `.env.example`, HUD `ui/netclaw-visual/env-map.js` card

## Phase 7: Polish

- [X] T015 Run `python3 scripts/reconcile-mcp.py` (read exit code directly), `scripts/verify-spec-artifacts.py`, inventory/catalog verifiers; compare failures against main baseline
- [X] T016 Write `specs/191-cisco-iq-mcp/verification.md` with real results and the not-verified list
- [X] T017 Commit logically, push, open PR with `Refs #346`

## Dependencies
T001-T004 -> US1 -> US2 -> US3; US4 tasks T012-T014 after US1-US3 code. T002, T004, T006, T008, T010, T011, T014 parallel with neighbours (different files).

## Strategy
MVP = US1 (enable/status + tests); then US2; then policy/skill; then coherence surfaces.
