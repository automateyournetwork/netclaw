---
name: percepxion-oob
description: "Manage Lantronix out-of-band (OOB) infrastructure via Percepxion central management platform: device inventory, serial port inspection via SLC CLI, firmware compliance, config management, security auditing, and closed-loop incident remediation. Use during outages, maintenance windows, compliance cycles, and AI-assisted automation workflows."
version: 1.0.0
license: Apache-2.0
user-invocable: true
tags: [lantronix, percepxion, oob, out-of-band, console-server, slc9000, slc8000, emg7500, emg8500, network-ops, serial-console, network-automation, aoob, naf, closed-loop, fleet-management, incident-remediation]
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "uv"], "env": ["PERCEPXION_USERNAME", "PERCEPXION_PASSWORD"] } } }
---

# Percepxion OOB Skill

## What Is Out-of-Band Management?

Out-of-Band (OOB) management is a dedicated secondary path to the console port of every network device in your infrastructure. When a switch, router, firewall, or server becomes unreachable via its production (in-band) network interface, OOB gives you serial console access through an independent control plane, often with a resilient cellular network WAN connection,  so you can, Day-0 provision, diagnose, recover, or remediate even when the production network is completely dark.

OOB turns a midnight outage that would require a truck roll into a routine remote session.

**Lantronix hardware in this stack:**

| Device | Role | Ports | Cellular | Status |
|--------|------|-------|--------|--------|
| **SLC9000** | Console server, current gen. Serial or USB console ports and Ethernet switch ports. Dual power, redundant management interfaces, Percepxion-native, OpenAPI 3.1. | 16-48 | Optional 5G | Announced June 1st, 2026 |
| **SLC8000** | Console server, previous gen. Still widely deployed in enterprise and carrier networks. Full Percepxion support. | 8-48 | - | Shipping until December 31st, 2026 |
| **EMG series** | Compact console server for small closets or remote edge sites. | 4-8 | Optional 4G | Production |

**Percepxion** is the SaaS-native management platform that aggregates these devices into a single API surface. It handles device ZTP, authentication, session brokering, firmware lifecycle, configuration management, access logging, and multi-tenant operations across thousands of devices. The Percepxion MCP server exposes 37 tools against this API.

---

## Key Terms: OOB Device vs. Managed Device

This skill operates on two distinct device types. Confusing them causes wrong tool calls and unwanted outcomes.

| Term | What it is | Examples | How you reference it |
|------|-----------|---------|---------------------|
| **OOB device** (also: console server) | The Lantronix hardware managed by Percepxion. Has serial ports that cable to managed devices. | SLC9000, SLC8000, EMG7500, EMG8500 | By `device_id` in most MCP tool calls |
| **Managed device** (also: attached device, target device) | The network device whose console port is physically cabled to a serial port on the OOB device. NOT managed by Percepxion directly. | Cisco switch, Juniper router, Palo Alto firewall, OOB-connected server | Via `get_security_telemetry` (full inventory: hostname, model, serial, IP, OS) or `get_port_telemetry` (single port). `list_device_ports` returns port state only, not managed-device identity. |

**Tool routing for port and managed-device queries:**

| Question | Correct tool | Notes |
|----------|-------------|-------|
| What ports does this OOB device have? | `list_device_ports` | Returns port names, numbers, and connection state. Does NOT return managed-device hostname, model, serial, or IP. |
| What managed devices are attached to this OOB device? | `get_security_telemetry` | Source of truth for managed-device inventory. Returns per-port `dp_info` records: hostname, model, serial, IP, OS version, uptime, CPU/memory/flash. Also includes console manager, firmware, network, and audit records. |
| What is on a specific port (e.g. port 2)? | `get_port_telemetry` | Single-port filtered view. Returns structured managed-device object for that port only. Cheaper than `get_security_telemetry` for targeted single-port questions. |
| What port is a named managed device on? | `list_device_ports` with device name as `device_id` | Searches port index by label/name. Returns `parent_device_id` and `port_number` for computing SSH connection string. |

**The key distinction for tool calling:**

- All Percepxion MCP tools, `get_device_list`, `get_device_details`, `get_device_config`, `firmware_compliance_report`, `reboot_device`, and `send_direct_cli_command`, operate on the **OOB device**. The `device_id` in every tool call is the OOB device ID from `get_device_list` or `get_device_details`.
- `send_direct_cli_command` runs commands on the SLC's own management CLI (Linux shell), not on managed devices attached via serial. Valid commands are SLC-native: `show deviceport names`, `show deviceport port N`, `connect direct deviceport N`,`show sysstatus`, `admin version`, `diag ping <ip>`, `diag traceroute <ip>`. Cisco/Juniper/Arista CLI syntax will not work here. Full CLI command reference in Users Guide [cdn.lantronix.com/wp-content/uploads/pdf/900-704-RBD-SLC-UG.pdf](https://cdn.lantronix.com/wp-content/uploads/pdf/900-704-RBD-SLC-UG.pdf) beginning in chapter "15: Command Reference".
- There is no Percepxion MCP tool that provides an interactive managed-device CLI session over serial. However, the MCP can compute the direct SSH connection string you need, see the "When to ask for clarification" section below. For a fully interactive terminal session rather than a connection string, SSH directly to the SLC (`ssh sysadmin@<slc-ip>`) and use `connect direct deviceport N` from the SLC shell. That is a human-in-the-loop operation outside this MCP server's scope.

**When to ask for clarification:**

If the operator says "I need to run a command on the device," ask:
- "Do you mean the OOB console server (the SLC itself), or a managed device attached to one of its serial ports?"

If they mean the SLC, proceed with `send_direct_cli_command` using SLC CLI syntax.

If they mean an attached managed device, do not stop at "SSH to the SLC directly." Instead, proactively look up the connection details they need:

1. `list_device_ports(device_id=<managed_device_name_or_port_label>)`, search port records by the managed device name or partial port label. The `device_id` parameter functions as a search string against the Percepxion port index, the same search the WebUI Device Ports view uses. Results include `parent_device_id` (which SLC hosts this port) and `port_number`.
2. From the matching port record, read `parent_device_id` and `port_number`. If the port status shows disconnected or no carrier detect, flag it before returning the connection string.
3. `get_device_details(device_id=parent_device_id)`, retrieve the SLC's management IP address.
4. Calculate the SSH direct-connect port: **3000 + port number** (port 2 → TCP 3002, port 16 → TCP 3016)
5. Return the ready-to-use connection string:
   ```
   ssh -p <3000+N> <username>@<slc-management-ip>
   ```

