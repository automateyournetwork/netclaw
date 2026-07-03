# Research: UE5 Network Digital Twin & Looking-Glass

**Feature**: 045-ue5-digital-twin
**Date**: 2026-07-03

## Overview

This feature has no `NEEDS CLARIFICATION` markers — the four architecture-level questions (interaction model, update model, interface-actor scope, MVP ambition) were resolved with the user before drafting the spec, and the four remaining smaller ambiguities (trap-alert persistence, incident-correlation matching, zoom-grouping source, playback pacing) were resolved during `/speckit.clarify` and are recorded in spec.md's `## Clarifications` section. This document instead captures the research needed to ground the plan's technical decisions in what already exists in this repository, since the entire strategy for this feature is "extend and orchestrate existing capability," not "build new infrastructure."

## Decision: Extend `044-ue5-mcp-network-viz` in place, no new skill

**Decision**: All new logic lives inside `workspace/skills/ue5-network-viz/` as extensions to `actors.py`, `materials.py`, `telemetry.py`, `camera.py`, plus five new submodules (`diagnostics.py`, `panels.py`, `incidents.py`, `playback.py`, `hierarchy.py`).

**Rationale**: `telemetry.py` already contains a `TelemetryPoller` background loop and a `TelemetryEventProcessor` with `process_syslog_event`/`process_snmp_trap` handler stubs, `update_device_status`/`update_link_status`, and `set_device_critical/warning/healthy` + `set_link_down/degraded/healthy` helpers. `actors.py` already carries `source_interface`/`target_interface` metadata on link specs and a `generate_label_actor_name` helper. `materials.py` already defines `DEVICE_TYPE_COLORS` with router=blue, switch=green, firewall=red, access_point=yellow, load_balancer=purple. Building a second skill or duplicating any of this would violate Constitution Principle VII (Skill Modularity) and directly contradict the spec's own Assumptions section ("this feature builds directly on the already-shipped 044 skill... rather than duplicating them").

**Alternatives considered**: A separate `ue5-digital-twin` skill was considered (matching the branch name) but rejected — it would need to import or re-implement 044's device/link spawning, layout, and camera logic to do anything useful, which is exactly the duplication the spec's Assumptions and FR-039 forbid.

## Decision: No new MCP servers

**Decision**: This feature adds zero new MCP servers. It orchestrates six that already exist in this repo: `unreal-mcp` (UE5.8, already registered in `config/openclaw.json`), `snmptrap-mcp` (from `010-telemetry-receivers`), `gnmi-mcp`, PagerDuty's MCP integration (already used by the `pagerduty-*` skills), `netbox-mcp-server`, and `infrahub-mcp` (both present under `mcp-servers/`, with `infrahub-mcp` already registered in `config/openclaw.json` and `netbox-reconcile`/`infrahub-sot` skills already present under `workspace/skills/`). pyATS integration is used through the existing `pyats-*` skill family for config/health/diagnostic data where gNMI coverage is insufficient (e.g., running-config retrieval, ping/traceroute execution).

**Rationale**: Every data source this feature needs (SNMP traps, interface telemetry, device health, running-config, incidents, rack/site placement) already has a working, registered integration in NetClaw. Building new receivers or clients would duplicate the exact work `010-telemetry-receivers` already did and violate Principle V (MCP-Native Integration)'s implicit preference for reusing existing MCP surfaces over creating parallel ones.

**Alternatives considered**: A dedicated polling/trap-relay microservice sitting between the existing MCP servers and the UE5 skill was considered, to decouple telemetry ingestion from the skill process. Rejected for this feature's scope — it would introduce a persistent service with its own lifecycle and failure modes, and the spec's Assumptions explicitly bound state to "the lifetime of the running NetClaw session," which the existing in-process `TelemetryPoller` already satisfies.

## Decision: Reuse 044's UE5 MCP client bug fixes verbatim

