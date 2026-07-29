---
name: halo-change-request
description: "Open a change request in HaloPSA / HaloITSM through a discover-preview-confirm-submit workflow, with the confirmed change ticket type cached in Memory. Use when raising a Halo change, opening a CR in Halo, submitting a change ticket, or asking NetClaw to file a change in HaloPSA."
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["HALO_BASE_URL", "HALO_CLIENT_ID", "HALO_CLIENT_SECRET"] } } }
---

# Halo Change Request

Open a **change request** in Halo through a strict discover -> preview -> confirm -> submit flow. Halo is **HaloPSA / HaloITSM** (the same product and the same REST API — HaloPSA is the MSP edition, HaloITSM the internal-IT edition). A "change request" in Halo is not a fixed object type: it is simply a **ticket type** ("Request Type") whose numeric id and custom fields are configured per organization — and an org often defines **several** change types (for example a customer-facing change and an internal change). This skill figures out *which* change is being raised, discovers the matching type, confirms it with a human, remembers it **per category**, learns its fields, and gates the single write behind explicit approval.

## MCP Server

- **Server**: `halo-mcp` (NetClaw-authored, `mcp-servers/halo-mcp/`)
- **Command**: `python3 -u mcp-servers/halo-mcp/halo_mcp_server.py` (stdio transport)
- **Auth**: OAuth2 client-credentials — `HALO_CLIENT_ID` / `HALO_CLIENT_SECRET` against `HALO_BASE_URL` (token from `<base>/auth/token`, resource API at `<base>/api`)
- **Python**: 3.10+  ·  **Dependencies**: `fastmcp`, `httpx`, `python-dotenv`
- **Read/write posture**: **read-only except one gated write** — `halo_create_change_request` is the ONLY tool in the entire server that can mutate Halo, and it previews (no write) unless `submit=true`.

This skill also uses the **Memory MCP** server (`memory-mcp`) to cache the confirmed change ticket type per Halo tenant.

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `halo_list_ticket_types` | `can_create_only?`, `customer?`, `showcounts?` | Discover ticket types ("Request Types"). Use `can_create_only=true` to find the org's CHANGE type |
| `halo_get_ticket_type` | `ticket_type` | Authoritative field **schema** for a type — required/optional/visible field definitions |
| `halo_list_fields` | `custom_only?` | Master `FieldInfo` catalog (ids <-> names <-> dropdown option values) |
| `halo_get_field` | `field` | One field definition by numeric id, with its lookup values |
| `halo_list_tickets` | `ticket_type?`, `customer?`, `asset_id?`, `status?`, `open_only?`, `search?` | Find a **sample** existing change to copy field patterns from |
| `halo_get_ticket` | `ticket` (numeric id) | Read one populated ticket as a concrete example |
| `halo_create_change_request` | `summary`, `details`, `ticket_type`, `customer?`, `site?`, `user?`, `asset?`, `custom_fields?`, `submit=false` | **THE ONLY WRITE.** Previews the exact POST body unless `submit=true` |
| `halo_list_clients` | `search?` | Resolve a Halo **Client** name to its id (the `customer` param) |
| `halo_list_sites` | `customer?`, `search?` | Resolve a site within a client |
| `halo_list_users` | `customer?`, `site_id?`, `search?` | Resolve the requesting contact/user |
| `memory_get_facts` | `entity`, `key?` | Recall the tenant's change-type catalog (`key="change_ticket_types"`) |
| `memory_record_fact` | `entity`, `key`, `value`, `metadata?` | Merge a confirmed change type ({id, name, category}) into the catalog |
| `memory_record_decision` | `context`, `decision`, `rationale`, ... | Log the human's ticket-type confirmation |
| `memory_invalidate` | `fact_id`, `reason` | Retire a cached ticket type that no longer resolves |

## Key Concepts

