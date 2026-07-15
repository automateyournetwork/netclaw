# Quickstart: UE5 Network Digital Twin & Looking-Glass Development

**Feature**: 045-ue5-digital-twin
**Date**: 2026-07-03

## Prerequisites

This feature extends `044-ue5-mcp-network-viz`, so everything in that feature's own quickstart already applies: Unreal Engine 5.8 installed via the Epic Games Launcher, the MCP plugin enabled with "All Tools" read/write access, and `ModelContextProtocol.StartServer` running. See `specs/044-ue5-mcp-network-viz/quickstart.md` for the full walkthrough — it is not repeated here.

Additional prerequisites specific to this feature, since it wires real telemetry/incident/inventory sources instead of stub data:

### Required running/configured integrations

1. **`snmptrap-mcp`** (from `010-telemetry-receivers`) — running and reachable, with a device configured to send SNMP traps to it, for live trap-persistence testing (Story 6).
2. **`gnmi-mcp`** and/or pyATS-connected devices — for live health polling, traffic utilization, config retrieval, and ping/traceroute execution (Stories 4, 5, 7, 8, 12).
3. **PagerDuty MCP integration** — with `PAGERDUTY_USER_API_KEY` configured (see `.env.example`), for incident correlation (Story 9). At least one open incident whose title/description/service name contains a real device hostname is needed to exercise the "found" path.
4. **`netbox-mcp-server`** and/or **`infrahub-mcp`** — for hierarchical zoom (Story 11). If neither has rack/site placement for your test devices, the manual-grouping fallback path can be exercised instead.

### Environment variables

No new environment variables are introduced by this feature — it reuses the existing variables already documented in `.env.example` for gNMI, PagerDuty, NetBox, and Infrahub. Confirm these are already set from prior features before starting.

## Development Loop

1. Build a base topology exactly as in 044 ("render my network in UE5"), confirming interface-level actors, labels, and the legend appear (Phase 1 of the plan).
2. Exercise live signal capabilities: request a traffic refresh, start/stop live mode, and (if a real trap sender is available) send a linkDown trap and confirm the sticky alert appears and persists across an unrelated refresh.
3. Exercise active diagnostics: request a ping and a traceroute between two real, reachable devices in the topology; request a device's config and confirm the panel appears and replaces itself on a repeat request.
4. Exercise operational context: request incident correlation for a device with and without a matching open incident; generate a few state changes and request playback of the last several minutes, both at default and adjusted speed.
5. Exercise spatial navigation: zoom into a rack/site grouping sourced from NetBox/Infrahub if available, or assign a manual grouping and zoom into it; request a device's live metrics HUD.

## Common Pitfalls (carried over from 044, still apply here)

- Any new UE5 MCP call added by this feature that bypasses `ue5_mcp_client.py`'s existing conventions (short tool names, SSE-stream-until-first-object reads, full-transform-always) will silently reintroduce bugs 044 already fixed once.
- Spawning an actor per interface regardless of operational state will reintroduce the actor-count/crash risk 044's incident history already surfaced — always gate on up/up state per FR-001/FR-002.
- Testing any of the trap/incident/inventory-backed capabilities against a mock instead of the real MCP server risks the same "reports success while doing nothing" failure mode already found and fixed once in 044 — prefer a live, explicitly-skipped test over a mocked one.