**Decision**: Any new UE5 MCP tool calls added by `diagnostics.py`, `panels.py`, and the legend/interface-actor additions to `actors.py` MUST go through the existing `ue5_mcp_client.py` (short tool names, not `toolset.method`; SSE stream read-until-first-JSON-RPC-object; always pass full transform location+rotation+scale together; tolerate `find_actors` returning a raw string).

**Rationale**: These are exact, previously-diagnosed bugs in the UE5.8 MCP plugin surface documented in 044's `SKILL.md` incident log. Re-implementing panel/animation calls without routing through the existing client would silently reintroduce the same "Unknown tool" false-success and transform-clobbering failures 044 already spent significant debugging time fixing.

**Alternatives considered**: None seriously — this is a straight reuse decision, not a design tradeoff.

## Decision: Interface-actor cap via up/up-only spawning

**Decision**: Only operationally up/up interfaces get a full 3D actor; down interfaces are summarized as a compact list on the parent device (per spec FR-001/FR-002).

**Rationale**: 044's incident history establishes this UE5 host is fragile under heavy actor load (repeated crashes during batch builds). A 48-port switch topology with all-interfaces-as-actors could add hundreds of actors per device; capping to up/up interfaces keeps actor count roughly proportional to the topology's actual active link count, which is the same order of magnitude 044 already validated as stable (~200 devices, ~500 links).

**Alternatives considered**: Configurable per-build actor density (all vs. up/up-only) was considered during the pre-spec Q&A and explicitly rejected by the user in favor of a simpler, fixed up/up-only rule with a down-interface list as the summarization mechanism.

## Decision: PagerDuty incident correlation via hostname substring match

**Decision**: An incident is correlated to a device/link if the device's hostname (or, for a link, either endpoint's hostname) appears in the incident's title, description, or service name — no new tagging convention required on the PagerDuty side.

**Rationale**: Resolved directly with the user during `/speckit.clarify`. This requires zero changes to how incidents get created and works immediately against any existing PagerDuty service, at the cost of being a heuristic (a hostname substring could theoretically false-positive against an unrelated incident that happens to mention the same string). This tradeoff is accepted explicitly in the clarification.

**Alternatives considered**: Structured-tag-only matching (more precise, but requires a new tagging discipline the user has not established) and a hybrid tag-then-text-fallback approach (more complex for a P9-priority story) were both offered and not chosen.

## Decision: Rack/site grouping sourced from NetBox/Infrahub, manual fallback

**Decision**: `hierarchy.py` queries `netbox-mcp-server` and `infrahub-mcp` for a device's rack/site placement; if neither has data for a device, the caller can supply an explicit manual grouping instead.

**Rationale**: Confirmed via `grep` that both `mcp-servers/netbox-mcp-server` and `mcp-servers/infrahub-mcp` exist in this repo, with `infrahub-mcp` already registered in `config/openclaw.json` and companion skills (`netbox-reconcile`, `infrahub-sot`) already present. Since most CML/pyATS/gNMI-sourced lab topologies carry no rack/site metadata at all, a source-of-truth-first-with-manual-fallback design keeps Story 11 usable immediately against real lab data while still respecting authoritative placement data when it exists — exactly the tradeoff the user specified when resolving this clarification.

**Alternatives considered**: Source-of-truth-only (rejected — makes the story unusable for the common unlabeled-lab case) and manual-only (rejected — ignores real placement data NetClaw already has access to via existing integrations).

## Decision: Compressed, adjustable-speed historical playback

**Decision**: `playback.py` replays a requested history window at a compressed default rate, with an explicit speed-adjustment parameter (e.g., "double speed"), rather than at real elapsed pace.

**Rationale**: Confirmed directly with the user. A DVR-style compressed-replay pattern is standard for session-review tooling and matches SC-008's expectation that replaying "the most recent 30 minutes" completes in well under 30 minutes.

**Alternatives considered**: Real elapsed-pace replay was offered and explicitly rejected by the user as the default (though nothing in the design prevents an extremely slow "adjusted speed" from approximating it if ever needed).
