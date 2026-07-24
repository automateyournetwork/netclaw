# HUD polish backlog (mobile + operator chrome)

**Status**: Active backlog — pick up when returning to Visual HUD UX  
**Spec home**: `specs/067-home-noc/`  
**Code home**: `ui/netclaw-visual/`  
**Last updated**: 2026-07-24 (H001–H003 + H006 shipped)

Capture of improvements identified while shipping Home tab layout fixes, panel collapse, floating terminal, and mobile layout. **Do not lose these** when context rotates to Docker/K3s/installer work.

---

## Already shipped (do not re-implement)

| Area | What landed | Commit / notes |
|------|-------------|----------------|
| Home KPI centering | Stop inheriting global `.label` transform (`home-kpi-label` / `home-kpi-value`) | `e9c3904` |
| Panel collapse | Left/right/footer slide off-screen; FILTERS / DETAIL / STATUS reopen; taller topbar z-index fix | `8933e55` |
| Floating terminal | Drag header, corner resize, collapse `_`/`+`, desktop geometry in `localStorage` | `8933e55` |
| Mobile layout v1 | `#app.mobile-layout` via `src/app-shell/mobile-layout.js`; bottom-sheet sidebars; bottom thumb chips; terminal bottom sheet; auto FOCUS quality + capped DPR; `visualViewport` resize; Home 2-col KPIs; safe-area insets | `e840909` |
| H001 Landscape | `#app.landscape-layout` on short landscape; compact topbar (hide eyebrow); shorter terminal sheet; auto-collapse chat on landscape enter; FOV bump | this session |
| H002 Reduced motion | `#app.reduced-motion`; freeze `.scan-beam`; GSAP `timeScale(40)`; skip cinematic burst; auto FOCUS | this session |
| H003 Long-press | Canvas long-press (~480ms) selects node, opens DETAIL sheet, optional `vibrate`; cancels on orbit drag | this session |
| H006 Smoke checklist | HUD README mobile/landscape checklist | this session |

**Key files**

- `ui/netclaw-visual/src/app-shell/mobile-layout.js`
- `ui/netclaw-visual/src/main.js` — `initChatWindow`, `onResize` / `viewportSize`, mobile wire in `wireUI`
- `ui/netclaw-visual/src/styles.css` — `#app.mobile-layout …` block
- `ui/netclaw-visual/src/styles/home.css` — mobile Home surface
- `ui/netclaw-visual/index.html` — `viewport-fit=cover`, chat resize handle

---

## Worth doing next (deferred from mobile pass)

Prioritized for **operator value / effort**. IDs `H###` are HUD-polish only (orthogonal to product Phases 3–7).

### P1 — Shipped this session (kept for history)

- **H001** Landscape mode chrome — done  
- **H002** `prefers-reduced-motion` — done  
- **H003** Touch long-press node detail — done  
- **H006** Mobile smoke checklist — done  

---

### P2 — Product polish (next HUD session)

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

#### H006 — Mobile smoke checklist — **shipped** (see HUD README)

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

1. **H004** / **H005** if installable / field use matters  
2. **H007–H010** as time allows  

Product path (Docker → K3s → installer → triage) remains **Phase 3+** in `tasks.md` and can resume when HUD polish is paused.

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
