---
name: f5-config-mgmt
description: "F5 BIG-IP configuration management - safe change workflow with baseline capture, planning, creation/update/deletion of virtual servers, pools, iRules, and profiles with full verification"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["F5_MCP_SCRIPT", "MCP_CALL"] } } }
---

# F5 BIG-IP Configuration Management

Structured change management workflows for F5 BIG-IP configuration changes via the iControl REST API. Every change follows: Baseline -> Plan -> Apply -> Verify -> Document.

## Golden Rule

**NEVER apply configuration without first capturing a baseline.** If the change goes wrong, you need to know what to restore.

## How to Call the Tools

The F5 MCP server provides 6 tools. Call them via mcp-call with the required environment variables:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" <tool_name> '{"param":"value"}'
```

### Available Tools

| Tool | Purpose | HTTP Method | Key Arguments |
|------|---------|-------------|---------------|
| `list_tool` | List F5 objects | GET | `object_name`, `object_type` |
| `show_stats_tool` | Show object statistics | GET | `object_name`, `object_type` |
| `show_logs_tool` | Show system logs | GET | `lines_number` |
| `create_tool` | Create objects | POST | `url_body`, `object_type` |
| `update_tool` | Update objects | PATCH | `url_body`, `object_type`, `object_name` |
| `delete_tool` | Delete objects | DELETE | `object_type`, `object_name` |

Object types: `virtual`, `pool`, `irule`, `profile`

---

## Change Workflow

### Phase 1: Pre-Change Baseline

Capture the current state of everything the change might affect. This is the rollback reference.

#### 1A: Capture Virtual Server State

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"virtual"}'
```

Store the full list of virtual servers, their configurations, pool assignments, and profiles.

#### 1B: Capture Pool State

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"pool"}'
```

Store pool configurations, member lists, monitor assignments, and load balancing methods.

#### 1C: Capture Statistics Baseline

For each affected object, capture current stats to compare post-change:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"my_virtual_server","object_type":"virtual"}'
```

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"my_pool","object_type":"pool"}'
```

#### 1D: Capture Log Baseline

Record the last 50 lines of logs to establish a timestamp reference:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"50"}'
```

Note the most recent log timestamp -- any errors after this timestamp are change-related.

#### 1E: Capture iRule and Profile State (if affected)

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"irule"}'
```

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"","object_type":"profile"}'
```

### Phase 2: Plan the Change

Before applying any configuration, explicitly state:

1. **What** objects will be created, updated, or deleted
2. **Why** the change is needed (business justification)
3. **Expected effect** on traffic flow and application delivery
4. **Risk assessment** -- what could go wrong
5. **Verification criteria** -- how to confirm success
6. **Rollback plan** -- exact steps to undo the change

### Phase 3: Apply Configuration

#### Creating Objects

Use `create_tool` to create new objects via POST. The `url_body` dict contains the iControl REST API body.

#### Example: Create a Pool with Members

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"pool_webapp","monitor":"http","loadBalancingMode":"round-robin","members":["10.1.1.10:80","10.1.1.11:80","10.1.1.12:80"]},"object_type":"pool"}'
```

**Pool creation best practices:**
- Always assign a health monitor (`http`, `https`, `tcp`, `icmp`, or a custom monitor)
- Choose the appropriate load balancing method:
  - `round-robin` -- default, equal distribution
  - `least-connections-member` -- best for unequal server capacity or variable request duration
  - `ratio-member` -- weighted distribution for heterogeneous backends
  - `fastest-node` -- route to fastest responding server
- Specify the `serviceDownAction` for graceful failure handling:
  - `none` -- connections persist on down member until timeout
  - `reset` -- RST sent to clients
  - `reselect` -- reselect a new member (recommended for HTTP)
  - `drop` -- silently drop connections
- Set `minActiveMembers` to trigger action when too many members fail
- Include `description` for documentation

#### Example: Create a Pool with Advanced Options

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"pool_api_backend","monitor":"https_443","loadBalancingMode":"least-connections-member","minActiveMembers":2,"serviceDownAction":"reselect","slowRampTime":300,"description":"API backend pool - managed by NetClaw","members":["10.2.1.20:443","10.2.1.21:443","10.2.1.22:443","10.2.1.23:443"]},"object_type":"pool"}'
```

