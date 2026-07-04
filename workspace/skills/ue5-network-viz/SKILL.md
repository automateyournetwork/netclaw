# UE5 Network Visualization Skill

**Version**: 0.2.0
**Feature**: 044-ue5-mcp-network-viz (foundation), 045-ue5-digital-twin (interactive digital twin)
**Status**: Active

## Overview

The UE5 Network Visualization skill enables 3D network topology visualization in Unreal Engine 5.8 using the built-in MCP server. Network engineers can request topology renderings via natural language, and NetClaw transforms network data into an immersive 3D scene with color-coded devices, animated links, and real-time health updates.

**045-ue5-digital-twin** extends this from a static snapshot into an interactive digital twin / network looking-glass: interface-level actors, universal labeling, a color legend, live traffic/health/trap-driven state, real ping/traceroute animation, on-demand config panels, PagerDuty incident correlation, historical playback, hierarchical zoom, and a floating metrics HUD — all conversational, no in-engine UI. See the "Digital Twin Capabilities (045)" section below for full command reference.

## Prerequisites

### Required Software

1. **Unreal Engine 5.8+** with MCP plugin enabled
   - Download from [unrealengine.com](https://www.unrealengine.com)
   - Enable plugin: Edit > Plugins > "Unreal MCP"
   - Auto-start server or run `ModelContextProtocol.StartServer`

2. **NetClaw Environment**
   - Python 3.10+
   - httpx package installed

3. **Network Data Source** (at least one)
   - pyATS with CDP/LLDP data
   - SuzieQ topology
   - GNS3/CML lab
   - Manual topology definition

### System Requirements

- **GPU**: Discrete GPU recommended (RTX 3060+ or AMD equivalent)
- **RAM**: 32GB+ for UE5
- **Storage**: ~100GB for UE5 installation

## Natural Language Commands

### Render Topology

```
"Render my network in UE5"
"Visualize the topology in Unreal Engine"
"Show me the network in 3D"
"Create a UE5 scene from my pyATS topology"
```

### Update Visualization

```
"Refresh the network visualization"
"Update the UE5 scene with current topology"
"Re-render only the changed devices"
```

### Health State Updates

```
"Mark router-1 as critical"
"Show core-sw-01 as warning state"
"Set the link between router-1 and switch-1 as down"
"Highlight unhealthy devices"
```

### Camera Navigation

```
"Focus on router-1"
"Show me the core routers"
"Fly through the network"
"Give me an overview of the entire topology"
"Switch to top-down view"
```

### Device Inspection

```
"What is device router-1?"
"List all rendered devices"
"Show me device details for core-sw-01"
```

### Scene Management

```
"Clear the UE5 scene"
"Reset the visualization"
```

## Digital Twin Capabilities (045)

Everything below extends a topology already built by the commands above into
an interactive digital twin — all conversational, no in-engine UI. Every
capability refuses (and tells you why) rather than silently attempting or
ignoring a request that names a device, interface, or link not present in
the currently built scene.

### Interfaces, Labels, Legend (always on)

Every render/refresh automatically gets: a separate small actor for each
up/up interface (attached near its parent device, with links connecting to
interfaces rather than device centers when interface data is available), a
compact "N down: ..." summary per device instead of one actor per down
interface, a label on every device/interface/link, and a legend actor
showing the live device-type color mapping. Nothing extra to ask for —
"render my topology" and "refresh the topology with colours" both include
all of this.

```
"Render my topology"
"Refresh the topology with colours"
```

### Traffic Visibility

```
"Show traffic on r1's links"
"Refresh the traffic visualization"
```

Colors links/interfaces on a green→yellow→red gradient from utilization data
you or NetClaw has already retrieved (via gnmi-mcp/pyATS). Links/interfaces
with no utilization data keep their normal appearance — never an error.

### Live Health

```
"Refresh device health"
"Start live mode"
"Is live mode running?"
"Stop live mode"
```

On-demand health refresh recolors device/link actors from real gnmi-mcp/pyATS
status. Live mode runs continuous background polling until explicitly
stopped; one unreachable device never blocks polling the rest.

### SNMP Trap Alerts (automatic once wired to snmptrap-mcp)

A real linkDown trap latches a sticky alert (hot pink) on the affected
interface that persists across unrelated refreshes — cleared only by a
matching linkUp trap or a confirmed healthy poll, never by time alone. Traps
for a device/interface not in the current topology are ignored, not errored.

### Ping and Traceroute

```
"Ping r1 from sw1"
"Traceroute from pc1 to r1"
```

Animates a real ping/traceroute result (green = success, red = failure/
timeout) along the path between actors. A device not in the current
topology is reported, not attempted.

### Show Config / Metrics HUD

```
"Show me r1's running config"
"Show metrics for sw1"
```

Renders a readable text panel near the device's actor with real content
(config or CPU/memory/uptime). Asking again replaces the panel with fresh
data — it never stacks duplicates or shows a stale cached value.

### Incident Correlation

```
"Is there an open incident for r1?"
"Check incidents for the r1-sw1 link"
```

Matches a device (or either endpoint of a link) against open PagerDuty
incidents by hostname substring in the title/description/service name. A
match applies a distinct alarm color (hot pink); no match is clearly
reported, never a silent no-op.

### Historical Playback

```
"Replay the last 30 minutes"
"Replay from 2pm to 2:30pm at double speed"
```

Replays recorded health/traffic/trap changes against the live scene in
original order, compressed by default (2x) with an adjustable speed. An
empty window is reported explicitly.

### Hierarchical Zoom

```
"Zoom into rack-1"
"Zoom out to the full site"
```

Groups devices by real NetBox/Infrahub rack/site placement first, with a
manual grouping fallback for devices neither source has placement for.
Zooming only toggles actor visibility and reframes the camera — it never
rebuilds the topology, so nothing is lost or duplicated when you zoom back
out.

## Device Type Visualization

| Device Type | Shape | Color | Hex |
|-------------|-------|-------|-----|
| Router | Cube | Blue | #3366CC |
| Switch | Cube | Green | #33B34D |
| Firewall | Cube | Red | #CC3333 |
| Access Point | Sphere | Yellow | #E6CC33 |
| Load Balancer | Cube | Purple | #9933CC |
| Endpoint | Sphere | Orange | #E68019 |
| Unknown | Cube | White | #FFFFFF |

## Health State Colors

### Device Status

| Status | Color | Effect |
|--------|-------|--------|
| Healthy | Device type color | Normal |
| Warning | Orange | Pulsing glow |
| Critical | Bright Red | Bright emissive |
| Unreachable | Dark Red | Flashing |
| Unknown | Gray | Dimmed |

### Link Status

| Status | Color | Visual |
|--------|-------|--------|
| Healthy | Green | Solid |
| Degraded | Yellow | Animated |
| Down | Red | Broken/dashed |
| Unknown | Gray | Faded |

## Topology Data Format

### Input Format

```json
{
  "devices": [
    {
      "hostname": "core-rtr-01",
      "device_type": "router",
      "ip_addresses": ["10.0.0.1"],
      "model": "Cisco ISR4451",
      "vendor": "Cisco",
      "status": "healthy",
      "utilization": 45.2
    }
  ],
  "links": [
    {
      "source_device": "core-rtr-01",
      "target_device": "dist-sw-01",
      "source_interface": "GigabitEthernet0/0",
      "target_interface": "GigabitEthernet1/0/1",
      "status": "healthy",
      "bandwidth": 1000,
      "utilization": 12.5
    }
  ],
  "source": "pyATS"
}
```

### Device Type Inference

If `device_type` is not specified, it's inferred from hostname:

- `rtr`, `router`, `cr`, `er` → Router
- `sw`, `switch`, `ds`, `as` → Switch
- `fw`, `firewall`, `asa`, `ftd` → Firewall
- `ap`, `wap`, `wireless` → Access Point
- `lb`, `f5`, `bigip` → Load Balancer
- `srv`, `server`, `host` → Endpoint

## UE5 MCP API Reference

### Critical Conventions (Discovered via Testing)

1. **Session Management**: UE5 MCP requires `Mcp-Session-Id` header from initialization
2. **Tool Search Mode**: Use meta-tools `list_toolsets`, `describe_toolset`, `call_tool`
3. **ProgrammaticToolset**: Scripts use `execute_tool(tool_name, arguments)` - arguments must be JSON strings, not dicts
4. **find_actors**: Requires `name`, `tag`, and `collision_channels` parameters (all required)
5. **_StrictDict**: Use direct key access `["key"]` (or `.get("key")` with **no** default) — `.get("key", default)` raises `_StrictDict.get() does not support a default value`. This ONLY applies to dicts/objects returned by calling *into* UE5 from a running script (e.g. `get_component_by_class()`, `get_all_level_actors()`). It does NOT apply to plain dicts you build yourself or to JSON already parsed client-side over the MCP wire — `ue5_mcp_client.py` and the per-actor functions in `actors.py` are all client-side and safe. It bites specifically inside code passed to `execute_tool_script` (see "Batch Build Pattern" below).
6. **Mesh Assignment**: Use `staticMesh` (lowercase 's') and pass the **loaded asset object**, not just path string
7. **Level Saving**: Must save to `/Game/` path (not `/Temp/`) to avoid crashes — see `save_level_as()`, which now does this programmatically instead of requiring a manual File > Save Current Level As.
8. **TextRenderActor billboard artifact**: spawning a `TextRenderActor` also spawns an editor-only billboard/sprite child component (renders as a black "Tt" box in editor viewport screenshots, separate from the real text). Hide it: `for comp in actor.get_components_by_class(unreal.BillboardComponent): comp.set_visibility(False)`.
9. **Label sizing**: a fixed `world_size` (24, later tried 95) is unreadable once a topology has more than a handful of devices. Scale it to the scene's bounding-box diagonal instead — roughly `diagonal / 20`, floored around 100. See `_compute_batch_specs()` in `actors.py`.
10. **Persist working files under `~/.openclaw/workspace/ue5-topo/`, never `/tmp`** — `/tmp` is wiped every time WSL restarts, which happens on every host crash. Losing an in-progress topology capture and generated build script to a crash cost real rework time during the 2026-07-01 incident. `persist_build_artifacts()` in `actors.py` does this automatically for every batch build.

### Batch Build Pattern (execute_tool_script)

**Use this for any initial/full topology build.** Spawning one actor at a time (`spawn_device_actor`/`spawn_link_actor`, one MCP round trip each) costs roughly 4 round trips per actor — for a 10-device/12-link topology that's ~90 round trips at 15-20s apiece, several minutes total, and every round trip is a chance for a host crash to leave the build half-finished. This is exactly what happened repeatedly during the 2026-07-01 live incident.

Instead, generate one Python script and run the *entire* build inside UE5 in a single `execute_tool_script` call:

```python
from workspace.skills.ue5_network_viz import render_topology_fast

async with UE5MCPClient() as client:
    # One MCP round trip builds every device, link, and label at once.
    # Falls back automatically to the slower per-actor path if the batch
    # build raises for any reason — this can never be worse than before.
    result = await render_topology_fast(client, topology)
```

Under the hood (`actors.render_topology_batch` / `actors.build_batch_scene_script`):

- All positioning, coloring, and label-sizing math happens **client-side**, before the script is generated. The UE5-side script only plays back pre-computed literals — it never needs to read a key out of a UE5-returned dict, so it can't trip the `_StrictDict` bug.
- `execute_tool_script`'s input schema is `{"script": "<python source>"}` (`script` is a required string) — confirmed live against a running UE5 8.0 MCP server on 2026-07-02.
- The exact **return-value** convention was not confirmed live (the UE5 session hung mid-test — the same instability this whole incident was about). The script sets a `result` variable to a JSON summary as its best-effort return value, but the client-side code does not trust it — it re-queries the scene via `find_netclaw_actors()` afterward to confirm what actually got spawned, the same way the live agent verified state by hand ("Verification confirms the scene: 10 devices, 12 links in their folders"). Re-verify this convention next time UE5 is stable for an extended session.
- `save_level_as(client, package_path="/Game/NetClaw/NetClawTopo")` calls `unreal.EditorLoadingAndSavingUtils.save_map(...)` via `execute_tool_script`, solving the "`/Temp/` level can't be saved" blocker programmatically instead of requiring the user to do it by hand.
- `capture_scene_screenshot(client, filename, width, height)` calls `unreal.AutomationLibrary.take_high_res_screenshot(...)` via `execute_tool_script`, avoiding the built-in `CaptureViewport` MCP tool entirely — that tool's schema requires every field, including a full nested `annotations` struct, with no defaults honored despite being marked optional.

`render_topology_incremental()` (health-state updates on an already-built scene) intentionally still uses the per-actor path — updating one or two actors doesn't benefit from rebuilding the whole scene in one script.

### Build-Specific Gotchas (confirmed live, 2026-07-02, second UE5 8.0 build)

Not every UE5 MCP build behaves the same way. Two build-specific issues surfaced during a real CML+pyATS→UE5 rebuild, both now handled:

1. **`tool_name` must be the SHORT method name, not the fully-qualified `<toolset>.method` string.** This build silently returned `"Unknown tool"` for every call because the skill passed the fully-qualified name in `tool_name` on top of the already-separate `toolset_name` — a "double-qualified" call this build's dispatcher didn't recognize. `UE5MCPClient.call_tool()` now strips the toolset prefix from `tool_name` automatically before sending, so every existing `TOOL_*` constant (kept fully-qualified for readability) keeps working unchanged. It also now detects `"Unknown tool"`/`"Unknown toolset"`/`"tool not found"` in the response text and reports `success=False` instead of silently reporting success — this exact gap is what caused a **false positive** ("10 devices rendered" when nothing had actually spawned).
2. **`execute_tool_script`'s Python sandbox can forbid `import unreal`.** On this build, only stdlib modules (`math`, `json`, `re`, `time`, etc.) are importable inside a script — meaning the entire batch-build pattern above is structurally unusable on this build, full stop. This fails immediately when the script runs, as a normal (non-exception) `success=False` result, not a Python exception — `render_topology_fast()` was fixed to check `result.success` in addition to catching exceptions, since only catching exceptions meant the automatic fallback to the per-actor path never actually triggered for this failure mode.

**Lesson**: always verify a build's actual capabilities (tool-name convention, `execute_tool_script` import allowlist) with a cheap smoke test before trusting a full build to succeed — do not trust a script's self-reported summary or a blanket `success=True` over re-querying the scene for what's really there.

### More Build-Specific Gotchas (confirmed live, 2026-07-03)

1. **SSE keep-alive can make a client hang on an answer that already arrived.** Some UE5 MCP builds respond over `text/event-stream` and keep the connection open as a keep-alive stream even after sending the actual JSON-RPC result. `UE5MCPClient` used to call `httpx`'s plain `.post()` and read `response.text`, which makes httpx wait for the full response body — i.e. for the connection to close — before returning. On a keep-alive build that hangs until the timeout fires even though the real answer was available instantly. This is very likely responsible for several "UE5 seems frozen" symptoms hit throughout this whole investigation. Fixed by switching `_send_request()` and `initialize_session()` to httpx's streaming API (`client.stream(...)` + `aiter_lines()`), reading the SSE stream line-by-line and stopping as soon as a complete JSON-RPC object arrives, instead of waiting for the connection to close. Verified live 2026-07-03: session init and `list_toolsets()` dropped from routinely timing out at 30-60s to completing in under half a second.
2. **`set_actor_transform` does not reliably preserve omitted fields, despite its own docs claiming it does.** Setting only `scale` on an existing actor was observed to silently reset its `location` to `(0,0,0)` on a live build — this is what caused an entire 22-actor scene to visually "stack in the middle" after an otherwise-successful build. Always pass the full transform (location + rotation + scale) together in a single call; never assume a partial update leaves the rest alone, regardless of what the tool's own documentation says.
3. **Actor refPaths can go stale across a level save.** Actors built on an unsaved `/Temp/Untitled_N` level and later persisted to a real `/Game/` level get a NEW refPath under the new level path — old refPaths captured before the save (e.g. in a persisted JSON artifact) will not resolve. Re-resolve actors via `find_actors(tag="netclaw")` and match by their stable index/name suffix rather than trusting a previously-cached refPath across a save/reload.
4. **CML canvas coordinates need both scaling AND centering, not just scaling.** A topology positioned by taking raw CML editor-canvas (x, y) and multiplying by a flat scale factor will have the right *relative* shape but can land its centroid thousands of units from world origin — CML's canvas coordinates have no relationship to where "the middle of the map" is in UE5. Always compute the centroid of the scaled positions and subtract it before spawning (see `_compute_batch_specs()`/the centering fix in `layout.py`'s `ForceDirectedLayout.run()` for the reference implementation) — do this for BOTH device positions and link midpoints/endpoints, derived from the already-centered device positions rather than recomputed from raw coordinates.

