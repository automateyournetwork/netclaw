---
name: infrahub-sot
description: "OpsMill Infrahub — infrastructure source of truth with schema-driven nodes, GraphQL queries, and branch-isolated changes. Use when querying Infrahub for device/IPAM inventory, browsing infrastructure schemas, running GraphQL queries, or making infrastructure changes safely via an auto-created session branch and a Proposed Change for human review."
version: 2.0.0
license: Apache-2.0
tags: [opsmill, infrahub, source-of-truth, infrastructure, graphql, schema, branches, ipam, dcim]
---

# Infrahub Source of Truth

## MCP Server

- **Repository**: [opsmill/infrahub-mcp](https://github.com/opsmill/infrahub-mcp)
- **Version**: 1.1.7+ (reworked — first stable release + production hardening)
- **Distribution**: PyPI (`pip install infrahub-mcp`), Docker (`registry.opsmill.io/opsmill/infrahub-mcp`), or from source
- **Entry point**: `infrahub-mcp` console script
- **Transport**: `stdio` (default) or `streamable-http` (remote clients / auth modes)
- **Requires**: `INFRAHUB_ADDRESS` + (`INFRAHUB_API_TOKEN` *or* `INFRAHUB_USERNAME`+`INFRAHUB_PASSWORD`)
- **Python**: 3.13+
- **Dependencies**: `fastmcp>=3.2.0`, `infrahub-sdk>=1.20.0`
- **Docs**: [docs.infrahub.app/mcp](https://docs.infrahub.app/mcp) (per-client setup, auth, configuration)

> **What changed in the rework**: the server moved to a modular `src/infrahub_mcp/` layout on
> FastMCP 3.x, added a **branch-isolated write model** (writes never touch the default branch),
> exposes **MCP resources and prompts** in addition to tools, serializes schema output with **TOON**
> internally to cut tokens, and ships as a **PyPI package + Docker image** with optional auth,
> rate limiting, caching, and OpenTelemetry/Prometheus observability. The old read-only tool
> surface (`get_node_filters`, `get_related_nodes`, `get_schema_mapping`, `get_schemas`,
> `get_graphql_schema`, `get_branches`, `branch_create`) has been replaced — see the table below.

## How Infrahub Differs

Infrahub is not just another IPAM/DCIM tool. Key differentiators:

- **Schema-driven** — define your own infrastructure models (not just built-in IPAM/DCIM). Devices, circuits, IP addresses, services, cloud resources — any infrastructure object can be modeled.
- **Versioned branches** — Git-like branching for infrastructure data. Changes are made on a branch, reviewed as a diff, and merged when approved. No more "who changed this in production?"
- **GraphQL-native** — full GraphQL API for flexible queries, not just REST. Query exactly the fields you need, traverse relationships in a single request.
- **Relationship-first** — rich relationship model between objects with relationship-level filters and traversal.

## Safety Model: Branch-Isolated Writes

The reworked server makes destructive operations safe by construction:

- **Writes never hit the default branch.** On the first write in a session, the server lazily
  auto-creates a session branch named `mcp/session-YYYYMMDD-<hex>` (pattern configurable via
  `INFRAHUB_MCP_BRANCH_PATTERN`). All `node_upsert` / `node_delete` / `mutate_graphql` land there.
- **Human review is mandatory to merge.** `propose_changes` opens a **Proposed Change** (PR) from
  the session branch to the default branch — a human reviews and merges it in the Infrahub UI. The
  agent never merges.
- **Session-branch recovery.** Stale/merged/deleted session branches are validated before reuse and
  auto-recovered on the next write; `reset_session_branch` clears or switches the active branch.
- **Read-only mode.** Setting `INFRAHUB_MCP_READ_ONLY=true` hides all write tools and blocks GraphQL
  mutations — use it for pure analysis/audit connections.

## MCP Tools (10 tools)

### Read Tools (5)

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_nodes` | `kind, filters?, partial_match?, include_attributes?, offset?, limit?, branch?` | Typed read of nodes of a kind. Supports attribute/relationship filters (`attr__value`, `rel__attr__value`), partial matching, and paging (returns `total_count`/`has_more`). |
| `search_nodes` | `kind, value, branch?` | Find nodes of a kind by partial substring via Infrahub's `any__value` filter. Works on concrete and abstract/generic kinds. |
| `get_schema` | `kind?, branch?` | Discover schema kinds (catalog) or, given a `kind`, its attributes/relationships/filter-map (TOON-encoded). Tool fallback for clients without MCP resources. |
| `get_session_info` | none | Report current session state — active `session_branch`, `infrahub_address`, `has_session_branch`. Call before writes to know the target branch. |
| `query_graphql` | `query, branch?` | Execute a **read-only** GraphQL query (mutations are rejected here). |

### Write Tools (5) — hidden when `INFRAHUB_MCP_READ_ONLY=true`

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `node_upsert` | `kind, data, ...` | Create or update a node on the active session branch. |
| `node_delete` | `kind, id` | Delete a node on the active session branch. |
| `mutate_graphql` | `mutation, ...` | Execute a GraphQL mutation (relationship edits / bulk ops typed tools can't express). Branch/schema-management mutations are blocked. |
| `propose_changes` | `title?, description?` | Open a Proposed Change from the session branch to the default branch for human review. |
| `reset_session_branch` | `branch?` | Clear the cached session branch (next write creates a fresh one) or point the session at a named branch. Rejects the default branch and merged/read-only branches. |

### Resources (3 + 1 template)

| Resource URI | Content |
|--------------|---------|
| `infrahub://schema` | Kind catalog (JSON) |
| `infrahub://schema/{kind}` | Per-kind schema + filter map (template) |
| `infrahub://graphql-schema` | Full GraphQL SDL (text) |
| `infrahub://branches` | All branches including the session branch (JSON) |

### Prompts (4)

`infrahub_agent` (system prompt; read-only vs read-write aware), `answer_infra_question`,
`make_infra_change`, `explore_schema`.

## Workflow: Discover Available Data

When first connecting to Infrahub:

1. **List kinds**: read resource `infrahub://schema` (or `get_schema` with no `kind`) — what infrastructure types are modeled?
2. **Inspect schema**: `get_schema(kind="InfraDevice")` — what attributes and relationships does a device have?
3. **Get nodes**: `get_nodes(kind="InfraDevice")` — list all devices (page with `offset`/`limit`).
4. **Report**: infrastructure data model overview with node counts per kind.

## Workflow: Infrastructure Audit

When auditing infrastructure state in Infrahub:

1. **Schema overview**: `get_schema` (no kind) — discover all kinds.
2. **Device inventory**: `get_nodes(kind="InfraDevice")` — all devices.
3. **IP addresses**: `get_nodes(kind="InfraIPAddress")` — all IPs (if IPAM is modeled).
4. **Prefixes**: `get_nodes(kind="InfraPrefix")` — all subnets.
5. **Search**: `search_nodes(kind="InfraDevice", value="core")` — fuzzy find by substring.
6. **Report**: infrastructure inventory from Infrahub with relationship context.

## Workflow: Branch-Isolated Change

When proposing an infrastructure change (the safe write path):

1. **Check session**: `get_session_info` — see the active session branch (or that none exists yet).
2. **Make changes**: `node_upsert(...)`, `node_delete(...)`, or `mutate_graphql(...)`. The first
   write **auto-creates** the `mcp/session-*` branch — you never edit the default branch directly.
3. **Verify**: `get_nodes(...)` on the session branch — confirm changes look correct.
4. **Propose**: `propose_changes(title="Add VLAN 200", description="...")` — opens a Proposed
   Change for human review.
5. **Human merges** in the Infrahub UI. To start a fresh unrelated change, call
   `reset_session_branch`.
6. **Report**: change summary + the Proposed Change link for review.

## Workflow: GraphQL Exploration

When building custom queries:

1. **Schema**: read resource `infrahub://graphql-schema` — full SDL, understand query structure.
2. **Test query**: `query_graphql(query="{ InfraDevice { edges { node { name { value } } } } }")`.
3. **Filtered query**: `query_graphql(query="{ InfraDevice(name__value: \"core-rtr\") { ... } }")`.
4. **Mutations** go through `mutate_graphql` (write tool) and land on the session branch — never `query_graphql`.
5. **Report**: custom data extraction with exactly the fields needed.

## Companion: infrahub-skills Plugin

The MCP server is for **live data** — querying and changing a running Infrahub instance. For
**authoring the artifacts** that define and validate that data, use the OpsMill
[**infrahub-skills**](https://github.com/opsmill/infrahub-skills) plugin (`infrahub@opsmill`, 12
skills). Rule of thumb: **`infrahub-sot` (this skill / the MCP) reads and changes live data;
`infrahub-skills` writes the files** (schemas, checks, transforms, generators) that shape it.

| Need | Use |
|------|-----|
| Query live nodes / IPAM, run GraphQL, make a branch-isolated change | **`infrahub-sot`** (this skill, MCP-backed) |
| Analyze/correlate live data, drift & impact analysis | `infrahub-analyzing-data` (also MCP-backed) |
| Design/validate schema YAML (nodes, generics, relationships) | `infrahub-managing-schemas` |
| Populate object data YAML (devices, sites, orgs) | `infrahub-managing-objects` |
| Write validation checks for Proposed Change pipelines | `infrahub-managing-checks` |
| Build transforms / Jinja2 config artifacts | `infrahub-managing-transforms` |
| Build design-driven generators | `infrahub-managing-generators` |
| Custom web-UI menus | `infrahub-managing-menus` |
| Audit an Infrahub repo against best practices | `infrahub-auditing-repo` |
| Import CSV/TSV into object YAML | `infrahub-importing-data` |
| File a bug/feature to the right `opsmill/infrahub-*` repo | `infrahub-reporting-issues` |
| Collect a redacted diagnostic bundle for support | `infrahub-collecting-diagnostics` |

Install: `npx skills add opsmill/infrahub-skills` (cross-tool) or, in Claude Code,
`/plugin marketplace add opsmill/claude-marketplace` then `/plugin install infrahub@opsmill`.
Only `infrahub-analyzing-data` requires a connected Infrahub MCP server; the rest are
file-authoring/reading and pair naturally with this skill's live-data workflows.

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
| `servicenow-change-workflow` | Infrahub Proposed Changes map to ServiceNow CRs — one session branch per change |
| `gait-session-tracking` | Record all Infrahub queries, session-branch writes, and Proposed Changes |

## Infrahub vs NetBox vs Nautobot

NetClaw supports all three source-of-truth platforms:

| Feature | NetBox | Nautobot | Infrahub |
|---------|--------|----------|----------|
| Origin | DigitalOcean / NetBox Labs | Network to Code | OpsMill |
| Data model | Fixed DCIM/IPAM + custom fields | Fixed DCIM/IPAM + Jobs + custom fields | Fully schema-driven (define any model) |
| Versioning | No branching | No branching | Git-like branches for data |
| API | REST + GraphQL | REST + GraphQL | GraphQL-native |
| MCP tools | Read-write via FastMCP | Read-only IPAM (5 tools) | Read + branch-isolated write + Proposed Changes (10 tools) |
| Use when | Standard IPAM/DCIM | Standard IPAM/DCIM (NTC ecosystem) | Custom infrastructure models, versioned & reviewed changes |

## Important Rules

- **Discover before querying** — read `infrahub://schema` (or `get_schema` with no kind) first to learn what kinds exist. Don't guess kind names, then `get_schema(kind=...)` for its filters.
- **Never write on the default branch** — use the write tools (`node_upsert` / `node_delete` / `mutate_graphql`). They land on the auto-created session branch by design; `query_graphql` is read-only.
- **Always propose, never merge** — finish a change with `propose_changes` and hand the Proposed Change to a human. The agent does not merge to the default branch.
- **Check the session first** — `get_session_info` before writes to see the target branch; `reset_session_branch` to start a clean, unrelated change.
- **Mutations need write permission** — the token/user must have write rights for `node_upsert`, `node_delete`, and `mutate_graphql`.
- **Read-only when auditing** — connect with `INFRAHUB_MCP_READ_ONLY=true` for pure analysis so write tools are unavailable.
- **Partial matching** — use `partial_match=True` in `get_nodes`, or `search_nodes`, for fuzzy value matching.
- **Record in GAIT** — log all Infrahub queries, session-branch writes, and Proposed Changes.

## Environment Variables

**Connection / credentials** (consumed by `infrahub-sdk`; no prefix):

- `INFRAHUB_ADDRESS` — **required**, Infrahub instance URL (e.g., `http://infrahub.example.com:8000`)
- `INFRAHUB_API_TOKEN` — API token auth, **or**
- `INFRAHUB_USERNAME` + `INFRAHUB_PASSWORD` — username/password auth (one auth method required)

**Server behavior** (pydantic-settings, prefix `INFRAHUB_MCP_`; defaults shown):

- `INFRAHUB_MCP_READ_ONLY` (`false`) — hide write tools and block GraphQL mutations
- `INFRAHUB_MCP_BRANCH_PATTERN` (`mcp/session-{date}-{hex}`) — session-branch naming; `INFRAHUB_MCP_MAX_BRANCH_RETRIES` (`5`)
- `INFRAHUB_MCP_LOG_LEVEL` (`info`)
- Rate limiting / retries: `INFRAHUB_MCP_RATE_LIMIT_RPS`, `INFRAHUB_MCP_RATE_LIMIT_BURST`, `INFRAHUB_MCP_RETRY_MAX_ATTEMPTS`, `INFRAHUB_MCP_RETRY_BASE_DELAY`
- Caching: `INFRAHUB_MCP_CACHE_ENABLED` (`false`), `INFRAHUB_MCP_CACHE_LIST_TTL`, `INFRAHUB_MCP_CACHE_READ_TTL`
- Observability: `INFRAHUB_MCP_OTEL_ENABLED`, `INFRAHUB_MCP_PROMETHEUS_ENABLED`
- Auth (non-`none` modes require `streamable-http`): `INFRAHUB_MCP_AUTH_MODE` (`none`|`oidc`|`token-passthrough`|`basic-passthrough`) plus OIDC settings (`INFRAHUB_MCP_OIDC_CONFIG_URL`, `INFRAHUB_MCP_OIDC_CLIENT_ID`, `INFRAHUB_MCP_OIDC_BASE_URL`, …)

**Transport flags**: `--transport {stdio,streamable-http}` (default `stdio`), `--host` (default `127.0.0.1`), `--port` (default `8001`).
