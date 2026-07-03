# Feature Specification: Check Point MCP Integration for NetClaw

**Feature Branch**: `031-checkpoint-mcp-integration`
**Created**: 2026-06-14
**Status**: Draft
**Input**: Production-grade integration of all 15 official Check Point MCP servers into NetClaw with unified `/checkpoint` skill, requested directly by Barak Kfir (Director, AI Architecture & Innovation at Check Point Software Technologies)

## Background

Check Point Software Technologies has officially released 15 MCP (Model Context Protocol) servers exposing their enterprise security platform to AI-powered automation. Barak Kfir directly requested integration of these servers into NetClaw, making this a vendor-endorsed, production-grade extension.

**Official Resources**:
- Portal: https://mcp.checkpoint.com/
- GitHub: https://github.com/CheckPointSW/mcp-servers
- All MCPs are TypeScript/NPM packages run via `npx @chkp/<package-name>`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Security Policy Audit (Priority: P1)

A security engineer wants to audit their Check Point firewall policies for overly permissive rules, compliance gaps, and optimization opportunities using natural language queries.

**Why this priority**: Policy management is the core use case for Check Point security platforms. The ability to query, analyze, and get insights on policies provides immediate value to all Check Point customers.

**Independent Test**: Can be fully tested by connecting to a Check Point Management Server and querying "show me overly permissive rules" - delivers actionable policy insights.

**Acceptance Scenarios**:

1. **Given** a configured Check Point Management Server connection, **When** user asks "audit my firewall policies for overly permissive rules", **Then** the system invokes management + policy-insights MCPs and returns a structured report of problematic rules with recommendations
2. **Given** valid credentials, **When** user asks "show me all rules allowing any-any", **Then** the system returns a list of rules matching that criteria with object details
3. **Given** a policy with thousands of rules, **When** user asks for policy optimization suggestions, **Then** the system provides prioritized recommendations without timeout

---

### User Story 2 - Threat Intelligence & Reputation Lookup (Priority: P1)

A SOC analyst needs to quickly check the reputation of suspicious IPs, URLs, or files encountered during incident investigation.

**Why this priority**: Threat intelligence is time-critical during security incidents. Instant reputation lookups enable faster triage and response.

**Independent Test**: Can be fully tested by querying "check reputation of IP 1.2.3.4" - delivers immediate threat intelligence without requiring full policy access.

**Acceptance Scenarios**:

1. **Given** a configured Reputation Service API key, **When** user asks "check reputation of IP 185.220.101.1", **Then** the system returns reputation score, categories, and risk assessment
2. **Given** a suspicious URL, **When** user asks "is this URL malicious: http://example.com/suspicious", **Then** the system returns URL reputation and categorization
3. **Given** a file hash, **When** user asks "check file reputation for SHA256 abc123...", **Then** the system returns file reputation and any known malware associations

---

### User Story 3 - Gateway Diagnostics & Troubleshooting (Priority: P2)

A network engineer needs to diagnose connectivity issues, performance problems, or hardware status on Check Point gateways.

**Why this priority**: Gateway health is critical for security operations. Diagnostics help identify and resolve issues before they impact security posture.

**Independent Test**: Can be fully tested by running "show gateway health status" against a configured gateway - delivers diagnostic data independently.

**Acceptance Scenarios**:

1. **Given** configured gateway SSH credentials, **When** user asks "show gateway health status", **Then** the system returns hardware, CPU, memory, and interface status
2. **Given** a connection issue, **When** user asks "debug why connection from 10.1.1.1 to 8.8.8.8 is failing", **Then** the system invokes connection-analysis MCP and returns debug logs with root cause analysis
3. **Given** high CPU on a gateway, **When** user asks "what's causing high CPU on the gateway", **Then** the system returns top processes and performance metrics

---

### User Story 4 - Threat Prevention Analysis (Priority: P2)

A security architect wants to review threat prevention coverage, IPS signatures, and IOC feeds to ensure adequate protection.

**Why this priority**: Understanding threat prevention posture is essential for security planning and compliance reporting.

**Independent Test**: Can be fully tested by querying "show threat prevention coverage gaps" - delivers security posture insights.

**Acceptance Scenarios**:

1. **Given** a configured management connection, **When** user asks "show threat prevention profiles", **Then** the system returns all TP profiles with their configurations
2. **Given** IPS blade enabled, **When** user asks "what IPS protections are missing for CVE-2024-xxxx", **Then** the system checks IPS updates and reports coverage status
3. **Given** IOC feeds configured, **When** user asks "show active IOC feeds and their status", **Then** the system returns feed information and last update times

---

