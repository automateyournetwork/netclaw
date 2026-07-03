# Feature Specification: UE5 Network Digital Twin & Looking-Glass

**Feature Branch**: `045-ue5-digital-twin`
**Created**: 2026-07-03
**Status**: Draft
**Input**: User description: "Extend NetClaw's UE5.8 network visualization skill from a static topology snapshot into an interactive digital twin and network looking-glass, with interface-level actors, universal labeling, a color legend, traffic visibility, live SNMP polling and trap alerts, ping and traceroute visualization, on-demand config display, incident correlation, historical playback, hierarchical zoom, and a floating metrics HUD, all driven conversationally through NetClaw"

## Clarifications

### Session 2026-07-03

- Q: Story 6 (SNMP trap alerts) — when a trap flags an interface/link down, how long should that visual alert persist? → A: Sticky — the alert persists until a corresponding recovery signal (linkUp trap or a health-poll confirming recovery) is received.
- Q: Story 9 (incident correlation) — how should NetClaw determine that a PagerDuty incident is correlated to a specific device or link? → A: Hostname match — an incident is correlated if the device's hostname (or a link's two endpoint hostnames) appears in the incident's title, description, or service name.
- Q: Story 11 (hierarchical zoom) — where should rack/site groupings come from, given most CML/pyATS/gNMI-sourced topologies carry no rack/site metadata? → A: NetBox and/or Infrahub (NetClaw's existing source-of-truth integrations) first, falling back to accepting a manual grouping request when neither has rack/site data for a device.
- Q: Story 10 (historical playback) — should replay run compressed or at real elapsed pace? → A: Compressed, at a fixed default rate with support for an adjustable speed (e.g., "replay the last 30 minutes at double speed").

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Interface-Level Actors (Priority: P1)

A network engineer builds a topology and sees each router and switch not as a single opaque box, but as a device with its own active ports represented individually, so the actual physical/logical connection points — not just the boxes — are visible in the 3D scene.

**Why this priority**: Every other story in this feature (labeling, traffic, trap alerts, ping animation) is anchored to an interface, not a device. Without interface-level actors, none of those capabilities have a real object to attach to.

**Independent Test**: Build a topology containing a device with a mix of up and down interfaces. Confirm that only the up/up interfaces spawn as individual actors attached to the parent device, and that links attach to those interface actors rather than to the device as a whole.

**Acceptance Scenarios**:

1. **Given** a device with 4 up/up interfaces and 20 down interfaces, **When** the topology is built, **Then** exactly 4 interface actors are spawned as children of that device, and the 20 down interfaces do not each receive an actor.
2. **Given** a link between two devices with known source/target interfaces, **When** the topology is built, **Then** the link visually attaches to the two specific interface actors rather than to the two device actors directly.
3. **Given** a device is repositioned by the topology layout, **When** the reposition happens, **Then** its interface actors move with it and remain visually attached.

---

### User Story 2 - Universal Visible Labeling (Priority: P2)

A network engineer looking at the 3D scene can identify every device, every active interface, and every link by name without needing to ask NetClaw or consult an external diagram — the labels are simply visible in the scene.

**Why this priority**: A digital twin that cannot be read at a glance is not usable as a looking-glass. Labeling is what turns "colored shapes" into "identifiable network elements," and every other capability produces results that are meaningless without it.

**Independent Test**: Build a topology and, without querying NetClaw, visually confirm every device, every up/up interface, and every link has a readable text label identifying it.

**Acceptance Scenarios**:

1. **Given** a built topology, **When** viewed in the scene, **Then** every device actor displays its hostname as a label.
2. **Given** a built topology, **When** viewed in the scene, **Then** every up/up interface actor displays its interface name as a label.
3. **Given** a built topology, **When** viewed in the scene, **Then** every link displays a label identifying which interfaces or devices it connects.

---

### User Story 3 - Color Legend (Priority: P3)

A network engineer new to a given topology can look at a single, always-visible legend in the scene and immediately understand what each device color represents, without memorizing a convention or asking NetClaw.

**Why this priority**: Color coding is only useful if it is decodable. A legend is a small addition that makes every other color-based signal (device type, health, traffic, alerts) interpretable.

**Independent Test**: Build any topology and confirm a legend is present showing the color assigned to each device type in use, without any additional request.

**Acceptance Scenarios**:

1. **Given** a topology build with routers, switches, firewalls, and endpoints, **When** the build completes, **Then** a single legend actor is visible showing the color for each of those device types.
2. **Given** the underlying device-type color mapping is later changed, **When** a new topology is built, **Then** the legend reflects the current mapping, not a stale hardcoded one.

---

### User Story 4 - Traffic Visibility on Links and Ports (Priority: P4)

A network engineer asks NetClaw to show current traffic levels, and links/interfaces visually respond — busier links look visibly different from idle ones — so congestion is something you can see, not just query.

**Why this priority**: This is the single most requested "wow" capability of a network digital twin, and it depends on interface-level actors (Story 1) already being in place to have somewhere meaningful to attach traffic state.

**Independent Test**: Request a traffic refresh on a topology where some links carry known utilization values and others have none. Confirm links with utilization data show a visually distinct state (e.g., intensity, pulse) proportional to that value, and links without data show their normal default appearance.

**Acceptance Scenarios**:

1. **Given** a link with high utilization data, **When** traffic visibility is requested, **Then** that link's visual state is clearly more "active" than a link with low or no utilization.
2. **Given** a link with no available utilization data, **When** traffic visibility is requested, **Then** that link shows its default appearance rather than an error or blank state.
3. **Given** traffic visibility was shown previously, **When** it is requested again with updated data, **Then** the visual state updates to reflect the new values.

---

### User Story 5 - Live Health via Polling (Priority: P5)

A network engineer asks NetClaw to check real device and interface health, and the scene's colors update to reflect actual current state (healthy, warning, critical, unreachable) — either as a one-time refresh or continuously during an active "live mode" session.

**Why this priority**: This turns the digital twin from a snapshot into a genuine reflection of live network state, which is the core promise of "digital twin." It depends on Story 1's interface actors to have a target for interface-level health.

**Independent Test**: Trigger an on-demand health refresh against a topology with a mix of healthy and degraded devices, and confirm actor colors change accordingly. Separately, start live mode, observe at least one automatic update without further prompting, then stop live mode.

**Acceptance Scenarios**:

1. **Given** a topology with a device in a critical state, **When** a health refresh is requested, **Then** that device's actor visually reflects the critical state.
2. **Given** live mode is started, **When** a monitored device's state changes during the session, **Then** the corresponding actor updates automatically without an additional user request.
3. **Given** live mode is running, **When** the user asks to stop it, **Then** polling stops and NetClaw confirms live mode is no longer active.
4. **Given** one device is unreachable during a poll, **When** the poll runs, **Then** the rest of the topology's devices are still polled and updated normally.

---

### User Story 6 - SNMP Trap Alerts (Priority: P6)

A network engineer sees a link or interface visually flag itself the moment a real SNMP trap (such as linkDown/linkUp) is received for a device in the current topology, without having to manually request a refresh.

**Why this priority**: Traps are event-driven and time-sensitive in a way polling is not; this is what makes the twin feel "alive" between explicit refreshes, reusing NetClaw's existing trap-receiving capability rather than duplicating it.

**Independent Test**: Send a linkDown trap for a device/interface present in the current topology and confirm the corresponding actor visually changes state without any user-initiated refresh. Send a trap for a device not in the topology and confirm it is ignored without error.

**Acceptance Scenarios**:

1. **Given** an interface actor in a healthy state, **When** a linkDown trap is received for that interface, **Then** the actor's visual state changes to reflect the down condition and persists in that state.
2. **Given** an interface previously flagged down by a trap, **When** a corresponding linkUp trap or a health-poll confirming recovery is received, **Then** the actor's visual state returns to reflect the up condition.
3. **Given** a trap arrives for a device not present in the current scene, **When** it is processed, **Then** no error occurs and no actor is affected.
4. **Given** an interface actor already flagged down by a trap, **When** no recovery signal has been received, **Then** the down visual state remains even after further unrelated topology refreshes.

---

### User Story 7 - Ping and Traceroute Visualization (Priority: P7)

A network engineer asks NetClaw to ping or traceroute between two devices in the topology, and watches the result animate through the 3D scene — a traveling indicator for a ping, a sequential hop-by-hop lighting for a traceroute — rather than reading raw command output.

**Why this priority**: This is a signature "looking glass" capability — it turns a text-based diagnostic into a spatial, visual one, and demonstrates the twin as an active troubleshooting tool, not just a display.

**Independent Test**: Request a ping between two known-reachable devices in the topology and confirm the path animates and completes. Request a traceroute to a target with an intermediate hop and confirm sequential hop illumination. Request either against a device not in the topology and confirm it is reported rather than attempted.

**Acceptance Scenarios**:

1. **Given** two reachable devices in the topology, **When** a ping is requested between them, **Then** the path between their actors animates to reflect a successful ping.
2. **Given** two devices with a known intermediate hop, **When** a traceroute is requested between them, **Then** each hop along the path is illuminated in sequence.
3. **Given** a ping or traceroute target is unreachable, **When** the operation completes, **Then** the failure is visually distinguishable from a success.
4. **Given** a requested device is not present in the current topology, **When** the request is made, **Then** NetClaw reports this instead of attempting the operation.

---

### User Story 8 - Show Config On Demand (Priority: P8)

A network engineer asks NetClaw to show a specific device's running configuration, and it appears as a readable panel next to that device in the 3D scene.

**Why this priority**: Configuration is one of the most common things an engineer needs mid-investigation; surfacing it directly in the spatial context of the device it belongs to keeps the engineer inside the twin instead of switching to another tool.

**Independent Test**: Request a device's configuration and confirm a readable panel appears near its actor showing real configuration content. Request it again and confirm the panel is replaced rather than duplicated.

**Acceptance Scenarios**:

1. **Given** a device in the topology, **When** its configuration is requested, **Then** a text panel showing its real running configuration appears near its actor.
2. **Given** a config panel is already showing for a device, **When** its configuration is requested again, **Then** the existing panel is replaced rather than stacking a duplicate.

---

### User Story 9 - Incident Correlation (Priority: P9)

A network engineer asks whether a device or link has any open incidents, and if so, the corresponding actor takes on a distinct alarm state, tying the 3D scene into NetClaw's existing incident-management awareness.

**Why this priority**: This connects the visual twin to operational reality (active incidents), letting an engineer triage visually rather than cross-referencing a separate incident dashboard.

**Independent Test**: With a known open incident whose title, description, or service name contains a device's hostname, request a correlation check and confirm the actor takes on an alarm state. With no incident referencing a different device's hostname, request a check on it and confirm NetClaw reports that none was found.

**Acceptance Scenarios**:

1. **Given** a device with an open, correlated incident, **When** incident correlation is requested, **Then** that device's actor displays a distinct alarm visual state.
2. **Given** a device with no correlated open incident, **When** incident correlation is requested, **Then** NetClaw clearly reports that no incident was found rather than leaving the actor unchanged with no explanation.

---

### User Story 10 - Historical Playback (Priority: P10)

A network engineer asks NetClaw to replay what happened in the topology over a recent window of time, and watches the recorded state changes play back in the scene in sequence.

**Why this priority**: Live state and alerts are only part of the picture — being able to look back at "what changed and when" during a session is what makes the twin useful for post-incident review, not just live monitoring.

**Independent Test**: Generate several recorded state changes during a session (e.g., via health refreshes or trap events), then request playback of that time window and confirm the changes replay in the same order they occurred, at a compressed pace, finishing well before the real window duration would have elapsed. Request playback at an adjusted speed and confirm it finishes proportionally faster or slower. Request playback of a window with no recorded changes and confirm this is reported clearly.

**Acceptance Scenarios**:

1. **Given** a session with recorded state changes over the last several minutes, **When** playback of that window is requested, **Then** the changes replay in the scene in their original order at a compressed default speed, completing in a small fraction of the original window's duration.
2. **Given** a session with recorded state changes, **When** playback is requested at an explicitly adjusted speed (e.g., double speed), **Then** the replay duration changes proportionally to the requested speed.
3. **Given** a requested playback window contains no recorded changes, **When** playback is requested, **Then** NetClaw reports that no changes were found for that window.

---

### User Story 11 - Hierarchical Zoom (Priority: P11)

A network engineer moves between a site-wide view, a rack-level view, and an individual-device view of the same network without needing to rebuild the topology from scratch each time.

**Why this priority**: Large topologies become unreadable at a single fixed scale; hierarchical zoom lets the same digital twin serve both "big picture" and "deep dive" use cases.

**Independent Test**: With a topology built for devices that carry rack/site placement in NetBox or Infrahub, request a transition into a specific rack's view and confirm the same underlying actors are shown at that level of detail without duplication or loss. With devices that carry no rack/site placement in either source, manually assign a grouping and confirm the same zoom behavior works from that manual grouping. Request a transition back to the site-wide view and confirm the same result.

**Acceptance Scenarios**:

1. **Given** a site-wide topology view where devices have rack/site placement recorded in NetBox or Infrahub, **When** a zoom into a specific rack is requested, **Then** the view transitions to show that rack's devices in greater detail, grouped using the source-of-truth placement data, without rebuilding the topology from scratch.
2. **Given** a topology where devices have no rack/site placement in NetBox or Infrahub, **When** the user manually assigns a set of devices to a named grouping, **Then** a zoom into that grouping is available using the manual assignment.
3. **Given** a rack-level or device-level view, **When** a zoom back out to the site-wide view is requested, **Then** the full topology is shown again with no duplicated or missing actors.

---

### User Story 12 - Floating Metrics HUD (Priority: P12)

A network engineer asks NetClaw to show live metrics for a specific device, and a floating panel appears above that device's actor showing current CPU, memory, and uptime.

**Why this priority**: This gives quick, spatially-anchored access to the most commonly requested health metrics without leaving the visual context of the device in question.

**Independent Test**: Request metrics for a device and confirm a floating panel appears above its actor showing current CPU, memory, and uptime values retrieved at request time.

**Acceptance Scenarios**:

1. **Given** a device in the topology, **When** its metrics are requested, **Then** a floating panel appears above its actor showing current CPU, memory, and uptime.
2. **Given** a metrics panel was shown previously for a device, **When** metrics are requested again, **Then** the panel reflects freshly retrieved values, not the previously displayed ones.

---

### Edge Cases

- What happens when a device reports zero up/up interfaces (fully down)? The device actor still spawns; every interface appears in its down-interface list; no interface actors are spawned for that device.
- What happens when a data source only reports device-level state with no per-interface detail? Links fall back to attaching device-to-device, as in the base visualization, rather than failing to render.
- What happens when a ping or traceroute target is unreachable? The failure/loss point is animated as a visually distinguishable outcome rather than silently showing nothing or showing a false success.
- What happens when live mode is started but the underlying data source is unreachable? The failure is reported clearly and live mode is left in a known, confirmable off/failed state rather than appearing to run silently.
- What happens when two trap events arrive for the same interface in quick succession? The actor reflects the most recently received state; events are not queued into overlapping or conflicting visual flashes. A down/alert state remains sticky until an explicit recovery signal is received, regardless of how many further unrelated events occur in the meantime.
- What happens when a device named in a config, ping, metrics, or incident-correlation request does not exist in the current built topology? NetClaw reports this to the user rather than attempting the operation against nothing.
- What happens when historical playback is requested for a window with no recorded changes? NetClaw reports that no changes were found for that window rather than silently doing nothing.
- What happens when a zoom-level transition is requested for a scope (e.g., a rack) that does not exist in the current topology? NetClaw reports this rather than transitioning to an empty or incorrect view.
- What happens when a device has no rack/site placement in NetBox or Infrahub and no manual grouping has been assigned for it? The device is reported as ungrouped rather than silently placed into an arbitrary or default group.

## Requirements *(mandatory)*

### Functional Requirements

**Interface-level actors (Story 1)**

- **FR-001**: System MUST spawn an individual 3D actor for every interface on a device that is reported operationally up/up.
- **FR-002**: System MUST NOT spawn an individual actor for an interface reported down; down interfaces MUST instead be represented as a compact list associated with their parent device.
- **FR-003**: Links MUST attach to the specific source and target interface actors when interface-level data is available for both ends, and MUST fall back to device-level attachment when it is not.
- **FR-004**: Interface actors MUST remain visually attached to their parent device actor when the parent is repositioned.

**Universal labeling (Story 2)**

- **FR-005**: Every device actor MUST display a visible 3D label showing its hostname.
- **FR-006**: Every up/up interface actor MUST display a visible 3D label showing its interface name.
- **FR-007**: Every link MUST display a visible 3D label identifying the interfaces or devices it connects.

**Color legend (Story 3)**

- **FR-008**: System MUST spawn exactly one legend actor per topology build, visible without requiring further interaction.
- **FR-009**: The legend MUST reflect the current device-type-to-color mapping in use, including a distinct color for endpoint/PC devices.

**Traffic visibility (Story 4)**

- **FR-010**: System MUST support visually representing link and interface traffic utilization (e.g., via color intensity, pulse, or thickness) proportional to a supplied utilization value.
- **FR-011**: Traffic visualization MUST be refreshable on demand and MUST reflect the most recently retrieved utilization data.
- **FR-012**: Links or interfaces without available utilization data MUST show their default (non-traffic) appearance rather than an error state.

**Live health via polling (Story 5)**

- **FR-013**: On request, system MUST retrieve real device/interface health state and update the corresponding actor's visual state to reflect healthy, warning, critical, or unreachable status.
- **FR-014**: System MUST support an explicit request to start continuous background polling ("live mode") and an explicit request to stop it.
- **FR-015**: System MUST be able to report whether live mode is currently active or inactive at any time.
- **FR-016**: A polling failure for one device or interface MUST NOT prevent polling of the rest of the topology.

**SNMP trap alerts (Story 6)**

- **FR-017**: System MUST consume SNMP trap events for devices present in the current topology and reflect a visually distinguishable state change on the corresponding interface or link actor.
- **FR-018**: linkDown and linkUp trap events MUST, at minimum, each produce a distinguishable visual outcome on the affected actor; a trap-driven down/alert state MUST persist (sticky) until a corresponding recovery signal (a linkUp trap or a health-poll confirming recovery) is received, not merely a transient flash.
- **FR-019**: Trap events referencing a device or interface not present in the current scene MUST be ignored without raising an error.

**Ping and traceroute visualization (Story 7)**

- **FR-020**: On request naming a source and destination device present in the topology, system MUST execute a real ping and animate the result along the path between their actors.
- **FR-021**: On request naming a source and destination device present in the topology, system MUST execute a real traceroute and animate sequential illumination of each hop along the path.
- **FR-022**: If a requested source or destination device is not present in the current topology, system MUST report this rather than attempting the operation.
- **FR-023**: Ping and traceroute failures MUST be visually distinguishable from successful outcomes.

**Show config on demand (Story 8)**

- **FR-024**: On request naming a device present in the topology, system MUST retrieve its real running configuration and render it as a readable text panel near that device's actor.
- **FR-025**: A repeated configuration request for the same device MUST replace any existing panel for that device rather than stacking duplicates.

**Incident correlation (Story 9)**

- **FR-026**: On request, system MUST check whether a device or link has an open incident correlated to it — determined by the device's hostname (or, for a link, either endpoint's hostname) appearing in the incident's title, description, or service name — and, if so, apply a distinguishable alarm visual state to the relevant actor.
- **FR-027**: If no correlated incident exists for the requested device or link, system MUST clearly report this.

