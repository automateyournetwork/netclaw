# Feature Specification: IP Fabric MCP Integration for NetClaw

**Feature Branch**: `032-ipfabric-mcp-integration`
**Created**: 2026-06-19
**Status**: Draft
**Input**: Production-grade integration of the official IP Fabric MCP Server into NetClaw with unified `/ipfabric` skill, developed in collaboration with Daren Fulwell (Field CTO, IP Fabric) and John Capobianco (Creator, NetClaw), representing nearly a decade of friendship and professional partnership.

## Background

IP Fabric provides an automated network assurance platform that discovers, models, and analyzes network infrastructure. The IP Fabric MCP Server is built directly into IP Fabric appliances and exposes network data through standardized MCP tools, prompts, and resources. This integration brings IP Fabric's powerful network analysis capabilities to NetClaw users through a unified `/ipfabric` skill.

**Official Resources**:
- Documentation: https://docs.ipfabric.io/latest/IP_Fabric_Settings/integration/mcp/
- MCP Endpoint: `https://<your-ipfabric-host>/mcp`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Network Health Assessment (Priority: P1)

A SOC analyst or network operator wants to quickly assess overall network health using natural language queries, identifying critical issues across the infrastructure without navigating multiple dashboards.

**Why this priority**: Network health visibility is the foundational use case. Every IP Fabric deployment benefits from quick health checks, making this the highest-value capability for broadest user adoption.

**Independent Test**: Can be fully tested by querying "check network health" against a configured IP Fabric instance - delivers immediate actionable health insights including snapshot freshness, intent violations, inventory issues, and routing stability.

**Acceptance Scenarios**:

1. **Given** a configured IP Fabric connection, **When** user asks "check network health", **Then** the system returns a comprehensive health overview including snapshot freshness, intent rule results, device issues, and routing protocol status
2. **Given** valid credentials, **When** user asks "show me critical issues only", **Then** the system filters results to display only critical-severity findings
3. **Given** a network with BGP deployments, **When** user asks "what's the BGP status across my network", **Then** the system returns BGP neighbor states and identifies any neighbors not in Established state
4. **Given** a network with routing issues, **When** user asks "are there any routing problems", **Then** the system identifies OSPF neighbors not in Full state, BGP session issues, and other routing adjacency problems

---

### User Story 2 - Path Analysis with Visual Diagrams (Priority: P1)

A network engineer needs to trace the network path between two endpoints and visualize it as a diagram for troubleshooting connectivity issues or validating expected traffic flow.

**Why this priority**: Path analysis with visualization is IP Fabric's signature capability. Visual diagrams dramatically accelerate troubleshooting and are essential for explaining network behavior to stakeholders.

**Independent Test**: Can be fully tested by requesting "show the path from 10.0.1.5 to 10.0.2.10 with diagram" - delivers both structured path data and a PNG visualization.

**Acceptance Scenarios**:

1. **Given** source and destination IPs, **When** user asks "show me the path from 10.0.1.5 to 10.0.2.10", **Then** the system traces the unicast path and returns hop-by-hop details
2. **Given** a path request with "diagram" in the query, **When** user asks "trace route from server A to server B with diagram", **Then** the system returns a PNG image visualizing the network path
3. **Given** a host IP, **When** user asks "show path from 192.168.1.100 to its gateway", **Then** the system traces the host-to-gateway path and returns the path details
4. **Given** a VRF-aware network, **When** user asks "show path from 10.1.1.1 to 10.2.2.2 in VRF MGMT", **Then** the system performs path lookup within the specified VRF context
5. **Given** a multicast environment, **When** user asks "show multicast path for group 239.1.1.1 from source 10.0.1.5 with diagram", **Then** the system traces multicast distribution and returns a visual diagram

---

### User Story 3 - Device Inventory Queries (Priority: P2)

An operations team member needs to query the device inventory by site, vendor, status, or other criteria to understand what equipment is deployed and identify devices requiring attention.

**Why this priority**: Inventory visibility is essential for operations but builds on the foundation of health and path analysis. Enables targeted device management and lifecycle planning.

**Independent Test**: Can be fully tested by querying "show all Cisco devices in site HQ" - delivers filtered inventory results.

**Acceptance Scenarios**:

1. **Given** a multi-site network, **When** user asks "show all Cisco devices in site HQ", **Then** the system returns inventory filtered by vendor and site
2. **Given** device health concerns, **When** user asks "find devices with uptime less than 1 day", **Then** the system returns devices that have recently rebooted
3. **Given** security audit requirements, **When** user asks "list devices with telnet enabled", **Then** the system returns devices with telnet protocol active
4. **Given** a large inventory, **When** user asks for device counts by vendor, **Then** the system returns aggregated inventory statistics

---

### User Story 4 - Routing Protocol Troubleshooting (Priority: P2)

A network engineer diagnosing routing issues needs to query BGP, OSPF, and other routing protocol states across the network to identify adjacency problems or configuration issues.

