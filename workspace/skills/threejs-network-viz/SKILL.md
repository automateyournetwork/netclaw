# Three.js Network Topology Visualization Skill

**Version**: 1.0.0
**Feature**: 046-threejs-network-viz
**Status**: Active

## Overview

Renders network topologies as interactive, fully-labeled 3D scenes directly in a web browser, using Three.js. Unlike NetClaw's UE5 (`ue5-network-viz`) and Blender (`blender-3d-viz`) visualization skills, this skill needs **no desktop application, no GPU, and no cross-OS bridge** — every visualization is a single, self-contained HTML file that opens directly in the engineer's own browser with no build step and no server process to manage, even in real-stencil mode.

Devices render as color-coded shapes by role (router, switch, firewall, load balancer, client); each device's interfaces are true child objects of that device (moving the device moves its interfaces automatically); links render as visible cables between the specific interfaces they connect (falling back to device-to-device when interface-level data isn't available); every device/interface/link is labeled with source-provided metadata (IP addresses, descriptions, etc., excluding credentials/config); operational state (healthy/degraded/down) overlays role coloring; and a legend explains every color/shape convention in use.

## Prerequisites

### Required

- **A modern desktop browser** (Chrome/Firefox/Edge) — nothing else. No engine, no GPU, no install.

### Optional (real-stencil mode, User Story 5)

- `SKETCHFAB_API_KEY` / `SKETCHFAB_USERNAME` in `.env` (see `.env.example`) — get a token from https://sketchfab.com/settings/password
- The vendored `sketchfab-mcp-server` (`mcp-servers/sketchfab-mcp-server/`), cloned and built via `npm install && npm run build`, registered as `sketchfab-mcp` in `config/openclaw.json`

### Topology sources

Any of NetClaw's existing topology-of-record or lab-emulation integrations — Cisco Modeling Labs, GNS3, containerlab, EVE-NG, Nautobot, NetBox/Infrahub, IP Fabric, or Forward Networks — or a freeform plain-language description requiring no live source at all.

## Natural Language Commands

### Render a live topology (User Story 1 & 2)

```
"Replicate the CML lab topology in a browser for me"
"Visualize my GNS3 project in Three.js"
"Show me the Nautobot-modeled network in a browser"
```

NetClaw resolves which source to use (asking for clarification if ambiguous and more than one is configured), retrieves the topology, builds the scene, writes it to `workspace/output/threejs-network-viz/topology-<timestamp>-<snapshot-id>.html`, and opens it in the default browser.

### Sketch a topology without a live source (User Story 3)

```
"Sketch a topology with a router called r1 and a switch called sw1, r1 connects to sw1"
"Show me two routers and a switch"
```

Produces the same quality scene as a live source, using the same shape/color/label/legend conventions. Omitted details (role, interface names) get clearly-marked defaults rather than failing to render.

### See health state (User Story 4)

State-based coloring is automatic whenever a source reports device/link operational state — no separate command needed. The legend explains both the role-color and state-color conventions together.

### Real 3D model stencils (User Story 5)

```
"Visualize the CML lab with real 3D models"
"Use real-stencil mode for this topology"
```

Enable real-stencil mode to attempt real 3D models (via Sketchfab, filtered to CC0-licensed models only) instead of procedural shapes, wherever a permitted model is found. Any device role without a verified CC0 model falls back automatically to its procedural shape, and NetClaw reports which devices fell back and why. **In practice, expect fallback to be the common outcome** — Sketchfab's catalog has essentially no CC0-licensed network-equipment-specific models; real-stencil mode is a visual enhancement layered on top of the same reliable procedural rendering, not a replacement for it.

Real-stencil mode never scrapes or auto-fetches from gated marketplaces (Fab, TurboSquid, CGTrader, GrabCAD) — for those, it only checks whether a user has manually placed a matching asset at `workspace/output/threejs-network-viz/assets/user-supplied/<role>.glb`.

### Navigate the scene

Standard mouse/trackpad controls once the page is open: left-drag to rotate, scroll to zoom, right-drag to pan (via `OrbitControls`).

## Architecture

| Module | Responsibility |
|---|---|
| `topology_model.py` | Canonical `Device`/`Interface`/`Link`/`TopologySnapshot` types every other module consumes |
| `layout.py` | Force-directed 3D layout with centroid re-centering (ported from `ue5-network-viz`) |
| `materials.py` | Role/state color tables and hostname-based device-role inference |
| `sources.py` | One adapter per topology source (8 live integrations + freeform), plus source-selection disambiguation |
| `assets.py` | Real-stencil resolution chain: cache/user-asset check → Sketchfab search + per-model CC0 verification → download+embed → procedural fallback |
| `scene_builder.py` | Builds the embedded topology JSON payload consumed by the HTML template |
| `html_template.py` | Renders the single self-contained HTML file, inlining vendored Three.js r147 |
| `output.py` | Writes the timestamped output file and opens it in the browser |
| `vendor/three/` | Vendored Three.js r147 core + `OrbitControls`/`GLTFLoader` (the last release with classic global/non-module builds — see `research.md` §1-2) |

## Environment Variables

| Variable | Required | Purpose |
|---|---|---|
| `SKETCHFAB_API_KEY` | Only for real-stencil mode | Sketchfab API authentication |
| `SKETCHFAB_USERNAME` | Only for real-stencil mode | Reference/attribution only, not required by the API itself |

## Known Limitations

- Extreme-scale topologies (thousands of devices) are not a target use case — the layout and scene are tuned for tens-of-devices/hundreds-of-interfaces lab and campus scale.
- Real-stencil mode embeds the full model into the HTML file (no linked assets, to preserve zero-server delivery), so a topology with several real models can produce a multi-megabyte file — a real, live-downloaded CC0 model tested during development was ~14MB (19MB base64-embedded).
- The vendored `sketchfab-mcp-server` had a real bug (license field silently dropped from its `sketchfab-model-details` tool output) found and patched during implementation — see the "NetClaw patch" comments in `mcp-servers/sketchfab-mcp-server/index.ts`. If this vendored server is ever re-cloned fresh from upstream, the patch must be reapplied and rebuilt (`npm run build`) before real-stencil mode's CC0 verification will work correctly.

See `specs/046-threejs-network-viz/tasks.md` for the full implementation history and `research.md` for the technical decisions behind the Three.js version pinning and Sketchfab integration.