**Historical playback (Story 10)**

- **FR-028**: System MUST record a timestamped history of state changes (health, traffic, trap-driven) that occur during a session.
- **FR-029**: On request specifying a prior time window, system MUST replay the recorded state changes for that window in the scene, in their original order, at a compressed default speed rather than real elapsed pace.
- **FR-030**: System MUST support an explicitly requested playback speed adjustment (e.g., "double speed") that proportionally changes the replay duration.
- **FR-031**: If a requested playback window contains no recorded changes, system MUST report this rather than performing a silent no-op.

**Hierarchical zoom (Story 11)**

- **FR-032**: System MUST support at least three distinct levels of topology detail (site/campus, rack, device) for the same underlying network.
- **FR-033**: System MUST source rack/site groupings from NetBox or Infrahub when a device's placement is recorded there, and MUST accept a manual grouping request as a fallback when neither source has placement data for a device.
- **FR-034**: On request specifying a target scope, system MUST transition the view between these levels without requiring the topology to be rebuilt from scratch.
- **FR-035**: A zoom-level transition MUST NOT lose or duplicate actors already present in the scene.

**Floating metrics HUD (Story 12)**

- **FR-036**: On request naming a device present in the topology, system MUST retrieve live CPU, memory, and uptime metrics and display them as a floating panel above that device's actor.
- **FR-037**: A repeated metrics request for the same device MUST reflect freshly retrieved values rather than a previously cached display.

