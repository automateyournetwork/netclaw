# MCP Tool Contracts — Halo MCP

All **18 tools** are registered on the `halo-mcp` FastMCP instance and exposed via stdio JSON-RPC. **17 are read-only; exactly 1 is a gated write** (`halo_create_change_request`). Every tool returns a **string** (TOON/JSON, or a JSON error envelope) and accepts a trailing `raw: bool = False` — when `raw=true` the untouched Halo payload is returned instead of the curated model.

## Error & result envelopes

- Read tools return the shaped model(s). List tools return `{"items": [...], "truncated": bool, "next_page"?: int, "record_count"?: int}`.
- Failures surface uniformly as `{"error": {"code", "message", "details"}}` with codes `ValidationError | Ambiguous | NotFound | UpstreamError` — tools never raise to the MCP layer.
- Name parameters (`ticket_type`, `customer`, `site`, `asset`) accept **either a name or a numeric id**; a name is resolved (exact→substring), and ambiguity/absence returns `Ambiguous`/`NotFound` with candidates.

---

## Ticket types (2) — Halo "Request Types"

### `halo_list_ticket_types`

```
halo_list_ticket_types(
    can_create_only: Optional[bool] = None,
    customer: Optional[str] = None,
    showcounts: Optional[bool] = None,
    raw: bool = False,
) -> str
```

