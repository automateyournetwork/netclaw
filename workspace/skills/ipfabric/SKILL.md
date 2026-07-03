# IP Fabric Network Assurance Skill

**Skill**: `/ipfabric`
**MCP Server**: ipfabric-mcp (remote HTTP via mcp-remote)
**Tools**: 10 (health, path lookups, diagrams, API discovery)

> Developed in collaboration with **Daren Fulwell** (Field CTO, IP Fabric) and **John Capobianco** (Creator, NetClaw), representing nearly a decade of professional partnership.

## Overview

The IP Fabric skill provides natural language access to IP Fabric's network assurance platform. IP Fabric discovers, models, and analyzes network infrastructure, exposing data through standardized MCP tools for health assessment, path analysis, visual diagrams, and custom API queries.

**Key Capabilities**:
- Network health assessment with intent verification
- Path analysis between any two endpoints
- Visual network diagrams (PNG)
- Device inventory queries
- Routing protocol troubleshooting (BGP, OSPF)
- Intent validation and compliance checking
- API discovery for advanced queries
- Cross-platform composition with other NetClaw skills

## Prerequisites

- IP Fabric appliance (v6.0+) with MCP Server enabled
- API token with appropriate RBAC permissions
- Network connectivity to IP Fabric over HTTPS

## Environment Variables

```bash
IPFABRIC_HOST=https://ipfabric.example.com    # Appliance URL (no trailing slash)
IPFABRIC_API_TOKEN=your-api-token-here        # API token from Settings → API Tokens
```

## MCP Tools Reference

### Health Assessment

| Tool | Description |
|------|-------------|
| `ipf_network_health_assess` | Comprehensive network health overview |

**Parameters**:
- `snapshotId` (optional): Snapshot ID or `$last` for most recent (default: `$last`)

**Returns**: Snapshot freshness, intent verification, device issues, routing stability

### Path Lookups

| Tool | Description |
|------|-------------|
| `ipf_pathlookup_unicast` | Trace unicast path between two IPs |
| `ipf_pathlookup_host-to-gateway` | Trace host to default gateway |
| `ipf_pathlookup_multicast` | Trace multicast distribution path |

**Common Parameters**:
- `src` (required): Source IP address
- `dst` (required for unicast): Destination IP address
- `group` (required for multicast): Multicast group address
- `snapshotId` (optional): Snapshot ID (default: `$last`)
- `vrf` (optional): VRF name for VRF-aware lookup
- `groupBy` (optional): Group results by `siteName`, `routingDomain`, or `stpDomain`
- `protocol` (optional): Filter by protocol (tcp, udp, icmp)

### Path Diagrams (PNG)

| Tool | Description |
|------|-------------|
| `ipf_png_pathlookup_unicast` | Unicast path as PNG diagram |
| `ipf_png_pathlookup_host-to-gateway` | Host-to-gateway path as PNG diagram |
| `ipf_png_pathlookup_multicast` | Multicast path as PNG diagram |

**Parameters**: Same as corresponding path lookup tools

**Returns**: Base64-encoded PNG image

### API Discovery

| Tool | Description |
|------|-------------|
| `ipf_api_endpoint_search` | Search for API endpoints using natural language |
| `ipf_api_endpoint_details` | Get endpoint details including parameters |
| `api_invoke` | Execute arbitrary API calls |

---

## Query Examples by Use Case

### Network Health Assessment (US1)

```
/ipfabric check network health
/ipfabric show me critical issues only
/ipfabric what's the BGP status across my network
/ipfabric are there any routing problems
/ipfabric show snapshot freshness
```

**Query Patterns** → `ipf_network_health_assess`:
- "health", "status", "issues", "problems"
- "BGP status", "OSPF status", "routing"
- "intent violations", "compliance"

### Path Analysis with Diagrams (US2)

```
/ipfabric show me the path from 10.0.1.5 to 10.0.2.10
/ipfabric trace route from server A to server B with diagram
/ipfabric show path from 192.168.1.100 to its gateway
/ipfabric show path from 10.1.1.1 to 10.2.2.2 in VRF MGMT
/ipfabric show multicast path for group 239.1.1.1 from source 10.0.1.5 with diagram
```

**Query Patterns** → `ipf_pathlookup_*` or `ipf_png_pathlookup_*`:
- "path", "trace", "route" → path lookup
- "from X to Y" → extract src/dst IPs
- "diagram", "png", "visualize", "picture" → use PNG variant
- "gateway" → use host-to-gateway variant
- "multicast", "group" → use multicast variant
- "VRF" → add vrf parameter

### Device Inventory Queries (US3)

```
/ipfabric show all Cisco devices in site HQ
/ipfabric find devices with uptime less than 1 day
/ipfabric list devices with telnet enabled
/ipfabric show device counts by vendor
/ipfabric what devices are in site DATACENTER
```

