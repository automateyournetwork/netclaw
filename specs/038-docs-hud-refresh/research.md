# Research: Documentation & HUD Refresh

**Feature**: 038-docs-hud-refresh
**Date**: 2026-06-23

## Summary

This research consolidates the verified counts and integration details needed to update NetClaw documentation. All values have been validated against the codebase.

---

## Decision 1: Skill Count

**Decision**: 179 skills

**Rationale**: Verified by counting skill directories in `workspace/skills/`:
```bash
find workspace/skills -maxdepth 1 -type d | tail -n +2 | wc -l
# Result: 179
```

**Alternatives Considered**:
- Using 180 (includes SKILL-SCHEMA.md file) - Rejected: SKILL-SCHEMA.md is not a skill
- Counting SKILL.md files (176) - Rejected: Some skills may not have SKILL.md yet

---

## Decision 2: MCP Server Count

**Decision**: 43 MCP servers

**Rationale**: Verified by counting entries in `config/openclaw.json`:
```bash
jq '.mcpServers | keys | length' config/openclaw.json
# Result: 43
```

**Alternatives Considered**:
- Counting mcp-servers/ directories (51) - Rejected: Not all have corresponding openclaw.json entries
- Using old count of 67 - Rejected: Outdated, includes deprecated/removed servers

---

## Decision 3: Terminology Standardization

**Decision**: Use "179 skills and 43 MCP servers" consistently

**Rationale**:
- "skills" is the established term in NetClaw
- "MCP servers" is more accurate than "MCP integrations" since some integrations have multiple servers
- Aligns with technical reality of config/openclaw.json structure

**Alternatives Considered**:
- "MCP integrations" - Rejected: Ambiguous (could mean logical integrations vs actual servers)
- "67 MCP integrations" - Rejected: Old methodology, not verifiable from current config

---

## Decision 4: New Integrations Documentation Format

**Decision**: Add each new integration as a bullet point in "What It Does" section, following existing format

**Rationale**: Maintains consistency with existing documentation style. Each integration gets:
- Bold verb phrase (e.g., "**Analyze**", "**Monitor**")
- Platform name
- Tool count if significant
- Brief capability description

**Alternatives Considered**:
- Separate "New Integrations" section - Rejected: Fragments the capability list
- Detailed subsections per integration - Rejected: README is already long

---

## Integration Details for Documentation

### Forward Networks (PR #072)

**Capabilities to Document**:
- Digital twin network modeling
- NQE (Network Query Engine) queries
- Path analysis and verification
- Configuration compliance checking
- Network state snapshots

**Suggested Documentation**:
> **Analyze** network state via Forward Networks digital twin — NQE queries, path verification, configuration compliance, and network snapshots through the forward-mcp server

### Claroty xDome (PR #071)

**Capabilities to Document**:
- OT/IoT asset inventory with Purdue Model classification
- Device communication topology
- Alert and vulnerability triage
- ITSM-gated operations (alert acknowledgement, labeling, assignment)
- 21 tools total (15 read + 6 ITSM-gated writes)

**Suggested Documentation**:
> **Discover and protect** OT/IoT/IoMT environments via Claroty xDome (21 tools) — asset inventory with Purdue Model classification, device communication topology, alert and vulnerability triage, ITSM-gated alert management

### IP Fabric (PR #068)

**Capabilities to Document**:
- Network assurance and intent verification
- Topology visualization
- Path lookup and verification
- Configuration compliance

**Suggested Documentation**:
> **Verify** network intent via IP Fabric — topology discovery, path verification, configuration compliance, and network assurance through the ipfabric skills

### EVE-NG (PR #060/#062)

**Capabilities to Document**:
- Lab topology management
- Node operations (start, stop, configure)
- Console access
- Topology design and validation

**Suggested Documentation**:
> **Simulate** network topologies in EVE-NG — lab management, node operations, console access, topology design and validation via eve-ng skills

### HumanRail (PR #061)

**Capabilities to Document**:
- Human-in-the-loop escalation workflows
- Approval gates for critical operations
- Notification and response tracking

**Suggested Documentation**:
> **Escalate** critical decisions via HumanRail — human-in-the-loop approval workflows for operations requiring human judgment

### Nautobot (PR #063)

**Capabilities to Document**:
- Source of truth integration (nautobot-mcp)
- Golden configuration management (nautobot-golden-config-mcp)
- Routing data queries (nautobot-routing-mcp)

**Suggested Documentation**:
> **Query** Nautobot source of truth (3 MCP servers) — IPAM, DCIM, golden configurations, routing data, and inventory reconciliation

### Ollama MCP (PR #073)

**Capabilities to Document**:
- Local LLM inference
- Model management
- Privacy-preserving AI operations

**Suggested Documentation**:
> **Run** local AI inference via Ollama MCP — privacy-preserving local LLM operations without cloud API calls

---

## Visual HUD Updates Required

The Visual HUD documentation at `ui/netclaw-visual/README.md` references:
- "48 integrations" → Update to "43 MCP servers"
- "103 skills" → Update to "179 skills"

---

## NEEDS CLARIFICATION: Resolved

All unknowns have been resolved through codebase verification:
- ✅ Skill count verified: 179
- ✅ MCP server count verified: 43
- ✅ Terminology standardized
- ✅ Integration documentation format defined
- ✅ All new integrations researched

---

## Research Complete

Ready for Phase 1 design and task generation.