**Cross-cutting**

- **FR-038**: All interactions described in this specification MUST be triggerable through natural-language conversation with NetClaw; in-engine clickable UI is explicitly out of scope.
- **FR-039**: This feature MUST extend the existing base visualization skill's device/link spawning, topology layout, and camera control rather than duplicating or replacing them.
- **FR-040**: Any request referencing a device, interface, or link not present in the currently built topology MUST be reported to the user rather than silently attempted or ignored.

### Key Entities

- **Interface Actor**: An individual 3D representation of a single up/up network interface; a child of its parent Device Actor; carries an interface name, operational state, and optional traffic/utilization state.
- **Down-Interface Summary**: A compact, non-actor listing of a device's operationally down interfaces, associated with that device's label or info panel.
- **Link**: A visual connection between two Interface Actors (or, as a fallback, two Device Actors); carries an identifying label and can carry a traffic/utilization visual state and a trap-driven alert state.
- **Legend**: A single persistent actor summarizing the current device-type-to-color mapping for a topology build.
- **Trap Event**: A real-time SNMP notification tied to a specific device/interface, driving a transient or persistent visual alert on the corresponding actor.
- **Config Panel**: An on-demand, in-scene text display of a device's real running configuration.
- **Incident**: An externally sourced record (from NetClaw's incident-management integration) correlated to a device or link via hostname matching against its title, description, or service name, driving an alarm visual state.
- **History Record**: A timestamped snapshot of a state change occurring during a session, used to support playback.
- **Zoom Level**: One of the supported levels of topology detail (site/campus, rack, device) available for a given built topology; rack/site groupings are sourced from NetBox or Infrahub when available, or from a manual assignment when neither source has placement data for a device.
- **Metrics HUD**: An on-demand floating panel showing a device's live CPU, memory, and uptime.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A network engineer can identify what each device color represents by looking at the in-scene legend alone, without needing to ask NetClaw or consult external documentation.
- **SC-002**: 100% of operationally up/up interfaces in a built topology display a readable label identifying that interface; 100% of devices and links display a readable identifying label.
- **SC-003**: A network engineer can request a real ping or traceroute between two devices and see the animated result complete in under 30 seconds.
- **SC-004**: A network engineer can request a device's live running configuration and see it rendered in the scene in under 15 seconds.
- **SC-005**: A visual alert for a device/interface state change driven by a real SNMP trap appears in the scene within 10 seconds of the trap being received.
- **SC-006**: A network engineer can start live mode, observe at least one automatic state update occur without manual intervention, and stop live mode — confirming its active/inactive status at each step.
- **SC-007**: A network engineer can determine whether a given device or link has an open, correlated incident without leaving NetClaw's conversational interface.
- **SC-008**: A network engineer can successfully replay at least the most recent 30 minutes of recorded session history on request, at a compressed default speed that completes well before 30 minutes of real time elapses, with the option to explicitly adjust that speed.
- **SC-009**: A network engineer can move between at least two hierarchical zoom levels (e.g., site to rack) for the same topology without triggering a full topology rebuild.
- **SC-010**: A network engineer can request live metrics for any device in the topology and receive a displayed result reflecting current values, not stale or cached ones.

## Assumptions

- All interactions described in this specification are conversational (natural language requests to NetClaw); in-engine clickable UI and custom UE5 Blueprint/UMG event handling are explicitly out of scope for this feature.
- The update model is hybrid: on-demand refresh is the default behavior, with an optional, explicitly started and stopped "live mode" providing continuous background polling for the duration of a session only.
- Only interfaces reported operationally up/up are spawned as individual 3D actors; down interfaces are represented as a compact per-device list rather than individual actors, in order to bound total actor count on devices with many ports.
- This feature is intentionally scoped as twelve prioritized, independently testable user stories (P1-P12) so that implementation and delivery can proceed and be checkpointed story by story, even though the full vision is captured in this one specification.
- This feature builds directly on the already-shipped 044 UE5 network visualization skill and reuses its existing device/link spawning, topology layout, and camera control rather than duplicating them.
- SNMP trap and syslog event ingestion reuse NetClaw's existing dedicated trap/event-receiving capability rather than introducing a new receiver.
- Device/interface polling, configuration retrieval, and ping/traceroute execution reuse NetClaw's existing network-access integrations rather than introducing new device-access mechanisms.
- Incident correlation reuses NetClaw's existing incident-management integration rather than introducing new incident tracking.
- Hierarchical zoom reuses NetClaw's existing NetBox and Infrahub source-of-truth integrations for rack/site placement data rather than introducing a new inventory system, falling back to manual grouping only when neither source has placement data for a device.
- Historical playback data is retained for the duration of a live NetClaw session only; long-term persistence of history beyond a session is out of scope for this feature.
- Real ping, traceroute, and configuration-retrieval operations are performed only against devices reachable through NetClaw's existing managed network access (e.g., a CML lab or other environment NetClaw already has credentials/access for), not against arbitrary unmanaged devices.
