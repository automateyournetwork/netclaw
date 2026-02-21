---
name: pyats-parallel-ops
description: "Fleet-wide parallel device operations - concurrent health checks, config audits, routing snapshots, severity-sorted reporting, and failure-isolated multi-device automation"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Parallel Fleet Operations

Execute operations across multiple network devices concurrently using OpenClaw's pCall (parallel call) capability. This skill governs how to scale single-device operations to an entire fleet with failure isolation, result aggregation, and severity-sorted reporting.

## When to Use

- Fleet-wide health checks across all devices in the testbed
- Mass configuration audits (collect running configs from every device)
- Network-wide routing table snapshots for baseline or comparison
- Pre/post change validation across all affected devices simultaneously
- Any operation where running sequentially on 10+ devices would be too slow

## How pCall Works in OpenClaw

In OpenClaw, parallel execution (pCall) is achieved by **listing multiple exec commands in a single response**. The agent runtime dispatches them concurrently and collects all results before proceeding.

### Key Principles

1. **Group by role or site** -- Organize devices into logical groups (core, distribution, access, WAN, DC) before dispatching
2. **Run operations concurrently** -- List one MCP call per device; they execute in parallel
3. **Failure isolation** -- If one device times out or errors, the other results are still collected
4. **Result aggregation** -- Collect all results, then produce a unified fleet report
5. **Severity sorting** -- Sort findings from CRITICAL to HEALTHY so the worst problems surface first

### pCall Pattern

To run the same command on multiple devices in parallel, list the calls together:

```bash
# Device 1
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show version"}'

# Device 2
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R2","command":"show version"}'

# Device 3
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"SW1","command":"show version"}'
```

All three commands execute concurrently. Results arrive independently and are aggregated by the agent.

## Step 0: Discover the Fleet

Always start by listing all devices in the testbed so you know what to operate on:

```bash
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_list_devices '{}'
```

This returns every device with its name, platform, OS, and connection details. Use this to build the device list for parallel operations.

## Example 1: Fleet-Wide Health Check

Run a health check on all devices in the testbed concurrently.

### Phase 1: Parallel Data Collection

Issue these commands simultaneously -- one set per device:

```bash
# R1 - CPU and memory
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show processes cpu sorted"}'

# R2 - CPU and memory
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R2","command":"show processes cpu sorted"}'

# SW1 - CPU and memory
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"SW1","command":"show processes cpu sorted"}'
```

Then in a second parallel wave, collect interface and NTP status:

```bash
# R1 - Interfaces
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip interface brief"}'

# R2 - Interfaces
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R2","command":"show ip interface brief"}'

# SW1 - Interfaces
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"SW1","command":"show ip interface brief"}'
```

### Phase 2: Parallel Log Collection

```bash
# R1 - Logs
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"R1"}'

# R2 - Logs
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"R2"}'

# SW1 - Logs
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_logging '{"device_name":"SW1"}'
```

### Phase 3: Aggregate and Report

After all parallel results return, analyze each device individually and produce the fleet summary (see Fleet Report Format below).

## Example 2: Fleet-Wide Config Audit

Collect the running configuration from every device in parallel for compliance analysis.

```bash
# R1 - Running config
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_running_config '{"device_name":"R1"}'

# R2 - Running config
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_running_config '{"device_name":"R2"}'

# SW1 - Running config
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_running_config '{"device_name":"SW1"}'

# SW2 - Running config
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_show_running_config '{"device_name":"SW2"}'
```

After collection, apply the **pyats-security** audit checks to each config and produce a fleet-wide security posture report.

**Common config audit checks to apply in parallel:**
- SSH version 2 only
- No telnet on VTY lines
- `service password-encryption` enabled
- VTY access-class applied
- NTP configured
- Logging host configured
- No default SNMP community strings

## Example 3: Fleet-Wide Routing Table Snapshot

Capture the routing table from every device simultaneously for baseline documentation or pre-change verification.

