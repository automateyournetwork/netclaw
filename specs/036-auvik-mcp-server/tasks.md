# Auvik API MCP Server — Implementation Plan (Tasks)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a read-only Auvik FastMCP server (20 tools, 4 skills) with name/IP→ID resolution and full multi-page aggregation, plus all Principle XI coherence artifacts.

**Architecture:** Async httpx `BasicAuth` client with auto-pagination over `links.next`; a shared resolver turns human identifiers into Auvik IDs; tools (one module per theme) shape JSON:API into dataclasses serialized via the TOON shim. Mirrors `azure-network-mcp`/`claroty-mcp` layout.

**Tech Stack:** Python 3.10+, FastMCP, httpx, python-dotenv, pytest + pytest-asyncio + respx; TOON via optional `netclaw_tokens` import.

**Source of truth for tool params/endpoints:** [contracts/mcp-tools.md](./contracts/mcp-tools.md). **Entities:** [data-model.md](./data-model.md). **API facts/gotchas:** [research.md](./research.md).

---

## Phase A — Scaffold & utilities

### Task A1: Package scaffold + requirements
**Files:** Create `mcp-servers/auvik-mcp/{__init__.py,requirements.txt}`, `mcp-servers/auvik-mcp/{clients,models,tools,utils}/__init__.py`, `tests/auvik-mcp/__init__.py`, `tests/auvik-mcp/conftest.py`

- [ ] **Step 1:** Create the directory tree and empty `__init__.py` files.
- [ ] **Step 2:** Write `requirements.txt`:
```
fastmcp>=2.0.0
httpx>=0.27.0
python-dotenv>=1.0.0
```
- [ ] **Step 3:** Write `tests/auvik-mcp/requirements-test.txt`: `pytest`, `pytest-asyncio`, `respx`.
- [ ] **Step 4:** `conftest.py` adds the server package to `sys.path` and sets dummy `AUVIK_USERNAME`/`AUVIK_API_KEY` env for imports.
- [ ] **Step 5:** Commit: `chore(036): scaffold auvik-mcp package`.

### Task A2: `utils/constants.py` (enums + defaults)
**Files:** Create `utils/constants.py`; Test `tests/auvik-mcp/test_constants.py`

- [ ] **Step 1 (test, fails):** assert `DEFAULT_BASE_URL == "https://auvikapi.us1.my.auvik.com"`, `INTERVALS == {"minute","hour","day"}`, `DEVICE_STAT_IDS` contains `cpuUtilization`, `COMPONENT_TYPES` contains `powerSupply`.
- [ ] **Step 2:** Run `pytest tests/auvik-mcp/test_constants.py -v` → FAIL (module missing).
- [ ] **Step 3 (impl):** Define `DEFAULT_BASE_URL`, `INTERVALS`, `DEVICE_STAT_IDS`, `DEVICE_AVAILABILITY_STAT_IDS`, `INTERFACE_STAT_IDS`, `SERVICE_STAT_IDS`, `COMPONENT_STAT_IDS`, `OID_STAT_IDS`, `COMPONENT_TYPES`, `DEVICE_TYPES`, `INTERFACE_TYPES`, `ALERT_SEVERITIES`, `ALERT_STATUSES`, `LIFECYCLE_STATUSES`, `ONLINE_STATUSES`, `NETWORK_TYPES` from [research.md §Enum vocabularies].
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): auvik constants/enums`.

### Task A3: `utils/toon_helper.py` (token shim)
**Files:** Create `utils/toon_helper.py`; Test `tests/auvik-mcp/test_toon_helper.py`

- [ ] **Step 1 (test, fails):**
```python
from utils.toon_helper import gcf_dumps
def test_gcf_dumps_json_fallback():
    out = gcf_dumps({"a": 1, "b": None})
    assert "a" in out and isinstance(out, str)