### 045-ue5-digital-twin Live Test Findings (confirmed live, 2026-07-03)

1. **The `execute_tool_script` sandbox restriction from gotcha #2 above initially appeared to block ALL of 045's new capabilities** — interface actors, labels, the legend, and live coloring were all originally implemented via `execute_tool_script` + native `unreal.*` calls. On a build where this sandbox forbids `import unreal` (confirmed live: `"Import of 'unreal' is not permitted. Allowed modules: {json, time, datetime, re, copy, math}"`), none of that could run. **This has since been resolved** for interfaces, labels, the legend, and all status/traffic/trap/incident/ping coloring — see items 5-8 below for the non-scripted replacement path. Config/metrics panels (`panels.py`) and hierarchical zoom (`hierarchy.py`'s `zoom_to`/`zoom_out_to_site`) still use `execute_tool_script` and remain blocked on this build; they're unit-tested and will activate automatically on a build without this restriction.
2. **A cosmetic lighting-setup failure was silently flipping a successful render to `success=False`.** `render_topology()`'s per-actor path wrapped the entire function (device spawn, link spawn, AND the optional lighting step) in one `try/except`. When `setup_default_lighting()` raised (itself a separate pre-existing bug — `scene.py`'s lighting functions used the wrong `call_tool()` keyword arguments), the shared `except` clause overwrote an already-correct `success=True, devices_rendered=4, links_rendered=3` down to `success=False`, making a fully successful 4-device render report as a total failure. Fixed by isolating the lighting step in its own try/except that records a non-fatal error instead of failing the whole render — never let an optional, cosmetic step's failure invalidate already-completed substantive work.
3. **`find_actors`'s returned actor references carry only `refPath` (the engine's auto-generated internal object name, e.g. `StaticMeshActor_34`), never the display Label** (e.g. `NC_core-rtr-01`) that `set_actor_label`/`generate_device_actor_name` set. Any code that re-queries `find_actors` afterward and tries to classify or count actors by matching a `"name"`/`"label"` field against a generated `NC_...` string (as opposed to trusting a script's own self-reported spawn tally, or the calling function's own per-actor `spawn_result.success` count) will not find what it's looking for. `render_topology()`'s per-actor path is unaffected — it counts from each spawn call's own immediate success response, never from a post-hoc `find_actors` re-query.
4. **`spawn_device_actor`/`spawn_link_actor` set the actor's real Label to a value that never matches `generate_device_actor_name()`'s "NC_..." string.** The spawn call's requested `"name"` is not reliably honored by the engine (it may fall back to an auto-generated name like `StaticMeshActor_34`), and the actor's *displayed* Label ends up being the bare hostname, not the `NC_`-prefixed one. Any later operation that reconstructs an actor reference from `generate_device_actor_name(hostname)` — coloring, destroying, focusing — silently targets nothing. **Fixed** by capturing the REAL reference returned by the spawn call itself and storing it in `scene.py`'s new `device_refs`/`link_refs`/`interface_refs` dicts (`register_device_actor(..., ref_path=actor.ref_path)` etc.); every later operation looks up this stored ref instead of reconstructing one from the name.
5. **`ObjectTools.set_properties` on mesh/material properties (`staticMesh`, `overrideMaterials`) silently no-ops when targeting the actor instead of its StaticMeshComponent.** `spawn_device_actor`'s original mesh-assignment call passed the *actor* reference; `get_properties` afterward confirmed `staticMesh` stayed `"None"`. Fixed by resolving the component first via `ActorTools.get_components` (`actors.get_mesh_component()`) and targeting that. This was silently breaking mesh assignment since 044 shipped — devices were invisible StaticMeshActors with no mesh at all, not a scale or color problem.
6. **`editor_toolset.toolsets.material_instance.MaterialInstanceTools` is a real, confirmed-available toolset — not script-based, unaffected by the `execute_tool_script` sandbox.** `MaterialInstanceTools.create(folder_path, asset_name, parent)` + `set_vector_parameter(instance, "Color", {r,g,b,a})`, applied to a mesh component's `overrideMaterials` array via `ObjectTools.set_properties`, is the confirmed-working, non-scripted way to recolor an actor. Parent it to `/Engine/BasicShapes/BasicShapeMaterial` — the same material this skill's own primitive meshes already use — which exposes exactly a `Color` vector parameter and a `Roughness` scalar. See `actors.apply_color_to_actor_ref()`/`_get_or_create_color_material()`.
7. **`EditorToolset.EditorAppToolset` has real, non-scripted camera and screenshot tools** (`SetCameraTransform`, `GetCameraTransform`, `FocusOnActors`, `CaptureViewport`) that were undiscovered through all of 044 and most of 045 — `camera.py`'s functions and `capture_scene_screenshot()` were built on `execute_tool_script` because this toolset simply hadn't been enumerated yet. `CaptureViewport` returns a base64 PNG directly in its response. Its schema has the same "marked optional but actually required" quirk documented elsewhere in this file — `captureTransform` and every field of `annotations` (including `classFilter`) must be passed explicitly even though the schema marks them optional; pass `gridSpacing`/`gridExtent`/`gridHeight`/`maxLabelDistance`/`maxLabels` all `0` with any valid `classFilter` to suppress the grid/label overlay entirely.
8. **The base primitive meshes (`/Engine/BasicShapes/Cube.Cube`, `Sphere.Sphere`, `Cylinder.Cylinder`) are already 100cm (1m) per side/diameter at `scale=1.0` — not 1cm as this codebase assumed since 044.** `DEFAULT_DEVICE_SCALE` was `{100,100,100}`, intended as "1 meter cubes" per its own comment, but actually produced **100-meter** cubes (confirmed live via `ActorTools.get_actor_bounds`: exactly 10000×10000×10000cm). This single bug explains nearly every visual-scale confusion this feature produced: devices completely overlapping despite a seemingly-generous layout spacing, screenshots showing one giant dark silhouette filling the frame, and every position offset elsewhere in this codebase (label height above a device, interface ring radius, camera framing distance) being tuned for human-scale objects and rendered meaningless against 100m devices. Fixed by using `scale=1.0` for devices (`INTERFACE_SCALE` similarly corrected from `20` to `0.2`, link cylinder thickness from `10` to `0.1`) — always verify a "scale" constant against `get_actor_bounds()` on a live build rather than trusting a comment's stated intent.
9. **`TextRenderComponent` only renders its text correctly from one side of its plane** — at the default `rotation=[0,0,0]`, labels read mirrored/backwards from `camera.py`'s default overview camera position. `spawn_label_actor()` now defaults to `rotation=[0, 225, 0]` (yaw toward -X,-Y, matching where `calculate_overview_position()` places the default camera) — a heuristic default, not a true camera-facing billboard, but it makes labels readable from NetClaw's own default viewpoint instead of facing away from it.

