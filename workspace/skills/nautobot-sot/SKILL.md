# SKILL: Nautobot Source of Truth

## Purpose

Query, manage, and reconcile the Nautobot network source of truth. Provides read access to devices, interfaces, VLANs, prefixes, IP addresses, and cables via GraphQL, and ITSM-gated write operations via REST API. Enables live-vs-SoT reconciliation by comparing pyATS device state against Nautobot records.

## MCP Server

`nautobot-mcp` (nautobot-mcp-v2)

## Tools Used

### Reads (GraphQL)
- `nautobot_get_devices` — device inventory with role, platform, location, primary IP
- `nautobot_get_interfaces` — interfaces with VLAN assignments, IPs, cable peers
- `nautobot_get_vlans` — VLANs with locations and groups
- `nautobot_get_prefixes` — IP prefixes from IPAM
- `nautobot_get_ip_addresses` — IP addresses with interface/device assignments
- `nautobot_get_cables` — cables with resolved endpoint names
- `nautobot_graphql` — arbitrary GraphQL for plugins and custom fields

### Writes (REST, ITSM-gated)
- `nautobot_create_ip_address` — create IP, optionally assign to interface
- `nautobot_create_vlan` — create VLAN with location
- `nautobot_create_prefix` — create prefix
- `nautobot_update_object` — update any Nautobot object by type + name

### Reconciliation
- `nautobot_reconcile` — compare live interfaces (from pyATS) against Nautobot

## Workflow: SoT Query

1. Use `nautobot_get_devices` to find devices matching criteria
2. Use `nautobot_get_interfaces` to inspect interface details
3. Use `nautobot_get_vlans`, `nautobot_get_prefixes`, `nautobot_get_ip_addresses` for L2/L3 data
4. Use `nautobot_get_cables` for physical topology

## Workflow: Reconciliation

1. Use pyATS MCP to collect live interface state from device
2. Pass live data to `nautobot_reconcile` with the device name
3. Review the diff report (matches, mismatches, device-only, nautobot-only)
4. Use write tools to fix SoT drift (with ITSM approval if enabled)

## Required Environment Variables

- `NAUTOBOT_URL` — Nautobot instance URL
- `NAUTOBOT_TOKEN` — API token with read+write permissions
- `NAUTOBOT_VERIFY_SSL` — SSL verification (default: false)
- `ITSM_ENABLED` / `ITSM_LAB_MODE` — write operation gating
