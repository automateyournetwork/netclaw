# GAIT Session Log — Halo (HaloPSA / HaloITSM) MCP Server

> **Audit trail recorded per Constitution Principle IV (Immutable Audit Trail).**
>
> The `gait-session-tracking` skill normally records turns live against the
> `gait_mcp` server during NetClaw agent execution. This build ran in a Claude
> Code shell where `gait_mcp` is not registered, so no turns were recorded live.
> This document is the trail assembled from the session transcript and the
> working tree on branch `069-halo-mcp-server`, in the spirit Principle IV
> requires: every operational decision is recorded, with the original action
> referenced rather than overwritten.

---

## Session metadata

| Field | Value |
|-------|-------|
| Session ID | `halo-mcp` |
| Branch | `069-halo-mcp-server` (base: `main` @ `12325d0`) |
| Date | 2026-07-24 |
| Agent | Claude Opus 4.8 (Claude Code shell) |
| Operator | Ben (RedEye Networks) |
| Spec | `specs/069-halo-mcp-server/` |
| Server | `mcp-servers/halo-mcp/` — 18 tools (17 read + 1 gated write) |
| Outcome | Server + per-MCP docs + full SDD spec complete; coherence wiring, skills, tests, and milestone are the tracked remaining tail |

---

## Turn 0 — Clarifying questions (scope decisions)

Four decisions framed the feature before any code was written. Each is recorded
with the answer chosen and why.

**Q1 — Auth model?**
> **Decided: OAuth2 client-credentials, cloud.** Halo's cloud API uses a
> client-credentials grant against `<base>/auth/token`, distinct from Auvik's
> HTTP Basic. Self-hosted layouts are supported via a `HALO_AUTH_URL` override
> but are not the primary path. Consequence: the client must acquire, cache,
> refresh-on-401, and never log the bearer token.

**Q2 — Write posture?**
> **Decided: exactly one write, confirm-before-submit.** The only mutation is
> `halo_create_change_request`, and it defaults to `submit=false` — assemble the
> exact `POST /api/Tickets` array body and return it as a **preview** with no
> HTTP write. A real POST requires a follow-up `submit=true` after explicit
> operator approval. Satisfies Principles I / II / III without an ITSM gate
> (Halo *is* the ITSM; its native CAB/approval runs after creation).

**Q3 — How to handle per-org customization?**
> **Decided: schema + sample-ticket field discovery, remembered in Memory MCP.**
> The change ticket type and its custom fields differ per instance, so the server
> ships field-discovery reads (`halo_get_ticket_type` → `fields[].fieldinfo`;
> `halo_list_fields`; `halo_get_ticket` for a concrete populated example) rather
> than a hard-coded change form. The skills orchestrate discover → confirm with
> the operator → cache the confirmed `{instance → change tickettype_id}` in
> Memory MCP → learn fields → assemble → confirm-before-submit → create. The
> server stays a stateless primitive layer.

**Q4 — Tool scope?**
> **Decided: broad-but-focused — 18 tools for two jobs.** Cover the two jobs
> (open changes; review asset/ticket context) plus the context reads they need
> (ticket types, fields, tickets, actions, assets, clients/sites/users/contracts,
> KB). Defer the hundreds of other Halo operations (ticket update, invoicing,
> projects, entity CRUD) to a future spec, documented in the README.

---

## Turn 1 — Server implementation

**Asked** *(implicit)* Build the Halo MCP server per the four decisions.

**Decided**

- Mirror the cleanest NetClaw REST-MCP layout: `tools/` + `clients/` + `models/`
  + `utils/`, per-domain tool modules, a lazily-created singleton client with
  fail-fast config validation.
