---
name: nautobot-sot
description: Nautobot IPAM & source of truth — IP address queries, prefix lookups, VRF/tenant/site filtering, IPAM search, connection testing
version: 1.0.0
tags: [nautobot, ipam, source-of-truth, ip-addresses, prefixes, vrf, dcim]
---

# Nautobot Source of Truth

Query Nautobot as a network source of truth for IPAM data — retrieve IP addresses with filtering by status, role, VRF, and tenant; look up network prefixes by site and role; search across all IP address data; and verify Nautobot connectivity. This is the Nautobot counterpart to the NetBox `netbox-reconcile` skill — use this skill when the organization runs Nautobot instead of (or alongside) NetBox.

## MCP Server

- **Repository**: [aiopnet/mcp-nautobot](https://github.com/aiopnet/mcp-nautobot)
- **Transport**: stdio (Python via MCP SDK) — also supports HTTP on configurable port
- **Requires**: `NAUTOBOT_URL`, `NAUTOBOT_TOKEN`
- **Python**: 3.13+
- **Read-only**: All tools are read-only (requires API token with read permissions)

## MCP Tools

| Tool | Parameters | What It Does |
|------|-----------|--------------|
| `get_ip_addresses` | `address?, prefix?, status?, role?, tenant?, vrf?, limit?, offset?` | Retrieve IP addresses with filtering — status (active, reserved, deprecated), role (loopback, secondary, anycast), VRF, tenant |
| `get_prefixes` | `prefix?, status?, site?, role?, tenant?, vrf?, limit?, offset?` | Retrieve network prefixes with filtering by site, role, status, VRF, tenant |
| `get_ip_address_by_id` | `ip_id` | Retrieve a specific IP address by its Nautobot UUID |
| `search_ip_addresses` | `query, limit?` | Full-text search across all IP address data — find IPs by any matching field |
| `test_connection` | none | Verify connectivity to the Nautobot API — returns status, URL, and timestamp |

### Tool Details

#### get_ip_addresses

The primary IPAM query tool. Supports rich filtering:

- **address** — specific IP to search (e.g., `10.0.1.1`)
- **prefix** — network prefix filter (e.g., `10.0.0.0/24`) — returns all IPs within the prefix
- **status** — `active`, `reserved`, `deprecated`
- **role** — `loopback`, `secondary`, `anycast`, `vip`, `hsrp`, `vrrp`
- **tenant** — filter by tenant (multi-tenancy support)
- **vrf** — filter by VRF (routing instance isolation)
- **limit** — max results (default: 100, max: 1000)
- **offset** — pagination offset

Returns JSON with count and IP address objects including assignment details.

#### get_prefixes

Network prefix (subnet) lookup with site awareness:

- **prefix** — specific prefix (e.g., `10.0.0.0/24`)
- **site** — filter by site/location name
- **role** — prefix role (production, development, management, etc.)
- **status** — active, reserved, deprecated, container
- **tenant** / **vrf** — multi-tenancy and routing isolation

Returns JSON with prefix objects including utilization data.

#### search_ip_addresses

Free-text search across all IP address fields. Use this when you don't know exactly what field to filter on:

- Query by partial IP, hostname, description, or any text in the IP record
- Default limit: 50 (max: 500)

## Workflow: IPAM Audit

When auditing IP address allocations:

1. **Test connection**: `test_connection` — verify Nautobot API is reachable
2. **List prefixes**: `get_prefixes` by site — what subnets are allocated per site
3. **IP utilization**: `get_ip_addresses` per prefix — how many IPs are active vs reserved
4. **Deprecated check**: `get_ip_addresses(status="deprecated")` — stale allocations
5. **Report**: IPAM utilization summary by site and prefix

## Workflow: IP Address Lookup

When investigating "what device uses IP 10.1.2.3?":

1. **Search**: `search_ip_addresses(query="10.1.2.3")` — find the IP
2. **Details**: `get_ip_address_by_id` — full details including device assignment
3. **Prefix context**: `get_prefixes(prefix="10.1.2.0/24")` — what subnet is it in, which site
4. **Report**: IP ownership, device assignment, subnet, site, VRF, tenant

## Workflow: VRF Reconciliation

When validating VRF IP allocations:

1. **Get VRF IPs**: `get_ip_addresses(vrf="PROD-VRF")` — all IPs in the VRF
2. **Get VRF prefixes**: `get_prefixes(vrf="PROD-VRF")` — all subnets in the VRF
3. **Cross-check**: verify IPs fall within expected prefix ranges
4. **Overlap detection**: compare prefixes across VRFs for unintended overlap
5. **Report**: VRF allocation summary with any anomalies

## Workflow: Site IP Summary

When generating an IP summary for a specific site:

1. **Site prefixes**: `get_prefixes(site="Chicago-DC")` — all subnets at the site
2. **Per-prefix IPs**: `get_ip_addresses(prefix="10.10.0.0/16")` — IPs in each prefix
3. **Loopbacks**: `get_ip_addresses(role="loopback", status="active")` — router loopbacks
4. **Report**: site IPAM dashboard with prefix utilization, loopback inventory, tenant breakdown

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `netbox-reconcile` | Nautobot and NetBox are alternative SoTs — use whichever the org runs; both provide IPAM data for reconciliation |
| `pyats-topology` | Nautobot provides intended state (IP assignments); pyATS discovers actual state from devices |
| `pyats-network` | Cross-reference Nautobot IPAM with live device IP configs from pyATS |
| `pyats-routing` | Validate routing table entries against Nautobot IPAM allocations |
| `radkit-remote-access` | Use Nautobot to identify device IPs, then RADKit to access those devices remotely |
| `aci-fabric-audit` | Nautobot IPAM vs ACI endpoint tracker for data center reconciliation |
| `meraki-network-ops` | Nautobot subnet allocations vs Meraki DHCP/VLAN assignments |
| `aws-network-ops` | Nautobot IPAM vs AWS VPC CIDR allocations for hybrid cloud reconciliation |
| `gait-session-tracking` | Record all Nautobot IPAM queries and reconciliation results in GAIT |
| `servicenow-change-workflow` | Reference Nautobot IPAM data when planning change requests |

## Nautobot vs NetBox

Both are popular network source-of-truth platforms. NetClaw supports both:

| Feature | NetBox (`netbox-reconcile`) | Nautobot (`nautobot-sot`) |
|---------|---------------------------|--------------------------|
| Origin | DigitalOcean / NetBox Labs | Network to Code (fork of NetBox) |
| IPAM | Full IPAM, DCIM, circuits | Full IPAM, DCIM, circuits + Jobs framework |
| API style | REST + GraphQL | REST + GraphQL + Jobs API |
| MCP tools | Read-only via FastMCP | Read-only via MCP SDK |
| Use when | Org uses NetBox | Org uses Nautobot |

If the organization runs **both**, use both skills for cross-platform reconciliation.

## Important Rules

- **Read-only** — all tools are read operations; no writes to Nautobot
- **API token scope** — ensure the token has read permissions for IPAM endpoints
- **Pagination matters** — for large datasets, use `limit` and `offset` to page through results (max 1000 per request)
- **VRF isolation** — IP addresses can be duplicated across VRFs; always filter by VRF when the network uses overlapping address space
- **Multi-tenancy** — filter by tenant for shared Nautobot instances serving multiple organizations
- **Record in GAIT** — log all Nautobot IPAM queries and reconciliation results

## Environment Variables

- `NAUTOBOT_URL` — Nautobot instance URL (e.g., `https://nautobot.example.com`)
- `NAUTOBOT_TOKEN` — Nautobot API token with read permissions
- `MCP_PORT` — Server port when running in HTTP mode (default: 8000, optional)
- `MCP_HOST` — Server bind address (default: 127.0.0.1, optional)
