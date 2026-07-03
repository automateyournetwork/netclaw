# Feature Specification: Documentation & HUD Refresh

**Feature Branch**: `038-docs-hud-refresh`
**Created**: 2026-06-23
**Status**: Draft
**Input**: User description: "Update NetClaw documentation (README, HUD, SOUL files) to reflect all changes since PR #031 through PR #075. The README currently mentions 113 skills and 67 MCP integrations but there are now 179 skills and 43 MCP servers. New features include: Forward MCP (#72), Claroty xDome (#71), Memory MCP (#69), Layered Memory (#70), IP Fabric (#68), Checkpoint (#65), Ollama MCP (#73), EVE-NG (#60, #62), Nautobot (#63), HumanRail (#61), and DefenseClaw/OpenShell security (#59). Update skill counts, integration lists, feature descriptions, and ensure Visual HUD references are accurate."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Skill Count Display (Priority: P1)

As a user viewing the NetClaw README or HUD, I want to see accurate counts of available skills and MCP integrations so that I understand the full capabilities of the platform.

**Why this priority**: The skill count is prominently displayed and currently shows 113 skills when 179 exist. This is the most visible inaccuracy and affects first impressions.

**Independent Test**: Can be fully tested by counting skills in the codebase and comparing against documented counts. Delivers immediate accuracy improvement.

**Acceptance Scenarios**:

1. **Given** the README displays skill counts, **When** a user views the README, **Then** the displayed count matches the actual number of skills in the codebase (179 skills).
2. **Given** the Visual HUD displays integration counts, **When** a user views the HUD, **Then** the MCP integration count reflects all currently supported servers.

---

### User Story 2 - Complete MCP Integration List (Priority: P1)

As a network engineer evaluating NetClaw, I want to see a complete list of MCP integrations so that I can determine if my infrastructure tools are supported.

**Why this priority**: MCP integrations are a core value proposition. Missing integrations from documentation may cause users to overlook key capabilities.

**Independent Test**: Can be tested by comparing documented MCP servers against `openclaw.json` configuration and mcp-servers directory.

**Acceptance Scenarios**:

1. **Given** the README lists MCP integrations, **When** reviewing the list, **Then** all integrations from PR #031-#075 are included (Checkpoint, IP Fabric, Memory MCP, Claroty xDome, Forward MCP, Ollama MCP, etc.).
2. **Given** a user searches for a specific integration (e.g., Forward Networks), **When** they search the README, **Then** the integration is listed with accurate description.

---

### User Story 3 - Updated Feature Descriptions (Priority: P2)

As a prospective user, I want feature descriptions that reflect current capabilities so that I can make informed decisions about adopting NetClaw.

**Why this priority**: Accurate feature descriptions build trust and help users understand what they're getting. Less urgent than counts but important for credibility.

**Independent Test**: Can be tested by reviewing each feature section and comparing against actual implementation.

**Acceptance Scenarios**:

1. **Given** the README describes Layered Memory, **When** a user reads the description, **Then** it accurately reflects the Memory MCP implementation from PR #033-#034.
2. **Given** the README describes security features, **When** a user reads about DefenseClaw, **Then** the description matches current capabilities.

---

### User Story 4 - Consistent Visual HUD References (Priority: P2)

As a user navigating NetClaw documentation, I want Visual HUD references to accurately describe the current UI so that I'm not confused by outdated screenshots or descriptions.

**Why this priority**: Visual inconsistencies cause confusion. Important but less critical than core feature documentation.

**Independent Test**: Can be tested by comparing HUD documentation against actual HUD display.

**Acceptance Scenarios**:

1. **Given** documentation references the Visual HUD, **When** a user follows the reference, **Then** the description matches current HUD appearance and capabilities.

---

### User Story 5 - Updated SOUL Files (Priority: P3)

As a contributor or advanced user, I want SOUL files to reflect current architecture and patterns so that I understand how the system works.

**Why this priority**: SOUL files are primarily for contributors and advanced users. Less visible but important for long-term maintenance.

**Independent Test**: Can be tested by reviewing SOUL files against current codebase patterns.

**Acceptance Scenarios**:

1. **Given** SOUL.md describes project architecture, **When** a contributor reads it, **Then** it accurately reflects current patterns and technologies.

---

### Edge Cases

