---
name: pyats-health-check
description: "Comprehensive network device health monitoring - CPU, memory, interfaces, hardware, NTP, logging, environment, and uptime analysis"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PYATS_TESTBED_PATH"] } } }
---

# Device Health Check

Perform comprehensive health assessments on network devices using pyATS. This skill defines the systematic approach for evaluating device health across all critical dimensions.

## When to Use

- Proactive daily/weekly health monitoring
- Pre-change and post-change validation
- Incident response — first thing you run when alerted
- Capacity planning and trending
- Compliance checks for operational readiness

## Health Check Procedure

Always run health checks in this exact order. Each section builds on the previous one.

### Step 1: Device Identity & Uptime

Run `show version` to establish baseline identity.

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show version"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Extract and report:**
- Hostname, model, serial number
- IOS-XE version and image filename
- Uptime (flag if < 24 hours — indicates recent reload)
- Last reload reason (flag if unexpected: crash, power failure)
- Total/available memory
- License status

**Thresholds:**
- Uptime < 24h → WARNING: Recent reload
- Uptime < 1h → CRITICAL: Very recent reload, check for crash
- Last reload reason contains "crash" or "error" → CRITICAL

### Step 2: CPU Utilization

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show processes cpu sorted"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Thresholds (5-second / 1-minute / 5-minute averages):**
- < 50% → HEALTHY
- 50-75% → WARNING: Elevated CPU
- 75-90% → HIGH: Investigate top processes
- > 90% → CRITICAL: Immediate investigation required

**Top processes to watch:**
- `IP Input` — high traffic volume or routing loops
- `BGP Router` / `BGP I/O` — large BGP table or instability
- `OSPF-1 Hello` — OSPF adjacency issues
- `Crypto IKMP` / `Crypto Engine` — IPsec overhead
- `SNMP ENGINE` — polling storm
- `ARP Input` — ARP storm or L2 loop

### Step 3: Memory Utilization

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show processes memory sorted"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

Also run:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show platform resources"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Thresholds:**
- Used < 70% → HEALTHY
- 70-85% → WARNING: Memory pressure
- 85-95% → HIGH: May impact routing table updates
- > 95% → CRITICAL: Risk of process crashes or OOM

**Memory consumers to watch:**
- `BGP Router` — large BGP table (full internet table = ~1M routes)
- `CEF process` — large FIB
- `OSPF Router` — large OSPF LSDB
- `HTTP CORE` — web server / RESTCONF overhead
- `IOSD iomem` — I/O memory for packet buffers

### Step 4: Interface Status

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ip interface brief"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

Then for each active interface, get detailed counters:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show interfaces"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Report for each interface:**
- Admin status (up/down) and protocol status (up/down)
- IP address and subnet
- Speed, duplex, MTU
- Input/output rate (bps and pps)
- Error counters: CRC, input errors, output errors, drops, overruns
- Resets counter (flag if incrementing — indicates flapping)
- Last input/output timestamps

**Flags:**
- Interface up/down → WARNING: Check physical or protocol
- CRC errors > 0 → WARNING: Physical layer issue (cabling, optics, duplex mismatch)
- Input errors incrementing → WARNING: Packet corruption
- Output drops > 0 → WARNING: Congestion or QoS issue
- Resets incrementing → CRITICAL: Interface flapping
- Line protocol down on configured interface → CRITICAL

### Step 5: Hardware & Environment

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show inventory"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show platform"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Report:** Module status (ok/fail), serial numbers, PID, transceiver types and DOM readings.

### Step 6: NTP Synchronization

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show ntp associations"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_run_show_command","arguments":{"device_name":"R1","command":"show clock"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Flags:**
- No NTP peer synchronized (no `*` in associations) → CRITICAL for logging/forensics
- Clock offset > 100ms → WARNING
- Clock offset > 1s → CRITICAL
- No NTP configured at all → CRITICAL

### Step 7: System Logs

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_show_logging","arguments":{"device_name":"R1"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Scan for these patterns:**
- `%SYS-*-RELOAD` — reload events
- `%LINEPROTO-5-UPDOWN` — interface flaps
- `%OSPF-*-ADJCHG` — OSPF adjacency changes
- `%BGP-*-ADJCHANGE` — BGP peer state changes
- `%DUAL-*-NBRCHANGE` — EIGRP neighbor changes
- `%SYS-2-MALLOCFAIL` — memory allocation failure (CRITICAL)
- `%SYS-3-CPUHOG` — process monopolizing CPU (HIGH)
- `%TRACKING-*` — IP SLA or object tracking changes
- `%SEC-*` / `%AUTHMGR-*` — security events
- `%PLATFORM-*-CRASH` — crash events (CRITICAL)
- `Traceback` — software bug (CRITICAL — open TAC case)

### Step 8: Connectivity Validation

Test reachability to critical infrastructure:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"pyats_ping_from_network_device","arguments":{"device_name":"R1","command":"ping 8.8.8.8 repeat 5"}}}' | PYATS_TESTBED_PATH=$PYATS_TESTBED_PATH python3 -u $PYATS_MCP_SCRIPT --oneshot
```

**Thresholds:**
- 100% success, RTT < 50ms → HEALTHY
- 100% success, RTT > 100ms → WARNING: High latency
- 80-99% success → WARNING: Packet loss
- < 80% success → CRITICAL: Significant packet loss
- 0% success → CRITICAL: No reachability

## Health Report Format

Always produce a summary table:

```
Device: R1 (devnetsandboxiosxec8k.cisco.com)
Model: C8000V | IOS-XE: 17.x.x | Uptime: XXd XXh

┌──────────────────┬──────────┬─────────────────────────┐
│ Check            │ Status   │ Details                 │
├──────────────────┼──────────┼─────────────────────────┤
│ CPU (5min avg)   │ HEALTHY  │ 12%                     │
│ Memory           │ HEALTHY  │ 45% used (1.2G/2.6G)   │
│ Interfaces       │ WARNING  │ Gi2 down/down           │
│ Hardware         │ HEALTHY  │ All modules OK          │
│ NTP              │ HEALTHY  │ Synced, offset 2ms      │
│ Logs             │ WARNING  │ 3 OSPF adjacency flaps  │
│ Connectivity     │ HEALTHY  │ 100% to 8.8.8.8, 23ms  │
└──────────────────┴──────────┴─────────────────────────┘

Overall: WARNING — 2 items need attention
```

Severity order: CRITICAL > HIGH > WARNING > HEALTHY. Overall status = worst individual status.
