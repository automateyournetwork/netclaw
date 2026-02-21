---
name: f5-troubleshoot
description: "F5 BIG-IP troubleshooting - virtual server failures, pool member health, connection issues, SSL/TLS problems, iRule errors, persistence issues, and performance degradation using structured methodology"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["F5_MCP_SCRIPT", "MCP_CALL"] } } }
---

# F5 BIG-IP Troubleshooting

Structured troubleshooting methodology for F5 BIG-IP issues. Follow a systematic approach: gather facts from multiple data sources, correlate symptoms, identify root cause, remediate, and verify.

## Troubleshooting Principles

1. **Define the problem** -- What exactly is broken? Who reported it? What is the expected vs actual behavior?
2. **Gather facts** -- List objects, check stats, read logs. Never assume.
3. **Consider possibilities** -- Based on facts, list likely root causes
4. **Create action plan** -- Test one variable at a time
5. **Implement and verify** -- Make one change, verify, document
6. **Document** -- Record what was found and what fixed it

## How to Call the Tools

The F5 MCP server provides 6 tools. Call them via mcp-call with the required environment variables:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" <tool_name> '{"param":"value"}'
```

### Available Tools for Troubleshooting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `list_tool` | List and inspect object configuration | Verify config is correct |
| `show_stats_tool` | Show live statistics and counters | Identify traffic flow issues |
| `show_logs_tool` | Show system logs | Find errors and event correlation |
| `update_tool` | Modify object configuration | Apply fixes |
| `create_tool` | Create new objects | Add missing objects |
| `delete_tool` | Remove objects | Remove problematic objects |

---

## Symptom: "Virtual Server Not Responding to Clients"

Clients report they cannot connect to the application VIP.

### Step 1: Verify Virtual Server Exists and Is Enabled

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

**Check:**
- Does the virtual server exist? If not, it was deleted or never created.
- Is it `enabled: true`? If disabled, someone took it out of service.
- Is the `destination` (VIP:port) correct?
- Is a `pool` assigned?
- Is `sourceAddressTranslation` configured? (Without SNAT/automap, return traffic may bypass the BIG-IP.)

**Decision tree:**
- VS does not exist -> Recreate it (use f5-config-mgmt skill)
- VS is disabled -> Re-enable: `update_tool` with `{"enabled":true}`
- VS has no pool -> Assign pool: `update_tool` with `{"pool":"pool_name"}`
- VS has no SNAT -> Check if servers have BIG-IP as default gateway; if not, add automap

### Step 2: Check Virtual Server Statistics

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

**Analyze:**

| Metric | Healthy Indicator | Problem Indicator |
|--------|-------------------|-------------------|
| Status availability | `available` | `offline` or `unknown` |
| Current connections | > 0 during business hours | 0 on production VIP |
| Total connections | Incrementing | Flat or zero |
| Client-side bits in | > 0 | Zero (no client traffic arriving) |
| Server-side bits out | > 0 | Zero (no traffic reaching backend) |
| Client bits in, server bits out = 0 | - | VIP not processing traffic at all |
| Client bits in > 0, server bits out = 0 | - | Traffic arriving but not forwarded to pool |

**If status is `offline`:**
The virtual server is marked down because the associated pool has no available members. Proceed to Step 3.

**If current connections = 0 but status is `available`:**
The VIP is healthy but no clients are connecting. The issue is upstream of the BIG-IP:
- DNS not resolving to the VIP address
- Firewall blocking traffic to the VIP
- Client network routing issue
- VIP is on wrong VLAN/subnet

### Step 3: Check the Associated Pool

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

**Check:**
- Are any members `available`? If all members are `offline`, the pool is down.
- What monitor is assigned? Is it appropriate for the service?
- Are members `enabled` or `disabled`? Disabled members were intentionally drained.
- What is the member-to-connection distribution? Is one member handling all traffic?

**If all members are offline -> Go to "Pool Member Marked Down" section below.**

### Step 4: Check Logs for Errors

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"200"}'
```

**Scan for:**
- `01010028` -- No members available in pool (confirms pool down)
- `01010025` -- Connection limit reached on virtual server
- `0107142f` -- SSL handshake failure
- `01070417` -- HTTP parse error
- `01010240` -- Connection queue full
- Timestamps correlating with the reported outage

