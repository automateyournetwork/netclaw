# Tasks: Skill Load and Prompt Limits

**Input**: `/specs/188-skill-load-limits/` (plan.md, spec.md, research.md, data-model.md, contracts/)
Tests are included: the issue requires an automated check and the task requires tests actually run.

## Phase 1: Setup

- [X] T001 Create `tests/skill-limits/` with `conftest.py` that puts `scripts/lib` on `sys.path` and provides a helper building a synthetic skills dir (N skill dirs with SKILL.md frontmatter)

## Phase 2: Foundational (blocks all stories)

- [X] T002 Create `scripts/lib/skill_limits.py` (stdlib only): `load_policy`, `shipped_skills`, `measure_prompt_chars`, `raise_limits`, `evaluate`, per contracts/skill-limits-cli.md and research.md R3/R4
- [X] T003 Create `config/skill-limits.json` with limits 400/400/400 and a prompt-char budget computed from the measurement (rounded up to 1000, 1.25x headroom), plus measurement constants and warnAtFraction
- [X] T004 [P] Unit tests for policy validation, shipped_skills, measurement and `raise_limits` (raise-only, preserves operator higher values and sibling keys, replaces invalid values, idempotent, bool rejected) in `tests/skill-limits/test_skill_limits_lib.py`

## Phase 3: User Story 1 - Border loads every shipped skill (P1)

**Independent test**: merge_config on empty and populated configs yields limits.

- [X] T005 [US1] Apply `raise_limits` to the config in `merge_config` in `scripts/install-mcp-config.py` before serialising (loading the lib via the existing `load_helper` pattern); keep mcp registrations behaviour unchanged
- [X] T006 [US1] Tests in `tests/skill-limits/test_border_config.py`: fresh config, operator higher value kept, lower raised, unrelated keys and `skills.entries` untouched, `mcpServers` layout, second run is a no-op (no new backup file)
- [X] T007 [US1] Verify Hermes path never reaches `merge_config` (read `scripts/lib/install-steps.sh core_deploy`; assert in a test that the `--config` call is only in the non-Hermes branch)

## Phase 4: User Story 2 - prompt limits cover all skills (P1)

- [X] T008 [US2] Ensure policy prompt count and char budget cover the shipped set (verify via `evaluate`) and tests in `tests/skill-limits/test_prompt_limits.py` for count and char overflow findings naming the limit and the overage

## Phase 5: User Story 3 - Members (P2)

- [X] T009 [US3] In `scripts/in2n-member-home.py` make `spec_skills_section` include `limits` from the policy (loaded from `config/skill-limits.json`); keep other behaviour
- [X] T010 [US3] Tests in `tests/skill-limits/test_member_config.py`: spec member config has limits; existing member tests still pass (`tests/n2n/test_member_spec_184.py`, `test_member_spec_providers_186.py`)

## Phase 6: User Story 4 - Drift check (P2)

- [X] T011 [US4] Create `scripts/check-skill-limits.py` per contract (exit 0/1/2, `--warn-only`, `--json`, `--skills-dir`, `--policy`)
- [X] T012 [US4] Register `skill-limits` surface in `scripts/reconcile-mcp.py` (SURFACES map, `--warn-only` forwarding list, `skill-limits:` prefix in `extract_findings`)
- [X] T013 [US4] Tests in `tests/skill-limits/test_check_cli.py`: repo passes; synthetic 401-skill dir fails naming the load limit; warn threshold; invalid policy exits 2
- [X] T014 [US4] Add path triggers (`config/skill-limits.json`, `workspace/skills/**`, `scripts/check-skill-limits.py`, `scripts/lib/skill_limits.py`) to `.github/workflows/mcp-reconciliation.yml`

## Phase 7: Polish

- [X] T015 [P] Update `docs/ADDING-AN-MCP.md` (limits section, new-skill step: run the check, fix the `not_loaded` 200 default text) and mention in `docs/N2N-RISK.md` if it describes the 200 default
- [X] T016 Run `python3 -m pytest tests/skill-limits tests/n2n/test_member_spec_184.py tests/n2n/test_member_spec_providers_186.py -q` and `python3 scripts/reconcile-mcp.py` (exit code directly), compare with pre-existing failures
- [X] T017 Write `specs/188-skill-load-limits/verification.md` with real results and what was not verified (real OpenClaw load behaviour)

## Dependencies
T001 -> T002/T003 -> T004. US1, US2, US3, US4 each depend only on Phase 2; US4 (T011) is independent of US1/US3. T016-T017 last.

## Parallel
T004 with T005-prep; T009 with T011; T015 anytime after T003.

## Strategy
MVP: Phase 1-3 (Border limits). Then US4 (guardrail), US2/US3, polish.
