# Quickstart: IP Fabric MCP Integration

**Time to complete**: 5 minutes
**Prerequisites**: IP Fabric appliance with MCP Server enabled, API token

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] IP Fabric appliance running (v6.0+)
- [ ] MCP Server enabled in IP Fabric (Settings → Integration → MCP Server)
- [ ] API token with appropriate RBAC permissions
- [ ] Network connectivity from NetClaw host to IP Fabric appliance (HTTPS/443)
- [ ] Node.js 18+ installed (for mcp-remote proxy)

## Step 1: Generate API Token (2 minutes)

1. Log into your IP Fabric appliance web UI
2. Navigate to **Settings** → **API Tokens**
3. Click **Create New Token**
4. Set permissions (recommend: Read-only for initial testing)
5. Copy the token immediately (it's only shown once)

## Step 2: Run Enable Script (1 minute)

For existing NetClaw installations:

```bash
cd ~/netclaw
./scripts/ipfabric-enable.sh
```

You'll be prompted for:
- **IP Fabric host URL**: e.g., `https://ipfabric.example.com`
- **API token**: The token you copied in Step 1

The script will:
1. Add environment variables to `~/.openclaw/.env`
2. Register the MCP server in `~/.openclaw/openclaw.json`
3. Reload the OpenClaw gateway

## Step 3: Verify Connection (1 minute)

Test the connection:

```bash
# List registered MCP servers
openclaw mcp list | grep ipfabric

# Should show:
# ipfabric-mcp    remote    https://your-host/mcp
```

## Step 4: Test with a Query (1 minute)

Open NetClaw and try:

```
/ipfabric check network health
```

Expected response:
- Snapshot information
- Device count
- Intent verification summary
- Routing protocol status

## Quick Reference

### Common Queries

| Query | What it does |
|-------|--------------|
| `check network health` | Overall health assessment |
| `show path from 10.0.1.5 to 10.0.2.10` | Trace unicast path |
| `trace route with diagram` | Path lookup with PNG visualization |
| `show BGP neighbors not Established` | BGP troubleshooting |
| `are there any intent violations` | Compliance check |

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `IPFABRIC_HOST` | IP Fabric appliance URL |
| `IPFABRIC_API_TOKEN` | API authentication token |

### Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect" | Verify `IPFABRIC_HOST` URL and network connectivity |
| "Authentication failed" | Regenerate API token in IP Fabric UI |
| "Permission denied" | Check RBAC permissions on API token |
| "Snapshot not found" | Run a new discovery in IP Fabric |

## Manual Configuration (Alternative)

If you prefer manual setup:

### 1. Add to .env

```bash
echo "IPFABRIC_HOST=https://ipfabric.example.com" >> ~/.openclaw/.env
echo "IPFABRIC_API_TOKEN=your-token-here" >> ~/.openclaw/.env
```

### 2. Add to openclaw.json

Add to `~/.openclaw/openclaw.json` under `mcp.servers`:

```json
{
  "ipfabric-mcp": {
    "command": "npx",
    "args": [
      "-y",
      "mcp-remote",
      "${IPFABRIC_HOST}/mcp",
      "--header",
      "Authorization:${IPFABRIC_AUTH_HEADER}"
    ],
    "env": {
      "IPFABRIC_AUTH_HEADER": "Bearer ${IPFABRIC_API_TOKEN}"
    }
  }
}
```

### 3. Restart Gateway

```bash
systemctl --user restart openclaw-gateway.service
```

## Next Steps

- Read the full guide: [docs/IPFABRIC.md](../../docs/IPFABRIC.md)
- Explore the skill: [workspace/skills/ipfabric/SKILL.md](../../workspace/skills/ipfabric/SKILL.md)
- Try path diagrams: Ask for any path "with diagram"
- Compose with other skills: Combine IP Fabric data with SuzieQ, Batfish, or Check Point

---

*This integration was developed in collaboration with Daren Fulwell (Field CTO, IP Fabric) and John Capobianco (Creator, NetClaw).*
