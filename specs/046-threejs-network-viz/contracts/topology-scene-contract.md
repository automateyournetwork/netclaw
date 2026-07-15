# Contracts: Three.js Browser Network Topology Visualization

**Feature**: 046-threejs-network-viz
**Date**: 2026-07-05

## Overview

This feature has two kinds of contract: (1) internal Python module contracts between `threejs-network-viz`'s own submodules and the existing topology-source skills/MCP servers and the new `sketchfab-mcp` server it composes, and (2) the payload contract between the Python-generated HTML file and its own embedded JavaScript runtime — the one true "interface" this feature exposes to something outside the Python process, since the whole point of the feature is a static artifact with no further backend calls after generation.

## `sources.py` — topology-source adapters

**Internal contract**: one function per supported source, each returning the canonical model from data-model.md, never a source-specific shape:

```python
def from_cml(raw_topology: dict) -> TopologySnapshot
def from_gns3(raw_topology: dict) -> TopologySnapshot
def from_containerlab(raw_topology: dict) -> TopologySnapshot
def from_eve_ng(raw_topology: dict) -> TopologySnapshot
def from_nautobot(raw_topology: dict) -> TopologySnapshot
def from_netbox_infrahub(raw_topology: dict) -> TopologySnapshot
def from_ip_fabric(raw_topology: dict) -> TopologySnapshot
def from_forward_networks(raw_topology: dict) -> TopologySnapshot
def from_freeform(description: str) -> TopologySnapshot

def resolve_source(request_text: str, available_sources: list[str]) -> str | AmbiguousSourceError
```

**Upstream capability needed**: none new — each `from_*` adapter calls the existing corresponding topology-source skill/MCP exactly as any other NetClaw skill would, and maps its native response onto `TopologySnapshot`/`Device`/`Interface`/`Link`. If a source's native data has no interface-level detail, the adapter MUST leave `LinkEndpoint.interface_name` as `None` rather than fabricating one (data-model.md validation rules; FR-004).

**Failure contract**: a source that is unreachable or errors MUST raise a distinguishable exception (e.g., `SourceUnreachableError`) that the calling skill entry point catches and reports verbatim to the engineer (FR-013) — it MUST NOT return a partially-populated `TopologySnapshot`.

## `assets.py` — real-stencil resolution chain

**Internal contract**:

```python
def resolve_device_asset(role: str, real_stencil_mode: bool) -> DeviceAsset
def check_cached_asset(role: str) -> DeviceAsset | None
def search_sketchfab_cc0(role: str) -> SketchfabModelRef | None
def verify_cc0_license(model_uid: str) -> bool
def download_and_embed(model_uid: str, fmt: Literal["glb"]) -> str  # returns base64
```

**Upstream capability needed** — `sketchfab-mcp` (community MCP, `mcp-servers/sketchfab-mcp-server/`):

| Tool | Used for | Contract notes |
|---|---|---|
| `sketchfab-search` | Find role-relevant candidates | Called with `downloadable: true`; the tool has **no license parameter**, so results are unfiltered by license and MUST NOT be treated as pre-vetted |
| `sketchfab-model-details` | Verify license per candidate | `verify_cc0_license()` MUST read the response's license field and accept only an exact `"cc0"` slug match (research.md §3); any other value (including missing/unknown) is a rejection, not a warning |
| `sketchfab-download` | Fetch the accepted model | Requested in `glb` format specifically (single binary file, no separate external texture/buffer references to manage) |

**Failure/fallback contract**: `resolve_device_asset()` MUST NOT raise on any Sketchfab failure mode (unreachable, no candidates, all candidates rejected) — it always returns a valid `DeviceAsset` (falling back to `kind: procedural`) and appends a `FallbackNote` to the snapshot's `fallback_report` (FR-021). It MUST NOT call any search/download tool at all for a role whose only lead is a gated marketplace (Fab, TurboSquid, CGTrader, GrabCAD) — for those, it only checks a user-supplied local asset path and, if absent, falls back with reason `gated_marketplace_verify_only_no_asset` (FR-020).

## `scene_builder.py` → `html_template.py` — embedded topology payload

This is the one payload contract that crosses from Python into the browser runtime, embedded as a `<script type="application/json" id="topology-data">...</script>` block (or an inline JS `const TOPOLOGY = {...}` assignment) inside the generated HTML. It MUST be a direct, lossless JSON serialization of `TopologySnapshot` (data-model.md), with these renderer-facing conventions:

- Every `Device` entry MUST carry a complete `position` (x, y, z) — never partial — matching FR-009's "full transform, never partial" rule as applied to the JS side: the runtime JS MUST apply position/rotation/scale as one complete `THREE.Object3D` transform call per object, never mutate a single axis independently.
- Every `Interface` entry's `local_offset` is relative to its parent `Device`'s local origin, not world space — the runtime JS MUST add the Interface as a child (`parentGroup.add(interfaceObject)`) rather than compute and set a world-space position directly, so repositioning the parent moves it automatically (FR-003).
- `Link.endpoint_a`/`endpoint_b` reference objects by `hostname` (+ optional `interface_name`) — the runtime JS resolves the actual world position via `object.getWorldPosition()` at draw time, never a pre-computed static coordinate baked in Python, so the link stays correct even if a future revision repositions devices client-side.
- `DeviceAsset.kind === "real_model"` entries carry `embedded_glb_base64`; the runtime JS decodes it locally (`atob` → `Uint8Array`) and calls `GLTFLoader.parse(arrayBuffer, '', onLoad, onError)` — it MUST NOT attempt any `fetch`/`XMLHttpRequest` for model data (research.md §2; required for `file://` compatibility).
- The payload MUST include a `legend` object (role→color and state→color mappings) generated from the same `materials.py` tables the renderer itself uses, never a value hardcoded separately in the HTML template (mirrors FR-006/FR-009 of spec 045's own legend-freshness rule, reused here as a consistency convention).

## `output.py` — file delivery

**Internal contract**:

```python
def write_scene(html: str, snapshot_id: str) -> Path   # returns the written file's absolute path
def open_in_browser(path: Path) -> None
```

**Contract notes**: `write_scene()` MUST write to a persistent, NetClaw-managed workspace output directory with a filename that embeds `snapshot_id` (timestamp-derived) so repeated requests never collide or overwrite (FR-023, Clarification session). `open_in_browser()` MUST use the engineer's OS-default browser association (e.g., `webbrowser.open()` in Python) — it MUST NOT start or depend on any local HTTP server.
