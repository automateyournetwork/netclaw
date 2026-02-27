---
name: pyats-junos-routing
description: "JunOS routing operations via pyATS — OSPF/OSPFv3, BGP, route table, MPLS/LDP/RSVP, TED, PFE, ping, traceroute across Juniper devices"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# JunOS Routing Operations via pyATS

Inspect Juniper routing protocols (OSPF, OSPFv3, BGP), route tables, MPLS/LDP/RSVP label-switched paths, traffic engineering database, PFE forwarding state, and perform connectivity tests (ping, traceroute) using pyATS `pyats_run_show_command`.

## How to Call

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"<command>"}'
```

---

## Commands

### OSPF (IPv4)

#### Neighbors
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf neighbor"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf neighbor detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf neighbor extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf neighbor 10.1.1.2 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf neighbor instance all"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf neighbor instance my-instance"}'
```

#### Interfaces
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface brief"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface ge-0/0/0"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface ge-0/0/0 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface brief instance my-instance"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface detail instance my-instance"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface instance my-instance"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf interface ge-0/0/0 detail instance my-instance"}'
```

#### Database (LSDB)
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database summary"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database external extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database opaque-area"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database advertising-router self detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database advertising-router 10.0.0.1 extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database lsa-id 10.0.0.1 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database network lsa-id 10.0.0.1 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf database router extensive"}'
```

#### Overview, Routes & Statistics
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf overview"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf overview extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf route brief"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf route detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf route network extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf route 10.0.0.0/24"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf statistics"}'
```

### OSPFv3 (IPv6)

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 neighbor"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 neighbor detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 neighbor extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 neighbor instance all"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 interface"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 interface extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 database"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 database extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 database external extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 database network detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 database link advertising-router 10.0.0.1 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 database advertising-router 10.0.0.1 extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 overview"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 overview extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 route network extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ospf3 route 2001:db8::/32"}'
```

### BGP

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp summary"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp summary instance my-vrf"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp neighbor"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp neighbor 10.1.1.2"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp group brief"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp group brief | no-more"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp group detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp group detail | no-more"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp group summary"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bgp group summary | no-more"}'
```

### Route Table

#### General
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route summary"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route 10.0.0.0/24"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route 10.0.0.1/32 extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route extensive 10.0.0.0/24"}'
```

#### By Protocol
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol ospf"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol ospf extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol bgp"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol bgp extensive 10.0.0.0/24"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol static"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol direct"}'
```

#### By Table
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route table inet.0"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route table inet.3"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route table mpls.0"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route table my-vrf.inet.0 10.0.0.0/24"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route table inet.0 label-switched-path my-lsp"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol ospf table inet.0 extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route protocol bgp table my-vrf.inet.0 extensive 10.0.0.0/24"}'
```

#### Advertising & Receiving Protocols
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route advertising-protocol bgp 10.1.1.2"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route advertising-protocol bgp 10.1.1.2 10.0.0.0/24"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route advertising-protocol bgp 10.1.1.2 10.0.0.0/24 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route receive-protocol bgp 10.1.1.2"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route receive-protocol bgp 10.1.1.2 10.0.0.0/24"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route receive-protocol bgp 10.1.1.2 extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route receive-protocol bgp 10.1.1.2 10.0.0.0/24 extensive"}'
```

#### Instance & Logical System
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route instance detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route instance my-vrf"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route logical-system my-lsys"}'
```

#### Forwarding Table
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route forwarding-table summary"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show route forwarding-table label 100000"}'
```

### MPLS

#### LSPs
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show mpls lsp name my-lsp detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show mpls lsp name my-lsp extensive"}'
```

#### LDP Parameters
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show mpls ldp parameters"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show mpls ldp discovery detail"}'
```

#### Configuration
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show configuration protocols mpls label-switched-path my-lsp"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show configuration protocols mpls path my-path"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show configuration interfaces ge-0/0/0 unit 0 family bridge vlan-id"}'
```

