---
name: protocol-participation
description: "Live BGP and OSPF control-plane participation — peer with real routers, inject/withdraw routes, query RIB/LSDB, adjust metrics, GRE tunnel status"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["NETCLAW_ROUTER_ID"] } } }
---

# Protocol Participation — BGP + OSPF + GRE

NetClaw becomes a real routing peer. Instead of just observing network state via SSH, the Protocol MCP server runs a full BGP-4 speaker (RFC 4271) and OSPFv3 speaker (RFC 5340) natively on the host, peering with production or lab routers over GRE tunnels.

## MCP Server

| Property | Value |
|----------|-------|
| **Source** | WontYouBeMyNeighbour BGP/OSPFv3/GRE modules |
| **Transport** | stdio |
| **Tools** | 10 |
| **Protocol modules** | BGP (20 files), OSPFv3 (8 files), GRE (4 files), Connectors (2 files) |
| **Dependencies** | `scapy`, `networkx`, `mcp`, `fastmcp` |

## Tools

### BGP Tools

#### `bgp_get_peers`

List BGP peer sessions with state, AS, IP, uptime, and prefix counts.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | — | — | No parameters |

**Returns:** `{ peers: [{peer, peer_as, state, local_addr, is_ibgp, uptime, prefixes_received, prefixes_sent}], count }`

#### `bgp_get_rib`

Query the Loc-RIB (best routes). Optionally filter by prefix.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prefix` | string | null | Optional CIDR filter (e.g. `10.0.0.0/24`) |

**Returns:** `{ routes: [{network, next_hop, as_path, local_pref, med, origin, communities}], count }`

#### `bgp_inject_route`

Inject a route into the BGP RIB and advertise to peers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `network` | string | required | CIDR prefix (e.g. `192.168.1.0/24`) |
| `next_hop` | string | null | Next-hop IP (defaults to self) |
| `as_path` | string | null | Comma-separated AS path (e.g. `65001,65002`) |
| `local_pref` | int | 100 | LOCAL_PREF value |

**Returns:** `{ success, network, route_info }`

#### `bgp_withdraw_route`

Withdraw a route from the BGP RIB and send withdrawal to peers.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `network` | string | required | CIDR prefix to withdraw |

**Returns:** `{ success, network }`

#### `bgp_adjust_local_pref`

Change the LOCAL_PREF for a route in the RIB.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `network` | string | required | CIDR prefix |
| `local_pref` | int | required | New LOCAL_PREF (higher = more preferred) |

**Returns:** `{ success, network, old_local_pref, new_local_pref }`

### OSPF Tools

#### `ospf_get_neighbors`

List OSPF neighbors with state, address, priority, and router ID.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | — | — | No parameters |

**Returns:** `{ neighbors: [{neighbor_id, state, address, priority}], count }`

#### `ospf_get_lsdb`

Query the OSPF Link State Database.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | — | — | No parameters |

**Returns:** `{ lsdb: [{type, advertising_router, ls_id, sequence, age}], count }`

#### `ospf_adjust_cost`

Change the OSPF cost on an interface.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `interface` | string | required | Interface name (e.g. `gre-netclaw`) |
| `cost` | int | required | New OSPF cost (1-65535) |

**Returns:** `{ success, interface, old_cost, new_cost }`

### GRE Tools

#### `gre_tunnel_status`

Check GRE tunnel status via system commands (`ip tunnel show`, `ip addr show`).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | — | — | No parameters |

**Returns:** `{ tunnels: [...], addresses: [...], count }`

### Meta Tools

#### `protocol_summary`

Consolidated BGP + OSPF + GRE state summary in a single call.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | — | — | No parameters |

**Returns:** `{ router_id, local_as, lab_mode, bgp: {configured, peer_count, peers, rib_size}, ospf: {configured, neighbor_count, neighbors}, gre: {tunnels, addresses, count} }`

---

## Environment Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `NETCLAW_ROUTER_ID` | `4.4.4.4` | BGP/OSPF router ID |
| `NETCLAW_LOCAL_AS` | `65001` | BGP local autonomous system number |
| `NETCLAW_BGP_PEERS` | `[{"ip":"172.16.0.1","as":65000}]` | JSON array of BGP peers |
| `NETCLAW_OSPF_AREAS` | `["0.0.0.0"]` | JSON array of OSPF area IDs |
| `NETCLAW_GRE_TUNNELS` | `[{"name":"gre-netclaw","local":"...","remote":"..."}]` | JSON array of GRE tunnels |
| `NETCLAW_LAB_MODE` | `true` | Relaxes CR requirement for lab testing |

---

## FRR Lab Testbed

A Docker-based 3-router FRR topology is provided in `lab/frr-testbed/` for testing:

```
NetClaw (AS 65001) ──GRE── Edge1 (AS 65000) ──OSPF── Core (RR) ──OSPF── Edge2
  host/WSL                  1.1.1.1              2.2.2.2           3.3.3.3
  172.16.0.2                172.16.0.1
  eBGP                      iBGP→Core            iBGP hub          iBGP→Core
