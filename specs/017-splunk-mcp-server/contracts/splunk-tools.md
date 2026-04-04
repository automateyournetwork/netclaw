# Splunk MCP Tools Contract

**Feature**: 017-splunk-mcp-server | **Date**: 2026-04-04

## Overview

This document defines the tool interface contract for the official Splunk MCP server integration.

## MCP Server Configuration

```json
{
  "splunk-mcp": {
    "command": "npx",
    "args": ["@splunk/mcp-server2", "--transport", "stdio"],
    "env": {
      "SPLUNK_HOST": "${SPLUNK_HOST}",
      "SPLUNK_PORT": "${SPLUNK_PORT}",
      "SPLUNK_USERNAME": "${SPLUNK_USERNAME}",
      "SPLUNK_PASSWORD": "${SPLUNK_PASSWORD}",
      "SPLUNK_VERIFY_SSL": "${SPLUNK_VERIFY_SSL}"
    }
  }
}
```

## Tool Catalog by Skill

### splunk-search (3 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `validate_spl` | read | query | Validation result with risk level |
| `search_oneshot` | read | query, earliest_time?, latest_time?, output_format? | Search results (blocking) |
| `search_export` | read | query, earliest_time?, latest_time?, output_format? | Streamed results (large sets) |

### splunk-indexes (2 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `get_indexes` | read | filter? | Array of index metadata |
| `get_config` | read | - | Server configuration |

### splunk-saved (2 tools)

| Tool | Type | Parameters | Returns |
|------|------|------------|---------|
| `get_saved_searches` | read | app?, owner?, search? | Array of saved searches |
| `run_saved_search` | read | name, earliest_time?, latest_time? | Search results |

## Parameter Details

### search_oneshot / search_export

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | - | SPL query string |
| earliest_time | string | No | -24h | Search start time |
| latest_time | string | No | now | Search end time |
| output_format | enum | No | markdown | markdown, json, csv |

### Time Format Examples

```
-1h          # 1 hour ago
-15m         # 15 minutes ago
-1d@d        # Yesterday at midnight
-7d@w0       # Last Sunday
2026-04-04T00:00:00
```

## Output Format (Markdown Tables)

Default format per user clarification:

```markdown
| _time | host | sourcetype | message |
|-------|------|------------|---------|
| 2026-04-04T10:00:00Z | router-01 | syslog | BGP peer 10.0.0.1 down |
| 2026-04-04T10:01:00Z | switch-01 | syslog | Interface Gi0/1 flapping |
```

## Security Features

### SPL Validation

Automatically blocks:
- `DELETE` commands
- `OUTPUTCSV` to sensitive paths
- Unbounded time ranges
- Known injection patterns

### Output Sanitization

Automatically redacts:
- Credit card numbers (XXXX-XXXX-XXXX-XXXX)
- Social Security Numbers (XXX-XX-XXXX)
- Configurable custom patterns

## Error Responses

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad Request | Invalid SPL syntax |
| 401 | Unauthorized | Invalid credentials |
| 403 | Forbidden | Query blocked by validation |
| 404 | Not Found | Index/saved search not found |
| 503 | Service Unavailable | Splunk unreachable |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SPLUNK_HOST` | Yes | Splunk server hostname |
| `SPLUNK_PORT` | No | Management port (default: 8089) |
| `SPLUNK_USERNAME` | Yes | Authentication username |
| `SPLUNK_PASSWORD` | Yes | Authentication password |
| `SPLUNK_VERIFY_SSL` | No | SSL verification (default: true) |
