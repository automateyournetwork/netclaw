# Data Model: Three.js Browser Network Topology Visualization

This model is the canonical shape produced by every `sources.py` adapter (live-source or freeform), consumed uniformly by `layout.py`, `materials.py`, and `scene_builder.py` regardless of origin (spec.md FR-011).

## TopologySnapshot

The complete, self-contained result of a single visualization request.

| Field | Type | Notes |
|---|---|---|
| `snapshot_id` | str | Unique per request; used to derive the output filename (FR-023) |
| `source_kind` | enum: `cml`, `gns3`, `containerlab`, `eve_ng`, `nautobot`, `netbox_infrahub`, `ip_fabric`, `forward_networks`, `freeform` | Origin of the data; drives which `sources.py` adapter produced it, never the rendering conventions used |
| `source_label` | str | Human-readable name of the specific source instance/lab/site (for display only) |
| `created_at` | datetime | Snapshot generation timestamp |
| `devices` | list[Device] | All devices in the topology |
| `links` | list[Link] | All links in the topology |
| `real_stencil_mode` | bool | Whether real-3D-model resolution was requested (Story 5) |
| `fallback_report` | list[FallbackNote] | Populated only when real-stencil mode is on and one or more devices fell back to procedural shapes (FR-021) |

## Device

| Field | Type | Notes |
|---|---|---|
| `hostname` | str | Required; primary label (FR-005) |
| `role` | enum: `router`, `switch`, `firewall`, `load_balancer`, `client`, `unclassified` | Drives shape/color (FR-002); `unclassified` is the explicit fallback per Edge Cases, never omitted |
| `state` | enum: `healthy`, `degraded`, `down`, `unknown` \| None | `unknown`/None both render as the neutral default (FR-017); `unknown` is used when the source explicitly reported "no data," None when the source never carries state at all |
| `interfaces` | list[Interface] | Structurally owned by this device (FR-003) |
| `metadata` | dict[str, str] | Any additional source-exposed descriptive fields (e.g., software version, description) surfaced in labels/panels per the Clarification session — MUST NOT contain credentials or full running-configuration content (FR-005a) |
| `device_asset` | DeviceAsset | Resolved visual representation (see below) |
| `position` | Vector3 (x, y, z) | Assigned by `layout.py`; always a complete, centered/scaled coordinate (FR-008, FR-009) |

## Interface

| Field | Type | Notes |
|---|---|---|
| `name` | str | Required; label (FR-005) |
| `parent_hostname` | str | The one Device this Interface structurally belongs to (FR-003) |
| `ip_address` | str \| None | Shown on the label by default when present (Clarification session) |
| `state` | enum: `healthy`, `degraded`, `down`, `unknown` \| None | Same semantics as Device.state |
| `metadata` | dict[str, str] | Same constraints as Device.metadata |
| `local_offset` | Vector3 (x, y, z) | Position relative to the parent Device's local origin (not world space) — this is what makes the interface move automatically when the device moves (FR-003) |

## Link

| Field | Type | Notes |
|---|---|---|
| `link_id` | str | Unique within the snapshot |
| `endpoint_a` | LinkEndpoint | First side |
| `endpoint_b` | LinkEndpoint | Second side |
| `state` | enum: `healthy`, `degraded`, `down`, `unknown` \| None | Same semantics as Device.state |
| `label` | str | Derived identifying label (endpoint hostnames and, when known, interface names — FR-005) |

### LinkEndpoint

| Field | Type | Notes |
|---|---|---|
| `hostname` | str | Always present |
| `interface_name` | str \| None | Present only when interface-level data was available from the source; when None, the renderer falls back to attaching this endpoint to the Device rather than an Interface (FR-004, Edge Cases) |

## DeviceAsset

The resolved visual representation for one Device, produced by `assets.py` (default procedural) or the real-stencil resolution chain (Story 5).

| Field | Type | Notes |
|---|---|---|
| `kind` | enum: `procedural`, `real_model` | `procedural` is always a safe, always-available value |
| `procedural_shape` | enum: `box`, `cylinder`, `extruded_icon` | Only meaningful when `kind == procedural`; selected by `Device.role` |
| `model_source` | enum: `cache`, `sketchfab`, `user_supplied` \| None | Only meaningful when `kind == real_model`; tracks provenance for the fallback report and future cache reuse |
| `model_license_slug` | str \| None | Only ever `"cc0"` when `model_source == sketchfab` — this field existing with any other value would itself indicate a policy violation (FR-019a) and must never occur in practice |
| `embedded_glb_base64` | str \| None | The actual model payload embedded into the generated HTML (FR-001, FR-019); None whenever `kind == procedural` |

## FallbackNote

| Field | Type | Notes |
|---|---|---|
| `hostname` | str | Which device fell back |
| `role` | str | The role that had no permitted model |
| `reason` | enum: `no_cc0_candidate_found`, `source_unreachable`, `gated_marketplace_verify_only_no_asset` | Surfaced to the engineer per FR-021 |

## Vector3

Shared value type (x, y, z floats) used for both layout positions and interface local offsets — ported from `ue5-network-viz/layout.py`'s existing `Vector3` (see research.md §4).

## State Transitions

None of these entities have a persisted lifecycle — a `TopologySnapshot` is fully assembled once per request and is immutable thereafter (FR-023: each request produces its own independent snapshot; nothing is mutated in place). "State" fields above describe a point-in-time operational status *value*, not a workflow state machine.

## Validation Rules (from Functional Requirements)

- Every `Interface.parent_hostname` MUST reference a `Device.hostname` present in the same `TopologySnapshot` (FR-003).
- A `Link` MUST reference two endpoints whose `hostname` is present in the snapshot; `interface_name`, when present, MUST reference an `Interface.name` that exists under that `LinkEndpoint.hostname`'s Device (FR-004).
- `Device.role` MUST default to `unclassified` rather than being left empty or omitted (Edge Cases).
- `DeviceAsset.embedded_glb_base64` MUST be populated whenever `kind == real_model`; a `real_model` DeviceAsset with no embedded payload is invalid (FR-001, FR-019).
- `DeviceAsset.model_license_slug` MUST equal `"cc0"` whenever `model_source == sketchfab` (FR-019a).
- `Device.metadata` and `Interface.metadata` MUST NOT include any key/value recognizable as a credential, secret, or full running-configuration blob (FR-005a) — enforced by `sources.py` adapters at assembly time, not by the renderer.
