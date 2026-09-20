---
name: splunk-saved
description: "Manage and run saved searches in Splunk."
version: 1.0.0
license: Apache-2.0
author: netclaw
tags: []
---

# Splunk Saved Searches Skill

Manage and run saved searches in Splunk.

## Tools

| Tool | Description |
|------|-------------|
| `get_saved_searches` | List all saved searches |
| `run_saved_search` | Execute a saved search by name |

## Example Queries

```
List all saved searches

Run the "Network Health Summary" saved search

Show saved searches in the network app
```

## Prerequisites

- `SPLUNK_HOST` Splunk server hostname
- `SPLUNK_PORT` Management port (default: 8089)
- `SPLUNK_USERNAME` Service account username
- `SPLUNK_PASSWORD` Service account password

## Server

This skill uses the `splunk-mcp` server via npx.

## Failure Behavior

- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