### Proper Actor Spawning Workflow

**CRITICAL**: To avoid null mesh errors when saving:

```python
# 1. Load the mesh asset FIRST
loaded_mesh = await load_asset(mesh_path)  # Returns asset object

# 2. Spawn empty StaticMeshActor
actor = await add_to_scene_from_class(
    actor_type={"refPath": "/Script/Engine.StaticMeshActor"},
    name="MyActor",
    xform={...}
)

# 3. Assign mesh using set_properties with lowercase 'staticMesh'
await set_properties(
    instance=actor["returnValue"],
    values='{"staticMesh": <loaded_mesh_object>}'  # NOT just path string!
)

# 4. Set label and tags
await set_label(actor=actor["returnValue"], label="Device Name")
await add_tag(actor=actor["returnValue"], tag="netclaw")
```

### Saving Topology Levels

To avoid `/Temp/` path crashes when saving:

1. **Before rendering**: Create folder `/Game/NetClaw/` via AssetTools.create_folder
2. **After rendering**: Use File > Save Current Level As... > `/Game/NetClaw/NetClawTopo`
3. **Subsequent saves**: Ctrl+S will work normally once saved to `/Game/` path

**Why /Temp/ crashes**: UE5 creates temporary levels in `/Temp/Untitled_*` which cannot be properly saved. Always save to a `/Game/` path first.

