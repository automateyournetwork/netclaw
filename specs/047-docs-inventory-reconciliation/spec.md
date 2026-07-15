# Feature Specification: Documentation Inventory Reconciliation

**Feature Branch**: `047-docs-inventory-reconciliation`
**Created**: 2026-07-07
**Status**: Draft
**Input**: User description: "Reconcile NetClaw's documentation inventory (README.md, SOUL.md, SOUL-SKILLS.md, mcp-servers/README.md, ui/netclaw-visual/README.md) so skill and MCP server counts are accurate and consistent everywhere, superseding the now-stale 038-docs-hud-refresh spec." (see full audit findings in Assumptions and prior-art notes below)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Trustworthy Skill/Integration Counts (Priority: P1)

As a prospective user or contributor evaluating NetClaw, I want every count of "skills" and "MCP integrations" I encounter across the project's documentation to agree with each other and with what's actually in the codebase, so that I can trust the project's stated scope instead of wondering which number is real.

**Why this priority**: Inconsistent headline numbers are the single most visible credibility problem in the project's documentation today — a reader hits four different skill counts and three different MCP counts within README.md and SOUL.md alone, before ever running the product. This is a first-impression and trust issue, not a cosmetic one.

**Independent Test**: Can be fully tested by grepping every skill/MCP count claim across README.md, SOUL.md, SOUL-SKILLS.md, mcp-servers/README.md, and ui/netclaw-visual/README.md, and confirming they all match one canonical figure derived from the live codebase.

**Acceptance Scenarios**:

1. **Given** a reader opens README.md, **When** they compare the count stated near the top of the file to the count stated in the "Skills" and "MCP Servers" section headings, **Then** all numbers match each other exactly.
2. **Given** a reader opens SOUL.md after reading README.md, **When** they compare the skill/MCP counts stated there, **Then** the numbers match README.md's numbers.
3. **Given** a reader counts skill directories in the codebase directly, **When** they compare that count to the documented count, **Then** they match.

---

### User Story 2 - Complete MCP Server and Skill Inventory Tables (Priority: P1)

As a network engineer evaluating whether NetClaw already supports a specific platform, I want the README's MCP Servers table and Skills tables to actually list every server and skill that exists in the codebase, so that I don't wrongly conclude a capability is missing and file a duplicate request or, worse, waste time building something that already exists.

**Why this priority**: This session's audit found an external reviewer incorrectly concluded that Azure, Batfish, GitLab, and NetFlow/IPFIX support were all missing from NetClaw — when all four are fully implemented. The review reached that (wrong) conclusion specifically because the README's own inventory tables are incomplete (the MCP Servers table lists 69 rows under a heading claiming 74, and undercounts the real total further still; the mcp-servers/README.md table lists only 12 of over 50 vendored servers). Incomplete tables actively mislead readers into thinking finished work doesn't exist.

**Independent Test**: Can be tested by cross-referencing every server directory under `mcp-servers/`, every entry in `config/openclaw.json`, and every skill directory under `workspace/skills/` against the README/mcp-servers/README.md tables and confirming zero omissions.

**Acceptance Scenarios**:

1. **Given** a server is registered in `config/openclaw.json` or vendored under `mcp-servers/`, **When** a reader searches the README's MCP Servers table or `mcp-servers/README.md`, **Then** they find a row for it.
2. **Given** a skill directory exists under `workspace/skills/`, **When** a reader searches the README's Skills section, **Then** they find an entry for it.
3. **Given** a reader searches specifically for "Azure", "Batfish", "GitLab", or "NetFlow"/"IPFIX" in the README, **Then** they find each one documented as an existing, shipped capability (not absent, and not described as new/upcoming).

---

### User Story 3 - Repeatable Verification Instead of Manual Recount (Priority: P2)

As a maintainer who will add more skills and MCP servers in future feature branches, I want a documented, automatable way to compute the true current skill/MCP counts, so that documentation can be re-verified in seconds after each new feature merges instead of drifting silently for months the way it did after spec 038.

**Why this priority**: This is the second time this exact class of problem has needed a dedicated spec (038 in June, this one in July, with 8 feature branches merging silently in between). Without a repeatable check, the same drift will recur after the next several feature branches merge. This is lower priority than fixing the current-state numbers (P1) because it's a process fix that prevents recurrence rather than fixing today's visible problem, but it's what makes the P1 fix durable.

