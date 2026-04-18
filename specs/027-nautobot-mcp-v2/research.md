# Research: Enhanced Nautobot MCP Server v2

**Feature**: 027-nautobot-mcp-v2
**Date**: 2026-04-09

## R1: Nautobot 3.1.0 API Architecture

**Decision**: Use GraphQL (POST /api/graphql/) for all reads, REST API (POST/PATCH/DELETE to /api/dcim/*, /api/ipam/*) for all writes.

**Rationale**: Verified against live instance at 192.168.3.253. Nautobot 3.1.0 uses graphene_django 3.2.3 which exposes GraphQL queries but **no mutations**. The `__schema { mutationType }` introspection returns null. REST API endpoints confirm PUT and POST actions via OPTIONS requests. This hybrid approach gives us the best of both worlds: efficient field selection and nested queries for reads, and full CRUD for writes.

**Alternatives considered**:
- REST-only (like v1): Rejected because GraphQL provides dramatically better query efficiency — one request can fetch a device with all its interfaces, IPs, and VLANs instead of 4+ REST calls.
- GraphQL-only: Not possible — Nautobot 3.1.0 has no GraphQL mutations.
- Wait for Nautobot to add GraphQL mutations: Unknown timeline, blocks all write functionality.

## R2: Nautobot 3.x Data Model Changes

**Decision**: Use `locations` throughout, never `site`. Use `status` as a nested object with `name` field.

**Rationale**: Nautobot 3.x replaced the `site` model with a hierarchical `locations` model. Verified via GraphQL introspection:
- DeviceType has `location { name }` (singular)
- VLANType has `locations { name }` (plural, many-to-many)
- PrefixType has `locations { name }` (plural)
- InterfaceType has no direct location (inherited from device)

Status is always a nested object: `status { name }` returns strings like "Active", "Connected".

**Alternatives considered**:
- Support both `site` and `location`: Rejected — Nautobot 3.x removed `site` entirely.

## R3: GraphQL Query Patterns

**Decision**: Use parameterized GraphQL queries with filter arguments. Nautobot supports Django-style lookups.

**Rationale**: Verified via introspection. The `devices` query accepts filters including:
- `name`, `location`, `role`, `platform`, `status`, `tenant` — exact match by name/slug
- `name__ic`, `name__isw`, `name__re` — case-insensitive contains, starts-with, regex
- `q` — general search across multiple fields
- `limit`, `offset` — pagination
- `has_interfaces`, `has_primary_ip` — boolean existence filters

Example working query:
```graphql
{
  devices(name: "HomeSwitch01") {
    name status { name } role { name } platform { name }
    location { name } primary_ip4 { address } serial
    interfaces { name type enabled status { name } description
      mac_address mtu mode
      untagged_vlan { vid name }
      tagged_vlans { vid name }
      ip_addresses { address }
    }
  }
}
```

**Alternatives considered**:
- Using GraphQL variables ($name: String): Supported but adds complexity. Will use for the raw query tool; structured tools will use string interpolation with proper escaping.

## R4: REST API Write Patterns

**Decision**: Use REST API for all create/update/delete operations. Look up related object IDs by name before writes.

**Rationale**: REST API endpoints confirmed via OPTIONS:
- `POST /api/dcim/devices/` — create device
- `PATCH /api/dcim/devices/{id}/` — partial update
- `POST /api/dcim/interfaces/` — create interface
- `POST /api/ipam/ip-addresses/` — create IP
- `POST /api/ipam/vlans/` — create VLAN
- `POST /api/ipam/prefixes/` — create prefix
- `POST /api/dcim/cables/` — create cable

REST writes require UUIDs for related objects (status, role, location, device). The server must resolve human-readable names to UUIDs via GraphQL lookup before issuing REST writes. Example: to create an interface, we need the device UUID, which we get from `{ devices(name: "HomeSwitch01") { id } }`.

**Alternatives considered**:
- Require users to provide UUIDs: Terrible UX. The agent should resolve names automatically.
- Cache all UUIDs at startup: Fragile — data changes. Better to look up on demand.

## R5: Cable Endpoint Resolution

**Decision**: Use REST API to resolve cable endpoints since GraphQL CableType only exposes `termination_a_type`/`termination_b_type` and `termination_a_id`/`termination_b_id` as raw content-type strings and UUIDs.

**Rationale**: GraphQL CableType fields are:
- `termination_a_type` → "dcim.interface"
- `termination_a_id` → UUID string
- `termination_b_type` → "dcim.interface"
- `termination_b_id` → UUID string

To get human-readable cable endpoints (device name + interface name), we need to resolve these UUIDs. Two approaches:
1. Query cables via GraphQL, then resolve endpoint UUIDs via additional GraphQL queries
2. Query cables via REST API which includes nested endpoint details

Will use approach 1 (GraphQL + resolution) for consistency, falling back to REST if needed.

**Alternatives considered**:
- REST-only for cables: Would work but breaks the GraphQL-for-reads pattern.

## R6: Authentication

**Decision**: Use `Authorization: Token <token>` header for both GraphQL and REST requests. Token from NAUTOBOT_TOKEN env var.

**Rationale**: Standard Nautobot authentication. Same token works for both GraphQL and REST. Verified working on live instance.

## R7: HTTP Client

**Decision**: Use `httpx` with async support, same as v1.

**Rationale**: Already a dependency of v1. Supports async, SSL verification toggle, timeouts. No reason to change.

## R8: ITSM Gating Pattern

**Decision**: Follow the same ITSM gating pattern as aruba-cx-mcp and other write-capable NetClaw MCP servers.

**Rationale**: Environment variables:
- `ITSM_ENABLED` — when true, all writes require a `cr_number` parameter
- `ITSM_LAB_MODE` — when true, bypasses ITSM gating for lab/dev use

Each write tool accepts an optional `cr_number` parameter. If ITSM is enabled and no CR is provided, the tool returns an error message. The CR number is logged to GAIT.

## R9: Reconciliation Architecture

**Decision**: Reconciliation is a tool within this MCP server that orchestrates data from two sources: Nautobot (via GraphQL) and live device state (passed as input from the agent, which gets it from pyATS MCP).

**Rationale**: The reconciliation tool does NOT call pyATS directly — it accepts structured device data as input. The agent orchestrates: (1) call pyATS MCP to get live state, (2) call nautobot-mcp-v2 to get SoT state, (3) call nautobot-mcp-v2 reconcile tool with both datasets. This keeps the MCP server focused and avoids cross-MCP dependencies.

Alternative approach: a single reconcile tool that accepts just a device name and internally queries both Nautobot GraphQL and the live device data passed as a JSON parameter. This is simpler for the agent.

**Decision**: Use the single-tool approach — the reconcile tool accepts device_name + live_interfaces (JSON from pyATS), queries Nautobot internally, and returns the diff.

## R10: Existing Data in Nautobot

**Verified data on 192.168.3.253**:
- 3 devices: HomeSwitch01 (FOC1733X062), HomeSwitch02 (FOC1724V1R9), pfSense-FW01
- All at location "House", all status "Active"
- HomeSwitch01/02: role "home_switch", platform "cisco_ios"
- pfSense-FW01: role "firewall", no platform set
- 34 VLANs (1, 2, 3, 13-17, 30-31, 35, 100-104, 220-229, 300, 310-316, 3000)
- 2 prefixes: 192.168.3.0/24, 192.168.100.0/24
- 2 cables (interface-to-interface)
- Interfaces with full detail: type, enabled, status, description, MAC, MTU, mode, VLAN assignments
- Plugins: bgp_models, golden_config, firewall_models, igp_models, ssot, device_onboarding, design_builder
