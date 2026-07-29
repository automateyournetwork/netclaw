# Research — HaloPSA / HaloITSM MCP Server

## What is Halo?

Halo ships one product family — **HaloPSA / HaloITSM / HaloCRM** — over a single REST API (`info.title` "Halo API"). It is an MSP/ITSM platform: tickets, assets, clients, contracts, KB, billing, projects, and hundreds of configuration objects. The two things that shape this server:

1. **It is write-capable** (unlike a monitoring source), so the write must be gated.
2. **Its data model is per-org customized.** The change ticket type and the fields it carries are configured by each customer, so the server discovers the shape at runtime instead of hard-coding it.

The API vocabulary differs from the product UI:

| Product UI term | REST resource | Notes |
|-----------------|---------------|-------|
| Ticket | **Faults** (`/api/Tickets`) | POST body is an **array**; list filter for type is `requesttype_id`, but the ticket's own field / create payload uses `tickettype_id` |
| Ticket type | **Request Types** (`/api/TicketType`) | `?includedetails=true` returns `fields[].fieldinfo` |
| Asset | **Devices** (`/api/Asset`) | asset→tickets via `/api/Tickets?asset_id=` |
| Custom field | **FieldInfo** (`/api/FieldInfo`) | the same numeric id is definition id, value id, and placement id |

## Authentication — OAuth2 client-credentials

Halo uses an **OAuth2 client-credentials** grant (not HTTP Basic):

```
POST <HALO_BASE_URL>/auth/token
  grant_type=client_credentials
  client_id=<HALO_CLIENT_ID>
  client_secret=<HALO_CLIENT_SECRET>
  scope=<HALO_SCOPE, default "all">
  tenant=<HALO_TENANT>          # hosted multi-tenant only
→ { access_token, expires_in, ... }
```

The token endpoint lives on the **auth server** (`<base>/auth/token`), a different path from the resource API (`<base>/api`), but the same host. The client:

- caches the token until `expires_in` minus a 60 s skew,
- sends `Authorization: Bearer <token>` on every `/api/*` call,
- refreshes once transparently on a 401 and retries,
- surfaces a second 401/403 as a structured auth error naming the env vars to check.

`HALO_AUTH_URL` overrides the token URL for self-hosted layouts.

## API surface actually used

Only the endpoints the two workflows need are wrapped — a deliberately small slice of Halo's very large API:

### Tickets ("Faults") — `/api/Tickets`

- `GET /api/Tickets` — list; filters used: `requesttype_id`, `client_id`, `asset_id`, `status`, `open_only`, `search`, plus page params.
- `GET /api/Tickets/{id}?includedetails=true&includelinkedobjects=true` — single ticket with linked assets + custom-field values.
- `POST /api/Tickets` — **array body** `[{ tickettype_id, summary, details, client_id?, site_id?, user_id?, assets?:[{id}], customfields?:[{id|name, value}] }]`. The one write.

### Ticket types ("Request Types") — `/api/TicketType`

- `GET /api/TicketType` — list; filters `client_id`, `can_create_only`, `showcounts`.
- `GET /api/TicketType/{id}?includedetails=true` — the type's `fields[]` placement list; each entry carries `fieldinfo` (the `FieldInfo` definition — type, input type, mandatory, dropdown `values[]`) plus per-field required/visible flags for agent and end-user screens. **This is the authoritative "what fields does this org's change need" read.**

### Fields — `/api/FieldInfo`

- `GET /api/FieldInfo?includevalues=true` (+ `iscustomfieldsetup=true` for custom-only) — the master field catalog with dropdown option values.
- `GET /api/FieldInfo/{id}?getlookupvalues=true` — one field definition with its lookup values.

### Assets ("Devices") — `/api/Asset`

- `GET /api/Asset` — list; filters `client_id`, `assettype_id`, `search`.
- `GET /api/Asset/{id}?includedetails=true` — asset detail + fields + ticket counts.
- `GET /api/Asset/{id}?includedetails=true&includehierarchy=true` — CMDB/CI hierarchy view.
- Asset → tickets: `GET /api/Tickets?asset_id=<id>`.

