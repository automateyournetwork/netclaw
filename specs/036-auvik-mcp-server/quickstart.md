# Quickstart: Auvik API MCP Server (036)

## Prerequisites
- Python 3.10+
- An Auvik user email + API key with read role permissions for the in-scope APIs (Auvik portal → Admin → API keys).
- Know your Auvik regional cluster (default `us1`).

## Install
```bash
cd mcp-servers/auvik-mcp
python -m venv .venv && . .venv/Scripts/activate   # (Windows: .venv\Scripts\activate; *nix: source .venv/bin/activate)
pip install -r requirements.txt
```

## Configure (env — never commit real values)
```bash
# from .env.example
AUVIK_USERNAME=you@example.com            # Basic-auth username (Auvik user email)
AUVIK_API_KEY=xxxxxxxxxxxxxxxxxxxx         # Basic-auth password (API key)
AUVIK_BASE_URL=https://auvikapi.us1.my.auvik.com   # swap us1 → your region
AUVIK_VERIFY_SSL=true
AUVIK_TIMEOUT=30
AUVIK_RATE_LIMIT=600                       # max requests/min (defensive; Auvik publishes no limit)
AUVIK_MAX_PAGES=50                         # pagination safety cap
```

## Run (stdio)
```bash
python mcp-servers/auvik-mcp/auvik_mcp_server.py
# Registered via config/openclaw.json as "auvik-mcp" for OpenClaw.
```

## Smoke tests (map to Success Criteria)

1. **Auth/health (SC-006)** — `auvik_verify_credentials()` → `{verified:true}`. A bad key returns a clear AuthError, not an empty success.
2. **Tenants (US1)** — `auvik_list_tenants()` returns the multi-client/client catalog (source of truth for tenant names).
3. **Name resolution, zero IDs (SC-001/SC-007)** — `auvik_list_devices(device="core-sw-01")` resolves the name → ID and returns the device. `auvik_list_devices(device="switch")` (ambiguous) returns `ResolutionCandidate[]`, not a guess. `auvik_list_devices(device="10.4.1.1")` resolves by IP.
4. **Multi-page completeness (SC-008)** — run a broad `auvik_list_devices(tenants=<big client>)` known to exceed one page; confirm the aggregated count exceeds `page_first` and `truncated`/`next_cursor` appear only when `AUVIK_MAX_PAGES` is hit.
5. **Alerts (US2)** — `auvik_list_alerts(severity="critical", dismissed=false)` returns a severity table; `auvik_list_alerts(entity="core-sw-01")` resolves the device → `entityId`.
6. **Performance (US3)** — `auvik_get_device_statistics(stat_id="cpuUtilization", device="core-sw-01", from_time="-1h", interval="minute")` returns a series; `availability=true, stat_id="uptime"` returns uptime.
7. **Lifecycle (US4)** — `auvik_list_device_lifecycle(last_support_status="expired")` lists EoS devices; `auvik_list_configurations(device="core-sw-01")` returns backup history.
8. **Read-only guarantee (SC-002)** — `grep -rEi "\.post\(|\.put\(|\.delete\(|\.patch\(" mcp-servers/auvik-mcp/` finds **no** mutating call; `tools/list` shows zero write tools.

## Troubleshooting
- **401/403** → check `AUVIK_USERNAME`/`AUVIK_API_KEY` and that the key's role covers the API; verify region in `AUVIK_BASE_URL`.
- **Empty results for a known device** → it may live under a different tenant; pass `tenants` or check `auvik_list_tenants()`.
- **`ValidationError: device_type required`** → `detail_level="extended"` requires `device_type` (Auvik mandates `filter[deviceType]`).
- **Truncated list** → raise `AUVIK_MAX_PAGES`, or narrow filters.
- **Slow / timed-out broad query** (multi-client keys) → an unscoped query across all client tenants can exceed `AUVIK_TIMEOUT`. Scope it with `tenants=` (accepts a tenant **name/domain-prefix** — resolved to the tenant ID automatically — or a raw tenant ID), or raise `AUVIK_TIMEOUT`. Use `auvik_list_tenants` to see available tenants. *(Validated against a live us2 tenant.)*
