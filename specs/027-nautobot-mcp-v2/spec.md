# Feature Specification: Enhanced Nautobot MCP Server v2

**Feature Branch**: `027-nautobot-mcp-v2`
**Created**: 2026-04-09
**Status**: Complete (base), Extended (virtualization tools added 2026-05-02)
**Input**: User description: "Rewrite the Nautobot MCP server to use GraphQL for reads and REST API for writes, add device/interface/VLAN/prefix/cable queries, write operations with approval gating, and reconciliation between live device config and Nautobot source of truth. Target: Nautobot 3.1.0."

## Context

The existing mcp-nautobot (v1) provides 5 tools using the REST API: get_ip_addresses, get_prefixes, get_ip_address_by_id, search_ip_addresses, and test_connection. It covers only IPAM IP/prefix queries.

The v2 server replaces v1 with a complete Nautobot integration:
- **GraphQL API** (POST /api/graphql/) for all read operations — efficient field selection, nested relationships, single-request multi-entity queries
- **REST API** (POST/PUT/PATCH to /api/dcim/*, /api/ipam/*) for all write operations — Nautobot 3.1.0 does not expose GraphQL mutations
- Covers devices, interfaces, VLANs, prefixes, IP addresses, and cables
- ITSM-gated write operations
- Live-vs-SoT reconciliation using pyATS data

### Nautobot 3.1.0 API Facts (verified against live instance at 192.168.3.253)

- GraphQL via graphene_django 3.2.3 — queries only, no mutations
- `locations` replaces the deprecated `site` field (Nautobot 3.x change)
- REST API supports POST (create), PUT (replace), PATCH (partial update), DELETE on all DCIM/IPAM endpoints
- Authentication: `Authorization: Token <token>` header on all requests
- GraphQL filters support Django-style lookups (__ic, __isw, __re, etc.)
- Pagination via `limit`/`offset` on GraphQL queries

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query Devices and Interfaces (Priority: P1)

As a network engineer, I want to query Nautobot for device inventory (devices, interfaces, IP assignments) using natural language so I can understand what the source of truth says about my network without navigating the Nautobot web UI.

**Why this priority**: Device and interface queries are the foundational read operations. Every other capability (writes, reconciliation) depends on being able to read the current SoT state. The existing v1 server only covers IP addresses and prefixes — devices and interfaces are the most critical gap.

**Independent Test**: Can be fully tested by asking "show me all devices at location House" or "what interfaces does HomeSwitch01 have?" and verifying structured results return from Nautobot's GraphQL API.

**Acceptance Scenarios**:

1. **Given** Nautobot has device records, **When** the operator requests "show all devices", **Then** the system returns device name, role, platform, location, status, primary IP, and serial number for each device.
2. **Given** Nautobot has interface records for a device, **When** the operator requests "show interfaces on HomeSwitch01", **Then** the system returns interface name, type, enabled state, status, description, MAC address, MTU, mode, untagged VLAN, tagged VLANs, and assigned IPs.
3. **Given** a device name that does not exist in Nautobot, **When** the operator queries that device, **Then** the system returns a clear "not found" message rather than an error.
4. **Given** Nautobot has multiple devices, **When** the operator queries with filters (location, role, platform, status), **Then** only matching devices are returned.

---

### User Story 2 - Query VLANs, Prefixes, IP Addresses, and Cables (Priority: P2)

As a network engineer, I want to query Nautobot for VLANs, prefixes, IP addresses, and cable connections so I can verify Layer 2 segmentation, IP allocation, and physical topology against the source of truth.

**Why this priority**: VLANs, prefixes, and cables complete the read-side picture. Prefixes and IPs exist in v1 but lack GraphQL efficiency and nested relationship data. VLANs and cables are new and essential for reconciliation (US5).

**Independent Test**: Can be tested by asking "show VLANs at location House" or "show cables connected to HomeSwitch01" and verifying results.

**Acceptance Scenarios**:

1. **Given** Nautobot has VLAN records, **When** the operator requests "show all VLANs", **Then** the system returns VLAN ID (vid), name, status, locations, VLAN group, tenant, and role.
2. **Given** Nautobot has prefix records, **When** the operator requests "show prefixes", **Then** the system returns prefix, status, locations, role, and tenant.
3. **Given** Nautobot has IP address records, **When** the operator requests "show IP addresses on HomeSwitch01", **Then** the system returns address, status, DNS name, description, assigned interface, and VRF.
4. **Given** Nautobot has cable records, **When** the operator requests "show cables", **Then** the system returns cable ID, type, status, label, and termination endpoints (device + interface on each side).
5. **Given** a query for VLANs filtered by location, **When** no VLANs exist for that location, **Then** the system returns a clear "no VLANs found" message.

---

### User Story 3 - Create and Update Records with Approval Gating (Priority: P3)

As a network engineer, I want to create and update Nautobot records (IP addresses, VLANs, prefixes, interfaces, cables) through natural language with ITSM approval gating so that the source of truth stays current while maintaining change control.

**Why this priority**: Write operations are the key differentiator from v1 (read-only). They enable the agent to fix SoT drift discovered during reconciliation. However, reads must work first, and writes require careful safety controls. Writes use the REST API since Nautobot 3.1.0 has no GraphQL mutations.

**Independent Test**: Can be tested in lab mode by asking "add VLAN 200 named Guest at location House" and verifying the record appears in Nautobot. Production mode requires a ServiceNow CR number.

**Acceptance Scenarios**:

1. **Given** ITSM is disabled (lab mode), **When** the operator requests "create IP address 10.0.1.50/24 on HomeSwitch01 GigabitEthernet1/0/1", **Then** the IP is created in Nautobot via REST API and confirmation is returned.
2. **Given** ITSM is enabled, **When** the operator requests a write operation without a CR number, **Then** the operation is blocked with a message explaining that a ServiceNow CR is required.
3. **Given** ITSM is enabled and a valid CR number is provided, **When** the operator requests "add VLAN 200 named Guest, CR CHG0012345", **Then** the VLAN is created and the CR number is logged in the audit trail.
4. **Given** the operator requests creation of a record that already exists, **When** the REST API returns a conflict, **Then** the system returns a clear conflict message with the existing record details.
5. **Given** the operator requests an update to a device field, **When** the REST API succeeds, **Then** the system returns both old and new values for the changed fields.

---

### User Story 4 - Raw GraphQL Query (Priority: P4)

As a power user, I want to execute arbitrary GraphQL queries against Nautobot so I can access any data model — including custom fields, relationships, plugin models (BGP, golden config, firewall), and computed fields — without waiting for new tools to be added.

**Why this priority**: A generic GraphQL tool provides escape-hatch flexibility for advanced users and future-proofs the server against Nautobot schema changes and plugin additions. Lower priority because the structured tools (US1-US2) cover 90% of use cases.

**Independent Test**: Can be tested by passing a raw GraphQL query string and verifying the response matches Nautobot's GraphQL explorer output.

**Acceptance Scenarios**:

1. **Given** a valid GraphQL query string, **When** the operator invokes the raw query tool, **Then** the system returns the GraphQL response data as structured JSON.
2. **Given** a GraphQL query with variables, **When** the operator provides both query and variables, **Then** the system correctly substitutes variables and returns results.
3. **Given** an invalid GraphQL query, **When** the query is executed, **Then** the system returns the GraphQL error messages without exposing internal details.

---

### User Story 5 - Live Config vs. Nautobot Reconciliation (Priority: P5)

As a network engineer, I want to compare live device state (from pyATS) against Nautobot's source of truth so I can identify drift — undocumented interfaces, IP mismatches, missing VLANs, stale cables — and optionally fix the SoT.

**Why this priority**: Reconciliation is the highest-value workflow but depends on all previous stories (reads for Nautobot state, writes to fix drift). It also requires pyATS MCP to be functional for live device data. This is the capstone feature.

**Independent Test**: Can be tested by asking "reconcile HomeSwitch01 interfaces against Nautobot" and verifying a diff report is generated showing matches, mismatches, and missing records.

**Acceptance Scenarios**:

1. **Given** pyATS can reach HomeSwitch01 and Nautobot has records for it, **When** the operator requests "reconcile HomeSwitch01 interfaces", **Then** the system returns a structured diff showing: interfaces in both (with field-level comparison), interfaces only on device, and interfaces only in Nautobot.
2. **Given** a reconciliation finds IP address drift (device has 10.0.1.1/24 but Nautobot says 10.0.1.2/24), **When** the diff is presented, **Then** the mismatch is clearly flagged with both values and the operator can choose to update Nautobot.
3. **Given** a reconciliation finds an interface on the device that is not in Nautobot, **When** the operator approves, **Then** the missing interface is created in Nautobot via REST API with data from the live device.
4. **Given** ITSM is enabled, **When** reconciliation proposes SoT updates, **Then** all writes require CR approval before execution.

---

### Edge Cases

- What happens when the Nautobot GraphQL endpoint is unreachable or returns a connection timeout?
- How does the system handle GraphQL queries that exceed Nautobot's max query depth or complexity limits?
- What happens when the API token has read-only permissions and a REST write is attempted?
- How does the system handle Nautobot custom fields that vary between deployments?
- What happens when reconciliation runs against a device that exists in pyATS testbed but not in Nautobot?
- What happens when Nautobot returns paginated results exceeding the requested limit?
- How does the system handle the Nautobot 3.x `locations` model (which replaced `sites`)?
- What happens when a REST write requires a related object ID (e.g., status, role) that must be looked up first?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use Nautobot's GraphQL API (POST to /api/graphql/) for all read operations.
- **FR-002**: System MUST use Nautobot's REST API (POST/PATCH/DELETE to /api/dcim/*, /api/ipam/*) for all write operations, since Nautobot 3.1.0 does not expose GraphQL mutations.
- **FR-003**: System MUST support querying devices with filtering by name, location, role, platform, status, and tenant.
- **FR-004**: System MUST support querying interfaces with filtering by device, name, type, enabled state, and status.
- **FR-005**: System MUST support querying VLANs with filtering by vid, name, location, VLAN group, and tenant.
- **FR-006**: System MUST support querying prefixes with filtering by prefix, status, location, and tenant.
- **FR-007**: System MUST support querying IP addresses with filtering by address, device, interface, status, and tenant.
- **FR-008**: System MUST support querying cables with filtering by device and status.
- **FR-009**: System MUST support a raw GraphQL query tool for arbitrary read queries.
- **FR-010**: System MUST support creating and updating IP addresses, VLANs, prefixes, interfaces, and cables via REST API.
- **FR-011**: All write operations MUST be gated by ITSM approval when ITSM_ENABLED is true. Lab mode (ITSM_LAB_MODE=true) bypasses gating.
- **FR-012**: System MUST support reconciliation between live device state (via pyATS) and Nautobot records, producing a structured diff report.
- **FR-013**: System MUST authenticate using a Nautobot API token via Authorization header, read from NAUTOBOT_TOKEN environment variable.
- **FR-014**: System MUST handle API errors gracefully, returning descriptive messages without exposing credentials or internal details.
- **FR-015**: System MUST support pagination via limit/offset parameters on all list queries.
- **FR-016**: All connection credentials (NAUTOBOT_URL, NAUTOBOT_TOKEN) MUST be read from environment variables at runtime.
- **FR-017**: System MUST log all operations to stderr for debugging.
- **FR-018**: System MUST be backwards-compatible — the v2 server replaces v1 in openclaw.json with a superset of capabilities.
- **FR-019**: System MUST use `locations` (not the deprecated `site`) for all location-based queries and writes, per Nautobot 3.x data model.
- **FR-020**: For REST writes that require related object IDs (status, role, location), the system MUST look up the ID by name/slug automatically so the operator can use human-readable names.

### Key Entities

- **Device**: A network device in Nautobot with name, role, platform, location, status, primary IP, serial number, and custom fields.
- **Interface**: A physical or virtual interface on a device with name, type, enabled state, status, description, MAC address, MTU, mode (ACCESS/TAGGED/TAGGED_ALL), untagged VLAN, tagged VLANs, and IP assignments.
- **IP Address**: An IP address/prefix assigned to an interface with address, status, DNS name, description, and tenant.
- **Prefix**: A network prefix in IPAM with prefix, status, locations, role, and tenant.
- **VLAN**: A Layer 2 VLAN with vid, name, status, locations, VLAN group, tenant, and role.
- **Cable**: A physical or logical connection between two endpoints (termination_a/b as device+interface pairs) with type, status, label, and color.
- **Reconciliation Report**: A structured diff comparing live device state against Nautobot records, categorized as match/mismatch/device-only/nautobot-only.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can query any Nautobot object type (device, interface, VLAN, prefix, IP, cable) and receive results within 3 seconds.
- **SC-002**: Write operations correctly create/update Nautobot records when verified through the Nautobot web UI or subsequent read query.
- **SC-003**: ITSM gating blocks 100% of write operations when enabled and no CR is provided.
- **SC-004**: Reconciliation correctly identifies all interface/IP/VLAN differences between a live device and Nautobot when tested against HomeSwitch01/02.
- **SC-005**: The raw GraphQL tool successfully executes any valid query that works in Nautobot's GraphQL explorer (/api/graphql/).
- **SC-006**: All v1 capabilities (IP address queries, prefix queries, search, connection test) continue to work via the new tools.
- **SC-007**: All artifact coherence checklist items are complete (README, install.sh, SOUL.md, SKILL.md, .env.example, TOOLS.md, config/openclaw.json, HUD).
- **SC-008**: 100% of write operations are recorded in the GAIT audit trail.

## Assumptions

- Nautobot instance is running version 3.1.0 with GraphQL enabled (graphene_django 3.2.3, queries only).
- The Nautobot API token has both read and write permissions. If the token is read-only, write operations will fail with a clear permission error.
- Nautobot 3.1.0 does NOT expose GraphQL mutations — all writes go through the REST API.
- Nautobot 3.x uses `locations` (not `sites`) — the v2 server must use the 3.x data model throughout.
- pyATS MCP server is functional and can reach the same devices that are registered in Nautobot (required for reconciliation only).
- The Nautobot instance at 192.168.3.253 is the target deployment with 3 devices (HomeSwitch01, HomeSwitch02, pfSense-FW01), 34 VLANs, 2 prefixes, and 2 cables.
- ITSM gating follows the same pattern as other NetClaw write-capable MCP servers (ITSM_ENABLED, ITSM_LAB_MODE environment variables).
- The v2 server replaces the v1 mcp-nautobot entry in openclaw.json — it is not an additional server.
- Reconciliation compares interface names, IP addresses, enabled state, and description. VLAN assignment comparison is a stretch goal.
- Installed Nautobot plugins (bgp_models, golden_config, firewall_models, igp_models, ssot, device_onboarding) are accessible via the raw GraphQL tool but do not get dedicated structured tools in v2.
