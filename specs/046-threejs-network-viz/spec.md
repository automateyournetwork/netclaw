# Feature Specification: Three.js Browser Network Topology Visualization

**Feature Branch**: `046-threejs-network-viz`
**Created**: 2026-07-05
**Status**: Draft
**Input**: User description: "Build a composable NetClaw skill that renders network topologies as interactive, fully-labeled 3D scenes in a web browser using Three.js, replacing the current Unreal Engine 5 and Blender visualization skills, which require heavyweight third-party desktop applications, GPUs, and cross-OS bridging to run. A network engineer should be able to ask NetClaw something like 'replicate the CML lab topology in a browser for me' and receive a self-contained 3D visualization that opens directly in a browser with no extra software installed. The skill must be composable with NetClaw's existing topology-source skills rather than replacing them, accepting topology data sourced live from any of NetClaw's existing network-of-record and lab-emulation integrations, or a freeform/manually-described topology. Devices, interfaces (as true children of their parent device), links (as wires between specific interfaces), labels, a legend, and state-based coloring are all required. Support both zero-setup procedural shapes and an optional real-3D-model stencil mode sourced only from genuinely open/CC0 origins, never scraped from gated marketplaces. Delivery must require no manual build step, no server process, and no desktop application. Avoid the scale, transform, attachment, and centering mistakes made in NetClaw's prior Blender and UE5 visualization skills."

## Clarifications

### Session 2026-07-05

- Q: Where/how should the generated visualization artifact be delivered and persisted? → A: Timestamped/unique file per request, kept in a NetClaw workspace output folder so the engineer can revisit or share past visualizations.
- Q: How much source metadata should appear in device/interface labels beyond identifying names? → A: Show everything the source exposes by default (IP addresses, descriptions, software versions, etc.), never credentials or full running-config content.
- Q: Does real-stencil mode (real 3D models) still have to meet the zero-server, single-file delivery promise, given browsers block loading separate local asset files from a double-clicked page? → A: Yes — always a single self-contained file; 3D models are embedded/inlined directly into it rather than referenced as separate files.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View a Live Topology as an Interactive 3D Scene (Priority: P1)

A network engineer asks NetClaw to visualize a topology from a live source (for example, "replicate the CML lab topology in a browser for me") and, within moments, has a 3D scene open in their web browser showing every device, every active interface, and every link between them — fully labeled, color-coded by role, and explained by an on-screen legend — that they can freely rotate, pan, and zoom to inspect from any angle.

**Why this priority**: This is the entire value proposition of the feature. Without a correctly rendered, readable, navigable scene generated on request with zero extra setup, nothing else in this feature matters.

**Independent Test**: Ask NetClaw to visualize a topology from a connected live source. Confirm a 3D scene opens in a browser with no manual build, install, or server step, and that every device, interface, and link is visible, labeled, and colored according to a legend also present in the scene.

**Acceptance Scenarios**:

1. **Given** a reachable live topology source, **When** the engineer asks NetClaw to visualize it, **Then** a self-contained 3D visualization opens in a browser without requiring the engineer to install, build, or run anything beyond a standard web browser.
2. **Given** a rendered scene, **When** the engineer inspects it, **Then** every device is shown as a distinct shape colored by its role (router, switch, firewall, load balancer, client/endpoint), every one of that device's interfaces appears as a labeled element attached to that device, and every link is drawn as a visible wire between the two specific interfaces it connects.
3. **Given** a rendered scene, **When** the engineer moves a device (or the scene is regenerated after a device moves), **Then** that device's interfaces and connected link endpoints move with it rather than staying behind or detaching.
4. **Given** a rendered scene, **When** the engineer uses standard mouse/trackpad controls, **Then** they can rotate, pan, and zoom the camera to view the topology from any angle.
5. **Given** a topology whose source coordinates are far from the origin or inconsistently scaled, **When** the scene is generated, **Then** the topology is centered and sized so the whole scene is visible and readable without manual camera repositioning.

---

### User Story 2 - Compose Topology Data From Any Supported Source (Priority: P2)

A network engineer can ask for a visualization sourced from any of NetClaw's existing topology-of-record or lab-emulation integrations — Cisco Modeling Labs, GNS3, containerlab, EVE-NG, Nautobot, NetBox/Infrahub, IP Fabric, or Forward Networks — and get the same quality of rendered scene regardless of which source supplied the data.

**Why this priority**: The visualization is only useful if it plugs into the topology sources engineers already use through NetClaw; a renderer that only works with one hardcoded source would not meet the "composable skill" goal.

**Independent Test**: Request a visualization sourced from at least two different supported integrations (for example, a CML lab and a Nautobot-modeled network) and confirm both produce a correctly rendered, fully-labeled scene using the same visual conventions.

**Acceptance Scenarios**:

