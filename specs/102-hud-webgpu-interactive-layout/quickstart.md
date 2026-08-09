# Phase 1 Quickstart: Verifying WebGPU + Interactive Layout

**Feature**: 102-hud-webgpu-interactive-layout
**Date**: 2026-08-07
**Input**: [spec.md](./spec.md) Success Criteria · [contracts/layout-api.md](./contracts/layout-api.md)

Follows Constitution VIII — observe → baseline → apply → verify. Two properties make this feature
harder to verify than 101, and both shape everything below:

1. **The renderer port has no live A/B** (FR-036 forbids keeping WebGL). Spec 101's committed
   baselines are the reference implementation now.
2. **Most failures here are visual or interactive**, and the render layer has no automated
   coverage. Pure logic is tested; drawing and pointer behaviour are screenshotted and clicked.

> **Do not read an exit code through a pipe.** `cmd | tail` reports `tail`'s status. Use
> `cmd >/dev/null 2>&1; echo $?`.

---

## 0. Baseline — reuse 101's, do not invent a new one

101 committed both the numbers and the tool. Use them, so the comparison is apples to apples.

```bash
cd /home/johncapobianco/netclaw
ls specs/101-hud-threejs-modernization/evidence/          # probe + JSON baselines
export CHROME_BIN=~/.cache/chrome-devtools-mcp/browsers/chrome/*/chrome-linux64/chrome
OUT_DIR=$PWD/evidence-102 LABEL=pre-102 SETTLE_MS=15000 SAMPLE_FRAMES=400 \
  node specs/101-hud-threejs-modernization/evidence/hud-probe.mjs
```

Reference figures from 101, same host: median **~750 ms**, 42 labels, zero page errors, one
pre-existing `/favicon.ico` 404.

**That ~750 ms is SwiftShader software rasterization (~1.4 fps), not real hardware.** Relative
comparison on this host is valid; nothing about perceived performance is. The operator's own
numbers decide FR-021/SC-005 in practice.

---

## 1. Layout foundations (pure — no renderer involved)

```bash
cd ui/netclaw-visual && node --test 'src/**/*.test.js' 2>&1 | tail -5
```

- [ ] **FR-039 determinism**: solve force-directed twice on identical input → deep-equal results.
      This single assertion *is* FR-039.
- [ ] **FR-040 bounded**: the solver returns; there is no tick loop left running.
- [ ] **FR-041 pinning**: a pinned node is at its pinned position after the solve.
- [ ] **FR-049 scoping**: a node moved in `freeform` is unmoved in `orgchart`.
- [ ] **FR-014 non-destructive**: switch preset and back → positions identical.
- [ ] **FR-016 tolerance**: a saved map with one unknown id and one missing id restores without
      error; unknown ignored, missing computed.
- [ ] **FR-033 validation**: `NaN`, `Infinity`, 10⁶ coordinates, 501 entries, unknown top-level
      keys, and a bad preset name are each rejected.
- [ ] **FR-047 clamp**: a camera zoom outside 072's `MIN_ZOOM`/`MAX_ZOOM` is clamped, not honoured.

---

## 2. Drag (US1)

- [ ] Drag a member → it moves; links follow (FR-005).
- [ ] **Wait out a full 30-second poll** → it does not snap back. *This is the most likely
      regression in the whole feature* — `updateOrgChart` repaints on every poll (FR-002).
- [ ] Enroll or simulate a new member → the moved node does not shift (FR-002).
- [ ] Drag from empty space → camera orbits as before (FR-043).
- [ ] Click without moving → selects, does not reposition (FR-044).
- [ ] Drag one node onto another → nothing snaps or merges (FR-007).
- [ ] Select a moved node → 101's ring appears at its **current** position (FR-006).

**FR-045, the camera lock-up — test all four termination paths.** Missing any one leaves the
camera permanently dead with no visible cause and no recovery but a reload:

- [ ] normal release → camera orbits again
- [ ] release outside the canvas → camera orbits again
- [ ] `pointercancel` (touch interruption / dev-tools dispatch) → camera orbits again
- [ ] an exception thrown mid-drag → camera orbits again

---

## 3. Presets (US2)

For **each** of the five — org chart, ring, grid, force, free-form:

- [ ] Band membership, health treatments, peer states and link topology unchanged; only positions
      differ (FR-011).
- [ ] **Screenshot it.** FR-013/SC-007 apply *per preset*. Spec 101 shipped a label collision that
      only a screenshot caught, and Grid and Ring both change inter-node spacing wholesale.