### Account context

- `GET /api/Client` — clients (customers).
- `GET /api/Site` — sites (filter `client_id`).
- `GET /api/Users` — users/contacts (filters `client_id`, `site_id`).
- `GET /api/ClientContract` — contracts (filter `client_id`).

### Knowledge

- `GET /api/KBArticle` — KB list (filter `search`).
- `GET /api/KBArticle/{id}` — one article with body.

## Pagination — page-based, in query strings

Halo paginates by **page number**, in query strings (not cursors, not Link headers, not offset-in-body):

- `pageinate=true`, `page_no=<1-based>`, `page_size=<n>` (server cap 100; default 50 here).
- The client's `get_all()` walks pages, stops when a page under-fills or the running total reaches the response's `record_count`, and enforces a hard `HALO_MAX_PAGES` cap that returns `truncated: true` with a `next_page` so nothing paginates unboundedly.

## Name resolution

Operators speak in names ("the Acme client", "SW-CORE-01"), Halo speaks in ids. `utils/resolver.py` fetches the relevant list (passing Halo's `search` where supported) and matches **exact (case-insensitive) first, then substring**: one match wins, multiple → `Ambiguous` with candidate ids, none → `NotFound`. Any all-digit value is treated as an id and passed through with no API call. Assets match on `inventory_number` / `key_field` / `name`; ticket types, clients, and sites match on `name`.

## Key differences from Auvik (036)

The Auvik MCP was the immediately prior MSP integration; the deltas are the interesting engineering:

| Concern | Auvik (036) | Halo (069) |
|---------|-------------|------------|
| Auth | HTTP **Basic** (username + API key) | OAuth2 **client-credentials** token (fetch, cache, refresh-on-401) |
| Pagination | JSON:API **cursor** links (`page[after]`) | **page-number** query params (`page_no`/`page_size`) |
| Response shape | JSON:API `{id, type, attributes}` | flat JSON objects (100+ fields on a Fault) |
| Writes | none (read-only monitoring) | **one gated write** (`POST /api/Tickets`) |
| POST body | n/a | an **array** of ticket objects, not a single object |
| Schema | fixed vendor schema | **per-org customized** — ticket type + fields vary per instance |
| Multi-tenancy | tenant path/param on reads | `tenant` on the token request; single bearer thereafter |

The per-org-schema difference is why this server ships field-discovery reads (`halo_get_ticket_type`, `halo_list_fields`) and pushes the "which change type(s) — customer, internal, emergency…" selection to the skills + Memory MCP (an org commonly defines more than one change type, remembered as a per-category catalog).

## Serialization

Responses serialize via the project's TOON helper (`utils/toon_helper.py`, `gcf_dumps`) with a plain-`json.dumps` fallback when the serializer import is unavailable — matching the convention in the other NetClaw REST MCPs. Curated dataclasses (see `data-model.md`) keep list responses flat so the tabular encoding gets maximum savings; `raw=true` on any tool bypasses shaping and returns the untouched Halo payload.

## Deferred scope

Halo's API has hundreds of operations. v1 implements 18 tools for exactly two jobs (open changes, review asset/ticket context). Explicitly **deferred** to a future spec:

- Ticket **update / status change / action posting / assignment**, attachments, time entries, approvals.
- Invoicing, quotations, contracts CRUD, billing, projects, opportunities.
- Asset/client/site/user **creation and mutation** (reads only in v1).
- Reporting, dashboards, and the many analytic/report tools.

The deferred list is documented in `mcp-servers/halo-mcp/README.md` so operators understand what is intentionally absent.

## What this PR does NOT change

- The Halo upstream API (we only call it).
- Any existing MCP server, skill, or spec (additive-only; zero deletions).
- The shared serialization module.
- Memory MCP internals — the skills *use* Memory to remember the confirmed change type(s) as a per-category catalog; this server does not touch Memory storage directly.
