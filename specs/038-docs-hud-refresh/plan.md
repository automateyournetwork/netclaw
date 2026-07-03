# Implementation Plan: Documentation & HUD Refresh

**Branch**: `038-docs-hud-refresh` | **Date**: 2026-06-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/038-docs-hud-refresh/spec.md`

## Summary

Update all NetClaw documentation to reflect changes from PRs #031-#075. Primary updates include correcting skill counts (113→179), MCP server counts (67→43), and documenting new integrations (Checkpoint, Forward Networks, Claroty xDome, IP Fabric, Memory MCP, Nautobot, EVE-NG, HumanRail, Ollama MCP). This is a documentation-only feature with no code changes.

## Technical Context

**Language/Version**: Markdown (documentation files)
**Primary Dependencies**: N/A (pure documentation)
**Storage**: N/A
**Testing**: Manual verification of counts against codebase
**Target Platform**: GitHub repository documentation
**Project Type**: Documentation update
**Performance Goals**: N/A
**Constraints**: Must maintain consistency with actual codebase counts
**Scale/Scope**: 4 primary files, ~15 integration descriptions to add/update

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **XI. Full-Stack Artifact Coherence** | COMPLIANT | This feature specifically addresses artifact coherence debt from PRs #031-#075 |
| **XII. Documentation-as-Code** | COMPLIANT | Updates documentation to reflect current state |
| **X. Observability as First-Class** | COMPLIANT | Visual HUD updates included in scope |
| **XVI. Spec-Driven Development** | COMPLIANT | Following SDD workflow via speckit |

**Gate Status**: PASSED - No violations. This feature restores documentation alignment per Constitution Principle XI.

## Project Structure

### Documentation (this feature)

```text
specs/038-docs-hud-refresh/
├── plan.md              # This file
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output (below)
├── data-model.md        # N/A - documentation only
├── quickstart.md        # N/A - documentation only
├── contracts/           # N/A - documentation only
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Files to Update (repository root)

```text
README.md                           # Primary user-facing docs
ui/netclaw-visual/README.md         # Visual HUD documentation
CLAUDE.md                           # AI-readable context (auto-generated)
workspace/SOUL.md                   # Architecture documentation
```

**Structure Decision**: No new files created. This feature updates existing documentation files only.

## Complexity Tracking

No violations to justify - this is a documentation update that restores compliance with Constitution Principle XI.

---

## Phase 0: Research

### Verified Counts (from codebase)

| Metric | Old Value | New Value | Source |
|--------|-----------|-----------|--------|
| Skills | 113 | 179 | `find workspace/skills -maxdepth 1 -type d \| wc -l` |
| MCP Servers | 67 | 43 | `jq '.mcpServers \| keys \| length' config/openclaw.json` |

### New Integrations to Document

| PR | Integration | Tools/Capabilities | Status in README |
|----|-------------|-------------------|------------------|
| #065 | Checkpoint Security | 15 MCP servers (policy, threat intel, gateway, SASE, malware) | Partially documented |
| #068 | IP Fabric | Network assurance, intent verification | Not documented |
| #069 | Memory MCP | SQLite facts + ChromaDB embeddings | Partially documented |
| #070 | Layered Memory | MEMORY.md integration | Partially documented |
| #071 | Claroty xDome | 21 tools: OT/IoT asset inventory, topology, risk triage | Not documented |
| #072 | Forward Networks | Digital twin, NQE queries, path analysis | Not documented |
| #073 | Ollama MCP | Local LLM inference | Not documented |
| #060/#062 | EVE-NG | Lab management, node operations, topology | Not documented |
| #061 | HumanRail | Human-in-the-loop escalation | Not documented |
| #063 | Nautobot | 3 servers: core, golden-config, routing | Not documented |
| #059 | DefenseClaw/OpenShell | Security sandbox, guardrails | Already documented |

### MCP Servers in config/openclaw.json (43 total)

```
aruba-cx-mcp, atlassian-mcp, azure-network-mcp, batfish-mcp, blender-mcp,
chkp-argos-erm, chkp-cpinfo-analysis, chkp-documentation, chkp-gw-connection-analysis,
chkp-harmony-sase, chkp-https-inspection, chkp-management, chkp-management-logs,
chkp-policy-insights, chkp-quantum-gaia, chkp-quantum-gw-cli, chkp-reputation-service,
chkp-spark-management, chkp-threat-emulation, chkp-threat-prevention,
claroty-mcp, cloudflare-analytics, cloudflare-dns-analytics, cloudflare-security,
cloudflare-workers, cloudflare-zerotrust, datadog-mcp, devnet-content-search,
forward-mcp, gitlab-mcp, gnmi-mcp, gns3-mcp, jenkins-mcp,
nautobot-golden-config-mcp, nautobot-mcp, nautobot-routing-mcp, pagerduty-mcp,
prisma-sdwan-mcp, splunk-mcp, suzieq-mcp, terraform-mcp, vault-mcp, zscaler-mcp
```

### README Locations Requiring Updates

| Location | Current Text | Required Change |
|----------|-------------|-----------------|
| Line 7 (header paragraph) | "113 skills...67 MCP integrations" | "179 skills...43 MCP servers" |
| Line 19 (installer description) | "deploys 113 skills...67 MCP integrations" | "deploys 179 skills...43 MCP servers" |
| Line 96 (HUD section) | "48 integrations, 103 skills" | "43 MCP servers, 179 skills" |
| "What It Does" section | Missing several integrations | Add Forward, Claroty, EVE-NG, etc. |

---

## Phase 1: Design

### Update Strategy

Since this is a documentation-only feature, the "design" consists of the update sequence:

1. **README.md Updates** (P1 priority)
   - Update all numeric counts (skills, MCP servers)
   - Add missing integration descriptions to "What It Does" section
   - Verify all 43 MCP servers are represented in integration lists

2. **Visual HUD README Updates** (P2 priority)
   - Update counts in ui/netclaw-visual/README.md
   - Verify HUD feature descriptions are accurate

3. **SOUL.md Updates** (P3 priority)
   - Verify architecture patterns are current
   - Add any missing capability summaries

4. **CLAUDE.md Verification** (P3 priority)
   - CLAUDE.md is auto-generated from feature plans
   - Verify recent features are included via CLAUDE.md generation

### Data Model

N/A - This is a documentation update. No data model changes.

### Contracts

N/A - No external interfaces defined by this feature.

### Quickstart

N/A - No new functionality to quickstart.

---

## Constitution Re-Check (Post-Design)

| Principle | Status | Notes |
|-----------|--------|-------|
| **XI. Full-Stack Artifact Coherence** | WILL BE COMPLIANT | This feature directly addresses coherence debt |
| **XII. Documentation-as-Code** | WILL BE COMPLIANT | All docs updated in same PR as this feature |
| **XVII. Milestone Documentation** | CONSIDER | Blog post may be appropriate after merge |

**Gate Status**: PASSED - Ready for task generation.

---

## Next Steps

1. Run `/speckit.tasks` to generate actionable task list
2. Execute tasks to update documentation files
3. Verify all counts match codebase
4. Create PR for review
