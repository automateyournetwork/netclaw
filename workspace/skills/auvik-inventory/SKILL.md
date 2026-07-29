---
name: auvik-inventory
description: "Auvik device, network, interface, and component inventory across MSP tenants — including entity notes, audit logs, and billing usage. Use when discovering what devices Auvik manages, listing networks or interfaces, checking component health, reviewing annotated entity notes, auditing who changed managed entities, or pulling billing/usage data for a date range."
license: Apache-2.0
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["AUVIK_USERNAME", "AUVIK_API_KEY", "AUVIK_BASE_URL"] } } }
---

# Auvik Inventory

Discover and document everything Auvik manages: devices, networks, interfaces, hardware components, entity notes, audit history, and billing usage. Works across MSP multi-tenant environments — scope to a single client or sweep all visible tenants.

## MCP Server

- **Server**: `auvik-mcp` (NetClaw MCP, Feature 036)
- **Command**: `python3 mcp-servers/auvik-mcp/auvik_mcp_server.py` (stdio transport)
- **Auth**: Basic auth via `AUVIK_USERNAME` + `AUVIK_API_KEY`
- **Read-only**: GET operations only — no create, update, or delete

## Available Tools

| Tool | What It Does |
|------|--------------|
| `auvik_verify_credentials` | Health-check the API connection; verify credentials before any session |
| `auvik_list_tenants` | List all tenants (MSP clients) visible to the API key; source of truth for `tenants` values |
| `auvik_list_devices` | List or inspect discovered devices at `info`, `detail`, or `extended` level; resolve by name, IP, or ID |
| `auvik_list_networks` | List networks at `info` or `detail` level; filter by type, scan status, or associated devices |
| `auvik_list_interfaces` | List network interfaces; filter by parent device name/IP, interface type, or operational status |
| `auvik_list_components` | List hardware components (CPU, memory, disk, fan, PSU); filter by device or component status |
| `auvik_list_entity_notes` | List notes attached to devices, networks, or interfaces; filter by entity name or type |
| `auvik_list_entity_audits` | List audit log entries for managed entities; filter by user, category, status, or date |
| `auvik_get_usage` | Billing/usage data for a date range; `scope=client` (all devices) or `scope=device` (single device) |

## Key Concepts

**Tenants = MSP clients.** Auvik is built for MSPs — each managed customer is a separate tenant. Most tools accept an optional `tenants` parameter (a tenant name or domain prefix). Omit it to query across all visible tenants; provide it to scope results to a single client.

**Identifier resolution.** Pass device names, hostnames, IP addresses, or partial names to `device`, `network`, `interface`, or `parent_device` parameters — the server resolves them to internal Auvik IDs. If a name matches multiple records, the tool returns `ResolutionCandidate[]` so you can narrow the query. If you already know the Auvik numeric ID (6+ digits), it is used directly.

**Cursor pagination.** List tools auto-aggregate all pages up to `AUVIK_MAX_PAGES` (default 50). The response includes `truncated: true` and a `next_cursor` when the cap is hit. Use `fetch_all=false` + `page_first` to page manually, or raise `AUVIK_MAX_PAGES` in `.env` for large inventories.

**`detail_level` on devices.** `info` returns basic fields; `detail` adds management status and discovery settings; `extended` adds richer hardware data but **requires** the `device_type` filter (Auvik API enforcement).

## Workflow

### Onboard a New MSP Client

1. **Verify connection**: `auvik_verify_credentials` — confirm API key is valid
2. **List tenants**: `auvik_list_tenants` — identify the new client's tenant name/domain prefix
3. **Discover devices**: `auvik_list_devices` with `tenants=<client>` and `detail_level=detail`
4. **List networks**: `auvik_list_networks` with `tenants=<client>` — map the IP topology
5. **List interfaces**: `auvik_list_interfaces` with `parent_device=<core-switch-name>` — enumerate uplinks
6. **Check components**: `auvik_list_components` with `tenants=<client>` — identify hardware health
7. **Pull entity notes**: `auvik_list_entity_notes` with `tenants=<client>` — surface existing annotations
8. **Record in GAIT**: log discovered inventory and any notes as a baseline commit

### Audit a Device Change

1. **Pull audit log**: `auvik_list_entity_audits` with `tenants=<client>` + `modified_after=<date>`
2. **Filter by user**: add `user=<email>` to isolate a specific administrator's actions
3. **Cross-reference notes**: `auvik_list_entity_notes` on the affected device to see current annotations
4. **Record in GAIT**: commit the audit trail with findings

### Billing Usage Review

1. **List tenants**: `auvik_list_tenants` — confirm tenant names
2. **Client usage**: `auvik_get_usage` with `scope=client`, `from_date=<YYYY-MM-DD>`, `thru_date=<YYYY-MM-DD>`, `tenants=<client>`
3. **Device usage**: `auvik_get_usage` with `scope=device`, `device=<hostname>`, `from_date=`, `thru_date=` for a single device
4. **Record in GAIT**: commit usage figures for billing reconciliation

## Integration with Other Skills

| Skill | How They Work Together |
|-------|------------------------|
| `gait-session-tracking` | **Mandatory** — start a branch before querying, record every turn, close with `gait_log` |
| `auvik-network-alerts` | After inventorying devices, check active alerts against the discovered asset list |
| `auvik-lifecycle` | Cross-reference device inventory against EoL/warranty data to identify at-risk assets |
| `auvik-performance` | Use device names discovered here as `device` params in performance queries |
| `netbox-reconcile` | Compare Auvik-discovered inventory against NetBox SoT to surface drift |
| `servicenow-change-workflow` | Correlate audit log entries with approved ServiceNow change records |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AUVIK_USERNAME` | Yes | Auvik user email (Basic-auth username) |
| `AUVIK_API_KEY` | Yes | Auvik API key (Basic-auth password) |
| `AUVIK_BASE_URL` | No | Regional cluster URL; defaults to `https://auvikapi.us1.my.auvik.com` — swap `us1` for your region |
| `AUVIK_VERIFY_SSL` | No | Set `false` to skip TLS verification (not recommended) |
| `AUVIK_TIMEOUT` | No | HTTP timeout in seconds (default: `30`) |
| `AUVIK_MAX_PAGES` | No | Pagination safety cap (default: `50`) |

## Important Rules

- **Read-only** — this skill never modifies Auvik data. No create, update, or delete operations exist.
- **Refer to assets by name or IP**, not by Auvik internal IDs. The resolver handles ID lookup automatically; IDs in prompts are fragile and tenant-specific.
- **Always scope to a tenant** when working in an MSP environment. Omitting `tenants` returns cross-tenant results, which can be noisy and may expose one client's data in another's context.
- **`detail_level=extended` requires `device_type`** — the Auvik API enforces this; omitting it returns a `ValidationError`.
- **Record every session in GAIT** — all inventory discoveries, audit findings, and usage pulls must be committed to the audit trail.