### Key Toolsets

| Shorthand | Full Path |
|-----------|-----------|
| scene | `editor_toolset.toolsets.scene.SceneTools` |
| actor | `editor_toolset.toolsets.actor.ActorTools` |
| material | `editor_toolset.toolsets.material_instance.MaterialInstanceTools` |
| primitive | `editor_toolset.toolsets.primitive.PrimitiveTools` |
| programmatic | `editor_toolset.toolsets.programmatic.ProgrammaticToolset` |

### Key Tools for Actor Spawning

| Operation | Full Tool Name |
|-----------|----------------|
| Spawn from asset | `editor_toolset.toolsets.scene.SceneTools.add_to_scene_from_asset` |
| Spawn from class | `editor_toolset.toolsets.scene.SceneTools.add_to_scene_from_class` |
| Remove actor | `editor_toolset.toolsets.scene.SceneTools.remove_from_scene` |
| Find actors | `editor_toolset.toolsets.scene.SceneTools.find_actors` |
| Set transform | `editor_toolset.toolsets.actor.ActorTools.set_actor_transform` |
| Run arbitrary script inside UE5 | `editor_toolset.toolsets.programmatic.ProgrammaticToolset.execute_tool_script` — schema `{"script": str}`, `script` required. Used by the batch build pattern above. |

