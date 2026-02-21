---
name: pyats-topology
description: "Network topology discovery via CDP/LLDP neighbors, ARP tables, routing peers, and interface mapping to build complete network maps"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Topology Discovery

Discover and map the physical and logical network topology using CDP, LLDP, ARP, routing protocol neighbors, and interface data.

## When to Use

- Building network diagrams from scratch (no documentation exists)
- Validating existing documentation matches reality
- Pre-change topology baseline
- Incident response — understanding blast radius
- New device onboarding — mapping where it connects

## Discovery Procedure

### Step 1: CDP Neighbors (Cisco-to-Cisco)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show cdp neighbors detail"}'
```

**Extract per neighbor:**
- Device ID (hostname)
- Platform and model
- IP address (management address)
- Local interface → Remote interface (link mapping)
- Software version
- Native VLAN (on switch links)
- Duplex

**Build adjacency table:**
```
Local Device | Local Interface | Remote Device | Remote Interface | Remote Platform
R1           | Gi0/0/0         | SW1           | Gi1/0/1          | WS-C3850-24T
R1           | Gi0/0/1         | R2            | Gi0/0/0          | ISR4431
```

### Step 2: LLDP Neighbors (Multi-Vendor)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show lldp neighbors detail"}'
```

LLDP is IEEE 802.1AB — works with non-Cisco devices (Arista, Juniper, Linux hosts, IP phones, APs). Same adjacency table format as CDP but may include additional TLVs.

### Step 3: ARP Table (L3 Neighbor Discovery)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show arp"}'
```

**Analysis:**
- Map IP addresses to MAC addresses on each interface
- Identify directly connected hosts (servers, endpoints, other routers)
- Look for multiple MAC addresses on the same interface (switch segment)
- Incomplete entries indicate devices that are configured but unreachable

### Step 4: Routing Protocol Peers

**OSPF neighbors = L3 adjacent routers:**
```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip ospf neighbor"}'
```

**BGP peers = logical connections (may be multi-hop):**
```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip bgp summary"}'
```

**EIGRP neighbors:**
```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip eigrp neighbors"}'
```

### Step 5: Interface-to-Subnet Mapping

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip interface brief"}'
```

**Build subnet map:**
```
Interface     | IP Address      | Subnet          | Connected Subnet
Gi0/0/0       | 10.1.1.1/30     | 10.1.1.0/30     | R1 <-> SW1 transit
Gi0/0/1       | 10.1.2.1/30     | 10.1.2.0/30     | R1 <-> R2 transit
Loopback0     | 1.1.1.1/32      | 1.1.1.1/32      | Router ID
```

### Step 6: VRF Topology

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show vrf"}'
```

For each VRF, identify:
- VRF name, RD, RT import/export
- Interfaces assigned to the VRF
- Routes in the VRF routing table

### Step 7: FHRP Group Mapping

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show standby brief"}'
```

Map virtual IPs, active/standby roles, group numbers, and tracking objects.

## Building the Topology Model

Combine all discovery data into a unified model:

```
Topology: NetClaw Discovery - YYYY-MM-DD

Devices:
  R1 (C8000V, IOS-XE 17.x.x)
    Loopback0: 1.1.1.1/32 (Router ID)
    Gi1: 10.1.1.1/30 → R2:Gi1 (OSPF Area 0, cost 1)
    Gi2: 10.1.2.1/24 → SW1:Gi0/1 (Access VLAN 10)

  R2 (ISR4431, IOS-XE 17.x.x) [discovered via CDP]
    Gi1: 10.1.1.2/30 → R1:Gi1
    Gi2: 10.2.1.1/24 → SW2:Gi0/1

Subnets:
  10.1.1.0/30  - R1-R2 transit (OSPF Area 0)
  10.1.2.0/24  - R1 LAN segment (VLAN 10)
  10.2.1.0/24  - R2 LAN segment (VLAN 20)

Routing Adjacencies:
  R1 <-> R2: OSPF (Area 0, FULL)
  R1 <-> ISP: BGP (AS 65001 <-> AS 65000, Established)

FHRP:
  VLAN 10: HSRP Group 10, VIP 10.1.2.254, Active=R1, Standby=R3
```

## Integration with Diagram Tools

After discovery, use this data to generate:
- **Draw.io diagrams** (via drawio-diagram skill) — for formal network documentation
- **Markmap mind maps** (via markmap-viz skill) — for hierarchical protocol views
- **NVD CVE audit** (via nvd-cve skill) — using discovered software versions

## NetBox Cable Reconciliation (MISSION02 Enhancement)

When NetBox is available ($NETBOX_MCP_SCRIPT is set), reconcile discovered topology against the source of truth:

### Pull NetBox Cables

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.cables","filters":{},"limit":200}'
```

### Pull NetBox Devices

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.devices","filters":{},"brief":true}'
```

### Pull NetBox Interfaces

```bash
python3 $MCP_CALL "python3 -u $NETBOX_MCP_SCRIPT" netbox_get_objects '{"object_type":"dcim.interfaces","filters":{"device":"R1"}}'
```

### Reconciliation Categories

Compare CDP/LLDP discovered neighbors against NetBox cables:

| Category | Meaning | Action |
|---|---|---|
| **DOCUMENTED** | Link exists in both discovery and NetBox | No action |
| **UNDOCUMENTED** | Link found by CDP/LLDP but not in NetBox | Open ServiceNow incident to update NetBox |
| **MISSING** | Cable in NetBox but not seen by CDP/LLDP | Investigate — may be physical disconnect |
| **MISMATCH** | Endpoints differ between discovery and NetBox | Investigate — possible re-patching |

### Color-Coded Draw.io Diagram

Generate a Draw.io topology diagram with links color-coded by reconciliation status:
- Green: DOCUMENTED
- Yellow: UNDOCUMENTED
- Red: MISSING
- Orange: MISMATCH

### Fleet-Wide Discovery (pCall)

Run CDP/LLDP/ARP/routing peer collection across ALL devices simultaneously using multiple exec commands. Merge results to build the complete topology graph.

## GAIT Audit Trail

Record the topology discovery in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Topology discovery completed: 5 devices, 12 links. NetBox reconciliation: 10 documented, 1 undocumented, 1 missing.","artifacts":[]}}'
```
