# Zabbix MCP Server

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![SafeSkill](https://safeskill.dev/api/badge/mpeirone-zabbix-mcp-server)](https://safeskill.dev/scan/mpeirone-zabbix-mcp-server)


A lightweight Model Context Protocol (MCP) server that provides **complete access to the entire Zabbix API** through just 3 tools. Compatible with **Zabbix 6.0+**.

<a href="https://glama.ai/mcp/servers/@mpeirone/zabbix-mcp-server">
<img width="380" height="200" src="https://glama.ai/mcp/servers/@mpeirone/zabbix-mcp-server/badge" alt="zabbix-mcp-server MCP server" />
</a>

## Why Zabbix MCP Server?

- **Complete API Coverage** - Access every Zabbix API method (100+) through a unified interface
- **Lightweight Context** - Only 3 tools instead of 50+ individual tools, keeping LLM context minimal
- **Always Up-to-Date** - Works with current and future Zabbix API methods automatically
- **Zabbix 6.0+ Compatible** - Supports Zabbix 6.0, 6.4, 7.0, and newer versions

## The 3 Tools

| Tool | Purpose |
|------|---------|
| `zabbix_api` | Execute any Zabbix API method |
| `zabbix_api_docs` | Get documentation for any API method |
| `zabbix_api_list` | Discover available API objects and methods |

## Quick Start

### Option 1: Claude Code Integration

Add to your Claude Code MCP configuration:

```bash
claude mcp add zabbix \
  --env ZABBIX_URL=https://your-zabbix-server.com \
  --env ZABBIX_TOKEN=your_api_token \
  -- uvx --from git+https://github.com/mpeirone/zabbix-mcp-server@main zabbix-mcp
```

### Option 2: Run with uv

```bash
git clone https://github.com/mpeirone/zabbix-mcp-server.git
cd zabbix-mcp-server
uv sync

# Configure environment
export ZABBIX_URL=https://your-zabbix-server.com
export ZABBIX_TOKEN=your_api_token

# Start the server
uv run python scripts/start_server.py
```

### Test Connection

```bash
uv run python scripts/test_server.py
```

## Option 3: Run with docker

```bash
git clone https://github.com/mpeirone/zabbix-mcp-server.git
cd zabbix-mcp-server

# Using docker-compose
docker compose up -d

# Or build manually
docker build -t zabbix-mcp-server .
docker run -e ZABBIX_URL=https://zabbix.example.com -e ZABBIX_TOKEN=your_token zabbix-mcp-server
```

## Environment Variables

### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `ZABBIX_URL` | Zabbix server URL | `https://your-zabbix-server.com` |

### Authentication (choose one)

| Variable | Description |
|----------|-------------|
| `ZABBIX_TOKEN` | API token (recommended) |
| `ZABBIX_USER` + `ZABBIX_PASSWORD` | Username and password |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `READ_ONLY` | `false` | Set to `true` to allow only read operations |
| `VERIFY_SSL` | `true` | Enable/disable SSL verification |
| `ZABBIX_API_WHITELIST` | `.*` | Comma-separated regex patterns for allowed API methods |
| `ZABBIX_API_BLACKLIST` | (empty) | Comma-separated regex patterns for blocked API methods |
| `ZABBIX_SKIP_VERSION_CHECK` | `false` | Skip Zabbix version compatibility check |
| `ZABBIX_API_TIMEOUT` | `30` | API request timeout in seconds |

### Transport

| Variable | Default | Description |
|----------|---------|-------------|
| `ZABBIX_MCP_TRANSPORT` | `stdio` | Transport type: `stdio` or `streamable-http` |
| `ZABBIX_MCP_HOST` | `127.0.0.1` | HTTP server host (when using `streamable-http`) |
| `ZABBIX_MCP_PORT` | `8000` | HTTP server port (when using `streamable-http`)|
| `ZABBIX_MCP_STATELESS_HTTP` | `false` | Stateless HTTP mode |
| `AUTH_TYPE` | - | Must be `no-auth` for HTTP transport (when using `streamable-http`) |

### Debug

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Set to `true` for verbose logging |

## Usage Examples

### Get Hosts

```python
zabbix_api(method='host.get', params={'output': ['hostid', 'name']})
```

### Get Problems

```python
zabbix_api(method='problem.get', params={'output': 'extend', 'recent': True})
```

### Create Host

```python
zabbix_api(method='host.create', params={
    'host': 'server-01',
    'groups': [{'groupid': '1'}],
    'interfaces': [{'type': 1, 'main': 1, 'useip': 1, 'ip': '192.168.1.100', 'port': '10050'}]
})
```

### Get Method Documentation

```python
zabbix_api_docs(method='host.create')
```

### List Available Methods

```python
zabbix_api_list()              # All objects and methods
zabbix_api_list(object='host')  # Host methods only
```

## Security Features

### Read-Only Mode

Set `READ_ONLY=true` to block all write operations:

```bash
export READ_ONLY=true
```

Only `get`, `version`, `check`, and `export` operations will be allowed.

### API Method Filtering

Control which API methods can be called using whitelist/blacklist patterns:

```bash
# Allow only host.* and item.get methods
export ZABBIX_API_WHITELIST="host\..*,item\.get"

# Block all delete and create operations
export ZABBIX_API_BLACKLIST=".*\.delete,.*\.create"
```

Both support comma-separated regex patterns. Blacklist is checked first.

## MCP Client Configuration

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "zabbix": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/mpeirone/zabbix-mcp-server@main", "zabbix-mcp"],
      "env": {
        "ZABBIX_URL": "https://zabbix.example.com",
        "ZABBIX_TOKEN": "your_api_token"
      }
    }
  }
}
```

## Troubleshooting

### Connection Issues

- Verify `ZABBIX_URL` is accessible
- Check authentication credentials
- Ensure Zabbix API is enabled

### Permission Errors

- Verify Zabbix user permissions
- Check if `READ_ONLY` mode is enabled

### Method Blocked

If you see "Method is not in whitelist" or "Method is blacklisted":
- Review `ZABBIX_API_WHITELIST` and `ZABBIX_API_BLACKLIST` patterns
- Ensure your regex patterns match the full method name (e.g., `host.get`)

### Debug Mode

```bash
export DEBUG=true
uv run python scripts/start_server.py
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## License

GPLv3 License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Zabbix](https://www.zabbix.com/) - Monitoring platform
- [Model Context Protocol](https://modelcontextprotocol.io/) - Integration standard
- [FastMCP](https://github.com/PrefectHQ/fastmcp) - MCP framework
- [python-zabbix-utils](https://github.com/zabbix/python-zabbix-utils) - Official Zabbix Python library
