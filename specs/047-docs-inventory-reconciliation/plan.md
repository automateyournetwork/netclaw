# Implementation Plan: Documentation Inventory Reconciliation

**Branch**: `047-docs-inventory-reconciliation` | **Date**: 2026-07-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/047-docs-inventory-reconciliation/spec.md`

## Summary

NetClaw's skill/MCP integration counts have drifted into four disagreeing numbers in README.md alone (plus two more in SOUL.md), and the README's own inventory tables are incomplete enough that an external reviewer wrongly concluded Azure, Batfish, GitLab, and NetFlow/IPFIX support were missing when all four already ship. This plan produces (1) a small, dependency-free Python script (`scripts/verify-inventory-counts.py`) that computes the true skill count from `workspace/skills/` and the true MCP integration count from `config/openclaw.json` (expanding bundled multi-server packages) plus a maintained list of externally-installed servers with no local footprint, and (2) a documentation edit pass across README.md, SOUL.md, SOUL-SKILLS.md, mcp-servers/README.md, and ui/netclaw-visual/README.md that brings every count and every inventory table in line with the script's output. Spec 038-docs-hud-refresh is referenced as superseded prior art. No new skills, MCP servers, or product code are introduced — this is documentation and a verification script only.

## Technical Context

**Language/Version**: Python 3.10+ (matches every other script in `scripts/`, e.g. `scan-all-mcp-source.py`, `register-all-mcps.py`)
**Primary Dependencies**: None beyond the Python standard library (`os`, `json`, `re`) — no new third-party packages
**Storage**: N/A (reads existing `workspace/skills/` directory tree and `config/openclaw.json`; writes no persistent state)
**Testing**: Manual verification — run the script before and after adding a throwaway skill directory / config entry and confirm the count changes (per spec.md User Story 3 acceptance scenarios); no existing pytest suite covers documentation tooling, so a lightweight `if __name__ == "__main__"` self-check is sufficient rather than a new test framework dependency
**Target Platform**: Linux/macOS dev environment (same as all other `scripts/*.py` maintenance tools; not deployed, not part of the runtime agent)
**Project Type**: Single-file CLI utility script + documentation edits (no service, no UI, no MCP server)
**Performance Goals**: N/A (runs once, on-demand, against a few hundred local files — sub-second execution)
**Constraints**: Script MUST NOT require network access, credentials, or any `.env` values (it reads only local repo files) so it can run in CI or a fresh checkout with zero setup
**Scale/Scope**: 186 skill directories with a `SKILL.md` (190 raw entries under `workspace/skills/`, 3 empty stub directories and 1 schema file excluded), 108 individually-counted MCP integrations (49 `config/openclaw.json` entries, already including all 15 Check Point `chkp-*` servers individually — no bundle expansion needed — plus 59 externally-installed servers documented in README prose or vendored under `mcp-servers/` but absent from `config/openclaw.json`) — five documentation files to reconcile

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle XII (Documentation-as-Code)** — directly on point: "README.md MUST accurately reflect the current count and state of all skills, MCP servers, and supported platforms." This entire feature exists to restore compliance with this principle. PASS (this feature is the remediation, not a new risk).
- **Principle XVI (Spec-Driven Development)** — followed: spec.md exists and is ratified before this plan; no ad-hoc doc edits. PASS.
- **Principle XI (Full-Stack Artifact Coherence)** — does not apply in the forward direction (no new MCP server or skill is being added), but its spirit is what this feature restores retroactively across artifacts that fell out of sync after specs 039–046 shipped without doc updates. PASS.
- **Principle V (MCP-Native Integration)** — not applicable; no new MCP server is built. The verification script is a plain CLI utility, matching the existing precedent of `scripts/scan-all-mcp-source.py` and `scripts/register-all-mcps.py`, which are also plain scripts, not MCP servers. PASS.
- **Principle XIII (Credential Safety)** — the script reads only local files (`workspace/skills/`, `config/openclaw.json`) and needs no credentials or `.env` values. PASS.
- **Principle XVII (Milestone Documentation via WordPress)** — this is a documentation-accuracy fix rather than a new capability milestone; a blog post is not required, but will be offered to the user as optional per the principle's spirit once the fix ships.
- No forbidden operations, no device-facing changes, no destructive commands involved.

No violations identified. Complexity Tracking table is not needed.

## Project Structure

### Documentation (this feature)

```text
specs/047-docs-inventory-reconciliation/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
scripts/
└── verify-inventory-counts.py    # NEW — computes ground-truth skill count
                                    #  (workspace/skills/ directory count) and
                                    #  MCP integration count (config/openclaw.json
                                    #  entries, expanded for bundled packages like
                                    #  Check Point, plus a maintained list of
                                    #  externally-installed servers with no local
                                    #  config/vendored footprint). Prints a report
                                    #  and exits non-zero if documented counts
                                    #  (parsed from README.md/SOUL.md) disagree.

README.md                          # EDIT — reconcile all count mentions + fill
                                    #  MCP Servers / Skills table gaps
SOUL.md                            # EDIT — reconcile count mentions
SOUL-SKILLS.md                     # EDIT — verify full skill listing, no count claim drift
mcp-servers/README.md              # EDIT — list all vendored servers, not a subset
ui/netclaw-visual/README.md        # EDIT — reconcile HUD description text only
                                    #  (ui/netclaw-visual/server.js itself is NOT
                                    #  changed — it already computes counts live)

specs/047-docs-inventory-reconciliation/
└── data-model.md                  # Documents the "Skill" and "MCP Integration"
                                    #  counting entities/rules (no runtime data model
                                    #  exists for this doc-only feature)
```

**Structure Decision**: This is a documentation-and-tooling-only feature — no new service, MCP server, or skill is created. The only new source artifact is one standalone CLI script under `scripts/`, matching the existing convention of plain maintenance scripts in that directory (`scan-all-mcp-source.py`, `register-all-mcps.py`). All other changes are edits to existing documentation files. No `tests/` directory changes are needed; the script is self-verifying (documented in quickstart.md) rather than covered by the existing pytest suite, since it has no product-code dependency to unit test against.

## Complexity Tracking

*No Constitution Check violations were identified. This table is not needed.*
