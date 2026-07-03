# Implementation Plan: DefenseClaw Security Integration

**Branch**: `027-netshell-security` | **Date**: 2026-04-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/027-netshell-security/spec.md`

## Summary

Integrate Cisco DefenseClaw as the production security layer for NetClaw. DefenseClaw provides automated OpenShell sandbox setup, component scanning, CodeGuard static analysis, LLM inspection, runtime guardrails, and SIEM integration. The implementation removes the original NetShell artifacts and replaces them with DefenseClaw integration in install.sh, with hobby mode preserved as the no-security alternative.

## Technical Context

**Language/Version**: Bash (installation scripts), Python 3.10+ (DefenseClaw requires), Go 1.25+, Node.js 20+
**Primary Dependencies**: DefenseClaw (Cisco), Docker (container runtime)
**Storage**: SQLite (DefenseClaw audit logs), optional SIEM (Splunk HEC, OTLP)
**Testing**: Manual validation via defenseclaw CLI commands
**Target Platform**: Linux (primary), macOS (secondary)
**Project Type**: Integration/Configuration (no new code, configuration and script updates)
**Performance Goals**: Installation <5 minutes, scanning latency <2 seconds, guardrail latency <10ms
**Constraints**: Docker required for DefenseClaw, Python 3.10+/Go 1.25+/Node.js 20+ required
**Scale/Scope**: Single NetClaw installation, 71+ MCP servers

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS | DefenseClaw adds guardrails that block dangerous operations |
| II. Read-Before-Write | PASS | No device operations in this feature |
| III. ITSM-Gated Changes | PASS | No production device changes |
| IV. Immutable Audit Trail | PASS | DefenseClaw provides SQLite audit + SIEM integration |
| V. MCP-Native Integration | PASS | DefenseClaw integrates with OpenClaw, not custom protocol |
| VI. Multi-Vendor Neutrality | PASS | Security layer is vendor-agnostic |
| VII. Skill Modularity | PASS | No new skills created |
| VIII. Verify After Every Change | PASS | No device changes |
| IX. Security by Default | PASS | DefenseClaw IS the security enhancement |
| X. Observability as a First-Class Citizen | PASS | DefenseClaw provides audit logging and SIEM |
| XI. Full-Stack Artifact Coherence | PASS | Cleanup section ensures all artifacts updated |
| XII. Documentation-as-Code | PASS | README, SOUL.md, CLAUDE.md updates planned |
| XIII. Credential Safety | PASS | DefenseClaw injects credentials at runtime |
| XIV. Human-in-the-Loop | N/A | No external communications |
| XV. Backwards Compatibility | PASS | Hobby mode preserves current behavior |
| XVI. Spec-Driven Development | PASS | Following speckit workflow |
| XVII. Milestone Documentation | PENDING | WordPress blog post after implementation |

**Gate Status**: PASS - All applicable principles satisfied.

## Project Structure

### Documentation (this feature)

```text
specs/027-netshell-security/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (minimal - config only)
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (N/A - no external APIs)
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output
```

### Source Code (repository root)

```text
# Files to UPDATE:
scripts/
└── install.sh           # Replace NetShell section with DefenseClaw

config/
└── openclaw.json        # Update security config section

# Files to UPDATE (documentation):
README.md                # Update security section
SOUL.md                  # Update P18-P25 to reference DefenseClaw
CLAUDE.md                # Update NetShell section to DefenseClaw

# Files to CREATE:
scripts/
├── defenseclaw-enable.sh   # Enable DefenseClaw post-install
└── defenseclaw-disable.sh  # Disable DefenseClaw (revert to hobby)

# Files to REMOVE:
netshell/                # Entire directory (replaced by DefenseClaw)
├── README.md
├── policies/
│   ├── base.yaml
│   └── mcp/*.yaml (23 files)
└── scripts/*.py (6 files), *.sh (3 files)
```

**Structure Decision**: This is a configuration/integration feature. No new source code directories. Updates to existing scripts and documentation. Removal of netshell/ directory.

## Complexity Tracking

No violations requiring justification. This feature simplifies the codebase by replacing custom NetShell implementation with DefenseClaw.

---

## Phase 0: Research

### Research Tasks

1. **DefenseClaw Installation Process**: Verify exact installation commands and prerequisites
2. **DefenseClaw CLI Commands**: Document commands for scanning, tool management, guardrails
3. **Integration with OpenClaw**: Verify TypeScript plugin integration requirements
4. **SIEM Configuration**: Document Splunk HEC and OTLP setup

### Findings

See [research.md](./research.md) for detailed findings.

---

## Phase 1: Design

### Data Model

Minimal - see [data-model.md](./data-model.md) for configuration schema.

### Contracts

N/A - DefenseClaw provides its own API. NetClaw only integrates via install scripts.

### Quickstart

See [quickstart.md](./quickstart.md) for user-facing setup guide.

---

## Phase 2: Tasks

Generated by `/speckit.tasks` command.

---

## Next Steps

1. Run Phase 0 research to verify DefenseClaw integration details
2. Generate design artifacts (data-model.md, quickstart.md)
3. Run `/speckit.tasks` to generate task list
4. Run `/speckit.implement` to execute
