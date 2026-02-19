---
name: pyats-network
description: "Network device automation via pyATS - run show commands, ping, apply config, learn config/logging, list devices, run Linux commands, execute dynamic tests on Cisco IOS-XE/NX-OS devices"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# pyATS Network Device Tool

You have access to a pyATS MCP server that can interact with network devices defined in the testbed.

## Server & Testbed

- **Server script:** `$PYATS_MCP_SCRIPT`
- **Testbed:** `$PYATS_TESTBED_PATH`
- **Environment variable:** `PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH`

## Available Devices

- **R1** (devnetsandboxiosxec8k.cisco.com) — Cisco IOS-XE, C8000v/CSR1kv

## How to Call Tools

Pipe a JSON-RPC request into the server in `--oneshot` mode:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"TOOL_NAME","arguments":{...}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

## All 8 Available Tools

### 1. `pyats_list_devices`

List all devices in the testbed with their properties: name, alias, type, OS, platform, connection types, credentials summary.

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_list_devices","arguments":{}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Use when:** Starting any session — always list devices first to confirm connectivity and inventory.

### 2. `pyats_run_show_command`

Execute any show command with automatic Genie structured parsing. Returns parsed JSON when a Genie parser exists, raw text otherwise.

- `device_name` (string): Target device from testbed
- `command` (string): Show command — **must** start with "show"

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip interface brief"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Validation rules:**
- Must start with "show"
- No pipes (`|`), redirects (`>`), or shell characters
- Cannot include: copy, delete, erase, reload, write, configure keywords
- Do NOT use for `show running-config` or `show logging` — use the dedicated tools

**Commands with Genie parsers (structured JSON output) on IOS-XE:**

Routing:
- `show ip route` / `show ip route vrf <name>`
- `show ip protocols`
- `show ip bgp` / `show ip bgp summary` / `show ip bgp neighbors`
- `show ip ospf` / `show ip ospf neighbor` / `show ip ospf interface` / `show ip ospf database`
- `show ip eigrp neighbors` / `show ip eigrp topology`
- `show isis neighbors` / `show isis database`
- `show ip static route`

Interfaces:
- `show ip interface brief` / `show ipv6 interface brief`
- `show interfaces` / `show interfaces <name>`
- `show interfaces status`
- `show interfaces counters`
- `show ip interface`

L2/Switching:
- `show vlan` / `show vlan brief`
- `show spanning-tree` / `show spanning-tree detail`
- `show mac address-table`
- `show etherchannel summary`

Neighbors:
- `show cdp neighbors` / `show cdp neighbors detail`
- `show lldp neighbors` / `show lldp neighbors detail`

FHRP:
- `show standby` / `show standby brief`
- `show vrrp` / `show vrrp brief`

System:
- `show version`
- `show inventory`
- `show processes cpu` / `show processes cpu sorted`
- `show processes memory` / `show processes memory sorted`
- `show platform`
- `show ntp associations` / `show ntp status`
- `show snmp`
- `show clock`
- `show bootflash`
- `show license`

Security:
- `show access-lists` / `show ip access-lists`
- `show crypto isakmp sa` / `show crypto ipsec sa`
- `show dot1x`
- `show port-security`
- `show authentication sessions`

QoS:
- `show policy-map` / `show policy-map interface`

VRF / MPLS:
- `show vrf` / `show vrf detail`
- `show mpls forwarding-table`
- `show mpls ldp neighbor`

Other:
- `show arp`
- `show ip nat translations`
- `show ip dhcp binding`
- `show track`
- `show route-map`
- `show ip prefix-list`
- `show bfd neighbors`
- `show flow monitor`

### 3. `pyats_configure_device`

Apply configuration changes to a device. Automatically enters config mode and exits.

- `device_name` (string): Target device
- `config_commands` (list of strings OR multiline string): Configuration lines

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_configure_device","arguments":{"device_name":"R1","config_commands":["interface Loopback99","ip address 99.99.99.99 255.255.255.255","description NetClaw-Test","no shutdown"]}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Rules:**
- Do NOT include `configure terminal`, `conf t`, or `end` — the tool handles mode transitions
- DO include `exit` commands when you need to return to a higher config context
- Preserves indentation for submode commands (route-maps, ACLs, etc.)
- **Blocked commands:** `write erase`, `erase`, `reload`, `delete`, `format`

### 4. `pyats_show_running_config`

