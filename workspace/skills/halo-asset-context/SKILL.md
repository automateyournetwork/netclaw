---
name: halo-asset-context
description: "Review a HaloPSA / HaloITSM asset (Device) with its related tickets and CMDB/CI relationships — read-only. Use when investigating a Halo asset, checking a device's ticket history, mapping CI dependencies, or gathering asset context before a change."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["HALO_BASE_URL", "HALO_CLIENT_ID", "HALO_CLIENT_SECRET"] } } }
---

# Halo Asset Context

Review an **asset** in Halo together with the tickets and CMDB/CI relationships around it — entirely **read-only**. Halo is **HaloPSA / HaloITSM** (the same product and REST API); assets are called **"Devices"** in Halo's API vocabulary. Use this to build a full operational picture of a device before acting on it, correlating its history and dependencies.

## MCP Server

- **Server**: `halo-mcp` (NetClaw-authored, `mcp-servers/halo-mcp/`)
- **Command**: `python3 -u mcp-servers/halo-mcp/halo_mcp_server.py` (stdio transport)
- **Auth**: OAuth2 client-credentials — `HALO_CLIENT_ID` / `HALO_CLIENT_SECRET` against `HALO_BASE_URL`
- **Python**: 3.10+  ·  **Dependencies**: `fastmcp`, `httpx`, `python-dotenv`
- **Read/write posture**: The whole server is **read-only except one gated write** (`halo_create_change_request`, in the halo-change-request skill). **Every tool in this skill is read-only** and makes no changes to Halo.

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `halo_list_assets` | `customer?`, `assettype_id?`, `search?` | List/search assets ("Devices"), optionally scoped by customer, asset type, or free text |
| `halo_get_asset` | `asset` (name / inventory-number / id) | Read one asset — detail, fields, and ticket counts |
| `halo_get_asset_tickets` | `asset`, `open_only?` | List the tickets related to an asset — the core context tool |
| `halo_get_asset_relationships` | `asset` | An asset's CMDB/CI hierarchy and relationship context |
| `halo_list_clients` | `search?` | Resolve a Halo **Client** name to its id (the `customer` param) |
| `halo_list_sites` | `customer?`, `search?` | Narrow to a site within a client |

## Key Concepts

- **Halo == HaloPSA == HaloITSM.** Same API for both editions.
- **Assets are "Devices."** `halo_list_assets` / `halo_get_asset` accept an asset **name, inventory number, or numeric id** — you do not need the id up front.
- **The Halo "Client" is the customer.** Scope asset queries to an org with the `customer` param (a client name or id); the server resolves it to a `client_id`. In an MSP (HaloPSA) tenant this is essential to avoid crossing client boundaries.
- **Two context dimensions:** *tickets* (what has gone wrong / changed on this device) via `halo_get_asset_tickets`, and *relationships* (what this device depends on or supports) via `halo_get_asset_relationships`. Use both for a complete picture.
- **Read-only.** Nothing here writes to Halo. If the review concludes a change is needed, hand off to **halo-change-request**.

## Workflow

Review an asset and everything around it:

1. **Locate the asset.** If you only have a description or partial name, search first:
   ```
   halo_list_assets(customer="<client>", search="<name/serial/model>")
   ```
   Scope by `customer` (the Halo Client) in multi-client tenants to disambiguate.

2. **Read the asset detail:**
   ```
   halo_get_asset(asset="<name / inventory number / id>")
   ```
   Note its type, key fields, owning client/site, and ticket counts.

3. **Pull its related tickets** (the core step):
   ```
   halo_get_asset_tickets(asset="<asset>")               # all history
   halo_get_asset_tickets(asset="<asset>", open_only=true) # active issues only
   ```
   Look for recurring faults, recent changes, and open work.

4. **Map its CMDB/CI relationships:**
   ```
   halo_get_asset_relationships(asset="<asset>")
   ```
   Understand upstream dependencies and downstream impact before anyone touches it.

5. **Report** an asset-context summary: identity, owning client/site, open vs historical tickets, notable recurring issues, and CI dependencies — plus a recommendation (e.g. "raise a change via halo-change-request" or "no action").

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **gait-session-tracking** | **Mandatory.** Record every asset/ticket/relationship query in the GAIT audit trail |
| **halo-change-request** | Hand off here when the review concludes a change is warranted — pass the affected asset into the `asset` param |
| **halo-ticket-context** | Drill into any individual ticket surfaced by `halo_get_asset_tickets` for its full action history |
| **nautobot-sot** / **netbox-reconcile** | Cross-reference Halo's asset record against the network source of truth; ticket any drift |
| **memory** | Recall prior findings about the same device across sessions |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HALO_BASE_URL` | Yes | Halo host, e.g. `https://<tenant>.halopsa.com` |
| `HALO_CLIENT_ID` | Yes | OAuth2 client-credentials application id |
| `HALO_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `HALO_TENANT` | Optional | Tenant identifier |
| `HALO_SCOPE` | Optional | OAuth2 scope (default `all`) |
| `HALO_AUTH_URL` | Optional | Override the auth-server URL for self-hosted layouts |
| `HALO_VERIFY_SSL` | Optional | `true`/`false` TLS verification (default `true`) |
| `HALO_TIMEOUT` | Optional | Per-request timeout in seconds (default 30) |
| `HALO_PAGE_SIZE` / `HALO_MAX_PAGES` | Optional | Pagination tuning (defaults 50 / 20) |
| `HALO_RATE_LIMIT` | Optional | Requests/minute cap (0 = disabled) |

## Important Rules

- **Read-only skill.** None of these tools change Halo. The only write in the entire `halo-mcp` server is `halo_create_change_request` (halo-change-request skill).
- **Scope by the Halo Client.** Pass the customer org via the `customer` param to keep queries inside client boundaries — critical in MSP (HaloPSA) tenants.
- **Assets resolve by name, inventory number, or id** — no need to look up the numeric id first.
- **Halo == HaloPSA == HaloITSM** — identical behavior for both editions.
- **GAIT logging is mandatory** for all queries.
- **Escalate, don't mutate.** If the context implies a change, route it through **halo-change-request** (preview -> confirm -> submit); never try to write from this skill.