**Query Patterns** → `api_invoke` with inventory endpoints:
- "devices", "inventory", "show all", "list"
- "Cisco", "Juniper", "Arista" → vendor filter
- "site X" → site filter
- "uptime" → uptime filter

### Routing Protocol Troubleshooting (US4)

```
/ipfabric show BGP neighbors that are not in Established state
/ipfabric list OSPF neighbors not in Full state
/ipfabric are there any routing adjacency issues
/ipfabric show routing neighbors for device CORE-RTR-01
```

**Query Patterns** → `ipf_network_health_assess` (routing section):
- "BGP neighbors", "BGP sessions", "BGP status"
- "OSPF neighbors", "OSPF adjacencies"
- "routing adjacency", "routing issues"
- "not Established", "not Full" → filter for problems

### Intent Validation and Compliance (US5)

```
/ipfabric are there any intent violations
/ipfabric check compliance status
/ipfabric show failed intent rules
/ipfabric what intent checks are failing
```

**Query Patterns** → `ipf_network_health_assess` (intent section):
- "intent violations", "intent rules"
- "compliance", "compliance status"
- "failed checks", "failing rules"

### Advanced API Discovery (US6)

```
/ipfabric find endpoints for device inventory
/ipfabric how do I query interface statistics
/ipfabric show me the API for routing tables
/ipfabric invoke /tables/inventory/devices with vendor filter Cisco
```

**Workflow**:
1. `ipf_api_endpoint_search` - Find relevant endpoints
2. `ipf_api_endpoint_details` - Get parameters and schema
3. `api_invoke` - Execute the query

### Cross-Platform Composition (US7)

```
/ipfabric compare network state with SuzieQ historical data
/ipfabric validate paths against Batfish config analysis
/ipfabric which Check Point firewall rules affect the path from 10.1.1.1 to 10.2.2.2
/ipfabric compare topology with my CML lab
```

**Composition Patterns**:

| Integration | IP Fabric Provides | Partner Provides | Use Case |
|-------------|-------------------|------------------|----------|
| SuzieQ | Live network state | Historical analysis | State drift detection |
| Batfish | Live paths, topology | Config analysis | Intent vs reality |
| Check Point | Path endpoints | Security policies | Security path analysis |
| CML/GNS3 | Production topology | Lab topology | Lab validation |

---

## Snapshot Handling

IP Fabric queries execute against a specific snapshot (point-in-time network state).

**Default Behavior**: All queries default to `$last` (most recent completed snapshot)

**Override Options**:
- By name: "using snapshot 'June Baseline'"
- By UUID: "snapshot abc123-def456"
- List first: "list available snapshots"

**Example**:
```
/ipfabric check network health using snapshot from last week
/ipfabric show path from 10.0.1.5 to 10.0.2.10 in snapshot 'Pre-Change'
```

---

## Diagram Handling

PNG diagrams are returned as base64-encoded images.

**Delivery Methods**:
- **CLI/Terminal**: Saved to workspace directory, path returned
- **Slack**: Attached as file to message
- **Teams**: Attached as file to message
- **Webex**: Attached as file to message
- **Discord**: Attached as file to message

**Workspace Storage**:
```
~/.openclaw/workspace/diagrams/ipfabric/
├── path-2026-06-19-001.png
└── path-2026-06-19-002.png
```

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| "Cannot connect" | Network issue or wrong URL | Verify IPFABRIC_HOST and connectivity |
| "Authentication failed" | Invalid or expired token | Regenerate token in IP Fabric UI |
| "Permission denied" | RBAC restrictions | Request appropriate token permissions |
| "Snapshot not found" | Invalid snapshot ID | Use `$last` or list available snapshots |
| "No path exists" | Disconnected endpoints | Check connectivity, verify IPs |

---

## RBAC Considerations

The API token's RBAC permissions determine accessible data:

| Permission Level | Capabilities |
|-----------------|--------------|
| Read-only | Health, paths, inventory, diagrams |
| Intent Admin | + Intent rule configuration |
| Full Access | All capabilities |

**Security Note**: API tokens are never exposed to the AI model. Only query results (network data) are processed.

---

## Related Documentation

- **Full Guide**: [docs/IPFABRIC.md](../../../docs/IPFABRIC.md)
- **Quickstart**: [specs/032-ipfabric-mcp-integration/quickstart.md](../../../specs/032-ipfabric-mcp-integration/quickstart.md)
- **IP Fabric Docs**: https://docs.ipfabric.io/latest/IP_Fabric_Settings/integration/mcp/

---

## Partnership Attribution

This integration was developed in collaboration with:

- **Daren Fulwell** - Field CTO, IP Fabric
- **John Capobianco** - Creator, NetClaw

Their partnership, spanning nearly a decade, continues to bring innovative network automation capabilities to the community.