### Step 5: Check Profiles and iRules

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"profile"}'
```

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"irule"}'
```

**Check:**
- Is the correct SSL profile assigned for HTTPS virtual servers?
- Is the HTTP profile assigned when HTTP inspection is needed?
- Are any iRules rejecting or redirecting traffic incorrectly?
- Is a persistence profile causing traffic to stick to a down member?

---

## Symptom: "Pool Member Marked Down"

Health monitor is marking one or more pool members as offline.

### Step 1: Identify Which Members Are Down

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

**Record:** Which members are `offline`, which are `available`, which are `disabled`.

### Step 2: Check Pool Statistics for the Down Member

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

**Analyze:**
- When did the member go down? (Check stats timestamps)
- Was there a gradual decline or sudden failure?
- Are connections draining from the down member?

### Step 3: Check Logs for Monitor Failure Details

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"500"}'
```

**Scan for these patterns:**

| Log Message | Meaning | Common Cause |
|-------------|---------|--------------|
| `01071681` Pool member ... monitor status down | Health check failed | Server not responding |
| `01071682` Pool member ... monitor status up | Health check recovered | Server came back |
| `01010028` No members available | All members down | Total pool failure |
| `FQDN ... cannot be resolved` | DNS resolution failure | DNS issue for FQDN pool members |
| `monitor ... instance ... timed out` | Monitor timeout | Server too slow or unreachable |

**Common root causes for pool member down:**

1. **Server is actually down** -- The application crashed, the OS is down, or the server was rebooted
2. **Network path issue** -- Firewall between BIG-IP and server blocking health check traffic, or routing issue on server VLAN
3. **Monitor mismatch** -- HTTP monitor expecting 200 but application returns 301/302 redirect
4. **Monitor URI wrong** -- Health check URI returns 404 because the page does not exist
5. **Port mismatch** -- Monitor checking wrong port (e.g., monitor on 80 but server on 8080)
6. **SSL mismatch** -- HTTP monitor used but server requires HTTPS (or vice versa)
7. **Response timeout** -- Server responds but too slowly for the monitor interval/timeout
8. **Receive string mismatch** -- Monitor expects specific string in response that changed after app deployment
9. **Source IP issue** -- Server firewall blocking the BIG-IP self-IP used for health checks

### Step 4: Verify Monitor Configuration

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

From the pool config, identify the monitor name and verify:
- **Type:** HTTP, HTTPS, TCP, ICMP, or custom
- **Interval/timeout:** Is the timeout shorter than the interval? (Must be: timeout < interval * 3+1 for 3 failures)
- **Send string:** What request is sent? (e.g., `GET /health HTTP/1.1\r\nHost: app.example.com\r\n\r\n`)
- **Receive string:** What response is expected? (e.g., `200 OK` or `healthy`)
- **Destination:** Is it `*:*` (use member address:port) or a specific IP:port?

### Step 5: Remediation

**If the server is healthy but the monitor is wrong, fix the monitor:**

Update the pool with a correct monitor:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"monitor":"tcp"},"object_type":"pool","object_name":"pool_webapp"}'
```

**If a member needs to be temporarily removed (graceful drain):**

Update the pool without the problematic member:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"members":["10.1.1.10:80","10.1.1.11:80"]},"object_type":"pool","object_name":"pool_webapp"}'
```

**WARNING:** This removes the member entirely. Existing connections will be terminated. For graceful drain, disable the member instead if the API supports it.

**If a replacement member needs to be added:**

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"members":["10.1.1.10:80","10.1.1.11:80","10.1.1.14:80"]},"object_type":"pool","object_name":"pool_webapp"}'
```

---

## Symptom: "Connection Limits / Persistence Issues"

Users report intermittent connectivity, session drops, or being load-balanced to a different server mid-session.

### Step 1: Check Virtual Server Connection Statistics

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

**Check for connection limit issues:**
- Is `connectionLimit` set and being reached?
- Are `clientsideCurConns` near the limit?
- Is the connection queue filling up? (Check logs for `01010240`)

**If connection limit is being hit:**

Either increase the limit or scale out with additional pool members:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"connectionLimit":0},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

Setting `connectionLimit` to `0` removes the limit entirely.

### Step 2: Check Persistence Configuration

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