- **Halo == HaloPSA == HaloITSM.** Same API; only the packaging differs. Everything here works against either.
- **"Change request" is a ticket type, not a built-in.** Its id and its custom fields are per-org. You must **discover** it (never hard-code it) and **confirm** it with a human before trusting it.
- **There is often more than one change type.** Many orgs split changes — e.g. a **customer** change vs an **internal** change, or standard / normal / emergency. Treat the change type as a *set*: work out *which* change this is (ask if unclear), keep a per-category catalog in Memory, and confirm the specific type before filing.
- **The Halo "Client" is the customer.** Every tool that scopes to a customer org takes it as the `customer` param (a client name or numeric id), which the server resolves to a `client_id`. When someone says "the client," they mean this.
- **Tickets are "Faults"; ticket types are "Request Types"; assets are "Devices"** in Halo's API vocabulary — the tool names hide this, but error text may show it.
- **One write, always gated.** `halo_create_change_request` with `submit=false` performs NO HTTP write; it returns the exact array body that *would* be POSTed to `/api/Tickets`. The real POST happens only on a second call with `submit=true`.
- **Memory holds the *type*, never the *contents*.** Cache only the confirmed ticket-type id and its field metadata — never credentials, never the text of any change ticket.

## Workflow

The full change-request flow, step by step. Do not skip steps (a) or (c).

### (a) Determine the change category, then recall or discover its type

An organization usually has **more than one** change type — most commonly a
**customer** change (raised against a client) and an **internal** change (internal
IT / infrastructure), and sometimes standard / normal / emergency splits. So first
decide *which* change this is, then resolve the matching type. Never assume there is
only one.

1. **Decide the category.** Infer from context: a change scoped to a specific
   customer/client is a **customer** change; a change with no client (internal infra,
   your own systems) is an **internal** change. **If it is at all ambiguous, ASK the
   operator** — e.g. *"Is this a customer change or an internal change?"* Use a short
   lowercase label for the category (`customer`, `internal`, `emergency`, ...).

2. **Recall the tenant's change-type catalog:**
   ```
   memory_get_facts(entity="halo-<tenant>", key="change_ticket_types")
   ```
   The value is a list of `{"id":..., "name":..., "category":...}` — the change types
   already confirmed for this instance. `<tenant>` is from `HALO_TENANT`, or the host
   of `HALO_BASE_URL` (e.g. `halo-acme` for `acme.halopsa.com`).

3. **If the needed category is already in the catalog**, validate it still resolves
   with `halo_get_ticket_type(ticket_type=<id>)`:
   - resolves cleanly -> use that id, go to (b).
   - no longer resolves (renamed/deleted) -> drop it from the catalog, re-discover
     (below), and `memory_invalidate` the stale fact when you rewrite the catalog.

4. **If the category is missing (or was invalidated), discover:**
   ```
   halo_list_ticket_types(can_create_only=true)
   ```
   This commonly returns **several** change-shaped types (e.g. "Change Request",
   "Internal Change", "Emergency Change"). **Present the candidates and ask the
   operator which one is the `<category>` change** — do NOT auto-pick when more than
   one looks like a change, and do NOT collapse them into a single "the change type".

5. **On confirmation, merge it into the catalog** (add the new category; keep the
   others — do not overwrite the whole list with a single entry):
   ```
   memory_record_fact(entity="halo-<tenant>", key="change_ticket_types",
                      value=<updated JSON list including {"id":<id>,"name":"<name>","category":"<category>"}>)
   memory_record_decision(context="Halo change type for <tenant> / <category>",
                          decision="Use ticket type <id> (<name>) for <category> changes",
                          rationale="Operator-confirmed from halo_list_ticket_types(can_create_only=true)")
   ```

Carry the selected `<id>` into (b) and (c). If a single request genuinely spans both
a customer and an internal change, that is **two** change tickets — run the flow once
per category, confirming each.

### (b) Learn the fields (schema + a real example)

1. **Authoritative schema** — which fields are required vs optional, and their dropdown values:
   ```
   halo_get_ticket_type(ticket_type=<id>)
   ```
   Use `halo_list_fields` / `halo_get_field` to resolve any custom `FieldInfo` ids <-> names <-> option values you need.

