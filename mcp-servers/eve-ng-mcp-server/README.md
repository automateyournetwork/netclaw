# EVE-NG MCP Server

MCP server for managing EVE-NG network lab environments. Provides natural language control over lab files, nodes, virtual networks, topology wiring, telnet console execution, and startup configuration management.

## Features

- **Lab Lifecycle**: List, inspect, create, delete, export, and import `.unl` lab files
- **Node Operations**: Add/remove nodes from templates, start/stop individual nodes or whole labs, wipe to factory defaults
- **Network & Topology**: Create virtual bridges, wire node interfaces to networks, inspect full topology
- **Console Execution**: Full telnet console access for IOS/IOL, Junos, VPCS, Arista EOS, and NX-OS — mode-aware with automatic bootstrap
- **Config Management**: Read, push, and clear node startup configs; bulk-export all configs before changes
- **GCF Encoding**: Structured responses are encoded in GCF format with graph auto-detection, session dedup, and JSON fallback
- **Caching**: Cookie auth plus short-lived GET response caching with automatic invalidation after writes
- **Pagination**: High-cardinality list/read tools support `page` and `page_size`
- **System**: EVE-NG status, available images, authentication check

## Prerequisites

- EVE-NG Community or Professional (tested on Community 6.x)
- Python 3.10+
- Network access to the EVE-NG host API (`/api/`) and console ports (`32768+`)
- Valid EVE-NG credentials

## Installation

```bash
cd mcp-servers/eve-ng-mcp-server

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your EVE-NG host details
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EVE_URL` | Yes | `http://127.0.0.1` | EVE-NG base URL (no trailing slash) |
| `EVE_USER` | Yes | - | EVE-NG username |
| `EVE_PASSWORD` | Yes | - | EVE-NG password |
| `EVE_VERIFY_SSL` | No | `true` | Verify TLS certificate (set `false` for self-signed) |
| `EVE_SESSION_TTL` | No | `1800` | Session cookie TTL in seconds (30 min default) |
| `EVE_HTML5` | No | `-1` | Login html5 flag (`-1` = auto, `0` = Java, `1` = HTML5) |
| `EVE_CONSOLE_HOST` | No | `127.0.0.1` | Host for telnet console connections — set to EVE host IP when running MCP server off-host |
| `EVE_CONSOLE_USER` | No | - | Optional guest console username for platforms that prompt on login |
| `EVE_CONSOLE_PASSWORD` | No | - | Optional guest console password |
| `EVE_CACHE_TTL` | No | `30` | GET response cache TTL in seconds |
| `EVE_CACHE_MAX_ENTRIES` | No | `256` | Maximum cached GET responses before oldest eviction |
| `EVE_MAX_PAGE_SIZE` | No | `200` | Upper bound for `page_size` on paginated tools |

### Auth Notes

EVE-NG uses **cookie-based sessions**, not Bearer tokens. The client logs in once, caches the session cookie, and re-authenticates automatically when the session expires or returns 401/412.

## Usage

### As MCP Server (stdio transport)

```bash
python3 -u eve_ng_mcp_server.py
```

### Register in OpenClaw

Add to `config/openclaw.json`:

```json
{
  "mcpServers": {
    "eve-ng": {
      "command": "python3",
      "args": ["-u", "mcp-servers/eve-ng-mcp-server/eve_ng_mcp_server.py"],
      "env": {
        "EVE_URL": "${EVE_URL}",
        "EVE_USER": "${EVE_USER}",
        "EVE_PASSWORD": "${EVE_PASSWORD}",
        "EVE_CONSOLE_HOST": "${EVE_CONSOLE_HOST}"
      }
    }
  }
}
```

## Available Tools (38)

### System (3 tools)

| Tool | Parameters | Description |
|------|------------|-------------|
| `eve_status` | — | EVE-NG system status: version, CPU, memory, disk |
| `eve_auth` | — | Verify authentication and get current user info |
| `eve_list_images` | `node_type?, page?, page_size?` | List available images, optionally filtered by type (`iol`, `qemu`, `dynamips`) |

### Lab Lifecycle (6 tools)

| Tool | Parameters | Description |
|------|------------|-------------|
| `eve_list_labs` | `folder?, page?, page_size?` | List all labs recursively (default `/`) |
| `eve_get_lab` | `lab_path` | Lab metadata: description, version, author |
| `eve_create_lab` | `name, folder?, description?, version?, author?` | Create a new empty lab |
| `eve_delete_lab` | `lab_path` | Delete lab and runtime objects |
| `eve_export_lab` | `lab_path` | Export via EVE ZIP package and return extracted raw `.unl` XML + package metadata |
| `eve_import_lab` | `archive_path, folder?` | Upload an EVE export ZIP and import it into the target folder |

### Node Operations (9 tools)