**Persistence troubleshooting:**

| Issue | Symptom | Resolution |
|-------|---------|------------|
| No persistence configured | Users lose session on every request | Add cookie or source-addr persistence |
| Source-addr persistence with SNAT | All users from same SNAT IP go to same member | Switch to cookie persistence |
| Cookie persistence but app on HTTP | Persistence cookie not inserted | Ensure HTTP profile is assigned |
| Persistence timeout too short | Users lose session during idle | Increase persistence timeout |
| Persistence timeout too long | Sessions stick to drained member | Lower timeout or use cookie |
| Fallback persistence not set | When primary persistence fails, connections randomize | Set fallback persistence |

### Step 3: Check Pool Member Connection Distribution

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

**If one member has vastly more connections than others:**
- Persistence is sticking too many sessions to one member
- Consider changing from source-address to cookie persistence
- Consider changing load balancing method from round-robin to least-connections

### Step 4: Check Logs for Connection Errors

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"300"}'
```

**Scan for:**
- `01010025` -- Connection limit reached
- `01010240` -- Connection queue full
- `01060102` -- Rate limit reached
- `TCL error` -- iRule causing connection drops
- `reset cause` -- Connection resets (RST) from server or BIG-IP

---

## Symptom: "SSL/TLS Certificate Problems"

Users see certificate warnings, SSL handshake failures, or HTTPS connections fail entirely.

### Step 1: Check SSL Profile Configuration

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"profile"}'
```

**Check the SSL client profile assigned to the virtual server:**
- Is a client SSL profile assigned? (Required for HTTPS VIPs)
- Which certificate and key are referenced?
- What TLS versions are enabled? (TLS 1.2 and 1.3 should be enabled; TLS 1.0 and 1.1 should be disabled)
- What cipher suites are configured?

**Common SSL issues:**

| Issue | Symptom | Log Pattern |
|-------|---------|-------------|
| Expired certificate | Browser shows "Not Secure" | `0107142f` SSL handshake failed |
| Wrong certificate (hostname mismatch) | Browser shows certificate warning | Client disconnects after handshake |
| Missing intermediate CA | Works in some browsers, fails in others | `0107143c` certificate verification failed |
| Weak cipher suite only | Modern browsers refuse to connect | `0107142f` with no common cipher |
| TLS version mismatch | Client can't negotiate | `0107142f` protocol version |
| Client cert required but not sent | Connection refused | `01071065` peer did not return certificate |
| SNI misconfiguration | Wrong cert served for hostname | Client sees cert for different domain |

### Step 2: Check Virtual Server for SSL Profile

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

Verify the correct SSL profile is assigned in the `profiles` list with `context: clientside`.

### Step 3: Check Logs for SSL Errors

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"300"}'
```

**Key SSL log messages:**

| Log Code | Meaning | Action |
|----------|---------|--------|
| `0107142f` | SSL handshake failure | Check cipher/version/cert compatibility |
| `0107143c` | Certificate verification failure | Check cert chain completeness |
| `01071065` | Peer certificate missing | Client cert auth configured but client has no cert |
| `01070417` | HTTP request on HTTPS port | Client sending plain HTTP to SSL VIP |
| `SSL routines:ssl3_read_bytes:sslv3 alert` | SSL alert received from peer | Version/cipher mismatch |

### Step 4: Remediation

**Update SSL profile ciphers to modern standards:**

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"ciphers":"TLSv1.2:TLSv1.3:!SSLv3:!RC4:!3DES:!EXPORT"},"object_type":"profile","object_name":"clientssl_webapp"}'
```

**Assign the correct SSL profile to a virtual server:**

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"profiles":[{"name":"clientssl_webapp","context":"clientside"},{"name":"http"},{"name":"tcp-wan-optimized","context":"clientside"},{"name":"tcp-lan-optimized","context":"serverside"}]},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

**WARNING:** The profiles list is a full replacement. Include ALL desired profiles.

---

## Symptom: "iRule Errors in Logs"

Logs show TCL errors or iRule-related failures.

