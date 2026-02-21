---
name: f5-health-check
description: "F5 BIG-IP health monitoring - virtual server status, pool member health, log analysis, performance statistics, and systematic health assessment"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["F5_MCP_SCRIPT", "MCP_CALL"] } } }
---

# F5 BIG-IP Health Check

Perform comprehensive health assessments on F5 BIG-IP appliances using the iControl REST API via MCP. This skill defines the systematic approach for evaluating BIG-IP health across virtual servers, pools, profiles, iRules, and system logs.

## When to Use

- Proactive daily/weekly BIG-IP health monitoring
- Pre-change and post-change validation for load balancer changes
- Incident response -- first thing to run when application delivery is impacted
- Capacity planning for virtual server and pool utilization
- Compliance checks for operational readiness of ADC infrastructure

## How to Call the Tools

The F5 MCP server provides 6 tools. Call them via mcp-call with the required environment variables:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" <tool_name> '{"param":"value"}'
```

### Available Tools

| Tool | Purpose | Key Arguments |
|------|---------|---------------|
| `list_tool` | List F5 objects by type | `object_name`, `object_type` (virtual/pool/irule/profile) |
| `show_stats_tool` | Show statistics for an F5 object | `object_name`, `object_type` (virtual/pool/irule/profile) |
| `show_logs_tool` | Show N lines of system logs | `lines_number` |
| `create_tool` | Create an F5 object via POST | `url_body`, `object_type` |
| `update_tool` | Update an F5 object via PATCH | `url_body`, `object_type`, `object_name` |
| `delete_tool` | Delete an F5 object | `object_type`, `object_name` |

## Health Check Procedure

Always run health checks in this exact order. Each section builds on the previous one.

### Step 1: Virtual Server Inventory and Status

List all virtual servers to establish the baseline inventory.

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"virtual"}'
```

**Extract and report:**
- Virtual server names and destination addresses (VIP:port)
- Enabled/disabled state
- Availability status (available, offline, unknown)
- Associated pool name
- IP protocol (TCP, UDP, any)
- Source address translation type (automap, SNAT pool, none)
- Assigned profiles (HTTP, SSL, TCP, persistence)

**Flags:**
- Virtual server status `offline` -> CRITICAL: VIP not serving traffic
- Virtual server status `unknown` -> WARNING: Cannot determine health
- Virtual server `disabled` -> INFO: Intentionally taken out of service (verify with change records)
- No pool assigned -> WARNING: Virtual server has no backend pool

### Step 2: Virtual Server Statistics (Per VIP)

For each virtual server discovered in Step 1, collect detailed statistics:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"my_virtual_server","object_type":"virtual"}'
```

**Key metrics to evaluate:**

| Metric | HEALTHY | WARNING | CRITICAL |
|--------|---------|---------|----------|
| Status availability | `available` | `unknown` | `offline` |
| Current connections | < 80% of connection limit | 80-95% of limit | > 95% of limit or at limit |
| Packets in/out | Non-zero, balanced ratio | Highly asymmetric (>100:1) | Zero in either direction |
| Bits in/out | Non-zero | Sudden drop >50% from baseline | Zero (no traffic flowing) |
| Total requests (HTTP VIPs) | Incrementing | Flat (stalled) | Decreasing or zero |
| Client-side connection rate | Steady or growing | Spike >200% baseline | Zero |

**Thresholds:**
- Current connections at 0 on a production VIP -> CRITICAL: No clients connecting
- Bits in = 0, bits out > 0 -> WARNING: VIP responding but no client data (possible health monitor traffic only)
- Connection limit reached -> CRITICAL: New clients being rejected (connection queue filling)
- 5xx response count incrementing -> WARNING: Backend servers returning errors

### Step 3: Pool Inventory and Member Health

List all pools and their members:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"pool"}'
```

**Extract and report for each pool:**
- Pool name and load balancing method (round-robin, least-connections, ratio, etc.)
- Monitor assignment (HTTP, HTTPS, TCP, ICMP, custom)
- Total members vs active members
- Each member: address:port, state (enabled/disabled), availability (available/offline/unknown)
- Minimum active members setting
- Action on service down (none, reject, drop, reselect)