### LDP

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ldp overview"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ldp neighbor"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ldp session"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ldp session 10.1.1.2 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ldp interface ge-0/0/0"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ldp interface ge-0/0/0 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ldp database session 10.1.1.2"}'
```

### RSVP

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show rsvp neighbor"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show rsvp neighbor detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show rsvp session"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show rsvp session transit"}'
```

### Traffic Engineering Database (TED)

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ted database extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ted database extensive 10.0.0.1"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ted database 10.0.0.1"}'
```

### PFE (Packet Forwarding Engine)

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show pfe route summary"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show pfe statistics traffic"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show pfe statistics ip icmp"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show krt queue"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show krt state"}'
```

### Connectivity Tests

#### Ping
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"ping 10.0.0.2 count 5"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"ping 10.0.0.2 source 10.0.0.1 count 5"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"ping 10.0.0.2 size 1500 count 5 do-not-fragment"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"ping 10.0.0.2 source 10.0.0.1 size 1500 count 5 tos 184 rapid"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"ping 10.0.0.2 ttl 10 count 5 wait 2"}'
```

#### MPLS Ping
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"ping mpls rsvp my-lsp"}'
```

#### Traceroute
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"traceroute 10.0.0.2 no-resolve"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"traceroute 10.0.0.2 source 10.0.0.1 no-resolve"}'
```

---

## Workflows

### 1. JunOS OSPF Health Check
```
show ospf overview → area count, SPF runs, LSA count
→ show ospf neighbor → verify all adjacencies Full
→ show ospf interface brief → check interface states (DR/BDR/DROther)
→ show ospf database summary → LSA count per type
→ show ospf statistics → error counters, retransmits
→ Flag: neighbors not Full, interface cost mismatches, high retransmit counts
→ GAIT
```

### 2. JunOS BGP Session Audit
```
show bgp summary → peer state, prefixes received, session uptime
→ show bgp neighbor {peer} → per-peer: hold time, keepalive, AFI/SAFI, import/export policy
→ show route advertising-protocol bgp {peer} → what we advertise
→ show route receive-protocol bgp {peer} → what we receive
→ Flag: peers not Established, prefix count anomalies, flapping sessions
→ GAIT
```

### 3. MPLS LSP Verification
```
show mpls lsp name {lsp} detail → path, state, bandwidth
→ show rsvp session → RSVP session state
→ show ldp session → LDP adjacency state
→ show route table mpls.0 → label bindings
→ ping mpls rsvp {lsp} → end-to-end LSP verification
→ show ted database extensive → TE topology view
→ GAIT
```

### 4. Route Table Baseline
```
show route summary → route count per table and protocol
→ show route protocol ospf → OSPF-learned routes
→ show route protocol bgp → BGP-learned routes
→ show route protocol static → static routes
→ show route forwarding-table summary → FIB state
→ show pfe route summary → PFE forwarding entries
→ show krt queue → pending route updates (should be 0)
→ GAIT
```

### 5. End-to-End Connectivity Test
```
ping {target} count 5 → basic reachability
→ ping {target} size 1500 count 5 do-not-fragment → MTU verification
→ traceroute {target} no-resolve → path analysis
→ Correlate with show route {target} → verify expected next-hop
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-junos-system** | Chassis/system context (RE CPU, FPC state) for routing issues |
| **pyats-junos-interfaces** | Interface state complements routing protocol analysis |
| **junos-network** | JunOS MCP for config changes; pyATS for operational verification |
| **pyats-routing** | Same methodology for Cisco devices — multi-vendor routing audits |
| **pyats-parallel-ops** | pCall pattern for fleet-wide BGP/OSPF audits |
| **te-path-analysis** | ThousandEyes path data complements traceroute analysis |
| **netbox-reconcile** | Cross-reference learned routes with NetBox prefix assignments |
| **gait-session-tracking** | Every command logged in GAIT |

---

## Guardrails

- **All commands are read-only** — show, ping, traceroute only
- **No routing config changes** — never use set/delete protocols via this skill
- **Use count limits on ping** — always specify `count` to avoid infinite pings
- **Use `no-resolve` on traceroute** — avoids DNS timeouts
- **Cross-reference with SoT** — compare route tables with expected prefixes in NetBox/Nautobot
- **Record in GAIT** — every command execution must be logged