The username is typically the operator's Percepxion/SLC credential. If unknown, surface the SLC IP and port and note they will be prompted for credentials on connect.

This saves the operator from logging into Percepxion to find port assignments manually.

This disambiguation drives every tool choice in this skill.

---

## When to Use This Skill

Proactive use is as important as reactive use. The Percepxion MCP is not a break-glass tool, it's the management plane for the OOB infrastructure at all times. Use it before incidents happen, not only during them.

| Trigger | OOB Role | Workflows / Tools |
|---------|----------|-------------------|
| Production network outage, device unreachable | Diagnose via SLC CLI, assess serial port state, capture evidence | W2 preflight + W3 diagnostics + W8 closed-loop |
| Maintenance window, fleet firmware update | Compliance scan + bulk upgrade via Smart Groups | W4: `firmware_compliance_report`, `update_firmware_by_smart_group` |
| Proactive compliance run | Config drift detection, template enforcement | W6: `get_device_config`, `clone_device_config`, `list_templates` |
| PagerDuty / Itential event fires | Closed-loop automated remediation with audit trail | W8 full flow |
| Security audit / access review | Who accessed what, when, from where | W5: `investigate_audit_logs`, `get_security_telemetry` |
| New site onboarding | Bulk device import and config clone | W7: `import_and_assign_devices`, `clone_device_config` |
| AI automation pre/post validation | Verify OOB path is healthy before and after primary-network changes | W2: `get_device_details`, `list_device_ports` or `send_direct_cli_command` |

**If a user asks about fleet health, firmware currency, config drift, or access history, pull the relevant Percepxion data immediately.** Do not wait for an incident to justify the query.

---

## Golden Rule

**Never send CLI commands to a managed device or push firmware to an OOB device without explicit operator confirmation.** `send_direct_cli_command` reaches live network infrastructure through a serial port, a wrong port number sends your command to the wrong managed device entirely. `update_firmware_by_smart_group` pushes firmware to OOB devices and is irreversible while in progress. All mutating actions require human confirmation before invocation.

**Always call `login_with_env` first.** Every session requires authentication. No other tool will succeed without an active session. This is not optional.

**Read before you write.** Call `get_device_list` or `get_device_details` to confirm the OOB device. Call `get_security_telemetry` (or `get_port_telemetry` for a single port) to confirm which port reaches the target managed device and verify it shows a connected managed device. `list_device_ports` returns port state only, it does not surface managed-device hostname, model, or serial. Never skip these steps.

---

## MCP Server

This skill uses the **percepxion-mcp-server**, a Python/FastMCP server that wraps the Percepxion REST API.

- **Repository:** https://github.com/Lantronix/percepxion-mcp-server
- **Transport:** stdio
- **Python version:** 3.11+

**Install:**
```bash
git clone https://github.com/Lantronix/percepxion-mcp-server.git
cd percepxion-mcp-server
uv venv && uv pip install -r requirements.txt
```

**Register in openclaw.json (stdio transport):**
```json
{
  "percepxion": {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "--directory", "/path/to/percepxion-mcp-server", "python", "percepxion_mcp.py"],
    "env": {
      "PERCEPXION_USERNAME": "${PERCEPXION_USERNAME}",
      "PERCEPXION_PASSWORD": "${PERCEPXION_PASSWORD}",
      "PERCEPXION_API_URL": "${PERCEPXION_API_URL}"
    }
  }
}
```

**Version requirement:** this skill was written based on percepxion-mcp-server v1.1.0. If not at this version or later, update the server from the repository above, in particular `get_cli_command_output` (retrieve actual CLI output text) and role-aware `organization_id` enforcement (see Platform Security Configuration) were both added in v1.1.0 and this skill assumes they're present.

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PERCEPXION_USERNAME` | Yes | | Percepxion login username |
| `PERCEPXION_PASSWORD` | Yes | | Percepxion login password |
| `PERCEPXION_API_URL` | No | `https://api.percepxion.ai/api` | API base URL. Use `https://api.gopercepxion.ai/api` for the Lantronix internal sandbox. |
| `PERCEPXION_CREDENTIAL_PROVIDER` | No | `env` | Credential backend: `env` (default), `vault`, `aws`, or `cyberark`. See Platform Security Configuration. |
| `PERCEPXION_DEFAULT_ORGANIZATION_ID` | No | | Default organization ID used when callers omit `organization_id`. Useful for single-organization deployments. Primary name; `PERCEPXION_DEFAULT_TENANT_ID` still works as a deprecated alias. |
| `PERCEPXION_REQUEST_TIMEOUT` | No | `45` | HTTP timeout in seconds. Raise to `120` or higher for large log downloads or slow links. |
| `PERCEPXION_FIRMWARE_DIR` | No | | If set, firmware uploads are restricted to files in this directory. Recommended for shared or automated deployments. |

> **Important:** Use `https://api.percepxion.ai/api`, not `api.gopercepxion.ai` which is a sandbox environment unless explicitly instructed by the user. The wrong domain causes silent auth failures.

---

## SLC MCP Server

Workflow 3 (SLC Console Diagnostics) and any direct, synchronous single-device access use the **slc-mcp-server**, a separate Python/FastMCP server that talks to an SLC9000/SLC8000 console server directly, not through Percepxion's cloud.

- **Repository:** https://github.com/Lantronix/slc-mcp-server
- **Transport:** stdio
- **Python version:** 3.11+

**Install:**
```bash
git clone https://github.com/Lantronix/slc-mcp-server.git
cd slc-mcp-server
uv venv && uv pip install -r requirements.txt
```

**Register in openclaw.json (stdio transport):**
```json
{
  "slc": {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "--directory", "/path/to/slc-mcp-server", "python", "slc_mcp.py"],
    "env": {
      "SLC_DEFAULT_IP": "${SLC_DEFAULT_IP}",
      "SLC_USERNAME": "${SLC_USERNAME}",
      "SLC_PASSWORD": "${SLC_PASSWORD}"
    }
  }
}
```