```
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):** mirror `azure-network-mcp/utils/gcf_helper.py`:
```python
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "src"))
def gcf_dumps(data, **kwargs) -> str:
    try:
        from netclaw_tokens.gcf_serializer import serialize_response
        return serialize_response(data).gcf_data
    except Exception:
        return json.dumps(data, indent=2, default=str)
```
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): TOON serialization shim`.

### Task A4: `utils/rate_limiter.py` (sliding window + Retry-After)
**Files:** Create `utils/rate_limiter.py`; Test `tests/auvik-mcp/test_rate_limiter.py`

- [ ] **Step 1 (test, fails):** with `SlidingWindowRateLimiter(max_calls=2, period=0.2)`, 3 awaited `acquire()` calls take ≥ ~0.2s (third waits); `parse_retry_after({"Retry-After":"5"}) == 5`; `parse_retry_after({}) is None`.
- [ ] **Step 2:** Run (pytest-asyncio) → FAIL.
- [ ] **Step 3 (impl):** `SlidingWindowRateLimiter` using an `asyncio.Lock` + monotonic timestamp deque; `async def acquire()` sleeps until a slot frees. `parse_retry_after(headers)->Optional[int]` (int seconds; warn+None on unparsable).
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): sliding-window rate limiter`.

### Task A5: `utils/pagination.py` (cursor extraction)
**Files:** Create `utils/pagination.py`; Test `tests/auvik-mcp/test_pagination.py`

- [ ] **Step 1 (test, fails):** `next_cursor_url({"links":{"next":"https://x/v1/...?page[after]=ABC&page[first]=300"}})` returns the URL; returns `None` when `links.next` absent/empty. `merge_page(acc, {"data":[...]})` appends items.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):** `next_cursor_url(payload)->Optional[str]` reads `payload["links"]["next"]`; `merge_page(acc:list, payload)->list` extends with `payload.get("data",[])`. (Driving the walk lives in the client — this is pure helpers; do NOT rely on `meta.totalPages`, it's deprecated.)
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): pagination cursor helpers`.

---

## Phase B — HTTP client

### Task B1: `clients/auvik_client.py` — construction + `get()`
**Files:** Create `clients/auvik_client.py`; Test `tests/auvik-mcp/test_client_get.py` (respx)

- [ ] **Step 1 (test, fails):** with respx mocking `GET {base}/v1/authentication/verify` → 200, `await AuvikClient(...).get("/v1/authentication/verify")` returns `{"success":True,"data":{...},"error":None}`. A 401 returns `success=False` with an auth message. Assert the request carries an `Authorization: Basic` header.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):** constructor `(base_url, username, password, verify_ssl=True, timeout=30, rate_limiter=None)`; lazy `_get_client()` builds `httpx.AsyncClient(base_url=..., auth=httpx.BasicAuth(u,p), verify=..., timeout=..., headers={"Accept":"application/vnd.api+json"})`. `async def get(path, params=None)` awaits `rate_limiter.acquire()` (if set), issues GET, maps 401/403→auth error, ConnectError/Timeout/HTTPStatusError→structured error, success→`{"success":True,"data":resp.json(),"error":None}`.
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): async Auvik httpx client (get)`.

### Task B2: 429 handling in `get()`
**Files:** Modify `clients/auvik_client.py`; Test `tests/auvik-mcp/test_client_429.py`

- [ ] **Step 1 (test, fails):** respx returns 429 + `Retry-After: 0` once then 200; `get()` retries and returns success; caps retries (e.g., 3) then returns a `RateLimited` error.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):** on 429, `parse_retry_after(resp.headers)` → `await asyncio.sleep(n)`, retry up to `max_retries=3`; exhausted → structured `RateLimited` error.
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): 429/Retry-After backoff`.

### Task B3: `get_all()` — auto multi-page aggregation (FR-019a)
**Files:** Modify `clients/auvik_client.py`; Test `tests/auvik-mcp/test_client_get_all.py`