```bash
# R1 - Full routing table
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R1","command":"show ip route"}'

# R2 - Full routing table
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R2","command":"show ip route"}'

# R3 - Full routing table
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R3","command":"show ip route"}'

# R4 - Full routing table
PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 $MCP_CALL "python3 -u $PYATS_MCP_SCRIPT" pyats_run_show_command '{"device_name":"R4","command":"show ip route"}'
```

After collection, analyze per device:
- Total route count by protocol (connected, static, OSPF, BGP, EIGRP)
- Default route presence and source
- Expected prefix verification
- ECMP paths for critical prefixes

Produce a fleet routing summary:

```
Fleet Routing Snapshot - YYYY-MM-DD HH:MM UTC

┌──────────┬────────┬────────┬──────┬──────┬──────────────┬─────────┐
│ Device   │ Total  │ Conn.  │ OSPF │ BGP  │ Default Rte  │ Status  │
├──────────┼────────┼────────┼──────┼──────┼──────────────┼─────────┤
│ R1       │ 47     │ 5      │ 12   │ 28   │ via 10.1.1.2 │ HEALTHY │
│ R2       │ 45     │ 4      │ 12   │ 27   │ via 10.1.1.1 │ HEALTHY │
│ R3       │ 38     │ 3      │ 12   │ 21   │ via 10.2.1.1 │ WARNING │
│ R4       │ 0      │ 0      │ 0    │ 0    │ MISSING      │ CRITICAL│
└──────────┴────────┴────────┴──────┴──────┴──────────────┴─────────┘
```

## Example 4: Severity-Sorted Fleet Reporting

After collecting results from all devices, aggregate findings and sort by severity. This is the standard output format for all fleet operations.

### Severity Levels

1. **CRITICAL** -- Immediate action required. Device unreachable, process crash, zero routes, total connectivity loss.
2. **HIGH** -- Fix within hours. CPU > 90%, memory > 95%, routing adjacency down, interface flapping.
3. **MEDIUM** -- Fix within days. Missing NTP, elevated CPU (50-75%), log errors, config non-compliance.
4. **HEALTHY** -- No issues. All checks passed.

### Fleet Report Format

```
Fleet Health Report - YYYY-MM-DD HH:MM UTC
Testbed: production-network
Devices scanned: 8 | Duration: 12s (parallel)

=== CRITICAL (Immediate Action) ===

[C-001] R4 - UNREACHABLE
  Connection timed out after 30s. Verify device is powered on and management IP is reachable.
  Impact: No data collected for R4. Manual investigation required.

[C-002] SW2 - CPU 97% (5min avg)
  Top process: OSPF-1 Hello (45%), IP Input (32%)
  Impact: Risk of control plane failure. OSPF hellos may be missed.

=== HIGH (Fix Within Hours) ===

[H-001] R2 - GigabitEthernet3 down/down
  Last state change: 2 hours ago. 47 resets in last 24h.
  Impact: Backup WAN link unavailable. No redundancy for site B.

[H-002] SW1 - OSPF neighbor 3.3.3.3 in INIT state
  Expected: FULL. Interface: Vlan100. Duration: 45 minutes.
  Impact: Inter-VLAN routing for VLAN 100 may be impaired.

=== MEDIUM (Fix Within Days) ===

[M-001] R1 - NTP not synchronized
  No peer with '*' in show ntp associations. Clock offset: unknown.
  Impact: Log timestamps may be inaccurate for forensics.

[M-002] R3 - 3 OSPF adjacency flaps in last 24h
  Neighbors affected: 2.2.2.2 on Gi1 (flapped 3 times).
  Impact: Route convergence events. Brief traffic disruption during SPF.

=== HEALTHY ===

R1: All checks passed (CPU 12%, Mem 45%, 4/4 interfaces up, OSPF stable)
R3: All checks passed (CPU 8%, Mem 38%, 3/3 interfaces up, BGP stable)
SW3: All checks passed (CPU 5%, Mem 22%, 24/24 ports up, STP stable)

=== FLEET SUMMARY ===

┌──────────┬──────────┬──────────────────────────────────────────────┐
│ Device   │ Status   │ Key Finding                                  │
├──────────┼──────────┼──────────────────────────────────────────────┤
│ R4       │ CRITICAL │ Unreachable - connection timeout              │
│ SW2      │ CRITICAL │ CPU 97% - OSPF/IP Input                      │
│ R2       │ HIGH     │ Gi3 down/down - 47 resets                    │
│ SW1      │ HIGH     │ OSPF neighbor INIT - Vlan100                 │
│ R1       │ MEDIUM   │ NTP not synchronized                         │
│ R3       │ MEDIUM   │ 3 OSPF flaps in 24h                          │
│ R1       │ HEALTHY  │ All checks passed                            │
│ R3       │ HEALTHY  │ All checks passed                            │
│ SW3      │ HEALTHY  │ All checks passed                            │
└──────────┴──────────┴──────────────────────────────────────────────┘

Overall Fleet Status: CRITICAL (2 critical, 2 high, 2 medium, 3 healthy)
```

