# Feature Specification: Golden Config Bootstrap Workflow

**Feature Branch**: `028-golden-config-bootstrap`
**Created**: 2026-04-09
**Status**: Draft
**Input**: User description: "Use NetClaw to set up the Nautobot Golden Config plugin from scratch — collect live configs via pyATS, reference RFCs and Cisco design guides for best practices, generate Jinja templates and compliance rules, create git repos, wire everything together in Nautobot, and run the first compliance check."

## Context

The Nautobot Golden Config plugin (v3.0.5) is installed on the Nautobot 3.1.0 instance at 192.168.3.253 but is unconfigured:
- ✅ Plugin installed, 10 jobs registered and enabled
- ✅ Default Settings exists with a dynamic group scoped to all devices
- ✅ Platform `cisco_ios` exists with `network_driver=cisco_xe`
- ✅ 3 devices: HomeSwitch01, HomeSwitch02 (Cisco WS-C3850-48P, IOS-XE), pfSense-FW01
- ❌ No git repositories for templates/backups/intended configs
- ❌ No SoT aggregation GraphQL query
- ❌ No compliance features or rules defined
- ❌ No Jinja templates
- ❌ Golden Config Setting has empty path templates and null repo links

### How Golden Config Works

1. **Backup** — Nautobot connects to devices (via Nornir/NAPALM) and stores running configs in a git repo
2. **Intended** — Nautobot renders Jinja templates using SoT data (from a GraphQL query) to generate the "intended" config per device
3. **Compliance** — Nautobot compares actual (backup) vs intended configs per compliance feature, producing pass/fail results with diffs and remediation

The bootstrap workflow must set up all three pillars: backup storage, intended config generation (templates + SoT query), and compliance rules.

### MCP Servers Involved

- **nautobot-mcp-v2** — create git repos, GraphQL queries, compliance features/rules, update GC settings
- **pyATS MCP** — collect live running configs from HomeSwitch01/02
- **RFC MCP** — look up relevant standards (NTP RFC 5905, AAA, SNMP, syslog, etc.)
- **GitHub MCP** — create the git repository, commit Jinja templates and directory structure
- **DevNet Content Search MCP** — pull Cisco validated design guides and best practices (when available)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Analyze Live Configs and Identify Compliance Features (Priority: P1)

As a network engineer, I want NetClaw to collect the running configs from my switches, analyze them, and propose a set of compliance features (e.g., AAA, NTP, logging, SNMP, banner, interfaces, VLANs) based on what config sections exist, so I have a starting point for golden config without manually reading through hundreds of lines.

**Why this priority**: Everything else depends on knowing what compliance features to track. This is the discovery phase that informs template creation and rule definition.

**Independent Test**: Ask "analyze HomeSwitch01 running config and propose compliance features" — the agent collects the config via pyATS, parses it into logical sections, and returns a proposed feature list with the config lines that belong to each.

**Acceptance Scenarios**:

1. **Given** pyATS can reach HomeSwitch01, **When** the operator requests config analysis, **Then** the agent collects the running config and proposes compliance features (e.g., aaa, ntp, logging, snmp, banner, stp, vty, interfaces) with the matching config lines for each.
2. **Given** the running config contains NTP configuration, **When** the agent proposes features, **Then** it references RFC 5905 (NTP) via the RFC MCP to validate the config against standards.
3. **Given** the operator approves the proposed features, **When** they confirm, **Then** the agent creates the compliance features in Nautobot via nautobot_create_compliance_feature.

---

### User Story 2 — Create Git Repository and Directory Structure (Priority: P2)

As a network engineer, I want NetClaw to create a GitHub repository with the correct directory structure for golden config (templates, intended configs, backups) and register it in Nautobot, so the golden config plugin has storage for all three pillars.

**Why this priority**: The git repo is infrastructure that the golden config plugin requires before it can store backups, render intended configs, or run compliance. Must be done before templates can be committed.

**Independent Test**: Ask "create a golden config git repo for my network" — the agent creates a GitHub repo with the correct structure and registers it in Nautobot.

**Acceptance Scenarios**:

1. **Given** GitHub MCP is configured with a valid token, **When** the operator requests repo creation, **Then** the agent creates a GitHub repo with directories: `templates/cisco_xe/`, `intended/`, `backups/`.
2. **Given** the repo is created, **When** the agent registers it in Nautobot, **Then** three git repository entries are created (or one with multiple provided_contents): jinja templates, intended configs, backup configs.
3. **Given** the repos are registered, **When** the agent updates the Golden Config Setting, **Then** the setting links to the repos with correct path templates (e.g., `{{obj.location.name}}/{{obj.name}}.cfg`).

---

### User Story 3 — Generate Jinja Templates from Live Config + Best Practices (Priority: P3)

As a network engineer, I want NetClaw to generate Jinja2 templates for my intended configs by templatizing the live running config — replacing device-specific values with SoT variables, hardening against RFC/Cisco best practices, and committing the templates to the git repo.

**Why this priority**: Templates are the core of golden config — they define what the intended config should look like. This is the most complex step and the highest-value output.

**Independent Test**: Ask "generate golden config templates for my Cisco switches based on their running configs and best practices" — the agent produces Jinja2 templates that use Nautobot SoT variables.

**Acceptance Scenarios**:

1. **Given** the running config has been collected and compliance features identified, **When** the operator requests template generation, **Then** the agent produces Jinja2 templates that replace device-specific values (hostname, IPs, interface descriptions) with SoT variables (e.g., `{{ obj.name }}`, `{{ obj.interfaces }}`, `{{ obj.primary_ip4.address }}`).
2. **Given** the NTP section of the config, **When** the agent generates the NTP template, **Then** it references RFC 5905 and Cisco best practices to include recommended settings (authentication, preferred server, access-group).
3. **Given** the templates are generated, **When** the agent commits them to the git repo, **Then** they are placed in the correct path (e.g., `templates/cisco_xe/main.j2`) matching the jinja_path_template in the GC setting.

---

### User Story 4 — Create SoT Aggregation Query and Compliance Rules (Priority: P4)

As a network engineer, I want NetClaw to create the SoT aggregation GraphQL query that feeds data into the Jinja templates, and create compliance rules with match_config patterns for each feature, so the golden config plugin can render intended configs and check compliance.

**Why this priority**: The SoT query and compliance rules are the final wiring that connects Nautobot data to templates and enables compliance checking. Without them, the templates can't render and compliance can't run.

**Independent Test**: Ask "create the SoT query and compliance rules for golden config" — the agent creates a saved GraphQL query and compliance rules per feature.

**Acceptance Scenarios**:

1. **Given** compliance features exist in Nautobot, **When** the operator requests SoT query creation, **Then** the agent creates a saved GraphQL query that returns all fields needed by the Jinja templates (device name, interfaces, IPs, VLANs, location, platform, etc.).
2. **Given** the SoT query is created, **When** the agent updates the Golden Config Setting, **Then** the sot_agg_query field links to the new query.
3. **Given** compliance features exist, **When** the agent creates compliance rules, **Then** each rule has a match_config pattern that identifies the relevant config section (e.g., `^aaa ` for AAA, `^ntp ` for NTP, `^logging ` for logging).

---

### User Story 5 — Run First Compliance Check (Priority: P5)

As a network engineer, I want NetClaw to trigger the golden config backup and compliance jobs and show me the results, so I can see which config sections are compliant and which need remediation.

**Why this priority**: This is the validation step that proves the entire setup works. It's the payoff for all the previous work.

**Independent Test**: Ask "run a golden config compliance check on HomeSwitch01" — the agent triggers the jobs and reports results.

**Acceptance Scenarios**:

1. **Given** all golden config infrastructure is set up (repos, templates, SoT query, compliance rules), **When** the operator requests a compliance check, **Then** the agent triggers the backup job, then the intended config job, then the compliance job.
2. **Given** the compliance job completes, **When** the agent queries results, **Then** it shows per-feature compliance status with diffs for non-compliant sections.
3. **Given** a feature is non-compliant, **When** the agent shows the diff, **Then** it includes the actual config, intended config, missing lines, and extra lines.