- What happens when new PRs are merged during documentation update? Document the current state with a timestamp.
- How to handle deprecated features? Mark clearly as deprecated rather than removing.
- What about features in development? Note as "coming soon" or exclude until merged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: README MUST display accurate skill count (179 skills as of 2026-06-23)
- **FR-002**: README MUST display accurate MCP integration count (43 MCP servers as of 2026-06-23)
- **FR-003**: README MUST list all MCP integrations added in PRs #031-#075
- **FR-004**: MCP integration list MUST include: Checkpoint (15 MCP servers: argos-erm, cpinfo-analysis, documentation, gw-connection-analysis, harmony-sase, https-inspection, management, management-logs, policy-insights, quantum-gaia, quantum-gw-cli, reputation-service, spark-management, threat-emulation, threat-prevention), IP Fabric (skills only), Memory MCP (native, #069), Claroty xDome (#071), Forward Networks (#072), Ollama MCP (#073), EVE-NG (#060/#062), Nautobot (#063 - nautobot-mcp, nautobot-golden-config-mcp, nautobot-routing-mcp), HumanRail (#061), Prisma SD-WAN, GNS3, DevNet Content Search
- **FR-005**: Feature descriptions MUST match current implementation capabilities
- **FR-006**: Visual HUD references MUST accurately describe current HUD appearance
- **FR-007**: SOUL.md MUST reflect current architecture patterns
- **FR-008**: CLAUDE.md MUST include recent feature additions from PRs #031-#075
- **FR-009**: All documentation MUST use consistent terminology and naming

### Key Entities

- **README.md**: Primary user-facing documentation with skill counts, feature lists, and getting started guide
- **SOUL.md/SOUL Files**: Architecture and design philosophy documentation
- **CLAUDE.md**: AI-readable project context and guidelines
- **Visual HUD**: OpenClaw's visual display interface for NetClaw capabilities
- **openclaw.json**: Configuration file containing MCP server definitions (source of truth for integrations)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Skill count in README matches actual codebase count (179 skills)
- **SC-002**: MCP integration count in README matches servers defined in openclaw.json (43 servers)
- **SC-003**: 100% of MCP integrations from PRs #031-#075 are documented in README
- **SC-004**: All feature descriptions reviewed and updated where inaccurate
- **SC-005**: No outdated references to previous skill/integration counts (113, 67, 103, 48) remain
- **SC-006**: SOUL files updated to reflect current architecture
- **SC-007**: Visual HUD documentation reflects accurate integration and skill counts

## Assumptions

- The skill count of 179 has been verified by counting directories in `workspace/skills/`
- The MCP server count of 43 has been verified from `config/openclaw.json`
- PR #031 (Checkpoint) through PR #075 represents the scope of undocumented changes
- The Visual HUD documentation exists and needs updating (not a complete rewrite)
- SOUL files exist and have a defined structure to follow
- No new PRs will be merged during this documentation update that significantly change counts
- The `config/openclaw.json` file in the repository represents the canonical MCP integration list
- README currently shows outdated counts: "113 skills", "67 MCP integrations", "48 integrations" (HUD section), "103 skills" (HUD section)

## Scope - Files to Update

### Primary Files

| File | Current State | Required Updates |
|------|---------------|------------------|
| `README.md` | Shows "113 skills", "67 MCP integrations", "48 integrations", "103 skills" | Update all counts to 179 skills, 43 MCP servers; add missing integrations |
| `ui/netclaw-visual/README.md` | Visual HUD documentation | Update skill/integration counts, verify accuracy |
| `CLAUDE.md` | Auto-generated from feature plans | Verify all recent features included |
| `workspace/SOUL.md` | Architecture documentation | Verify current patterns are documented |

### PRs to Document (Undocumented Changes)

| PR # | Feature | Documentation Needed |
|------|---------|---------------------|
| #065 | Checkpoint MCP (15 servers) | Add to MCP list, describe capabilities |
| #068 | IP Fabric MCP | Add skills documentation, verify in feature list |
| #069 | Memory MCP | Already partially documented, verify completeness |
| #070 | Layered Memory Integration | Verify MEMORY.md integration documented |
| #071 | Claroty xDome (21 tools) | Add to MCP list, describe OT/IoT capabilities |
| #072 | Forward Networks MCP | Add to MCP list, describe NQE and digital twin features |
| #073 | Ollama MCP | Add to MCP list, describe local LLM capabilities |
| #060/#062 | EVE-NG Skills | Add EVE-NG lab management capabilities |
| #061 | HumanRail MCP | Add human-in-the-loop escalation documentation |
| #063 | Nautobot MCP (3 servers) | Add nautobot-mcp, golden-config, routing servers |
| #059 | DefenseClaw/OpenShell | Verify security documentation complete |

### MCP Servers to Document (from config/openclaw.json)

**New servers requiring documentation:**
- `claroty-mcp` - Claroty xDome OT/IoT asset management
- `forward-mcp` - Forward Networks digital twin and NQE
- `nautobot-golden-config-mcp` - Nautobot golden configuration
- `nautobot-routing-mcp` - Nautobot routing data
- 15 `chkp-*` servers - Check Point Security suite

### Specific README Updates Required

1. **Line 7 (header)**: "113 skills" → "179 skills", "67 MCP integrations" → "43 MCP servers"
2. **Line 19**: "113 skills" → "179 skills", "67 MCP integrations" → "43 MCP servers"
3. **Line 96 (HUD section)**: "48 integrations, 103 skills" → "43 MCP servers, 179 skills"
4. **What It Does section**: Add Forward Networks, Claroty xDome, EVE-NG, HumanRail capabilities
5. **MCP integration lists**: Ensure all 43 servers are represented
