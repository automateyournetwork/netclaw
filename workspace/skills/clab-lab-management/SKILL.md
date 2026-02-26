---
name: clab-lab-management
description: ContainerLab network lab lifecycle management — authenticate, list, deploy, inspect, execute commands on, and destroy containerized network labs via the ContainerLab API
user-invokable: true
---

# ContainerLab Lab Management

Manage containerized network labs through the ContainerLab API. This skill handles the full lab lifecycle: list existing labs, deploy new topologies, inspect running labs, execute commands on lab nodes, and destroy labs when done.

## MCP Server

- **Command**: `python3 -u $CLAB_MCP_SCRIPT` (stdio transport)
- **Requires**: `CLAB_API_SERVER_URL`, `CLAB_API_USERNAME`, `CLAB_API_PASSWORD` environment variables
- **Auto-authentication**: Every tool call auto-authenticates — no explicit `authenticate` call needed

## How to Call Tools

```bash
python3 $MCP_CALL "python3 -u $CLAB_MCP_SCRIPT" <tool_name> '<args_json>'
```

## Available Tools

| Tool | Parameters | What It Does |
|------|-----------|-------------|
| `authenticate` | `apiServerURL`, `username`, `password` | Manual auth override (optional — auto-auth handles normal usage) |
| `listLabs` | none | List all labs on the ContainerLab server |
| `deployLab` | `topologyContent` (JSON object), `reconfigure` (bool) | Deploy a new lab topology |
| `inspectLab` | `labName`, `details` (bool) | Get lab details, node status, management IPs |
| `execCommand` | `labName`, `command`, `nodeName` (optional) | Execute a command on one or all nodes |
| `destroyLab` | `labName`, `cleanup` (bool), `graceful` (bool) | Destroy a lab and clean up resources |

## Workflow: Deploy a New Lab

When a user wants to create a containerized network lab:

1. **List existing labs**: `listLabs` — check what's already running, avoid name conflicts
2. **Deploy topology**: `deployLab` with a topology JSON object
3. **Inspect lab**: `inspectLab` with `details: true` — verify success, get management IPs
4. **Execute commands**: `execCommand` — run show commands to verify connectivity
5. **Report back**: Tell the user the lab is ready with node names and management IPs

### Example: 2-Node SR Linux Lab

```bash
# List existing labs
python3 $MCP_CALL "python3 -u $CLAB_MCP_SCRIPT" listLabs '{}'

# Deploy
python3 $MCP_CALL "python3 -u $CLAB_MCP_SCRIPT" deployLab '{"topologyContent":{"name":"srlinux-demo","topology":{"nodes":{"srl1":{"kind":"nokia_srlinux","image":"ghcr.io/nokia/srlinux:latest","type":"ixrd2l"},"srl2":{"kind":"nokia_srlinux","image":"ghcr.io/nokia/srlinux:latest","type":"ixrd2l"}},"links":[{"endpoints":["srl1:e1-1","srl2:e1-1"]},{"endpoints":["srl1:e1-2","srl2:e1-2"]}]}}}'

# Inspect
python3 $MCP_CALL "python3 -u $CLAB_MCP_SCRIPT" inspectLab '{"labName":"srlinux-demo","details":true}'

# Execute command
python3 $MCP_CALL "python3 -u $CLAB_MCP_SCRIPT" execCommand '{"labName":"srlinux-demo","nodeName":"srl1","command":"show version"}'
```

## Workflow: Lab Cleanup

When a user is done with a lab:

1. **Confirm with user**: Ask before destroying
2. **Destroy lab**: `destroyLab` with `graceful: true` and `cleanup: true`
3. **Record in GAIT**: Log the destruction for audit trail

```bash
python3 $MCP_CALL "python3 -u $CLAB_MCP_SCRIPT" destroyLab '{"labName":"srlinux-demo","cleanup":true,"graceful":true}'
```

## Topology Design Guidance

