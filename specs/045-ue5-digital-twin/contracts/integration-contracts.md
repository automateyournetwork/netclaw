# Integration Contracts: UE5 Network Digital Twin & Looking-Glass

**Feature**: 045-ue5-digital-twin
**Date**: 2026-07-03

## Overview

Unlike 044 — which defined contracts against a single upstream (the UE5.8 MCP server) — this feature is primarily an orchestration layer across six existing MCP integrations plus the UE5 MCP server itself. This document defines the *internal* contract each new/extended `ue5-network-viz` submodule exposes to the rest of the skill, and the *capability* contract each submodule expects from its upstream MCP integration (not exact upstream tool signatures, which belong to those integrations' own contracts, e.g. 010-telemetry-receivers' for `snmptrap-mcp`).

## UE5 MCP Server (existing, `ue5_mcp_client.py`)

No new transport or tool-calling conventions. Every new UE5-facing call in this feature (interface actors, legend, panels, ping/traceroute animation, zoom-level visibility toggling) MUST go through the existing `UE5MCPClient.call_tool()` and MUST follow the conventions 044 already established:

| Convention | Rule |
|---|---|
| Tool naming | Call short tool names, not `toolset.method` |
| Transport | Read the SSE stream line-by-line; stop at the first complete JSON-RPC object |
| Transforms | Always pass `location` + `rotation` + `scale` together, even when only one changed |
| `find_actors` | Tolerate a raw JSON string response as well as a parsed list/dict |

## `actors.py` (extended)

**Internal contract exposed to the rest of the skill**:

```python
async def spawn_interface_actor(client, device_actor_ref, hostname, interface_name) -> ActorRef
async def spawn_link_actor_to_interfaces(client, source_ref, target_ref, link_id) -> ActorRef
async def spawn_legend_actor(client, level_path) -> ActorRef
def generate_interface_label_actor_name(hostname, interface_name) -> str
def generate_link_label_actor_name(link_id) -> str
```

**Upstream capability needed**: none new — reuses the existing UE5 MCP actor-spawn/transform/material tool calls already wrapped by 044.

## `materials.py` (extended)

**Internal contract**:

```python
DEVICE_TYPE_COLORS[DeviceType.ENDPOINT] = Color(...)  # orange, was gray
def generate_legend_swatches() -> list[{"device_type": str, "color": Color, "label": str}]
def get_alarm_color() -> Color   # incident/alarm visual state, distinct from existing status colors
```

**Upstream capability needed**: none — pure local color-mapping logic.

## `telemetry.py` (extended — primary integration surface)

**Internal contract**:

```python
async def start_live_mode(client, poller: TelemetryPoller) -> None
async def stop_live_mode(poller: TelemetryPoller) -> None
def get_live_mode_status(poller: TelemetryPoller) -> LiveModeState

def record_history(subject_key: str, change_type: str, previous_state, new_state) -> None
def get_history_window(start: datetime, end: datetime) -> list[HistoryRecord]

def latch_sticky_alert(subject_key: str, trap_type: str) -> None
def clear_sticky_alert(subject_key: str, cleared_by: str) -> None
def is_sticky_alert_active(subject_key: str) -> bool
```

**Upstream capability needed from `snmptrap-mcp`** (010-telemetry-receivers): a way to receive or query linkDown/linkUp (and other) trap events for devices in the current topology, keyed by source device/interface, so `process_snmp_trap` can call `latch_sticky_alert`/`clear_sticky_alert` accordingly.

**Upstream capability needed from `gnmi-mcp`/pyATS**: per-device/per-interface operational state (up/down), health indicators (for healthy/warning/critical/unreachable classification), and interface utilization counters (for traffic visualization). A single failed device/interface query MUST NOT abort the rest of a poll cycle (FR-016) — this is an internal contract on the poll-loop implementation, not on the upstream.

## `diagnostics.py` (new)

**Internal contract**:

```python
async def animate_ping(client, source_hostname: str, dest_hostname: str) -> PingResult
async def animate_traceroute(client, source_hostname: str, dest_hostname: str) -> TracerouteResult
```

Both functions MUST resolve `source_hostname`/`dest_hostname` against the actors currently in the built topology first, and return/report a "device not in topology" outcome (FR-022, FR-040) *before* attempting any real network operation.

**Upstream capability needed**: pyATS/gNMI's ability to execute a real ping and a real traceroute from/through the managed network and return per-hop and success/failure results.

## `panels.py` (new)

**Internal contract**:

```python
async def show_config_panel(client, hostname: str) -> ActorRef
async def show_metrics_hud(client, hostname: str) -> ActorRef
async def _render_panel(client, hostname: str, kind: str, content: str) -> ActorRef  # shared primitive; replaces any existing panel of the same kind for this hostname
```

**Upstream capability needed**: pyATS/gNMI running-config retrieval (for `show_config_panel`) and live CPU/memory/uptime metrics retrieval (for `show_metrics_hud`).

## `incidents.py` (new)

**Internal contract**:

```python
async def correlate_incident(client, hostname_or_link: str) -> IncidentCorrelationResult
```

`IncidentCorrelationResult` carries either a matched `Incident` (see data-model.md) with `alarm_state_applied=True`, or an explicit "no incident found" result (FR-027) — never a silent no-op.

**Upstream capability needed**: PagerDuty's existing MCP integration (already used by the `pagerduty-*` skills) — list/query open incidents, with title/description/service-name fields available for the hostname substring match.

## `playback.py` (new)

**Internal contract**:

```python
async def replay_window(client, start: datetime, end: datetime, speed: float = DEFAULT_SPEED) -> PlaybackResult
```

Reads `telemetry.get_history_window()`, replays each `HistoryRecord` against the live scene in original order at `speed`, and returns an explicit "no changes found for this window" result (FR-031) when the slice is empty.

**Upstream capability needed**: none beyond `telemetry.py`'s own history buffer — this module does not call any external MCP server directly.

## `hierarchy.py` (new)

**Internal contract**:

```python
async def resolve_zoom_groups(hostnames: list[str]) -> list[ZoomGroup]   # NetBox/Infrahub first
def assign_manual_group(group_name: str, hostnames: list[str], zoom_level: str) -> ZoomGroup  # fallback
async def zoom_to(client, group_name: str) -> None   # toggles actor visibility/camera framing, no rebuild
async def zoom_out_to_site(client) -> None
```

**Upstream capability needed from `netbox-mcp-server`/`infrahub-mcp`**: device rack/site placement lookup by hostname. When neither source has data for a device, `resolve_zoom_groups` MUST leave it out of any group rather than guessing, and the device is reported as ungrouped (spec.md edge case) unless `assign_manual_group` is subsequently called for it.

## Test Contract

Every capability above gets at least one live-integration test in `tests/integration/test_ue5_mcp.py`, following 044's convention of testing against a real running UE5.8 MCP server rather than a mock (044's own incident history shows mocking this specific server produces false-positive "passing" tests). Where a capability also depends on a live upstream *event* rather than just a live upstream *server* (a real SNMP trap being sent, a real open PagerDuty incident existing), the test MUST skip explicitly rather than mock the event, per the false-positive-verification lesson already recorded in 044's `SKILL.md`.
