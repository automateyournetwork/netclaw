# Quickstart: UE5 Network Visualization Development

**Feature**: 044-ue5-mcp-network-viz
**Date**: 2026-06-28

## Prerequisites

### Required Software

1. **Unreal Engine 5.8+**
   - Download from [unrealengine.com](https://www.unrealengine.com) via Epic Games Launcher
   - Free for internal/non-commercial use

2. **NetClaw Environment**
   - Python 3.10+
   - NetClaw workspace configured

3. **Network Data Source** (at least one)
   - pyATS with CDP/LLDP data
   - SuzieQ with topology
   - GNS3/CML lab

### System Requirements

- **GPU**: Discrete GPU recommended (NVIDIA RTX 3060+ or AMD equivalent)
- **RAM**: 32GB+ recommended for UE5
- **Storage**: ~100GB for UE5 installation
- **OS**: Windows 10/11 (UE Editor), WSL2 (NetClaw) or native Linux

## Setup

### Step 1: Enable UE5 MCP Plugin

1. Launch Unreal Engine 5.8
2. Create or open a project
3. Go to **Edit > Plugins**
4. Search for "**Unreal MCP**" (or "ModelContextProtocol")
5. Enable the plugin
6. Restart the editor when prompted

### Step 2: Configure Auto-Start

1. Go to **Edit > Editor Preferences**
2. Navigate to **General > Model Context Protocol**
3. Enable **Auto Start Server**
4. Verify settings:
   - Port: `8000` (default)
   - URL Path: `/mcp` (default)

### Step 3: Verify MCP Server Running

Open the editor console (` key) and run:
```
ModelContextProtocol.StartServer
```

You should see:
```
LogModelContextProtocol: MCP server started on http://127.0.0.1:8000/mcp
```

### Step 4: Test Connectivity

From WSL/terminal, verify the server is reachable:

```bash
# Simple connectivity test
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

Expected response: JSON with available tools or meta-tools.

### Step 5: Configure NetClaw

Add to `.env`:
```bash
# UE5 MCP Server
UE5_MCP_URL=http://127.0.0.1:8000/mcp
```

The MCP server registration in `config/openclaw.json` should include:
```json
{
  "unreal-mcp": {
    "url": "${UE5_MCP_URL:-http://127.0.0.1:8000/mcp}"
  }
}
```

## Development Workflow

### Running Integration Tests

Tests require UE5 running with MCP enabled:

```bash
# Start UE5 first, then run tests
cd /home/johncapobianco/netclaw
pytest tests/integration/test_ue5_mcp.py -v
```

### Manual Testing

1. Start UE5 with a blank level
2. Ensure MCP server is running (check console)
3. Run the skill:
   ```
   "Render my network in UE5"
   ```
4. Observe actors spawning in the viewport

### Debugging Tips

**MCP Inspector**: Use the official MCP Inspector for debugging:
```bash
npx @modelcontextprotocol/inspector
```
Point it at `http://127.0.0.1:8000/mcp`.

**UE5 Console Commands**:
```
ModelContextProtocol.StartServer      # Start MCP server
ModelContextProtocol.StopServer       # Stop MCP server
ModelContextProtocol.RefreshTools     # Reload toolsets after changes
```

**Log Verbosity**:
```
Log LogModelContextProtocol Verbose
```

### WSL to Windows Connectivity

If running NetClaw in WSL2 and UE5 on Windows:

1. UE5 MCP binds to `127.0.0.1` by default
2. From WSL, `localhost` should reach Windows via WSLg
3. If not working, use Windows host IP:
   ```bash
   WIN_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
   export UE5_MCP_URL="http://${WIN_IP}:8000/mcp"
   ```

## Quick Commands

### Test Basic Actor Spawning

```python
# In Python REPL with MCP client
import httpx
import json

url = "http://127.0.0.1:8000/mcp"

# List toolsets
response = httpx.post(url, json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "list_toolsets",
        "arguments": {}
    },
    "id": 1
})
print(response.json())

# Spawn a test cube
response = httpx.post(url, json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "call_tool",
        "arguments": {
            "toolset": "ActorTools",
            "tool": "spawn_actor",
            "args": {
                "class": "/Engine/BasicShapes/Cube.Cube",
                "name": "test_cube",
                "location": [0, 0, 100],
                "scale": [50, 50, 50]
            }
        }
    },
    "id": 2
})
print(response.json())
```

### Clear Test Actors

```python
# Remove all netclaw actors
response = httpx.post(url, json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "call_tool",
        "arguments": {
            "toolset": "SceneTools",
            "tool": "clear_actors_with_tag",
            "args": {"tag": "netclaw"}
        }
    },
    "id": 3
})
```

## Directory Structure

After implementation, the feature adds:

```
netclaw/
├── workspace/skills/ue5-network-viz/
│   └── SKILL.md                    # Skill documentation
├── config/openclaw.json            # MCP server registration (modified)
├── .env.example                    # Environment variables (modified)
├── SOUL.md                         # Skill definition (modified)
├── README.md                       # Feature documentation (modified)
├── scripts/install.sh              # UE5 setup instructions (modified)
└── specs/044-ue5-mcp-network-viz/  # This feature's docs
```

## Common Issues

### "MCP server not reachable"
- Verify UE5 is running
- Check MCP plugin is enabled
- Run `ModelContextProtocol.StartServer` in UE5 console
- Verify port 8000 is not blocked

### "Tool not found"
- Run `ModelContextProtocol.RefreshTools` in UE5 console
- Verify AllToolsets plugin is enabled

### "Actor not appearing"
- Check the viewport is focused on world origin
- Verify scale is large enough (UE5 uses centimeters, so 50+ for visibility)
- Check Output Log for errors

### Slow first command
- Normal behavior - first MCP command may timeout
- Subsequent commands are faster
- Increase timeout in client if needed

## Next Steps

1. Run the test suite to verify setup
2. Try basic rendering with test topology
3. Implement layout algorithm
4. Add material/color support
5. Implement incremental updates
6. Add telemetry integration
