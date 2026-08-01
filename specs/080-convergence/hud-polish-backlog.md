# HUD polish backlog (mobile + operator chrome)

**Status**: Active backlog — pick up when returning to Visual HUD UX  
**Spec home**: `specs/080-convergence/`  
**Code home**: `ui/netclaw-visual/`  
**Last updated**: 2026-07-24 (H001–H010 shipped — Phase H complete)

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
| H006 Smoke checklist | HUD README mobile/landscape checklist | earlier |
| H004 PWA shell | `manifest.webmanifest`, icons 192/512/maskable, `sw.js` shell+graph cache, register on boot | this session |
| H005 Stale graph | `graph-cache.js` localStorage; fetchGraph fallback; STALE banner + Retry; SW network-first `/api/graph` | earlier |
| H007 Knowledge mobile | Bottom sheet when expanded; collapsed pill chip; header tap on coarse pointer | this session |
| H008 Topbar height | `ResizeObserver` → `--topbar-height` for sidebars + Home root | this session |
| H009 Quality persist | `localStorage` mode + pin; survives reload / mobile auto-FOCUS when pinned | this session |
| H010 Terminal snaps | collapsed → peek (~30%) → expanded (~55%); cycle toggle; drag snaps nearest | this session |

**Key files**

- `ui/netclaw-visual/src/app-shell/mobile-layout.js`
- `ui/netclaw-visual/src/app-shell/graph-cache.js` / `register-sw.js`
- `ui/netclaw-visual/public/sw.js`, `manifest.webmanifest`, `icons/*`
- `ui/netclaw-visual/src/main.js` — `fetchGraph`, stale banner, chat window, mobile wire
- `ui/netclaw-visual/src/styles.css` — mobile/landscape + `.stale-banner`
- `ui/netclaw-visual/index.html` — PWA meta, stale banner, chat resize handle

---

## Worth doing next (deferred from mobile pass)

Prioritized for **operator value / effort**. IDs `H###` are HUD-polish only (orthogonal to product Phases 3–7).

### P1 — Shipped this session (kept for history)

- **H001** Landscape mode chrome — done  
- **H002** `prefers-reduced-motion` — done  
- **H003** Touch long-press node detail — done  
- **H006** Mobile smoke checklist — done  

---

### P2 — Shipped this session

- **H004** PWA shell — done (`public/manifest.webmanifest`, `public/sw.js`, `public/icons/*`)  
- **H005** Offline / stale graph — done (`graph-cache.js`, stale banner, SW graph cache)  

**Install note**: Chromium “Install app” / iOS Share → Add to Home Screen needs **HTTPS** (or localhost). LAN HTTP will still run the HUD but may not prompt install.

---

### P3 — Shipped (Phase H complete)

- **H007** Knowledge panel mobile pass — done  
- **H008** Dynamic topbar height — done  
- **H009** Quality mode persistence — done  
- **H010** Terminal snap points — done  

---

## Suggested pickup order

**Phase H (H000–H010) is complete.** Next default:

1. Product **Phase 3 Docker** (`tasks.md` T030+)  
2. Ad-hoc HUD bugs only as they appear  

Product path (Docker → K3s → installer → triage) remains **Phase 3+** in `tasks.md`.

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
