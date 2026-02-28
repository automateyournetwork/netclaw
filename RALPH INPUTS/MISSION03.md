# MISSION03: NetClaw Mesh — BGP Peering Between NetClaw Instances

> *Any NetClaw, anywhere in the world, can peer with any other NetClaw over BGP.*

---

## Summary

MISSION03 enables NetClaw instances to form BGP peering sessions with each other over the internet using ngrok TCP tunnels. Each NetClaw keeps its local FRR lab network and additionally peers with remote NetClaws to exchange routing intelligence across independent network domains. The result is a global mesh of AI network agents sharing real routing data at machine speed.

---

## What This Changes

| Before (MISSION01-02) | After (MISSION03) |
|---|---|
| Single NetClaw, local FRR lab only | Any number of NetClaws peered globally |
| BGP peers matched by exact source IP | Peers identified by AS number from BGP OPEN message |
| Install wizard supports one peer | Wizard supports local peers + remote mesh peers |
| No ngrok integration | ngrok TCP tunnels expose BGP port to the world |
| Routes stay local | Routes propagate across the mesh |

---

## Architecture

```
  NetClaw-A (AS 65001)                    NetClaw-B (AS 65002)
  Router-ID 4.4.4.4                       Router-ID 5.5.5.5
  ┌──────────────────┐                    ┌──────────────────┐
  │  Python BGP       │                    │  Python BGP       │
  │  Speaker          │                    │  Speaker          │
  │  Listen :1179     │                    │  Listen :1179     │
  │                   │                    │                   │
  │  Local FRR Lab    │                    │  Local FRR Lab    │
  │  (GRE to Edge1)  │                    │  (GRE to Edge1)  │
  └────────┬──────────┘                    └────────┬──────────┘
           │                                        │
           │  ngrok tcp 1179                        │  ngrok tcp 1179
           │  → 0.tcp.ngrok.io:11111                │  → 0.tcp.ngrok.io:22222
           │                                        │
           └──────── eBGP over ngrok ───────────────┘
                  AS 65001 ↔ AS 65002

  What flows across the mesh:
  ─ Identity routes (4.4.4.4/32, 5.5.5.5/32)
  ─ Local lab prefixes (10.0.12.0/24, 192.168.99.0/24, etc.)
  ─ Any injected routes from either side
```

### At Scale: Route Server Model (RFC 7947)

```
                NetClaw-RS (Route Server, AS 65000)
                        0.tcp.ngrok.io:9999
                       /        |        \
                      /         |         \
  NetClaw-A (65001)  NetClaw-B (65002)  NetClaw-C (65003)
  John's network     Alice's network    Bob's network

  Each NetClaw peers only with the Route Server.
  The RS reflects routes between all members.
  This is IXP architecture — except the members are AI agents.
```

---

## The Core Technical Problem and Solution

### The Problem

The existing BGP agent (`agent.py`) matches incoming connections by **exact source IP**:

```python
peer_ip = peer_addr[0]                    # Extract source IP from TCP socket
session = self.sessions.get(peer_ip)      # Look up by IP
if not session:
    writer.close()                        # No match → rejected
```

When connections arrive through ngrok, they come from ngrok infrastructure IPs or `127.0.0.1` — not the remote peer's real IP. Two different NetClaws connecting through ngrok both arrive from the same source. The current code cannot distinguish them.

### The Solution: OPEN-Based Peer Identification

Instead of matching by source IP, read the BGP OPEN message first. The OPEN contains the peer's AS number and router-ID — a unique identity. Match against configured mesh peers by AS number.

```
Incoming TCP connection
        │
        ▼
  Try exact IP match ──── found ──── existing collision logic (unchanged)
        │
    not found
        │
        ▼
  Any mesh peers configured? ── no ── reject
        │
       yes
        │
        ▼
  Read BGP OPEN from wire
  Extract peer AS number
        │
        ▼
  Match AS against mesh_sessions ── found ── accept connection
        │                                    process pre-read OPEN
    not found
        │
        ▼
      reject
```

This preserves all existing behavior for local FRR peers while adding mesh support.

---

## Implementation Plan

### Phase 1: BGP Session Config (session.py)

Add two fields to `BGPSessionConfig`:

```python
accept_any_source: bool = False    # Accept connections from any IP (mesh/ngrok)
hostname: bool = False             # peer_ip is a hostname, not an IP
```

