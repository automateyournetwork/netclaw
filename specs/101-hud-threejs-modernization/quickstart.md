# Phase 1 Quickstart: Verifying HUD three.js Modernization

**Feature**: 101-hud-threejs-modernization
**Date**: 2026-08-06
**Input**: [spec.md](./spec.md) Success Criteria · [contracts/visual-contract.md](./contracts/visual-contract.md)

Follows Constitution VIII — **observe → baseline → apply → verify**. The unusual thing about this
feature is that its unit tests **cannot see rendering**: the 7 modules importing three.js have
zero coverage, and every existing test lives on feature 072's pure side (research R2). So visual
verification is not a nicety here, it is the only evidence for half the requirements.

> **Do not read an exit code through a pipe.** `cmd | tail` reports `tail`'s status. Use
> `cmd >/dev/null 2>&1; echo $?` (CLAUDE.md — this mistake misdiagnosed spec 075).

---

## 0. The two performance baselines (FR-044) — do this first, it cannot be recreated

FR-047 gates the upgrade's own frame-time delta, and SC-005 measures US2/US3/US4 against the
**post-bump** baseline. Capture the pre-bump one before touching anything.

```bash
cd ui/netclaw-visual
node -e "console.log(JSON.parse(require('fs').readFileSync('node_modules/three/package.json')).version)"
# expect 0.170.0
```

Record for each baseline: **machine, browser + version, scene composition (node counts by band),
quality mode, and median frame time over a sustained window** — not an instantaneous reading.

Capture frame time in the browser with the HUD open and idle (no camera movement):

```js
// paste in DevTools console; reports median frame time over ~10s
(() => { const t=[]; let p=performance.now();
  const f=n=>{t.push(n-p);p=n;if(t.length<600)requestAnimationFrame(f);
    else{const s=t.slice(60).sort((a,b)=>a-b);
      console.log('median frame ms:', s[s.length>>1].toFixed(2), 'n=', s.length);}};
  requestAnimationFrame(f); })()
```

Also record the current scene composition, so "same scene" is checkable rather than assumed:

```bash
curl -s localhost:3001/api/n2n | python3 -c "
import json,sys; d=json.load(sys.stdin)
print('peers:', len(d.get('peers',[])), '| members:', len(d.get('members',[])),
      '| live members:', sum(1 for m in d.get('members',[]) if m.get('live')),
      '| edge nodes:', len(d.get('edgeNodes',[])))"
```

**Put all of it in the PR.** An unreproducible baseline makes FR-021, FR-047 and SC-005
unverifiable, and SC-005 says a run that cannot produce the numbers *fails* rather than passing
by default.

---

## 1. Sequencing — why the bump goes first

`netclaw-hud.service` runs Vite from the working tree, so a dependency change is immediately
visible to anyone watching the HUD (FR-028). Two options:

