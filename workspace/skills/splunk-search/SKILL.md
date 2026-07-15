---
name: splunk-search
description: "Execute and validate SPL (Search Processing Language) queries."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Splunk Search Skill

Execute and validate SPL (Search Processing Language) queries.

## Tools

| Tool | Description |
|------|-------------|
| `validate_spl` | Validate SPL syntax without executing |
| `search_oneshot` | Execute SPL query and return results |
| `search_export` | Execute SPL query and export to file |

## Output Format

Results are formatted as **Markdown tables** for easy reading. Sensitive fields are automatically sanitized.

## Example Queries

```
Validate this SPL: index=network sourcetype=syslog | stats count by host

Search for all firewall denies in the last hour

Export BGP peer events from the network index
```

## SPL Tips

- Use `earliest=-1h` for time ranges
- Use `| table field1, field2` to select columns
- Use `| stats count by field` for aggregations

## Prerequisites

- `SPLUNK_HOST` Splunk server hostname
- `SPLUNK_PORT` Management port (default: 8089)
- `SPLUNK_USERNAME` Service account username
- `SPLUNK_PASSWORD` Service account password

## Server

This skill uses the `splunk-mcp` server via npx.
