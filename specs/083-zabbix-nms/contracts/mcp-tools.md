# Tool Contract — `zabbix-mcp` (spec 083 / R11)

**Adopted, not authored.** `mpeirone/zabbix-mcp-server`, GPL-3.0, pinned `0722f48`, vendored **unmodified**.
Runs from a **dedicated virtualenv** (needs fastmcp 3.x; five repo servers pin `<3`).

**Manifest measured 589 tokens** (2,234 chars) — 11.8% of the 5,000 ceiling, via a live MCP handshake.

## The three tools

| Tool | Purpose |
|---|---|
| `zabbix_api(method, params)` | Generic JSON-RPC passthrough to any allowed Zabbix method |
| `zabbix_api_docs(method)` | Upstream documentation for a method |
| `zabbix_api_list(object)` | Available methods for an object |

## What NetClaw controls, and what it does not

| | |
|---|---|
| **Controls** | `READ_ONLY=true` **forced by NetClaw** (the upstream launcher defaults it to `false` — measured); a destructive-method deny-list; TLS verification; the venv; the credentials |
| **Does NOT control** | the tool surface, the request shape, whether the correct `value_type` is used, whether history or trends is queried |

**That second row is the whole risk.** There is no chokepoint between the agent and the API, so FR-001–FR-006
are enforced by the skills. A caller that ignores them gets a wrong answer and nothing stops it. Recorded as
a first for NetClaw (FR-033a).

## Verified behaviour (live Zabbix 7.0.29)

```
zabbix_api(host.get)     → [{"hostid":"10084","host":"Zabbix server"}]
zabbix_api(host.delete)  → REFUSED: "Server is in read-only mode ..."
```

Read/write classification is a **method-name prefix heuristic** (`get`, `version`, `check`, `export`) — not a
curated list. A future read method not matching those prefixes would be wrongly refused; a write method that
did match would be wrongly allowed. The deny-list is the second layer for exactly that reason.

## The methods the skills use

| Need | Method | Trap |
|---|---|---|
| Inventory | `host.get` (+`selectInterfaces`/`selectTags`), `hostgroup.get` | — |
| Item discovery | `item.get` → **`value_type`, `history`, `trends`** | **must precede any history call** |
| Recent metrics | `history.get` | **`value_type` defaults to 3; 84/121 items are 0** |
| Older metrics | `trend.get` | hourly min/avg/max; numeric only; empty for <1h-old installs |
| Current problems | `problem.get` | empty is legitimate, ≠ unreachable |
| Problem history | `event.get` | heavier |
| Availability | `host.get` interface `available` + `problem.get` | one poller's view |

## What this integration will not do

- **No writes, at all** — acknowledging, enabling/disabling hosts, maintenance windows. Clarification
  decision; adding any requires a NetClaw-owned layer carrying both gates *and* per-call audit (FR-023,
  FR-038c).
- **No NMS configuration** — hosts, templates, triggers, items.
- **No per-call GAIT** — inherited limitation, acceptable only because this is read-only (FR-038).
- **No trap or flow reception** — `snmptrap-mcp` and `ipfix-mcp` own those.
- **No current device state** — `pyats`, `multivendor-cli`, `fortinet` own that.
