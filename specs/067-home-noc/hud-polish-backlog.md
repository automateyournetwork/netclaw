# HUD polish backlog (mobile + operator chrome)

**Status**: Active backlog — pick up when returning to Visual HUD UX  
**Spec home**: `specs/067-home-noc/`  
**Code home**: `ui/netclaw-visual/`  
**Last updated**: 2026-07-24  

Capture of improvements identified while shipping Home tab layout fixes, panel collapse, floating terminal, and first-pass mobile layout. **Do not lose these** when context rotates to Docker/K3s/installer work.

---

## Already shipped (do not re-implement)

| Area | What landed | Commit / notes |
|------|-------------|----------------|
| Home KPI centering | Stop inheriting global `.label` transform (`home-kpi-label` / `home-kpi-value`) | `e9c3904` |
| Panel collapse | Left/right/footer slide off-screen; FILTERS / DETAIL / STATUS reopen; taller topbar z-index fix | `8933e55` |
| Floating terminal | Drag header, corner resize, collapse `_`/`+`, desktop geometry in `localStorage` | `8933e55` |
| Mobile layout v1 | `#app.mobile-layout` via `src/app-shell/mobile-layout.js`; bottom-sheet sidebars; bottom thumb chips; terminal bottom sheet; auto FOCUS quality + capped DPR; `visualViewport` resize; Home 2-col KPIs; safe-area insets | `e840909` |

**Key files**

- `ui/netclaw-visual/src/app-shell/mobile-layout.js`
- `ui/netclaw-visual/src/main.js` — `initChatWindow`, `onResize` / `viewportSize`, mobile wire in `wireUI`
- `ui/netclaw-visual/src/styles.css` — `#app.mobile-layout …` block
- `ui/netclaw-visual/src/styles/home.css` — mobile Home surface
- `ui/netclaw-visual/index.html` — `viewport-fit=cover`, chat resize handle

---

## Worth doing next (deferred from mobile pass)

Prioritized for **operator value / effort**. IDs `H###` are HUD-polish only (orthogonal to product Phases 3–7).

### P1 — High impact, small–medium effort

#### H001 — Landscape mode chrome
**Why**: Phones in landscape crush the tall topbar + bottom chips; graph and Home content get a thin strip.  
**Do**:
- Detect `orientation: landscape` + short height (or `max-height: 500px`)
- Compact topbar: hide long eyebrow, shrink brand, single-row COMMAND|HOME + metrics
- Raise bottom sheets / terminal max-height % when landscape
- Optional: auto-collapse terminal to header strip on landscape enter  
**Touch**: `mobile-layout.js` snapshot + CSS under `#app.mobile-layout.landscape` (or media query pair)  
**Accept**: On a phone landscape, COMMAND graph has ≥50% viewport height free of chrome; HOME Overview KPIs remain readable without horizontal scroll.

#### H002 — `prefers-reduced-motion`
**Why**: Scan-beam, GSAP focus tweens, and bloom-ish motion can be harsh / battery-heavy; a11y expectation.  
**Do**:
- On `matchMedia('(prefers-reduced-motion: reduce)')`:
  - Disable or freeze `.scan-beam` animation
  - Skip GSAP ornamental pulses; keep functional camera moves short or instant
  - Prefer quality FOCUS if user has not pinned quality
- Document in HUD README  
**Touch**: `styles.css`, `main.js` animate/GSAP sites, `mobile-layout.js` or small `a11y.js`  
**Accept**: With OS “reduce motion” on, no continuous full-screen scan animation; scene still navigable.

#### H003 — Touch long-press node detail
**Why**: Desktop uses hover tooltip + click; mobile has no reliable hover; mis-taps orbit the camera.  
**Do**:
- 400–500ms press on canvas hit → open right detail sheet (or bottom DETAIL) without requiring precise double-tap
- Cancel long-press if pointer moves beyond small threshold (orbit gesture)
- Haptic `navigator.vibrate(10)` when supported (optional, gated)  
**Touch**: `main.js` `onPointerMove` / `onClick` / new pointerdown timer on `renderer.domElement`  
**Accept**: On coarse pointer, long-press selects a node and opens DETAIL sheet; drag still orbits.