---

### Edge Cases

- What happens when pyATS cannot reach a device during config collection?
- What happens when the GitHub token doesn't have repo creation permissions?
- What happens when a Jinja template has syntax errors?
- How does the system handle devices with different platforms (IOS-XE vs pfSense)?
- What happens when the golden config backup job fails due to connectivity?
- How does the system handle config sections that don't map cleanly to a single compliance feature?
- What happens when the SoT query returns fields that don't exist for all devices?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST collect running configs from devices via pyATS MCP.
- **FR-002**: System MUST analyze running configs and propose compliance features based on config section identification.
- **FR-003**: System MUST reference relevant RFCs via RFC MCP when proposing best practices for each compliance feature.
- **FR-004**: System MUST create a GitHub repository with the correct directory structure for golden config.
- **FR-005**: System MUST register git repositories in Nautobot with correct provided_contents types.
- **FR-006**: System MUST generate Jinja2 templates that use Nautobot SoT variables to produce intended configs.
- **FR-007**: System MUST create a SoT aggregation GraphQL query that returns all fields needed by the templates.
- **FR-008**: System MUST create compliance features and rules in Nautobot with appropriate match_config patterns.
- **FR-009**: System MUST update the Golden Config Setting to link repos, path templates, and SoT query.
- **FR-010**: System MUST be able to trigger golden config jobs (backup, intended, compliance) via Nautobot's job API.
- **FR-011**: System MUST present compliance results in a human-readable format showing per-feature pass/fail with diffs.
- **FR-012**: All write operations MUST be ITSM-gated when enabled.
- **FR-013**: System MUST handle the pfSense device gracefully — either skip it (no network_driver) or note it as unsupported for golden config.
- **FR-014**: System MUST commit Jinja templates to the git repo via GitHub MCP.

### Key Entities

- **Compliance Feature**: A logical config section to track (e.g., "aaa", "ntp", "logging"). Created in Nautobot.
- **Compliance Rule**: Links a feature to a platform with a match_config regex pattern. Created in Nautobot.
- **Jinja Template**: A Jinja2 file that renders intended config from SoT data. Stored in git.
- **SoT Aggregation Query**: A saved GraphQL query in Nautobot that provides device data to templates.
- **Golden Config Setting**: The configuration object that ties repos, templates, queries, and scope together.
- **Config Plan**: A generated remediation plan for non-compliant config sections.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running configs are collected from HomeSwitch01 and HomeSwitch02 via pyATS.
- **SC-002**: At least 5 compliance features are created (e.g., aaa, ntp, logging, snmp, banner).
- **SC-003**: Compliance rules exist for each feature on the cisco_ios platform.
- **SC-004**: A GitHub repo exists with Jinja templates in the correct directory structure.
- **SC-005**: The Golden Config Setting is fully wired — all three repos linked, path templates set, SoT query assigned.
- **SC-006**: The compliance job runs successfully and produces per-feature results for both switches.
- **SC-007**: The agent can explain each compliance result and suggest remediation for non-compliant features.

## Assumptions

- GitHub MCP is configured with a token that has repo creation permissions.
- pyATS MCP can SSH to HomeSwitch01 and HomeSwitch02 (already verified working).
- The Nautobot golden config plugin's Nornir/NAPALM backend can also reach the switches for backup jobs (same network, same credentials).
- RFC MCP is available for standards lookups.
- DevNet Content Search MCP may or may not be functional (it was listed as failing in the session summary) — the workflow should degrade gracefully without it.
- The operator will review and approve proposed compliance features and templates before they are committed — this is not a fully autonomous workflow.
- pfSense-FW01 is excluded from golden config scope (no cisco_ios platform, no NAPALM driver).
- The golden config plugin's backup job uses the same SSH credentials as pyATS (NETCLAW_USERNAME/PASSWORD from .env).
- Jinja templates will initially be simple (templatized running config) and can be refined iteratively.
- This is a NetClaw skill (workspace/skills/golden-config-bootstrap/SKILL.md), not a new MCP server. It orchestrates existing MCP tools.
