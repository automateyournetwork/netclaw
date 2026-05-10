# Feature Specification: nautobot-routing-mcp

**Spec**: `030-nautobot-routing-mcp`
**Created**: 2026-05-11
**Status**: Planned
**Server Location**: `mcp-servers/nautobot-routing-mcp/server.py`

## Context

The Nautobot BGP Models plugin has a deeply nested object graph:

```
AutonomousSystem
  └─ RoutingInstance (per device)
       ├─ PeerGroup
       │    ├─ PeerGroupAddressFamily (afi_safi per group)
       │    └─ PeerGroupTemplate
       ├─ AddressFamily (afi_safi per instance)
       └─ (linked via PeerEndpoint)

Peering (abstract container — no device affinity)
  ├─ PeerEndpoint A (local side)
  │    ├─ routing_instance → device
  │    ├─ source_ip / source_interface
  │    ├─ peer_group
  │    ├─ autonomous_system (remote AS override)
  │    └─ PeerEndpointAddressFamily
  └─ PeerEndpoint B (remote side)
       └─ (same structure)
```

Creating a single BGP peering in Nautobot requires understanding this chain and making 5-8 API calls in the correct order. The LLM burns 2000+ tokens navigating this. The existing tools in nautobot-mcp-v2 (`nautobot_create_bgp_peering`, `nautobot_create_bgp_peer_group`, `nautobot_create_autonomous_system`) attempt to simplify this but use inconsistent patterns (old `client.get()`/`client.post()` methods) and don't cover the full model.

The IGP Models plugin (OSPF) has a simpler but still multi-object model:
```
OSPFConfiguration (per device, process_id)
  └─ OSPFInterfaceConfiguration (interface + area + cost)
```

**This spec defines a standalone MCP server** that provides high-level, one-call tools for routing protocol management in Nautobot.

## Design Principles

1. **One tool = one routing operation** — creating a peering is one call, not five
2. **Topology-aware reads** — return the full routing picture for a device in one query
3. **Relationship-aware writes** — tools handle the object chain internally
4. **Reconciliation-ready** — tools that compare Nautobot model vs live device state
5. **Idempotent** — creating a peering that already exists returns the existing one

## Data Model (Nautobot BGP Models 2.3.2)

### REST Endpoints (`/api/plugins/bgp/`)
| Endpoint | Objects | Lab Count |
|----------|---------|-----------|
| `autonomous-systems` | ASN definitions | ~5 |
| `routing-instances` | Per-device BGP process (device + ASN + router_id) | ~10 |
| `peer-groups` | Peer group definitions (per routing instance) | ~10 |
| `peer-group-templates` | Reusable peer group config templates | 0 |
| `peerings` | Abstract peering container (status only) | 58 |
| `peer-endpoints` | One side of a peering (routing_instance, source_ip, peer_group) | 116 |
| `address-families` | AFI/SAFI per routing instance | 3 |
| `peer-group-address-families` | AFI/SAFI per peer group | ~10 |
| `peer-endpoint-address-families` | AFI/SAFI per endpoint | ~100 |

### Key Relationships
- A **Peering** has exactly 2 **PeerEndpoints** (A and B)
- Each **PeerEndpoint** belongs to a **RoutingInstance** (which belongs to a device)
- A **PeerEndpoint** optionally references a **PeerGroup**
- **AddressFamilies** can be attached at instance, group, or endpoint level
- The `peer` field on a PeerEndpoint points to the OTHER endpoint in the same Peering

## Tools

### BGP Topology (Read)

| Tool | Purpose | Returns |
|------|---------|---------|
| `routing_get_bgp_summary(device=)` | Full BGP topology for a device: peers, groups, AFIs, ASNs | Structured summary like `show bgp summary` |
| `routing_get_bgp_peers(device=)` | List all BGP peers for a device with remote AS, state, group | Peer table |
| `routing_get_bgp_peer_detail(device, peer_ip)` | Full detail of a specific peering: both endpoints, AFIs, group | Complete peering object |
| `routing_get_peer_groups(device=)` | List peer groups with member count, AFIs, templates | Group table |
| `routing_get_autonomous_systems()` | List all ASNs in the model | ASN table |

### BGP Write (ITSM-gated)

