# MCP Tool Contracts — Claroty xDome MCP

All 21 tools are registered on the `claroty-mcp` FastMCP instance and exposed via stdio JSON-RPC. Read-only tools return the result directly; ITSM-gated write tools return `{"itsm_gate": ..., "applied": bool, "response": ...}` so callers can verify the gate result and the upstream response in one structure.

## Read-only tools (15)

### `list_devices`

```
list_devices(
    site_id: Optional[str] = None,
    purdue_level: Optional[str] = None,
    device_purpose: Optional[str] = None,
    name_contains: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    max_items: int = 500,
) -> str
```

Returns GCF-encoded `{"count": int, "devices": [...]}`. Errors return `{"error": "..."}` as JSON.

### `get_device_details`

```
get_device_details(device_id: str) -> str
```

### `get_device_communication_map`

```
get_device_communication_map(
    device_id: Optional[str] = None,
    site_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> str
```

### `list_alerts`

```
list_alerts(
    severity: Optional[str] = None,
    status: Optional[str] = None,
    site_id: Optional[str] = None,
    assignee: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    max_items: int = 500,
) -> str
```

### `get_alert_with_devices`

```
get_alert_with_devices(alert_id: str, device_limit: int = 200) -> str
```

Composite of two xDome calls (alert lookup + affected devices) returned in one structure.

### `list_vulnerabilities`

```
list_vulnerabilities(
    severity: Optional[str] = None,
    cvss_min: Optional[float] = None,
    cve_contains: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    max_items: int = 500,
) -> str
```

### `get_vulnerable_devices`

```
get_vulnerable_devices(vulnerability_id: str, limit: int = 200, offset: int = 0) -> str
```

### `list_sites` / `get_site`

```
list_sites(limit: int = 200, offset: int = 0) -> str
get_site(site_id: str) -> str
```

### `list_edge_locations`

```
list_edge_locations(site_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> str
```

Read-only — sensor lifecycle is out of v1 scope.

### `list_servers` / `get_server_interfaces`

```
list_servers(limit: int = 100, offset: int = 0) -> str
get_server_interfaces(server_id: Optional[str] = None, limit: int = 100, offset: int = 0) -> str
```

### `list_ot_activity_events`

```
list_ot_activity_events(
    device_id: Optional[str] = None,
    site_id: Optional[str] = None,
    event_type: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    max_items: int = 1000,
) -> str
```

### `get_audit_log`

```
get_audit_log(
    start: Optional[str] = None,
    end: Optional[str] = None,
    user: Optional[str] = None,
    action_contains: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    max_items: int = 1000,
) -> str
```

### `list_organization_zones`

```
list_organization_zones(limit: int = 200, offset: int = 0) -> str
```

## ITSM-gated write tools (6)

All write tools take a required `cr_number` parameter. They first call `validate_change_request(cr_number)` from `utils/itsm_gate.py`; if `valid: False`, they return without calling xDome.

### `acknowledge_alert`

```
acknowledge_alert(
    alert_id: str,
    resolution: str,
    cr_number: str,
    note: Optional[str] = None,
) -> str
```

Returns `{"itsm_gate": {...}, "applied": bool, "response": ...}` (or `error`).

### `set_vulnerability_relevance`

```
set_vulnerability_relevance(
    device_id: str,
    vulnerability_id: str,
    relevant: bool,
    cr_number: str,
    note: Optional[str] = None,
) -> str
```

### `set_device_purdue_level`

```
set_device_purdue_level(device_id: str, purdue_level: str, cr_number: str) -> str
```

### `set_device_custom_attribute`

```
set_device_custom_attribute(
    device_id: str,
    attribute_key: str,
    attribute_value: str,
    cr_number: str,
) -> str
```

### `label_alerts`

```
label_alerts(
    alert_ids: list[str],
    labels: list[str],
    cr_number: str,
    replace: bool = False,
) -> str
```

### `assign_alerts`

```
assign_alerts(
    alert_ids: list[str],
    assignee: str,
    cr_number: str,
    note: Optional[str] = None,
) -> str
```

## Error envelope

All tools catch upstream exceptions and return `{"error": "..."}` as a JSON string rather than raising. This keeps the MCP layer's behaviour predictable from the agent's perspective.

## Rate-limit envelope

The sliding-window limiter inside `client.post()` may sleep before issuing a request when the per-minute budget is full. The sleep is invisible to the tool author; the only observable effect is a higher latency on the affected call.