### SLC Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLC_DEFAULT_IP` | No | | Default device IP, used when `device_id` isn't in the per-device registry |
| `SLC_USERNAME` | No | `sysadmin` | Default username |
| `SLC_PASSWORD` | No | | Default password |
| `SLC_TOTP_SECRET` | No | | Default TOTP secret for 2FA-enabled devices |
| `SLC_{KEY}_IP` / `SLC_{KEY}_USERNAME` / `SLC_{KEY}_PASSWORD` / `SLC_{KEY}_TOTP_SECRET` | No | | Per-device credentials, `{KEY}` is the device identifier uppercased with non-alphanumeric characters replaced by `_` (e.g. `device_id` `slc9000-dc-a` becomes `SLC_SLC9000_DC_A_IP`) |
| `SLC_VERIFY_SSL` | No | `true` | Set to `false` only for lab devices with self-signed certificates. Never disable in production. |
| `SLC_CREDENTIAL_PROVIDER` | No | `env` | Credential backend: `env` (default), `vault`, `aws`, `percepxion`, or `cyberark`. The `percepxion` provider looks up device IP from the Percepxion device registry (requires `PERCEPXION_API_URL`/`PERCEPXION_USERNAME`/`PERCEPXION_PASSWORD` above) while SLC credentials still come from `SLC_{KEY}_*`. |
| `SLC_CLI_WRITE_ENABLED` | No | `false` | Allow write commands via `apply_config_commands` and px client tools |
| `SLC_CLI_YOLO` | No | `false` | Disable all CLI policy filtering. Never use in production. |

Read-only commands (`show`, `diag`, `ping`, `traceroute`, etc.) are always permitted regardless of `SLC_CLI_WRITE_ENABLED`. A built-in deny list (`factory-reset`, `write erase`, `erase startup-config`, `erase flash`, `reload`, `reboot`, `format`, `shutdown`, `power off`, `reset system`, `init 0`, `halt`) always blocks unless `SLC_CLI_YOLO=true`.

---

## Workflow 1: Session Auth + Device Discovery (P1, Required First Step)

Every session starts here. You must authenticate before any other tool will succeed.

### Step 1: Authenticate

```
Tool: login_with_env
Parameters: {}
```

Returns a session token stored in memory for the server process lifetime. Confirm the response shows `"ok": true` before proceeding.

### Step 2: List All OOB Devices

`get_device_list` returns OOB devices (the Lantronix console servers), not managed devices. All are optional parameters.

```
Tool: get_device_list
Parameters: {
  "search_query": "*",
  "limit": 25,
  "sort": "device_name",
  "order": "asc"
}
```

Returns all OOB console servers managed by your Percepxion account. Note device IDs, you'll need them for every subsequent tool call. Use `search_query` to filter by hostname or model.

### Step 3: (Multi-tenant) List Organizations and Filter by Org

If the account manages multiple customer organizations:

```
Tool: list_organizations
Parameters: {}
```

(`list_tenants` still works as a deprecated alias for `list_organizations`. `organization_id` is the primary parameter name across all tools; `tenant_id` still works everywhere as a deprecated alias.)

Then filter by organization:

```
Tool: get_devices_by_organization
Parameters: {
  "organization_id": "org-abc123"
}
```

**If the authenticated account is a Percepxion Project Admin**, `organization_id` is *required*, not optional, on job/telemetry/content/Smart-Group/audit calls (`send_direct_cli_command`, `get_cli_command_output`, `search_job_groups`, `get_job_group`, `update_device_config`, `reboot_device`, `request_device_syslog_upload`, smart group and firmware tools, audit tools, and more). A Project Admin's access spans every organization in their project, so Percepxion can't infer a single default the way it does for Tenant Admin/Tenant User accounts (auto-scoped to their one organization, `organization_id` optional for those). Omitting it as a Project Admin raises a clear error naming the missing parameter (percepxion-mcp-server v1.1.0+); before that fix it surfaced as an opaque `400 ACCESS_DENIED: "Invalid access to tenant."` Call `list_organizations` first if you don't already have the ID to pass. Device-inventory tools (`get_device_list`, `get_device_details`, `list_device_ports`) don't require it for any role. See Platform Security Configuration for the full rule.

### Step 4: Get Details for a Specific OOB Device

Look up by device ID or serial number, at least one is required.

```
Tool: get_device_details
Parameters: {
  "device_id": "device-abc123"
}
```

Or by serial number if device ID is unknown:

```
Tool: get_device_details
Parameters: {
  "serial_num": "SLC9016-XXXXXX"
}
```

Returns hostname, firmware version, model, IP address, last check-in time, and status for the **OOB device**.

### Example Prompts
- "Show all OOB devices managed by Percepxion"
- "List all console servers in org org-abc123"
- "Get details for device device-abc123"
- "What firmware version is each SLC9000 running?"
- "Which devices haven't checked in recently?"

---

## Workflow 2: Preflight, Validate OOB Path Before Automation (P2, Run Before Any Automated Action)

Before triggering automated remediation, maintenance tasks, or configuration changes, confirm the OOB device is reachable and the target serial port shows an active connection. A failed preflight stops you before committing to an operation on a dead or misidentified console path.

### Step 1: Confirm the OOB Device is Online

```
Tool: get_device_details
Parameters: {
  "device_id": "device-abc123"
}
```

Check status is `online` and last check-in is recent. If the OOB device is offline, the serial path is unavailable. Stop and alert the operator.

### Step 2: List Device Ports

`list_device_ports` returns port names, numbers, and connection state. `get_security_telemetry` returns full managed-device inventory per port (hostname, model, serial, IP, OS version). Use both: `list_device_ports` to enumerate ports and confirm connection state, `get_security_telemetry` (or `get_port_telemetry` for a single port) to confirm the right managed device is present on the target port. A `list_device_ports` result of `total: 0` or an empty port status does not mean no managed devices are attached, the telemetry endpoint is authoritative for that question.

```
Tool: list_device_ports
Parameters: {
  "device_id": "device-abc123",
  "limit": 100
}
```

Confirm the port status shows `connected`. Then verify managed-device identity:

```
Tool: get_port_telemetry
Parameters: {
  "device_id": "device-abc123",
  "port_number": 4
}
```

Or for all ports at once:

```
Tool: get_security_telemetry
Parameters: {
  "device_id": "device-abc123"
}
```