**Why this priority**: Routing protocol analysis is critical for network stability but requires understanding of routing concepts. Essential for network engineers performing troubleshooting.

**Independent Test**: Can be fully tested by querying "show BGP neighbors not in Established state" - delivers protocol-specific troubleshooting data.

**Acceptance Scenarios**:

1. **Given** a BGP network, **When** user asks "show BGP neighbors that are not in Established state", **Then** the system returns all BGP neighbors with problematic states and their details
2. **Given** an OSPF network, **When** user asks "list OSPF neighbors not in Full state", **Then** the system returns OSPF adjacencies that haven't reached full adjacency
3. **Given** routing concerns, **When** user asks "are there any routing adjacency issues", **Then** the system analyzes all routing protocols and reports anomalies
4. **Given** a specific device, **When** user asks about routing neighbors for that device, **Then** the system returns protocol-specific neighbor information

---

### User Story 5 - Intent Validation and Compliance (Priority: P2)

A security or compliance team member needs to validate that the network complies with defined intent rules - both built-in checks and custom compliance policies.

**Why this priority**: Intent verification enables proactive compliance monitoring. Valuable for organizations with regulatory requirements or strict security policies.

**Independent Test**: Can be fully tested by querying "are there any intent violations" - delivers compliance status against defined rules.

**Acceptance Scenarios**:

1. **Given** configured intent rules, **When** user asks "are there any intent violations", **Then** the system returns a summary of failed intent checks with severity levels
2. **Given** specific compliance concerns, **When** user asks "check compliance status", **Then** the system reports on all intent rule evaluations
3. **Given** custom intent rules defined, **When** user queries about specific rule categories, **Then** the system filters results to relevant compliance areas

---

### User Story 6 - Advanced API Discovery and Queries (Priority: P3)

A power user needs to access IP Fabric data not covered by specialized tools, using API discovery to find endpoints, understand parameters, and execute custom queries.

**Why this priority**: API discovery enables extensibility for advanced use cases but requires technical knowledge. Valuable for power users who need custom data access.

**Independent Test**: Can be fully tested by searching "find endpoints for device inventory" and then invoking the discovered endpoint.

**Acceptance Scenarios**:

1. **Given** a data need not covered by specialized tools, **When** user asks "find endpoints for device inventory", **Then** the system searches and returns relevant API endpoints
2. **Given** a discovered endpoint, **When** user requests endpoint details, **Then** the system returns parameters, response schema, and usage examples
3. **Given** endpoint details, **When** user invokes the API with parameters, **Then** the system executes the call and returns formatted results

---

### User Story 7 - Cross-Platform Composition (Priority: P4)

A network security engineer wants to correlate IP Fabric network data with other NetClaw data sources to perform comprehensive analysis across multiple platforms.

**Why this priority**: Cross-platform composition differentiates NetClaw from standalone tools but requires multiple integrations to be configured. Enables advanced multi-source analysis.

**Independent Test**: Requires both IP Fabric and at least one other NetClaw skill configured; can be tested by querying "compare IP Fabric topology with my CML lab".

**Acceptance Scenarios**:

1. **Given** IP Fabric and SuzieQ both configured, **When** user asks to compare network state, **Then** the system correlates data from both sources and highlights differences
2. **Given** IP Fabric and Batfish configured, **When** user asks "validate IP Fabric paths against Batfish config analysis", **Then** the system cross-references live state with configuration analysis
3. **Given** IP Fabric and Check Point configured, **When** user asks "which firewall rules affect the path from A to B", **Then** the system correlates network paths with security policies
4. **Given** IP Fabric and CML/GNS3 configured, **When** user asks to compare lab to production, **Then** the system identifies topology differences

---

### User Story 8 - Installation and Onboarding (Priority: P1)

A new NetClaw user wants to enable IP Fabric integration during initial setup, or an existing user wants to add IP Fabric support to their installation.

**Why this priority**: Frictionless onboarding is critical for adoption. Both new and existing users must have clear, simple paths to enable the integration.

**Independent Test**: Can be fully tested by running ipfabric-enable.sh and configuring credentials - delivers a working IP Fabric connection.

**Acceptance Scenarios**:

1. **Given** running install.sh, **When** installer reaches IP Fabric step and user selects yes, **Then** the system prompts for host URL and API token and configures the MCP
2. **Given** an existing NetClaw installation, **When** user runs ipfabric-enable.sh, **Then** the system adds IP Fabric MCP configuration and reloads
3. **Given** credentials not available at install time, **When** user skips credential entry, **Then** the system configures MCP with placeholder variables for later configuration
4. **Given** configured credentials, **When** user verifies connection, **Then** the system confirms connectivity to the IP Fabric MCP endpoint

---

### Edge Cases