Add `_pending_open` attribute to `BGPSession.__init__` for storing pre-read OPEN messages.

Modify `accept_connection()` to process `_pending_open` when set — the OPEN was already consumed from the wire by the agent during identification, so the session replays it directly into the FSM instead of reading it again.

**File:** `mcp-servers/protocol-mcp/bgp/session.py`

---

### Phase 2: BGP Agent Dual-Key Sessions (agent.py)

Add a parallel session index for mesh peers:

```python
self.mesh_sessions: Dict[int, BGPSession] = {}    # Key: peer_as
```

Modify `add_peer()` — if `config.accept_any_source` is True, store in `mesh_sessions` by AS number and use a synthetic key (`mesh-as65002`) in the main sessions dict.

Add `_read_open_message()` helper — reads exactly one BGP OPEN from a raw TCP stream, parses it, returns the message object with AS and router-ID.

Modify `_handle_incoming_connection()`:
1. Try existing IP-based lookup first (local FRR peers work unchanged)
2. If no match and mesh_sessions exist, read OPEN, match by AS
3. Store pre-read OPEN on the session, then call `accept_connection()`

Update `remove_peer()` to clean both session indexes.

**File:** `mcp-servers/protocol-mcp/bgp/agent.py`

---

### Phase 3: Speaker Passthrough (speaker.py)

Add `accept_any_source` and `hostname` parameters to `BGPSpeaker.add_peer()`. Pass through to `BGPSessionConfig`.

**File:** `mcp-servers/protocol-mcp/bgp/speaker.py`

---

### Phase 4: Daemon Peer Format (bgp-daemon-v2.py)

Support three peer types in `NETCLAW_BGP_PEERS` JSON:

**Type 1 — Local FRR peer** (unchanged):
```json
{"ip": "172.16.0.1", "as": 65000}
```
Active connection to a known IP. This is how the GRE/FRR lab works today.

**Type 2 — Outbound mesh peer** (we connect to their ngrok):
```json
{"ip": "0.tcp.ngrok.io", "as": 65002, "port": 22222, "hostname": true}
```
Active connection to a remote ngrok endpoint. `asyncio.open_connection` resolves hostnames natively.

**Type 3 — Inbound mesh peer** (they connect to us via our ngrok):
```json
{"as": 65003, "passive": true, "accept_any_source": true}
```
No IP needed. Passive. Identified by AS from OPEN when they connect.

Add runtime HTTP API endpoints:
- `POST /add_peer` — add a mesh peer without restarting the daemon
- `POST /remove_peer` — remove a peer cleanly

Auto-advertise router-ID as /32 identity route on session establishment.

**File:** `mcp-servers/protocol-mcp/bgp-daemon-v2.py`

---

### Phase 5: Protocol MCP Server (server.py)

Mirror the same peer type handling from the daemon in the MCP server's lazy initialization. Both entry points must parse the same JSON format.

**File:** `mcp-servers/protocol-mcp/server.py`

---

### Phase 6: Install Script Mesh Wizard (install.sh)

Extend Step 42 with a mesh peering section:

```
Enable protocol participation? [y/N] y

  Router ID (e.g. 4.4.4.4): 4.4.4.4
  Local BGP AS (e.g. 65001): 65001
  BGP peer IP (e.g. 172.16.0.1): 172.16.0.1
  BGP peer AS (e.g. 65000): 65000
  Lab mode? [Y/n] y

Enable NetClaw Mesh peering (BGP over ngrok)? [y/N] y

  BGP listen port (default 1179): 1179

  Add a remote NetClaw peer? [y/N] y
    Remote ngrok hostname (e.g. 0.tcp.ngrok.io): 0.tcp.ngrok.io
    Remote ngrok port (e.g. 12345): 11111
    Remote AS number (e.g. 65002): 65002
    Add another remote peer? [y/N] n

  Accept inbound mesh connections? [Y/n] y
```

The wizard merges local FRR peers and mesh peers into a single `NETCLAW_BGP_PEERS` JSON array. Writes `BGP_LISTEN_PORT` and `NETCLAW_MESH_ENABLED=true` to `~/.openclaw/.env`.

Optional: detect ngrok, start it, capture the endpoint from the ngrok API (`http://127.0.0.1:4040/api/tunnels`), and display it for sharing.

**File:** `scripts/install.sh`

---

## The User Experience