**Flags:**
- All members `offline` -> CRITICAL: Pool is down, no healthy backends
- Members < minimum active threshold -> CRITICAL: Below minimum, failover action triggered
- Any single member `offline` -> WARNING: Reduced capacity
- > 50% members `offline` -> HIGH: Significant capacity degradation
- Member `disabled` but not `offline` -> INFO: Intentionally drained (verify with change records)
- No monitor assigned -> WARNING: Pool health is not being checked

### Step 4: Pool Statistics (Per Pool)

For each pool, collect statistics to assess utilization:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"my_pool","object_type":"pool"}'
```

**Key metrics to evaluate:**

| Metric | HEALTHY | WARNING | CRITICAL |
|--------|---------|---------|----------|
| Active member count | All members active | < 75% active | < 50% active or zero |
| Current connections per member | Evenly distributed | Skewed >3:1 ratio | Single member handling all traffic |
| Server-side connections | Incrementing | Flat | Zero |
| Total requests served | Incrementing | Flat | Decreasing |
| Bytes in/out | Balanced | Asymmetric | Zero |

**Connection distribution analysis:**
- Even distribution across members -> HEALTHY: Load balancing working correctly
- Uneven distribution with round-robin -> WARNING: Possible persistence override or health issue
- Single member with all connections -> CRITICAL: All other members likely down
- Zero connections on a member -> WARNING: Member may be failing health checks intermittently

### Step 5: Profile Inventory

List all profiles to document the configuration posture:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"profile"}'
```

**Check for:**
- SSL/TLS profiles: certificate expiration dates, cipher suite strength, TLS version minimums
- HTTP profiles: X-Forwarded-For insertion, response compression, request/response size limits
- TCP profiles: idle timeout values, Nagle algorithm setting, keep-alive intervals
- Persistence profiles: type (cookie, source-addr, SSL), timeout values
- OneConnect profiles: connection pooling settings

**Flags:**
- SSL cert expiring within 30 days -> WARNING: Plan renewal
- SSL cert expiring within 7 days -> CRITICAL: Immediate renewal required
- SSL cert expired -> CRITICAL: Service will fail for HTTPS clients
- TLS 1.0 or 1.1 enabled -> WARNING: Deprecated protocols, security risk
- Weak cipher suites (RC4, DES, 3DES, export ciphers) -> WARNING: Security vulnerability

### Step 6: iRule Inventory

List all iRules to document traffic manipulation logic:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"irule"}'
```

**Check for:**
- iRules assigned to virtual servers vs orphaned iRules
- iRule event types in use (HTTP_REQUEST, HTTP_RESPONSE, CLIENT_ACCEPTED, etc.)
- Deprecated Tcl commands or known-problematic patterns
- iRules performing logging (potential performance impact at scale)

**Flags:**
- iRule with `log` statements in high-traffic path -> WARNING: Performance impact
- iRule using `HTTP::collect` without `HTTP::release` -> CRITICAL: Memory leak risk
- Orphaned iRule (not assigned to any virtual server) -> INFO: Cleanup candidate
- iRule with `catch` blocks -> INFO: Error handling present (good practice)

### Step 7: System Logs Analysis

Pull recent system logs to detect errors and anomalies:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"200"}'
```

**Scan for these critical patterns:**

| Pattern | Severity | Meaning |
|---------|----------|---------|
| `01010028` | CRITICAL | No members available for pool |
| `01010029` | CRITICAL | Pool member monitor status down |
| `0107142f` | CRITICAL | SSL handshake failure |
| `01070417` | CRITICAL | HTTP parse error |
| `01060102` | HIGH | Connection rate limit reached |
| `01010025` | HIGH | Virtual server connection limit reached |
| `01071681` | WARNING | Pool member has been marked down |
| `01071682` | INFO | Pool member has been marked up |
| `01010240` | WARNING | Connection queue full |
| `0107143c` | WARNING | SSL certificate verification failure |
| `01070727` | WARNING | Pool member rate limit reached |
| `MCP error` | HIGH | Management plane communication issue |
| `disk_usage` | WARNING | Disk space issue on BIG-IP |
| `memory` | HIGH | Memory pressure on BIG-IP |
| `ha_status` | CRITICAL | High availability state change |
| `failover` | CRITICAL | HA failover event detected |