- [ ] **Step 1 (test, fails):** respx serves page 1 (`data` of 2 items + `links.next`=page2 url) then page 2 (2 items, no `links.next`). `await client.get_all("/v1/inventory/device/info", params={...})` returns `{"items":[4 items],"page_count":2,"truncated":False,"next_cursor":None}`. With `max_pages=1`, returns 2 items, `truncated=True`, `next_cursor`=page2 url.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):** `async def get_all(path, params=None, max_pages=AUVIK_MAX_PAGES)`: loop `get()`, `merge_page`, follow `next_cursor_url` (request the absolute next URL directly; strip base), increment page count; stop at no-next or cap. Return `{items, page_count, truncated, next_cursor}`.
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): client.get_all auto-pagination`.

---

## Phase C — Resolver (FR-024/025/026)

### Task C1: ID-shape detection + resolve-by-name/IP
**Files:** Create `utils/resolver.py`; Test `tests/auvik-mcp/test_resolver.py`

- [ ] **Step 1 (test, fails):**
```python
import pytest
from utils.resolver import looks_like_id, resolve_device

def test_looks_like_id():
    assert looks_like_id("242216279026467843") is True
    assert looks_like_id("core-sw-01") is False
    assert looks_like_id("10.4.1.1") is False

@pytest.mark.asyncio
async def test_resolve_device_single(fake_client_one_match):
    res = await resolve_device(fake_client_one_match, "core-sw-01")
    assert res.id == "999" and res.ambiguous is False

@pytest.mark.asyncio
async def test_resolve_device_ambiguous(fake_client_two_matches):
    res = await resolve_device(fake_client_two_matches, "switch")
    assert res.ambiguous is True and len(res.candidates) == 2

@pytest.mark.asyncio
async def test_resolve_device_none(fake_client_no_match):
    res = await resolve_device(fake_client_no_match, "nope")
    assert res.ambiguous is False and res.id is None and res.candidates == []
```
(Provide the three `fake_client_*` fixtures in `conftest.py` returning canned `get_all` payloads.)
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):**
```python
import re
from dataclasses import dataclass, field
_ID_RE = re.compile(r"^\d{6,}$")
def looks_like_id(v: str) -> bool: return bool(_ID_RE.match(v.strip()))

@dataclass
class Resolution:
    id: str | None = None
    ambiguous: bool = False
    candidates: list = field(default_factory=list)

def _is_ip(v: str) -> bool: ...  # simple ipaddress.ip_address try/except

async def resolve_device(client, value, tenants=None):
    if looks_like_id(value):
        return Resolution(id=value)
    # NOTE: /v1/inventory/device/info has NO name filter — fetch (paginated)
    # and match client-side on deviceName / ipAddresses.
    params = {"tenants": tenants} if tenants else None
    res = await client.get_all("/v1/inventory/device/info", params=params)
    items = res["items"]
    if _is_ip(value):
        matches = [d for d in items if value in (d.get("attributes",{}).get("ipAddresses") or [])]
    else:
        v = value.lower()
        exact = [d for d in items if (d.get("attributes",{}).get("deviceName") or "").lower() == v]
        matches = exact or [d for d in items if v in (d.get("attributes",{}).get("deviceName") or "").lower()]
    cands = [_candidate(d) for d in matches]
    if len(cands) == 1: return Resolution(id=cands[0]["id"])
    if len(cands) > 1:  return Resolution(ambiguous=True, candidates=cands)
    return Resolution()