Retrieve the full running configuration from a device.

- `device_name` (string): Target device

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_show_running_config","arguments":{"device_name":"R1"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Use when:** Capturing configuration baselines, auditing config, pre/post change verification.

### 5. `pyats_show_logging`

Fetch system logs (last 250 entries) from a device.

- `device_name` (string): Target device

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_show_logging","arguments":{"device_name":"R1"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Use when:** Checking for errors, tracebacks, interface flaps, protocol events after changes.

### 6. `pyats_ping_from_network_device`

Execute ping from the network device itself (not from the MCP client).

- `device_name` (string): Source device
- `command` (string): Ping command (e.g., `ping 8.8.8.8`, `ping 10.0.0.1 repeat 100 source Loopback0`)

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_ping_from_network_device","arguments":{"device_name":"R1","command":"ping 8.8.8.8"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Returns:** Structured JSON with success rate %, RTT stats, packet loss when Genie parsing succeeds.

### 7. `pyats_run_linux_command`

Execute shell commands on Linux-based devices in the testbed.

- `device_name` (string): Linux-capable device
- `command` (string): Shell command

**Use when:** The testbed includes Linux hosts (containers, VMs) for system administration tasks.

### 8. `pyats_run_dynamic_test`

Execute a complete pyATS AEtest validation script inline. The script runs in a sandboxed environment.

- `test_script_content` (string): Complete Python AEtest script

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_dynamic_test","arguments":{"test_script_content":"import logging\nfrom pyats import aetest\n\nlogger = logging.getLogger(__name__)\n\nTEST_DATA = {\"expected_interfaces\": [\"GigabitEthernet1\", \"Loopback0\"]}\n\nclass InterfaceTest(aetest.Testcase):\n    @aetest.test\n    def verify_interfaces(self):\n        for intf in TEST_DATA[\"expected_interfaces\"]:\n            logger.info(f\"Checking interface: {intf}\")\n            assert intf.startswith(\"Gi\") or intf.startswith(\"Loop\"), f\"Unexpected interface type: {intf}\"\n\nif __name__ == \"__main__\":\n    aetest.main()"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Rules:**
- Must define `TEST_DATA` as a Python dict literal (not loaded from file/network)
- Cannot connect to devices (embed all data inline)
- 300-second timeout
- **Banned imports:** os, sys, subprocess, shutil, socket, pathlib, pickle, yaml, requests, urllib, http, ssl
- **Banned functions:** `__import__()`, `eval()`, `exec()`, `compile()`, `open()`, `json.loads()`

**Use when:** Complex pass/fail validation, multi-step assertions, compliance checks on data already collected via show commands.

## Alternative: Direct Python pyATS

For operations beyond the 8 MCP tools, use pyATS directly:

```python
from pyats.topology import loader
tb = loader.load('$PYATS_TESTBED_PATH')
device = tb.devices['R1']
device.connect(learn_hostname=True, log_stdout=False)
output = device.parse('show ip interface brief')
print(output)
device.disconnect()
```

### Genie Learn (multi-command feature snapshots)

```python
from genie.testbed import load
testbed = load('$PYATS_TESTBED_PATH')
dev = testbed.devices['R1']
dev.connect(learn_hostname=True, log_stdout=False)

# Learn returns an OS-agnostic normalized data model
ospf = dev.learn('ospf')       # Neighbors, interfaces, database, areas, LSAs
bgp = dev.learn('bgp')         # Neighbors, address-families, routes, state
intf = dev.learn('interface')   # All interfaces: status, IP, counters, MTU, speed
routing = dev.learn('routing')  # Full routing table from all protocols
platform = dev.learn('platform') # Hardware, modules, images, slots

print(ospf.info)
dev.disconnect()
```

All 34 learnable features: acl, arp, bgp, config, device, dot1x, eigrp, fdb, hsrp, igmp, interface, isis, lag, lisp, lldp, mcast, mld, msdp, nd, ntp, ospf, pim, platform, prefix_list, rip, route_policy, routing, static_routing, stp, terminal, utils, vlan, vrf, vxlan.

### Genie Diff (state comparison)

```python
from genie.utils.diff import Diff

# Capture before state
before = dev.learn('ospf')

# ... make changes ...

# Capture after state
after = dev.learn('ospf')

diff = Diff(before.info, after.info)
diff.findDiff()
print(diff)  # Shows + additions and - deletions
```
