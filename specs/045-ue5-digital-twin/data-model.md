# Data Model: UE5 Network Digital Twin & Looking-Glass

**Feature**: 045-ue5-digital-twin
**Date**: 2026-07-03

## Overview

This document defines the data structures this feature adds on top of 044's existing `NetworkDevice`/`Interface`/`Link` model (in `actors.py`/`materials.py`). Entities here are additive — nothing here replaces or restructures 044's existing types; interface actors, for instance, are a new *rendering* of interfaces that already exist as data on `NetworkDevice`, not a new device model.

## Entities

### InterfaceActor

Represents an individual up/up interface's 3D presence in the scene, spawned as a child of its parent device actor.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `parent_hostname` | string | Hostname of the owning device | Existing topology data |
| `interface_name` | string | Interface name (e.g. `GigabitEthernet0/1`) | Existing topology data (`source_interface`/`target_interface` on link specs, plus device interface inventory) |
| `operational_state` | enum (`up`, `down`) | Only `up` interfaces get an `InterfaceActor`; `down` interfaces are excluded from actor spawning entirely | pyATS/gNMI |
| `actor_name` | string | Generated UE5 actor name, following the existing `generate_device_actor_name`/`generate_link_actor_name` naming convention | Derived |
| `traffic_state` | float? (0.0-1.0, normalized utilization) | Optional traffic visual intensity; absent means default (non-traffic) appearance | pyATS/gNMI utilization counters |
| `health_state` | enum (`healthy`, `warning`, `critical`, `unreachable`) | Same status vocabulary already defined in `materials.py`'s `DeviceStatus` | pyATS/gNMI health poll |
| `alert_sticky` | bool | True if a trap-driven down/alert state is currently latched on this interface | Sticky-state registry (see below) |

**Relationships**: many `InterfaceActor` per `NetworkDevice` (0..N, only up/up); a `Link` references 0, 1, or 2 `InterfaceActor`s (falls back to device-level attachment when interface data is unavailable on one or both ends, per FR-003).

### DownInterfaceSummary

Not an actor — a compact, textual list attached to a device's existing label/info panel.

| Field | Type | Description |
|-------|------|-------------|
| `parent_hostname` | string | Owning device |
| `down_interface_names` | string[] | Names of all interfaces on this device currently reported down |

### Legend

A single persistent actor per topology build, generated from the live `DEVICE_TYPE_COLORS` mapping — never a hand-maintained duplicate.

| Field | Type | Description |
|-------|------|-------------|
| `actor_name` | string | Generated legend actor name (one per build) |
| `entries` | `{device_type: string, color: Color, label: string}[]` | Read directly from `materials.DEVICE_TYPE_COLORS` at build time |

### StickyAlertState (new registry in `telemetry.py`)

In-memory registry, not persisted, tracking which interfaces/links currently have a trap-latched alert.

| Field | Type | Description |
|-------|------|-------------|
| `key` | string | `"{hostname}:{interface_name}"` or a link identifier |
| `latched_since` | timestamp | When the down/alert trap was received |
| `trap_type` | string | e.g. `linkDown` |
| `cleared_by` | enum (`linkUp_trap`, `health_poll_recovery`, none) | What cleared the state, once cleared |

**Lifecycle**: created on a down-type trap for a known device/interface; cleared only by a matching `linkUp` trap or a health-poll-confirmed recovery (FR-018) — never by the mere passage of time or an unrelated refresh.

### LiveModeState (new, in `telemetry.py`)

Session-scoped control state for the existing `TelemetryPoller`.

| Field | Type | Description |
|-------|------|-------------|
| `active` | bool | Whether live mode is currently running |
| `started_at` | timestamp? | When live mode was last started |
| `poll_interval_seconds` | float | Reuses the existing `TelemetryPoller` configuration, not a new value |

### HistoryRecord (new, in `telemetry.py`)

One entry per recorded state change, appended to a session-scoped, bounded in-memory buffer.

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | timestamp | When the change occurred |
| `subject_key` | string | Device hostname, `"{hostname}:{interface}"`, or link identifier |
| `change_type` | enum (`health`, `traffic`, `trap`) | What kind of change this record captures |
| `previous_state` | any | State before the change (for accurate replay) |
| `new_state` | any | State after the change |

**Relationships**: `playback.py` reads a time-bounded slice of `HistoryRecord`s and replays them against the live scene in order.

### ConfigPanel / MetricsHUD (shared `Panel` primitive in `panels.py`)

| Field | Type | Description |
|-------|------|-------------|
| `parent_hostname` | string | Device the panel is anchored to |
| `panel_kind` | enum (`config`, `metrics`) | Which variant this is |
| `actor_name` | string | Generated panel actor name; a repeat request for the same `(parent_hostname, panel_kind)` replaces this actor rather than creating a new one (FR-025, FR-037) |
| `content` | string | Rendered text (raw running-config, or formatted CPU/memory/uptime) |
| `retrieved_at` | timestamp | When the underlying data was fetched — always the most recent request, never cached across requests |

### Incident (new, in `incidents.py`)

Not a locally-owned record — a reference to a PagerDuty incident, annotated with the correlation this feature performs.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `incident_id` | string | PagerDuty incident identifier | PagerDuty |
| `title`, `description`, `service_name` | string | Fields checked for hostname substring correlation | PagerDuty |
| `correlated_subject` | string? | The device hostname or link identifier this incident was matched to, if any | Derived (hostname substring match, FR-026) |
| `alarm_state_applied` | bool | Whether the corresponding actor currently shows the alarm visual state | Derived |

### ZoomGroup (new, in `hierarchy.py`)

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| `group_name` | string | Rack or site identifier | NetBox/Infrahub, or a manual grouping request |
| `zoom_level` | enum (`site`, `rack`, `device`) | Which level this grouping applies to | Derived |
| `member_hostnames` | string[] | Devices belonging to this group | NetBox/Infrahub placement data, or manual assignment |
| `source` | enum (`netbox`, `infrahub`, `manual`) | Where this grouping came from, per the resolution order in FR-033 | Derived |

**Relationships**: a device with no `ZoomGroup` membership from any source is reported as ungrouped (per spec.md's edge cases) rather than defaulted into an arbitrary group.

## State Transitions

### Trap-driven alert (Story 6)

```
[no alert] --(down-type trap received)--> [sticky alert latched]
[sticky alert latched] --(matching up-type trap)--> [no alert]
[sticky alert latched] --(health poll confirms recovery)--> [no alert]
[sticky alert latched] --(any unrelated refresh/poll)--> [sticky alert latched]  (unchanged)
```

### Live mode (Story 5)

```
[inactive] --(start_live_mode request)--> [active, poller running]
[active] --(stop_live_mode request)--> [inactive, poller stopped]
[active] --(NetClaw process restarts)--> [inactive]  (never persists across restarts)
```

### Zoom level (Story 11)

```
[site view] --(zoom into rack X)--> [rack X view]  (existing actors' visibility toggled, no rebuild)
[rack X view] --(zoom into device Y)--> [device Y view]
[any view] --(zoom out to site)--> [site view]
```
