---
name: pyats-asa-firewall
description: "Cisco ASA firewall operations via pyATS — VPN sessions, failover state, interfaces, routing, service policies, resource usage, AnyConnect monitoring"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Cisco ASA Firewall Operations via pyATS

Inspect Cisco ASA firewalls using pyATS `pyats_run_show_command`. Covers VPN session monitoring (AnyConnect, WebVPN, IPSec), failover state, interfaces, routing, service policies, resource usage, and system inventory.

## Testbed Requirements

ASA devices in the pyATS testbed with `os: asa`:

```yaml
devices:
  asa-fw-01:
    os: asa
    type: firewall
    connections:
      cli:
        protocol: ssh
        ip: 10.0.0.10
        port: 22
    credentials:
      default:
        username: "%ENV{NETCLAW_USERNAME}"
        password: "%ENV{NETCLAW_PASSWORD}"
      enable:
        password: "%ENV{NETCLAW_ENABLE}"
```

## How to Call

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"asa-fw-01","command":"<command>"}'
```

---

## Commands

### System & Inventory

#### Version
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show version"}'
```
ASA software version, hardware model, serial number, RAM, flash, license, uptime, last reload reason.

#### Hardware Inventory
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show inventory"}'
```
Hardware inventory: chassis, modules, SFPs with serial numbers and PIDs.

#### Resource Usage
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show resource usage"}'
```
Per-context resource utilization: connections, xlates, hosts, NAT, routes, ACL elements. **Critical for multi-context ASA** — identifies contexts approaching resource limits.

### Failover & High Availability

#### Failover Status
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show failover"}'
```
Failover state (Active/Standby), peer state, last failover time, failover reason, stateful failover stats. **Check this first on any HA pair.**

#### Failover Interfaces
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show failover interface"}'
```
Failover and stateful failover link status, IP addresses, hello interval, peer monitoring.

### Interfaces

#### Interface Summary
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show interface ip brief"}'
```
Compact interface table: interface name, IP address, status (up/down), method.

#### Interface Detail
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show interface detail"}'
```
Full interface details: speed, duplex, MAC, input/output packets/bytes/errors, collision counts, CRC errors.

#### Interface Summary (Traffic)
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show interface summary"}'
```
Summary traffic stats per interface.

#### Interface Name Mapping
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show nameif"}'
```
Maps physical interface names to security zone names (e.g., GigabitEthernet0/0 → outside, GigabitEthernet0/1 → inside). Shows security level per interface.

### Routing

#### Routing Table
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show route"}'
```
Full routing table: connected, static, OSPF, EIGRP, BGP routes with next-hop, interface, metric, age.

### ARP Table

```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show arp"}'
```
ARP cache: interface, IP address, MAC address, age. Cross-reference with NetBox for MAC verification.

### ASP (Accelerated Security Path) Drops

```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show asp drop"}'
```
Packets dropped by the ASP — categorized by reason: flow-drop, acl-drop, inspect-drop, rpf-violated, no-route, etc. **Critical for troubleshooting** — reveals why traffic is being blocked.

### Security Contexts

```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show context"}'
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show context detail"}'
```
Multi-context ASA: list all security contexts, allocated interfaces, resource class, admin state. `detail` shows interface allocation and URL mappings.

### Traffic & Service Policies

#### Traffic Statistics
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show traffic"}'
```
Per-interface traffic rates: input/output packets/sec and bytes/sec.

#### Service Policy (MPF)
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show service-policy"}'
```
Modular Policy Framework hit counts: class-maps, inspect actions, policing, shaping, QoS. Shows connection counts per policy.

### VPN Sessions

#### VPN Session Summary
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show vpn-sessiondb summary"}'
```
Summary of all active VPN sessions by type: AnyConnect, L2L, WebVPN, clientless, total sessions, peak concurrent.

#### All VPN Sessions
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show vpn-sessiondb"}'
```
Full VPN session database — all types, user, duration, bytes, encryption.

#### AnyConnect Sessions
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show vpn-sessiondb anyconnect"}'
```
AnyConnect SSL VPN sessions: username, duration, bytes tx/rx, IP assignment, tunnel group, encryption, NAC result.