List ticket types. Use this to **discover which type(s) an org uses for CHANGES** (Halo is per-org customized, so the change type's id/name vary — and an org may define several, e.g. a customer change vs an internal change). `can_create_only=true` limits to types the API app may create; `customer` (name or id) scopes to a client; `showcounts` adds ticket counts.

### `halo_get_ticket_type`

```
halo_get_ticket_type(ticket_type: str, raw: bool = False) -> str
```

Get a ticket type's full field **SCHEMA** (authoritative field discovery). `ticket_type` is a name or numeric id. Returns the type plus `fields[]`: each field's id/name, the underlying `FieldInfo` (type, input type, dropdown values), and required/visible flags for agent and end-user screens. Pair with a sample ticket (`halo_get_ticket`) for a concrete example.

## Fields (2) — `FieldInfo` catalog

### `halo_list_fields`

```
halo_list_fields(custom_only: Optional[bool] = None, raw: bool = False) -> str
```

List field definitions (`FieldInfo`) with dropdown values. `custom_only=true` for custom fields only. The same numeric id is the field's definition id, its value id on a ticket (`customfields[].id`), and its placement id on a ticket type — so this resolves field ids ↔ names ↔ option values.

### `halo_get_field`

```
halo_get_field(field: str, raw: bool = False) -> str
```

Get a single field definition (`FieldInfo`) by **numeric id**, with lookup values.

## Tickets (4 read + 1 gated write) — Halo "Faults"

### `halo_get_ticket`

```
halo_get_ticket(ticket: str, raw: bool = False) -> str
```

Read a single ticket by **numeric id** — full detail + linked assets/customfields. Tickets are addressed by id only (not name). Useful as a concrete example of a populated change ticket.

### `halo_list_tickets`

```
halo_list_tickets(
    ticket_type: Optional[str] = None,
    customer: Optional[str] = None,
    asset_id: Optional[int] = None,
    status: Optional[str] = None,
    open_only: Optional[bool] = None,
    search: Optional[str] = None,
    raw: bool = False,
) -> str
```

List/search tickets. `ticket_type` (name or id) → `requesttype_id`; `customer` (name or id) → `client_id`; `asset_id` returns tickets linked to that asset; `search` is free-text; `open_only=true` limits to open tickets. Paginated.

### `halo_get_ticket_actions`

```
halo_get_ticket_actions(ticket: str, raw: bool = False) -> str
```

List a ticket's actions/notes history (`/Actions`) by **numeric ticket id**.

### `halo_get_asset_tickets`

```
halo_get_asset_tickets(asset: str, open_only: Optional[bool] = None, raw: bool = False) -> str
```

The core "review an asset's tickets for context" tool. `asset` is a name / inventory number / id. `open_only=true` for open tickets only.

### `halo_create_change_request` — THE ONE GATED WRITE

```
halo_create_change_request(
    summary: str,                              # required
    details: str,                              # required
    ticket_type: str,                          # required (name or id)
    customer: Optional[str] = None,            # name or id → client_id
    site: Optional[str] = None,                # name or id → site_id
    user: Optional[int] = None,                # numeric user id
    asset: Optional[str] = None,               # name/inventory-number/id → links asset
    custom_fields: Optional[dict] = None,      # {field id-or-name: value}
    submit: bool = False,                      # GATE: false = preview only
    raw: bool = False,
) -> str
```

Open a change request in Halo. **GATED — previews unless `submit=true`.**

- **Required fields**: `summary`, `details`, `ticket_type`. Any missing → `ValidationError` with no HTTP call.
- **`submit=false` (DEFAULT — no write)**: resolves ids, normalizes `custom_fields` into `customfields[{id|name, value}]`, assembles the exact array body, and returns:
  ```json
  {"preview": true, "would_post": "/api/Tickets",
   "body": [{"tickettype_id": ..., "summary": ..., "details": ...,
             "client_id"?: ..., "site_id"?: ..., "user_id"?: ...,
             "assets"?: [{"id": ...}], "customfields"?: [{"id"|"name": ..., "value": ...}]}],
   "note": "Change request NOT submitted. Review the body, then re-call with submit=true after explicit user approval."}
  ```
- **`submit=true` (the only real write)**: `POST /api/Tickets` and returns `{"created": true, "ticket": {...}}`. Only call this **after** the operator explicitly approves the previewed body. Halo's own CAB/approval workflow runs after creation.
- `custom_fields` accepts a dict `{id_or_name: value}` or a list of `{"id"|"name", "value"}`; numeric identifiers become `{"id": int}`, non-numeric become `{"name": str}`. Learn the required set via `halo_get_ticket_type`.

## Assets (3) — Halo "Devices"

### `halo_get_asset`

```
halo_get_asset(asset: str, raw: bool = False) -> str
```

Read a single asset by name/inventory-number/id — detail + fields + ticket counts.

### `halo_list_assets`

```
halo_list_assets(
    customer: Optional[str] = None,
    assettype_id: Optional[int] = None,
    search: Optional[str] = None,
    raw: bool = False,
) -> str
```

List/search assets, optionally scoped by customer (name or id), asset type, or free text.

### `halo_get_asset_relationships`

```
halo_get_asset_relationships(asset: str, raw: bool = False) -> str
```

Get an asset's CMDB/CI hierarchy and relationship context (by name or id). Returns `{asset_id, hierarchy, related_ticket_id, child_count}` (or the raw payload with `raw=true`).

## Context (4) — clients / sites / users / contracts

### `halo_list_clients`

```
halo_list_clients(search: Optional[str] = None, raw: bool = False) -> str
```

List/search clients (customers). Use to resolve a client name to its id.

### `halo_list_sites`

```
halo_list_sites(customer: Optional[str] = None, search: Optional[str] = None, raw: bool = False) -> str
```

List/search sites, optionally scoped to a customer (name or id).

### `halo_list_users`

```
halo_list_users(
    customer: Optional[str] = None,
    site_id: Optional[int] = None,
    search: Optional[str] = None,
    raw: bool = False,
) -> str
```

List/search users/contacts, optionally scoped to a customer or site.

### `halo_list_contracts`

```
halo_list_contracts(customer: Optional[str] = None, raw: bool = False) -> str
```

List client contracts/agreements (`/ClientContract`), optionally scoped to a customer.

## Knowledge (2) — KB articles

### `halo_list_kb_articles`

```
halo_list_kb_articles(search: Optional[str] = None, raw: bool = False) -> str
```

Search the Halo knowledge base for articles (resolution/runbook context).

### `halo_get_kb_article`

```
halo_get_kb_article(article: str, raw: bool = False) -> str
```

Get a single KB article by **numeric id**, including its body.

---

## Tool inventory (authoritative — matches `REGISTERED_TOOL_NAMES`)

| # | Tool | Kind |
|---|------|------|
| 1 | `halo_list_ticket_types` | read |
| 2 | `halo_get_ticket_type` | read |
| 3 | `halo_list_fields` | read |
| 4 | `halo_get_field` | read |
| 5 | `halo_get_ticket` | read |
| 6 | `halo_list_tickets` | read |
| 7 | `halo_get_ticket_actions` | read |
| 8 | `halo_get_asset_tickets` | read |
| 9 | `halo_create_change_request` | **gated write** |
| 10 | `halo_get_asset` | read |
| 11 | `halo_list_assets` | read |
| 12 | `halo_get_asset_relationships` | read |
| 13 | `halo_list_clients` | read |
| 14 | `halo_list_sites` | read |
| 15 | `halo_list_users` | read |
| 16 | `halo_list_contracts` | read |
| 17 | `halo_list_kb_articles` | read |
| 18 | `halo_get_kb_article` | read |
