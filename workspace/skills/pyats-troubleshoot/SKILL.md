---
name: pyats-troubleshoot
description: "Systematic network troubleshooting - connectivity, routing, interface, protocol, and performance issues using structured OSI-layer and divide-and-conquer methodology"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Network Troubleshooting

Structured troubleshooting methodology for network issues. Follow the OSI model bottom-up or divide-and-conquer approach depending on the symptom.

## Troubleshooting Principles

1. **Define the problem** — What exactly is broken? Who reported it? What's the expected vs actual behavior?
2. **Gather facts** — Run show commands, check logs, verify config. Never assume.
3. **Consider possibilities** — Based on facts, list likely causes
4. **Create action plan** — Test one variable at a time
5. **Implement and verify** — Make one change, verify, document
6. **Document** — Record what was found and what fixed it

## Symptom: "I Can't Reach X" (Connectivity Loss)

### Layer 1: Physical

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show interfaces"}'
```

**Check:**
- Is the interface up/up? (admin up, line protocol up)
- If down/down → cable, SFP, or remote end shut
- If up/down → L2 protocol issue (encapsulation mismatch, keepalive failure)
- If administratively down → `no shutdown` needed
- CRC errors → bad cable, duplex mismatch, faulty optic
- Input errors → physical layer corruption
- Resets incrementing → interface flapping

### Layer 2: Data Link

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show arp"}'
```

**Check:**
- Is there an ARP entry for the next-hop? If not → L2 issue
- `Incomplete` ARP entries → destination not responding on the segment
- For switches: check MAC address table, VLAN assignment, STP state

### Layer 3: Network

```bash
# Check local interface has correct IP
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip interface brief"}'

# Check routing table for destination
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip route"}'

# Ping the destination
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"R1","command":"ping 10.0.0.1"}'
```

**L3 troubleshooting decision tree:**
1. Is there a route for the destination? → `show ip route <destination>`
2. If no route → routing protocol issue or missing static route
3. If route exists → what's the next-hop? Is next-hop reachable?
4. Ping the next-hop → if fails, problem is between this router and next-hop
5. Ping the destination from progressively closer routers (divide-and-conquer)
6. Ping with source interface specified to test specific paths

**Advanced ping options:**
```bash
# Ping with specific source
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"R1","command":"ping 10.0.0.1 source Loopback0"}'

# Ping with larger packet size (test MTU)
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"R1","command":"ping 10.0.0.1 size 1500 df-bit"}'

# Extended ping with repeat count
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_ping_from_network_device '{"device_name":"R1","command":"ping 10.0.0.1 repeat 100 source Loopback0"}'
```

### Layer 4+: ACLs and NAT

```bash
# Check ACLs that might be blocking traffic
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip access-lists"}'

# Check NAT translations
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip nat translations"}'
```

**ACL troubleshooting:**
- Check hit counts on deny statements — is the ACL dropping the traffic?
- Verify ACL is applied to the correct interface and direction (in vs out)
- Remember implicit `deny any` at the end of every ACL
- Check if ACL is referenced in a route-map or NAT rule

---

## Symptom: "Routing Protocol Adjacency Down"

### OSPF Neighbor Down

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip ospf neighbor"}'

PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip ospf interface"}'
```

**OSPF adjacency troubleshooting checklist:**
1. Can you ping the neighbor? (L1/L2/L3 reachability)
2. Are hello/dead timers matching? (must match)
3. Are area IDs matching? (must match)
4. Is authentication matching? (type and key must match)
5. Is the network type matching? (broadcast vs point-to-point)
6. Is MTU matching? (causes EXSTART/EXCHANGE stuck state)
7. Is the interface in the correct OSPF process and area?
8. Is the interface passive? (passive interfaces don't form adjacencies)
9. Is there an ACL blocking OSPF (protocol 89, multicast 224.0.0.5/224.0.0.6)?

### BGP Peer Down

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip bgp summary"}'

PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip bgp neighbors"}'
```

**BGP adjacency troubleshooting checklist:**
1. Can you reach the neighbor IP from the source IP? (TCP port 179)
2. Is `update-source` configured correctly? (iBGP typically uses Loopback)
3. Is `ebgp-multihop` needed? (if eBGP peer is not directly connected)
4. Is the neighbor AS number correct?
5. Is the password matching? (if MD5 authentication configured)
6. Is there an ACL blocking TCP port 179?
7. Is `neighbor X activate` present under the correct address-family?
8. Is the neighbor administratively shut? (`neighbor X shutdown`)
9. Check NOTIFICATION messages in `show ip bgp neighbors` for error codes

**BGP NOTIFICATION error codes:**
| Code | Meaning |
|------|---------|
| 1 - Message Header Error | Malformed packet |
| 2 - OPEN Message Error | Capability mismatch, bad AS, bad hold time |
| 3 - UPDATE Message Error | Malformed UPDATE, invalid path attribute |
| 4 - Hold Timer Expired | Peer stopped sending KEEPALIVEs |
| 5 - FSM Error | Unexpected state transition |
| 6 - Cease | Administrative shutdown, max-prefix exceeded, peer deconfigured |

---

## Symptom: "Slow Performance / High Latency"

### Step 1: Check Device Resources

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show processes cpu sorted"}'

PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show processes memory sorted"}'
```

### Step 2: Check Interface Utilization and Errors

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show interfaces"}'
```

**Look for:**
- High input/output rate relative to interface speed → congestion
- Output drops → congestion (needs QoS or bandwidth upgrade)
- Input errors / CRC errors → physical layer issues causing retransmissions
- Overruns → CPU can't process packets fast enough