#### AnyConnect Inactive Sessions
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show vpn-sessiondb anyconnect sort inactivity"}'
```
AnyConnect sessions sorted by inactivity time — useful for identifying idle sessions consuming licenses.

#### WebVPN Sessions
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show vpn-sessiondb webvpn"}'
```
Clientless WebVPN sessions: user, duration, bytes, inactivity.

#### VPN Load Balancing
```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show vpn load-balancing"}'
```
VPN cluster load distribution across ASA peers — sessions per member, load percentage.

### IPSec / IKEv2

```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show crypto ikev2 sa"}'
```
IKEv2 Security Associations: peer, state (READY), local/remote IDs, encryption, PRF, DH group, lifetime.

### IP Pool

```bash
pyats_run_show_command '{"device_name":"asa-fw-01","command":"show ip local pool vpn-pool"}'
```
VPN IP address pool usage: available, in use, range. **Monitor for pool exhaustion** — running out of addresses blocks new VPN connections.

---

## Workflows

### 1. ASA Health Check
```
show version → ASA version, model, uptime, last reload
→ show failover → HA state (Active/Standby), peer health
→ show interface ip brief → interface up/down state
→ show resource usage → context resource utilization
→ show asp drop → dropped packet analysis
→ Severity-sort → GAIT
```

### 2. VPN Monitoring Dashboard
```
show vpn-sessiondb summary → total sessions by type, peak concurrent
→ show vpn-sessiondb anyconnect → active AnyConnect users
→ show vpn-sessiondb anyconnect sort inactivity → idle sessions
→ show ip local pool vpn-pool → address pool utilization
→ show vpn load-balancing → cluster distribution
→ show crypto ikev2 sa → IKEv2 tunnel state
→ Flag: pool > 80% used, sessions near license limit, idle > 8h
→ GAIT
```

### 3. ASA Failover Verification
```
show failover → verify Active/Standby state
→ show failover interface → failover link health
→ show interface ip brief → all interfaces match expected state
→ show route → routing table consistent with active role
→ show vpn-sessiondb summary → VPN sessions present on active unit
→ GAIT
```

### 4. ASA Security Audit
```
show version → verify supported ASA version (cross-reference NVD CVE)
→ show asp drop → analyze drop reasons for anomalies
→ show service-policy → policy hit counts, inspect actions
→ show context detail → verify context isolation (multi-context)
→ show traffic → per-interface throughput baseline
→ GAIT
```

### 5. VPN Troubleshooting
```
show vpn-sessiondb anyconnect → verify user session exists
→ show crypto ikev2 sa → IKEv2 tunnel established?
→ show interface ip brief → outside interface up?
→ show route → default route present?
→ show ip local pool vpn-pool → addresses available?
→ show asp drop → packets being dropped for this flow?
→ show service-policy → inspect policies blocking traffic?
→ GAIT
```

---

## Parallel Operations

Run ASA health checks across multiple firewalls concurrently:

```bash
# ASA Pair - Primary
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"asa-fw-01","command":"show failover"}'

# ASA Pair - Secondary
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"asa-fw-02","command":"show failover"}'

# Remote Site ASA
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"asa-remote-01","command":"show failover"}'
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-network** | Core pyATS commands for IOS-XE/NX-OS devices alongside ASA firewalls |
| **pyats-security** | CIS benchmark-style audits complement ASA-specific security checks |
| **pyats-parallel-ops** | pCall pattern for fleet-wide ASA health checks |
| **fmc-firewall-ops** | FMC manages FTD; ASA is managed directly — different platforms, similar mission |
| **ise-posture-audit** | ISE NAC results correlate with ASA VPN session NAC status |
| **netbox-reconcile** | Cross-reference ASA interfaces, IP assignments with NetBox |
| **nvd-cve** | Scan ASA version against NVD vulnerability database |
| **servicenow-change-workflow** | Gate ASA config changes behind ServiceNow CRs |
| **gait-session-tracking** | Every ASA command logged in GAIT |

---

## Guardrails

- **All commands are read-only** — show commands only
- **No config changes** — never use `configure terminal` or `write memory` via this skill
- **Monitor VPN pool usage** — alert when pool utilization exceeds 80%
- **Check failover before maintenance** — always verify HA state before any maintenance window
- **Cross-reference with SoT** — compare interface IPs and routes with NetBox
- **Record in GAIT** — every command execution must be logged