---

### P2 — Product polish

#### H004 — PWA shell (installable HUD)
**Why**: Operators want home-screen launch; better standalone mobile chrome.  
**Do**:
- `manifest.webmanifest` (name NetClaw Visual, theme `#07111f`, `display: standalone`)
- Icons (192 / 512) under `ui/netclaw-visual/public/`
- Link from `index.html`; optional minimal service worker that caches shell + last `/api/graph` snapshot only (no secrets)
- HTTPS note in quickstart (required for install)  
**Accept**: “Add to Home Screen” works on iOS Safari + Chromium; standalone launch shows COMMAND|HOME without browser URL bar clutter.

#### H005 — Offline / degraded shell
**Why**: Gateway or graph API blips leave a dead loading screen; mobile networks are flaky.  
**Do**:
- Cache last good graph JSON in `sessionStorage` / Cache API
- Boot with “stale graph” banner + last-updated time when `/api/graph` fails
- Keep chat UI mounted; show gateway offline (already partially present)  
**Accept**: Kill home-api/graph for one request → HUD still shows last topology with clear STALE badge.

#### H006 — Mobile smoke checklist
**Why**: No automated mobile CI; regressions will return.  
**Do**: Add checklist section to `quickstart.md` or `ui/netclaw-visual/README.md`:
- [ ] Phone width ≤720: FILTERS + DETAIL chips visible; left filters not permanently gone
- [ ] Collapse / reopen sidebars
- [ ] Terminal drag, resize, collapse
- [ ] HOME KPIs 2-col, tabs tappable (44px)
- [ ] iOS keyboard open does not permanently mis-size canvas
- [ ] Landscape (H001 once done)  
**Accept**: Manual run takes &lt;10 minutes; checklist linked from 067 tasks.

---

### P3 — Nice-to-have

#### H007 — Knowledge panel mobile pass
**Why**: RAG panel is fixed large width; can cover terminal on phones.  
**Do**: Same bottom-sheet pattern as sidebars; collapse by default on `mobile-layout`.  
**Touch**: `panels/KnowledgePanel.js` + CSS

#### H008 — Dynamic topbar height measurement
**Why**: Hard-coded `top: 168px` / Home root offsets break if brand/tabs change again.  
**Do**: JS `ResizeObserver` on `.topbar` → set `--topbar-height` CSS variable; position sidebars/Home from var.  
**Touch**: `mobile-layout.js` or `main.js`, `styles.css`, `home.css`

#### H009 — Quality mode persistence
**Why**: Auto FOCUS on mobile is good; desktop users who pick BROADCAST lose it on reload.  
**Do**: Persist `qualityMode` + `qualityUserPinned` in `localStorage`.  
**Touch**: `main.js` `setQualityMode` / boot

#### H010 — One-handed terminal peek
**Why**: Expanded sheet covers graph during long tool output.  
**Do**: Half-height snap points (collapsed / peek ~30% / expanded ~55%) on mobile swipe of chat header.  
**Touch**: `initChatWindow` + CSS

---

## Suggested pickup order

When next opening a **HUD UX** session (not blocked on deploy):

1. **H001** landscape + **H002** reduced motion (same CSS/media pass)  
2. **H003** long-press select  
3. **H006** smoke checklist (lock the above)  
4. **H004** / **H005** if installable / field use matters  
5. **H007–H010** as time allows  

Product path (Docker → K3s → installer → triage) remains **Phase 3+** in `tasks.md` and should stay the default fork-main sequence unless operator asks for HUD polish.

---

## Out of scope for this backlog

- Multi-vendor adapters (Phase 7)  
- guardian-claw ensure / iN2N risk install (Phase 5)  
- Full redesign of Three.js scene graph  
- Replacing OrbitControls with a custom mobile-only camera  

---

## How to resume

```text
1. Read this file + ui/netclaw-visual/src/app-shell/mobile-layout.js
2. Pick next open H### checkbox in tasks.md “Phase H”
3. Implement → rebuild dist → restart netclaw-hud → tick task
4. Update “Already shipped” table here when something lands
```