Confirm the target port's `managed_device` shows `Managed Device Attached: Yes` and the hostname or model matches the expected device. If the port shows no device in either tool, the serial cable may be unplugged or the managed device is powered off. Warn the operator and stop unless they explicitly override.

For richer per-port detail (carrier detect state, baud rate, bytes transferred), supplement with a CLI call:

```
Tool: send_direct_cli_command
Parameters: {
  "device_id": "device-abc123",
  "command": "show deviceport port 4",
  "description": "W2 preflight, detailed port 4 inspection"
}
```

Poll `get_job_group` (or `search_job_groups`) with the returned `job_group_id` until status reaches `"Completed"`, then call `get_cli_command_output` with that same `job_group_id` and `device_id` for the actual command output text. `get_job_group` alone returns status and metadata only, never the output text, see the Async Operations section below.

### Step 3: Proceed, Abort, or Override

- **Pass:** OOB device online, target port connected with carrier detect. Proceed to the calling workflow.
- **Fail:** Report the specific failure reason (OOB offline / port disconnected / no carrier detect). Stop by default.
- **Operator override:** If the operator explicitly acknowledges the failure and authorizes proceeding, record their acknowledgment in the `description` field of all subsequent tool calls: `"description": "Operator authorized: proceeding despite [reason]"`. This creates an auditable record. The operator's override cannot bypass server-side CLI policy (see Platform Security Configuration).

### Example Prompts
- "Run a preflight check on the OOB path before we start the maintenance window"
- "Verify the serial port for Chicago-WAN-01 is connected and has carrier"
- "Check all OOB console paths in this window are reachable before we start"
- "Preflight failed on port 4, the operator acknowledges the risk and says proceed"

---

## Workflow 3: SLC Console Diagnostics and Device Port Inspection (P3)

Use `send_direct_cli_command` to run diagnostic commands on the SLC's own management CLI. This is how you assess port state, check SLC system health, and collect evidence before or during an incident. All commands target the SLC itself, not managed devices attached via serial.

**What `send_direct_cli_command` does:** Submits a command to the SLC's native Linux/management shell and returns a job group ID. The SLC executes the command and reports what it observes, including the state of each serial port (carrier detect, baud rate, bytes transferred). The `device_id` is always the OOB device (SLC) ID.

**What it does NOT do:** Pass commands through to managed devices (Cisco switch, Juniper router, Arista switch). Commands like `show ip interface brief` or `show ip bgp summary` are Cisco IOS syntax and will not work here. If the operator needs to reach a managed device CLI, the MCP can compute the direct SSH connection string (`ssh -p <3000+N> <user>@<slc-ip>`) using `get_device_details` and `list_device_ports`, see "When to ask for clarification" in the Key Terms section. For a fully interactive terminal session, SSH directly to the SLC (`ssh admin@<slc-ip>`) and use `connect direct deviceport N` from the SLC shell. That is a human-in-the-loop operation outside this MCP server's scope.

All `send_direct_cli_command` calls are asynchronous, and returning the actual output text is a two-step follow-up, not one. Poll status first, then fetch output:

```
Tool: get_job_group
Parameters: { "job_group_id": "<id from send_direct_cli_command response>" }
```

Once status reaches `"Completed"`:

```
Tool: get_cli_command_output
Parameters: {
  "job_group_id": "<same id>",
  "device_id": "<same device_id>"
}
```

`get_job_group` alone never returns CLI output text, only job status and metadata (device, command string, timestamps). Calling `get_cli_command_output` before the job completes returns `total_results: 0`, not an error, retry after a short delay. (percepxion-mcp-server v1.1.0+; earlier versions had no working way to retrieve CLI output text via the API at all, only job status via MQTT.)

### Step 1: Check SLC System Health

```
Tool: send_direct_cli_command
Parameters: {
  "device_id": "device-abc123",
  "command": "show sysstatus",
  "description": "SLC health check, pre-incident diagnostics"
}
```

```
Tool: get_job_group
Parameters: {
  "job_group_id": "<id from send_direct_cli_command response>"
}
```

Once `"status": "Completed"`:

```
Tool: get_cli_command_output
Parameters: {
  "job_group_id": "<id from send_direct_cli_command response>",
  "device_id": "device-abc123"
}
```

### Step 2: Inspect a Specific Serial Port

```
Tool: send_direct_cli_command
Parameters: {
  "device_id": "device-abc123",
  "command": "show deviceport port 4",
  "description": "Port 4 inspection, checking carrier detect and connection state"
}
```

Poll `get_job_group` for status, then `get_cli_command_output` (same `job_group_id` + `device_id`) for the actual text. Output includes: baud rate, carrier detect (yes/no), connection state, bytes sent/received since last session. A `no carrier` result means the attached device is powered off or the cable is disconnected.

### Step 3: Survey All Ports

```
Tool: send_direct_cli_command
Parameters: {
  "device_id": "device-abc123",
  "command": "show portstatus",
  "description": "Full port survey, pre-maintenance audit"
}
```

Poll `get_job_group` for status, then `get_cli_command_output` for the actual text. Returns the mode and state of every device port. Useful for inventory checks and preflight before bulk operations.

### Step 4: Test Network Reachability from the SLC

```
Tool: send_direct_cli_command
Parameters: {
  "device_id": "device-abc123",
  "command": "diag ping 192.168.1.50",
  "description": "Reachability test to managed device management IP from SLC local network"
}
```

Poll `get_job_group` for status, then `get_cli_command_output` for the actual text. Tests whether the managed device is reachable via its management IP from the SLC's network path. Confirms whether the failure is in-band (unreachable from the SLC too) or isolated to the production network.

### Step 5: Collect SLC Evidence After Diagnostics

After any diagnostic session, capture OOB device logs for the audit trail:

```
Tool: get_device_syslogs
Parameters: {
  "device_id": "device-abc123"
}
```

```
Tool: query_device_access_log
Parameters: {
  "device_id": "device-abc123",
  "query": "session opened"
}
```

### Example Prompts
- "Check the health status of the SLC at device-abc123"
- "What does port 4 look like on device-abc123, is it connected and does it have carrier detect?"
- "Survey all serial ports on device-abc123 to find which ones are active"
- "Run diag ping 192.168.1.50 from the SLC to test if the managed device is reachable via OOB network path"
- "Get the syslogs from device-abc123 after the diagnostic session"

---

## Workflow 4: Firmware Compliance and Updates (P4)

