# Nautobot MCP Server v2

Enhanced Nautobot 3.1.0 integration for NetClaw — GraphQL reads, REST writes, ITSM-gated changes, live-vs-SoT reconciliation.

Replaces the v1 mcp-nautobot (5 IPAM-only REST tools) with 13 tools covering devices, interfaces, VLANs, prefixes, IP addresses, cables, raw GraphQL, write operations, and reconciliation.

## Architecture

- **Reads**: GraphQL API (`POST /api/graphql/`) — efficient field selection, nested relationships
- **Writes**: REST API (`POST/PATCH /api/dcim/*`, `/api/ipam/*`) — Nautobot 3.1.0 has no GraphQL mutations
- **Transport**: stdio (FastMCP)

## Tools (13)

### Read Tools (7) — GraphQL

| Tool | Description |
|------|-------------|
| `nautobot_get_devices` | Query devices with filters (name, location, role, platform, status) |
| `nautobot_get_interfaces` | Query interfaces with VLAN assignments, IPs, cable peer |
| `nautobot_get_vlans` | Query VLANs with locations, groups, tenants |
| `nautobot_get_prefixes` | Query IP prefixes from IPAM |
| `nautobot_get_ip_addresses` | Query IP addresses with interface/device assignments |
| `nautobot_get_cables` | Query cables with resolved endpoint names |
| `nautobot_graphql` | Execute arbitrary GraphQL queries (plugins, custom fields) |

### Write Tools (5) — REST API, ITSM-gated

| Tool | Description |
|------|-------------|
| `nautobot_create_ip_address` | Create IP address, optionally assign to interface |
| `nautobot_create_vlan` | Create VLAN with location association |
| `nautobot_create_prefix` | Create IP prefix |
| `nautobot_update_object` | Update any object (device, interface, IP, VLAN, prefix, cable) |
| `nautobot_reconcile` | Compare live device state against Nautobot SoT |

### Utility (1)

| Tool | Description |
|------|-------------|
| `nautobot_test_connection` | Verify GraphQL and REST connectivity |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NAUTOBOT_URL` | Yes | — | Nautobot base URL (e.g., `https://192.168.3.253`) |
| `NAUTOBOT_TOKEN` | Yes | — | API token with read+write permissions |
| `NAUTOBOT_VERIFY_SSL` | No | `false` | Verify SSL certificates |
| `NAUTOBOT_TIMEOUT` | No | `30` | Request timeout in seconds |
| `ITSM_ENABLED` | No | `false` | Enable ITSM gating for writes |
| `ITSM_LAB_MODE` | No | `true` | Bypass ITSM gating for lab use |

## Installation

```bash
cd mcp-servers/nautobot-mcp-v2/
pip install -r requirements.txt
```

## Standalone Test

```bash
export NAUTOBOT_URL="https://192.168.3.253"
export NAUTOBOT_TOKEN="your-token"
export NAUTOBOT_VERIFY_SSL="false"
python3 -u server.py
```

## Files

| File | Purpose |
|------|---------|
| `server.py` | FastMCP server with all 13 tool definitions |
| `nautobot_client.py` | GraphQL + REST client, ID resolution, error handling |
| `reconcile.py` | Interface reconciliation diff engine |
| `requirements.txt` | Python dependencies |
