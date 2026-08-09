# Phase 1 Data Model: HUD WebGPU Showcase + Interactive Layout

**Feature**: 102-hud-webgpu-interactive-layout
**Date**: 2026-08-07
**Input**: [spec.md](./spec.md) · [research.md](./research.md) · [plan.md](./plan.md)

**One new persisted entity** — the saved layout file. Everything else is in-memory client state.
`/api/n2n` and `/api/graph` are unchanged (FR-032); nothing here is derived from or written back
to federation state.

---

## 1. `PresetId` — the closed set

```
'orgchart' | 'ring' | 'grid' | 'force' | 'freeform'
```

Exactly five (FR-038). `orgchart` is the default and MUST reproduce `computeLayout()` verbatim
(FR-010) — it is not a preset *implementation*, it is the absence of one.

`freeform` is the only preset with **no computed baseline**: nodes start where the org chart put
them and every subsequent position is the operator's. That makes it the one preset where an empty
position map is meaningful rather than a bug.

---

## 2. `LayoutStore` — per-preset position memory

`src/orgchart/layout-store.js`. Pure, no clock, no DOM. Holds the whole arrangeable state.

```js
{
  activePreset: PresetId,
  positions: { [PresetId]: { [nodeId]: {x, y, z} } },   // sparse — only moved nodes
  pinned:    { [PresetId]: Set<nodeId> },               // FR-041, force preset only
                                                       // `pinned` is the field name; prose may
                                                       // say "pin"/"pinning" for the action
  camera:    { position: {x,y,z}, target: {x,y,z}, zoom: number } | null,
  dirty:     boolean,
}
```

### Rules

| Rule | Source |
|---|---|
`positions` is **sparse** — a node absent from the map uses its computed/preset position | FR-050 |
Positions are keyed **per preset**; a node dragged in `freeform` MUST NOT move in `orgchart` | FR-049 |
`pinned` is per preset too; pinning under `force` MUST NOT leak elsewhere | FR-041, FR-049 |
Switching preset changes `activePreset` only — **never clears any position map** | FR-014 |
Any position change, preset switch, or camera change sets `dirty` | FR-051 |
A successful save clears `dirty`; a failed save MUST NOT | FR-053 |

**Why sparse and not a full snapshot**: a full map would freeze every node at whatever the layout
computed on the day it was saved, so a member enrolling later would land on top of a stale
neighbour and a member leaving would leave a hole. Sparse means "the operator moved these; compute
the rest", which is what makes FR-016's tolerance rules fall out for free rather than needing
reconciliation logic.

---

## 3. `SavedLayout` — the persisted file

The **only** persistent entity. Written by `server.js` to a fixed path (FR-034).

```json
{
  "version": 1,
  "savedAt": "2026-08-07T18:30:00Z",
  "activePreset": "ring",
  "positions": { "ring": { "as65006-6.6.6.6": {"x": 12.5, "y": 40, "z": 0} } },
  "pinned":    { "force": ["johns-risk/pyats"] },
  "camera":    { "position": {...}, "target": {...}, "zoom": 1.4 }
}
```

| Field | Purpose |
|---|---|
`version` | Schema generation. A file with an unknown version is ignored, not migrated (FR-019). |
`savedAt` | Operator-facing only. Never used for logic — a clock-dependent decision here would be untestable. |
`activePreset` | Which preset was active at save. |
`positions` | Per-preset sparse maps (§2). |
`pinned` | Per-preset pinned node ids. |
`camera` | Pose (FR-018), clamped on restore (FR-047). |

### What it MUST NOT contain (FR-018, SC-008)

No peer state, no member state, no inventory, no channel state, no tokens, no credentials, no
endpoint addresses. **Node identifiers and numbers only.** SC-008 is verified by inspecting what is
actually written, not by reading the serializer — a test that asserts on the emitted payload.

Node identifiers are already non-secret: they are AS numbers and router IDs the HUD renders as
visible labels.

---

## 4. `LayoutPayloadValidation` — the write gate

`src/orgchart/layout-payload.js`. Pure, and deliberately shared between client and server so one
implementation defines the contract.

