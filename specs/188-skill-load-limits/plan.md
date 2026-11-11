# Implementation Plan: Skill Load and Prompt Limits

**Branch**: `188-skill-load-limits` | **Date**: 2026-11-11 | **Spec**: [spec.md](spec.md)
**Input**: GitHub issue #326

## Summary

OpenClaw loads at most 200 skills per source and injects at most 150 skills / 18,000 characters into the prompt; the workspace ships 240. NetClaw writes none of these limits. Plan: one policy file (`config/skill-limits.json`) is the source of truth; one stdlib library (`scripts/lib/skill_limits.py`) applies it raise-only to a config dict and measures the shipped skills; `install-mcp-config.py merge_config` applies it to the Border runtime config, `in2n-member-home.py spec_skills_section` applies it to freshly built member configs; a new `scripts/check-skill-limits.py` is wired into `scripts/reconcile-mcp.py` as the `skill-limits` surface (CI-run) and fails when the shipped skills exceed any configured limit. Chosen option: issue options 1 + 3 (2 already exists through the per-agent allowlist).

## Technical Context

**Language/Version**: Python 3.10+, stdlib only
**Primary Dependencies**: none new
**Storage**: files only (`config/skill-limits.json`; runtime `openclaw.json` edited in place by the existing atomic private writer)
**Testing**: pytest (`tests/skill_limits/`), plus `python3 scripts/reconcile-mcp.py --surface skill-limits`
**Target Platform**: macOS and Ubuntu/WSL installers; CI container
**Project Type**: installer/tooling scripts
**Performance Goals**: check completes in under 2 s (reads ~240 small files)
**Constraints**: raise-only; idempotent; no change to Hermes; read-only check
**Scale/Scope**: 240 skills today, 400 limit, 1.6x headroom

## Constitution Check

- I-X (device safety, ITSM, audit): not applicable, no device or network action.
- XI Artifact coherence: no new MCP/skill. Touch README only if skill counts appear (they do not change); docs updated (ADDING-AN-MCP.md, new section). PASS.
- XV Backwards compatibility: only adds `skills.limits` keys and raises numbers; never lowers, never removes keys; Hermes untouched. PASS.
- XVI Spec-driven: this spec. PASS. XIII credentials: none handled. PASS.

Post-design re-check: no violations.

## Project Structure

### Documentation
```text
specs/188-skill-load-limits/
  plan.md research.md data-model.md quickstart.md contracts/ tasks.md verification.md
```

### Source Code
```text
config/skill-limits.json                 # NEW policy (source of truth)
scripts/lib/skill_limits.py              # NEW shared logic (load, count, measure, raise_only, evaluate)
scripts/check-skill-limits.py            # NEW CLI check
scripts/reconcile-mcp.py                 # add "skill-limits" surface
scripts/install-mcp-config.py            # merge_config applies limits (OpenClaw only; caller already skips Hermes)
scripts/in2n-member-home.py              # spec_skills_section adds limits
.github/workflows/mcp-reconciliation.yml # path triggers for workspace/skills/** and the policy
docs/ADDING-AN-MCP.md                    # limits section, adjust not_loaded text
tests/skill_limits/                      # NEW tests
```

**Structure Decision**: single shared library imported by both writers and the check, so the three can never disagree.
