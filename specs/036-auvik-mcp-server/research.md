# Research: Auvik API MCP Server (036)

**Phase 0 output** — consolidates the Auvik API surface and the NetClaw MCP conventions this server must follow. All API facts below were extracted directly from the attached OpenAPI 3.0.1 (`auvikopenapi.txt`); conventions were extracted from the live repo.

## 1. Auvik API essentials

| Aspect | Finding | Decision |
|---|---|---|
| Spec | OpenAPI 3.0.1, `info.version` v1, 50 paths, media type `application/vnd.api+json` (JSON:API) | Treat all responses as JSON:API (`data[]`, `included[]`, `links`, `meta`). |
| Auth | `ApiKey` scheme = HTTP **Basic** ("Username and apiKey as the password") | `httpx.BasicAuth(AUVIK_USERNAME, AUVIK_API_KEY)`. |
| Base URL | Only `https://auvikapi.us1.my.auvik.com` attested in the spec | `AUVIK_BASE_URL` env, default `…us1…`; other regions follow `auvikapi.{region}.my.auvik.com` (external knowledge, not asserted by spec). |
| Pagination | Cursor-based. `links.next/prev/first/last` carry opaque `page[after]`/`page[before]` tokens. `meta.totalPages` is the **only** `meta` field and is **`deprecated`**. | **Drive pagination off `links.next`**, never a count. Auto-follow `next` until absent or `AUVIK_MAX_PAGES` cap. |
| Page size | `page[first]` (number), `page[after]`/`page[before]` (cursor), `page[last]` | Default `page[first]=300` (Auvik's example), configurable. |
| Rate limits | **None documented** anywhere in the 638 KB spec (no `429`, "throttle", "rate limit", "x-ratelimit") | Implement defensive sliding-window limiter + `Retry-After`/backoff on 429 regardless; `AUVIK_RATE_LIMIT` configurable. |
| Multi-tenant | `tenants` query param (MSP multi-client). Optional on most inventory/stat endpoints; **REQUIRED** on the 4 SNMP-poller endpoints. `/v1/tenants` & `/v1/tenants/detail` & `/v1/billing/usage/device/{id}` take no `tenants`. | Expose optional `tenants` on every tool; enforce required where the API demands it. |

### Spec gotchas to carry forward (must handle in code)
1. **`meta.totalPages` is deprecated** and the only `meta` key — paginate via `links.next`, not a record/page count.
2. **`/v1/settings/snmppoller/{snmpPollerSettingId}/devices`** — path param is `snmpPollerSettingId`, not `id`.
3. **`/v1/alert/history/info`** declares `filter[detectedTimeAfter]`/`[detectedTimeBefore]` as `type: boolean`, but they are ISO-8601 timestamps (spec bug). Model and send as datetime strings.
4. **`/v1/inventory/device/detail/extended`** **requires** `filter[deviceType]`. The extended tool path must require/iterate a device type.
5. **`configResourceObject.attributes`** is thin (`backupTime`, `isRunning`); the device link and config body are JSON:API relationships, not attributes. The single-fetch `/{id}` returns the fuller object.
6. **`/v1/tenants`** accepts **no** query params (no filter, no `tenants`, no paging). `/v1/tenants/detail` **requires** `tenantDomainPrefix`.
7. Only `us1` is attested — make region configurable, don't hard-promise other regions.

### Required-parameter map (enforce in tool validation)
- `device/detail/extended` → `filter[deviceType]` required.
- `tenants/detail` → `tenantDomainPrefix` required.
- `billing/usage/client` → `filter[fromDate]` + `filter[thruDate]` required.
- `billing/usage/device/{id}` → path `id` + `filter[fromDate]` + `filter[thruDate]` required.
- `stat/device`, `stat/deviceAvailability`, `stat/interface`, `stat/service`, `stat/component/{componentType}` → `filter[fromTime]` + `filter[interval]` required (`thruTime` optional).
- `stat/snmppoller/int` → `filter[fromTime]` + `filter[interval]` + `tenants` required.
- `stat/snmppoller/string` → `filter[fromTime]` + `tenants` required (no interval; has `filter[compact]`).
- `stat/oid/{statId}` → no time params (point-in-time OID read); `statId` enum = `deviceMonitor`.
- `settings/snmppoller`, `settings/snmppoller/{id}/devices` → `tenants` required.

### Enum vocabularies (→ `utils/constants.py`)
- `filter[interval]`: `minute | hour | day`.
- `statId` per category:
  - device: `bandwidth, cpuUtilization, memoryUtilization, storageUtilization, packetUnicast, packetMulticast, packetBroadcast`
  - deviceAvailability: `uptime, outage`
  - interface: `bandwidth, utilization, packetLoss, packetDiscard, packetMulticast, packetUnicast, packetBroadcast`
  - service: `pingTime, pingPacket`
  - component: `capacity, counters, idle, latency, power, queueLatency, rate, readiness, ready, speed, swap, swapRate, temperature, totalLatency, utilization`
  - oid: `deviceMonitor`
- `componentType`: `cpu, cpuCore, disk, fan, memory, powerSupply, systemBoard`.
- alert `filter[severity]`: `unknown, emergency, critical, warning, info`; alert `filter[status]`: `created, resolved, paused, unpaused`.
- lifecycle status enum: `covered, available, expired, securityOnly, unpublished, empty`.
- `onlineStatus`: `online, offline, unreachable, testing, unknown, dormant, notPresent, lowerLayerDown`.
- `networkType`: `routed, vlan, wifi, loopback, network, layer2, internet`.
- `entity note entityType`: `root, device, network, interface`.
- snmppoller `filter[type]`: `string, numeric`; `filter[useAs]`: `serialNo, poller`.
- `deviceType` (48 values, verbatim from `DeviceTypeSchema`): `unknown, switch, l3Switch, router, accessPoint, firewall, workstation, server, storage, printer, copier, hypervisor, multimedia, phone, tablet, handheld, virtualAppliance, bridge, controller, hub, modem, ups, module, loadBalancer, camera, telecommunications, packetProcessor, chassis, airConditioner, virtualMachine, pdu, ipPhone, backhaul, internetOfThings, voipSwitch, stack, backupDevice, timeClock, lightingDevice, audioVisual, securityAppliance, utm, alarm, buildingManagement, ipmi, thinAccessPoint, thinClient, subnet`.
- `interfaceType` (30 values, verbatim from `filter[interfaceType]`): `ethernet, wifi, bluetooth, cdma, coax, cpu, distributedVirtualSwitch, firewire, gsm, ieee8023AdLag, inferredWired, inferredWireless, interface, linkAggregation, loopback, modem, wimax, optical, other, parallel, ppp, radiomac, rs232, tunnel, unknown, usb, virtualBridge, virtualNic, virtualSwitch, vlan`.

## 2. NetClaw MCP conventions (from live repo)

| Concern | Convention (source) | Apply as |
|---|---|---|
| Framework | FastMCP, stdio, tools via `@mcp.tool()`, `mcp.run()`; env at module load, **fail fast** if creds missing (`gns3-mcp`, `suzieq-mcp`) | `auvik_mcp_server.py` instantiates `FastMCP("auvik-mcp")`, registers tools, `mcp.run()`. |
| HTTP client | Async `httpx.AsyncClient`, lazy-init, structured `{success,data,error}` returns, handles ConnectError/Timeout/HTTPStatusError/401-403 (`suzieq-mcp`) | `clients/auvik_client.py` with `httpx.BasicAuth`, auto-pagination + 429 retry baked into `get()`. |
| Logging | To **stderr** only (stdout reserved for JSON-RPC) | `logging.basicConfig(stream=sys.stderr)`. |
| Token optimization | TOON/GCF shim with JSON fallback (`azure-network-mcp/utils/gcf_helper.py`, Feature 006) | `utils/toon_helper.py` → `gcf_dumps()` with `json.dumps` fallback; `raw=true` opt-out. |
| Rate limiter | Azure's is only an exception translator; Claroty wrote a real sliding-window limiter | Write a real `utils/rate_limiter.py` (monotonic clock + window). |
| Models | Dataclasses + `to_dict()` (drop None) + `to_json()` via TOON (`azure-network-mcp/models/responses.py`) | `models/responses.py` dataclasses for each entity. |
| Layout | `azure-network-mcp` / `claroty-mcp`: `clients/ models/ tools/ utils/` + entrypoint + `requirements.txt` + `README.md` + `.env.example` | Mirror exactly. |
| GAIT | Session-level audit (file-based log this session; `gait_logger.py` pattern exists for runtime tool logging) | Server stays stdio read-only; session GAIT log covers the build. Runtime tool-call GAIT logging deferred (read-only, low risk) — note in plan. |

## 3. Decisions resolved (no open `NEEDS CLARIFICATION`)

- **D1 — ID resolution** (spec FR-024/025/026): a shared `utils/resolver.py` turns a name/hostname/IP/partial into the correct Auvik ID. **Important:** `/v1/inventory/device/info`, `/network/info`, and `/interface/info` have **no name filter** in the Auvik API — the only name filters that exist are `filter[deviceName]` (on `/component/info`), `filter[entityName]` (on `/entity/note`), and `filter[name]` (on `/settings/snmppoller`). Therefore device/network/interface resolution **fetches the (paginated) list and matches client-side** on the resource's name fields — devices on `attributes.deviceName` (case-insensitive: exact first, then substring) and `attributes.ipAddresses` (for IP inputs); tenants on `domainPrefix`/`displayName` (from `/v1/tenants`); entity notes/components may additionally use their server-side name filters. ID-shape heuristic: a value matching `^\d{6,}$` is treated as an existing Auvik ID and used directly. Ambiguous → return `ResolutionCandidate[]`; none → explicit "no match". Resolution honors `tenants` scope and walks all pages (via `client.get_all`).
- **D2 — Pagination** (spec FR-019a): `clients/auvik_client.get_all()` auto-follows `links.next` up to `AUVIK_MAX_PAGES` (default 50), aggregating `data[]`; returns a `truncated` flag + continuation cursor when capped. Single-page mode available via explicit `page_first`/cursor.
- **D3 — Read-only**: no POST/PUT/DELETE tools; `alert/dismiss` excluded. No `itsm_gate.py`. Verified by source inspection (SC-002).
- **D4 — Skill→tool mapping**: `auvik-inventory` (devices, networks, interfaces, components, tenants, entity notes/audits, usage, verify), `auvik-network-alerts` (alerts), `auvik-lifecycle` (lifecycle, warranty, configurations), `auvik-performance` (device/interface/service/component/oid stats, SNMP poller settings + history).
- **D5 — Extended detail**: `auvik_list_devices(detail_level="extended")` requires `device_type` (API mandates `filter[deviceType]`); documented in the tool contract and validated.
- **D6 — Stat time defaults**: tools require `from_time` + `interval` where the API does; provide friendly relative inputs (e.g., `from_time="-1h"`) resolved to ISO-8601 by the tool layer.

## 4. Out of scope (v1)
ASM / SaaS Management endpoints (`/v1/asm/*`); any write/mutation (incl. `alert/dismiss`); runtime per-tool GAIT MCP logging (covered by session-level GAIT log). Each may be a follow-up spec.