Use before maintenance windows, for quarterly compliance reviews, or when CVEs require a coordinated patch across the fleet.

### Step 1: Check Firmware Status for One Device

```
Tool: get_device_firmware_status
Parameters: {
  "device_id": "device-abc123"
}
```

### Step 2: Run a Fleet-Wide Compliance Report

`expected_firmware_version` is required. Use `model_filter` to scope to one device family.

```
Tool: firmware_compliance_report
Parameters: {
  "expected_firmware_version": "9.7.0.0R11",
  "model_filter": "SLC9000",
  "limit": 1000
}
```

Returns compliant, non-compliant, and unknown devices for the OOB fleet against the specified version.

### Step 3: List Available Firmware Packages

```
Tool: list_firmware_content
Parameters: {}
```

Returns firmware packages available in Percepxion for your OOB device models (SLC9000, SLC8000, EMG).

### Step 4: Create a Smart Group for Non-Compliant Devices

Use a `query` filter string OR an explicit `device_ids` list, not both. Use `temporary: true` for one-off operations.

```
Tool: create_smart_group
Parameters: {
  "name": "slc9000-non-compliant-q2",
  "query": "firmware_ver:9.7.0.0R7 AND model:SLC9000",
  "description": "Non-compliant SLC9000s for Q2 patch cycle",
  "temporary": true
}
```

Returns a smart group ID. Smart groups re-evaluate membership at execution time.

### Step 5: Confirm Scope with Operator

Present: smart group name, member count, current firmware versions, target firmware version, and the local firmware file path that will be uploaded. Wait for explicit confirmation.

### Step 6: Push Firmware Update

`update_firmware_by_smart_group` uploads a local firmware file to Percepxion and targets one or more smart groups. You must have the firmware file on disk before calling this. `smart_group_ids` is an array.

```
Tool: update_firmware_by_smart_group
Parameters: {
  "firmware_file_path": "/path/to/SLC9000-9.7.0.0R11.bin",
  "smart_group_ids": ["sg-abc123"],
  "content_name": "SLC9000-9.7.0.0R11",
  "version": "9.7.0.0R11",
  "description": "Q2 compliance patch, operator authorized",
  "enable": true
}
```

This is asynchronous and maps to a multipart/form-data upload. Returns a job group ID immediately.

### Step 7: Monitor Job Status

```
Tool: get_job_group
Parameters: {
  "job_group_id": "jg-xyz789"
}
```

Or search recent jobs:

```
Tool: search_job_groups
Parameters: {
  "query": "firmware update",
  "limit": 10
}
```

Poll until status is `completed` or `failed`. On `failed`, surface the error reason to the operator.

For a per-device breakdown across the Smart Group (which devices succeeded, which failed) rather than just the overall job status, use `get_job_results_by_device(job_group_id)` instead of, or alongside, `get_job_group`.

### Step 8: Clean Up the Smart Group

```
Tool: delete_smart_group
Parameters: {
  "smart_group_id": "sg-abc123"
}
```

### Example Prompts
- "Run a firmware compliance report for all devices"
- "Which SLC9000s are not on firmware 9.7.0.0R11?"
- "Push firmware 9.7.0.0R11 to all non-compliant SLC9000s"
- "What's the status of this morning's firmware update job?"
- "List available firmware for SLC8000"

---

## Workflow 5: Security Audit and Access Investigation (P5)

Use for post-incident access reviews, compliance audits, or when a security team needs to reconstruct who accessed which OOB devices during a specific window.

### Step 1: Get Security Telemetry for a Specific OOB Device

`device_id` is required, this is scoped to one OOB device, not fleet-wide.

```
Tool: get_security_telemetry
Parameters: {
  "device_id": "device-abc123",
  "selected": true
}
```

Returns telemetry statistics useful for security analysis on that OOB device.

### Step 2: Investigate Audit Logs by Time Window and Search String

`investigate_audit_logs` has no `device_id` parameter. Filter by device using `search_string`. Date parameters are `from_date` and `to_date`, not `start_time`/`end_time`. If dates are omitted, the default range is effectively all history.

```
Tool: investigate_audit_logs
Parameters: {
  "search_string": "device-abc123",
  "from_date": "2026-06-01",
  "to_date": "2026-06-02",
  "limit": 50,
  "order": "desc"
}
```

To filter by specific users, pass a list to `usernames`:

```
Tool: investigate_audit_logs
Parameters: {
  "usernames": ["jsmith@example.com", "kwilson@example.com"],
  "from_date": "2026-06-01",
  "to_date": "2026-06-02",
  "limit": 50
}
```

### Step 3: Search User Audit Records

`investigate_user_audit_logs` returns user records with last audit action summaries. Filter with `user_filter` string, there are no date range parameters on this tool.

```
Tool: investigate_user_audit_logs
Parameters: {
  "user_filter": "jsmith@example.com",
  "limit": 50,
  "order": "asc"
}
```

### Step 4: Download Raw Access Log for Forensic Export

For SIEM ingestion or evidence preservation:

```
Tool: download_device_access_log
Parameters: {
  "device_id": "device-abc123"
}
```

### Step 5: Query Access Log for Specific Events

```
Tool: query_device_access_log
Parameters: {
  "device_id": "device-abc123",
  "query": "session opened port 8"
}
```

### Example Prompts
- "Who accessed device-abc123 during the outage window on June 1?"
- "Show all OOB actions by user jsmith@example.com in the last 7 days"
- "Get the fleet security telemetry summary"
- "Download the access log for device-abc123 for forensic export"
- "Were there any failed login attempts on OOB devices in the last 24 hours?"

---

## Workflow 6: Configuration Management (P6)

Use for baseline config distribution, config audit, or onboarding new OOB devices (console servers) with a standard configuration. All tools in this workflow operate on the OOB device, not on managed devices attached to it.

### Step 1: Read Current Device Config

```
Tool: get_device_config
Parameters: {
  "device_id": "device-abc123"
}
```

### Step 2: Update a Config Parameter

**Requires operator confirmation.** Present the proposed change before applying.

Use either `property_name` + `new_value` for a single change, or `items` for multiple changes at once. `apply_now: true` (default) saves and immediately creates a config pull job.

```
Tool: update_device_config
Parameters: {
  "device_id": "device-abc123",
  "property_name": "syslog_server",
  "new_value": "192.168.1.100",
  "apply_now": true
}
```

