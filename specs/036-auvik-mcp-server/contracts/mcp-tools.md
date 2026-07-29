# MCP Tool Contracts: Auvik API MCP Server (036)

**Phase 1 output.** 20 read-only tools across 4 modules. Every tool returns a TOON/JSON string. Conventions shared by all tools:

- **`tenants`** (str, optional unless noted REQUIRED): MSP multi-client scope. Accepts a tenant name or domain prefix; resolved to the API's tenant value.
- **Identifier params** (`device`, `network`, `interface`, `component`, etc.): accept **name / hostname / IP / partial / Auvik ID**. Resolved via `utils/resolver.py` (FR-024/025/026). Ambiguous → returns `ResolutionCandidate[]`; no match → explicit error; already-an-ID (`^\d{6,}$`) → used directly.
- **Pagination**: list tools auto-aggregate all pages via `links.next` up to `AUVIK_MAX_PAGES`; response includes `truncated` + `next_cursor` when capped. `page_first` (int) and `fetch_all` (bool, default true) override.
- **`raw`** (bool, default false): return raw JSON instead of TOON.
- **Errors**: `{error:{code,message,details}}`; codes `ValidationError|AuthError|NotFound|Ambiguous|RateLimited|UpstreamError`.

---

## Module: inventory (skill `auvik-inventory`)

### `auvik_list_devices`
List/inspect discovered devices. **GET** `/v1/inventory/device/info` | `…/detail` | `…/detail/extended` (+ `/{id}` when a single device resolves).
- `detail_level` (str: `info|detail|extended`, default `info`)
- `device` (str, optional) — name/IP/ID; when set, returns the single device.
- `device_type` (str, optional; **REQUIRED when `detail_level=extended`** per API)
- `make_model`, `vendor_name`, `online_status`, `modified_after`, `not_seen_since`, `networks` (filters)
- `state_known` (bool), `tenants`, `page_first`, `fetch_all`, `raw`
- Maps: info→`filter[deviceType|makeModel|vendorName|onlineStatus|modifiedAfter|notSeenSince|networks|stateKnown]`, `include=deviceDetail`; detail→`filter[manageStatus|discovery*|trafficInsightsStatus]`; extended→`filter[deviceType]`(req)+`modifiedAfter|notSeenSince|stateKnown`.

### `auvik_list_networks`
**GET** `/v1/inventory/network/info` | `…/detail` (+ `/{id}`).
- `detail_level` (`info|detail`, default `info`), `network` (str, optional — name/ID)
- `network_type`, `scan_status`, `devices`, `modified_after`, `scope` (detail only), `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_list_interfaces`
**GET** `/v1/inventory/interface/info` (+ `/{id}`).
- `interface` (str, optional), `parent_device` (str, optional — resolved to device ID), `interface_type`, `admin_status`, `operational_status`, `modified_after`, `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_list_components`
**GET** `/v1/inventory/component/info` (+ `/{id}`).
- `component` (str, optional), `device` (str, optional → `filter[deviceId]`/`deviceName`), `current_status` (`ok|degraded|failed`), `modified_after`, `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_list_tenants`
**GET** `/v1/tenants` (no params) | `/v1/tenants/detail` (when `detail=true`, requires `tenant_domain_prefix`).
- `detail` (bool, default false), `tenant_domain_prefix` (str, required when `detail=true`), `available_tenants` (bool), `raw`
- Note: `/v1/tenants` accepts no filters/paging; this is the source of truth for tenant names used in resolution.

### `auvik_list_entity_notes`
**GET** `/v1/inventory/entity/note` (+ `/{id}`).
- `entity` (str, optional → `filter[entityId]`/`entityName`), `entity_type` (`root|device|network|interface`), `last_modified_by`, `modified_after`, `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_list_entity_audits`
**GET** `/v1/inventory/entity/audit` (+ `/{id}`).
- `user`, `category`, `status`, `modified_after`, `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_get_usage`
**GET** `/v1/billing/usage/client` | `/v1/billing/usage/device/{id}`.
- `scope` (`client|device`, default `client`), `device` (str, required when `scope=device` — resolved to ID), `from_date` (**REQUIRED**), `thru_date` (**REQUIRED**), `tenants` (client scope only), `raw`

### `auvik_verify_credentials`
**GET** `/v1/authentication/verify`. No params. Returns auth/health status. (Utility; surfaced in `auvik-inventory`.)

---

## Module: alerts (skill `auvik-network-alerts`)

### `auvik_list_alerts`
**GET** `/v1/alert/history/info` (+ `/{id}`).
- `alert_id` (str, optional — single alert), `entity` (str, optional → `filter[entityId]`)
- `severity` (`unknown|emergency|critical|warning|info`), `status` (`created|resolved|paused|unpaused`)
- `dismissed` (bool), `dispatched` (bool)
- `detected_time_after`, `detected_time_before` (ISO-8601 strings — sent as datetimes despite the spec mislabeling them boolean)
- `alert_definition_id`, `alert_specification_id`, `tenants`, `page_first`, `fetch_all`, `raw`

---

## Module: lifecycle (skill `auvik-lifecycle`)