#### Example: Create a Virtual Server

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"vs_webapp_https","destination":"10.100.1.50:443","ipProtocol":"tcp","pool":"pool_webapp","sourceAddressTranslation":{"type":"automap"},"profiles":[{"name":"clientssl"},{"name":"http"},{"name":"tcp-wan-optimized","context":"clientside"},{"name":"tcp-lan-optimized","context":"serverside"}],"description":"HTTPS virtual server for webapp - managed by NetClaw"},"object_type":"virtual"}'
```

**Virtual server creation best practices:**
- Always specify `destination` as VIP_IP:port
- Always assign `sourceAddressTranslation` (automap or SNAT pool) unless servers have BIG-IP as default gateway
- Assign appropriate profiles:
  - Client SSL profile for HTTPS termination
  - HTTP profile for HTTP inspection, compression, X-Forwarded-For
  - TCP profiles: `tcp-wan-optimized` on clientside, `tcp-lan-optimized` on serverside
  - Persistence profile if session affinity is required
- Set `pool` to the backend pool name
- Include `description` for documentation
- Consider `connectionLimit` to protect backend servers

#### Example: Create an HTTP Virtual Server (Non-SSL)

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"vs_webapp_http","destination":"10.100.1.50:80","ipProtocol":"tcp","pool":"pool_webapp","sourceAddressTranslation":{"type":"automap"},"profiles":[{"name":"http"},{"name":"tcp-wan-optimized","context":"clientside"},{"name":"tcp-lan-optimized","context":"serverside"}],"description":"HTTP virtual server for webapp - managed by NetClaw"},"object_type":"virtual"}'
```

#### Example: Create an HTTP-to-HTTPS Redirect Virtual Server

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"vs_webapp_redirect","destination":"10.100.1.50:80","ipProtocol":"tcp","profiles":[{"name":"http"}],"rules":["/Common/redirect_to_https"],"description":"HTTP-to-HTTPS redirect - managed by NetClaw"},"object_type":"virtual"}'
```

#### Example: Create an iRule

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"redirect_to_https","apiAnonymous":"when HTTP_REQUEST {\n  HTTP::redirect https://[HTTP::host][HTTP::uri]\n}"},"object_type":"irule"}'
```

**iRule creation best practices:**
- Keep iRules as simple as possible -- complexity degrades performance
- Avoid `log` statements in production iRules on high-traffic virtual servers
- Always pair `HTTP::collect` with `HTTP::release` to prevent memory leaks
- Use `catch` blocks for error handling in complex iRules
- Test iRule syntax before deploying (syntax errors can prevent virtual server from starting)

#### Example: HTTP Header Insertion iRule

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"insert_headers","apiAnonymous":"when HTTP_REQUEST {\n  HTTP::header insert X-Forwarded-Proto https\n  HTTP::header insert X-Real-IP [IP::client_addr]\n}\nwhen HTTP_RESPONSE {\n  HTTP::header insert Strict-Transport-Security \"max-age=31536000; includeSubDomains\"\n}"},"object_type":"irule"}'
```

#### Example: Maintenance Page iRule

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"maintenance_page","apiAnonymous":"when HTTP_REQUEST {\n  HTTP::respond 503 content \"<html><body><h1>Service Temporarily Unavailable</h1><p>We are performing scheduled maintenance. Please try again later.</p></body></html>\" Content-Type \"text/html\"\n}"},"object_type":"irule"}'
```

#### Example: URI-Based Pool Selection iRule

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"uri_routing","apiAnonymous":"when HTTP_REQUEST {\n  switch -glob [string tolower [HTTP::uri]] {\n    \"/api/*\" { pool pool_api_backend }\n    \"/static/*\" { pool pool_static_content }\n    default { pool pool_webapp }\n  }\n}"},"object_type":"irule"}'
```

#### Updating Objects

Use `update_tool` to modify existing objects via PATCH. Only include the fields you want to change.

#### Example: Update Pool Members (Add a Member)

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"members":["10.1.1.10:80","10.1.1.11:80","10.1.1.12:80","10.1.1.13:80"]},"object_type":"pool","object_name":"pool_webapp"}'
```

**WARNING:** The members list in an update is a full replacement, not an append. Always include ALL desired members (existing + new) in the list. Omitting existing members will remove them.