2. **A concrete example** — read a real, populated change to see how fields are actually filled:
   ```
   halo_list_tickets(ticket_type=<id>)      # find a recent one
   halo_get_ticket(ticket=<sample id>)      # inspect its summary/details/customfields
   ```

3. Cache field metadata alongside the type id (`metadata={...}`) if it helps future runs — but only the metadata, never any ticket's contents.

### (c) Assemble, PREVIEW, then STOP for approval

1. Resolve the customer/site/user as needed (`halo_list_clients`, `halo_list_sites`, `halo_list_users`).
2. **Preview (no write):**
   ```
   halo_create_change_request(
       summary="...", details="...", ticket_type="<id>",
       customer="<client name or id>", site="...", user=<id>, asset="...",
       custom_fields={<id-or-name>: <value>, ...},
       submit=false)
   ```
3. **Present the returned preview `body` to the operator verbatim.** It is the exact `/api/Tickets` payload.
4. **STOP. Do NOT submit until the operator explicitly approves this specific preview** (Constitution XIV, Human-in-the-Loop). A vague "go ahead" earlier does not count — approval is per change, on the previewed body.
5. **Only after explicit approval**, re-call the identical arguments with `submit=true` to perform the one real write.

### (d) Record the outcome in GAIT

Log the decision and the created ticket id to the GAIT audit trail (see gait-session-tracking): the confirmed ticket type, the previewed body, the approval, and the resulting Halo ticket id.

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **gait-session-tracking** | **Mandatory.** Record the ticket-type decision, the preview, the human approval, and the created ticket id in the GAIT audit trail |
| **memory** | Caches the per-category change-type catalog per tenant (`entity="halo-<tenant>"`, `key="change_ticket_types"`); no credentials or ticket contents |
| **halo-ticket-context** | Read the created change and its action history afterward for follow-up |
| **halo-asset-context** | Review the affected asset and its open tickets before proposing the change |
| **servicenow-change-workflow** | Sibling gated-change pattern (STOP-until-confirmed) if the org also runs ServiceNow |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HALO_BASE_URL` | Yes | Halo host, e.g. `https://<tenant>.halopsa.com` |
| `HALO_CLIENT_ID` | Yes | OAuth2 client-credentials application id (Configuration > Integrations > Halo API) |
| `HALO_CLIENT_SECRET` | Yes | OAuth2 client secret |
| `HALO_TENANT` | Optional | Tenant identifier (also used to key Memory as `halo-<tenant>`) |
| `HALO_SCOPE` | Optional | OAuth2 scope (default `all`) |
| `HALO_AUTH_URL` | Optional | Override the auth-server URL for self-hosted layouts |
| `HALO_VERIFY_SSL` | Optional | `true`/`false` TLS verification (default `true`) |
| `HALO_TIMEOUT` | Optional | Per-request timeout in seconds (default 30) |
| `HALO_PAGE_SIZE` / `HALO_MAX_PAGES` | Optional | Pagination tuning (defaults 50 / 20) |
| `HALO_RATE_LIMIT` | Optional | Requests/minute cap (0 = disabled) |

## Important Rules

- **There is exactly ONE write tool** — `halo_create_change_request`. Every other Halo tool is read-only. Never attempt any other mutation through this server.
- **Never submit without explicit, per-change approval.** Always preview first (`submit=false`), present the exact body, STOP, and only re-call with `submit=true` after the operator approves *that* preview (Constitution XIV).
- **Discover the change ticket type(s); never assume it, and never assume there is only one.** An org may have customer / internal / emergency change types. Work out which category applies (ask if unclear), confirm the specific candidate with a human, and keep a per-category catalog. When discovery returns several change-shaped types, present them and let the operator choose — do not auto-pick.
- **Store only the ticket-type id + field metadata in Memory — NEVER credentials, secrets, or the contents of any ticket.** Memory keys off `halo-<tenant>`.
- **Re-validate the cache.** If the cached type no longer resolves via `halo_get_ticket_type`, `memory_invalidate` it and re-discover.
- **Halo == HaloPSA == HaloITSM** — the workflow is identical for both editions.
- **GAIT logging is mandatory** for the decision and the created ticket id.
