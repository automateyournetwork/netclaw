# Halo API MCP Server (Feature 069)

A focused FastMCP/stdio server for **HaloPSA / HaloITSM / HaloCRM** (one REST API,
`info.title` "Halo API"). Two jobs for NetClaw:

1. **Open change requests** — the single gated write (confirm-before-submit).
2. **Review assets and their related tickets** for operational context.

Halo is heavily customized per organization: a "change request" is just a ticket
type whose id and custom fields differ per instance. This server exposes the
primitives (list ticket types, read a type's field schema, read a sample ticket,
create a change request); the `halo-*` skills orchestrate discovering the change
ticket type, confirming it with the operator, and caching it in Memory MCP.

**18 tools — 17 read-only + 1 gated write.** Halo vocabulary: tickets = "Faults",
ticket types = "Request Types", assets = "Devices".

## Tools

### Ticket types (2)
- `halo_list_ticket_types` — list types (use `can_create_only` to find creatable ones)
- `halo_get_ticket_type` — a type's full field **schema** (authoritative field discovery)

### Fields (2)
- `halo_list_fields` — the FieldInfo catalog (standard + custom, with dropdown values)
- `halo_get_field` — a single field definition by id

### Tickets (4 read + 1 write)
- `halo_get_ticket` — full ticket detail + linked assets/customfields (by id)
- `halo_list_tickets` — list/search, filter by ticket type / customer / asset / status
- `halo_get_ticket_actions` — a ticket's actions/notes history
- `halo_get_asset_tickets` — tickets related to an asset
- `halo_create_change_request` — **GATED WRITE.** `submit=false` (default) returns a
  preview of the exact POST body and writes nothing; `submit=true` creates the ticket

### Assets (3)
- `halo_get_asset` — asset detail + fields + ticket counts
- `halo_list_assets` — list/search assets
- `halo_get_asset_relationships` — CMDB/CI hierarchy context

### Context (4)
- `halo_list_clients` · `halo_list_sites` · `halo_list_users` · `halo_list_contracts`

### Knowledge (2)
- `halo_list_kb_articles` · `halo_get_kb_article`

## Transport & auth

- **Transport:** stdio (JSON-RPC on stdout; logs to stderr).
- **Auth:** OAuth2 **client-credentials**. The server fetches a bearer token from
  `<HALO_BASE_URL>/auth/token`, caches it until expiry, refreshes on 401, and sends
  `Authorization: Bearer` to `<HALO_BASE_URL>/api/*`.
- **Read-only by default:** the only write is `halo_create_change_request`, and it is
  confirm-before-submit — nothing is created unless a tool call passes `submit=true`.

## Environment variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `HALO_BASE_URL` | yes | Halo host, e.g. `https://<tenant>.halopsa.com` (no `/api`) |
| `HALO_CLIENT_ID` | yes | API application client id (client-credentials) |
| `HALO_CLIENT_SECRET` | yes | API application secret |
| `HALO_TENANT` | no | hosted multi-tenant id (blank for single-tenant) |
| `HALO_SCOPE` | no | OAuth scope (default `all`) |
| `HALO_AUTH_URL` | no | override token URL for self-hosted layouts |
| `HALO_VERIFY_SSL` | no | verify TLS (default `true`) |
| `HALO_TIMEOUT` | no | per-request timeout seconds (default `30`) |
| `HALO_PAGE_SIZE` | no | list page size (default `50`, server cap `100`) |
| `HALO_MAX_PAGES` | no | max pages per list call (default `20`) |
| `HALO_RATE_LIMIT` | no | proactive calls/min limiter (default `0` = off) |

## Install

```bash
# Windows:
pip install -r mcp-servers/halo-mcp/requirements.txt
# macOS / Linux:
pip3 install -r mcp-servers/halo-mcp/requirements.txt
```

## Configure

```bash
cp mcp-servers/halo-mcp/.env.example mcp-servers/halo-mcp/.env
# edit .env — set HALO_BASE_URL, HALO_CLIENT_ID, HALO_CLIENT_SECRET (+ HALO_TENANT)
```

Create the API application in Halo: **Configuration > Integrations > Halo API**, add
a **Client Credentials** application, and grant it the minimum permissions (read
tickets/assets, create tickets).

## Run (stdio)

```bash
cd mcp-servers/halo-mcp && python3 halo_mcp_server.py
```

Registered automatically by `config/openclaw.json` when NetClaw launches; there is
no need to run it by hand except for debugging.

## Change-request safety

`halo_create_change_request` is the only write and is **confirm-before-submit**:

1. Called with `submit=false` (default), it resolves ids, assembles the exact
   `POST /api/Tickets` array body, and returns it as a **preview** — no HTTP write.
2. The operator reviews the preview.
3. Only a follow-up call with `submit=true` performs the POST. Halo's own CAB /
   approval workflow then runs on the created change.