#### Example: Update Pool Load Balancing Method

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"loadBalancingMode":"least-connections-member"},"object_type":"pool","object_name":"pool_webapp"}'
```

#### Example: Update Pool Monitor

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"monitor":"https_443"},"object_type":"pool","object_name":"pool_api_backend"}'
```

#### Example: Update Virtual Server Pool Assignment

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"pool":"pool_webapp_v2"},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

#### Example: Add iRule to Virtual Server

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"rules":["/Common/redirect_to_https","/Common/insert_headers"]},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

**WARNING:** The rules list in an update is a full replacement. Include ALL desired iRules in the list.

#### Example: Disable a Virtual Server (Maintenance)

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"enabled":false},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

#### Example: Re-enable a Virtual Server

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"enabled":true},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

#### Deleting Objects

Use `delete_tool` to remove objects. **Always verify no dependencies exist before deletion.**

#### Example: Delete a Pool

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" delete_tool '{"object_type":"pool","object_name":"pool_old_webapp"}'
```

**CRITICAL:** You cannot delete a pool that is still assigned to a virtual server. Remove the pool reference from the virtual server first, or reassign to a different pool.

#### Example: Delete a Virtual Server

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" delete_tool '{"object_type":"virtual","object_name":"vs_old_webapp"}'
```

#### Example: Delete an iRule

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" delete_tool '{"object_type":"irule","object_name":"old_redirect_rule"}'
```

**CRITICAL:** You cannot delete an iRule that is still assigned to a virtual server. Remove the iRule reference from the virtual server first.

#### Deletion Order (Dependencies)

When decommissioning a full application stack, delete in this order:

1. Remove iRule references from virtual servers (update)
2. Delete virtual servers
3. Delete pools
4. Delete orphaned iRules
5. Delete orphaned profiles

Reversing this order will cause dependency errors.

---

### Traffic Shifting / Blue-Green Deployment

A common F5 change pattern is shifting traffic between pool versions for deployments.

#### Step 1: Create the New Pool (Green)

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" create_tool '{"url_body":{"name":"pool_webapp_v2","monitor":"http","loadBalancingMode":"round-robin","members":["10.1.2.10:80","10.1.2.11:80","10.1.2.12:80"],"description":"Webapp v2.0 pool - blue/green deployment"},"object_type":"pool"}'
```

#### Step 2: Verify New Pool Health

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"pool_webapp_v2","object_type":"pool"}'
```

Confirm all members are available and passing health checks before shifting traffic.

#### Step 3: Shift Virtual Server to New Pool

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"pool":"pool_webapp_v2"},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

#### Step 4: Monitor Post-Shift

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"pool_webapp_v2","object_type":"pool"}'
```

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"100"}'
```

Verify traffic is flowing to the new pool, no errors in logs, and response times are acceptable.

#### Step 5: Rollback (If Needed)

If the new pool is unhealthy, immediately revert to the old pool:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"pool":"pool_webapp"},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

#### Step 6: Cleanup Old Pool (After Burn-In)

Once the new pool is verified stable (after appropriate burn-in period), remove the old pool:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" delete_tool '{"object_type":"pool","object_name":"pool_webapp"}'
```

---

### Phase 4: Post-Change Verification

Immediately after applying configuration, verify the change.

#### 4A: Verify Object Was Created/Updated

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" list_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

Compare with the pre-change baseline to confirm only intended changes were made.

#### 4B: Verify Object Health

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"pool_webapp","object_type":"pool"}'
```

Confirm:
- Pool members are marked available (passing health checks)
- Virtual server is available and accepting connections
- Statistics are incrementing (traffic is flowing)

#### 4C: Check for Errors in Logs

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_logs_tool '{"lines_number":"100"}'
```

Look for new error messages that appeared after the Phase 1D baseline timestamp.

#### 4D: Verify Dependent Objects

If you changed a pool, verify the virtual servers that reference it are still healthy:

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" show_stats_tool '{"object_name":"vs_webapp_https","object_type":"virtual"}'
```

### Phase 5: Rollback (If Verification Fails)

If verification fails, roll back by restoring the baseline state.

**For created objects:** Delete the newly created object.

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" delete_tool '{"object_type":"pool","object_name":"pool_webapp_v2"}'
```

