# Contracts: spec 190

## Daemon
- `POST /n2n/grants` body adds optional `access_class` (`read`|`read_write`). Invalid -> HTTP 400 `{"error": ...}`, nothing stored. Response `{"grant_id": n, "access_class": "..."}`.
- `GET /n2n/grants` rows include `access_class`.
- `GET /n2n/classifications` -> `{"classifications":[{target_type,target_name,access,source,updated_at}]}`.
- `POST /n2n/classifications` body one of:
  - `{"target_type","target_name","access":"read|write"}` (operator override),
  - `{"target_type","target_name","access":null}` or `"clear": true` (clear override),
  - `{"server":"cml-mcp","tools":[{"name","annotations":{"readOnlyHint":bool}}]}` (annotation import).
  Invalid -> 400.
- `POST /n2n/trust` (one-step) accepts optional `access_class` applied to all granted tools/skills.

## n2n-mcp tools
`n2n_grant(..., access_class: Optional[str])`, `n2n_classify(target_type, target_name, access)`, `n2n_import_annotations(server, tools_json)`, `n2n_list_classifications()`.

## Wire
No new methods or error codes. Denied class check returns -32001 NOT_ALLOWLISTED. Card adds optional `mcp_servers[].tool_access` and `skills[].access`.

## Audit
`decision=access_class_denied, outcome=denied` per refused call; `decision=granted` rows for grants (existing) with target unchanged; `decision=classified|classification_cleared` with `target_type=classification`.
