# Feature Specification: HaloPSA / HaloITSM MCP Server

**Feature Branch**: `069-halo-mcp-server`
**Created**: 2026-07-24
**Status**: Draft
**Input**: Add a Halo (HaloPSA / HaloITSM / HaloCRM) MCP server + skills to NetClaw for two focused jobs: opening **change requests** and reviewing **assets and their related tickets** — with first-class handling for Halo's per-org customization (the change ticket type and its fields differ per instance).

## Why this is different from Auvik (036)

Auvik is a read-only monitoring source with a fixed schema. Halo is a **write-capable ITSM** whose data model is **reconfigured by every customer**. There is no universal "change request" object: a change is simply a ticket of whatever ticket type that org designated for changes, carrying whatever custom fields that org attached to it. The server therefore cannot ship a hard-coded change form. Instead it exposes the **primitives to learn each org's shape at runtime** (list ticket types, read a type's field schema, read a sample populated ticket) and one **gated write** to assemble and create the change once the shape is known and the operator has approved it.

## User Scenarios & Testing

### User Story 1 — Open a change request (Priority: P1)

A NetClaw operator needs to open a change request in Halo for an upcoming maintenance window. Their Halo instance defines **more than one** change type — a customer-facing "Change Control" and a separate internal change (ids vary) — each with its own custom fields (change window, risk level, approver). The operator does not know which type applies here, nor the ticket-type/field ids off-hand — the assistant has to work out *which* change this is, discover the matching type, confirm it, and remember it per category.

**Why this priority**: Opening changes is the headline write and the whole reason the server carries a write path. Every safety guarantee (confirm-before-submit, per-org discovery) exists to serve this flow.

**The per-org customization flow** (the heart of this feature):

1. **Discover (per category)** — determine which change this is (customer vs internal vs emergency…; ask the operator if ambiguous — instances often define several change types), then `halo_list_ticket_types(can_create_only=true)` enumerates the creatable ticket types.
2. **Confirm with the user** — the assistant presents the candidate(s) and asks which one is *this* change's type (never guesses; never auto-picks when several look change-shaped).
3. **Remember** — the confirmed type is merged into a per-instance **change-type catalog** (`{instance -> [{id, name, category}]}`) in **Memory MCP**, so the next change of that category skips discovery.
4. **Learn the fields** — `halo_get_ticket_type(<id>)` returns the type's field schema (`fields[].fieldinfo`: required/optional, input type, dropdown options); `halo_get_ticket(<a recent change id>)` supplies a concrete populated example so the assistant sees real values in context.
5. **Assemble** — the assistant maps the operator's intent onto `summary`, `details`, and `custom_fields{field id-or-name -> value}`.
6. **Confirm before submit** — `halo_create_change_request(..., submit=false)` returns the exact `POST /api/Tickets` body as a **preview**; nothing is written.
7. **Create** — only after the operator explicitly approves the preview does a second call with `submit=true` perform the write. Halo's own CAB/approval workflow then runs on the created change.

**Independent Test**: With valid `HALO_*` client-credentials env, invoke the `halo-change-request` skill with "open a change to reboot the core switch Saturday night". Verify the assistant discovers the change type, confirms it, previews a body containing `tickettype_id` and any `customfields[]`, and creates the ticket only after approval.

**Acceptance Scenarios**:

1. **Given** a configured Halo tenant, **When** the operator asks "what ticket types can I open a change under?", **Then** `halo_list_ticket_types(can_create_only=true)` returns each type's id/name.
2. **Given** a chosen change type, **When** the operator asks "what fields does that change type need?", **Then** `halo_get_ticket_type(<id>)` returns `fields[]` with each field's `mandatory`/visibility flags and `fieldinfo` (type + dropdown values).
3. **Given** an assembled change, **When** the assistant calls `halo_create_change_request(..., submit=false)`, **Then** the response is `{"preview": true, "would_post": "/api/Tickets", "body": [...]}` and **no** HTTP write occurs.
4. **Given** an approved preview, **When** the assistant re-calls with `submit=true`, **Then** the ticket is created and `{"created": true, "ticket": {...}}` is returned.
5. **Given** a missing `summary`/`details`/`ticket_type`, **When** the create is attempted, **Then** a `ValidationError` is returned with no HTTP call.

