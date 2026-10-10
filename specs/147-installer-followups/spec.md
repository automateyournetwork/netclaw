# Feature Specification: Installer follow-ups

**Feature Branch**: `147-installer-followups`  
**Created**: 2026-10-10  
**Status**: Draft — waiting for the owner's installer failure details  
**Input**: Close spec 146 through PR/merge, then start a new spec for other installer problems. The owner will provide the reports separately.

## User Scenarios & Testing

### User Story 1 — Resolve a reported installation failure (Priority: P1)

An operator reports an installer failure. Capture enough sanitized evidence to reproduce it, identify the responsible stage, and define the expected successful behavior before choosing a fix.

**Independent test**: Each accepted report receives a reproduction that fails on the recorded baseline and passes after its scoped fix.

**Acceptance scenarios**:

1. Given a new report, when triage is complete, its command, affected component/stage, expected behavior, actual error and known host/runtime versions are recorded; missing facts remain explicitly unknown.
2. Given a confirmed repository defect, when its fix is accepted, a meaningful regression reproduces the original failure and verifies the corrected result.
3. Given an issue already addressed by an existing PR, when the reports are compared, this spec links and coordinates that work instead of independently duplicating it.

### Edge cases to assess against actual reports

- Fresh installs versus reruns with existing runtime configuration and credentials.
- Unsupported host or interpreter versus a repository defect.
- Partial installs or failed dependencies followed by misleading success.
- Issues already fixed in main or covered by pending installer work.

These are triage considerations, not claims that new defects have been found.

## Requirements

- **FR-001**: Record each supplied failure and its evidence in this spec before implementation.
- **FR-002**: Keep observed failures, hypotheses, upstream limitations and existing fixes distinct.
- **FR-003**: Define the affected platforms/components and acceptance criteria per confirmed issue; preserve unrelated operator configuration and the spec 146 dotenv behavior.
- **FR-004**: Use isolated temporary homes/runtimes and dummy credentials for reproduction where possible. Keep credentials, private topology and private logs out of repository artifacts.
- **FR-005**: Update research, plan and tasks with the selected solution before implementation; report relevant verification and untested host/live boundaries honestly.

## Success Criteria

- Every accepted fix has a traceable report, baseline, expected behavior and regression evidence.
- Relevant installer regressions and repository checks pass without weakening assertions.
- Existing credentials and unrelated runtime configuration remain intact.
- Source release metadata advances once only when this spec's eventual fix scope is completed; this draft does not advance the version.

## Assumptions and scope boundary

No new failure details have been supplied yet. The owner explicitly said they will send them for this spec. This draft authorizes intake and planning, not an invented installer rewrite or speculative package/runtime changes.

Spec 146 is the preceding dotenv/onboarding fix. PR #287 separately proposes host preflight and Zabbix repairs; its status must be rechecked when reports arrive. No merge of that PR is part of this draft.