### Step 3: Check QoS Policy

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show policy-map interface"}'
```

**Check:** Class drops, queue depths, policing rates.

### Step 4: Verify Routing Path

Is traffic taking the expected path?

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip route 10.0.0.1"}'
```

Is traffic taking a suboptimal path through a slower link? Check metrics, AD values, and path selection.

### Step 5: Check for Routing Loops

Symptoms: incrementing TTL-exceeded counters, packets bouncing between two routers.

```bash
# Check for TTL exceeded ICMP messages
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"R1"}'
```

Trace the route: check the next-hop for the destination on each router in the path. If router A points to B and B points back to A → routing loop.

---

## Symptom: "Interface Flapping"

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"R1"}'

PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show interfaces"}'
```

**Common causes of interface flapping:**
- Bad cable or SFP (CRC errors, input errors)
- Duplex mismatch (one end auto, other end forced)
- Speed mismatch
- Power issues (PoE budget exceeded on switch ports)
- Carrier/ISP issue on WAN links
- STP topology change (on switched networks)
- Aggressive OSPF/BGP timers causing protocol flap on congested links

**Logs to look for:**
- `%LINEPROTO-5-UPDOWN` — interface state transitions with timestamps
- `%LINK-3-UPDOWN` — physical link state changes
- Frequency of flaps: every few seconds = likely physical; every few minutes = possible timer/keepalive issue

---

## NetBox Cross-Reference (MISSION02 Enhancement)

When NetBox is available ($NETBOX_MCP_SCRIPT is set), query the source of truth during investigation to validate expected state vs reality:

### Check Expected Interface State

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.interfaces","filters":{"device":"R1"},"brief":true}'
```

**Use during troubleshooting:**
- Connectivity loss → Is the interface supposed to be up? What IP should it have?
- Interface flapping → What cable/circuit is documented? What's the remote end?
- Routing issues → What prefix/VLAN is assigned in NetBox vs what the device shows?

### Check Expected Cables and Neighbors

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.cables","filters":{"device":"R1"}}'
```

**Compare:** If CDP/LLDP shows a different neighbor than NetBox documents, the physical topology may have changed without being updated — flag for investigation.

### Check Expected IP Assignments

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"ipam.ip-addresses","filters":{"device":"R1"}}'
```

**Compare:** Flag IP_DRIFT if device IP differs from NetBox. This is often the root cause of "can't reach X" tickets when someone changed an IP without updating the source of truth.

---

## Multi-Hop Parallel State Collection (pCall)

When troubleshooting spans multiple devices (e.g., connectivity between R1 and R4 traversing R2 and R3), collect state from ALL suspect hops simultaneously rather than one at a time:

### Parallel State Gathering

First, list all devices to identify the path:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_list_devices
```

Then run the same show commands on ALL hops concurrently. For example, for a connectivity loss between R1 and R4:

Run these commands on R1, R2, R3, and R4 simultaneously:
- `show ip interface brief` — interface state on every hop
- `show ip route <destination>` — does each hop have a route?
- `show ip arp` — is next-hop reachable at L2?
- `show ip ospf neighbor` or `show ip bgp summary` — adjacency state

**Benefit:** Instead of spending 4 sequential rounds (one per device), you get the complete picture in a single parallel pass. This lets you immediately identify where in the path the failure occurs.

### Parallel Adjacency Check

When an OSPF or BGP adjacency is down, always check BOTH ends simultaneously:

```bash
# Run on BOTH peers at the same time
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip ospf neighbor"}'
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R2","command":"show ip ospf neighbor"}'
```

Compare: timer mismatches, area mismatches, authentication failures, and MTU issues require data from both ends to diagnose.

### Severity-Sorted Results

After collecting parallel state, sort findings by severity for triage:

```
┌──────────┬────────────────────────┬──────────┐
│ Device   │ Finding                │ Severity │
├──────────┼────────────────────────┼──────────┤
│ R2       │ No route to 10.4.0.0/24│ CRITICAL │
│ R3       │ Gi2 down/down          │ CRITICAL │
│ R1       │ ARP incomplete for NH  │ HIGH     │
│ R4       │ All interfaces up      │ HEALTHY  │
└──────────┴────────────────────────┴──────────┘

Root cause: R3 Gi2 is down → R2 lost its route via R3 → R1 can't ARP for an unreachable next-hop.
```

---

## GAIT Audit Trail

After completing a troubleshooting session, record findings and resolution in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Troubleshooting: Connectivity loss R1→R4. Root cause: R3 Gi2 down/down (cable fault). Resolution: Escalated to field team for cable replacement. Verified routing reconverged via alternate path R1→R2→R5→R4.","artifacts":[]}}'
```

---

## General Troubleshooting Commands Quick Reference

| What to Check | Command |
|---------------|---------|
| Interface status | `show ip interface brief` |
| Interface details | `show interfaces <name>` |
| Routing table | `show ip route` |
| Specific route | `show ip route <ip>` |
| OSPF neighbors | `show ip ospf neighbor` |
| BGP summary | `show ip bgp summary` |
| EIGRP neighbors | `show ip eigrp neighbors` |
| ARP table | `show arp` |
| ACLs with hit counts | `show ip access-lists` |
| NAT translations | `show ip nat translations` |
| CPU usage | `show processes cpu sorted` |
| Memory usage | `show processes memory sorted` |
| System logs | use `pyats_show_logging` tool |
| Running config | use `pyats_show_running_config` tool |
| Connectivity test | use `pyats_ping_from_network_device` tool |
