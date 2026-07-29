# Quickstart — Halo (HaloPSA / HaloITSM) MCP Server

## Prerequisites

- **Python 3.10+**.
- A **Halo cloud tenant** (HaloPSA / HaloITSM / HaloCRM — one API).
- An **OAuth2 client-credentials API application** created in Halo:
  **Configuration → Integrations → Halo API → New**, authentication method **Client Credentials**. Grant it the minimum permissions for these workflows: read tickets / ticket types / assets / clients, and **create tickets** (for change requests). Copy the **Client ID** and **Client Secret**.
- These become the env vars:

  | Variable | Required | Description |
  |----------|:--------:|-------------|
  | `HALO_BASE_URL` | yes | Halo host, e.g. `https://<tenant>.halopsa.com` (no `/api`) |
  | `HALO_CLIENT_ID` | yes | API application client id |
  | `HALO_CLIENT_SECRET` | yes | API application secret |
  | `HALO_TENANT` | no | hosted multi-tenant id (blank for single-tenant) |
  | `HALO_SCOPE` | no | OAuth scope (default `all`) |
  | `HALO_AUTH_URL` | no | override token URL for self-hosted layouts |
  | `HALO_VERIFY_SSL` / `HALO_TIMEOUT` | no | TLS verify (default `true`) / per-request seconds (default `30`) |
  | `HALO_PAGE_SIZE` / `HALO_MAX_PAGES` | no | page size (default `50`, cap `100`) / max pages (default `20`) |
  | `HALO_RATE_LIMIT` | no | proactive calls/min limiter (default `0` = off; 429 backoff always on) |

## 1. Install

```bash
# Windows:
pip install -r mcp-servers/halo-mcp/requirements.txt
# macOS / Linux:
pip3 install -r mcp-servers/halo-mcp/requirements.txt
```

Or re-run the NetClaw modular installer from the repo root and select the **Halo** component — it picks up the new catalog entry + install step automatically.

## 2. Configure

```bash
cp mcp-servers/halo-mcp/.env.example mcp-servers/halo-mcp/.env
# edit .env — set HALO_BASE_URL, HALO_CLIENT_ID, HALO_CLIENT_SECRET (+ HALO_TENANT if hosted)
```

The MCP server is registered in `config/openclaw.json` under `mcpServers.halo-mcp`.

## 3. Standalone smoke test

```bash
cd mcp-servers/halo-mcp && python3 halo_mcp_server.py
```

On stderr you should see the client init line and:

```
Starting halo-mcp server (transport=stdio, base_url=https://<tenant>.halopsa.com, tools=18)
```

If `HALO_BASE_URL` / `HALO_CLIENT_ID` / `HALO_CLIENT_SECRET` are unset, the first tool call raises a clear `ValueError` naming the missing var — fix `.env` first.

## 4. Getting-started smoke (via the agent)

Start the gateway and TUI, then run these prompts in order.

### Smoke #1 — Auth + read path

```
"List the ticket types I can open a change under"
```

Expect `halo_list_ticket_types(can_create_only=true)` to return a list of `{id, name}`. This proves the OAuth2 token was acquired and the resource API is reachable. If you get an auth error, re-check the client id/secret/tenant/scope.

### Smoke #2 — Asset + ticket context (User Story 2)

```
"Show me asset SW-CORE-01 and its open tickets"
```

Expect `halo_get_asset("SW-CORE-01")` (name resolved to id) with fields + ticket counts, then `halo_get_asset_tickets("SW-CORE-01", open_only=true)` listing the linked open tickets. An ambiguous name returns an `Ambiguous` envelope with candidates — pick one by id.

### Smoke #3 — Change-request GATE (must NOT write)

```
"Open a change to reboot the core switch Saturday night"
```

Watch the flow: the assistant discovers/confirms the change ticket type, learns its fields (`halo_get_ticket_type`), then calls `halo_create_change_request(..., submit=false)`. The response MUST be:

```json
{"preview": true, "would_post": "/api/Tickets", "body": [ ... ], "note": "Change request NOT submitted. ..."}
```

Confirm **no ticket was created** in Halo. This is the core safety guarantee.

### Smoke #4 — Change-request SUBMIT (the one write)

After reviewing the preview:

```
"Looks good — submit it"
```

Only now does the assistant re-call with `submit=true`, and you should see `{"created": true, "ticket": {...}}` plus a new ticket in Halo. Halo's own CAB/approval workflow then runs on the created change.

### Smoke #5 — Field discovery

```
"What fields does the change ticket type require?"
```

Expect `halo_get_ticket_type(<id>)` returning `fields[]` with `mandatory` flags and, for dropdowns, the `fieldinfo.values[]` options. This is what lets the assistant assemble `custom_fields` correctly.

### Smoke #6 — Regression

Confirm an existing skill still works (e.g. run an unrelated read against another MCP). Adding Halo is additive-only — `git diff --stat main` should show zero deletions.

## 5. Per-org memory note

Change ticket types differ per Halo instance, and an instance often defines **several** (e.g. a customer change and an internal change). On first use of a given category the `halo-change-request` skill works out which change this is, discovers the candidate types (`halo_list_ticket_types`), **confirms the right one with you**, and merges it into a per-instance change-type catalog (`{instance → [{id, name, category}]}`) in **Memory MCP**. Later changes of a known category skip discovery; a new category — or a different Halo tenant — triggers a fresh discover-and-confirm.

## 6. Constitution checklist

Tick every box in `specs/069-halo-mcp-server/checklists/requirements.md` before opening the PR.

## 7. Blog post

Per Principle XVII, draft a WordPress milestone post. If the WordPress MCP is unavailable, save the draft as `docs/blog/2026-07-24-halo-mcp.md` and present it for review before publishing.
