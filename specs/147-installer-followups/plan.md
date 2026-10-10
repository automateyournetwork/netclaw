# Plan: Installer follow-ups

**Branch**: `147-installer-followups`  
**Date**: 2026-10-10  
**Spec**: [spec.md](spec.md)  
**Status**: Intake draft; technical design awaits the failure reports.

Follow the checked-in Spec Kit workflow manually: specify, clarify, research/plan, tasks, analyze, implement and verify. The slash-command integration is unavailable in this session.

## Technical context

Existing entry points are `scripts/install.sh` and `scripts/setup.sh`; shared orchestration is in `scripts/lib/`. Installer helpers use Bash and Python. Existing unit and installer contract suites provide isolated reproduction infrastructure. Affected host, component, dependency and runtime versions remain unknown.

## Sequence

1. Capture each owner-supplied report and compare it with merged spec 146 and pending PR #287.
2. Reproduce confirmed failures on an isolated baseline; record assumptions and missing evidence.
3. Define the smallest affected implementation surface and expected before/after behavior.
4. Amend this plan and its tasks before editing runtime code.
5. Implement and verify agreed fixes with appropriate regressions, update operator documentation, and prepare patch release metadata after completion.

## Constitution check

Preserve credentials and operator state; no provider calls, daemon operations, device configuration or system package installs are needed for draft intake. No new MCP/skill/HUD capability is proposed. Reassess artifact coherence after the concrete scope is known. No version bump for this draft.
