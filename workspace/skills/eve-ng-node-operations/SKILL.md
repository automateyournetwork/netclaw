---
name: eve-ng-node-operations
description: Manage EVE-NG node lifecycle. Use when listing nodes, checking runtime state, creating or deleting nodes, starting or stopping nodes or whole labs, verifying node details, or wiping node NVRAM back to factory defaults.
user-invocable: true
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["EVE_URL","EVE_USER","EVE_PASSWORD"]}}}
---

# EVE-NG Node Operations

Use this skill for **node lifecycle control**.

## Workflow

1. List or inspect nodes before acting.
2. Before starting or creating nodes, apply `{baseDir}/references/node-guardrails.md`.
3. For node creation choices, check `{baseDir}/references/node-types.md`.
4. Treat `verified: false` start/stop results as incomplete; confirm with status or console.

## Available tools

- `eve_list_nodes`
- `eve_get_node`
- `eve_create_node`
- `eve_delete_node`
- `eve_start_node`
- `eve_stop_node`
- `eve_start_lab`
- `eve_stop_lab`
- `eve_wipe_node`

## Node-ID and runtime-status guardrails

- Preserve existing EVE node IDs; do not renumber or replace node IDs as a workaround unless the user explicitly asks.
- On local EVE, treat node runtime as lab-UUID scoped (`/opt/unetlab/tmp/0/<lab_uuid>/<node_id>`). EVE API status can leak across labs that reuse node IDs, so use MCP-corrected status or verify local runtime before concluding a node is up.
- If a same-ID node in another lab appears UP, fix the runtime/status scoping problem; do not rewrite the lab's node IDs.