```
`_candidate(d)` → `{id, name, ipAddress, entityType:"device", tenant}`. `resolve_network`/`resolve_tenant` follow the same client-side-match shape (networks have no name filter either; tenants come from `/v1/tenants`, matched on `domainPrefix`/`displayName`).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5 (impl, generic):** add `resolve_network`, `resolve_interface`, `resolve_tenant` (tenant via `/v1/tenants` name/domainPrefix match) following the same shape; add focused tests. 
- [ ] **Step 6:** Run → PASS. **Step 7:** Commit `feat(036): entity resolver (name/IP→id, candidates)`.

### Task C2: Resolver helper for tools — `resolve_or_error`
**Files:** Modify `utils/resolver.py`; Test add to `test_resolver.py`

- [ ] **Step 1 (test, fails):** `resolve_or_error(Resolution(id="9"))` → `("9", None)`; ambiguous → `(None, {"error":{"code":"Ambiguous",...,"candidates":[...]}})`; none → `(None, {"error":{"code":"NotFound",...}})`.
- [ ] **Step 2:** Run → FAIL. **Step 3 (impl):** the helper. **Step 4:** PASS. **Step 5:** Commit `feat(036): resolve_or_error tool helper`.

---

## Phase D — Models

### Task D1: `models/responses.py`
**Files:** Create `models/responses.py`; Test `tests/auvik-mcp/test_models.py`

- [ ] **Step 1 (test, fails):** `to_dict(Device(id="1", device_name="x", ip_addresses=["10.0.0.1"]))` drops None keys; `to_json([Device(...)])` returns a string; `Device.from_resource({"id":"1","attributes":{"deviceName":"x","ipAddresses":["10.0.0.1"]}})` maps fields.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):** `to_dict`/`to_json` (TOON via `toon_helper.gcf_dumps`) helpers + dataclasses for each entity in [data-model.md] with a `from_resource(cls, obj)` classmethod mapping `attributes.*`. Cover Device, DeviceDetail, DeviceLifecycle, DeviceWarranty, Network, Interface, Component, Configuration, Tenant, EntityNote, EntityAudit, Alert, Statistic, SnmpPollerSetting, SnmpPollerHistory, Usage.
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): response dataclasses + TOON serialization`.

---

## Phase E — Tools + server (one task per tool; each starts with a failing param-mapping test)

> **Pattern (canonical tool — implement once, reuse shape):** each tool (a) validates required params against constants, (b) resolves identifier params via the resolver (returning the `Ambiguous`/`NotFound` error envelope verbatim if unresolved), (c) builds the exact `filter[...]`/`tenants`/`page[...]` params from [contracts/mcp-tools.md], (d) calls `client.get`/`get_all`, (e) maps resources via `models.from_resource`, (f) returns `to_json(...)` (or raw JSON if `raw=true`), (g) wraps everything in try/except → error envelope. Tools are `async`. Tests use respx + assert the **outgoing params/path** match the contract (no live API).

### Task E1: inventory tool — `auvik_list_devices` (canonical, full impl)
**Files:** Create `tools/inventory.py`; Test `tests/auvik-mcp/test_tool_list_devices.py`