### Step 1: Pull Recent Logs

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"500"}'
```

**Scan for iRule error patterns:**

| Pattern | Meaning | Common Cause |
|---------|---------|--------------|
| `TCL error` | Tcl script runtime error | Syntax error, undefined variable, missing command |
| `can't read "variable"` | Variable not defined | Variable used before assignment or in wrong event |
| `command not found` | Invalid Tcl or iRule command | Typo or deprecated command |
| `HTTP::collect` without `HTTP::release` | Payload collection started but never released | Missing release in all code paths (memory leak) |
| `invalid command name "pool"` | Pool command in wrong event | `pool` used outside HTTP_REQUEST event |
| `too many re-entering calls` | Recursive iRule invocation | iRule triggering itself |
| `exceeded CPU time limit` | iRule taking too long | Complex regex or infinite loop |
| `abort` | iRule explicitly aborted | Error condition in catch block |

### Step 2: Identify the Problematic iRule

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"irule"}'
```

Cross-reference the iRule name from the log error with the iRule inventory. Check which virtual servers have this iRule assigned.

### Step 3: Review iRule Content

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"problematic_irule","object_type":"irule"}'
```

**Common iRule bugs to check for:**
- Variables used across events without being set in all code paths
- `HTTP::collect` without corresponding `HTTP::release` in all branches
- Missing `default` case in `switch` statements
- Regex patterns that can cause catastrophic backtracking
- `log` statements in high-traffic events (performance issue, not error)
- String operations on binary data
- Missing error handling (`catch`) around operations that can fail

### Step 4: Fix the iRule

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"apiAnonymous":"when HTTP_REQUEST {\n  catch {\n    switch -glob [string tolower [HTTP::uri]] {\n      \"/api/*\" { pool pool_api_backend }\n      default { pool pool_webapp }\n    }\n  } err {\n    log local0. \"iRule error: $err\"\n    pool pool_webapp\n  }\n}"},"object_type":"irule","object_name":"uri_routing"}'
```

**Alternatively, if the iRule is causing critical failures, remove it from the virtual server immediately:**

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"rules":[]},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

This removes all iRules from the virtual server. Traffic will flow to the default pool without any iRule processing. Fix the iRule, then re-attach it.

---

## Symptom: "Performance Degradation"

Application is slow, high latency, or throughput has dropped.

### Step 1: Check Virtual Server Statistics

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

**Look for:**
- Connection count near the limit -> Bottleneck at the VIP
- High bits/sec relative to interface capacity -> Bandwidth saturation
- Connection rate spike -> Possible DDoS or legitimate traffic surge
- Asymmetric traffic (high client-side, low server-side) -> Backend not keeping up

### Step 2: Check Pool Member Distribution

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

**Look for:**
- Uneven connection distribution -> Some members overloaded, others idle
- Single member with most connections -> Persistence issue or members down
- All members at high connection count -> Need more backend capacity
- High server-side connection time -> Backend application slow

**If distribution is uneven, consider changing load balancing:**

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"loadBalancingMode":"least-connections-member"},"object_type":"pool","object_name":"pool_webapp"}'
```

### Step 3: Check for Pool Members Down (Reduced Capacity)

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

If members are down, the remaining members are handling more traffic than designed. This is the most common cause of "slow application" reports -- not a BIG-IP issue but a capacity issue.

### Step 4: Check System Logs for Errors

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"500"}'
```

**Performance-related log patterns:**

| Pattern | Meaning | Action |
|---------|---------|--------|
| `01010025` | Connection limit reached | Increase limit or add capacity |
| `01010240` | Connection queue full | Increase queue depth or backend capacity |
| `01060102` | Rate limit reached | Review rate limiting config |
| `01070727` | Pool member rate limit | Member receiving too much traffic |
| `memory` | BIG-IP memory pressure | Check for memory leaks, iRule issues |
| `disk_usage` | BIG-IP disk pressure | Check for log rotation issues |
| `tmm_semaphore` | TMM (Traffic Management Microkernel) contention | BIG-IP itself is overloaded |
| `aggressive_mode` | Memory aggressive mode enabled | BIG-IP is under severe memory pressure |

### Step 5: Check iRules for Performance Impact

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"irule"}'
```

**iRule performance killers:**
- `log` statements on every request -> Disk I/O bottleneck
- Complex regex matching -> CPU overhead
- `HTTP::collect` large payloads -> Memory consumption
- `DNS::lookup` in data path -> Blocking operation, adds latency
- Multiple iRules with same events -> Event processing overhead
- `persist uie` with large strings -> Persistence table bloat

