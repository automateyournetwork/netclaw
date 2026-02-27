---
name: pyats-junos-interfaces
description: "JunOS interface operations via pyATS — physical/logical interfaces, LACP, CoS, LLDP, ARP, BFD, IPv6 neighbors, traffic monitoring, optics diagnostics"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# JunOS Interface Operations via pyATS

Inspect Juniper device interfaces, link aggregation, class of service, LLDP neighbors, ARP tables, BFD sessions, and optics diagnostics using pyATS `pyats_run_show_command`. Complements the JunOS MCP server (PyEZ/NETCONF) with SSH/CLI-based operational commands.

## How to Call

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"<command>"}'
```

---

## Commands

### Interface Status

#### All Interfaces — Summary
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces terse"}'
```
Compact table: interface name, admin/oper status, protocol, address. Fastest way to check up/down state across all interfaces.

#### All Interfaces — Full
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces"}'
```
Full interface details: physical properties, speed, MTU, MAC, traffic stats, error counters.

#### All Interfaces — Descriptions
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces descriptions"}'
```
Interface descriptions only — useful for verifying circuit IDs and peer identifiers. Also: `show interfaces descriptions ge-0/0/0`.

#### All Interfaces — Statistics
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces statistics"}'
```
Input/output bytes, packets, errors, drops across all interfaces. Also: `show interfaces statistics ge-0/0/0`.

#### All Interfaces — Extensive
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces extensive"}'
```
Maximum detail including MAC stats, filter stats, CoS queuing stats, logical interfaces. Also: `show interfaces extensive no-forwarding`.

### Specific Interface

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces ge-0/0/0"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces ge-0/0/0 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces ge-0/0/0 extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces ge-0/0/0 terse"}'
```

#### Terse with Match (Filter)
```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces terse | match ge-0/0"}'
```
Filter interface list to a specific FPC/PIC slot.

### Interface Policers & Queues

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces policers ge-0/0/0"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces queue ge-0/0/0"}'
```

### Optics Diagnostics

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces diagnostics optics"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show interfaces diagnostics optics ge-0/0/0"}'
```
SFP/XFP/QSFP optical power levels (tx/rx dBm), laser bias current, temperature, voltage. **Critical for detecting failing optics** — low rx power indicates fiber or SFP issue.

### LACP (Link Aggregation)

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show lacp interfaces ae0"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show lacp statistics interfaces ae0"}'
```
LACP state, actor/partner system ID, port priority, key, member link status. Statistics show LACP PDU tx/rx counts and errors.

### Class of Service

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show class-of-service interface ge-0/0/0"}'
```
CoS configuration and queue mapping for a specific interface — forwarding class, scheduler, transmit rate.

### LLDP Neighbors

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show lldp"}'
```
LLDP neighbor table — remote system, port, chassis ID. Cross-reference with pyats-topology for neighbor discovery.

### ARP Table

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show arp"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show arp no-resolve"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show arp | no-more"}'
```
ARP cache: MAC address, IP address, interface. `no-resolve` skips DNS lookups (faster). `| no-more` disables paging.

### IPv6 Neighbors

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ipv6 neighbors"}'
```
IPv6 NDP neighbor table — link-layer address, state (reachable/stale/incomplete), interface.

### BFD Sessions

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bfd session"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bfd session address 10.1.1.2 detail"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show bfd session address 10.1.1.2 extensive"}'
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"show ppm transmissions protocol bfd detail"}'
```
BFD session state, interval, multiplier, neighbor. Use for fast-failover validation on OSPF/BGP/LDP sessions.

### Traffic Monitoring

```bash
pyats_run_show_command '{"device_name":"juniper-rtr-01","command":"monitor interface traffic"}'
```
Real-time interface traffic rates — bytes/sec, packets/sec per interface. **Note:** This is a streaming command; pyATS will capture a snapshot.

---

## Workflows

### 1. JunOS Interface Health Check
```
show interfaces terse → identify down interfaces
→ show interfaces extensive {down_intf} → error counters, drops
→ show interfaces diagnostics optics {intf} → optical power levels
→ show lldp → verify expected neighbors
→ Severity-sort (down=CRITICAL, errors=WARNING, low optics=WARNING)
→ GAIT
```

### 2. LACP Audit
```
show interfaces terse | match ae → identify LAG interfaces
→ show lacp interfaces {ae_intf} → member status, actor/partner
→ show lacp statistics interfaces {ae_intf} → PDU counters, errors
→ show interfaces {ae_intf} extensive → aggregate stats
→ Flag: missing members, LACP mismatches, PDU errors
→ GAIT
```

### 3. Optics Fleet Scan
```
pyats_list_devices → identify JunOS devices (parallel)
→ show interfaces diagnostics optics per device
→ Flag: rx power < -20 dBm (WARNING), < -25 dBm (CRITICAL)
→ Cross-reference SFP serial numbers with NetBox
→ GAIT
```

### 4. ARP/Neighbor Audit
```
show arp no-resolve → collect ARP table
→ show ipv6 neighbors → collect NDP table
→ Cross-reference with NetBox/Nautobot IPAM → flag unknown MACs
→ show lldp → verify physical neighbors match expected topology
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-junos-system** | Chassis/system context for interface issues (FPC/PIC status) |
| **pyats-junos-routing** | Routing protocol status complements interface state |
| **junos-network** | JunOS MCP for config changes; pyATS for operational verification |
| **pyats-topology** | LLDP + ARP data feeds topology discovery |
| **netbox-reconcile** | Cross-reference interface IPs, MACs, optics serials with NetBox |
| **pyats-parallel-ops** | pCall pattern for fleet-wide interface audits |
| **gait-session-tracking** | Every command logged in GAIT |

---

## Guardrails

- **All commands are read-only** — show and monitor commands only
- **No interface config changes** — never use `set interfaces` via this skill
- **Cross-reference optics** — always compare diagnostic values against vendor specifications
- **Record in GAIT** — every command execution must be logged
