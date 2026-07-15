---
name: prisma-sdwan-topology
description: "Discover Prisma SD-WAN sites, ION elements, machines, and network topology"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["PAN_CLIENT_ID", "PAN_CLIENT_SECRET", "PAN_TSG_ID"]
---

# Prisma SD-WAN Topology Discovery

Discover your Palo Alto Networks Prisma SD-WAN fabric topology through natural language. View all sites, ION devices (elements), hardware inventory, and full site-to-site topology.

## When to Use

- Listing all SD-WAN sites in your fabric
- Viewing ION devices at a specific site
- Auditing hardware inventory (serial numbers, models)
- Understanding site-to-site connectivity and topology
- Identifying hub vs spoke site roles
- Getting a count of devices across the fabric

## MCP Server

- **Server**: `prisma-sdwan-mcp` (community MCP from iamdheerajdubey)
- **Command**: `python3 -u mcp-servers/prisma-sdwan-mcp/src/prisma_sdwan_mcp/server.py` (stdio transport)
- **Auth**: OAuth2 via `PAN_CLIENT_ID`, `PAN_CLIENT_SECRET`, `PAN_TSG_ID`
- **Region**: `PAN_REGION` (americas or europe, default: americas)

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_sites` | site_id? | List all SD-WAN sites or get specific site details |
| `get_elements` | element_id?, site_id? | List ION devices, optionally filter by site |
| `get_machines` | machine_id? | List hardware inventory with serial numbers and models |
| `get_topology` | None | Get full network topology graph (sites + links) |

## Workflow Examples

### Site Discovery

```bash
# List all SD-WAN sites
"Show me all Prisma SD-WAN sites"

# Get details for a specific site
"What's the configuration for the Headquarters site?"

# Count devices at each site
"How many ION devices are at each site?"
```

### Element Inventory

```bash
# List all ION elements
"List all ION routers in the SD-WAN fabric"

# Find elements at a specific site
"What ION devices are at the San Francisco site?"

# Check device states
"Which ION elements are currently offline?"
```

### Hardware Audit

```bash
# List all hardware
"Show me the hardware inventory for all ION devices"

# Find specific models
"Which sites have ION 3000 devices?"

# Check software versions
"What software versions are running across the fabric?"
```

### Topology Analysis

```bash
# Get full topology
"Show me the SD-WAN network topology"

# Understand hub-spoke design
"Which sites are configured as hubs?"

# Check VPN connectivity
"What are the site-to-site VPN links?"
```

## Integration with Other Skills

- **prisma-sdwan-status**: After discovering topology, check element health
- **prisma-sdwan-config**: Drill into interface and routing configuration
- **prisma-sdwan-apps**: View application definitions used in policies

## Response Examples

### Site List Response

```json
{
  "sites": [
    {
      "id": "abc123",
      "name": "Headquarters",
      "element_count": 2,
      "admin_state": "active",
      "address": {
        "city": "San Francisco",
        "state": "CA"
      }
    }
  ],
  "total_count": 15
}
```

### Element List Response

```json
{
  "elements": [
    {
      "id": "def456",
      "name": "hq-router-1",
      "site_name": "Headquarters",
      "model_name": "ION 3000",
      "software_version": "6.2.1",
      "state": "online",
      "role": "hub"
    }
  ]
}
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | OAuth2 authentication failed | Verify PAN_CLIENT_ID, PAN_CLIENT_SECRET, PAN_TSG_ID |
| TOKEN_EXPIRED | Access token expired | Server auto-refreshes; restart if persistent |
| NOT_FOUND | Site or element not found | Check IDs via get_sites or get_elements |
| REGION_MISMATCH | Wrong regional endpoint | Set PAN_REGION=europe for EU deployments |

## Notes

- Read-only operations - no ServiceNow CR gating required
- Sites and elements can be referenced by name or UUID
- All operations logged to GAIT audit trail
- OAuth2 tokens auto-refresh (50-minute TTL)
