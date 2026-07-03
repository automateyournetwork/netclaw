# Config guardrails

## Native export rule
For export/backup requests, use native EVE config export first:
- single node → `eve_export_node_config`
- whole lab → `eve_export_all_node_configs`

Do not default to console scraping unless the native path fails or the user explicitly asks for console output.

## Startup-config mode rule
Stored config text alone is not enough. Verify required nodes have startup-config mode ON before expecting configs to apply at next boot.

## Cheaper-check rule
Use `eve_list_config_summaries` first for existence, mode, and size checks. Escalate to `eve_get_node_config` or `eve_get_all_configs` only when the full config text is needed.

## Config vs wipe
- `eve_set_node_config`: write startup config, node stopped
- `eve_wipe_node_config`: clear startup config only, node stopped
- `eve_wipe_node`: clear NVRAM + startup config, node stopped