### Python API Note (packaging fix, 2026-07-02)

Every submodule (`actors.py`, `renderer.py`, `scene.py`, `camera.py`, `telemetry.py`) previously used bare absolute imports (`from actors import ...`) while `__init__.py` used package-relative imports (`from .actors import ...`). That combination meant the documented `from workspace.skills.ue5_network_viz import ...` entry point in this file's own Quick Start (below) had never actually worked — it failed immediately with `ModuleNotFoundError`. This is why the 2026-07-01 incident's live agent had to hand-write everything from scratch in ad hoc scripts instead of using this skill's own API. Every cross-module import now uses a `try: from .x import ... except ImportError: from x import ...` shim, so both the documented package import **and** the sys.path-style loading a live agent does when writing ad hoc scripts work correctly. Verified 2026-07-02 by importing the package both ways.

### Asset Paths for Basic Shapes

```python
ASSET_PATHS = {
    "cube": "/Engine/BasicShapes/Cube.Cube",
    "sphere": "/Engine/BasicShapes/Sphere.Sphere",
    "cylinder": "/Engine/BasicShapes/Cylinder.Cylinder",
    "cone": "/Engine/BasicShapes/Cone.Cone",
}
```

### Transform Format

```json
{
  "location": {"x": 0, "y": 0, "z": 0},
  "rotation": {"pitch": 0, "yaw": 0, "roll": 0},
  "scale": {"x": 50, "y": 50, "z": 50}
}
```