**For updated objects:** Patch the object with the original values from the baseline.

```bash
IP_ADDRESS=$F5_IP_ADDRESS Authorization_string=$F5_AUTH_STRING python3 $MCP_CALL "python3 -u $F5_MCP_SCRIPT" update_tool '{"url_body":{"pool":"pool_webapp"},"object_type":"virtual","object_name":"vs_webapp_https"}'
```

**For deleted objects:** Recreate the object using the baseline configuration.

After rollback, re-verify that the BIG-IP returned to its baseline state.

---

## Change Documentation

After every change, produce a change report:

```
F5 Change Report -- YYYY-MM-DD HH:MM UTC
Device: $F5_IP_ADDRESS
Requestor: [who requested the change]

Change Description:
  Created pool_webapp with 3 members for new web application

Objects Modified:
  [CREATED] pool_webapp (pool) -- 3 members, round-robin, HTTP monitor
  [CREATED] vs_webapp_https (virtual) -- 10.100.1.50:443, SSL offload, automap

Pre-Change State:
  - Virtual servers: 4 active
  - Pools: 3 active
  - No errors in logs

Post-Change State:
  - Virtual servers: 5 active (+1 vs_webapp_https)
  - Pools: 4 active (+1 pool_webapp)
  - pool_webapp: 3/3 members available
  - vs_webapp_https: available, accepting connections
  - New log entries: pool_webapp member 10.1.1.10:80 monitor status up (expected)

Verification: PASSED
Rollback Required: No
```

---

## ServiceNow Change Request Integration

When ServiceNow is available ($SERVICENOW_MCP_SCRIPT is set), every F5 configuration change MUST be gated by an approved Change Request.

### Pre-Change: Create CR

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" create_change_request '{"short_description":"Create pool_webapp and vs_webapp_https on F5 BIG-IP","description":"Create new pool with 3 web server members (10.1.1.10-12:80) and HTTPS virtual server (10.100.1.50:443) with SSL offload. Health monitor: HTTP. Load balancing: round-robin. Rollback: delete vs_webapp_https then pool_webapp.","category":"Network","priority":"3","risk":"moderate","impact":"3"}'
```

### Approval Gate

```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" get_change_request_details '{"change_id":"CHG0012345"}'
```

**STOP** if state is not approved. Inform the human and wait.

### Post-Change: Close CR

If verification passes:
```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0012345","work_notes":"Change applied and verified. pool_webapp 3/3 members available, vs_webapp_https accepting connections, no errors in logs.","state":"closed"}'
```

If verification fails:
```bash
python3 $MCP_CALL "python3 -u $SERVICENOW_MCP_SCRIPT" update_change_request '{"change_id":"CHG0012345","work_notes":"Post-change verification FAILED. Rollback initiated. Objects removed. Human review required.","state":"review"}'
```

---

## Integration with Other Skills

| Skill | Integration Point |
|-------|------------------|
| **f5-health-check** | Pre-change health validation and post-change verification |
| **f5-troubleshoot** | Investigate failures during verification phase |
| **servicenow-change-workflow** | CR creation, approval gate, closure |
| **drawio-diagram** | Generate before/after topology diagrams |
| **markmap-viz** | Visualize change plan as a mind map |
| **gait-session-tracking** | Audit trail for every phase |

## GAIT Audit Trail

Record every phase of the change in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"prompt":"F5 config change: Create pool_webapp and vs_webapp_https","response":"Phase 1 baseline captured (4 virtuals, 3 pools, no errors). Phase 2 plan approved. Phase 3 applied: created pool_webapp (3 members, HTTP monitor, round-robin) and vs_webapp_https (10.100.1.50:443, SSL offload, automap). Phase 4 verification PASSED: all members available, VIP accepting connections, no log errors. ServiceNow CR CHG0012345 closed successful.","artifacts":["f5-change-report.txt"]}'
```

The 5-phase workflow with GAIT creates an immutable record:
1. **Baseline** -- GAIT commit with pre-change object state
2. **Plan** -- GAIT commit with change plan and CR number
3. **Apply** -- GAIT commit with exact API calls made
4. **Verify** -- GAIT commit with post-change state and diff
5. **Document** -- GAIT commit with final summary and CR closure