**Log analysis guidelines:**
- Group errors by type and count occurrences
- Note timestamps of first and last occurrence
- Identify trending errors (increasing frequency)
- Correlate pool member down events with specific health monitors
- Identify SSL errors that indicate certificate or cipher issues

### Step 8: Extended Log Analysis (If Issues Detected)

If Step 7 reveals errors, pull more log lines for deeper analysis:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"1000"}'
```

**Advanced log analysis:**
- Correlate timestamps: Did pool member down events coincide with traffic spikes?
- Check for flapping: Is a member repeatedly going up/down? (indicates marginal health)
- Identify blast radius: Which virtual servers were affected by pool member failures?
- Check HA events: Any failover or sync-related messages?

## Health Report Format

Always produce a summary table after completing all steps:

```
F5 BIG-IP Health Report
Device: $F5_IP_ADDRESS
Date: YYYY-MM-DD HH:MM UTC

+---------------------------+----------+------------------------------------------+
| Check                     | Status   | Details                                  |
+---------------------------+----------+------------------------------------------+
| Virtual Servers           | HEALTHY  | 5/5 available, all serving traffic       |
| Pool Health               | WARNING  | pool_web: 3/4 members active (node3 dn) |
| Connection Utilization    | HEALTHY  | Peak VIP at 45% connection limit         |
| Traffic Distribution      | HEALTHY  | Even distribution across pool members    |
| SSL/TLS Profiles          | WARNING  | www_ssl cert expires in 21 days          |
| iRules                    | HEALTHY  | 3 active, no problematic patterns        |
| System Logs               | HIGH     | 47x 01010029 (monitor down) in last hour |
+---------------------------+----------+------------------------------------------+

Overall: WARNING -- 2 items need attention

Action Items:
1. [WARNING] Investigate pool_web node3 health check failures
2. [WARNING] Renew SSL certificate for www_ssl profile (expires in 21 days)
3. [HIGH] Investigate spike in pool member monitor-down log messages
```

Severity order: CRITICAL > HIGH > WARNING > HEALTHY. Overall status = worst individual status.

## Fleet Health Check (Multiple BIG-IP Devices)

When monitoring multiple F5 appliances, run the full procedure on each device and produce a fleet summary:

```
+------------------+----------+----------+--------+--------+-----------+
| BIG-IP           | Virtuals | Pools    | SSL    | Logs   | Overall   |
+------------------+----------+----------+--------+--------+-----------+
| bigip-prod-01    | HEALTHY  | WARNING  | HEALTHY| HEALTHY| WARNING   |
| bigip-prod-02    | HEALTHY  | HEALTHY  | WARN   | HIGH   | HIGH      |
| bigip-dr-01      | HEALTHY  | HEALTHY  | HEALTHY| HEALTHY| HEALTHY   |
+------------------+----------+----------+--------+--------+-----------+
```

Sort devices by severity (CRITICAL first) for triage prioritization.

## Integration with Other Skills

- Use **f5-config-mgmt** to remediate issues found during health checks (e.g., update pool members, modify monitors)
- Use **f5-troubleshoot** for deep-dive investigation when health check reveals CRITICAL or HIGH findings
- Use **drawio-diagram** to visualize the BIG-IP topology (virtual servers -> pools -> members)
- Use **markmap-viz** to create hierarchical health status mind maps
- Use **servicenow-change-workflow** to create incidents for CRITICAL findings requiring remediation

## GAIT Audit Trail

After completing a health check, record the session in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"F5 BIG-IP health check on $F5_IP_ADDRESS","response":"Health check completed. Virtual servers: 5/5 HEALTHY. Pools: WARNING (pool_web 3/4 members). SSL: WARNING (cert expires 21 days). Logs: HIGH (47x monitor-down events). Overall: WARNING. Action items: investigate pool_web node3, renew SSL cert, investigate log spike.","artifacts":["f5-health-report.txt"]}'
```
