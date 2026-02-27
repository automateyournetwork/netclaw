---
name: junos-network
description: "Juniper JunOS device automation via PyEZ/NETCONF — CLI execution, configuration management, Jinja2 template rendering, device facts, batch operations, config diff and rollback comparison (10 tools)"
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["JUNOS_DEVICES_FILE"] } } }
---

# Juniper JunOS Network Automation

Manage Juniper devices through the JunOS MCP server powered by PyEZ over NETCONF. Execute CLI commands, retrieve and push configurations, render Jinja2 templates, gather device facts, compare rollback configs, and operate across multiple routers in parallel.

## MCP Server

| Field | Value |
|-------|-------|
| **Repository** | [Juniper/junos-mcp-server](https://github.com/Juniper/junos-mcp-server) |
| **Transport** | stdio (default for CLI), streamable-http (for IDE) |
| **Python** | 3.10+ (3.11 recommended) |
| **Protocol** | SSH → NETCONF → PyEZ (junos-eznc) |
| **Dependencies** | `junos-eznc>=2.7.4`, `jxmlease>=1.0.3`, `lxml>=6.0.0`, `mcp[cli]>=1.12.2`, `ncclient>=0.6.15`, `paramiko>=3.5.1` |
| **Install** | `git clone` + `pip install -r requirements.txt` or `pip install .` |
| **Entry Point** | `junos-mcp-server -f devices.json -t stdio` or `python3 jmcp.py -f devices.json -t stdio` |
| **Container** | `docker build -t junos-mcp-server .` (python:3.11-slim based) |

## Device Inventory

Devices are defined in a `devices.json` file (not environment variables):

```json
{
  "core-rtr-01": {
    "ip": "10.0.0.1",
    "port": 22,
    "username": "netops",
    "auth": {
      "type": "ssh_key",
      "private_key_path": "/home/user/.ssh/junos_key"
    }
  },
  "edge-rtr-02": {
    "ip": "10.0.0.2",
    "port": 22,
    "username": "admin",
    "auth": {
      "type": "password",
      "password": "changeme"
    }
  }
}
```

SSH key authentication is strongly recommended for production. Jumphost/ProxyCommand is supported via `ssh_config` field.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `JUNOS_DEVICES_FILE` | `devices.json` | Path to device inventory JSON |
| `JUNOS_TIMEOUT` | `360` | Default command timeout in seconds |

---

## Tools (10)

### Device Inventory (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_router_list` | — | List all available Junos routers (passwords/keys filtered from output) |
| `add_device` | `device_name?`, `device_ip?`, `device_port?`, `username?`, `ssh_key_path?` | Add a new Junos device interactively (streamable-http only) |
| `reload_devices` | `file_name` | Reload the device dictionary from a new JSON file |

### CLI Execution (2 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `execute_junos_command` | `router_name`, `command`, `timeout?` | Execute a JunOS CLI command on a single router |
| `execute_junos_command_batch` | `router_names`, `command`, `timeout?` | Execute the same command on multiple routers in parallel |

### Configuration Management (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_junos_config` | `router_name` | Retrieve the full running configuration (`show configuration \| display set`) |
| `junos_config_diff` | `router_name`, `version?` | Compare current config against a rollback version (1-49) |
| `load_and_commit_config` | `router_name`, `config_text`, `config_format?`, `commit_comment?` | Load and commit configuration (formats: set, text, xml) |

### Template & Facts (2 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `render_and_apply_j2_template` | `template_content`, `vars_content`, `router_name?`, `router_names?`, `apply_config?`, `dry_run?`, `commit_comment?` | Render Jinja2 template with YAML variables; optionally apply to one or many routers with dry-run support |
| `gather_device_facts` | `router_name`, `timeout?` | Gather device facts: hostname, model, serial, version, uptime, RE info |

---

## Safety Features

### Command Blocklist (`block.cmd`)
The server ships with a blocklist that prevents destructive CLI commands:
- `request system reboot`
- `request system halt`
- `request system power-cycle`
- `request system power-off`
- `request system zeroize`

Custom patterns (regex) can be added to `block.cmd`.

### Configuration Blocklist (`block.cfg`)
Prevents dangerous configuration changes:
- `set system root-authentication` — blocks root password changes
- `set system login user ... authentication` — blocks user credential changes

Custom patterns (regex) can be added to `block.cfg`.

### Credential Filtering
`get_router_list` automatically strips passwords and SSH key paths before returning device data.

---

## Workflows

### 1. JunOS Device Discovery
```
get_router_list → inventory all available Junos routers
→ gather_device_facts(router) per device → hostname, model, serial, version, uptime
→ Cross-reference with NetBox/Nautobot → flag discrepancies
→ GAIT
```

### 2. JunOS Health Check
```
get_router_list → identify target routers
→ execute_junos_command_batch(routers, "show chassis alarms") → alarm check
→ execute_junos_command_batch(routers, "show system processes extensive") → CPU/memory
→ execute_junos_command_batch(routers, "show interfaces terse") → interface status
→ execute_junos_command_batch(routers, "show bgp summary") → BGP peer health
→ Severity-sort findings → GAIT
```

### 3. JunOS Configuration Audit
```
get_router_list → select target routers
→ get_junos_config(router) → retrieve running config
→ junos_config_diff(router, version=1) → check for uncommitted or recent changes
→ Compare against golden config templates → flag deviations
→ GAIT
```

### 4. JunOS Configuration Deployment
```
ServiceNow CR must be in Implement state
→ get_junos_config(router) → baseline current config
→ render_and_apply_j2_template(template, vars, router, dry_run=true) → preview changes
→ render_and_apply_j2_template(template, vars, router, apply_config=true, commit_comment="CR-12345") → apply
→ get_junos_config(router) → verify post-change config
→ execute_junos_command(router, "show bgp summary") → verify protocol health
→ GAIT
```

### 5. JunOS Batch Operations
```
get_router_list → filter to target group (e.g., all edge routers)
→ execute_junos_command_batch(routers, "show version") → version inventory
→ execute_junos_command_batch(routers, "show ospf neighbor") → protocol health
→ Aggregate results → severity-sort → GAIT
```

### 6. JunOS Rollback Investigation
```
junos_config_diff(router, version=1) → compare against last committed config
→ junos_config_diff(router, version=2) → compare against version before that
→ Identify what changed, when, and the impact
→ execute_junos_command(router, "show system commit") → commit history
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-network** | JunOS MCP for Juniper devices, pyATS MCP for Cisco devices — unified multi-vendor fleet management |
| **netbox-reconcile** | Cross-reference JunOS device facts (model, serial, version) against NetBox source of truth |
| **nautobot-sot** | Same as NetBox — validate Juniper device IPAM data in Nautobot |
| **infrahub-sot** | Cross-reference Infrahub node data with Juniper device inventory |
| **itential-automation** | Itential workflows can orchestrate JunOS config deployments; Junos command templates complement Itential's |
| **servicenow-change-workflow** | Gate all JunOS config commits behind ServiceNow Change Requests |
| **gait-session-tracking** | Every JunOS command, config push, and batch operation logged in GAIT |
| **nso-device-ops** | NSO for multi-vendor orchestration, JunOS MCP for direct Juniper device access |
| **te-network-monitoring** | Validate network health via ThousandEyes after JunOS config changes |
| **fmc-firewall-ops** | Correlate Juniper ACL/firewall-filter config with Cisco FMC security policies |
| **subnet-calculator** | VLSM planning for Juniper interface addressing |
| **nvd-cve** | Scan Junos OS versions against NVD vulnerability database |

---

## JunOS MCP vs pyATS MCP

| Capability | JunOS MCP | pyATS MCP |
|-----------|-----------|-----------|
| **Vendor** | Juniper only | Cisco (IOS-XE, NX-OS, IOS-XR) |
| **Protocol** | NETCONF via PyEZ | SSH + Genie parsers |
| **CLI Execution** | `execute_junos_command` | `pyats_run_command` |
| **Batch Operations** | `execute_junos_command_batch` (native parallel) | `pyats_pcall` (parallel pCall) |
| **Config Retrieval** | `get_junos_config` (set format) | `pyats_run_command("show run")` |
| **Config Push** | `load_and_commit_config` (NETCONF commit) | `pyats_configure_device` (SSH configure terminal) |
| **Template Support** | Built-in Jinja2 rendering + apply | External (Jinja2 → configure) |
| **Config Diff** | `junos_config_diff` (rollback compare) | Manual diff via show commands |
| **Device Facts** | `gather_device_facts` (PyEZ facts) | `pyats_learn("platform")` |
| **Safety** | `block.cmd` + `block.cfg` regex blocklists | Built-in destructive command blocking |
| **MCP Tools** | 10 | 8 |

---

## Guardrails

- **Always call `get_router_list` first** — verify the target device exists before executing commands
- **Always baseline before changes** — call `get_junos_config` before any `load_and_commit_config` or template apply
- **Use dry_run for templates** — set `dry_run=true` on `render_and_apply_j2_template` to preview changes before committing
- **Gate config changes** — all `load_and_commit_config` and `render_and_apply_j2_template(apply_config=true)` calls must have a ServiceNow CR in `Implement` state
- **Use batch for fleet ops** — prefer `execute_junos_command_batch` over looping `execute_junos_command` for multi-router operations
- **Set reasonable timeouts** — default is 360s; reduce for simple show commands, increase for large config operations
- **Include commit comments** — always provide a `commit_comment` referencing the ServiceNow CR number
- **Verify after config pushes** — call `get_junos_config` and protocol-specific show commands after changes
- **Respect the blocklists** — `block.cmd` and `block.cfg` prevent destructive operations; do not bypass them
- **Record in GAIT** — every command, config push, batch operation, and template rendering must be logged