Multiple changes at once using `items`:

```
Tool: update_device_config
Parameters: {
  "device_id": "device-abc123",
  "items": [
    {"name": "hostname", "value": "slc9000-chicago-01"},
    {"name": "banner", "value": "Authorized access only. All sessions are logged."}
  ],
  "apply_now": true
}
```

### Step 3: Clone Config from One Device to Another

`record_names` is required, it specifies which config record names to copy from the source. Read the source config first with `get_device_config` to identify the record names.

1. Read source config: `get_device_config` on the baseline device
2. Identify `record_names` from the response
3. Confirm source and target device IDs with the operator

```
Tool: clone_device_config
Parameters: {
  "source_device_id": "device-abc123",
  "target_device_id": "device-def456",
  "record_names": ["network", "services", "authentication"],
  "template_name": "Chicago-Baseline-v2"
}
```

### Step 4: List Config Templates

```
Tool: list_templates
Parameters: {}
```

### Example Prompts
- "Get the current config for device-abc123"
- "Clone the config from our baseline device device-abc123 to newly racked device-def456"
- "Update the syslog server on device-abc123 to 192.168.1.100"
- "List all config templates in Percepxion"

---

## Workflow 7: OOB Device Lifecycle Operations (P7)

For onboarding new Lantronix hardware into Percepxion, offboarding decommissioned OOB devices, or rotating the credentials Percepxion uses to authenticate to each OOB device.

### Import and Assign New Devices

```
Tool: import_and_assign_devices
Parameters: {
  "devices": [
    {"device_id": "device-new-001", "device_name": "slc9000-chicago-02", "serial_num": "SLC9016-XXXXXX"},
    {"device_id": "device-new-002", "device_name": "slc9000-chicago-03", "serial_num": "SLC9016-YYYYYY"}
  ],
  "organization_id": "org-abc123"
}
```

Each entry in `devices` must include `device_id`, `device_name`, and `serial_num`. A fourth optional field `device_description`can be used for additional context. `organization_id` is required here for Project Admin sessions, see Platform Security Configuration.

### Reboot an OOB Device

**Requires operator confirmation.** A reboot of the OOB device causes a brief loss of serial console access to all managed devices on its ports. Confirm the maintenance window is acceptable.

1. Confirm OOB device ID and hostname via `get_device_details`
2. Confirm operator accepts the access loss window
3. Execute:

```
Tool: reboot_device
Parameters: {
  "device_id": "device-abc123",
  "description": "Scheduled reboot, maintenance window approved by operator"
}
```

### Remove a Decommissioned OOB Device

**Irreversible.** Confirm before executing.

```
Tool: remove_device_from_platform
Parameters: {
  "device_id": "device-abc123"
}
```

Or unassign from a tenant without removing from the platform:

```
Tool: unassign_devices
Parameters: {
  "device_ids": ["device-abc123"]
}
```

### Upload Syslog from OOB Device to Percepxion

Request the OOB device to upload its current syslog buffer for retrieval:

```
Tool: request_device_syslog_upload
Parameters: {
  "device_id": "device-abc123"
}
```

### Example Prompts
- "Add two new SLC9000s to tenant org-abc123"
- "Reboot OOB device device-abc123, it's been unresponsive to management pings"
- "Remove device-abc123 from Percepxion, it's been decommissioned"
- "Upload the syslog from device-abc123 so I can review it"

---

## Workflow 8: Closed-Loop Incident Remediation (P8)

**Trigger:** An upstream orchestrator (PagerDuty, Itential FlowAI, monitoring webhook) signals that a device is unreachable via the primary network. This workflow gives the orchestrator a complete OOB response: diagnostic evidence, optional remediation, and a traceable audit trail to close the incident ticket.

**Write access prerequisite:** Steps 7-8 (remediation commands) require `PERCEPXION_CLI_WRITE_ENABLED=true` on the MCP server. Steps 1-6 and 9 are read-only and always available.

### Step 1: Authenticate

```
Tool: login_with_env
Parameters: {}
```

Skip if already authenticated in this session.

### Step 2: Locate the OOB Device

```
Tool: get_device_list
Parameters: {
  "search_query": "<site-name or managed-device-name>"
}
```

Returns the Lantronix OOB device (SLC console server) managing the affected infrastructure at that site.

### Step 3: Confirm OOB Device is Reachable

```
Tool: get_device_details
Parameters: {
  "device_id": "<oob_device_id>"
}
```

**Critical branch:** If the OOB device itself is unreachable (`online: false`), OOB access is unavailable. Stop and escalate to a human. Do not proceed.

### Step 4: W2 Preflight, Verify Port State

Run Workflow 2 to confirm the managed device is connected at the serial layer. Check `show deviceport port <N>` via `send_direct_cli_command` for carrier detect and connection state.

If the port shows no carrier or a disconnected state, log this as a finding in the incident record and decide with the operator whether to continue.

### Step 5: Collect Pre-Action Evidence

```
Tool: get_device_syslogs
Parameters: {
  "device_id": "<oob_device_id>"
}
```

Captures the OOB device syslog before any action. This is the before-state evidence.

### Step 6: Run Diagnostic Commands

```
Tool: send_direct_cli_command
Parameters: {
  "device_id": "<oob_device_id>",
  "command": "show sysstatus",
  "description": "Automated incident response, incident-id: <upstream-incident-id>, diagnostics phase"
}
```

Run SLC-native diagnostics as needed (`show sysstatus`, `show deviceport port <N>`, `diag ping <ip>`). Always include the upstream incident ID in the `description` field. Poll `get_job_group` for status, then call `get_cli_command_output` with the same `job_group_id` and `device_id` for the actual diagnostic text, that's what goes into the incident record, `get_job_group` alone has no output.

### Step 7: Execute Remediation (Write Access Required)

**Only if `PERCEPXION_CLI_WRITE_ENABLED=true`.** Present the proposed command to the operator or upstream orchestrator before executing.

```
Tool: send_direct_cli_command
Parameters: {
  "device_id": "<oob_device_id>",
  "command": "<recovery-command>",
  "description": "Automated remediation, incident-id: <upstream-incident-id>, approved by: <orchestrator-or-operator>"
}
```

Confirm status via `get_job_group`, then confirm actual output via `get_cli_command_output` with the same `job_group_id` and `device_id`. Do not report remediation as successful based on job status alone, verify the device's own response text.