### User Story 2 — Review an asset and its related tickets (Priority: P2)

An operator triaging a recurring problem on a specific device needs to see the asset's detail and every ticket ever raised against it, to decide whether this is a known-recurring issue before opening anything new.

**Why this priority**: The read-side context loop is the everyday value and the "read-before-write" foundation for User Story 1 — you review the asset's history before you propose a change to it.

**Independent Test**: Invoke the `halo-asset-context` skill with "show me SW-CORE-01 and its open tickets" and verify the response includes the asset (by name resolution), its fields/ticket counts, and the list of related tickets.

**Acceptance Scenarios**:

1. **Given** an asset name, **When** the operator asks "look up SW-CORE-01", **Then** `halo_get_asset("SW-CORE-01")` resolves the name to an id and returns detail + fields + ticket counts.
2. **Given** an asset, **When** the operator asks "what tickets are on it?", **Then** `halo_get_asset_tickets("SW-CORE-01", open_only=true)` returns the linked open tickets.
3. **Given** a ticket of interest, **When** the operator asks "what's the history?", **Then** `halo_get_ticket_actions(<id>)` returns the action/note timeline.
4. **Given** an ambiguous asset name, **When** two devices match, **Then** the resolver returns `{"error": {"code": "Ambiguous", ...}}` with candidate ids rather than guessing.

### Edge Cases

- Halo returns HTTP 401 mid-session (token expired server-side): the client transparently refreshes the bearer token once and retries; a second 401/403 surfaces as an auth error.
- Halo returns HTTP 429: the client honors `Retry-After` and retries up to 3 times, then returns a rate-limited error.
- A list endpoint under-fills a page: the page-based paginator stops cleanly; a hard `HALO_MAX_PAGES` cap sets `truncated: true` with a `next_page`.
- A name resolves to multiple entities: `Ambiguous` with candidates; a name resolves to none: `NotFound`. An all-digit value is treated as an id and passed through without a lookup.
- Missing `HALO_BASE_URL` / `HALO_CLIENT_ID` / `HALO_CLIENT_SECRET`: the client raises a clear `ValueError` on first use naming the missing var.
- `submit=true` with an invalid custom-field id: Halo rejects the POST; the structured upstream error is surfaced, and (because writes are gated) it can only reach Halo after a human approved the preview.

## Requirements

### Functional Requirements

