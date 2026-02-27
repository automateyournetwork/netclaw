---
name: infrahub-sot
description: OpsMill Infrahub — infrastructure source of truth with versioned branches, schema-driven nodes, GraphQL queries, relationship traversal
version: 1.0.0
tags: [opsmill, infrahub, source-of-truth, infrastructure, graphql, schema, branches, ipam, dcim]
---

# Infrahub Source of Truth

Query and manage infrastructure data in OpsMill Infrahub — a versioned, schema-driven infrastructure source of truth. Discover schema kinds, retrieve nodes with rich filtering, traverse relationships, execute arbitrary GraphQL queries, and manage branches for change isolation. Infrahub combines IPAM, DCIM, and custom infrastructure models with Git-like branching for safe, auditable infrastructure changes.

## MCP Server

- **Repository**: [opsmill/infrahub-mcp](https://github.com/opsmill/infrahub-mcp)
- **Transport**: stdio via FastMCP (also supports HTTP on configurable port)
- **Requires**: `INFRAHUB_ADDRESS`, `INFRAHUB_API_TOKEN`
- **Python**: 3.13+
- **Dependencies**: `fastmcp`, `infrahub_sdk`

## How Infrahub Differs

Infrahub is not just another IPAM/DCIM tool. Key differentiators:

- **Schema-driven** — define your own infrastructure models (not just built-in IPAM/DCIM). Devices, circuits, IP addresses, services, cloud resources — any infrastructure object can be modeled.
- **Versioned branches** — Git-like branching for infrastructure data. Make changes on a branch, review diffs, merge when approved. No more "who changed this in production?"
- **GraphQL-native** — full GraphQL API for flexible queries, not just REST. Query exactly the fields you need, traverse relationships in a single request.
- **Relationship-first** — rich relationship model between objects with relationship-level filters and traversal.

## MCP Tools (10 tools)

### Node Operations (3 tools)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_nodes` | `kind, branch?, filters?, partial_match?` | Retrieve all objects of a specific kind with optional filtering and partial matching |
| `get_node_filters` | `kind, branch?` | List available filters for a kind — attribute filters (`attr__value`), relationship filters (`rel__attr__value`) |
| `get_related_nodes` | `kind, relation, filters?, branch?` | Traverse a relationship from a node kind — get connected objects (peers, members, interfaces, etc.) |

### Schema Operations (3 tools)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_schema_mapping` | `branch?` | List all schema node kinds and generics available in Infrahub (discover what data types exist) |
| `get_schema` | `kind, branch?` | Full schema for a specific kind — attributes, relationships, their types (understand the data model) |
| `get_schemas` | `branch?, exclude_profiles?, exclude_templates?` | Retrieve all schemas, optionally excluding profiles and templates |

### GraphQL Operations (2 tools)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_graphql_schema` | none | Retrieve the full GraphQL schema from Infrahub (SDL format) |
| `query_graphql` | `query, branch?` | Execute an arbitrary GraphQL query against Infrahub — full flexibility for complex queries |

### Branch Operations (2 tools)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_branches` | none | List all branches in Infrahub with their details |
| `branch_create` | `name, sync_with_git?` | Create a new branch for isolated infrastructure changes |

## Workflow: Discover Available Data

When first connecting to Infrahub:

1. **List kinds**: `get_schema_mapping` — what infrastructure types are modeled?
2. **Inspect schema**: `get_schema(kind="InfraDevice")` — what attributes and relationships does a device have?
3. **List filters**: `get_node_filters(kind="InfraDevice")` — how can I query devices?
4. **Get nodes**: `get_nodes(kind="InfraDevice")` — list all devices
5. **Report**: infrastructure data model overview with node counts per kind

## Workflow: Infrastructure Audit

When auditing infrastructure state in Infrahub:

1. **Schema overview**: `get_schema_mapping` — discover all kinds
2. **Device inventory**: `get_nodes(kind="InfraDevice")` — all devices
3. **IP addresses**: `get_nodes(kind="InfraIPAddress")` — all IPs (if IPAM is modeled)
4. **Prefixes**: `get_nodes(kind="InfraPrefix")` — all subnets
5. **Relationships**: `get_related_nodes(kind="InfraDevice", relation="interfaces")` — device interfaces
6. **Report**: infrastructure inventory from Infrahub with relationship context

## Workflow: Branch-Based Change

When proposing an infrastructure change:

1. **List branches**: `get_branches` — see existing branches
2. **Create branch**: `branch_create(name="change-123-add-vlan")` — isolate changes
3. **Query current state**: `get_nodes(kind="InfraVLAN", branch="change-123-add-vlan")` — view on branch
4. **Make changes via GraphQL**: `query_graphql(query="mutation { ... }", branch="change-123-add-vlan")`
5. **Verify**: `get_nodes` on branch — confirm changes look correct
6. **Merge**: (via Infrahub UI/API — merge branch to main)
7. **Report**: change summary with before/after branch comparison

## Workflow: GraphQL Exploration

When building custom queries:

1. **Schema**: `get_graphql_schema` — full SDL schema, understand query structure
2. **Test query**: `query_graphql(query="{ InfraDevice { edges { node { name { value } } } } }")`
3. **Filtered query**: `query_graphql(query="{ InfraDevice(name__value: \"core-rtr\") { ... } }")`
4. **Nested relationships**: traverse in a single query via GraphQL nesting
5. **Report**: custom data extraction with exactly the fields needed

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `netbox-reconcile` | Infrahub as primary SoT, NetBox as legacy — compare and migrate |
| `nautobot-sot` | Infrahub as primary SoT, Nautobot as legacy — compare IPAM data |
| `pyats-topology` | Infrahub provides intended state; pyATS discovers actual device state for reconciliation |
| `pyats-network` | Cross-reference Infrahub infrastructure model with live device configs |
| `pyats-routing` | Validate routing table entries against Infrahub prefix/IP allocations |
| `aci-fabric-audit` | Infrahub fabric model vs ACI actual state |
| `meraki-network-ops` | Infrahub planned state vs Meraki actual DHCP/VLAN assignments |
| `aws-network-ops` | Infrahub cloud model vs AWS VPC actual state |
| `radkit-remote-access` | Use Infrahub to identify device IPs, then RADKit for remote CLI access |
| `servicenow-change-workflow` | Infrahub branches map to ServiceNow CRs — create branch per change |
| `gait-session-tracking` | Record all Infrahub queries, branch operations, and infrastructure changes |

## Infrahub vs NetBox vs Nautobot

NetClaw supports all three source-of-truth platforms:

| Feature | NetBox | Nautobot | Infrahub |
|---------|--------|----------|----------|
| Origin | DigitalOcean / NetBox Labs | Network to Code | OpsMill |
| Data model | Fixed DCIM/IPAM + custom fields | Fixed DCIM/IPAM + Jobs + custom fields | Fully schema-driven (define any model) |
| Versioning | No branching | No branching | Git-like branches for data |
| API | REST + GraphQL | REST + GraphQL | GraphQL-native |
| MCP tools | Read-write via FastMCP | Read-only IPAM (5 tools) | Read + GraphQL mutations + branches (10 tools) |
| Use when | Standard IPAM/DCIM | Standard IPAM/DCIM (NTC ecosystem) | Custom infrastructure models, versioned changes |

## Important Rules

- **Discover before querying** — always call `get_schema_mapping` first to learn what kinds exist. Don't guess kind names.
- **Use filters** — call `get_node_filters` to learn valid filter syntax before using `get_nodes` with filters.
- **Branch for changes** — create a branch before making mutations via `query_graphql`. Never mutate main directly.
- **GraphQL mutations require authorization** — ensure the API token has write permissions for mutation queries.
- **Partial matching** — use `partial_match=True` in `get_nodes` for fuzzy matching on filter values.
- **Relationship traversal** — use `get_related_nodes` to follow relationships; use `get_schema` to discover relationship names first.
- **Record in GAIT** — log all Infrahub queries, branch operations, and infrastructure changes.

## Environment Variables

- `INFRAHUB_ADDRESS` — Infrahub instance URL (e.g., `http://infrahub.example.com:8000`)
- `INFRAHUB_API_TOKEN` — Infrahub API authentication token
- `MCP_HOST` — Server bind address when running in HTTP mode (default: `0.0.0.0`, optional)
- `MCP_PORT` — Server port when running in HTTP mode (default: `8001`, optional)