### Step 8: Collect Post-Action Audit Evidence

```
Tool: investigate_audit_logs
Parameters: {
  "search_string": "<oob-device-name-or-ip>"
}
```

Confirms the OOB action is in Percepxion's audit trail. Include the audit log excerpt in the incident closure report.

### Step 9: Report to Upstream Orchestrator

Return a structured outcome to the calling system (Itential, PagerDuty, ServiceNow):

- Job group ID from Step 7 (or Step 6 if no remediation was performed)
- Pre-action syslog summary from Step 5
- Post-action audit log entry from Step 8
- Final status: `remediated`, `diagnosed-only`, or `escalate-to-human`

### Governance Note

AI-initiated OOB access carries the same audit trail as human access. The `description` field on every `send_direct_cli_command` call is the machine's justification. Treat it like a change ticket number. Percepxion logs who authenticated, what commands ran, and when, regardless of whether a human or an AI agent initiated the session.

### Example Prompts
- "A PagerDuty alert fired on core-switch-nyc-01, it's unreachable via primary network. Run an OOB diagnostic."
- "Itential FlowAI is executing incident INC-4821. Open an OOB session to the SLC managing router-chi-03 and collect evidence."
- "Run automated OOB remediation on device-abc123, incident ID INC-4821, write access is enabled."

---

## Platform Security Configuration

### MCP Server Credential Providers

`login_with_env` supports four credential backends, selected by the `PERCEPXION_CREDENTIAL_PROVIDER` environment variable on the server:

| Provider | Env var to set | When to use |
|----------|---------------|-------------|
| `env` (default) | `PERCEPXION_USERNAME` + `PERCEPXION_PASSWORD` | Dev, local testing, simple deployments |
| `vault` | `VAULT_ADDR`, `VAULT_TOKEN`, `VAULT_SECRET_PATH` | Production, HashiCorp Vault for secret management |
| `aws` | `AWS_SECRET_NAME`, `AWS_REGION` | Production, AWS Secrets Manager |
| `cyberark` | `CYBERARK_URL`, `CYBERARK_APP_ID`, `CYBERARK_SAFE`, `CYBERARK_OBJECT` | Enterprise deployments already running CyberArk Central Credential Provider (CCP) |

To switch providers at runtime, use `reconfigure_credentials` then re-authenticate:

```
Tool: reconfigure_credentials
Parameters: {
  "provider": "vault"
}
```

Valid values: `"env"`, `"vault"`, `"aws"`, `"cyberark"`. After calling this, always follow with `login_with_env` to re-authenticate with the new provider. This is NOT per-device credential rotation, it changes which secret store the MCP server itself uses for its Percepxion session credentials.

### Role-Based `organization_id` Requirement (v1.1.0+)

Percepxion's RBAC model has three roles, and their `organization_id`/`tenant_id` requirements differ:

| Role | Scope | `organization_id` on job/telemetry/content/Smart-Group/audit calls |
|------|-------|----------------------------------------------------------------|
| Tenant User | One or more specific organizations, explicitly group-granted | Optional, auto-scoped |
| Tenant Admin | One organization | Optional, auto-scoped |
| Project Admin | Every organization in their project | **Required** |

A Project Admin's access spans an entire Percepxion project (Percepxion's hierarchy is Project > Portal > Organization), and there's no API endpoint that enumerates a project's member organizations, so the server can't infer a single default the way it does for the other two roles. Omitting `organization_id` as a Project Admin now raises a clear error naming the missing parameter; before percepxion-mcp-server v1.1.0 this surfaced as an opaque `400 ACCESS_DENIED: "Invalid access to tenant."` with no indication why. **If a call fails with either error, check the authenticated account's role before assuming a bug**, call `list_organizations` to find the ID to pass. Device-inventory tools (`get_device_list`, `get_device_details`, `list_device_ports`) don't require it for any role.

### MCP Server CLI Policy (Operator Override Controls)

`send_direct_cli_command` enforces server-side CLI policy. These are environment variables set on the MCP server, not parameters in the tool call. **The AI cannot override these policies at runtime**, they must be configured by whoever starts the server.

| Env var | Default | Effect |
|---------|---------|--------|
| `PERCEPXION_CLI_WRITE_ENABLED` | `false` | `true` enables write commands. Read-only (`show`, `get`, `ping`, `traceroute`) is the default. |
| `PERCEPXION_CLI_MAX_LENGTH` | `512` | Maximum command length in characters. Automated workflows that build long commands will hit this silently. |
| `PERCEPXION_CLI_DENY_COMMANDS` | built-in list | Comma-separated commands to block in addition to the built-in deny list |
| `PERCEPXION_CLI_PERMIT_COMMANDS` | unset | Comma-separated explicit allowlist; if set, only these commands (and their subcommands) are allowed |
| `PERCEPXION_CLI_YOLO` | `false` | `true` disables ALL filtering including the deny list. Use with extreme caution. |

**Built-in deny list** (always blocked unless YOLO mode): `reload`, `factory-reset`, `write erase`, and similar destructive commands.

**Operator override pattern:** If an operator explicitly accepts risk and needs to run a write command or a normally-blocked command:
1. The server must be restarted with `PERCEPXION_CLI_WRITE_ENABLED=true` (or `PERCEPXION_CLI_YOLO=true` for full bypass)
2. The AI records the operator's authorization in the `description` field of every `send_direct_cli_command` call: `"description": "Write access enabled, operator authorized: [reason]"`
3. This creates an auditable record in the Percepxion job group log

### Percepxion Platform RBAC

User and device access permissions are configured in the Percepxion UI, not via this MCP server. A `send_direct_cli_command` failure with a permissions error means RBAC on the platform needs updating, there is nothing to change in the MCP call itself.

### Command Filtering at the Platform Level

