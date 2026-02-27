---
name: pyats-linux-network
description: "Linux host network operations via pyATS — interface configuration, routing tables, network connections, and multi-table route inspection across fleet hosts"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Linux Host Network Operations

Inspect and analyze networking on Linux hosts in the pyATS testbed using `pyats_run_linux_command`. This skill covers interface configuration, routing tables (including policy routing), and network connection state.

## Testbed Requirements

Linux hosts must be defined in the pyATS testbed with `os: linux`. See **pyats-linux-system** for the testbed YAML format.

## How to Call

All commands use `pyats_run_linux_command`:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"<command>"}'
```

## Commands

### Interface Configuration

#### All Interfaces

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ifconfig"}'
```

Returns all interfaces with: IP address, netmask, broadcast, MAC address, MTU, RX/TX packets, RX/TX errors, RX/TX bytes, flags (UP/RUNNING/MULTICAST).

**What to check:**
- Interface UP/DOWN state — is the expected interface active?
- IP address correctness — does it match NetBox/Nautobot records?
- RX/TX errors — non-zero errors indicate physical or driver issues
- MTU — verify jumbo frames (9000) or standard (1500) as expected
- Dropped packets — may indicate buffer or rate-limit issues

#### Specific Interface

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ifconfig eth0"}'
```

Common interfaces to inspect:
- `eth0` / `ens192` — Primary management interface
- `docker0` — Docker bridge network
- `lo` — Loopback (verify 127.0.0.1)
- `bond0` — NIC bonding/teaming
- `vlan100` — VLAN sub-interface
- `tun0` / `wg0` — VPN tunnel interfaces
- `br-*` — Docker/bridge networks

### Routing Tables

#### Full Routing Table (All Tables)

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ip route show table all"}'
```

Returns routes from ALL routing tables — main, local, custom policy tables. This is the most comprehensive route view on a Linux host.

**What to check:**
- Default gateway present and correct
- Expected subnets reachable via correct interfaces
- Policy routing tables (table 100, table 200, etc.) configured correctly
- No blackhole or unreachable routes (unless intentional)
- Metric values — lower metric = preferred path

#### Legacy Route Command

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"route"}'
```

Legacy `route` command — shows the kernel IP routing table (main table only). Prefer `ip route show table all` for complete view.

#### Route with Flags

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"route -n"}'
```

The `-n` flag shows numeric addresses (no DNS resolution). Other useful flags:
- `route -n` — Numeric output (faster, no DNS dependency)
- `route -e` — Extended information (like `netstat -r`)

### Network Connections

#### Routing Table via netstat

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"netstat -rn"}'
```

`netstat -rn` shows the kernel routing table in numeric format. Equivalent to `route -n` but with netstat-style output columns: Destination, Gateway, Genmask, Flags, MSS, Window, irtt, Iface.

**Route flags:**
- `U` — Route is up
- `G` — Route uses a gateway
- `H` — Target is a host (not a network)
- `D` — Created by ICMP redirect
- `M` — Modified by ICMP redirect

---

## Workflows

### 1. Linux Network Health Check
```
pyats_list_devices → identify Linux hosts in testbed
→ pyats_run_linux_command(host, "ifconfig") → check interface states
→ pyats_run_linux_command(host, "ip route show table all") → verify routing
→ pyats_run_linux_command(host, "netstat -rn") → cross-reference routes
→ Flag: interfaces down, missing routes, error counters > 0
→ Severity-sort → GAIT
```

### 2. Linux Network Audit
```
pyats_list_devices → identify all Linux hosts
→ pyats_run_linux_command per host ("ifconfig") → collect interface data
→ Cross-reference IPs with NetBox/Nautobot IPAM → flag drift
→ pyats_run_linux_command per host ("ip route show table all") → collect routes
→ Verify default gateways match expected values
→ GAIT
```

### 3. Multi-Host Routing Comparison
```
pyats_run_linux_command(host-1, "ip route show table all") → host 1 routes
→ pyats_run_linux_command(host-2, "ip route show table all") → host 2 routes
→ Compare: same subnets, same gateways, same metrics?
→ Flag asymmetric routing or missing routes
→ GAIT
```

### 4. Interface Error Investigation
```
pyats_run_linux_command(host, "ifconfig") → check all interfaces
→ Identify interfaces with non-zero RX/TX errors or drops
→ pyats_run_linux_command(host, "ifconfig eth0") → deep dive on problem interface
→ Correlate with network device interfaces (pyats-network show commands)
→ GAIT
```

### 5. Post-Change Network Verification
```
ServiceNow CR must be in Implement state
→ pyats_run_linux_command(host, "ifconfig") → verify interface state post-change
→ pyats_run_linux_command(host, "ip route show table all") → verify routes post-change
→ pyats_run_linux_command(host, "netstat -rn") → confirm routing table
→ Compare against pre-change baseline
→ GAIT
```

---

## Parallel Operations

Run network checks across multiple Linux hosts concurrently:

```bash
# Host 1
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-01","command":"ifconfig"}'

# Host 2
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-02","command":"ifconfig"}'

# Host 3
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_linux_command '{"device_name":"linux-host-03","command":"ifconfig"}'
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-network** | Correlate Linux host interfaces with network device interfaces — verify end-to-end connectivity |
| **pyats-routing** | Compare Linux host routes with network device routing tables (OSPF, BGP, EIGRP) |
| **pyats-linux-system** | System-level commands (ps, docker, ls) complement network-level inspection |
| **pyats-linux-vmware** | VMware ESXi host networking (vSwitch, vmkernel) via vim-cmd |
| **pyats-parallel-ops** | pCall pattern for fleet-wide Linux network audits |
| **pyats-troubleshoot** | Linux host network data feeds into OSI-layer troubleshooting |
| **netbox-reconcile** | Cross-reference ifconfig IP/MAC data against NetBox IPAM and DCIM records |
| **nautobot-sot** | Same as NetBox — validate Linux host IP addresses against Nautobot |
| **subnet-calculator** | Verify subnet masks and CIDR notation from ifconfig output |
| **gait-session-tracking** | Every Linux network command logged in GAIT |

---

## Guardrails

- **Always call `pyats_list_devices` first** — verify Linux hosts exist in the testbed
- **Read-only commands only** — ifconfig, ip route show, netstat, route are all read-only
- **No configuration changes** — never use `ip addr add`, `ip route add`, `ifconfig up/down`, or `iptables` via this skill
- **Gate network changes behind ServiceNow** — if extending to write operations, require a Change Request
- **Cross-reference with SoT** — always compare discovered IPs and routes against NetBox/Nautobot
- **Record in GAIT** — every command execution must be logged
