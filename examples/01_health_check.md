# Example: Device Health Check

## Prompt

```
Run a full health check on R1
```

## What NetClaw Does

NetClaw uses the **pyats-health-check** skill to run an 8-step assessment:

### Step 1: Device Identity & Uptime

```
→ pyats_run_show_command: show version
```

Extracts hostname, model (C8000V), IOS-XE version, uptime, last reload reason, memory, license status. Flags if uptime < 24h (recent reload) or last reload was a crash.

### Step 2: CPU Utilization

```
→ pyats_run_show_command: show processes cpu sorted
```

Reads 5-sec / 1-min / 5-min averages. Identifies top consumers (BGP I/O, OSPF Hello, SNMP ENGINE, IP Input). Applies thresholds:
- < 50% → HEALTHY
- 50-75% → WARNING
- 75-90% → HIGH
- \> 90% → CRITICAL

### Step 3: Memory Utilization

```
→ pyats_run_show_command: show processes memory sorted
```

Calculates used vs total percentage. Flags heavy consumers (BGP Router, CEF process, IOSD iomem). Thresholds:
- < 70% → HEALTHY
- 70-85% → WARNING
- 85-95% → HIGH
- \> 95% → CRITICAL

### Step 4: Interface Status

```
→ pyats_run_show_command: show ip interface brief
→ pyats_run_show_command: show interfaces
```

Reports per-interface: admin/protocol status, IP, speed/duplex, input/output rates, error counters (CRC, drops, overruns, resets). Flags any interface that is up/down, has incrementing CRC errors, or is flapping.

### Step 5: Hardware & Environment

```
→ pyats_run_show_command: show inventory
→ pyats_run_show_command: show platform
```

Module status, serial numbers, transceiver types.

### Step 6: NTP Synchronization

```
→ pyats_run_show_command: show ntp associations
→ pyats_run_show_command: show clock
```

Checks for synchronized peer (`*` in output). Flags if no peer synced, offset > 100ms, or NTP not configured.

### Step 7: System Logs

```
→ pyats_show_logging
```

Scans for critical syslog patterns: `%SYS-2-MALLOCFAIL`, `%SYS-3-CPUHOG`, `%LINEPROTO-5-UPDOWN`, `%OSPF-*-ADJCHG`, `%BGP-*-ADJCHANGE`, `Traceback`, `%PLATFORM-*-CRASH`.

### Step 8: Connectivity

```
→ pyats_ping_from_network_device: ping 8.8.8.8 repeat 5
```

Measures success rate and RTT. 100% with < 50ms → HEALTHY.

## Example Output

```
Device: R1 (devnetsandboxiosxec8k.cisco.com)
Model: C8000V | IOS-XE: 17.9.4a | Uptime: 45d 12h

┌──────────────────┬──────────┬─────────────────────────┐
│ Check            │ Status   │ Details                 │
├──────────────────┼──────────┼─────────────────────────┤
│ CPU (5min avg)   │ HEALTHY  │ 8%                      │
│ Memory           │ HEALTHY  │ 42% used (1.1G/2.6G)   │
│ Interfaces       │ HEALTHY  │ 3/3 up/up               │
│ Hardware         │ HEALTHY  │ All modules OK          │
│ NTP              │ HEALTHY  │ Synced, offset 4ms      │
│ Logs             │ HEALTHY  │ No critical events      │
│ Connectivity     │ HEALTHY  │ 100% to 8.8.8.8, 18ms  │
└──────────────────┴──────────┴─────────────────────────┘

Overall: HEALTHY — All checks passed
```

## Skills Used

- **pyats-health-check** (primary)
- **pyats-network** (underlying MCP tool calls)