- [ ] **Step 1 (test, fails):** respx asserts: default → `GET /v1/inventory/device/info` with `include=deviceDetail`; `device="core-sw-01"` → resolver runs then single `/v1/inventory/device/info/{id}`; `detail_level="extended"` without `device_type` → returns `ValidationError` (no HTTP call); `detail_level="extended", device_type="switch"` → `GET /v1/inventory/device/detail/extended?filter[deviceType]=switch`; ambiguous device → `Ambiguous` envelope with candidates.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3 (impl):** implement per the pattern + contract. This is the reference implementation other inventory tools copy.
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): tool auvik_list_devices`.

### Task E2–E8: remaining inventory tools
Implement, each with its own failing respx test asserting endpoint+params per [contracts/mcp-tools.md]; commit per tool:
- [ ] **E2** `auvik_list_networks` (`/network/info|/detail`, `network` resolve)
- [ ] **E3** `auvik_list_interfaces` (`/interface/info`, `parent_device`/`interface` resolve)
- [ ] **E4** `auvik_list_components` (`/component/info`, `device` resolve)
- [ ] **E5** `auvik_list_tenants` (`/tenants` no-params | `/tenants/detail` requires `tenant_domain_prefix`)
- [ ] **E6** `auvik_list_entity_notes` (`/entity/note`, `entity` resolve)
- [ ] **E7** `auvik_list_entity_audits` (`/entity/audit`)
- [ ] **E8** `auvik_get_usage` (`/billing/usage/client` requires from/thru | `/billing/usage/device/{id}` resolve+required dates) and `auvik_verify_credentials` (`/authentication/verify`)

### Task E9: alerts tool — `auvik_list_alerts`
**Files:** Create `tools/alerts.py`; Test `tests/auvik-mcp/test_tool_alerts.py`
- [ ] **Step 1 (test, fails):** `severity="critical", dismissed=False` → `filter[severity]=critical&filter[dismissed]=false`; `entity="core-sw-01"` → resolves to `filter[entityId]`; `detected_time_after="2026-06-01T00:00:00Z"` sent as a **string** (not boolean); `alert_id` → single `/{id}`.
- [ ] **Step 2:** FAIL → **Step 3:** impl → **Step 4:** PASS → **Step 5:** Commit `feat(036): tool auvik_list_alerts`.

### Task E10–E12: lifecycle tools
**Files:** Create `tools/lifecycle.py`; one test file per tool.
- [ ] **E10** `auvik_list_device_lifecycle` (`/device/lifecycle`, `device` resolve)
- [ ] **E11** `auvik_list_device_warranty` (`/device/warranty`, `device` resolve)
- [ ] **E12** `auvik_list_configurations` (`/inventory/configuration`, `device`→`filter[deviceId]`, `config_id`→`/{id}` body)

### Task E13–E19: performance tools
**Files:** Create `tools/performance.py`; one test file per tool. Assert required `from_time`+`interval` validation and `statId`/`componentType` enum validation.
- [ ] **E13** `auvik_get_device_statistics` (`/stat/device/{statId}` | `/stat/deviceAvailability/{statId}` when `availability=true`; `device`→`filter[deviceId]`)
- [ ] **E14** `auvik_get_interface_statistics` (`/stat/interface/{statId}`)
- [ ] **E15** `auvik_get_service_statistics` (`/stat/service/{statId}`)
- [ ] **E16** `auvik_get_component_statistics` (`/stat/component/{componentType}/{statId}`)
- [ ] **E17** `auvik_get_oid_statistics` (`/stat/oid/deviceMonitor`, no time params)
- [ ] **E18** `auvik_list_snmp_poller_settings` (`/settings/snmppoller` tenants REQUIRED | `/{snmpPollerSettingId}` | `/{snmpPollerSettingId}/devices` when `with_devices`)
- [ ] **E19** `auvik_get_snmp_poller_history` (`/stat/snmppoller/string` no-interval | `/int` interval REQUIRED; tenants REQUIRED)

### Task E20: server entrypoint + registration
**Files:** Create `auvik_mcp_server.py`; Test `tests/auvik-mcp/test_server_registration.py`
- [ ] **Step 1 (test, fails):** import server; assert exactly 20 tools registered; assert **no** tool name implies a write and the client class defines no `post/put/delete/patch` method (SC-002). Assert `get_client()` raises if creds missing.
- [ ] **Step 2:** FAIL.
- [ ] **Step 3 (impl):** load_dotenv, stderr logging, read `AUVIK_*` env, `get_client()` singleton (fail-fast), instantiate `SlidingWindowRateLimiter(AUVIK_RATE_LIMIT)`, register all 20 tools from the `tools/` modules via `@mcp.tool()`, `if __name__=="__main__": mcp.run()`.
- [ ] **Step 4:** Run → PASS. **Step 5:** Commit `feat(036): auvik MCP server entrypoint (20 tools, read-only)`.

### Task E21: server README + .env.example
**Files:** Create `mcp-servers/auvik-mcp/README.md`, `mcp-servers/auvik-mcp/.env.example`
- [ ] Document tool inventory, env vars, transport, install (per [quickstart.md]). Commit `docs(036): auvik-mcp README + .env.example`.

---

## Phase F — Skills (4 × SKILL.md)

### Task F1–F4: write skills (template = an existing MCP-backed `SKILL.md`)
Each: frontmatter (`name`, `description` with "Use when…", `license: Apache-2.0`, `metadata.openclaw.requires.env: [AUVIK_USERNAME, AUVIK_API_KEY, AUVIK_BASE_URL]`), tool table, key concepts, a workflow, integration-with-other-skills (incl. `gait-session-tracking`), env vars, rules.
- [ ] **F1** `workspace/skills/auvik-inventory/SKILL.md` (devices, networks, interfaces, components, tenants, entity notes/audits, usage, verify)
- [ ] **F2** `workspace/skills/auvik-network-alerts/SKILL.md` (alerts)
- [ ] **F3** `workspace/skills/auvik-lifecycle/SKILL.md` (lifecycle, warranty, configurations)
- [ ] **F4** `workspace/skills/auvik-performance/SKILL.md` (stats, SNMP poller)
- [ ] Commit `docs(036): add 4 auvik skills`.

---

## Phase G — Coherence artifacts (Principle XI — all before merge)

Each edit follows the exact existing format (see [checklists/requirements.md] for file+location). Verify counts by reading current values, not assuming.
- [ ] **G1** `config/openclaw.json` — register `"auvik-mcp"` (python3 `-u` `mcp-servers/auvik-mcp/auvik_mcp_server.py`, env block `${AUVIK_*}`). Commit.
- [ ] **G2** `.env.example` — `AUVIK_*` block with descriptive comments, no values. Commit.
- [ ] **G3** `scripts/install.sh` — new numbered step (venv + `pip install -r requirements.txt`). Commit.
- [ ] **G4** `ui/netclaw-visual/server.js` — add Auvik to `INTEGRATION_CATALOG` (`{id,name,category,prefixes:['auvik-'],color,transport:'stdio',toolEstimate:20,description}`) and `ENV_MAP` (`auvik:{env:[AUVIK_USERNAME,AUVIK_API_KEY,AUVIK_BASE_URL],files:[],notes}`). Commit.
- [ ] **G5** `README.md` — add MCP-server row + 4-skill section; bump MCP and skill counts in headers/intro. Commit.
- [ ] **G6** `SOUL.md` + `SOUL-SKILLS.md` — register the 4 skills + procedures; bump counts. Commit.
- [ ] **G7** `TOOLS.md` — add Auvik connection-details line. Commit.
- [ ] **G8** `CLAUDE.md` / `AGENTS.md` "Active Technologies"/"Recent Changes" — append the 036 entry if that pattern is maintained. Commit.

---

## Phase H — Verification, regression, milestone

- [ ] **H1** Run full unit suite: `pytest tests/auvik-mcp/ -v` → all pass. Confirm SC-002 (read-only) and SC-008 (pagination) tests green.
- [ ] **H2** Regression (SC-004): smoke an existing server import (e.g. `python -c "import mcp-servers/suzieq-mcp/server.py"` equivalent) + `python -m json.tool config/openclaw.json` validates. 
- [ ] **H3** Live smoke (operator, optional): run quickstart smoke tests 1–8 against a real Auvik tenant; record results in the GAIT log.
- [ ] **H4** Complete [checklists/requirements.md]; verify every Principle XI box.
- [ ] **H5** WordPress milestone draft (Principle XVII) at `docs/blog/2026-06-21-auvik-mcp.md`; if WordPress MCP unavailable, note in GAIT log.
- [ ] **H6** Final GAIT summary commit; open PR with constitution-compliance summary.

## Self-review (writing-plans)
- **Spec coverage:** every FR-001…FR-026 maps to a task (Phase B/C/D/E) — see coverage map in contracts. SC-001…SC-008 covered by H1/H3 + quickstart smokes. ✅
- **Placeholders:** none — foundational units (constants, toon, rate limiter, pagination, client, resolver, models, canonical tool, server) have complete code or precise test+impl steps; repetitive tools reference the canonical pattern + contract (not "similar to Task N" — each names its endpoint/params/test). ✅
- **Type consistency:** `client.get`/`get_all` return shapes, `Resolution`, `resolve_or_error`, `from_resource`, `to_json` used consistently across tasks. ✅