- **FR-001**: System MUST list ticket types ("Request Types") with `can_create_only`, `customer`, and `showcounts` filters, so an operator can discover which type(s) an org uses for changes (an org may define several — e.g. a customer change and an internal change — and the skill selects/confirms the right one per category).
- **FR-002**: System MUST return a ticket type's full field **schema** (`fields[]` with per-field required/visible flags and the underlying `FieldInfo`, including dropdown option values) as the authoritative field-discovery read.
- **FR-003**: System MUST list field definitions (`FieldInfo`) with dropdown values, and fetch a single field by id, so field ids ↔ names ↔ option values resolve.
- **FR-004**: System MUST read a single ticket ("Fault") by numeric id with full detail, linked assets, and custom-field values — usable as a concrete example of a populated change.
- **FR-005**: System MUST list/search tickets filtered by ticket type, customer, asset id, status, open-only, and free-text search.
- **FR-006**: System MUST list a ticket's actions/notes history by ticket id.
- **FR-007**: System MUST list the tickets related to an asset (resolved by name or id), with an open-only filter.
- **FR-008**: System MUST open a change request as a ticket of a caller-supplied ticket type, mapping caller intent onto `summary`, `details`, and `customfields[]`, resolving customer/site/asset names to ids, and linking the asset.
- **FR-009**: The change-request write MUST be **confirm-before-submit**: with `submit=false` (default) it performs NO HTTP write and returns the exact array POST body as a preview; a real POST happens only on a follow-up call with `submit=true`.
- **FR-010**: System MUST read a single asset ("Device") by name/inventory-number/id with detail fields and ticket counts; list/search assets scoped by customer, asset type, or search; and return an asset's CMDB/CI relationship view.
- **FR-011**: System MUST provide account-context reads: list clients (customers), sites, users/contacts, and contracts — each optionally scoped to a customer (and users to a site).
- **FR-012**: System MUST search the knowledge base for articles and fetch a single KB article (including its body) by id.
- **FR-013**: System MUST authenticate via OAuth2 **client-credentials**, caching the bearer token until shortly before expiry, refreshing once on a 401, and never logging the secret or token.
- **FR-014**: System MUST resolve human names to Halo ids (exact-then-substring, single match wins; multiple → `Ambiguous` with candidates; none → `NotFound`) and pass all-digit values through as ids.
- **FR-015**: System MUST page-paginate list endpoints (`pageinate`/`page_no`/`page_size`), stop on an under-filled page, and cap at `HALO_MAX_PAGES` with a `truncated`/`next_page` signal.
- **FR-016**: Every tool MUST return a result string and surface upstream/validation failures as a uniform `{"error": {"code","message","details"}}` envelope (`ValidationError | Ambiguous | NotFound | UpstreamError`) rather than raising.

### Key Entities

- **Ticket** (Halo "Fault"): id, tickettype_id, summary, details, status, priority, client/site/user, agent/team, category, dates, linked assets, custom-field values.
- **TicketType** (Halo "Request Type"): id, name, use, active, ticket_count, and (on detail) `fields[]` of **TicketTypeField** (placement + required/visible flags + `FieldInfo`).
- **FieldInfo**: a field definition (standard or custom) — id, name, label, type/inputtype, mandatory, default, character limit, regex, and dropdown `values[]`.
- **CustomField**: a custom-field VALUE carried on a ticket/asset (`customfields[]`).
- **Asset** (Halo "Device"): id, inventory_number, key_field, asset type, client/site, status, open/total ticket counts, detail fields, custom fields.
- **Action**: a ticket action/note (who, date, note, outcome, hidden-from-user).
- **Client / Site / User / Contract**: account-context entities.
- **KBArticle**: knowledge-base article (name, summary, body, views).

## Success Criteria

### Measurable Outcomes

- **SC-001**: An operator can go from "open a change" to a reviewed preview in fewer than 5 chat turns, with the change ticket type discovered and confirmed — not hard-coded.
- **SC-002**: 100% of change creations pass through the confirm-before-submit gate — verified by reading `tools/tickets.py` and by smoke #3 in `quickstart.md` (a `submit=false` call makes zero writes).
- **SC-003**: A second change against the same instance skips discovery because the confirmed change tickettype_id was cached in Memory MCP.
- **SC-004**: Adding Halo does not regress any existing skill — `git diff --stat main` shows zero deletions and touches only Halo additions plus the coherence files.
- **SC-005**: The Coherence Checklist in `checklists/requirements.md` passes with every box ticked (per Constitution Principle XI).

## Assumptions

- The operator has created a **Client Credentials** API application in Halo (Configuration → Integrations → Halo API) with the minimum permissions to read tickets/types/assets and create tickets.
- The target is a **cloud** Halo instance; self-hosted layouts are supported by overriding `HALO_AUTH_URL` but are not the primary path.
- Discovery/confirmation/memory of the change ticket type(s) — an org may define several (customer, internal, emergency…), remembered as a per-category catalog — is orchestrated by the `halo-*` skills; the server exposes primitives, not the workflow.
- Halo's own CAB / approval workflow runs after ticket creation — the server creates the change, it does not approve it.
- Ticket **update**, action posting, attachments, time entries, invoicing, and the ~700 other Halo operations are explicitly **out of v1 scope** (see `research.md` "Deferred scope").
