---
name: pyats-config-mgmt
description: "Network change management - pre-change baselines, configuration deployment, post-change verification, rollback procedures, and compliance validation"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Configuration Management

Structured change management workflows for network configuration changes. Every change follows: Baseline → Plan → Apply → Verify → Document.

## Golden Rule

**NEVER apply configuration without first capturing a baseline.** If the change goes wrong, you need to know what to roll back to.

## Change Workflow

### Phase 1: Pre-Change Baseline

Capture the current state of everything the change might affect.

#### 1A: Save Running Configuration

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_show_running_config","arguments":{"device_name":"R1"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

Store this output — it is the rollback reference.

#### 1B: Capture Relevant State

Depending on the change type, capture the appropriate state:

**For interface changes:**
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip interface brief"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot

echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show interfaces"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**For routing changes:**
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip route"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot

echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip ospf neighbor"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot

echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip bgp summary"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**For ACL/security changes:**
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip access-lists"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

#### 1C: Connectivity Baseline

Ping critical targets before the change:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_ping_from_network_device","arguments":{"device_name":"R1","command":"ping 8.8.8.8 repeat 10"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

### Phase 2: Plan the Change

Before applying any config, explicitly state:
1. **What** config lines will be applied
2. **Why** each line is needed
3. **What** the expected effect is
4. **What** could go wrong (risk assessment)
5. **How** to verify success
6. **How** to rollback if it fails

### Phase 3: Apply Configuration

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_configure_device","arguments":{"device_name":"R1","config_commands":["interface Loopback99","ip address 99.99.99.99 255.255.255.255","description NetClaw-Managed","no shutdown"]}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Configuration best practices:**
- Apply one logical change at a time (don't batch unrelated changes)
- Do NOT include `configure terminal` or `end` — the tool handles this
- DO include `exit` when changing config context (e.g., exiting an interface)
- Use descriptive descriptions on interfaces and route-maps
- For complex changes (route-maps, ACLs), build the complete object before applying to an interface

**Common configuration patterns:**

**Interface configuration:**
```json
["interface GigabitEthernet2", "description WAN-Link-to-ISP", "ip address 203.0.113.1 255.255.255.252", "no shutdown"]
```

**OSPF configuration:**
```json
["router ospf 1", "router-id 1.1.1.1", "network 10.0.0.0 0.0.255.255 area 0", "passive-interface default", "no passive-interface GigabitEthernet1"]
```

**BGP configuration:**
```json
["router bgp 65001", "neighbor 10.1.1.2 remote-as 65002", "neighbor 10.1.1.2 description ISP-Peer", "address-family ipv4 unicast", "neighbor 10.1.1.2 activate", "neighbor 10.1.1.2 route-map ISP-IN in", "neighbor 10.1.1.2 route-map ISP-OUT out", "exit-address-family"]
```

**ACL configuration:**
```json
["ip access-list extended MGMT-ACCESS", "permit tcp 10.0.0.0 0.0.0.255 any eq 22", "permit tcp 10.0.0.0 0.0.0.255 any eq 443", "deny ip any any log"]
```

**Route-map configuration:**
```json
["route-map ISP-IN permit 10", "match ip address prefix-list ALLOWED-IN", "set local-preference 200", "exit", "route-map ISP-IN deny 99"]
```

**Static route:**
```json
["ip route 0.0.0.0 0.0.0.0 203.0.113.2 name DEFAULT-TO-ISP"]
```

**NTP configuration:**
```json
["ntp server 10.0.0.1 prefer", "ntp server 10.0.0.2", "ntp source Loopback0"]
```

### Phase 4: Post-Change Verification

Immediately after applying config, verify:

#### 4A: Check for Errors in Logs

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_show_logging","arguments":{"device_name":"R1"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

Look for new error messages that appeared after the change timestamp.

#### 4B: Verify the Config Was Applied

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_show_running_config","arguments":{"device_name":"R1"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

Compare with the pre-change config to confirm only intended changes were made.

#### 4C: Verify Expected State

Re-run the same show commands from Phase 1B and compare:
- Are routing adjacencies still up?
- Are the expected new routes present?
- Are interface states correct?
- Are ACL counters incrementing as expected?

#### 4D: Connectivity Verification

Re-ping all targets from Phase 1C:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_ping_from_network_device","arguments":{"device_name":"R1","command":"ping 8.8.8.8 repeat 10"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

Compare success rate and RTT with baseline.

### Phase 5: Rollback (If Needed)

If verification fails, roll back by applying the inverse configuration:

**To remove added config:**
```json
["no interface Loopback99"]
```

**To restore changed config:**
Apply the original configuration lines from the Phase 1A baseline.

**For complex rollbacks**, apply the entire relevant section from the saved running config.

After rollback, re-verify that the device returned to its baseline state.

## Change Documentation

After every change, produce a change report:

```
Change Report — YYYY-MM-DD HH:MM UTC
Device: R1 (devnetsandboxiosxec8k.cisco.com)
Requestor: [who requested the change]

Change Description:
  Added Loopback99 (99.99.99.99/32) for OSPF router-id migration

Config Applied:
  interface Loopback99
   ip address 99.99.99.99 255.255.255.255
   description OSPF-RID-Migration
   no shutdown

Pre-Change State:
  - Routing table: 47 routes
  - OSPF neighbors: 2 (FULL)
  - Connectivity: 100% to 8.8.8.8

Post-Change State:
  - Routing table: 48 routes (+1 connected 99.99.99.99/32)
  - OSPF neighbors: 2 (FULL) — no change
  - Connectivity: 100% to 8.8.8.8 — no change
  - New log entries: %LINEPROTO-5-UPDOWN: Loopback99 up/up

Verification: PASSED
Rollback Required: No
```

## Compliance Templates

### Minimum Security Baseline (Apply to Every New Device)

```json
[
  "service timestamps debug datetime msec localtime",
  "service timestamps log datetime msec localtime",
  "service password-encryption",
  "no ip source-route",
  "no ip http server",
  "ip http secure-server",
  "ip ssh version 2",
  "ip ssh time-out 60",
  "ip ssh authentication-retries 3",
  "login on-failure log",
  "login on-success log",
  "banner login ^ Authorized access only. All activity is monitored. ^"
]
```

### VTY Hardening

```json
[
  "line vty 0 4",
  "transport input ssh",
  "exec-timeout 15 0",
  "login local",
  "exit",
  "line vty 5 15",
  "transport input ssh",
  "exec-timeout 15 0",
  "login local"
]
```