### User Story 5 - SASE Management (Priority: P2)

An administrator managing distributed networks wants to query and configure Check Point SASE regions, networks, and applications.

**Why this priority**: SASE is a growing deployment model. Managing cloud-delivered security alongside on-premises is increasingly common.

**Independent Test**: Can be fully tested by querying "show SASE regions and their status" - delivers SASE visibility.

**Acceptance Scenarios**:

1. **Given** configured SASE credentials, **When** user asks "show all SASE regions", **Then** the system returns region information with status
2. **Given** SASE applications defined, **When** user asks "list applications in SASE policy", **Then** the system returns application definitions and rules
3. **Given** network connectivity issues, **When** user asks "show SASE network configurations", **Then** the system returns network topology and settings

---

### User Story 6 - File/Malware Analysis (Priority: P2)

A security analyst needs to analyze suspicious files for malware using Check Point's Threat Emulation cloud service.

**Why this priority**: Automated malware analysis accelerates incident response and threat hunting workflows.

**Independent Test**: Can be fully tested by submitting a file for analysis - delivers malware verdict independently.

**Acceptance Scenarios**:

1. **Given** a configured Threat Emulation API key, **When** user submits a file for analysis, **Then** the system uploads to TE cloud and returns analysis results
2. **Given** a file hash, **When** user asks "analyze file with hash abc123...", **Then** the system checks existing verdicts or triggers new analysis
3. **Given** analysis complete, **When** user asks for detailed report, **Then** the system returns behavioral analysis, IOCs, and verdict

---

### User Story 7 - Cross-Platform Composition (Priority: P3)

A network security engineer wants to correlate Check Point policies with network topology from other NetClaw sources (CML labs, SuzieQ, Batfish).

**Why this priority**: Composability with other NetClaw skills enables advanced use cases and differentiates from standalone Check Point tools.

**Independent Test**: Can be tested by asking "compare Check Point policies with my CML lab topology" - requires both Check Point and CML configured.

**Acceptance Scenarios**:

1. **Given** Check Point management and CML lab configured, **When** user asks "cross-reference firewall rules with lab topology", **Then** the system correlates policies with network paths
2. **Given** SuzieQ and Check Point configured, **When** user asks "which Check Point rules affect traffic to devices in SuzieQ inventory", **Then** the system maps rules to network devices
3. **Given** multiple security platforms, **When** user asks for unified security posture, **Then** the system aggregates insights from available sources

---

### User Story 8 - Installation & Onboarding (Priority: P1)

A new NetClaw user wants to enable Check Point integration during initial setup, or an existing user wants to add Check Point support.

**Why this priority**: Frictionless onboarding is critical for adoption. Both new and existing users must have clear paths to enable the integration.

**Independent Test**: Can be fully tested by running install.sh and selecting Check Point integration - delivers configured environment.

**Acceptance Scenarios**:

1. **Given** running install.sh, **When** installer reaches Check Point step and user selects yes, **Then** the system prompts for credentials and configures all 15 MCPs
2. **Given** an existing NetClaw installation, **When** user runs checkpoint-enable.sh, **Then** the system adds Check Point MCP configurations and reloads
3. **Given** credentials not available at install time, **When** user skips credential entry, **Then** the system configures MCPs with placeholder variables for later configuration

---

### Edge Cases

- What happens when Check Point Management Server is unreachable? System returns clear error with connectivity troubleshooting steps.
- How does system handle expired or invalid credentials? System returns authentication error with guidance to update credentials.
- What if only some MCPs are configured (partial setup)? System uses available MCPs and indicates which capabilities are unavailable.
- How does system handle large policy sets (10,000+ rules)? System implements pagination and progress indication for long-running queries.
- What if user query maps to multiple MCPs? System invokes all relevant MCPs and aggregates results coherently.

## Requirements *(mandatory)*

### Functional Requirements

**MCP Server Configuration**

- **FR-001**: System MUST support configuration of all 15 official Check Point MCP servers via environment variables
- **FR-002**: System MUST allow partial configuration (not all MCPs required to be configured)
- **FR-003**: System MUST validate MCP connectivity on startup and report unavailable servers
- **FR-004**: System MUST support CHKP_TELEMETRY_DISABLED=true to disable Check Point telemetry

**Skill Behavior**

- **FR-005**: System MUST provide a `/checkpoint` skill that auto-detects which MCP(s) to invoke based on natural language query
- **FR-006**: System MUST support invoking multiple MCPs for queries requiring data from multiple sources
- **FR-007**: System MUST provide clear error messages when required MCPs are not configured for a query
- **FR-008**: System MUST be composable with other NetClaw skills (CML, SuzieQ, Batfish, etc.)
- **FR-008a**: System MUST use the first configured gateway as default when multiple gateways exist, allowing users to specify a different target gateway in their query