1. **Given** a topology available through any one supported source integration, **When** the engineer requests a visualization of it, **Then** NetClaw retrieves that source's topology data and renders it using the same device shapes, colors, labeling, and legend conventions used for every other source.
2. **Given** an engineer does not specify which source to use and more than one is plausible, **When** the request is ambiguous, **Then** NetClaw asks which source to use rather than guessing silently.
3. **Given** a named source is unreachable or returns an error, **When** the engineer requests a visualization from it, **Then** NetClaw reports the failure clearly rather than producing an empty, partial, or misleading scene.

---

### User Story 3 - Sketch a Freeform Topology Without a Live Source (Priority: P3)

A network engineer describes a topology directly in conversation — devices, their roles, and how they connect — without pointing at any live system, and receives the same kind of rendered 3D scene as if it had come from a live source.

**Why this priority**: Not every topology an engineer wants to visualize exists in a connected source yet (a proposed design, a whiteboard sketch, a training example); freeform input makes the skill useful even with no integration in play.

**Independent Test**: Describe a small topology in plain language (a handful of devices and their connections, no live source referenced) and confirm a correctly rendered, labeled scene is produced from that description alone.

**Acceptance Scenarios**:

1. **Given** a plain-language description of devices and how they connect, **When** the engineer asks NetClaw to visualize it, **Then** a 3D scene is rendered using the same shape, color, labeling, and legend conventions as a live-sourced topology.
2. **Given** a freeform description that omits some detail (for example, a device's role or an interface name), **When** the scene is rendered, **Then** NetClaw fills the gap with a clearly-indicated reasonable default (for example, a generic device shape or a generated interface name) rather than failing to render.

---

### User Story 4 - See Device and Link Health Through Color (Priority: P4)

A network engineer looking at a rendered scene can tell at a glance which devices and links are healthy, degraded, or down, because state is reflected through color in addition to the base role-based coloring.

**Why this priority**: A topology diagram that only shows shape and role, with no health signal, is a static picture; reflecting known state is what makes the visualization operationally useful rather than purely illustrative.

**Independent Test**: Visualize a topology that includes at least one device or link reported as down or degraded, and confirm that element is visually distinguishable from the healthy elements around it, with the legend explaining the distinction.

**Acceptance Scenarios**:

1. **Given** topology data that includes operational state for devices and/or links, **When** the scene is rendered, **Then** any element reported down or degraded is visually distinguishable from healthy elements, and the legend explains what each state color means.
2. **Given** topology data with no available state information for a given device or link, **When** the scene is rendered, **Then** that element shows a neutral default appearance rather than an incorrect or misleading health state.

---

### User Story 5 - Use Real 3D Device Models Instead of Shapes (Priority: P5)

A network engineer who wants a more visually rich scene can turn on a "real stencil" mode, and devices render using recognizable 3D models (for example, generic router, switch, or rack-style models) instead of plain procedural shapes, wherever a permitted model is available — with no visible gap for devices that lack one.

**Why this priority**: This is a visual quality enhancement, not a functional requirement for the core value of the feature (which is fully met by procedural shapes); it is intentionally lowest priority so the feature ships and delivers value without depending on solving 3D asset sourcing first.

**Independent Test**: Enable real-stencil mode on a topology where some device roles have a permitted model available and others do not, and confirm the available roles render with real models while the rest fall back to procedural shapes with no missing or broken elements.

**Acceptance Scenarios**:

1. **Given** real-stencil mode is enabled and a device's role has a model available from a permitted open/CC0 source or a user-supplied asset, **When** the scene is rendered, **Then** that device displays the real 3D model instead of a procedural shape.
2. **Given** real-stencil mode is enabled and a device's role has no permitted model available, **When** the scene is rendered, **Then** that device falls back to its procedural shape automatically, and NetClaw reports which devices fell back and why.
3. **Given** a device role's model would only be available from a marketplace that gates downloads behind login/checkout or restricts redistribution, **When** NetClaw resolves an asset for that role, **Then** it never attempts to automatically fetch or scrape from that marketplace, checking only whether the user has already supplied a matching asset manually.

---

### Edge Cases

- What happens when a topology has no interface-level detail from its source, only device-level connectivity? Links fall back to attaching device-to-device rather than failing to render.
- What happens when a topology is very large (dozens of devices, hundreds of interfaces)? The scene still renders and remains navigable; readability may require the engineer to zoom in, but nothing is silently dropped.
- What happens when the same topology is requested twice in a row? Each request produces its own independent, up-to-date visualization; an older open scene is not silently mutated.
- What happens when a device name or role can't be classified from the source data? It renders using a generic default shape and color, clearly marked as unclassified in its label, rather than being omitted.
- What happens when the freeform description and a live source both reference the same topology name? NetClaw treats each request as it is stated — a freeform request is never silently redirected to a live source, and vice versa.
- What happens when real-stencil mode is enabled but no permitted models exist for any device role in the topology? The entire scene renders using procedural shapes, and NetClaw reports that no real models were available rather than failing the request.
- What happens when a device or link's operational state is unknown or was never retrieved? It renders in its neutral default appearance rather than being shown as down or degraded by assumption.

## Requirements *(mandatory)*

### Functional Requirements

**Core rendering and delivery (Story 1)**

- **FR-001**: System MUST render a requested topology as a single self-contained file that opens directly in the engineer's web browser without requiring any manual build step, background server process, or separate desktop application — including when real-stencil mode (FR-018) is used, in which case any real 3D models MUST be embedded directly into that same file rather than referenced as separate files.
- **FR-002**: System MUST represent each device as a distinct shape colored according to its role (at minimum: router, switch, firewall, load balancer, client/endpoint).
- **FR-003**: System MUST represent each of a device's interfaces as an element structurally attached to its parent device, such that repositioning the device also repositions its interfaces.
- **FR-004**: System MUST render each link as a visible connection between the two specific interfaces it connects when interface-level data is available, and MUST fall back to a device-to-device connection when it is not (see Edge Cases).
- **FR-005**: Every device, every rendered interface, and every link MUST display a readable label identifying it (at minimum: device hostname, interface name, and link endpoints), and SHOULD surface additional descriptive metadata available from the source (for example, IP addresses, descriptions, software versions) when present.
- **FR-005a**: System MUST NOT embed credentials, secrets, or full running-configuration content in device/interface/link labels or panels, regardless of what metadata the source otherwise exposes.
- **FR-006**: System MUST include exactly one legend in the scene explaining the current color and shape conventions in use.
- **FR-007**: The engineer MUST be able to rotate, pan, and zoom the camera to view the rendered scene from any angle.
- **FR-008**: System MUST scale and center each rendered topology so the full scene is visible and readable by default, regardless of the value ranges or coordinate system used by the originating source data.
- **FR-009**: System MUST apply position, rotation, and scale updates to a rendered object as a complete set rather than partial updates, so that changing one property never silently resets another to an unintended default.

**Composable topology sourcing (Story 2)**

- **FR-010**: System MUST accept topology data sourced from any of NetClaw's existing topology-of-record and lab-emulation integrations, including at minimum Cisco Modeling Labs, GNS3, containerlab, EVE-NG, Nautobot, NetBox/Infrahub, IP Fabric, and Forward Networks.
- **FR-011**: System MUST apply the same rendering, labeling, coloring, and layout conventions regardless of which supported source supplied the topology data.
- **FR-012**: When a visualization request does not clearly identify which source to use and more than one is plausible, system MUST ask the engineer to clarify rather than guessing.
- **FR-013**: If a named topology source is unreachable or returns an error, system MUST report the failure clearly rather than producing an empty, partial, or misleading scene.

**Freeform topology input (Story 3)**

- **FR-014**: System MUST accept a plain-language, freeform description of devices and their connections as an alternative to a live source, and render it using the same conventions as a live-sourced topology.
- **FR-015**: When a freeform description omits a detail needed to render an element (such as role or interface name), system MUST substitute a clearly-indicated reasonable default rather than failing to render that element.

**State-based coloring (Story 4)**

- **FR-016**: When operational state (healthy, degraded, down) is available for a device or link, system MUST visually distinguish that state through color in addition to its base role coloring, and the legend MUST explain the state color convention.
- **FR-017**: When no operational state is available for a device or link, system MUST render it in a neutral default appearance rather than implying an unknown health state.

**Real 3D model stencils (Story 5)**

- **FR-018**: System MUST support an optional mode in which devices render using real 3D models in place of procedural shapes, defaulting to procedural shapes when this mode is not requested.
- **FR-019**: When real-stencil mode is enabled, system MUST resolve a model for each device role by first checking for an already-available asset, then attempting to source one from an origin with genuine open/CC0 licensing and a real programmatic search-and-download path — Sketchfab (filtered to CC0-licensed, downloadable models only) is the primary such source — and MUST embed the resolved model data directly into the single delivered file rather than linking to it as a separate file.
- **FR-019a**: When resolving a candidate model from Sketchfab (or any similar mixed-license catalog), system MUST verify the specific model's license is CC0 before using it, and MUST reject and fall back past any candidate whose license is unknown or not CC0, even if the catalog as a whole permits some downloads.
- **FR-020**: System MUST NOT attempt to automatically fetch or scrape 3D models from marketplaces that gate downloads behind login/checkout or whose licenses prohibit redistribution; for such sources, system MUST only check whether the engineer has manually supplied a matching asset.
- **FR-021**: When no permitted model is available for a device role, system MUST fall back automatically to that device's procedural shape and report which devices fell back and why.

**Cross-cutting**

- **FR-022**: All visualization requests described in this specification MUST be triggerable through natural-language conversation with NetClaw.
- **FR-023**: Each visualization request MUST produce its own independent, freshly-generated scene saved as a distinctly-named artifact in a persistent NetClaw workspace output location; NetClaw MUST NOT silently mutate or overwrite a previously generated scene, so the engineer can revisit or share past visualizations later.

### Key Entities

- **Topology Snapshot**: The complete set of devices, interfaces, links, and (if available) state data assembled for a single visualization request, regardless of whether it came from a live source or a freeform description.
- **Device**: A router, switch, firewall, load balancer, client/endpoint, or other network element; carries a hostname, a role used for shape/color selection, an optional operational state, a set of interfaces, and any additional descriptive metadata the source exposes (for example, software version, description) — excluding credentials or full running-configuration content.
- **Interface**: A named connection point belonging to exactly one parent Device; rendered as an element structurally attached to that device; the endpoint that Links attach to when interface-level data is available; carries an optional IP address and other source-provided descriptive metadata.
- **Link**: A connection between two Interfaces (or, as a fallback, two Devices); carries an identifying label and an optional operational state.
- **Legend**: A single always-present element in each rendered scene explaining the current role-based and state-based color/shape conventions.
- **Device Asset**: The visual representation resolved for a given device — either a procedural shape (default) or, in real-stencil mode, a real 3D model resolved through the permitted-source resolution chain, with a documented fallback reason when a real model is not used.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A network engineer can go from asking for a topology visualization to having a fully rendered, navigable 3D scene open in their browser in under 30 seconds for a typical lab-sized topology (dozens of devices), with no manual installation or setup step performed by the engineer.
- **SC-002**: 100% of devices, interfaces represented in a rendered scene, and links display a readable identifying label, and a legend explaining every color/shape convention in use is present in every rendered scene.
- **SC-003**: Across topologies sourced from at least two different supported integrations plus a freeform description, all three produce scenes that a network engineer judges to use consistent shape, color, and labeling conventions.
- **SC-004**: Across a sample of topologies with varied source coordinate ranges, 100% render fully visible and centered by default, with zero instances of devices rendering off-screen, overlapping due to scale error, or requiring manual camera repositioning to become readable.
- **SC-005**: When real-stencil mode is used on a topology where some device roles have no permitted model, 100% of those devices still render (via automatic fallback) with no missing or broken visual elements, and the engineer is told which devices fell back.
- **SC-006**: A network engineer can identify which devices or links are degraded or down by color alone, cross-checked against the legend, without needing to ask NetClaw to explain the scene.

## Assumptions

- Each visualization request produces a static snapshot of the topology at the time of the request; continuous live-updating of an already-rendered scene is out of scope for this feature (NetClaw's existing UE5 digital twin skill already covers live/continuous monitoring use cases for engineers who need that).
- The rendered scene is delivered as a self-contained artifact, saved with a distinct name per request in a persistent NetClaw workspace output location and opened in the engineer's own default web browser; no NetClaw-managed server process needs to stay running for the engineer to view or navigate it, and prior visualizations remain available to revisit or share.
- "Composable" means this skill consumes topology data already retrievable through NetClaw's existing source-integration skills (CML, GNS3, containerlab, EVE-NG, Nautobot, NetBox/Infrahub, IP Fabric, Forward Networks); it does not introduce new device-access or authentication mechanisms of its own.
- Procedural shapes are the default device appearance; real-3D-model stencil mode is opt-in and is a visual enhancement layered on top of the same underlying topology data, not a separate rendering pipeline. Real-stencil mode still produces a single self-contained file with any real 3D models embedded directly into it — it never trades away the zero-server, double-click-to-open delivery model, even at the cost of a larger file size.
- The set of device roles with real-3D-model support may be partial at any given time; automatic, graceful fallback to procedural shapes for unsupported roles is treated as correct behavior, not an error condition.
- Marketplaces without a real programmatic, redistribution-permitting download path (for example, Fab, TurboSquid, CGTrader, GrabCAD) are never scraped or auto-downloaded from; for those, this feature only verifies whether the engineer has already placed a matching asset and reports what is missing.
- Sketchfab is the primary automated source for real-stencil models: it has a genuine API-based search-and-download path, but its catalog is mixed-license (not everything is CC0), so this feature MUST check each candidate model's individual license via that same API and only use models confirmed CC0, rejecting anything else back to the procedural-shape fallback.
- Desktop/mouse interaction (rotate, pan, zoom) is the primary supported navigation method; touch-specific interaction is not a requirement for this feature.
- A single rendered scene is expected to comfortably handle a typical lab or campus-sized topology (tens of devices, hundreds of interfaces); extreme-scale topologies (thousands of devices) are not a target use case for this feature.