| Check | Bound | Why |
|---|---|---|
Top-level shape | object with known keys only | Unknown keys rejected, not ignored — silent acceptance of junk is how a schema rots |
`version` | integer, must equal a supported value | FR-019 |
Preset keys | must be one of the five `PresetId` values | FR-038 |
Node id | string, length ≤ 128, no path separators | FR-034 — ids are used only as map keys, never as path components, and this makes that structural |
Coordinates | finite numbers, `abs(v) ≤ 10000` | FR-033. `NaN`/`Infinity` propagate into three.js as invisible geometry corruption rather than an error |
Entry count | ≤ 500 nodes per preset | FR-033. Scene is ~40; 500 is generous and still bounded |
Total size | ≤ 256 KB | FR-033 — the global `express.json({limit:'4mb'})` is far too permissive for this route (research R5) |
`camera.zoom` | finite, clamped to 072's `MIN_ZOOM`/`MAX_ZOOM` | FR-047 |

**Rejection is a 400 with a reason, never a partial write.** A payload that fails any check is
written nowhere — a half-applied layout is worse than a rejected one.

---

## 5. `DragSession` — transient

Lives only between `pointerdown` and termination. Never persisted.

```js
{ nodeId, pointerId, startScreen: {x,y}, startWorld: Vector3, moved: boolean }
```

`moved` becomes true once movement exceeds the FR-044 threshold, and it is what decides
**select vs drag** on release.

**Termination is the dangerous part.** The session MUST be torn down and `controls.enabled`
restored on `pointerup`, `pointercancel`, `lostpointercapture`, *and* on an exception during the
move handler (research R6). Wiring only `pointerup` leaves the camera permanently dead after any
abnormal end, with no visible cause and no recovery but a reload — the worst failure available in
this feature, because the operator cannot even tell what broke.

---

## 6. `ForceLayoutInput` / `ForceLayoutResult`

`src/orgchart/force-layout.js`. Pure, deterministic, bounded (FR-039/040).

**Input**: node ids + kinds, link pairs, pinned ids, iteration count.
**Output**: `{ [nodeId]: {x, y, z} }` — a plain position map, identical in shape to every other
preset's output. The solver never touches three.js and never runs in the render loop.

| Property | Mechanism |
|---|---|
Deterministic (FR-039) | Initial positions seeded from a hash of the node's stable identity string. **No `Math.random()`, no clock.** |
Bounded (FR-040) | Fixed iteration count, not an energy threshold — a threshold is data-dependent and may not converge, whereas a count is bounded by construction |
Stops (FR-040) | Runs to completion once and returns; there is no tick loop to leave running |
Respects pins (FR-041) | Pinned nodes are held fixed and act as attractors for the rest |

**Determinism is testable precisely because the solver is pure**: run it twice on the same input
and assert deep equality. That test is the whole of FR-039.

---

## 7. State transitions

```
                    drag (FR-043/044)          preset switch (FR-014)
   computed  ──────────────────────────►  arranged  ◄──────────────────►  arranged
   position                                (dirty)      positions kept       (other preset)
                                              │          per preset
                                              │
                              explicit save   │  (FR-015 — never automatic)
                                              ▼
                                    validate (FR-033) ──► reject 400, nothing written
                                              │             dirty STAYS set (FR-053)
                                              ▼
                                    write file (FR-034) ──► dirty cleared
                                              │
                     reload ──► read ──► clamp camera (FR-047) ──► apply sparse positions
                                              │                    unknown ids ignored (FR-016)
                                              ▼                    missing ids computed
                                    corrupt/unknown version ──► fall back to computed,
                                                                 say so (FR-019)
```

---

## 8. Validation summary

| Rule | Requirement |
|---|---|
Positions scoped per preset, never global | FR-049 |
Preset switching never destroys positions | FR-014 |
Sparse maps — absent means computed | FR-050, FR-016 |
Nodes added since save get computed positions; removed ids ignored silently | FR-016 |
Saved data is identifiers and numbers only | FR-018, SC-008 |
Coordinates finite and bounded | FR-033 |
Camera clamped to 072's existing constraints | FR-047 |
Empty/nonsense camera falls back to framing the chart | FR-048 |
Corrupt or unknown-version file falls back to computed, visibly | FR-019 |
Failed save leaves `dirty` set | FR-053, FR-035 |
Force solver deterministic and bounded | FR-039, FR-040 |