| Tool | Parameters | Description |
|------|------------|-------------|
| `eve_list_nodes` | `lab_path, page?, page_size?` | All nodes with status, type, image, console port |
| `eve_get_node` | `lab_path, node` | Full node details |
| `eve_create_node` | `lab_path, name, node_type, template, image?, left?, top?, ram?, ethernet?, serial?, console?, cpu?, icon?` | Add node from template |
| `eve_delete_node` | `lab_path, node` | Remove a node (stop first) |
| `eve_start_node` | `lab_path, node` | Start node + poll until running |
| `eve_stop_node` | `lab_path, node` | Stop node + poll until stopped |
| `eve_start_lab` | `lab_path` | Start all nodes, return per-node results |
| `eve_stop_lab` | `lab_path` | Stop all nodes, return per-node results |
| `eve_wipe_node` | `lab_path, node` | Factory reset — clear NVRAM (stop first) |

Nodes can be referenced by **name** (`R1`) or **numeric ID** — resolution is case-insensitive.

### Network & Topology (7 tools)

| Tool | Parameters | Description |
|------|------------|-------------|
| `eve_get_topology` | `lab_path` | Full topology: nodes, networks, link connections |
| `eve_list_networks` | `lab_path, page?, page_size?` | All virtual networks with type and ID |
| `eve_create_network` | `lab_path, name, network_type?, visibility?, left?, top?` | Create a virtual network |
| `eve_delete_network` | `lab_path, network` | Delete a network |
| `eve_list_node_interfaces` | `lab_path, node` | Node interfaces and their current network connections |
| `eve_connect_interface` | `lab_path, node, interface_id, network` | Wire node interface to a network |
| `eve_list_node_types` | `page?, page_size?` | All node templates installed on EVE-NG |

#### Network Types

| `network_type` | Description |
|---|---|
| `bridge` | Internal L2 bridge — isolated between nodes |
| `ovs` | Open vSwitch bridge |
| `pnet0`–`pnet9` | Physical uplink to EVE host interfaces |
| `cloud0`–`cloud9` | Cloud/internet bridge mapped to host interfaces |

### Console Execution (6 tools)

| Tool | Parameters | Description |
|------|------------|-------------|
| `eve_discover_node` | `lab_path, node` | Resolve node → console host:port + running status |
| `eve_exec_ios` | `lab_path, node, commands, config_mode?, save?, command_timeout?, wait?` | IOS / IOL / IOS-XE console |
| `eve_exec_junos` | `lab_path, node, commands, command_timeout?, wait?` | Junos operational mode |
| `eve_exec_vpcs` | `lab_path, node, commands, command_timeout?, dhcp_timeout?, prompt_timeout?` | VPCS console |
| `eve_exec_eos` | `lab_path, node, commands, config_mode?, save?, command_timeout?, wait?` | Arista EOS console |
| `eve_exec_nxos` | `lab_path, node, commands, config_mode?, save?, command_timeout?, wait?` | Cisco NX-OS console |

#### OS Console Behavior

| OS | Prompt detection | Auto-bootstrap | Pagination |
|---|---|---|---|
| IOS/IOL | `#`, `>`, `(config)#`, `(config-if)#`, `(config-router)#` | Bypasses setup dialog + autoinstall | `terminal length 0` |
| Junos | `>` (op), `[edit]` (config), `%`/`$` (unix) | Login if needed, unix→cli, exit config mode | `set cli screen-length 0` |
| VPCS | `VPCS>` | Waits for prompt | N/A |
| Arista EOS | `#`, `>`, `(config)#`, `(config-XX)#` | Login if needed | `terminal length 0` + `terminal width 512` |
| NX-OS | `#`, `>`, `(config)#`, `(config-XX)#` | Login + setup wizard dismiss | `terminal length 0` + `terminal width 511` |

Console connections go via **raw telnet** to `EVE_CONSOLE_HOST:port`. Default port formula: `32768 + node_id` (overridden by the API `console` field when present).

If a guest prompts for credentials, set `EVE_CONSOLE_USER` and `EVE_CONSOLE_PASSWORD` explicitly instead of relying on baked-in defaults.

### Config Management (7 tools)

| Tool | Parameters | Description |
|------|------------|-------------|
| `eve_get_node_config` | `lab_path, node` | Get stored startup config text plus current startup-config mode for one node |
| `eve_export_node_config` | `lab_path, node` | Export a running node's config into the lab file as startup config |
| `eve_set_node_config` | `lab_path, node, config` | Push startup config text (node must be stopped) |
| `eve_set_node_startup_mode` | `lab_path, node, enabled` | Turn use of the node's stored startup-config ON or OFF at boot |
| `eve_export_all_node_configs` | `lab_path` | Native EVE export of all supported running-node configs into the lab file |
| `eve_list_config_summaries` | `lab_path, page?, page_size?` | Cheap config inventory: existence, mode, and size without reading full config text |
| `eve_get_all_configs` | `lab_path, page?, page_size?` | Read startup-config mode + stored config text for all supported nodes |
| `eve_wipe_node_config` | `lab_path, node` | Clear startup config only (lighter than `eve_wipe_node`) |

## Response Format