### Actor Reference Format

```json
{"refPath": "/Game/Maps/Untitled.Untitled:PersistentLevel.ActorName"}
```

## Configuration

### Environment Variables

```bash
# UE5 MCP Server URL (default: localhost:8000)
UE5_MCP_URL=http://127.0.0.1:8000/mcp
```

### MCP Server Registration

In `config/openclaw.json`:

```json
{
  "mcpServers": {
    "unreal-mcp": {
      "url": "${UE5_MCP_URL:-http://127.0.0.1:8000/mcp}"
    }
  }
}
```

## Example Workflows

### Basic Topology Rendering

```python
from workspace.skills.ue5_network_viz import (
    UE5MCPClient,
    safe_render_topology,
)

# Define or fetch topology
topology = {
    "devices": [
        {"hostname": "core-rtr-01", "device_type": "router"},
        {"hostname": "dist-sw-01", "device_type": "switch"},
        {"hostname": "dist-sw-02", "device_type": "switch"},
        {"hostname": "fw-01", "device_type": "firewall"},
    ],
    "links": [
        {"source_device": "core-rtr-01", "target_device": "dist-sw-01"},
        {"source_device": "core-rtr-01", "target_device": "dist-sw-02"},
        {"source_device": "dist-sw-01", "target_device": "fw-01"},
        {"source_device": "dist-sw-02", "target_device": "fw-01"},
    ],
}

# Render with error handling
result = await safe_render_topology(topology)
print(f"Rendered {result.devices_rendered} devices, {result.links_rendered} links")
```

