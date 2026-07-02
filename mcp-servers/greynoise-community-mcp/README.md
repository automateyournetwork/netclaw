# GreyNoise Community MCP

A minimal MCP server wrapping the **free, no-key** [GreyNoise Community API](https://docs.greynoise.io/reference/getcommunityip).

It answers the single most useful question for perimeter and scan alerts:
**is this source IP benign internet background noise (a known scanner like
Censys or Shodan) or something targeted?** — without a GreyNoise Enterprise key.

## Why this exists

The official GreyNoise MCP and the unified `threatintel-mcp` both use GreyNoise's
**Enterprise** API, which requires a paid key. The Community endpoint is free and
unauthenticated (rate-limited). This server exposes just that endpoint, as one
tool, so NetClaw can classify scan sources at zero cost.

Keeping it to a single tool is deliberate: every MCP tool schema is loaded into
each agent session's context, and NetClaw runs on context-limited models. See
`docs/architecture/skill-context-scoping.md`.

## Tool

| Tool | Description |
|------|-------------|
| `greynoise_community_lookup(ip)` | Returns `{noise, riot, classification, name, link, last_seen}` for an IP. `noise=true` + `classification=benign` + `name=Censys` means routine scanning. |

## Configuration

No key required. Optionally set `GREYNOISE_API_KEY` to raise the Community rate
limit. Example `openclaw.json` entry:

```json
{
  "mcp": {
    "servers": {
      "greynoise-community-mcp": {
        "command": "/home/ubuntu/netclaw/.venv/bin/python",
        "args": ["/home/ubuntu/netclaw/mcp-servers/greynoise-community-mcp/server.py"]
      }
    }
  }
}
```

## Run standalone

```bash
pip install -r requirements.txt
python server.py
```

> Note: this server is currently vendored in-tree. To match the other MCPs
> (git submodules under `mcp-servers/`), push it to its own repository and
> convert it to a submodule.
