---
name: cml-node-operations
description: CML node operations — start, stop, console access, CLI execution, config management, node details
version: 1.0.0
tags: [cml, nodes, console, cli, config]
---

# CML Node Operations

Operate individual CML nodes — start, stop, get console access, execute CLI commands, manage startup/running configurations, and inspect node state. This is how you interact with devices inside a CML lab.

## MCP Server

- **Command**: `cml-mcp` (pip-installed, stdio transport)
- **Requires**: `CML_URL`, `CML_USERNAME`, `CML_PASSWORD` environment variables
- **Optional**: `cml-mcp[pyats]` for CLI execution via pyATS

## Available Tools

### Node Lifecycle

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `start_node` | `lab_id`/`lab_title`, `node_id`/`node_label` | Start (boot) a single node |
| `stop_node` | `lab_id`/`lab_title`, `node_id`/`node_label` | Stop (shutdown) a single node |
| `get_node` | `lab_id`/`lab_title`, `node_id`/`node_label` | Get node details: state, CPU, RAM, interfaces, config |
| `get_nodes` | `lab_id`/`lab_title` | List all nodes with their current states |
| `wipe_node` | `lab_id`/`lab_title`, `node_id`/`node_label` | Wipe a node's configuration (reset to default) |

### Configuration Management

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `set_node_config` | `lab_id`/`lab_title`, `node_id`/`node_label`, `config` | Set a node's startup configuration |
| `get_node_config` | `lab_id`/`lab_title`, `node_id`/`node_label` | Get a node's current configuration |
| `download_lab_configs` | `lab_id`/`lab_title` | Download all node configs from a running lab |

### Console & CLI Access

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `get_node_console` | `lab_id`/`lab_title`, `node_id`/`node_label` | Get console connection details (URL, protocol) |
| `get_node_console_log` | `lab_id`/`lab_title`, `node_id`/`node_label`, `lines?` | Retrieve console log output from a running node |
| `execute_command` | `lab_id`/`lab_title`, `node_id`/`node_label`, `command` | Execute a CLI command on a running node (requires pyATS) |

## Node States

| State | Meaning |
|-------|---------|
| `DEFINED_ON_CORE` | Node exists but is not running |
| `BOOTING` | Node is in the process of booting |
| `BOOTED` | Node has finished booting and is reachable |
| `STOPPED` | Node has been shut down |

## Workflow: Configure and Boot a Node

When a user wants to configure a specific node:

1. **Check node state**: `get_node` to see current state
2. **Set startup config**: `set_node_config` with the full configuration
3. **Start the node**: `start_node` to boot it
4. **Wait for boot**: Nodes take 30-120 seconds depending on type
5. **Verify**: `execute_command` to run `show version` or `show ip int brief`
6. **Report**: Tell the user the node is ready

## Workflow: Collect Running Configs

When a user wants to back up or review configs:

1. **Ensure lab is running**: `get_lab` to check state
2. **Download all configs**: `download_lab_configs` gets everything at once
3. **Or target specific nodes**: `get_node_config` for individual nodes
4. **Optionally commit to GitHub**: Use github-ops skill to commit configs to a repo

## Workflow: Console Log Troubleshooting

When a user needs to see what happened during boot or troubleshoot a node:

1. **Check node state**: `get_node` — node must be BOOTED or BOOTING
2. **Get console log**: `get_node_console_log` to retrieve recent console output
3. **Analyze output**: Look for error messages, boot failures, config errors
4. **Common issues to spot**:
   - `%PARSER-4-BADCFG` — invalid configuration commands
   - `%LINK-3-UPDOWN` — interface state changes
   - `%OSPF-5-ADJCHG` — OSPF adjacency changes
   - `%BGP-5-ADJCHANGE` — BGP neighbor state changes
   - `%SYS-5-RESTART` — system restart messages
   - Boot failures, license errors, memory allocation errors
5. **Report**: Summarize the console log findings

## Workflow: Execute CLI Commands

When a user wants to run show commands or make live changes:

