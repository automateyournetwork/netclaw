---
name: halo-ticket-context
description: "Review a HaloPSA / HaloITSM ticket for resolution context — its detail, action/note history, linked assets, and related KB runbooks — read-only. Use when investigating a Halo ticket, gathering resolution context, reading a ticket's note history, or finding runbooks for an open issue."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["HALO_BASE_URL", "HALO_CLIENT_ID", "HALO_CLIENT_SECRET"] } } }
---

# Halo Ticket Context

Review a **ticket** in Halo to gather everything needed to understand and resolve it — the ticket detail, its full action/note history, the assets it touches, and related knowledge-base runbooks. Entirely **read-only**. Halo is **HaloPSA / HaloITSM** (the same product and REST API); tickets are called **"Faults"** in Halo's API vocabulary.

## MCP Server

- **Server**: `halo-mcp` (NetClaw-authored, `mcp-servers/halo-mcp/`)
- **Command**: `python3 -u mcp-servers/halo-mcp/halo_mcp_server.py` (stdio transport)
- **Auth**: OAuth2 client-credentials — `HALO_CLIENT_ID` / `HALO_CLIENT_SECRET` against `HALO_BASE_URL`
- **Python**: 3.10+  ·  **Dependencies**: `fastmcp`, `httpx`, `python-dotenv`
- **Read/write posture**: The whole server is **read-only except one gated write** (`halo_create_change_request`, in the halo-change-request skill). **Every tool in this skill is read-only.**

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `halo_get_ticket` | `ticket` (numeric id) | Read one ticket ("Fault") — summary, details, status, priority, client/site/user, and linked assets |
| `halo_get_ticket_actions` | `ticket` (numeric id) | The ticket's actions/notes history (the investigation timeline) |
| `halo_list_tickets` | `ticket_type?`, `customer?`, `asset_id?`, `status?`, `open_only?`, `search?` | Find a ticket by type, customer, asset, status, or free text |
| `halo_get_asset` | `asset` (name / inventory-number / id) | Read a linked asset surfaced on the ticket |
| `halo_list_kb_articles` | `search?` | Search the Halo knowledge base for related runbooks |
| `halo_get_kb_article` | `article` (numeric id) | Read one KB article, including its body |

## Key Concepts

- **Halo == HaloPSA == HaloITSM.** Same API for both editions.
- **Tickets are "Faults"** and are addressed by **numeric id only** — they are not name-resolvable. If you don't have the id, find it with `halo_list_tickets` (by `customer`, `asset_id`, `status`, or `search`) first.
- **The Halo "Client" is the customer.** Filter ticket lists to an org with the `customer` param (a client name or id).
- **Actions are the story.** `halo_get_ticket_actions` returns the note/action timeline — the richest source of what has already been tried and what remains.
- **Assets link tickets to devices.** `halo_get_ticket` returns linked assets; read them with `halo_get_asset` (or pivot to the **halo-asset-context** skill).
- **KB articles are the runbooks.** Search with `halo_list_kb_articles`, then read the full body with `halo_get_kb_article` for resolution/runbook context.
- **Read-only.** Nothing here writes. If a change is warranted, hand off to **halo-change-request**.

## Workflow

Assemble resolution context for a ticket:

1. **Identify the ticket.** If you only have a description, find its id first:
   ```
   halo_list_tickets(customer="<client>", search="<keywords>", open_only=true)
   ```

2. **Read the ticket detail:**
   ```
   halo_get_ticket(ticket=<id>)
   ```
   Capture status, priority, client/site/requesting user, and any linked assets.

3. **Read the note history** (the core step):
   ```
   halo_get_ticket_actions(ticket=<id>)
   ```
   Reconstruct the timeline: what was diagnosed, what was tried, current state.

4. **Inspect linked assets** surfaced in step 2:
   ```
   halo_get_asset(asset="<linked asset name or id>")
   ```
   For the device's own ticket history and CI dependencies, switch to **halo-asset-context**.

5. **Find related runbooks** in the knowledge base:
   ```
   halo_list_kb_articles(search="<symptom / technology>")
   halo_get_kb_article(article=<id>)   # read the full runbook body
   ```

6. **Report** a resolution-context summary: the issue, timeline of actions to date, affected assets, applicable KB runbooks, and the recommended next step (resolve, escalate, or raise a change via halo-change-request).

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **gait-session-tracking** | **Mandatory.** Record every ticket/action/KB query in the GAIT audit trail |
| **halo-asset-context** | Pivot from a linked asset to its full device context (tickets + CI relationships) |
| **halo-change-request** | If resolution requires a change, hand off here (preview -> confirm -> submit) |
| **rag** | Cross-reference vendor documentation in the RAG knowledge base alongside Halo KB runbooks |
| **memory** | Recall prior sessions about the same ticket, client, or recurring symptom |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HALO_BASE_URL` | Yes | Halo host, e.g. `https://<tenant>.halopsa.com` |
| `HALO_CLIENT_ID` | Yes | OAuth2 client-credentials application id |
| `HALO_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `HALO_TENANT` | Optional | Tenant identifier |
| `HALO_SCOPE` | Optional | OAuth2 scope (default `all`) |
| `HALO_AUTH_URL` | Optional | Override the auth-server URL for self-hosted layouts |
| `HALO_VERIFY_SSL` | Optional | `true`/`false` TLS verification (default `true`) |
| `HALO_TIMEOUT` | Optional | Per-request timeout in seconds (default 30) |
| `HALO_PAGE_SIZE` / `HALO_MAX_PAGES` | Optional | Pagination tuning (defaults 50 / 20) |
| `HALO_RATE_LIMIT` | Optional | Requests/minute cap (0 = disabled) |

## Important Rules

- **Read-only skill.** None of these tools change Halo. The only write in the entire `halo-mcp` server is `halo_create_change_request` (halo-change-request skill).
- **Tickets are addressed by numeric id only.** Use `halo_list_tickets` to find the id when you don't have it; scope by the Halo `customer` (Client) in multi-client tenants.
- **Halo == HaloPSA == HaloITSM** — identical behavior for both editions.
- **GAIT logging is mandatory** for all queries.
- **Escalate, don't mutate.** If the context implies a change, route it through **halo-change-request** (preview -> confirm -> submit); never try to write from this skill.