### `auvik_list_device_lifecycle`
**GET** `/v1/inventory/device/lifecycle` (+ `/{id}`).
- `device` (str, optional), `sales_availability`, `software_maintenance_status`, `security_software_maintenance_status`, `last_support_status` (lifecycle enum), `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_list_device_warranty`
**GET** `/v1/inventory/device/warranty` (+ `/{id}`).
- `device` (str, optional), `covered_under_warranty` (bool), `covered_under_service` (bool), `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_list_configurations`
**GET** `/v1/inventory/configuration` (+ `/{id}` for the backup body).
- `config_id` (str, optional — single backup, returns body), `device` (str, optional → `filter[deviceId]`), `backup_time_after`, `backup_time_before`, `is_running` (bool), `tenants`, `page_first`, `fetch_all`, `raw`

---

## Module: performance (skill `auvik-performance`)

### `auvik_get_device_statistics`
**GET** `/v1/stat/device/{statId}` | `/v1/stat/deviceAvailability/{statId}`.
- `stat_id` (**REQUIRED**; device: `bandwidth|cpuUtilization|memoryUtilization|storageUtilization|packetUnicast|packetMulticast|packetBroadcast`; availability: `uptime|outage`)
- `availability` (bool, default false → switches to deviceAvailability path)
- `from_time` (**REQUIRED**; accepts relative e.g. `-1h` → ISO-8601), `interval` (**REQUIRED**: `minute|hour|day`), `thru_time` (optional)
- `device` (str, optional → `filter[deviceId]`), `device_type`, `omit_undiscovered` (bool, availability only), `tenants`, `raw`

### `auvik_get_interface_statistics`
**GET** `/v1/stat/interface/{statId}`.
- `stat_id` (**REQUIRED**: `bandwidth|utilization|packetLoss|packetDiscard|packetMulticast|packetUnicast|packetBroadcast`)
- `from_time` (**REQUIRED**), `interval` (**REQUIRED**), `thru_time`
- `interface` (str, optional → `filter[interfaceId]`), `interface_type`, `parent_device` (str → resolved), `tenants`, `raw`

### `auvik_get_service_statistics`
**GET** `/v1/stat/service/{statId}`.
- `stat_id` (**REQUIRED**: `pingTime|pingPacket`), `from_time` (**REQUIRED**), `interval` (**REQUIRED**), `thru_time`, `service_id`, `tenants`, `raw`

### `auvik_get_component_statistics`
**GET** `/v1/stat/component/{componentType}/{statId}`.
- `component_type` (**REQUIRED**: `cpu|cpuCore|disk|fan|memory|powerSupply|systemBoard`)
- `stat_id` (**REQUIRED**: `capacity|counters|idle|latency|power|queueLatency|rate|readiness|ready|speed|swap|swapRate|temperature|totalLatency|utilization`)
- `from_time` (**REQUIRED**), `interval` (**REQUIRED**), `thru_time`, `component_id`, `parent_device` (str → resolved), `tenants`, `raw`

### `auvik_get_oid_statistics`
**GET** `/v1/stat/oid/deviceMonitor` (point-in-time; no time window).
- `device` (str, optional → `filter[deviceId]`), `device_type`, `oid` (str), `tenants`, `page_first`, `fetch_all`, `raw`

### `auvik_list_snmp_poller_settings`
**GET** `/v1/settings/snmppoller` | `/{snmpPollerSettingId}` | `/{snmpPollerSettingId}/devices`.
- `tenants` (**REQUIRED**), `poller_id` (str, optional — single setting), `with_devices` (bool, default false → `/devices` sub-resource)
- `device` (str → `filter[deviceId]`), `use_as` (`serialNo|poller`), `type` (`string|numeric`), `device_type`, `make_model`, `vendor_name`, `oid`, `name`, `page_first`, `fetch_all`, `raw`

### `auvik_get_snmp_poller_history`
**GET** `/v1/stat/snmppoller/string` | `/v1/stat/snmppoller/int`.
- `value_type` (`string|int`, default `int`), `tenants` (**REQUIRED**), `from_time` (**REQUIRED**), `thru_time`
- `interval` (**REQUIRED when `value_type=int`**: `minute|hour|day`; ignored for `string`)
- `compact` (bool, `string` only), `snmp_poller_setting_id` (str), `device` (str → resolved), `page_first`, `fetch_all`, `raw`

---

## Coverage check (FR → tool)
FR-001 `auvik_list_devices` · FR-002 `auvik_list_networks` · FR-003 `auvik_list_interfaces` · FR-004 `auvik_list_components` · FR-005 `auvik_list_tenants` · FR-006 `auvik_list_entity_notes`/`auvik_list_entity_audits` · FR-007 `auvik_get_usage` · FR-008 `auvik_list_alerts` · FR-009 (no writes — verified by absence) · FR-010/011 stats tools · FR-012 `auvik_list_snmp_poller_settings` · FR-013 `auvik_get_snmp_poller_history` · FR-014 `auvik_list_device_lifecycle` · FR-015 `auvik_list_device_warranty` · FR-016 `auvik_list_configurations` · FR-017/018/020 client (auth/base-url/rate-limit) · FR-019/019a pagination util · FR-021 TOON · FR-022 `auvik_verify_credentials` · FR-023 server lifecycle · FR-024/025/026 `utils/resolver.py`.