**Installation & Upgrade**

- **FR-009**: install.sh MUST include a step "Enable Check Point Security Integration? [y/N]"
- **FR-010**: System MUST provide checkpoint-enable.sh script for existing installations
- **FR-011**: System MUST add MCP configurations to ~/.openclaw/config/mcp-servers.json
- **FR-012**: System MUST update documentation (README, SOUL, skill docs) with Check Point information

**Security**

- **FR-013**: System MUST never expose credentials to the AI model (handled by MCP server)
- **FR-014**: System MUST document that queried data is exposed to the model for compliance awareness
- **FR-015**: System MUST support credential storage in environment variables with CHKP_ prefix
- **FR-016**: System MUST support configurable logging levels (minimal/standard/verbose) via CHKP_LOG_LEVEL environment variable, defaulting to standard (queries + MCPs invoked, no response data)

### MCP Servers to Configure

| # | Package Name | Purpose | Required Credentials |
|---|--------------|---------|---------------------|
| 1 | @chkp/quantum-management-mcp | Policies, rules, objects, topology | MGMT server, user, pass, domain |
| 2 | @chkp/management-logs-mcp | Connection and audit logs | MGMT server credentials |
| 3 | @chkp/threat-prevention-mcp | TP policies, IPS, IOC feeds | MGMT server credentials |
| 4 | @chkp/https-inspection-mcp | HTTPS inspection policies | MGMT server credentials |
| 5 | @chkp/harmony-sase-mcp | SASE management | SASE client ID, secret, tenant |
| 6 | @chkp/reputation-service-mcp | URL/IP/file reputation | Reputation API key |
| 7 | @chkp/quantum-gw-cli-mcp | Gateway diagnostics | Gateway SSH credentials |
| 8 | @chkp/quantum-gw-connection-analysis-mcp | Connection debug | Gateway SSH credentials |
| 9 | @chkp/threat-emulation-mcp | Malware analysis | TE API key |
| 10 | @chkp/quantum-gaia-mcp | GAIA OS management | Gateway SSH credentials |
| 11 | @chkp/documentation-mcp | Documentation assistant | None (public) |
| 12 | @chkp/spark-management-mcp | Spark firewall (MSP) | Spark API key |
| 13 | @chkp/cpinfo-analysis-mcp | CPInfo diagnostics | None (file-based) |
| 14 | @chkp/argos-erm-mcp | Exposure/risk management | Argos API key |
| 15 | @chkp/policy-insights-mcp | Policy optimization | MGMT server credentials |

### Key Entities

- **MCP Server**: A Check Point NPM package that exposes specific security platform capabilities via MCP protocol
- **Credential Set**: Environment variables grouped by Check Point product (CHKP_MGMT_*, CHKP_SASE_*, etc.)
- **Query Router**: Logic that maps natural language queries to appropriate MCP server(s)
- **Skill Definition**: The `/checkpoint` skill configuration in SKILL.md format

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can query any of the 15 Check Point security domains using natural language within 30 seconds of response time for typical queries
- **SC-002**: New users can enable Check Point integration during install.sh in under 5 minutes
- **SC-003**: Existing users can add Check Point support using checkpoint-enable.sh in under 2 minutes
- **SC-004**: 90% of common security queries are correctly routed to the appropriate MCP(s) without user intervention
- **SC-005**: System gracefully handles partial configurations, clearly indicating available vs unavailable capabilities
- **SC-006**: Documentation enables self-service setup without requiring support escalation for 95% of users
- **SC-007**: Cross-platform queries (Check Point + other NetClaw skills) complete successfully when both data sources are configured

## Clarifications

### Session 2026-06-14

- Q: How should users target specific gateways when multiple are deployed? → A: Default gateway - use first configured gateway unless user specifies otherwise
- Q: What level of query logging/observability should the /checkpoint skill provide? → A: Configurable - let users set logging level via environment variable

## Assumptions

- Users have valid Check Point product licenses and API access for the products they wish to query
- Node.js/NPM is available on the system (required to run npx for Check Point MCPs)
- Check Point MCPs are stable and maintained by Check Point (official vendor support)
- Users understand that queried security data will be processed by the AI model
- Network connectivity exists between NetClaw host and Check Point management servers/cloud services
- Check Point's MCP telemetry preferences are respected via CHKP_TELEMETRY_DISABLED environment variable
- The 15 MCPs represent the current official set; future MCPs may be added in subsequent releases
