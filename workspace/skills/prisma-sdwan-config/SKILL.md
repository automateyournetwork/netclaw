---
name: prisma-sdwan-config
description: "Inspect Prisma SD-WAN interfaces, routing (BGP, static), policies, and security zones"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["PAN_CLIENT_ID", "PAN_CLIENT_SECRET", "PAN_TSG_ID"]
---

# Prisma SD-WAN Configuration Inspection

Inspect the configuration of your Palo Alto Networks Prisma SD-WAN fabric. View interfaces, WAN circuits, BGP peers, static routes, policy sets, security zones, and generate site configuration exports.

## When to Use

- Viewing interface configurations (LAN and WAN)
- Checking WAN circuit bandwidth and BFD settings
- Reviewing BGP peering configurations and states
- Auditing static routes across sites
- Understanding policy set assignments
- Reviewing security zone definitions
- Generating YAML configuration exports for documentation

## MCP Server

- **Server**: `prisma-sdwan-mcp` (community MCP from iamdheerajdubey)
- **Command**: `python3 -u mcp-servers/prisma-sdwan-mcp/src/prisma_sdwan_mcp/server.py` (stdio transport)
- **Auth**: OAuth2 via `PAN_CLIENT_ID`, `PAN_CLIENT_SECRET`, `PAN_TSG_ID`
- **Region**: `PAN_REGION` (americas or europe, default: americas)

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_interfaces` | site_id, element_id | List LAN/WAN interface configurations |
| `get_wan_interfaces` | site_id | List WAN-specific interface configurations |
| `get_bgp_peers` | site_id, element_id | List BGP peer configurations and states |
| `get_static_routes` | site_id, element_id | List static route configurations |
| `get_policy_sets` | None | List all policy set definitions |
| `get_security_zones` | None | List security zone definitions |
| `generate_site_config` | site_id, elements?, filename?, overwrite? | Export site config as YAML |

## Workflow Examples

### Interface Review

```bash
# List all interfaces on an element
"Show me the interfaces on hq-router-1"

# Check WAN circuits at a site
"What WAN interfaces are configured at the Headquarters site?"

# Find interface IPs
"What IP addresses are assigned to interfaces at branch-01?"
```

### Routing Configuration

```bash
# Check BGP peers
"List the BGP peers on hq-router-1"

# Verify BGP state
"Are all BGP sessions established?"

# Review static routes
"What static routes are configured at the datacenter site?"
```

### Policy and Security

```bash
# List policy sets
"Show me all SD-WAN policy sets"

# Find default policy
"Which policy set is the default?"

# Review security zones
"What security zones are defined?"

# Check zone assignments
"Which interfaces are in the trusted zone?"
```

### Configuration Export

```bash
# Generate site config YAML
"Export the Headquarters site configuration as YAML"

# Export with specific filename
"Generate a config export for branch-01 as branch-01-backup.yaml"
```

## Integration with Other Skills

- **prisma-sdwan-topology**: Get site_id and element_id before config queries
- **prisma-sdwan-status**: Cross-reference alarms with interface config
- **prisma-sdwan-apps**: View applications referenced in policies

## Response Examples

### Interfaces Response

```json
{
  "interfaces": [
    {
      "id": "int001",
      "name": "1",
      "type": "lan",
      "admin_state": "up",
      "operational_state": "up",
      "ipv4_config": {
        "address": "192.168.1.1",
        "prefix": 24
      },
      "mtu": 1500
    }
  ]
}
```

### BGP Peers Response

```json
{
  "bgp_peers": [
    {
      "id": "bgp001",
      "name": "ISP-Peer",
      "peer_ip": "203.0.113.1",
      "peer_asn": 65001,
      "local_asn": 65000,
      "state": "established"
    }
  ]
}
```

### Policy Sets Response

```json
{
  "policy_sets": [
    {
      "id": "pol001",
      "name": "Default-Policy",
      "description": "Default traffic policy",
      "default_policy": true
    }
  ]
}
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | OAuth2 authentication failed | Verify credentials |
| NOT_FOUND | Site or element not found | Check IDs via prisma-sdwan-topology |
| INVALID_PARAM | Missing required parameter | Provide both site_id and element_id where required |

## Notes

- Read-only operations - no ServiceNow CR gating required
- get_interfaces and get_bgp_peers require both site_id and element_id
- get_wan_interfaces only requires site_id
- generate_site_config creates validated YAML output
- All operations logged to GAIT audit trail
