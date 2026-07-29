# Data Model — Halo MCP

Curated dataclasses defined in `mcp-servers/halo-mcp/models/responses.py`. Halo returns flat JSON objects (not JSON:API `{id,type,attributes}`) and they are very large — a `Faults` (ticket) object has 100+ fields. Each dataclass **curates the relevant subset** for the change-request + asset/ticket-context use cases. `from_resource(obj)` maps the flat Halo object onto those fields; `to_dict()` drops `None`; `to_json()` serializes via TOON (JSON fallback). A `_g(obj, *keys)` helper returns the first present, non-None value among alternate Halo key names. Every field is `Optional`.

Vocabulary: tickets = "Faults", ticket types = "Request Types", assets = "Devices".

## Entities

### Ticket (Halo "Fault")

Curated fields for context + change requests. `from_resource(obj, include_details=True)` — `details` is dropped in list mode.

| Field | Source key(s) |
|-------|---------------|
| `id` | `id` |
| `tickettype_id` | `tickettype_id` |
| `summary` | `summary` |
| `details` | `details` (only when `include_details`) |
| `status_id` / `status_name` | `status_id` / `status_name`\|`status` |
| `priority_id` / `priority_name` | `priority_id` / `priority_name`\|`priority` |
| `client_id` / `client_name` | `client_id` / `client_name` |
| `site_id` / `site_name` | `site_id` / `site_name` |
| `user_id` / `user_name` | `user_id` / `user_name` |
| `agent_id` | `agent_id` |
| `team` | `team` |
| `category_1` | `category_1` |
| `date_occurred` | `dateoccurred`\|`datecreated` |
| `last_update` | `lastactiondate`\|`last_update` |
| `assets` | `assets[]` → `[{id, name: inventory_number\|key_field\|name}]` |
| `customfields` | `customfields[]` → list of `CustomField` |

### TicketType (Halo "Request Type")

`from_resource(obj, include_fields=False)`; `fields` is populated only on the detail read.

| Field | Source key(s) |
|-------|---------------|
| `id` | `id` |
| `name` | `name` |
| `use` | `use`\|`typename` |
| `description` | `description` |
| `active` | `active` |
| `ticket_count` | `count`\|`ticket_count` |
| `fields` | `fields[]` → list of `TicketTypeField` (detail read only) |

### TicketTypeField (Halo "RequestTypeField")

A field's placement on a ticket type — the required/visible flags plus the field definition.

| Field | Source key(s) |
|-------|---------------|
| `fieldid` | `fieldid` |
| `fieldname` | `fieldname` |
| `seq` | `seq` |
| `required_agent` | `agentcheckboxmandatory` |
| `required_enduser` | `endusercheckboxmandatory` |
| `visible_agent` | `technew`\|`techdetail` |
| `visible_enduser` | `endusernew`\|`enduserdetail` |
| `fieldinfo` | `fieldinfo` → nested `FieldInfo` |

### FieldInfo

A field definition from `/api/FieldInfo` (standard or custom). The `id` here is the same numeric id used as a value id on a ticket (`customfields[].id`) and as a placement id on a ticket type (`RequestTypeField.fieldid`).

| Field | Source key(s) |
|-------|---------------|
| `id`, `name`, `label` | direct |
| `type`, `inputtype` | direct |
| `custom`, `usage` | direct |
| `mandatory`, `defaultvalue` | direct |
| `characterlimit`, `regex` | direct |
| `values` | `values[]` → `[{id, name: name\|value}]` (dropdown options) |

### CustomField

A custom-field **VALUE** carried on a ticket/asset (`customfields[]`).

`id`, `name`, `label`, `value`, `display`

### Asset (Halo "Device")

`from_resource(obj, include_fields=False)`; `fields` + `customfields` populate only on the detail read.

| Field | Source key(s) |
|-------|---------------|
| `id` | `id` |
| `inventory_number` | `inventory_number` |
| `key_field` | `key_field`\|`key_field_name` |
| `assettype_id` / `assettype_name` | direct |
| `client_id` / `client_name` | direct |
| `site_id` / `site_name` | direct |
| `status_id` | `status_id` |
| `open_ticket_count` / `total_ticket_count` | direct |
| `related_ticket_id` | `related_ticket_id` |
| `fields` | `fields[]` → `[{name: field_label\|name, value: display\|value}]` (detail) |
| `customfields` | `customfields[]` → list of `CustomField` (detail) |

### Action

A ticket action / note (`/api/Actions`).

| Field | Source key(s) |
|-------|---------------|
| `id` | `id` |
| `ticket_id` | `ticket_id`\|`faultid` |
| `who` | `who`\|`agentname` |
| `action_date` | `actiondate`\|`datetime` |
| `note` | `note`\|`note_html` |
| `outcome` | `outcome` |
| `hidden_from_user` | `hiddenfromuser`\|`important` |

### Client

`id`, `name`, `inactive`

### Site

`id`, `name`, `client_id`, `client_name`

### User

`id`, `name`, `emailaddress`, `client_id`, `site_id`

### Contract

| Field | Source key(s) |
|-------|---------------|
| `id` | `id` |
| `ref` | `ref`\|`reference` |
| `client_id` | `client_id` |
| `start_date` | `startdate`\|`start_date` |
| `end_date` | `enddate`\|`end_date` |

### KBArticle

`from_resource(obj, include_body=False)` — `article_body` populates only on the by-id read.

| Field | Source key(s) |
|-------|---------------|
| `id`, `name` | direct |
| `summary` | `summary`\|`description` |
| `article_body` | `article` (only when `include_body`) |
| `views` | `views`\|`viewcount` |

## Relationships

- **Ticket** → **TicketType** (many-to-one) via `ticket.tickettype_id`; the type's `fields[]` define what a ticket of that type may carry.
- **TicketTypeField** → **FieldInfo** (one-to-one) — the placement embeds the definition; the same id addresses the value in `customfields[]`.
- **Ticket** ↔ **Asset** (many-to-many) — `ticket.assets[]`; asset→tickets via `/api/Tickets?asset_id=`.
- **Ticket** → **Client / Site / User** (many-to-one) — resolved by id/name via `utils/resolver.py`.
- **Asset** → **Client / Site** (many-to-one); `Asset.related_ticket_id` + hierarchy surface CMDB/CI context.
- **Action** → **Ticket** (many-to-one) via `action.ticket_id`.
- **Contract** / **KBArticle** provide standalone account/knowledge context.

## Serialization behaviour

All dataclasses are flat (nested content is reduced to small `{id, name}` / `{name, value}` dicts) so the TOON tabular encoding gets maximum savings on list responses. `to_dict()` drops `None` so absent Halo fields never bloat the payload. Any tool called with `raw=true` bypasses these models and returns the untouched Halo JSON.