- **Isolated probe** (research R2's technique) — copy `src/`, `index.html`, `canvas.html`,
  `vite.config.js` to a scratch dir with its own `node_modules`. Proves the build; does not
  disturb the running service. Note the test fixtures resolve at `<project>/../../specs/...`, so
  that path must be mirrored or symlinked.
- **In place**, then `systemctl --user restart netclaw-hud.service` — an explicit, confirmed step.

Land US5 **alone** and re-baseline before starting US1–US4. Priority orders value; this orders
measurement (plan.md).

---

## 2. US5 — the upgrade (SC-004, SC-007, FR-047)

```bash
cd ui/netclaw-visual
npm install three@0.185.1
npm run build >/dev/null 2>&1; echo "build exit=$?"     # expect 0
npm test    >/dev/null 2>&1; echo "test exit=$?"        # expect 0
```

- [ ] Build exits 0 with **no source change** (already verified in an isolated probe — research R2).
- [ ] `npm test` exits 0. **Remember this proves nothing about rendering** — no test imports three.js.
- [ ] Bundle within ~10% of 753 kB (SC-007). Expected ~799 kB, +6.1%.
- [ ] Post-bump baseline captured (§0) and the delta from pre-bump is **≤10%** (FR-047).
- [ ] `ui/netclaw-visual/README.md` and `THIRD_PARTY_NOTICES.md` version references updated (FR-026).
- [ ] `python3 scripts/reconcile-mcp.py >/dev/null 2>&1; echo $?` → `0` (FR-027).

Then the visual check that the unit tests cannot do (FR-034/035), via `chrome-devtools-mcp`:

- [ ] HUD loads at `localhost:3000` with **zero console errors** and no three.js deprecation warnings.
- [ ] Screenshot: org-chart bands, labels, links, camera framing and all seven post-processing
      passes visually intact (FR-025).

---

## 3. US1 — peer inspector (SC-001, FR-001..006, FR-045)

Click each of the 7 peers and confirm the panel shows **that** peer:

- [ ] Nate → Nate's identity, state, channel state, inventory freshness. Not the generic overview.
- [ ] Byrn → its own detail, with staleness stated in operator terms, not a bare timestamp (FR-004).
- [ ] Both Hermes rows (`as65007` severed, `as65008` federated) → **distinguishable**, because
      `identity` is shown and not only the shared label.
- [ ] AB and Carapace (`inventory_received_at: null`) → "never seen", not "0s ago" (FR-004).
- [ ] The severed Hermes is not presented as reachable.
- [ ] Keyboard-activate a peer → same panel (FR-005). Both paths were broken.
- [ ] A peer with in-flight tasks lists them; a peer without shows an explicit "none", not a blank.
- [ ] **No row renders `undefined`** (P2). This is what routing peers through `peer-core` would have caused.

FR-006, the guard:

- [ ] Call `setDetail` with an unknown kind in dev → fails loudly. It MUST NOT reach the default
      overview branch. That silent fallthrough is the original bug.

FR-045, selected peer vanishes:

```bash
# with a peer selected in the HUD, retire its endpoint so it changes underneath you
#   (spec 100's tool — reversible, and the peer stays federated)
curl -s -X POST localhost:8179/n2n/peers/forget-endpoint \
  -H 'Content-Type: application/json' -d '{"peer":"<identity>","actor":"spec101-verify"}'
```

- [ ] Panel retains last known detail **with a not-in-feed banner**; scene drops the selected treatment.
- [ ] Panel is neither blanked nor left reading as current.

---

## 4. US3 — liveness encoding (SC-003, FR-012..017)

The defect being fixed: five of seven peers currently render identically to healthy Nate, because
`colorForStructural` never reads `stale` and `channel_state: "unknown"` hits the healthy default
(data-model §1).

- [ ] Screenshot containing a LIVE, a STALE and a SEVERED peer → **three mutually distinct**
      channel combinations per visual-contract §3 (SC-003).
- [ ] Byrn and Nicholas (`unknown` + `stale`) no longer look like Nate.
- [ ] AB/Carapace read as **never seen**, and are **not** in the alarm hue family (R3, FR-016/017).
- [ ] Greyscale screenshot → all six peer states still separable (FR-014).
- [ ] `prefers-reduced-motion` → encoding intact with motion suppressed (channel 3 is redundant).
- [ ] Members unchanged: `HOT`/`WARM`/`COLD`/`FAULT` exactly as before (FR-013).
- [ ] `npm test` covers the pairwise ≥18 luminance rule as a permanent test, not a screenshot.

Empty and failure states:

- [ ] A **successful** poll with zero peers → feature 072's empty state, not a failure indicator.

---

## 5. US2 — selection (SC-002, FR-007..011)

- [ ] Screenshot with the panel hidden → the selected node carries every declared channel-5
      treatment and is distinct from an unselected node of the same type (SC-002).
- [ ] Select a **STALE** peer and a **COLD** member → selection legible on dim nodes, and the node
      does **not** brighten toward the healthy treatment (the FR-007 defect).
- [ ] Legible with bloom at configured strength.
- [ ] Legible at both extremes of the camera's zoom range (FR-011).
- [ ] Deselect → prior appearance fully restored, no residue (FR-008).
- [ ] Exactly one node reads as selected (FR-009).
- [ ] `prefers-reduced-motion` → static treatment (FR-010).

---

## 6. US4 — link flow (FR-018..021)

- [ ] Nate's link (LIVE) shows directional flow.
- [ ] Byrn's link (STALE) shows none. Severed shows none.
- [ ] `prefers-reduced-motion` → live/not-live still distinguishable without continuous animation.
- [ ] Median frame time within **110%** of the post-bump baseline (FR-021, SC-005), measured with
      §0's snippet on the same machine, browser, scene and quality mode.

---

## 7. Preservation (FR-037..040)

- [ ] Chat interface untouched.
- [ ] Right-hand information bar untouched.
- [ ] No sibling node moves on select or expand (FR-038, feature 072 layout stability).
- [ ] `git diff --stat` shows **no change** to `server.js` (FR-039).
- [ ] Keyboard navigation and the a11y tree still work; `aria-expanded` stays in step with the
      pointer path.

---

## 8. Final gates

```bash
cd ui/netclaw-visual && npm test >/dev/null 2>&1; echo "hud tests exit=$?"
cd /home/johncapobianco/netclaw
python3 scripts/reconcile-mcp.py >/dev/null 2>&1; echo "reconcile exit=$?"
/usr/bin/python3 -m pytest tests/n2n/ -q 2>&1 | tail -2      # must stay green — untouched
git diff --stat -- ui/netclaw-visual/server.js               # must be empty
```

- [ ] All exit 0; `tests/n2n/` unaffected.
- [ ] Every "verified" claim backed by a build result, screenshot, or test — never inspection alone (SC-009).
- [ ] Branch is still `101-hud-threejs-modernization` before committing — other agents switch
      branches in this shared checkout.