### Person A (First Mover)

```bash
# 1. Install NetClaw, enable protocol + mesh
./scripts/install.sh
# → Router-ID: 4.4.4.4, AS: 65001
# → Local FRR peer: 172.16.0.1 AS 65000
# → Mesh enabled, accepting inbound: yes
# → No remote peers yet (you're first)

# 2. Start local FRR lab
cd lab/frr-testbed && docker compose up -d
sudo bash scripts/setup-gre.sh

# 3. Expose BGP port via ngrok
ngrok tcp 1179
# → Your endpoint: 0.tcp.ngrok.io:11111
# Share this with other NetClaw operators
```

### Person B (Joins the Mesh)

```bash
# 1. Install NetClaw, enable protocol + mesh
./scripts/install.sh
# → Router-ID: 5.5.5.5, AS: 65002
# → Local FRR peer: 172.16.0.1 AS 65000 (their own lab)
# → Mesh enabled, accepting inbound: yes
# → Remote peer: 0.tcp.ngrok.io:11111 AS 65001 (Person A)

# 2. Start their local FRR lab
cd lab/frr-testbed && docker compose up -d
sudo bash scripts/setup-gre.sh

# 3. Expose their BGP port via ngrok
ngrok tcp 1179
# → Their endpoint: 0.tcp.ngrok.io:22222
# Share back with Person A
```

### Person A Adds Person B

```bash
# Add Person B at runtime (no restart needed)
curl -X POST http://127.0.0.1:8179/add_peer \
  -d '{"ip":"0.tcp.ngrok.io","as":65002,"port":22222,"hostname":true}'
```

### What Happens

```
Person A's RIB                          Person B's RIB
───────────────                         ───────────────
4.4.4.4/32      (self, identity)        5.5.5.5/32      (self, identity)
10.0.12.0/24    (from FRR lab)          10.0.12.0/24    (from their FRR lab)
192.168.99.0/24 (from FRR Edge2)        192.168.99.0/24 (from their FRR Edge2)
5.5.5.5/32      (from mesh peer B)      4.4.4.4/32      (from mesh peer A)
```

Both NetClaws see each other's identity and network prefixes. Standard BGP best-path selection applies. Either side can influence routing with LOCAL_PREF, communities, or AS-path manipulation.

---

## Taking This to the Next Level

### Level 1: Authenticated Mesh with Community Tags

Add BGP community support to carry metadata across the mesh:

| Community | Meaning |
|---|---|
| 65001:100 | Production prefix — handle with care |
| 65001:200 | Lab prefix — experimental |
| 65001:911 | Incident in progress — avoid this path |
| 65001:666 | Security event — quarantine related |

NetClaw instances can make routing decisions based on what the other side is telling them through communities. Not just "here's a prefix" but "here's a prefix, and here's the context."

### Level 2: Distributed Incident Response

When NetClaw-A detects an anomaly (interface flapping, BGP path changes, CPU spike), it injects a route with an incident community. NetClaw-B sees that community and can:
- Alert its operator
- Adjust its own routing to avoid the affected path
- Correlate with its own telemetry data

Two AI agents doing a cross-domain incident bridge — at machine speed, with structured data instead of voice calls.

### Level 3: Collective Intelligence via Route Injection

Each NetClaw has visibility into its local network. With mesh peering, every NetClaw gains visibility into every other NetClaw's network. The collective RIB becomes a distributed view of global reachability.

A NetClaw instance can answer: "Can I reach 10.200.0.0/16?" by checking if any mesh peer is advertising it. This is the same question operators ask on NOC bridge calls — except the answer comes back in milliseconds.

### Level 4: NetClaw IXP (Internet Exchange Point)

Deploy a NetClaw Route Server (RS) instance. Every other NetClaw peers only with the RS. The RS reflects routes between all members (RFC 7947). This is exactly how AMS-IX, DE-CIX, and LINX work — except the members are AI agents, not ISPs.

```
                   NetClaw Route Server (AS 65000)
                   0.tcp.ngrok.io:9999
                  /    |    |    |    \
                 /     |    |    |     \
  NetClaw-A   B     C     D     E    ...
  AS 65001  65002 65003 65004 65005

  Each member peers once. RS reflects routes to all.
  New member joins: one BGP session, instant mesh visibility.
```