Percepxion also supports per-port CLI command filtering configured in the platform UI (separate from the MCP server's CLI policy). If a command is allowed by the MCP server policy but blocked by Percepxion's own filtering, surface the error to the operator and advise reviewing the platform's command filter for that port.

### Session Audit

All MCP-initiated sessions are fully logged in Percepxion's audit trail: who authenticated, which commands ran, job group IDs, and session duration. Retrieve via `investigate_audit_logs`.

---

## Async Operations

The following tools are asynchronous, they return a job group ID immediately and continue in the background:

- `update_firmware_by_smart_group`
- `request_device_syslog_upload`
- `reboot_device`
- `send_direct_cli_command` (always async, not conditional on firmware build)

Always follow async calls with:

```
Tool: get_job_group
Parameters: { "job_group_id": "<id returned by the async call>" }
```

Poll until status is `"Completed"` or `"Failed"`. On failure, surface the full error reason to the operator before suggesting next steps.

**`get_job_group` and `search_job_groups` never return CLI output text**, only status and job metadata (device, command string, timestamps). For `send_direct_cli_command` jobs specifically, once status reaches `"Completed"`, call `get_cli_command_output(job_group_id, device_id)` for the actual device response text (percepxion-mcp-server v1.1.0+). For a multi-device job (e.g. a Smart Group firmware push or a CLI command sent to several devices at once), `get_job_results_by_device(job_group_id)` returns a per-device result rollup instead of one device at a time.

---

## Integration with Other NetClaw Skills

- **pagerduty-incidents**, When an incident fires on an unreachable device, trigger this skill to open an OOB console session and gather diagnostic evidence before escalating to a human
- **servicenow-change-workflow**, Reference ServiceNow change ticket IDs in audit records when performing governed OOB access during a change window
- **netbox-source-of-truth**, Cross-reference Percepxion device IDs with NetBox CIs to confirm expected firmware version, rack position, site, and device owner before taking action
- **itential-orchestration**, Itential FlowAI triggers W8 (closed-loop remediation); NetClaw executes the OOB session via Percepxion and returns a structured outcome (job group ID + audit evidence) to close the incident ticket. Pass the Itential workflow execution ID as the `description` value in every `send_direct_cli_command` call to create a traceable link between the automation record and the OOB action in Percepxion's audit log
- **gait-session-tracking**, Log all Percepxion operations to the GAIT audit trail for compliance evidence and post-incident review
- **grafana-observability**, Correlate Percepxion access events and telemetry with Grafana dashboard alerts when investigating device unreachability patterns

---

## Important Rules

**Terminology**
- When an operator says "the device," ask: OOB device (the Lantronix console server) or managed device (the router/switch/firewall attached to it)? Never assume.
- `device_id` in all MCP tool calls is the **OOB device** ID from `get_device_list`. This is always the Lantronix SLC or EMG, never the managed device (router/switch/firewall) attached to it.

**Authentication**
- Always call `login_with_env` at the start of every session. No other tool works without it.
- Never expose `PERCEPXION_USERNAME`, `PERCEPXION_PASSWORD`, `VAULT_TOKEN`, or session tokens in logs, chat output, or error messages.
- Use `https://api.percepxion.ai/api` as the API URL. `api.gopercepxion.ai` causes silent auth failures unless the operator has confirmed their instance uses that domain.

**Preflight before automation**
- Run Workflow 2 before any automated sequence that sends configuration changes or destructive commands to a managed device.
- If preflight fails at any step, stop by default. Only proceed if the operator explicitly acknowledges the failure and authorizes continuation, record their acknowledgment in the `description` field of every subsequent tool call.

**SLC CLI scope**
- `send_direct_cli_command` sends commands to the SLC's own management CLI (Linux/management shell), not to managed devices. Valid commands are SLC-native: `show sysstatus`, `show deviceport port <N>`, `show portstatus`, `diag ping <ip>`, `admin version`, etc.
- Interactive managed-device CLI (typing into a router or switch prompt over serial) is not supported by this MCP. The MCP can compute the direct SSH connection string (`ssh -p <3000+N> <user>@<slc-ip>`), see "When to ask for clarification" in the Key Terms section. For a fully interactive terminal session, direct SSH to the SLC followed by `connect direct deviceport <N>` from the SLC shell is required. That is a human-in-the-loop operation outside MCP scope.
- `send_direct_cli_command` is asynchronous. Poll `get_job_group` (or `search_job_groups`) for status, then call `get_cli_command_output` with the same `job_group_id` + `device_id` for the actual output text, `get_job_group` alone never returns it.
- If the authenticated account is a Percepxion Project Admin, `organization_id` is required (not optional) on `send_direct_cli_command`, `get_cli_command_output`, and most other job/telemetry/content/audit tools, see Workflow 1 Step 3 and Platform Security Configuration.
- Read-only by default (`PERCEPXION_CLI_WRITE_ENABLED=false`). Write commands require server reconfiguration. The AI cannot bypass CLI policy at runtime.

**Firmware updates (OOB devices)**
- `update_firmware_by_smart_group` requires a local firmware file (`firmware_file_path`) and targets `smart_group_ids` (array). Confirm the file path, group membership count, and target version before calling.
- Always track the async job to completion via `get_job_group` or `search_job_groups`.

**Credential provider**
- `reconfigure_credentials` switches the MCP server's credential provider (`env`, `vault`, `aws`), it does NOT rotate per-device passwords. Always follow it with `login_with_env` to re-authenticate.

**Destructive lifecycle operations**
- For `remove_device_from_platform` and `reboot_device`, require the operator to confirm the OOB device hostname before executing.
- `reboot_device` causes temporary loss of serial console access to all managed devices on the OOB device's ports.

**Async tracking**
- `send_direct_cli_command`, `update_firmware_by_smart_group`, `reboot_device`, and `request_device_syslog_upload` are all asynchronous. Never leave a job untracked, always poll to `completed` or `failed` and report the final status.

**Proactive use**
- Firmware compliance reports and config drift checks should run on a schedule, not just during incidents. When a user asks for fleet health, pull `firmware_compliance_report` and `get_device_config` across the fleet without waiting for a problem to surface.

**Automation pipeline preflight (when OOB coverage exists)**
- This rule only applies when Percepxion is available in the session. Before making primary-network changes, search `get_device_list` for the target device hostname or IP. If no OOB device is found, proceed normally, absent OOB coverage is expected and not a blocker. If an OOB device is found, run W2 preflight. A known OOB path that is unreachable is worth flagging before committing the change; an OOB path that simply doesn't exist is not.

**Evidence always (W8 and any automated remediation)**
- Every automated OOB action via W8 must call `get_device_syslogs` before and `investigate_audit_logs` after. This evidence is non-negotiable for compliance and incident closure. Do not skip these steps even if the remediation command fails.
