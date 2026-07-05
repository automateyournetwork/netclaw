# Quickstart: Three.js Browser Network Topology Visualization Development

**Feature**: 046-threejs-network-viz
**Date**: 2026-07-05

## Prerequisites

Unlike the UE5/Blender skills, this feature needs no desktop application, GPU, or cross-OS bridge — that's the entire point. What it does need:

1. **A modern desktop browser** (Chrome/Firefox/Edge) on the machine where the generated HTML file will be opened.
2. **At least one already-working topology-source integration** to exercise Story 1/2 with real data — any one of: a running CML lab, `gns3-mcp-server`, `clab-mcp-server` (containerlab), `eve-ng-mcp-server`, `nautobot-mcp-v2`, `netbox-mcp-server`/`infrahub-mcp`, an IP Fabric integration, or `forward-mcp`. Freeform input (Story 3) needs none of these.
3. **The vendored `sketchfab-mcp-server`** — only required for Story 5 (real-stencil mode). It was cloned and built this session at `mcp-servers/sketchfab-mcp-server/` (`npm install && npm run build`) and registered as `sketchfab-mcp` in `config/openclaw.json`.
4. **Vendored Three.js r147 assets** — `build/three.js`, `examples/js/controls/OrbitControls.js`, `examples/js/loaders/GLTFLoader.js`, fetched once from `unpkg.com/three@0.147.0/...` and committed under `workspace/skills/threejs-network-viz/vendor/three/` (research.md §1–2). This is a one-time setup task in Phase 1 of the plan, not something to re-fetch per run.

### Environment variables

New for this feature (already added to `.env.example`; only needed for Story 5):

```bash
SKETCHFAB_API_KEY=your_sketchfab_api_token   # https://sketchfab.com/settings/password -> API Tokens
SKETCHFAB_USERNAME=your_sketchfab_username   # for reference/attribution only, not required by the API
```

No environment variables are needed for procedural-shape mode (the default) or for any already-integrated topology source — those reuse each source's own existing credentials.

## Development Loop

1. Build the core renderer against one live source first (Phase 1 of the plan): ask for a visualization of a small, known topology (e.g., a 3-4 device CML or GNS3 lab) and confirm a single `.html` file opens automatically in the browser showing labeled, colored, centered devices with interfaces attached as true children and links drawn between the correct interfaces.
2. Verify the anti-regression checks explicitly called out in spec.md's lessons-learned framing: move the browser camera around a device with several interfaces and confirm none of them "lag behind" or detach; check a topology whose source coordinates are large/off-origin renders centered anyway.
3. Add a second live source adapter and freeform input (Phase 2); confirm both produce visually consistent scenes to the first source.
4. Enable real-stencil mode (Phase 3) on a topology with mixed device roles; confirm roles with a resolvable CC0 Sketchfab model render as real geometry, everything else falls back cleanly to procedural shapes, and the reported fallback list is accurate. Open the resulting HTML file on a machine with no network access at all and confirm it still renders fully (proving the embedding, not linking, actually worked).
5. Feed a topology with mixed up/degraded/down devices and links (Phase 4) and confirm color state is visually distinguishable and explained by the legend.

## Common Pitfalls (carried over from 024/044/045 — see spec.md's own framing and research.md §4)

- Any new device/link scale or spacing constant introduced ad hoc (instead of routed through `layout.py`'s ported, already-fixed centering logic) risks reintroducing the exact class of scale/overlap bug fixed once in `ue5-network-viz` (commit `5281cac`).
- Setting only one of position/rotation/scale on a `THREE.Object3D` instead of the complete transform will reintroduce the "partial update silently resets the rest" bug from the same lesson — always set the full transform, matching FR-009 and the scene payload contract's explicit rule.
- Computing and hardcoding an interface's world-space position instead of adding it as a true child (`parentGroup.add(...)`) will look correct in a static screenshot but silently break the instant a device is repositioned — this was the core structural mistake being avoided per FR-003.
- Treating Sketchfab's `downloadable: true` search filter as a license guarantee: it is not. Every candidate MUST be verified individually via `sketchfab-model-details`'s license field before download/embed (FR-019a) — skipping this check would violate the CC0-only policy even though it would "work" in the sense of successfully downloading a model.
- Referencing a downloaded `.glb` as a separate linked file instead of base64-embedding it defeats the entire point of Story 5's single-file requirement — confirmed by the "open with no network access" test in step 4 above.