- What happens when IP Fabric appliance is unreachable? System returns clear error with connectivity troubleshooting steps.
- How does system handle expired or invalid API tokens? System returns authentication error with guidance to regenerate token.
- What if user queries a snapshot that doesn't exist? System lists available snapshots and prompts for selection.
- How does system handle requests for features not licensed in the IP Fabric instance? System reports capability unavailable with explanation.
- What if path lookup returns no path (disconnected endpoints)? System clearly indicates no path exists and suggests troubleshooting steps.
- How are large PNG diagrams handled in different channels? System adapts delivery method based on channel capabilities (file attachment for Slack/Teams/Webex, inline for supported channels).

## Requirements *(mandatory)*

### Functional Requirements

**MCP Server Configuration**

- **FR-001**: System MUST support configuration of the IP Fabric MCP Server via environment variables (IPFABRIC_HOST, IPFABRIC_API_TOKEN)
- **FR-002**: System MUST use the mcp-remote proxy to connect to the remote IP Fabric MCP endpoint over HTTPS
- **FR-003**: System MUST validate MCP connectivity on startup and report unavailable server with troubleshooting guidance
- **FR-004**: System MUST respect IP Fabric's RBAC - the skill can only access data permitted by the API token's role

**Skill Behavior**

- **FR-005**: System MUST provide a `/ipfabric` skill that auto-detects which MCP tool(s) to invoke based on natural language query
- **FR-006**: System MUST default to the most recent snapshot (`$last`) when snapshotId is required but not specified
- **FR-007**: System MUST allow users to specify a snapshot by name or UUID to override the default
- **FR-008**: System MUST provide clear error messages when the MCP is not configured or credentials are invalid
- **FR-009**: System MUST support all IP Fabric MCP tools: health assessment, path lookups (unicast, host-to-gateway, multicast), path diagrams, API discovery, and API invocation

**Diagram Handling**

- **FR-010**: System MUST handle PNG diagrams returned by path diagram tools
- **FR-011**: System MUST save diagram images to the workspace for reference
- **FR-012**: System MUST support diagram attachment to messaging channels (Slack, Teams, Webex, Discord) when delivering results

**Installation and Configuration**

- **FR-013**: install.sh MUST include a step "Enable IP Fabric Integration? [y/N]"
- **FR-014**: System MUST provide ipfabric-enable.sh script for existing installations
- **FR-015**: System MUST add MCP configuration to ~/.openclaw/openclaw.json under mcp.servers
- **FR-016**: System MUST update documentation (README, SOUL, skill docs) with IP Fabric information

**Security**

- **FR-017**: System MUST never expose API tokens to the AI model (handled by MCP server)
- **FR-018**: System MUST document that queried network data is exposed to the model for user awareness
- **FR-019**: System MUST support credential storage in environment variables with IPFABRIC_ prefix

**Cross-Platform Composition**

- **FR-020**: System MUST be composable with other NetClaw skills (SuzieQ, Batfish, Check Point, CML, GNS3)
- **FR-021**: System MUST clearly indicate when composed queries require skills that are not configured

### Key Entities

- **IP Fabric Snapshot**: A point-in-time capture of network state; queries are executed against a specific snapshot; `$last` refers to the most recent
- **Network Path**: The route traffic takes between source and destination, including all hops, interfaces, and forwarding decisions
- **Intent Rule**: A compliance check that validates network state against expected behavior (built-in or custom)
- **API Endpoint**: A specific IP Fabric REST API path with parameters and response schema, discoverable via natural language search

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can query IP Fabric network health using natural language within 30 seconds of response time for typical queries
- **SC-002**: Path analysis queries return both structured data and visual diagrams when requested
- **SC-003**: New users can enable IP Fabric integration during install.sh in under 5 minutes
- **SC-004**: Existing users can add IP Fabric support using ipfabric-enable.sh in under 2 minutes
- **SC-005**: 90% of common network queries are correctly routed to the appropriate IP Fabric tool without user intervention
- **SC-006**: System gracefully handles unavailable or misconfigured MCP, clearly indicating the issue and resolution steps
- **SC-007**: Documentation enables self-service setup without requiring support escalation for 95% of users
- **SC-008**: PNG diagrams are successfully delivered through all supported messaging channels (Slack, Teams, Webex, Discord)
- **SC-009**: Cross-platform queries (IP Fabric + other NetClaw skills) complete successfully when both data sources are configured

## Assumptions

- Users have a running IP Fabric appliance with MCP Server enabled (Settings → Integration → MCP Server)
- Users have valid IP Fabric API tokens with appropriate RBAC permissions for desired queries
- Node.js/NPM is available on the system (required to run npx mcp-remote proxy)
- Network connectivity exists between NetClaw host and IP Fabric appliance over HTTPS
- IP Fabric's MCP Server is the official supported version (built into IP Fabric appliances)
- Users understand that queried network data will be processed by the AI model
- The AI assistant will automatically use `$last` snapshot unless user specifies otherwise
- Diagram rendering capabilities in IP Fabric are available (standard feature)