```

```bash
# Start lab
cd lab/frr-testbed && docker compose up -d

# Create GRE tunnel (requires sudo)
sudo bash scripts/setup-gre.sh

# Verify
bash scripts/verify.sh
```

---

## Workflows

### 1. Route Injection with Change Control

```
servicenow-change-workflow → CR approved
→ bgp_inject_route(network, next_hop, local_pref)
→ bgp_get_rib(prefix) → verify route in table
→ pyats-routing → verify on remote devices
→ gait-session-tracking → record change
```

### 2. Traffic Engineering via LOCAL_PREF

```
bgp_get_rib() → current routes
→ bgp_adjust_local_pref(network, local_pref)
→ bgp_get_peers() → verify advertisement
→ gait-session-tracking
```

### 3. OSPF Cost Manipulation

```
ospf_get_neighbors() → verify adjacencies
→ ospf_adjust_cost(interface, cost)
→ ospf_get_lsdb() → verify LSA update
→ pyats-routing → verify SPF reconvergence
→ gait-session-tracking
```

### 4. Protocol Health Check

```
protocol_summary() → full state snapshot
→ bgp_get_peers() → check all Established
→ ospf_get_neighbors() → check all Full
→ gre_tunnel_status() → check all tunnels up
→ gait-session-tracking
```

### 5. Controlled Route Withdrawal

```
servicenow-change-workflow → CR approved
→ bgp_get_rib(prefix) → verify route exists
→ bgp_withdraw_route(network)
→ bgp_get_rib(prefix) → verify withdrawal
→ pyats-routing → verify removal on peers
→ gait-session-tracking
```

### 6. Lab Testing (no CR required)

```
NETCLAW_LAB_MODE=true
→ bgp_inject_route / bgp_withdraw_route
→ bgp_get_rib → verify
→ ospf_adjust_cost → test convergence
→ protocol_summary → snapshot
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **servicenow-change-workflow** | MUST gate all route inject/withdraw/cost changes in production |
| **gait-session-tracking** | Record every protocol mutation in the audit trail |
| **pyats-routing** | Cross-verify protocol state from the device CLI side |
| **uml-diagram** | Generate BGP state machines and OSPF area diagrams |
| **markmap-viz** | Visualise RIB hierarchy and OSPF LSDB as mind maps |
| **netbox-reconcile** | Cross-reference peering with NetBox IPAM/circuits |
| **drawio-diagram** | Topology diagrams showing GRE underlay + BGP/OSPF overlay |
| **cml-topology-builder** | Provision lab topologies that NetClaw can then peer with |

---

## Safety Rules

1. **NEVER** inject or withdraw routes without an approved ServiceNow CR — unless `NETCLAW_LAB_MODE=true`
2. **ALWAYS** verify current RIB (`bgp_get_rib`) before injecting to prevent routing loops
3. **ALWAYS** verify peer state (`bgp_get_peers`) before advertising — only to Established peers
4. **ALWAYS** record protocol changes in GAIT (`gait-session-tracking`)
5. **GRE tunnels require sudo** — the install wizard handles initial setup; runtime queries via `gre_tunnel_status` do not require elevated privileges
6. **Lab mode** (`NETCLAW_LAB_MODE=true`) relaxes the CR requirement for the FRR testbed — never set this in production

## Guardrails

- **Route mutations are gated** — ServiceNow CR approval required in production
- **Read operations are always safe** — `bgp_get_peers`, `bgp_get_rib`, `ospf_get_neighbors`, `ospf_get_lsdb`, `gre_tunnel_status`, `protocol_summary`
- **GRE is the default tunnel transport** — native Linux kernel support, every major vendor supports it (Cisco, Juniper, Arista, FRR, Nokia), RFC 2784/2890 compliant
- **Raw sockets require root for protocol speakers** — BGP (TCP/179), OSPF (IP/89), GRE (IP/47)
- **No secrets in protocol state** — RIB/LSDB queries return routing information, not credentials
