---
name: auvik-lifecycle
description: "Auvik device end-of-life posture, warranty/service coverage, and configuration backup history for refresh and renewal planning. Use when identifying devices past or approaching end-of-life, auditing warranty and service contract coverage, reviewing configuration backup history, planning hardware refreshes, or preparing QBR lifecycle reports for MSP clients."
license: Apache-2.0
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["AUVIK_USERNAME", "AUVIK_API_KEY", "AUVIK_BASE_URL"] } } }
---

# Auvik Device Lifecycle

Assess the end-of-life posture, warranty and service contract coverage, and configuration backup history of Auvik-managed devices. Supports hardware refresh planning, renewal pipeline management, and QBR lifecycle reporting across MSP tenants.

## MCP Server

- **Server**: `auvik-mcp` (NetClaw MCP, Feature 036)
- **Command**: `python3 mcp-servers/auvik-mcp/auvik_mcp_server.py` (stdio transport)
- **Auth**: Basic auth via `AUVIK_USERNAME` + `AUVIK_API_KEY`
- **Read-only**: GET operations only — no lifecycle record modifications

## Available Tools

| Tool | What It Does |
|------|--------------|
| `auvik_list_device_lifecycle` | EoL and last-support posture for managed devices; filter by `sales_availability`, `software_maintenance_status`, `security_software_maintenance_status`, or `last_support_status` |
| `auvik_list_device_warranty` | Warranty and service contract coverage; filter by `covered_under_warranty` (bool) or `covered_under_service` (bool) |
| `auvik_list_configurations` | Configuration backup history; `config_id` retrieves the full backup body; filter by device, backup time window, or `is_running` (running vs. startup config) |

## Key Concepts

**Tenants = MSP clients.** All three tools accept an optional `tenants` parameter (name or domain prefix). Omit it to query all visible tenants; provide it to scope to a single client.

**Identifier resolution.** The `device` parameter on all three tools accepts a hostname, IP address, partial name, or Auvik numeric ID. The server resolves names and IPs to internal IDs automatically. Ambiguous matches return `ResolutionCandidate[]`.

**Lifecycle status fields.** `auvik_list_device_lifecycle` surfaces four independent status dimensions:
- `sales_availability` — whether the device is still sold by the vendor
- `software_maintenance_status` — whether the OS/firmware receives updates
- `security_software_maintenance_status` — whether security patches are still released
- `last_support_status` — whether the vendor still provides any support

**Warranty vs. service.** `auvik_list_device_warranty` distinguishes between manufacturer warranty (`covered_under_warranty`) and service contracts such as SMARTnet or NBD (`covered_under_service`). A device may have one, both, or neither.

**Configuration backups.** `auvik_list_configurations` returns a list of backup records. Retrieve the full configuration text by passing the `config_id` of a specific record. Use `is_running=true` to filter for running-config backups vs. startup-config. Combine `backup_time_after` and `backup_time_before` (ISO-8601) to bound a review window.

**Cursor pagination.** List tools auto-aggregate all pages up to `AUVIK_MAX_PAGES`. Narrow filters (e.g., a specific tenant + device) to manage response size on large inventories.

## Workflow

### Hardware Refresh Planning

1. **Start GAIT branch**: `gait_branch` with name like `auvik-lifecycle-review-<client>-2026-06-21`
2. **List all lifecycle data**: `auvik_list_device_lifecycle` with `tenants=<client>` — no status filter to capture full picture
3. **Identify at-risk devices**: re-run with `last_support_status=endOfLife` to isolate unsupported hardware
4. **Check warranty gaps**: `auvik_list_device_warranty` with `covered_under_warranty=false`, `covered_under_service=false` to find completely uncovered devices
5. **Cross-reference inventory**: `auvik-inventory` (`auvik_list_devices`) with `detail_level=detail` to get make/model, install location, and online status
6. **Record in GAIT**: commit a refresh candidate list with device names, EoL dates, and warranty status

### QBR Lifecycle Report for an MSP Client

1. **Pull lifecycle posture**: `auvik_list_device_lifecycle` with `tenants=<client>` — all devices
2. **Pull warranty summary**: `auvik_list_device_warranty` with `tenants=<client>` — coverage per device
3. **Identify immediate risk**: filter `last_support_status=endOfLife` + `covered_under_service=false` — highest-priority refresh candidates
4. **Identify upcoming risk**: filter `software_maintenance_status=endOfSoftwareMaintenance` — devices losing patch support soon
5. **Record in GAIT**: commit QBR lifecycle data with client name and report date

### Configuration Backup Audit

1. **List recent backups**: `auvik_list_configurations` with `tenants=<client>`, `backup_time_after=<7-days-ago>` — verify backups are occurring
2. **Check running config**: `auvik_list_configurations` with `device=<hostname>`, `is_running=true` — list running-config backup records
3. **Retrieve backup body**: `auvik_list_configurations` with `config_id=<id>` — retrieve full configuration text for a specific backup
4. **Spot-check after a change window**: narrow `backup_time_after` and `backup_time_before` around a maintenance window to confirm configs were captured
5. **Record in GAIT**: commit backup verification results with timestamps

## Integration with Other Skills

| Skill | How They Work Together |
|-------|------------------------|
| `gait-session-tracking` | **Mandatory** — start a branch before querying, record every turn, close with `gait_log` |
| `auvik-inventory` | Enrich lifecycle findings with device make/model, online status, and network location |
| `auvik-network-alerts` | Recurring alerts on EoL or unwarranted devices signal accelerated refresh priority |
| `netbox-reconcile` | Compare Auvik lifecycle data against NetBox SoT to update asset records with EoL and warranty fields |
| `servicenow-change-workflow` | Raise change requests for refresh projects; link lifecycle findings to hardware replacement CRs |

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

- **Read-only** — this skill cannot update lifecycle records, warranty data, or trigger configuration backups. All data reflects what Auvik has already collected.
- **Refer to devices by name or IP**, not by Auvik internal IDs. Pass `device=<hostname-or-IP>` and let the resolver do the lookup.
- **Scope to a tenant** in MSP environments to avoid mixing lifecycle data across clients.
- **`config_id` is required to retrieve backup content** — `auvik_list_configurations` without `config_id` returns metadata only (timestamps, device, backup type); the full configuration text is only returned when a specific `config_id` is provided.
- **Record every session in GAIT** — refresh planning decisions, QBR data pulls, and configuration audit results all go to the audit trail.