### Real-Time Health Updates

```python
from workspace.skills.ue5_network_viz import (
    UE5MCPClient,
    set_device_critical,
    set_link_down,
)

async with UE5MCPClient() as client:
    # Mark device as critical (red glow)
    await set_device_critical(client, "core-rtr-01")

    # Mark link as down (red)
    await set_link_down(client, "core-rtr-01", "dist-sw-01")
```

### Camera Fly-Through

```python
from workspace.skills.ue5_network_viz import (
    UE5MCPClient,
    flythrough_orbit,
    focus_on_device,
)

async with UE5MCPClient() as client:
    # Focus on specific device
    await focus_on_device(client, "core-rtr-01")

    # Orbital fly-through around topology
    await flythrough_orbit(client, duration=30.0)
```

### Incremental Updates

```python
from workspace.skills.ue5_network_viz import (
    UE5MCPClient,
    render_topology_incremental,
    parse_topology_dict,
)

async with UE5MCPClient() as client:
    # Initial render
    await render_topology_from_dict(client, initial_topology)

    # Later: incremental update (preserves camera)
    new_topology = parse_topology_dict(updated_data)
    await render_topology_incremental(client, new_topology)
```

## Integration with Other Skills

### pyATS Integration

```
"Get topology from pyATS and render in UE5"
"Visualize the testbed in Unreal Engine"
```

