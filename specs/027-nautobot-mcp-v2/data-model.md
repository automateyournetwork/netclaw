# Data Model: Enhanced Nautobot MCP Server v2

**Feature**: 027-nautobot-mcp-v2
**Date**: 2026-04-09

## Entities

### NautobotConfig

Runtime configuration sourced from environment variables.

| Field | Type | Source | Default | Validation |
|-------|------|--------|---------|------------|
| url | str | `NAUTOBOT_URL` | (required) | Must be valid HTTP/HTTPS URL |
| token | str | `NAUTOBOT_TOKEN` | (required) | Non-empty string |
| verify_ssl | bool | `NAUTOBOT_VERIFY_SSL` | `false` | "true"/"false" |
| timeout | int | `NAUTOBOT_TIMEOUT` | `30` | Positive integer (seconds) |
| itsm_enabled | bool | `ITSM_ENABLED` | `false` | "true"/"false" |
| itsm_lab_mode | bool | `ITSM_LAB_MODE` | `true` | "true"/"false" |

**Validation rules**:
- `url` must not have a trailing slash
- Server must fail to start if `NAUTOBOT_URL` or `NAUTOBOT_TOKEN` are not set
- ITSM gating is active when `itsm_enabled=true` AND `itsm_lab_mode=false`

### GraphQL Query Patterns

Nautobot 3.1.0 GraphQL queries follow this pattern:

```
POST /api/graphql/
Authorization: Token <token>
Content-Type: application/json

{"query": "{ devices(name: \"HomeSwitch01\") { name status { name } } }"}
```

Filter arguments use Django-style lookups:
- Exact: `name: "HomeSwitch01"`
- Contains (case-insensitive): `name__ic: "switch"`
- Starts with: `name__isw: "Home"`
- Regex: `name__re: "^Home.*01$"`
- Pagination: `limit: 50, offset: 0`
- Boolean: `has_primary_ip: true`
- Search: `q: "switch"`

### REST API Write Patterns

Nautobot 3.1.0 REST writes follow this pattern:

```
POST /api/dcim/interfaces/
Authorization: Token <token>
Content-Type: application/json

{"device": "<uuid>", "name": "Gi1/0/49", "type": "1000base-t", "status": "<uuid>"}
```

Related objects require UUIDs. Resolution flow:
1. User provides human-readable name (e.g., status="Active")
2. Server queries GraphQL: `{ statuses(name: "Active") { id } }` (or uses REST lookup)
3. Server substitutes UUID into REST payload
4. Server issues REST POST/PATCH

### REST Endpoint Map

| Object Type | REST Endpoint | Create | Update | Delete |
|-------------|---------------|--------|--------|--------|
| Device | /api/dcim/devices/ | POST | PATCH /{id}/ | DELETE /{id}/ |
| Interface | /api/dcim/interfaces/ | POST | PATCH /{id}/ | DELETE /{id}/ |
| IP Address | /api/ipam/ip-addresses/ | POST | PATCH /{id}/ | DELETE /{id}/ |
| IP-to-Interface | /api/ipam/ip-address-to-interface/ | POST | — | DELETE /{id}/ |
| Prefix | /api/ipam/prefixes/ | POST | PATCH /{id}/ | DELETE /{id}/ |
| VLAN | /api/ipam/vlans/ | POST | PATCH /{id}/ | DELETE /{id}/ |
| Cable | /api/dcim/cables/ | POST | PATCH /{id}/ | DELETE /{id}/ |
| Location | /api/dcim/locations/ | — | — | — |
| Status | (lookup only) | — | — | — |
| Role | (lookup only) | — | — | — |

### ReconciliationReport

Output of the reconcile tool.

| Field | Type | Description |
|-------|------|-------------|
| device_name | str | Device being reconciled |
| timestamp | str | ISO 8601 timestamp of reconciliation |
| matches | list[InterfaceMatch] | Interfaces matching between live and SoT |
| mismatches | list[InterfaceMismatch] | Interfaces with field-level differences |
| device_only | list[InterfaceRecord] | Interfaces on live device but not in Nautobot |
| nautobot_only | list[InterfaceRecord] | Interfaces in Nautobot but not on live device |
| summary | dict | Counts: {matches, mismatches, device_only, nautobot_only, total_live, total_nautobot} |

### InterfaceMismatch

| Field | Type | Description |
|-------|------|-------------|
| name | str | Interface name |
| differences | list[FieldDiff] | Per-field differences |

### FieldDiff

| Field | Type | Description |
|-------|------|-------------|
| field | str | Field name (e.g., "enabled", "description", "mtu") |
| live | any | Value from live device |
| nautobot | any | Value from Nautobot |

## Nautobot 3.1.0 GraphQL Type Reference

Verified via introspection on 192.168.3.253:

### DeviceType fields (used)
`id`, `name`, `serial`, `status { name }`, `role { name }`, `platform { name }`, `location { name }`, `device_type { model manufacturer { name } }`, `primary_ip4 { address }`, `primary_ip6 { address }`, `interfaces { ... }`, `comments`

### InterfaceType fields (used)
`id`, `name`, `type`, `enabled`, `status { name }`, `description`, `mac_address`, `mtu`, `mode`, `device { name }`, `untagged_vlan { vid name }`, `tagged_vlans { vid name }`, `ip_addresses { address }`, `cable { id }`, `connected_endpoint`, `label`, `lag { name }`

### VLANType fields (used)
`id`, `vid`, `name`, `status { name }`, `locations { name }`, `vlan_group { name }`, `tenant { name }`, `role { name }`, `description`

### PrefixType fields (used)
`id`, `prefix`, `status { name }`, `locations { name }`, `role { name }`, `tenant { name }`, `description`

### IPAddressType fields (used)
`id`, `address`, `status { name }`, `dns_name`, `description`, `tenant { name }`, `interface_assignments { interface { name device { name } } }`

### CableType fields (used)
`id`, `type`, `status { name }`, `label`, `color`, `length`, `length_unit`, `termination_a_type`, `termination_a_id`, `termination_b_type`, `termination_b_id`