- [ ] Force-directed selected twice → identical arrangement (FR-039).
- [ ] Force-directed settles and **stops** — no ongoing motion, no continuous frame cost (FR-040).
- [ ] Org chart preset → byte-identical to 101's committed baseline screenshot (FR-010, SC-002).

---

## 4. Save / restore (US3)

```bash
curl -s localhost:3001/api/layout | python3 -m json.tool | head
```

- [ ] First run → `200` with `empty: true`, **not** a 404.
- [ ] Save, reload → positions **and** camera restored (FR-018).
- [ ] Add a member, reload → it appears at its computed position, not hidden (FR-016).
- [ ] Remove a member, reload → the stale entry is ignored silently (FR-016).
- [ ] Corrupt the file by hand → `200` with a `warning`, HUD falls back to computed and says so
      (FR-019). Not a 500 — that would be indistinguishable from the server being down.

Rejections (FR-033) — each must be `400` with a **specific** reason and write nothing:

```bash
for body in '{"version":1,"positions":{"ring":{"a":{"x":null,"y":0,"z":0}}}}' \
            '{"version":1,"positions":{"nosuchpreset":{}}}' \
            '{"version":999}' '{"version":1,"unexpectedKey":true}'; do
  curl -s -o /dev/null -w "%{http_code} " -X PUT localhost:3001/api/layout \
    -H 'Content-Type: application/json' -d "$body"
done; echo
```

- [ ] All four return `400`, and the file on disk is unchanged after each.

**SC-008 — assert on what was actually written, not on the serializer:**

```bash
grep -ciE 'channel_state|inventory|pinned_key|token|secret|endpoint_host' <layout-file>
```

- [ ] Returns `0`. Node identifiers and numbers only.

---

## 5. Unsaved-change handling (FR-051/052/053)

- [ ] Drag something → unsaved state is **visible on screen** (FR-052). This is the primary signal.
- [ ] Attempt to leave → browser warns (FR-051).
- [ ] With nothing changed → **no** warning. A warning that cries wolf trains you to dismiss the
      one that matters.
- [ ] Save succeeds → indicator clears (FR-053).
- [ ] Save fails (stop the server, then save) → arrangement retained in memory **and still shown
      as unsaved** (FR-035, FR-053). A failed write must never present as a successful one.

> The unload dialog is a backstop, not a guarantee — browsers suppress it on tab discard, crash,
> OS shutdown and without prior interaction. That is why FR-052's on-screen indicator is the
> primary signal and is tested first.

---

## 6. Renderer migration (US4)

- [ ] `grep -rE "EffectComposer|ShaderMaterial" src/` → **no matches** (FR-036). One path only.
- [ ] HUD loads with zero page errors; the pre-existing `/favicon.ico` 404 may remain.
- [ ] Screenshot vs 101's baseline: bands, labels, links, six peer states, selection ring, link
      flow all intact (FR-023, SC-006).
- [ ] `peer-treatments.test.js` still passes **unmodified** — the peer encoding is data, not
      rendering, and must survive the port untouched.
- [ ] Bloom, RGB-shift, SMAA, afterimage, film present; vignette hand-written and present.
- [ ] **GlitchPass**: confirm the drop was signed off, or that it was reimplemented (FR-021).
- [ ] Frame time within 110% of the §0 baseline (SC-005).

---

## 7. Showcase (US5)

- [ ] On WebGPU: a light per live claw, no frame collapse (FR-024).
- [ ] On WebGPU: compute particle flow on **live links only** (FR-025).
- [ ] Force the WebGL 2 backend → showcase features **absent, nothing broken or empty** (SC-004).
- [ ] Simulate a device-lost event → scene degrades rather than blanking (FR-026).

---

## 8. Final gates

```bash
cd ui/netclaw-visual && node --test 'src/**/*.test.js' >/dev/null 2>&1; echo "hud tests=$?"
cd /home/johncapobianco/netclaw
python3 scripts/reconcile-mcp.py >/dev/null 2>&1; echo "reconcile=$?"
/usr/bin/python3 -m pytest tests/n2n/ -q 2>&1 | tail -2      # must stay green — untouched
git diff --stat -- ui/netclaw-visual/server.js               # ONLY the layout route
```

- [ ] All exit 0; `tests/n2n/` unaffected.
- [ ] `server.js` diff shows **only** `GET`/`PUT /api/layout` (FR-032).
- [ ] `ui/netclaw-visual/README.md` renderer table updated — 101's version of it becomes wrong the
      moment `WebGPURenderer` lands.
- [ ] Branch is still `102-hud-webgpu-interactive-layout` before committing.