| Tool | Purpose | Creates |
|------|---------|---------|
| `routing_create_peering(device, local_ip, peer_ip, peer_asn, peer_group=, afi=, description=)` | Create a complete BGP peering in one call | ASN (if new) + Peering + 2 Endpoints + AFIs |
| `routing_delete_peering(device, peer_ip)` | Remove a peering and both endpoints | Deletes Peering + Endpoints |
| `routing_create_peer_group(device, name, remote_asn=, source_interface=, afi=, route_map_in=, route_map_out=)` | Create a peer group with AFIs | PeerGroup + PeerGroupAddressFamilies |
| `routing_delete_peer_group(device, name)` | Remove a peer group (fails if members exist) | Deletes PeerGroup |
| `routing_add_peer_to_group(device, peer_ip, group)` | Move an existing peer into a group | Updates PeerEndpoint.peer_group |
| `routing_remove_peer_from_group(device, peer_ip)` | Remove peer from its group | Clears PeerEndpoint.peer_group |
| `routing_create_autonomous_system(asn, description=)` | Create or return existing ASN | AutonomousSystem |
| `routing_create_routing_instance(device, asn, router_id=)` | Create BGP routing instance for a device | RoutingInstance |

### OSPF Topology (Read)

| Tool | Purpose | Returns |
|------|---------|---------|
| `routing_get_ospf_summary(device=)` | OSPF config for a device: process, areas, interfaces, costs | Structured summary |
| `routing_get_ospf_interfaces(device=, area=)` | List OSPF-enabled interfaces with area, cost, timers | Interface table |

### OSPF Write (ITSM-gated)

| Tool | Purpose | Creates |
|------|---------|---------|
| `routing_create_ospf_instance(device, process_id, router_id=)` | Create OSPF process on a device | OSPFConfiguration |
| `routing_add_ospf_interface(device, interface, area, cost=, network_type=)` | Add interface to OSPF | OSPFInterfaceConfiguration |
| `routing_remove_ospf_interface(device, interface)` | Remove interface from OSPF | Deletes OSPFInterfaceConfiguration |

### Reconciliation

| Tool | Purpose | Returns |
|------|---------|---------|
| `routing_reconcile_bgp(device, live_peers)` | Compare Nautobot BGP model vs live peer data (from pyATS) | Drift report: missing peers, extra peers, ASN mismatches |
| `routing_reconcile_ospf(device, live_neighbors)` | Compare Nautobot OSPF model vs live neighbor data | Drift report: missing interfaces, area mismatches |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NAUTOBOT_URL` | Yes | `http://localhost:8080` | Nautobot instance URL |
| `NAUTOBOT_TOKEN` | Yes | — | Nautobot API token |
| `NAUTOBOT_TIMEOUT` | No | `60` | API request timeout (seconds) |
| `ITSM_ENABLED` | No | `false` | Require ServiceNow CR for writes |
| `ITSM_LAB_MODE` | No | `true` | Bypass ITSM in lab mode |

## Server Structure

```
mcp-servers/nautobot-routing-mcp/
├── server.py              # FastMCP server with all tools
├── nautobot_client.py     # Shared async HTTP client (same pattern as golden-config-mcp)
├── bgp_helpers.py         # BGP object chain resolution helpers
├── requirements.txt       # httpx, fastmcp, mcp
└── __init__.py
```

## Key Implementation Details

### BGP Peering Creation Chain

```python
async def _create_full_peering(device, local_ip, peer_ip, peer_asn, peer_group=None, afi="ipv4_unicast"):
    """Create the full BGP peering object chain."""
    # 1. Find or create remote ASN
    asn_id = await _find_or_create_asn(peer_asn)
    
    # 2. Find local device's routing instance
    instance_id = await _find_routing_instance(device)
    
    # 3. Find local and peer IP IDs
    local_ip_id = await _find_ip(local_ip)
    peer_ip_id = await _find_ip(peer_ip)  # may be None for external peers
    
    # 4. Find peer group if specified
    pg_id = await _find_peer_group(device, peer_group) if peer_group else None
    
    # 5. Create the Peering container
    peering_id = await _create_peering()
    
    # 6. Create Endpoint A (local)
    ep_a_id = await _create_endpoint(peering_id, instance_id, local_ip_id, pg_id)
    
    # 7. Create Endpoint B (remote)
    ep_b_id = await _create_endpoint(peering_id, None, peer_ip_id, asn_override=asn_id)
    
    # 8. Add address families to endpoint
    await _add_endpoint_afi(ep_a_id, afi)
    
    return peering_id
```

### Idempotency Pattern

All write tools check for existing objects before creating:
```python
# Check if peering already exists between these IPs
existing = await _find_peering_by_ips(device, local_ip, peer_ip)
if existing:
    return {"status": "already_exists", "peering_id": existing["id"]}
```

