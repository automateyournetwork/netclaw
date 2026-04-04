# Implementation Plan: Terraform MCP Server Integration

**Branch**: `018-terraform-mcp-server` | **Date**: 2026-04-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/018-terraform-mcp-server/spec.md`

## Summary

Integrate the official HashiCorp Terraform MCP server to provide Infrastructure as Code (IaC) capabilities within NetClaw. This is a community MCP server integration following the established pattern (clone → register → skills → documentation). The server provides 15+ tools across Registry, Operations, and HCP Terraform toolsets, all enabled for maximum functionality.

## Technical Context

**Language/Version**: Go (official HashiCorp Terraform MCP server)
**Primary Dependencies**: terraform-mcp-server (official), Terraform CLI, HCP Terraform API
**Storage**: N/A (stateless proxy to Terraform APIs and local CLI)
**Testing**: Manual verification via quickstart.md scenarios
**Target Platform**: Linux/macOS (OpenClaw runtime)
**Project Type**: MCP server integration (community server + NetClaw skills)
**Performance Goals**: N/A (API proxy, latency dependent on Terraform operations)
**Constraints**: Requires TFE_TOKEN for HCP Terraform features
**Scale/Scope**: 15+ tools, 3 skills, 1 MCP server registration

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| V. MCP-Native Integration | ✅ PASS | Official HashiCorp MCP server |
| VII. Skill Modularity | ✅ PASS | 3 focused skills (registry, workspaces, operations) |
| XI. Full-Stack Artifact Coherence | ⏳ PENDING | Will update all artifacts |
| XII. Documentation-as-Code | ⏳ PENDING | SKILL.md files to be created |
| XIII. Credential Safety | ✅ PASS | Token via TFE_TOKEN env var |
| XVI. Spec-Driven Development | ✅ PASS | Following SDD workflow |
| XVII. Milestone Documentation | ⏳ PENDING | Blog post after implementation |

**Gate Status**: PASS - No violations requiring justification

## Project Structure

### Documentation (this feature)

```text
specs/018-terraform-mcp-server/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   └── terraform-tools.md
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code (repository root)

```text
# Community MCP server (installed via go install or binary)
# No local server code - uses official terraform-mcp-server binary

# NetClaw skills
workspace/skills/
├── terraform-registry/SKILL.md
├── terraform-workspaces/SKILL.md
└── terraform-operations/SKILL.md

# Configuration updates
config/openclaw.json          # MCP server registration
.env.example                  # Environment variables
scripts/install.sh            # Installation instructions
README.md                     # Architecture and counts
SOUL.md                       # Skill index update
ui/netclaw-visual/server.js   # UI integration catalog
```

**Structure Decision**: Community MCP server pattern - no local server code, skills only. The official terraform-mcp-server binary is used directly.

## Complexity Tracking

> No violations requiring justification - standard community MCP integration pattern.