**Independent Test**: Can be tested by running the documented counting procedure/script before and after adding a new skill directory or a new `config/openclaw.json` entry, and confirming the reported counts change accordingly.

**Acceptance Scenarios**:

1. **Given** a new skill directory is added under `workspace/skills/`, **When** the counting procedure is run, **Then** the reported skill count increases by one.
2. **Given** a new server is registered in `config/openclaw.json`, **When** the counting procedure is run, **Then** the reported MCP integration count increases accordingly.
3. **Given** a maintainer wants to verify documentation before a release, **When** they follow the documented procedure, **Then** they get a clear pass/fail signal without needing to manually eyeball multiple files.

---

### Edge Cases

- What happens when an MCP server is registered in `config/openclaw.json` but has no locally vendored directory under `mcp-servers/` (e.g., it's installed at runtime via pip/npm/docker, such as GitHub, Microsoft Graph, Itential, Cisco NSO, Cisco CML)? These MUST still count toward the total MCP integration figure and MUST still appear in the README's MCP Servers table — the counting method cannot rely on `mcp-servers/` directory listing alone.
- What happens when a single vendored directory actually represents multiple independently listed integrations (e.g., `checkpoint-mcp-servers/` contains 15 distinct `chkp-*` servers, `mcp-servers/` counts it as one directory)? The documented total MUST count each independently-registered/independently-described server, not the containing directory.
- What happens when a skill or MCP server is deprecated or removed in a future branch? The counting procedure and documentation MUST be re-run and updated as part of that branch's own work, not left for a future reconciliation spec.
- What happens when the Visual HUD's live-computed count (from `ui/netclaw-visual/server.js`) disagrees with the static count documented in README.md after this fix ships? Since the HUD computes its number dynamically from the same `workspace/skills/` directory, any future disagreement signals that README.md has drifted again and should be treated as the definitive drift-detection signal going forward.
- What happens to spec 038-docs-hud-refresh once this spec ships? It MUST be left in place as historical record (not deleted or rewritten), with this spec's documentation referencing it as prior art rather than duplicating its content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Documentation MUST state a single, consistent skill count across README.md (all locations: header prose, "What It Does" intro, Visual HUD prose, and the "Skills" section heading), SOUL.md, and SOUL-SKILLS.md.
- **FR-002**: Documentation MUST state a single, consistent MCP integration/server count across README.md (all locations: header prose, "What It Does" intro, Visual HUD prose, and the "MCP Servers" section heading), SOUL.md, and mcp-servers/README.md.
- **FR-003**: The documented skill count MUST equal the actual number of skill directories present under `workspace/skills/` at the time of writing (excluding non-skill files such as `SKILL-SCHEMA.md`).
- **FR-004**: The documented MCP integration count MUST equal the union of (a) all entries registered in `config/openclaw.json`, expanding any multi-server bundle (such as the Check Point suite) into its individually documented sub-servers, and (b) any additional externally-installed servers (pip/npm/docker) that are part of NetClaw's supported integration set but not present in `config/openclaw.json` or vendored under `mcp-servers/`.
- **FR-005**: The README's "MCP Servers" table MUST contain a row for every server counted under FR-004, with no omissions.
- **FR-006**: The README's "Skills" section MUST contain an entry for every skill directory counted under FR-003, with no omissions.
- **FR-007**: `mcp-servers/README.md` MUST list every vendored server directory present under `mcp-servers/`, not a partial subset.
- **FR-008**: Documentation MUST explicitly confirm, as already-shipped capabilities (not new additions), the existence of: Azure networking (azure-network-mcp), Batfish configuration analysis (batfish-mcp), GitLab DevOps (gitlab-mcp), and NetFlow v5/v9 + IPFIX flow telemetry (ipfix-mcp) — correcting a specific external claim that these were missing.
- **FR-009**: Documentation MUST NOT describe or imply the addition of a Kubernetes/OpenShift cluster-management MCP or sFlow support as part of this effort — both are explicitly out of scope and reserved for future, separately-scoped work.
- **FR-010**: A documented, repeatable procedure (script or step-by-step instructions) MUST exist that computes the current skill count and current MCP integration count directly from the codebase (per FR-003 and FR-004), so future documentation updates can be verified without manual recounting.
- **FR-011**: The reconciliation MUST reference spec 038-docs-hud-refresh as prior, superseded work rather than duplicating its content, and MUST leave that spec's files in place unmodified as historical record.
- **FR-012**: The prose description of the Visual HUD in README.md MUST accurately describe that the HUD computes its skill/integration counts live from the codebase (rather than stating a specific static number that can drift out of sync with the HUD's actual live-rendered output).

### Key Entities

- **Skill count**: The total number of skill directories under `workspace/skills/`, each representing one documented operational capability exposed to the agent.
- **MCP integration count**: The total number of distinct, individually-usable MCP servers NetClaw supports, whether vendored locally under `mcp-servers/`, registered in `config/openclaw.json`, or installed at runtime via an external package manager — with bundled multi-server packages (e.g., Check Point) counted per sub-server, not per bundle.
- **Canonical documentation set**: The five files in scope for this reconciliation — README.md, SOUL.md, SOUL-SKILLS.md, mcp-servers/README.md, and ui/netclaw-visual/README.md — which must all agree with each other and with the codebase.
- **Counting procedure**: The repeatable method (script or documented steps) that derives the skill count and MCP integration count directly from the codebase, serving as the ground-truth source for all five canonical files going forward.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader can find the skill count and MCP integration count in any of the five canonical documentation files and get the identical number in all of them, with zero discrepancies.
- **SC-002**: The documented skill count and MCP integration count exactly match the counts produced by the documented counting procedure run against the current codebase, with zero discrepancy.
- **SC-003**: Every server counted by the counting procedure appears as a distinct row in the README's MCP Servers table and in mcp-servers/README.md; every skill directory appears as a distinct entry in the README's Skills section — 100% coverage, zero omissions.
- **SC-004**: A reader searching the README for "Azure", "Batfish", "GitLab", or "NetFlow"/"IPFIX" finds each documented as an existing capability within one search, eliminating the specific false-negative that caused the external review's incorrect gap claims.
- **SC-005**: After this reconciliation, running the documented counting procedure again after a future feature branch adds one new skill and one new MCP server produces updated counts within the same session, with no ambiguity about which files need updating.

## Assumptions

- Ground truth as of 2026-07-07 (subject to re-verification via the FR-010 counting procedure at implementation time, since branches may merge between spec-writing and implementation): `workspace/skills/` contains 190 skill directories; `config/openclaw.json` `mcpServers` has 49 registered entries (15 of which are the `chkp-*` Check Point suite); `mcp-servers/` contains 54 vendored local server directories, a population that only partially overlaps `config/openclaw.json` since some documented servers (GitHub, Microsoft Graph, Itential, Cisco NSO, Cisco CML, and others) are installed via pip/npm/docker at runtime with no local vendored directory.
- The Visual HUD implementation itself (`ui/netclaw-visual/server.js`) is already correct: it computes skill count live from `workspace/skills/` via `parseSkills()` and derives integration count dynamically from an `INTEGRATION_CATALOG` mapped against skill file prefixes. This spec treats the HUD's live-computation approach as the reference pattern and does not require changes to the HUD's code — only to the README's stale prose description of what the HUD shows.
- Spec 038-docs-hud-refresh (created 2026-06-23) attempted this same class of reconciliation and targeted 179 skills / 43 MCP servers as correct at that time. Eight feature branches (039-twitter-x-integration, 040-twitter-mentions, 042-twilio-voice-mcp, 043-full-voice-integration, 044-ue5-mcp-network-viz, 045-ue5-digital-twin, 046-threejs-network-viz, plus the drift already present when 038 was written) have since merged without a follow-up documentation update, making 038's target numbers stale. This spec supersedes 038; 038's files remain as historical record per FR-011.
- Building a Kubernetes/OpenShift cluster-management MCP and adding sFlow support to the existing `ipfix-mcp` are both genuine capability gaps identified during this audit's fact-check pass, but are explicitly out of scope for this documentation-only spec (per FR-009) and will be scoped as separate future feature specs.
- "MCP integration count" is defined at the individually-usable-server level (e.g., each of the 15 Check Point `chkp-*` servers counts individually), consistent with how the existing README table and `config/openclaw.json` already enumerate them — not at the vendored-directory level, which would undercount bundled packages.
- No new skills or MCP servers are being built as part of this spec; all changes are documentation-only edits to existing files plus the addition of one new counting procedure (script or documented steps).