### BGP Summary Query (Efficient)

Instead of N+1 queries, use a single GraphQL query to get the full topology:
```graphql
{
  bgp_routing_instances(device: "RR1") {
    device { name }
    autonomous_system { asn }
    router_id { address }
    peer_groups { name autonomous_system { asn } }
    endpoints {
      source_ip { address }
      peer { source_ip { address } }
      peer_group { name }
      autonomous_system { asn }
      enabled
    }
  }
}
```

### Reconciliation Format

```json
{
  "device": "RR1",
  "nautobot_peers": 12,
  "live_peers": 10,
  "drift": {
    "in_nautobot_not_live": [
      {"peer_ip": "10.255.255.1", "asn": 65099, "status": "documented but not established"}
    ],
    "in_live_not_nautobot": [
      {"peer_ip": "192.168.1.1", "asn": 64512, "status": "undocumented peer"}
    ],
    "asn_mismatch": [],
    "group_mismatch": []
  }
}
```

## Relationship to Other MCP Servers

| Server | Responsibility |
|--------|---------------|
| `nautobot-mcp-v2` | Generic SoT CRUD (devices, interfaces, IPs, VLANs). BGP/OSPF read tools deprecated → point here |
| `nautobot-routing-mcp` | Routing protocol model management (BGP peerings, OSPF, reconciliation) |
| `nautobot-golden-config-mcp` | Config lifecycle (templates render FROM the routing model, this server manages the model) |
| `protocol-mcp` | Live BGP/OSPF participation (scapy speakers). Uses routing-mcp to document peers in Nautobot |
| `pyATS MCP` | Collect live state (`show bgp summary`, `show ip ospf neighbor`) for reconciliation input |

## Migration from nautobot-mcp-v2

These tools should be deprecated in nautobot-mcp-v2:

| Current Tool | Replacement |
|-------------|-------------|
| `nautobot_get_bgp_routing` | `routing_get_bgp_summary` |
| `nautobot_get_autonomous_systems` | `routing_get_autonomous_systems` |
| `nautobot_get_ospf_routing` | `routing_get_ospf_summary` |
| `nautobot_create_bgp_peering` | `routing_create_peering` |
| `nautobot_create_autonomous_system` | `routing_create_autonomous_system` |
| `nautobot_create_bgp_peer_group` | `routing_create_peer_group` |

Also remove from `_OBJECT_REGISTRY`:
- `autonomous_system`
- `bgp_routing_instance`
- `bgp_peer_group`
- `bgp_peering`

(Keep in registry for `nautobot_delete` backward compat, but add deprecation notes.)

## Success Criteria

- **SC-001**: LLM can create a full BGP peering (ASN + peering + endpoints + AFI) in 1 tool call
- **SC-002**: LLM can get the complete BGP topology for a device in 1 tool call
- **SC-003**: LLM can reconcile Nautobot BGP model vs live state in 1 tool call (given pyATS output)
- **SC-004**: LLM can manage peer groups (create, add/remove members) in 1 tool call each
- **SC-005**: LLM can add/remove OSPF interfaces in 1 tool call
- **SC-006**: Idempotent — creating an existing peering returns it without error
- **SC-007**: No more than 200 tokens of context burned per routing operation

## Workflow Examples

### Before (nautobot-mcp-v2 — 8+ calls, LLM confusion):
```
nautobot_graphql → find routing instance → nautobot_get_autonomous_systems → 
nautobot_create_autonomous_system → nautobot_graphql → find IPs →
nautobot_create_bgp_peering → (fails on missing field) → retry → ...
```

### After (nautobot-routing-mcp — 1 call):
```
routing_create_peering(device="RR1", local_ip="10.255.255.2/30", 
                       peer_ip="10.255.255.1/30", peer_asn=65099,
                       peer_group="NETCLAW-PEERS", afi="ipv4_unicast")
→ {"created": true, "peering_id": "...", "endpoints": [...]}
```

### Reconciliation workflow:
```
# Step 1: Get live state via pyATS
pyats_run_command(device="RR1", command="show bgp summary")

# Step 2: Compare against Nautobot model
routing_reconcile_bgp(device="RR1", live_peers='[{"ip":"10.0.0.1","asn":65001,"state":"Established"},...]')

# Step 3: Fix drift
routing_create_peering(device="RR1", local_ip="...", peer_ip="10.0.0.5", peer_asn=65005)
```