### SuzieQ Integration

```
"Render SuzieQ topology in UE5"
"Show me the SuzieQ network in 3D"
```

### GNS3/CML Integration

```
"Render my GNS3 lab in UE5"
"Visualize the CML topology in Unreal Engine"
```

### Telemetry Integration (Feature 010)

When Telemetry Receivers MCP is active, device/link colors update automatically based on:

- Syslog messages (severity → device status)
- SNMP traps (link up/down)
- NetFlow data (utilization → link color intensity)

## Performance

| Metric | Target | Notes |
|--------|--------|-------|
| Render 100 devices | <60 seconds | With materials and lighting |
| Status color update | <30 seconds | Real-time telemetry |
| Camera transitions | Smooth 60fps | Native UE5 interpolation |
| Max devices | 200 | Performance limit |
| Max links | 500 | Performance limit |

## Troubleshooting

### "Cannot connect to UE5 MCP"

1. Verify UE5 is running
2. Check MCP plugin is enabled (Edit > Plugins)
3. Run `ModelContextProtocol.StartServer` in UE5 console
4. Verify port 8000 is not blocked

### "Tool not found"

1. Run `ModelContextProtocol.RefreshTools` in UE5 console
2. Verify AllToolsets plugin is enabled

### "Actors not appearing"

1. Ensure viewport shows world origin
2. Check scale (UE5 uses centimeters, actors need scale 50+)
3. Check Output Log for spawn errors

### Slow first command

Normal behavior - UE5 MCP first request may timeout. Retry.

## Related Documentation

- [Quickstart Guide](./quickstart.md)
- [UE5 MCP Tool Contracts](../../specs/044-ue5-mcp-network-viz/contracts/mcp-tools.md)
- [Data Model](../../specs/044-ue5-mcp-network-viz/data-model.md)
- [Feature Specification](../../specs/044-ue5-mcp-network-viz/spec.md)