Benefits:
- **O(1) peering** — new members add one peer, not N peers
- **Policy at the RS** — the RS can filter, tag, and prioritize routes
- **Centralized visibility** — the RS has the complete mesh RIB

### Level 5: Cross-Domain Traffic Engineering

With BGP between NetClaws, you get traffic engineering for free:
- **AS-path prepending** — make a path less preferred across the mesh
- **MED** — express preference for one entry point over another
- **LOCAL_PREF** — each NetClaw controls its own egress policy
- **Conditional route injection** — only advertise a prefix when certain conditions are met (e.g., circuit health above threshold)

NetClaw-A can tell NetClaw-B "prefer my secondary link for this prefix" by manipulating path attributes — the same tools ISPs use, applied to AI-managed networks.

### Level 6: EVPN Overlay Between NetClaws

If both sides support EVPN (already partially implemented in the protocol MCP), the mesh becomes a full overlay network:
- **MAC/IP learning** across the mesh
- **ARP suppression** — reduce broadcast across domains
- **Multi-tenancy** — VNI-based separation between different customer/project networks
- **Seamless L2 extension** — stretch a VLAN between two NetClaw domains

This is how hyperscalers interconnect data centers. Two NetClaws with EVPN peering can extend an L2 domain across the internet.

### Level 7: Autonomous Mesh Optimization

The mesh peers continuously. Each NetClaw monitors:
- RTT to each mesh peer (BGP keepalive timing)
- Route stability (flap damping metrics)
- Prefix count per peer (RIB growth rate)
- Reachability (can I actually forward traffic to advertised prefixes?)

Based on this data, each NetClaw autonomously:
- Dampens flapping peers
- Prefers stable paths over shorter but unreliable ones
- Alerts operators when mesh health degrades
- Generates mesh topology visualizations (Markmap/Draw.io)

### Level 8: Discovery Protocol — No Manual Configuration

Replace manual "share your ngrok endpoint" with a discovery service:

1. Each NetClaw registers its ngrok endpoint + AS + router-ID with a lightweight registry (GitHub Gist, simple HTTP API, or even a DNS TXT record)
2. On startup, each NetClaw queries the registry for known peers
3. BGP sessions auto-establish
4. Peers that disappear from the registry get removed after a grace period

This turns the mesh from "call your friend and exchange endpoints" to "plug in and auto-discover."

---

## Files Modified

| File | Change |
|---|---|
| `mcp-servers/protocol-mcp/bgp/session.py` | Add `accept_any_source`, `hostname` to config; `_pending_open` replay |
| `mcp-servers/protocol-mcp/bgp/agent.py` | `mesh_sessions` index, OPEN-based matching, `_read_open_message` helper |
| `mcp-servers/protocol-mcp/bgp/speaker.py` | Pass new config fields through `add_peer` |
| `mcp-servers/protocol-mcp/bgp-daemon-v2.py` | Three peer types, runtime API, identity route |
| `mcp-servers/protocol-mcp/server.py` | Same peer type handling |
| `scripts/install.sh` | Mesh wizard section in Step 42 |

---

## Verification

```bash
# 1. Local FRR lab still works (no regression)
sudo bash lab/frr-testbed/scripts/verify.sh

# 2. Daemon starts with mesh config
curl http://127.0.0.1:8179/peers
# → Shows local FRR peer + mesh peers

# 3. ngrok tunnel is exposing BGP port
curl http://127.0.0.1:4040/api/tunnels
# → Shows tcp tunnel to port 1179

# 4. Remote peer connects (from another NetClaw)
# → Daemon logs: "Matched incoming connection to mesh peer AS65002"
# → /peers shows ESTABLISHED

# 5. Routes propagate
curl http://127.0.0.1:8179/rib
# → Shows remote peer's identity route and prefixes
```

---

## Missions

| Mission | Status | Summary |
|---|---|---|
| MISSION01 | Complete | Core pyATS agent, 7 skills, Markmap, Draw.io, RFC, NVD CVE, SOUL v1 |
| MISSION02 | Complete | NetBox, ServiceNow, GAIT, ACI, ISE, Wikipedia, 6 MCPs, 7 skills, SOUL v2 |
| MISSION03 | Active | NetClaw Mesh — BGP peering between NetClaw instances via ngrok, OPEN-based peer identification, multi-peer support, route exchange, mesh IXP model |

---

*NetClaw Mesh — Every NetClaw a router. Every router a peer. Every peer a colleague.*