1. **Verify node is BOOTED**: `get_node` to check state
2. **Execute command**: `execute_command` with the CLI command
3. **Parse output**: Present the results in a readable format
4. **Multiple commands**: Run them sequentially, one `execute_command` per command

Common commands to execute:
```
show ip interface brief
show ip ospf neighbor
show ip bgp summary
show running-config
show cdp neighbor
show version
show ip route
show interfaces status
```

## Workflow: Reset and Reconfigure

When a user wants to start fresh with a node:

1. **Stop the node**: `stop_node`
2. **Wipe the config**: `wipe_node` resets to factory default
3. **Set new config**: `set_node_config` with the new startup configuration
4. **Start the node**: `start_node`
5. **Verify**: Execute show commands to confirm the new config took effect

## Startup Configuration Templates

### IOSv Router (Basic OSPF)
```
hostname {HOSTNAME}
!
interface Loopback0
 ip address {LOOPBACK_IP} 255.255.255.255
!
interface GigabitEthernet0/0
 ip address {MGMT_IP} {MASK}
 no shutdown
!
interface GigabitEthernet0/1
 ip address {P2P_IP} {MASK}
 no shutdown
!
router ospf 1
 router-id {LOOPBACK_IP}
 network {LOOPBACK_IP} 0.0.0.0 area 0
 network {P2P_NETWORK} {WILDCARD} area 0
!
line con 0
 logging synchronous
line vty 0 4
 login local
 transport input ssh
!
end
```

### IOSv Router (Basic BGP)
```
hostname {HOSTNAME}
!
interface Loopback0
 ip address {LOOPBACK_IP} 255.255.255.255
!
interface GigabitEthernet0/1
 ip address {PEER_IP} {MASK}
 no shutdown
!
router bgp {LOCAL_AS}
 bgp router-id {LOOPBACK_IP}
 bgp log-neighbor-changes
 neighbor {NEIGHBOR_IP} remote-as {REMOTE_AS}
 !
 address-family ipv4
  network {LOOPBACK_IP} mask 255.255.255.255
  neighbor {NEIGHBOR_IP} activate
 exit-address-family
!
end
```

### NX-OS Switch (Basic VXLAN Leaf)
```
hostname {HOSTNAME}
!
feature ospf
feature bgp
feature nv overlay
feature vn-segment-vlan-based
!
interface loopback0
  ip address {LOOPBACK_IP}/32
!
interface Ethernet1/1
  description To-Spine1
  no switchport
  ip address {P2P_IP}/30
  no shutdown
!
router ospf 1
  router-id {LOOPBACK_IP}
!
router bgp {AS}
  router-id {LOOPBACK_IP}
  neighbor {SPINE_IP} remote-as {AS}
    update-source loopback0
    address-family l2vpn evpn
      send-community extended
!
end
```

### IOS-XR Router (Basic IS-IS)
```
hostname {HOSTNAME}
!
interface Loopback0
 ipv4 address {LOOPBACK_IP} 255.255.255.255
!
interface GigabitEthernet0/0/0/0
 ipv4 address {P2P_IP} {MASK}
 no shutdown
!
router isis CORE
 is-type level-2-only
 net 49.0001.{SYSTEM_ID}.00
 address-family ipv4 unicast
  metric-style wide
 !
 interface Loopback0
  passive
  address-family ipv4 unicast
  !
 !
 interface GigabitEthernet0/0/0/0
  address-family ipv4 unicast
  !
 !
!
end
```

## Important Rules

- **Check node state before operations** — don't start an already-booted node or stop an already-stopped one
- **Wait for boot** — IOSv takes ~60s, NX-OS ~90s, IOS-XR ~120s to boot
- **`execute_command` requires pyATS** — the `cml-mcp[pyats]` extra must be installed
- **Set configs BEFORE starting** — `set_node_config` sets the startup config; apply it before boot
- **Use labels not IDs** — labels like "R1" are more human-readable than UUIDs
- **Record in GAIT** — log all configuration changes and CLI commands for audit trail

## Environment Variables

- `CML_URL` — CML server URL
- `CML_USERNAME` — CML username
- `CML_PASSWORD` — CML password
- `CML_VERIFY_SSL` — Verify SSL certificate (true/false)