## Failure Isolation

When one device fails during parallel execution, it does **not** block or cancel the other operations:

- **Connection timeout** -- Mark device as CRITICAL/UNREACHABLE, continue with others
- **Command error** -- Record the error for that device, continue collecting from others
- **Parse failure** -- Fall back to raw text output for that device, report as WARNING

### Handling Unreachable Devices

```bash
# If R4 times out, you still get results from R1, R2, R3
# In the fleet report, R4 appears as:
#   [C-001] R4 - UNREACHABLE
#   Connection timed out. Device excluded from further checks.
```

The key principle: **always produce a report for every device, even if the report says "unreachable."**

## Grouping Strategies

### By Role

Group devices by their function in the network to prioritize operations:

```
Core routers:    R1, R2          (check first - highest blast radius)
Distribution:    SW1, SW2        (check second)
Access:          SW3, SW4, SW5   (check third)
WAN:             WAN1, WAN2      (check in parallel with core)
```

### By Site

For multi-site networks, group by location:

```
Site A (HQ):      R1, SW1, SW2
Site B (Branch):  R2, SW3
Site C (DR):      R3, SW4
```

### By Change Scope

When validating a change, group by affected vs unaffected:

```
Affected devices:    R1, R2       (check thoroughly - full health check)
Adjacent devices:    SW1, R3      (check routing adjacencies and connectivity)
Unaffected devices:  SW3, SW4     (spot check - verify no collateral damage)
```

## Scaling Guidelines

| Fleet Size | Strategy |
|------------|----------|
| 1-5 devices | Single parallel wave, all commands at once |
| 6-20 devices | Two waves: critical devices first, then remaining |
| 20-50 devices | Group by role/site, run 10-15 devices per wave |
| 50+ devices | Group by site, sample 20% per wave, expand if issues found |

For large fleets, start with a **sampling strategy**: pick 2-3 devices per role per site, run full health checks, then expand to the full fleet only if anomalies are found.

## Integration with Other Skills

- **pyats-health-check** -- The single-device health check procedure. pCall scales it to the fleet by issuing one health check per device in parallel.
- **pyats-security** -- Fleet-wide security audit. Collect all running configs in parallel, then apply security checks to each config.
- **pyats-topology** -- Fleet-wide topology discovery. Run CDP/LLDP neighbor collection on all devices in parallel to build the complete network map.
- **pyats-dynamic-test** -- Run the same aetest validation script against multiple devices in parallel for fleet-wide compliance testing.
- **pyats-config-mgmt** -- Pre/post change validation on all affected devices simultaneously.
- **drawio-diagram** -- After fleet discovery, generate a topology diagram showing device status (color-coded by health severity).
- **markmap-viz** -- Generate fleet health mind maps organized by severity or site.
