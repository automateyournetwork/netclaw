---
name: eve-ng-config-ops
description: Manage EVE-NG startup configurations stored in lab files. Use when exporting configs natively into the lab, reading embedded startup configs, pushing startup config before boot, clearing config without full NVRAM wipe, or bulk-checking stored configs after lab changes.
user-invocable: true
metadata: {"openclaw":{"requires":{"bins":["python3"],"env":["EVE_URL","EVE_USER","EVE_PASSWORD"]}}}
---

# EVE-NG Config Operations

Use this skill for **startup-config management inside lab files**.

## Workflow

1. Prefer native EVE export tools first for export/backup requests.
2. Read `{baseDir}/references/config-guardrails.md` before export, push, or wipe work.
3. Use summaries first; read full config text only when needed.
4. Stop nodes before writing or clearing startup config.

## Available tools

- `eve_get_node_config`
- `eve_export_node_config`
- `eve_set_node_config`
- `eve_set_node_startup_mode`
- `eve_export_all_node_configs`
- `eve_list_config_summaries`
- `eve_get_all_configs`
- `eve_wipe_node_config`
