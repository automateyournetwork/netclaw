# Splunk Indexes Skill

Discover and inspect Splunk indexes and configuration.

## Tools

| Tool | Description |
|------|-------------|
| `get_indexes` | List all available indexes |
| `get_config` | Get Splunk server configuration |

## Example Queries

```
List all Splunk indexes

What indexes contain network data?

Show Splunk server configuration
```

## Prerequisites

- `SPLUNK_HOST` Splunk server hostname
- `SPLUNK_PORT` Management port (default: 8089)
- `SPLUNK_USERNAME` Service account username
- `SPLUNK_PASSWORD` Service account password

## Server

This skill uses the `splunk-mcp` server via npx.