ContainerLab topologies define nodes and links in a structured JSON format.

### Supported Node Kinds

ContainerLab supports a wide range of network operating systems:

| Kind | Platform | Example Image |
|------|----------|---------------|
| `cisco_iosxr` | Cisco IOS XR | `ios-xr/xrd-control-plane:latest` |
| `cisco_iosxe` | Cisco IOS XE (Cat8000v) | `c8000v:latest` |
| `cisco_nxos` | Cisco NX-OS (Nexus 9000v) | `n9kv:latest` |
| `cisco_ftdv` | Cisco Firepower FTDv | `ftdv:latest` |
| `nokia_srlinux` | Nokia SR Linux | `ghcr.io/nokia/srlinux:latest` |
| `ceos` | Arista cEOS | `ceos:latest` |
| `juniper_crpd` | Juniper cRPD | `crpd:latest` |
| `frr` | FRRouting | `frrouting/frr:latest` |
| `linux` | Generic Linux | `alpine:latest` |

For the full list, see the [ContainerLab documentation](https://containerlab.dev/manual/kinds/).

### Basic Topology Structure

```json
{
  "name": "lab-name",
  "topology": {
    "nodes": {
      "node1": {
        "kind": "nokia_srlinux",
        "image": "ghcr.io/nokia/srlinux:latest"
      },
      "node2": {
        "kind": "nokia_srlinux",
        "image": "ghcr.io/nokia/srlinux:latest"
      }
    },
    "links": [
      {"endpoints": ["node1:e1-1", "node2:e1-1"]}
    ]
  }
}
```

### Common Lab Patterns

**Multi-vendor lab:**
```
"Deploy a 4-node lab:
- 2 x SR Linux switches (leaf1, leaf2)
- 1 x FRR router (spine1)
- 1 x Linux host (client1)
- leaf1 and leaf2 connected to spine1
- client1 connected to leaf1"
```

**Spine-leaf fabric:**
```
"Build a 2-spine, 4-leaf SR Linux fabric:
- Full mesh between spines and leaves
- iBGP between all nodes"
```

## Integration with Other Skills

- Use **gait-session-tracking** to record all lab operations in the audit trail
- Use **markmap-viz** to visualize lab topologies as interactive mind maps
- Use **drawio-diagram** for lab network diagrams

## Important Rules

- **Lab-only operations** — ContainerLab operations are lab-only. No ServiceNow CR gating required
- **GAIT audit mandatory** — Record all lab operations in the GAIT audit trail
- **List before deploy** — Always list existing labs before deploying to avoid name conflicts
- **Inspect after deploy** — Always inspect after deployment to verify success and get management IPs
- **Graceful shutdown** — Use `graceful: true` when destroying labs for clean node shutdown
- **Docker restart** — If the ContainerLab API server runs in Docker and auth fails, the container may need a restart to pick up new Linux users

## Error Handling

- **Auth fails (401)**: Check `CLAB_API_SERVER_URL`, `CLAB_API_USERNAME`, `CLAB_API_PASSWORD` in `~/.openclaw/.env`. If the API server runs in Docker, restart the container after creating the Linux user
- **Deploy fails**: Check topology syntax — nodes must have valid `kind` and `image` fields. Use `listLabs` to check for name conflicts
- **Exec fails**: Verify the lab is deployed via `inspectLab`. Check node name is correct
- **Destroy fails**: Verify lab name via `listLabs`. If graceful shutdown times out, retry without `graceful: true`

## Environment Variables

- `CLAB_API_SERVER_URL` — ContainerLab API server URL (e.g., http://localhost:8080)
- `CLAB_API_USERNAME` — API username (default: netclaw)
- `CLAB_API_PASSWORD` — API password
- `CLAB_MCP_SCRIPT` — Path to the Python MCP server script (set by install.sh)
- `MCP_CALL` — Path to mcp-call.py wrapper (set by install.sh)