### Step 6: Scale Out (If Root Cause Is Capacity)

If the root cause is insufficient backend capacity, add more pool members:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"members":["10.1.1.10:80","10.1.1.11:80","10.1.1.12:80","10.1.1.13:80","10.1.1.14:80"]},"object_type":"pool","object_name":"pool_webapp"}'
```

**WARNING:** Members list is a full replacement. Include ALL desired members (existing + new).

---

## Symptom: "HA Failover or Sync Issues"

Logs indicate high-availability state changes, failover events, or configuration sync failures.

### Step 1: Check System Logs for HA Events

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"500"}'
```

**HA-related log patterns:**

| Pattern | Severity | Meaning |
|---------|----------|---------|
| `ha_status` active -> standby | CRITICAL | This unit has gone standby -- failover occurred |
| `ha_status` standby -> active | CRITICAL | This unit has become active -- peer failed |
| `failover` | CRITICAL | Failover event in progress |
| `config_sync` failed | HIGH | Configuration not synchronizing between peers |
| `device_trust` | HIGH | Device trust certificate issue |
| `heartbeat` lost | CRITICAL | HA heartbeat lost -- peer may be down |
| `network_failover` | CRITICAL | Network-based failover triggered |

### Step 2: Verify Object State After Failover

After any failover event, immediately verify all virtual servers and pools:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"virtual"}'
```

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"pool"}'
```

Confirm all virtual servers are available and all pool members are healthy on the now-active unit.

---

## Common F5 Error Code Quick Reference

| Code | Severity | Meaning | First Action |
|------|----------|---------|--------------|
| `01010025` | HIGH | VS connection limit reached | Check stats, increase limit |
| `01010028` | CRITICAL | No pool members available | Check pool health |
| `01010029` | CRITICAL | Pool member monitor down | Check member + monitor |
| `01010240` | HIGH | Connection queue full | Check capacity |
| `01060102` | HIGH | Rate limit reached | Review rate config |
| `0107142f` | CRITICAL | SSL handshake failure | Check cert + ciphers |
| `01070417` | HIGH | HTTP parse error | Check client requests |
| `0107143c` | WARNING | Cert verification fail | Check cert chain |
| `01071681` | WARNING | Pool member marked down | Check member health |
| `01071682` | INFO | Pool member marked up | Recovery event |
| `01070727` | WARNING | Member rate limit | Check distribution |
| `TCL error` | HIGH | iRule error | Check iRule code |

---

## Troubleshooting Decision Flowchart

```
Client reports application down
|
+-> Check VIP status (list_tool + show_stats_tool virtual)
    |
    +-> VIP offline?
    |   +-> Check pool (list_tool + show_stats_tool pool)
    |       +-> All members down? -> Check servers + monitors
    |       +-> Some members down? -> Reduced capacity, check remaining
    |       +-> No pool assigned? -> Assign pool (update_tool)
    |
    +-> VIP available but 0 connections?
    |   +-> DNS, firewall, or routing issue upstream of BIG-IP
    |
    +-> VIP available, connections present, but errors?
        +-> Check logs (show_logs_tool)
        +-> SSL errors? -> Check profiles + certs
        +-> HTTP errors? -> Check iRules + backend health
        +-> Connection limits? -> Scale out or increase limits
```

---

## Integration with Other Skills

| Skill | Integration Point |
|-------|------------------|
| **f5-health-check** | Run health check first to scope the problem |
| **f5-config-mgmt** | Apply fixes using proper change workflow |
| **servicenow-change-workflow** | Create incident tickets for CRITICAL findings |
| **drawio-diagram** | Visualize traffic flow for complex troubleshooting |
| **markmap-viz** | Create troubleshooting decision trees |

## GAIT Audit Trail

After completing a troubleshooting session, record findings and resolution in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"F5 troubleshoot: vs_webapp_https not responding to clients","response":"Investigation: VIP status offline due to pool_webapp all members down. Root cause: HTTP health monitor expecting 200 but app returning 301 redirect after deployment. Fix: updated monitor receive string to accept 301. Verification: all 3 pool members now available, VIP status available, client connections incrementing. Logs clear of 01010028 errors.","artifacts":["f5-troubleshoot-report.txt"]}'
```
