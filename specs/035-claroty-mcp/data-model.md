# Data Model — Claroty xDome MCP

Lightweight, GCF-friendly dataclasses defined in `mcp-servers/claroty-mcp/models/responses.py`. These project the subset of xDome attributes a NetClaw operator typically wants; raw dicts pass through alongside the projected model when a tool needs to expose untyped fields.

## Entities

### Device

OT / IoT / IoMT asset under xDome management.

| Field | Type | Source |
|-------|------|--------|
| `id` | str | `id` or `device_id` or `uuid` |
| `name` | str? | `name` / `hostname` / `display_name` |
| `ip_address` | str? | `ip_address` / `ip` |
| `mac_address` | str? | `mac_address` / `mac` |
| `vendor` | str? | `vendor` |
| `model` | str? | `model` |
| `os` | str? | `os` / `operating_system` |
| `device_type` | str? | `device_type` / `type` |
| `device_purpose` | str? | `device_purpose` / `purpose` |
| `purdue_level` | str? | `purdue_level` (stringified) |
| `site_id` | str? | `site_id` |
| `site_name` | str? | `site_name` |
| `risk_score` | float? | `risk_score` |
| `first_seen` | str? | `first_seen` |
| `last_seen` | str? | `last_seen` |

### Alert

xDome security alert (event-driven detection).

| Field | Source |
|-------|--------|
| `id`, `title`, `severity`, `status`, `type`, `description` | direct |
| `site_id`, `site_name`, `assignee` | direct |
| `labels` | list[str] |
| `affected_device_count` | `affected_device_count` / `device_count` |
| `created_at`, `updated_at` | direct |

### Vulnerability

CVE-aligned finding.

| Field | Source |
|-------|--------|
| `id`, `cve_id`, `title`, `severity`, `description` | direct |
| `cvss_score` | `cvss_score` / `cvss` |
| `affected_device_count` | direct |
| `first_seen`, `last_seen` | direct |

### Site

Physical / logical site grouping.

`id`, `name`, `description`, `address`, `device_count`, `group_id`

### EdgeLocation

Remote sensor / collector.

`id`, `name`, `site_id`, `status`, `last_heartbeat`, `version`

### Server

Physical or virtual xDome management node.

`id`, `name`, `ip_address`, `role`, `status`, `version`

### OTActivityEvent

Single OT activity / protocol observation.

`id`, `timestamp`, `device_id`, `event_type`, `description`, `severity`

### AuditEntry

xDome audit-log entry.

`id`, `timestamp`, `user`, `action`, `target`, `details`

### OrganizationZone

Network segmentation zone.

`id`, `name`, `description`, `device_count`

## Relationships

- **Alert** ⟶ **Device** (many-to-many) — surfaced via `get_alert_with_devices` and `list_alerts` `affected_device_count`.
- **Vulnerability** ⟶ **Device** (many-to-many) — surfaced via `get_vulnerable_devices`.
- **Device** ⟶ **Site** (many-to-one) — `device.site_id` resolves into `Site`.
- **Device** ⟶ **OrganizationZone** (many-to-one) — via xDome's segmentation engine; surfaced opaquely as `zones` on raw device responses for v1.
- **EdgeLocation** ⟶ **Site** (many-to-one).
- **OTActivityEvent** ⟶ **Device** (many-to-one).
- **AuditEntry** is standalone.

## GCF serialisation behaviour

All dataclasses are flat (no nested dicts where avoidable) so the GCF serializer's tabular encoding gets maximum savings on list responses. The largest single saving is on `list_devices` (the most common heavy call).