Tools return the standard success/error envelope, serialized as **GCF when available** and **pretty JSON on fallback**.

Paginated tools include `count`, `total_count`, and a `pagination` object.

```json
// Success
{
  "success": true,
  "data": { ... },
  "message": "Human-readable summary",
  "count": 5,
  "total_count": 42,
  "pagination": {
    "page": 1,
    "page_size": 5,
    "returned": 5,
    "total_count": 42,
    "total_pages": 9,
    "has_next": true
  }
}

// Error
{
  "success": false,
  "error": "Node 'R99' not found. Available: ['R1', 'R2', 'R3']",
  "error_code": "EVE_NOT_FOUND",
  "status_code": 404
}
```

Use pagination proactively on large environments, for example:

```text
 eve_list_labs(folder="/", page=1, page_size=50)
 eve_list_nodes(lab_path="/ENSLD/7-OSPF.unl", page=1, page_size=25)
 eve_list_config_summaries(lab_path="/ENSLD/7-OSPF.unl", page=1, page_size=25)
```

## Error Codes

| Code | HTTP | Description |
|------|------|-------------|
| `EVE_AUTH_FAILED` | 401 | Wrong credentials |
| `EVE_SESSION_EXPIRED` | 412 | Session cookie expired (auto-retry) |
| `EVE_NOT_FOUND` | 404 | Lab, node, or network doesn't exist |
| `EVE_CONFLICT` | 409 | Name already in use |
| `EVE_VALIDATION` | 400 | Invalid parameters |
| `EVE_SERVER_ERROR` | 500 | EVE-NG internal error |
| `EVE_UNREACHABLE` | — | Cannot connect to EVE-NG host |
| `EVE_CONSOLE_TIMEOUT` | — | Cannot connect to telnet console port |

## Example Commands

```
"Is EVE-NG healthy?"
"What labs do I have?"
"Start the BGP lab"
"Show me the nodes in /Labs/demo.unl"
"Add a vIOS router called R3 to the BGP lab"
"Connect R1 interface 0 to Net12"
"Run 'show ip route' on R1"
"Configure R2 with OSPF and save"
"Export all startup configs from the BGP lab before I change anything"
"Export the triangle lab and import it on the DR EVE host"
"Wipe R1 back to factory and reload it"
```

## Workflow: Build a Lab from Scratch

```
1. eve_create_lab        name=Triangle-OSPF
2. eve_create_node       (x3: R1, R2, R3 — node_type=iol, template=iol)
3. eve_create_network    (x3: Net12, Net23, Net13 — network_type=bridge)
4. eve_connect_interface (wire each router pair through its network)
5. eve_set_node_config   (push pre-built startup configs while nodes are stopped)
6. eve_start_lab         (boot all three nodes)
7. eve_exec_ios          (verify OSPF adjacencies)
```

## Important Constraints

- **Single-user**: This EVE-NG instance is single-user. Do not start a new lab while another is running.
- **Ask before shutdown**: If another running lab would need to be stopped to proceed, ask the user first before shutting it down.
- **Wiring rule**: Stop affected nodes before changing interface connections to avoid stale host bridges.
- **Boot lag**: API may report a node as "running" while it is still booting — use `eve_discover_node` to confirm console readiness.
- **Config write**: `eve_set_node_config` requires the node to be stopped; configs are stored inside the `.unl` file.
- **Startup-config mode matters**: A node can have stored config data in the `.unl` while still booting default if its startup-config mode is `0`/OFF. The per-node startup-config selector must be ON (`1`/Exported) for the config to apply at boot.
- **Native config export**: EVE's native running-config export uses the node/lab `.../export` API actions (same as GUI export-all-configurations) and writes supported startup configs straight into the `.unl` file.
- **Cheap config check first**: prefer `eve_list_config_summaries` when you only need to compare existence, mode, or size. Use `eve_get_all_configs` only when you truly need the full embedded startup-config text.
- **Export/import reality**: EVE exports labs as ZIP archives containing the `.unl`; images are not bundled and must exist separately on the destination host.
- **Startup caveat**: On some hosts, bulk lab start can race after import; sequential per-node start is a valid workaround when the first all-at-once boot is partial.

## Related Skills

| Skill | Focus |
|---|---|
| `eve-ng-lab-management` | Lab CRUD, system status, images |
| `eve-ng-node-operations` | Node lifecycle, start/stop/wipe |
| `eve-lab-topology-build` | Networks, interface wiring, topology inspection |
| `eve-ng-console-ops` | Telnet console execution across all supported OSes |
| `eve-ng-config-ops` | Startup config read/push/clear/bulk-export |
| `eve-lab-topology-design` | Design planning and `.unl` validation |

## Smoke Test

From the repo root:

```bash
python3 mcp-servers/eve-ng-mcp-server/tests/test_eve_skills_smoke.py
```

This validates the EVE skill docs against the MCP server tool set and checks that the UNL validator script launches correctly.

## License

Part of the NetClaw project.
