---
name: pyats-routing
description: "CCIE-level routing protocol analysis - OSPF, BGP, EIGRP, IS-IS, static routes, RIB/FIB verification, redistribution audit, and convergence validation"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Routing Protocol Analysis

Deep routing protocol expertise for OSPF, BGP, EIGRP, IS-IS, and the routing table. This skill provides CCIE-level analysis workflows.

## Routing Table Analysis

Always start here. The routing table is the source of truth for forwarding decisions.

### Full Routing Table

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

### Per-Protocol Routes

```bash
# OSPF routes only
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route ospf"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot

# BGP routes only
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route bgp"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot

# Connected and static
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route connected"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot

echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route static"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

### VRF Routes

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route vrf MGMT"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Analysis checklist:**
- Route source codes: C (connected), S (static), O (OSPF), O IA (OSPF inter-area), O E1/E2 (OSPF external), B (BGP), D (EIGRP), D EX (EIGRP external)
- Administrative distance and metric for each route
- Next-hop reachability — is the next-hop IP actually reachable?
- Recursive lookups — routes pointing to next-hops resolved through other routes
- Equal-cost multipath (ECMP) — multiple next-hops for the same prefix
- Default route presence and source
- Unexpected route absence — if a prefix should be there but is not

---

## OSPF Deep Dive

### OSPF Process Overview

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip ospf"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Check:** Router ID, areas configured, SPF run count (high = instability), reference bandwidth, stub/NSSA config, authentication.

### OSPF Neighbors

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip ospf neighbor"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Neighbor state analysis:**
- FULL — Healthy, full adjacency
- FULL/DR or FULL/BDR — Normal on broadcast/NBMA networks
- FULL/DROTHER — Normal on broadcast/NBMA (non-DR/BDR)
- 2WAY/DROTHER — Normal, two DROTHERs don't form full adjacency
- INIT — One-way communication only → check MTU, ACLs, authentication
- EXSTART/EXCHANGE — Stuck in database exchange → MTU mismatch (most common), OSPF area mismatch, authentication
- LOADING — Stuck loading LSAs → database corruption, memory issues
- DOWN — No hello packets → interface down, ACL blocking, hello/dead timer mismatch

**Common OSPF problems and their symptoms:**
| Symptom | Likely Cause |
|---------|-------------|
| Stuck in EXSTART | MTU mismatch between neighbors |
| Stuck in INIT | Hello reaching neighbor but not returning (ACL, asymmetric routing) |
| Neighbor flapping | Unstable link, hello/dead timer too aggressive, CPU too high to process hellos |
| Missing routes | Area type mismatch (stub vs non-stub), missing `redistribute` or `default-information originate` |
| Suboptimal routing | Cost misconfiguration, missing `auto-cost reference-bandwidth` |

### OSPF Interfaces

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip ospf interface"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Check per interface:** Area assignment, network type (broadcast/point-to-point/NBMA), cost, hello/dead timers, DR/BDR election, authentication type, passive status.

### OSPF Database (LSDB)

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip ospf database"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**LSA types to understand:**
- Type 1 (Router LSA) — Every router generates one per area
- Type 2 (Network LSA) — DR generates on broadcast/NBMA segments
- Type 3 (Summary LSA) — ABR advertises between areas
- Type 4 (ASBR Summary) — ABR advertises ASBR reachability
- Type 5 (External LSA) — ASBR redistributes external routes
- Type 7 (NSSA External) — External routes in NSSA areas (converted to Type 5 at ABR)

**Red flags in LSDB:**
- Rapidly incrementing sequence numbers → LSA flooding loop
- Type 5 LSAs in stub area → misconfiguration
- Missing Type 3 LSAs for expected inter-area prefixes → ABR filtering or area mismatch
- Duplicate Router IDs → same RID on two routers

---

## BGP Deep Dive

### BGP Summary

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip bgp summary"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Check:** Local AS, router ID, table version, total paths/best paths, per-neighbor state.

**Neighbor state column meaning:**
- Number (e.g., 5) → Established, number = received prefixes
- `Idle` → Not configured correctly, or administratively shut
- `Idle (Admin)` → `neighbor shutdown` configured
- `Active` → TCP connection failing → check reachability, TTL, ACLs
- `Connect` → TCP SYN sent, no response
- `OpenSent` → TCP connected, waiting for OPEN reply
- `OpenConfirm` → OPEN received, waiting for KEEPALIVE
- `Established` → Healthy

### BGP Neighbors Detail

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip bgp neighbors"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Deep analysis per neighbor:**
- BGP state, uptime, last reset reason
- Messages sent/received (OPEN, UPDATE, KEEPALIVE, NOTIFICATION)
- Hold time and keepalive interval
- Address families negotiated
- Route-map/filter-list/prefix-list applied (inbound/outbound)
- Next-hop-self, soft-reconfiguration, route-reflector-client status
- Notification messages — decode the error code/subcode

**Common BGP problems:**
| Symptom | Likely Cause |
|---------|-------------|
| Stuck in Active | TCP connection failing — check ACL, reachability, `update-source`, `ebgp-multihop` |
| Neighbor flapping | Unstable link, route-map causing route churn, max-prefix exceeded |
| 0 prefixes received | No `network` or `redistribute` on remote side, outbound filter on remote, address-family not activated |
| Routes not in RIB | Next-hop unreachable (`next-hop-self` missing for iBGP), route filtered by policy |
| Suboptimal path | Weight/local-pref/AS-path/MED not set correctly |

### BGP Table

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip bgp"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**BGP best path selection order (memorize this):**
1. Highest Weight (Cisco proprietary, local to router)
2. Highest Local Preference (iBGP, default 100)
3. Locally originated (network/redistribute/aggregate)
4. Shortest AS-path
5. Lowest Origin (IGP < EGP < Incomplete)
6. Lowest MED (from same neighbor AS only)
7. eBGP over iBGP
8. Lowest IGP metric to next-hop
9. Oldest route (for eBGP)
10. Lowest router ID
11. Lowest neighbor IP

---

## EIGRP Analysis

### EIGRP Neighbors

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip eigrp neighbors"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Check:** Hold timer (resetting to max means hellos received), uptime, SRTT, RTO, Q count (should be 0 — non-zero means retransmission queue backed up).

### EIGRP Topology

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip eigrp topology"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**DUAL states:**
- Passive (P) → Route is stable, normal
- Active (A) → Route in active query state → DUAL is searching for a feasible successor → if stuck, SIA (Stuck In Active) will kill the neighbor

**EIGRP metric components (classic):** Bandwidth, Delay, Reliability, Load, MTU (only BW and delay used by default).

**EIGRP metric components (wide/named mode):** Throughput, Latency, Reliability, Load, MTU, Extended attributes.

---

## Redistribution Audit

When multiple routing protocols are in use, check redistribution points:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip protocols"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Redistribution checklist:**
- Is redistribution mutual (two-way)? Risk of routing loops
- Are route-maps/prefix-lists applied to redistribution? They should be
- Are metrics set correctly on redistribution? (seed metric for EIGRP, metric-type for OSPF)
- Is there a risk of suboptimal routing through the redistribution boundary?
- Administrative distance tuning — are AD values set to prefer the right protocol?

### Route Filtering Verification

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show route-map"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot

echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip prefix-list"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

---

## Convergence Validation

After any routing change, verify convergence:

1. Check all expected neighbor adjacencies are FULL/Established
2. Verify the routing table has all expected prefixes
3. Ping across the network from the device to validate data plane
4. Check logs for any protocol events during the change
5. Compare route counts before and after

```bash
# Verify route count
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route summary"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```
