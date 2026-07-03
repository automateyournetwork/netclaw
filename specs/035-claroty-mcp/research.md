# Research — Claroty xDome MCP Server

## What is xDome?

Claroty xDome is a SaaS OT / IoT / IoMT visibility and threat-detection platform. The REST API exposes assets, alerts, vulnerabilities, site organisation, edge sensor management, audit logs, and user-action workflow primitives. Base URL: `https://api.medigate.io/`. Authentication: HTTP Bearer token generated in xDome's Admin Settings → User Management.

## API quirks

Three things the xDome API does that depart from typical REST conventions:

1. **All endpoints are POST.** There are no GETs — even pure list/lookup endpoints accept a POST with a JSON filter body. The client wrapper hides this from tool authors with `post(endpoint, body)` and `paginate(endpoint, body)`.
2. **Pagination is offset/limit, in the request body.** Not query strings, not page tokens, not Link headers. The paginator injects `offset` and `limit` into the body and stops when the response item count drops below `limit`.
3. **Rate limiting is 2000 calls/min/endpoint.** Quota exhaustion returns HTTP 429 with a `Retry-After` header. The sliding-window limiter in `utils/rate_limiter.py` caps outgoing requests at the configured budget (`CLAROTY_RATE_LIMIT_PER_MIN`, default 2000) so we never trip the upstream gate; the client honors `Retry-After` if we do.

## Rate-limiter design

The existing `mcp-servers/azure-network-mcp/utils/rate_limiter.py` is an Azure SDK exception translator — not a real rate limiter. There is no token-bucket pattern in NetClaw to copy, so this PR introduces one. It is the simplest design that works:

- A deque of timestamps with a 60-second window.
- A single `asyncio.Lock` guarding the deque so two coroutines cannot both decide there is room.
- `acquire()` drops expired timestamps, sleeps if at capacity until the oldest falls out of the window, then records a new timestamp.
- Monotonic clock so wall-clock skew doesn't disturb the window.

The limiter is **shared across endpoints** because xDome's quota is per-endpoint but our token is shared across all tools — capping at the per-endpoint number is a safe upper bound that gives operators predictable behaviour.

## Filter syntax

xDome's `filter_by` body field accepts operator-keyed expressions:

| Op | Use |
|----|-----|
| `in` / `not_in` | exact-match include/exclude |
| `contains` / `not_contains` | substring (string fields only) |
| `in_subnet` / `not_in_subnet` | CIDR (IP fields) |
| `min` / `max` | numeric range (used for cvss_score, risk_score) |

Tool authors should prefer the simplest operator that satisfies the call. Compound filters are supported but adding tools that build them dynamically is out of v1 scope.

## Comparison to existing FastMCP REST servers in NetClaw

| Server | Pattern reused here |
|--------|---------------------|
| `suzieq-mcp` | Module-level singleton client, `validate_config()` at startup, fail-fast on missing env vars. |
| `azure-network-mcp` | `tools/` subdir layout, `clients/` + `models/` + `utils/` separation, GCF helper shim, FastMCP `mcp.tool()(fn)` registration. |
| `gnmi-mcp` | `itsm_gate.py` is a verbatim copy; same `CHG\d+` regex and `NETCLAW_LAB_MODE` bypass. |

## Lab-mode flag

NetClaw currently has two lab-mode env vars in use:

- `NETCLAW_LAB_MODE` (gnmi-mcp)
- `ITSM_LAB_MODE` (nautobot-mcp-v2, nautobot-routing-mcp)

This is a known inconsistency. **We pick `NETCLAW_LAB_MODE`** because (a) the `itsm_gate.py` we copied uses it, (b) the constitution mentions `NETCLAW_LAB_MODE`, and (c) introducing a `CLAROTY_LAB_MODE` would create a third name. The nautobot inconsistency is a separate cleanup, tracked as a follow-up.

## Deferred-scope rationale

The xDome API has 59 operations. v1 implements ~21. The deferred set is:

- **Edge sensor lifecycle** (add/update/delete locations, generate/rotate API keys, ingest sensor output) — sensor lifecycle wants its own ITSM CR taxonomy (sensor pairing, key rotation cadence) and probably its own skill. Reads are in scope so the asset-inventory skill can answer "what is monitoring this site".
- **Site CRUD** (add/update/delete sites + site groups + attribution rules) — site CRUD is administrative and rarely needed during day-to-day operations. Reads are in scope.
- **Organisation policy CRUD** (zones, firewall groups, ACL policies, zone policies, fw-group policies) — read of zones is in scope; CRUD is a separate workflow domain.
- **CMMS asset upsert + AI matching** — CMMS sync is its own integration concern; if needed, it gets its own skill.

The deferred list is in `mcp-servers/claroty-mcp/README.md` "Deferred to a future spec" so operators understand what's not here.

## GCF serialization

NetClaw uses GCF by default (per `config/openclaw.json` `tokenOptimization.gcfSerializationDefault`). The 9-line `utils/gcf_helper.py` is the project convention — `sys.path.insert` to reach `src/netclaw_tokens`, import `serialize_response`, fall back to `json.dumps` on any exception. We **do not** refactor GCF into a proper Python package import in this PR; that touches every MCP and is its own change.

## What this PR does NOT change

- The xDome upstream API (we just call it).
- The shared `src/netclaw_tokens` module.
- Existing MCP servers, skills, or specs.
- The HUD's React/Three.js layout — only `server.js` integration metadata is touched.
- The `ITSM_LAB_MODE` inconsistency in the nautobot MCPs (separate cleanup).