- `clients/halo_client.py`: OAuth2 client-credentials token acquire/cache/refresh;
  `get()` / `get_all()` (page-number pagination: `pageinate`/`page_no`/`page_size`)
  / `post()` (Halo's **array** ticket body); 401 single transparent refresh; 429
  `Retry-After` backoff; structured `{success, data, error}` envelope (never raises).
- `models/responses.py`: 12 curated dataclasses (`Ticket`, `TicketType`,
  `TicketTypeField`, `FieldInfo`, `CustomField`, `Asset`, `Action`, `Client`,
  `Site`, `User`, `Contract`, `KBArticle`) projecting the relevant subset of
  Halo's very large flat objects; `_g()` handles alternate key names.
- `utils/resolver.py`: name→id resolution (exact→substring; single match wins,
  multiple → `Ambiguous`, none → `NotFound`; all-digit values pass through).
- `tools/tickets.py`: the four ticket reads plus `halo_create_change_request` —
  required-field validation (no HTTP), id resolution, `_normalize_custom_fields`
  into `customfields[{id|name, value}]`, exact array-body assembly, and the
  preview-vs-submit gate.
- `halo_mcp_server.py`: 18 `@mcp.tool()` wrappers; `TOOL_FUNCS` +
  `REGISTERED_TOOL_NAMES` exports for test introspection; stdio transport;
  logging to stderr (stdout reserved for JSON-RPC); secret never logged.

**Created**

```
mcp-servers/halo-mcp/halo_mcp_server.py
mcp-servers/halo-mcp/clients/halo_client.py
mcp-servers/halo-mcp/models/responses.py
mcp-servers/halo-mcp/tools/{_common,ticket_types,fields,tickets,assets,context,knowledge}.py
mcp-servers/halo-mcp/utils/{constants,resolver,pagination,rate_limiter,toon_helper}.py
mcp-servers/halo-mcp/{requirements.txt,.env.example,README.md}
```

---

## Turn 2 — Vocabulary + API-surface alignment

**Decided**

- Encoded Halo's UI↔REST vocabulary gap in `utils/constants.py` so future
  maintainers aren't surprised: tickets = **Faults** (`/api/Tickets`), ticket
  types = **Request Types** (`/api/TicketType`), assets = **Devices**
  (`/api/Asset`), custom fields = **FieldInfo** (`/api/FieldInfo`).
- Captured the one-id-three-roles fact: the same numeric id is a field's
  definition id (`FieldInfo.id`), its value id on a ticket (`customfields[].id`),
  and its placement id on a ticket type (`RequestTypeField.fieldid`) — which is
  what lets `custom_fields` be written back by id.
- Captured the list-vs-create key asymmetry: the ticket **list** filter is
  `requesttype_id`, but the ticket's own field and the **create** payload use
  `tickettype_id`.

---

## Turn 3 — SDD spec authored

**Asked** Author the Spec-Driven Development artifacts (Constitution XVI).

**Decided**

- Wrote the full spec set under `specs/069-halo-mcp-server/`, mirroring the shape
  and tone of `specs/035-claroty-mcp/`. Kept every artifact **accurate to the
  actual implementation** by reading the server/model/tool files rather than
  inventing behavior.
- `contracts/mcp-tools.md` transcribes the exact 18 tool signatures + docstrings
  from `halo_mcp_server.py`; `data-model.md` transcribes the actual dataclass
  fields + source keys from `models/responses.py`; `research.md` documents the
  real Halo API slice used and the Auvik (036) contrasts (OAuth vs Basic,
  page-paging vs JSON:API cursors, array POST bodies, per-org schema).

**Created**

```
specs/069-halo-mcp-server/{spec,plan,research,data-model,quickstart,tasks}.md
specs/069-halo-mcp-server/contracts/mcp-tools.md
specs/069-halo-mcp-server/checklists/requirements.md
specs/069-halo-mcp-server/gait-session-log.md   (this file)
```

---

## Phases executed vs remaining

| Phase | Status |
|-------|--------|
| Foundation (scaffold, requirements, .env.example) | ✅ done |
| Utilities (constants, pagination, rate_limiter, toon_helper, resolver) | ✅ done |
| Client + models | ✅ done |
| Tools (6 modules, 18 tools) | ✅ done |
| Server entry (FastMCP, stdio, 18 registered) | ✅ done |
| Per-MCP docs (README, .env.example) | ✅ done |
| SDD spec (this directory) | ✅ done |
| Skills — `halo-change-request`, `halo-asset-context`, `halo-ticket-context` | ✅ done |
| Repo-wide coherence (openclaw.json, installer catalog + steps, ui, SOUL/SOUL-SKILLS/TOOLS/README, .gitignore, .env.example) | ✅ done |
| Tests (`tests/halo-mcp/` — resolver, pagination, client, tool suites + gated-write) | ✅ done |
| Live smoke + regression | ⏳ pending (T-038–T-039, needs a tenant) |
| Milestone blog (Principle XVII) | ⏳ pending (T-040) |

---

## Constitution principle compliance

| Principle | Compliance evidence |
|-----------|---------------------|
| **I — Safety-first** | Exactly one write; it defaults to a no-write preview. Field-discovery + review reads precede any change. |
| **II — Read-before-write** | 17 read tools alongside 1 write; the documented change flow requires reads first (list types → read schema → read a sample ticket → assemble → preview). |
| **III — Change-gated** | The write is confirm-before-submit: `submit=false` makes no HTTP call and returns the exact body for human review; `submit=true` is required to create. Halo's native CAB/approval runs after creation. |
| **IV — Immutable audit trail** | This document. |
| **V — MCP-native** | FastMCP server, stdio transport, JSON-RPC lifecycle handled by FastMCP. |
| **VIII — Verify after change** | The submit path returns `{created, ticket}` echoing the created object. |
| **XI — Full-stack artifact coherence** | Tracked in `checklists/requirements.md`; code + per-MCP docs + SDD done, wiring/skills/tests/blog pending. |
| **XIII — Credential safety** | `HALO_CLIENT_SECRET` only in env; never logged (startup log prints base_url/tenant/scope, not the secret); token held in memory. |
| **XV — Backwards compatibility** | Additive only; no shared schema or existing MCP/skill/spec changed. To be confirmed structurally via `git diff --stat main` = zero deletions before PR. |
| **XVI — Spec-driven development** | Full SDD spec at `specs/069-halo-mcp-server/`. |
| **XVII — Milestone documentation** | Blog draft tracked as T-040; present for review before publishing. |

---

## Remaining (not satisfiable from a code-only session)

- **Live end-to-end smoke** against a Halo tenant — needs a client-credentials
  API application with read + create-ticket permissions (offline component smoke
  passed; the gated write's preview path is verifiable without a tenant).
- **Regression diff** (`git diff --stat main` = zero deletions) to confirm before
  PR, and the **WordPress milestone blog** (Principle XVII) — the tracked tail in
  `tasks.md` (T-039, T-040). The repo-wide coherence wiring, the three skills, and
  the `tests/halo-mcp/` suite are complete.

## Turn 4 — Live smoke + post-feedback corrections

**Asked** Run the live smoke against a real Halo tenant; then operator feedback.

**Did / Decided**

- **Live smoke: 18/18 tools green** through the real MCP server (stdio) against a
  real Halo cloud tenant (28 ticket types, 105 clients, 6360 field defs, 1000s of
  assets/tickets). `halo_create_change_request(submit=false)` assembled a correct
  change body against the org's real change type and **wrote nothing** — the gate
  verified against production.
- **Correction to Turn 1** — the 429 `Retry-After` value was being dropped:
  `parse_retry_after(dict(resp.headers))` lowercased the header key while the parser
  matched the capitalized `Retry-After`, so the backoff always fell to the 1s
  fallback. Fixed (pass the case-insensitive `resp.headers`; parser made
  case-insensitive) and pinned by a test. Same latent bug noted in the auvik client
  (PR #165) — flagged as a follow-up task.
- **Correction to Q3 (change-type model)** — the earlier decision cached a single
  `{instance → change tickettype_id}`. Operator feedback: their instance defines
  **multiple** change types (id 27 = customer change; a separate internal change),
  and many orgs split changes (customer / internal / emergency). Superseded: the
  change type is a **per-category set**, remembered as a catalog
  `{instance → [{id, name, category}]}` under Memory key `change_ticket_types`. The
  `halo-change-request` skill now determines the category (asking if ambiguous),
  presents candidates without auto-picking, and confirms per category. spec.md,
  research.md, quickstart.md, and contracts/mcp-tools.md updated to match. Server
  code unchanged (`halo_create_change_request` already takes any `ticket_type`).

**End of session log.**
