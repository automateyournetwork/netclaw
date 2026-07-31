# HUD / Convergence handoff

What a new session needs to know before touching `ui/netclaw-visual/` or
`ui/convergence-api/`. Written 2026-07-29.

---

## 1. The one rule

**Never add functionality by editing `ui/netclaw-visual/server.js` or
`src/main.js` inline.** Upstream owns both and rewrites them. The HUD 2.0 merge
(`2ca395c`) deleted ~500 lines of this fork's code from those two files and
**produced no errors** — the markup in `index.html` and the modules on disk
survived, only the wiring went. Symptoms were "the CONVERGENCE tab does nothing"
and "the footer stopped populating", which cost hours to trace.

Everything fork-specific goes in one of:

| Path | Owner | For |
|---|---|---|
| `modules/<id>/` | fork | optional features (Convergence, retro theme, scene quality) |
| `server.local.js` | fork | general backend repair |
| `src/fork-local/ui.js` | fork | general frontend repair |
| `ssh-terminal.js` | fork | SSH PTY backend |
| `src/panels/TerminalPanel.js` | fork | SSH PTY frontend |

Upstream-owned files carry **hooks only**. Current footprint: ~186 lines across
both, in discrete labelled blocks.

---

## 2. The hooks and patches in upstream-owned files

Every one is labelled `FORK PATCH` or `FORK-LOCAL` — grep for those.

**`server.js`** (5 patches + 2 hooks)

1. `requireTrustedClient` — gates `/api/env`, `/api/testbed/raw`, `/api/models`
   to loopback + RFC1918. `HUD_TRUSTED_IPS` / `HUD_API_TOKEN` tighten it.
2. Dropped the plaintext `value` from `/api/env/:integrationId`. **Do not
   reintroduce it** — it leaked every credential in `.env` unauthenticated.
3. `${VAR}` resolution in `getGatewayConfig()` — `openclaw.json` stores the token
   as `"${OPENCLAW_GATEWAY_TOKEN}"`; unresolved it 401s and the HUD reports
   "gateway offline" while the gateway is fine.
4. `forkLastChatUsage` declaration + capture in `/api/chat` — backs the footer
   "Last Turn" field.
5. Module loader hook (`loadModules` + `registerModuleIndex`), then the
   `server.local.js` hook. **Order matters:** modules first, `server.local.js`
   second, because its SPA fallback swallows every unmatched GET.

**`src/main.js`** (2 hooks + 1 dead block)

1. `registerForkUI({ dom, state })` at the **end** of `wireUI()`. Must stay last:
   it replaces `#chat-toggle` with a clone to drop upstream's competing collapse
   handler, which requires upstream's to already be attached.
2. `loadModuleUIs({ dom, state, setDetail, focusTarget })`, fire-and-forget.
3. A "Console" button inside `setDetail('device')` — **dead code.** See §6.

---

## 3. Module contract

Full spec in `ui/netclaw-visual/modules/README.md`. Essentials:

```
modules/<id>/
  module.json   { id, name, description, requiresEnv: [...] }
  server.js     export function register(app, ctx)
  ui.js         export function registerUI(ctx)
```

- `requiresEnv` unset → discovered but **not registered**: no routes, no UI, no
  CSS in the bundle. This is what makes optional mean optional.
- Backend registers last, so first-party routes win.
- Frontend uses `import.meta.glob` with `!../modules/_*/ui.js` negation, so
  `_example/` never enters the bundle.
- A throwing module is logged and skipped; HUD and siblings unaffected.
- Modules must **not** import each other or reach into `src/`. Use events —
  see `netclaw:open-terminal` in §5.

Verify: `curl -s localhost:3001/api/modules | jq`

---

## 4. Verification one-liners

```bash
# expected startup lines
journalctl --user -u netclaw-hud -n 6 --no-pager | grep -E "modules|local"
#   [modules] convergence: registered
#   [local] fork extensions loaded (5 route groups, frontend: dist/)

# module state
curl -s localhost:3001/api/modules | jq '.modules[] | {id,configured,routes,missing}'

# fork endpoints that must be 200
for p in / /api/graph /api/home/status /api/models /api/tokens/summary \
         /api/ssh/capabilities; do
  echo "$(curl -s -o /dev/null -w '%{http_code}') $p"; done

# browser console after a hard refresh
#   [fork-ui] restored: topbar-height, footer-token-strip, model-readout,
#                       terminal-provider, chat-drawer-move-resize
#   [modules] UI mounted: convergence
```

After `npm run build` the bundle hashes change — **hard refresh (Ctrl+Shift+R)**
or you will be looking at a cached, apparently-broken HUD.

### Two renderers, one layout

`orgchart/` computes the layout; two renderers draw it. Neither owns the data.

| Theme | Renderer | Where |
|---|---|---|
| Modern | WebGL (Three.js) + CSS2D labels | `src/orgchart-render/` |
| Retro | DOM Program Manager desktop | `modules/retro-theme/program-manager.js` |

`setOrgChartTheme()` rethemes the WebGL chart **in place** — no remount, so a
dragged claw keeps its position across a theme switch. Retro hides `#scene-root`
and mounts the DOM desktop instead; the two never co-exist. Retro also bypasses
the composer entirely in `animate()` rather than toggling passes, because
scene-quality reasserts pass state every frame and `enableCinematicBurst()` fires
on a 6s timeout — a bypass cannot be overridden by either.

### COMMAND layout and right rail

- Internal member claws use a readable multi-row default from
  `src/orgchart/layout.js`; department summaries render as compact two-line
  cards instead of one long strip.
- `src/orgchart-render/drag.js` owns drag lifecycle and click suppression. Two
  grab targets: a **claw** moves alone, a **department card** moves its header,
  rail and every claw under it together. Positions persist per Border in browser
  localStorage through `src/orgchart/positions.js` (**schema v2** — v1 documents
  are discarded, not migrated, because they held claw offsets against a default
  packing that has since changed). Footer **Layout → RESET** clears the key and
  restores the computed default, including department positions.
- Rails and summaries update **in place**; they must never be rebuilt during an
  interaction, because `DragControls` holds a live reference to the department
  handle mesh. Anything that does rebuild them (theme switch, a member enrolling)
  must call `state.orgChartDrag.refresh()` — the targets array is mutated in
  place, never replaced, for the same reason.
- Border, external peers and the mobile-edge lane keep their structural
  positions; only claws and departments move.
- The right rail order is **Focus → Selection → Knowledge**. Knowledge uses
  `new KnowledgePanel(socket, { docked: true })`; docked mode keeps RAG behavior
  but deliberately skips floating drag/resize and geometry restoration.

---

## 5. Hard-won gotchas

- **The env loader reads BOTH `~/.openclaw/.env` and the repo `.env`.** Commenting
  a variable in one is not enough to test the unconfigured path. This made the
  module-gating test look broken.
- **A CSS variable with a fallback everywhere and a writer nowhere reads as a
  working layout until content changes.** `--topbar-height` had six consumers,
  all with fallbacks, and its only writer was the orphaned `mobile-layout.js`.
  Nothing looked broken until the topbar grew past 140px, at which point it
  covered the sidebar collapse buttons. **When auditing a merge, grep for who
  *writes* each custom property, not just who reads it.** Now published by
  `initTopbarHeight()` in `fork-local`.
- **`.topbar-brand-block` is `flex-direction: column`.** Anything appended there
  becomes a new stacked row and makes the topbar taller — which then pushes it
  over whatever sits below. Add topbar controls to a flex row (see
  `.retro-tab-row`) or directly to `.topbar`, which is a row.
- **Orphaned CSS fails completely silently.** `index.html` only `<link>`s
  `src/styles.css`; anything else needs a JS import. `home.css` lost its import
  in the merge and the Convergence view rendered as an unstyled `position:static`
  div *behind* the fixed canvas — visually identical to a dead button, nothing in
  the console. **When auditing a merge, check CSS imports, not just JS.**
- **`server.listen(port)` with no host already binds all interfaces** (`::`
  dual-stack). An earlier "fix" adding `0.0.0.0` was unnecessary; the real fault
  was missing static serving returning 404 on `/`.
- **`HUD_SSH_*` must resolve from `.env`, not just `process.env`** — the systemd
  unit has no `EnvironmentFile`, so `process.env`-only reads made documented
  settings silently inert.
- **Do not `git stash pop` blind.** This repo has pre-existing stashes
  (`pre-cert-merge` and others). A no-op `git stash -u` followed by `pop` will
  pop *someone else's* stash and conflict hard. Check `git stash list` first.
- **The washed-out 3D scene is a WebGL problem, not CSS** — which is why it looked
  identical in both themes. Four causes: `toneMappingExposure = 1.55` on top of
  ACES, `UnrealBloomPass` threshold `0.5` (quality modes only ever change
  *strength*, so no mode escapes the haze), `alpha: true` with no clear colour so
  the page gradient lifts the black point, and grain + RGB shift on at `balanced`.
  `modules/scene-quality/` retunes it live rather than editing `main.js`, because
  the exposure carries upstream's comment "operator feedback".
- **The "halo" framing the viewport is `VignetteShader`** (`main.js` ~432,
  darkness 1.4 / offset 0.95). Added once and never touched again — no quality
  mode disables it — so it reads as permanent chrome rather than an effect.
  `scene-quality`'s Edge vignette slider defaults to 0, which disables the pass.
- **`.home-root` is `position: fixed` + `overflow: auto`.** Anything mounted as a
  row inside it scrolls out of the clip region on a long subview and is simply
  gone, with no scrollbar on the page to suggest otherwise. That is what happened
  to the Convergence section selectors; they now live in `#home-topbar-slot` in
  the topbar. Consequence: the toolbar is **not** inside `HomeView.element`, so
  toolbar lookups must use `qs()`/`qsa()`, and any Convergence stylesheet needs
  the `:is(.home-root, .home-topbar-slot)` scope or the toolbar goes unstyled.
- **Three upstream paths rewrite the post-processing values**, and only one is a
  click: `setQualityMode()` (button *or* keyboard), `enableCinematicBurst()` (6s
  timeout on chat activation, restores from the quality mode), and init ordering.
  Anything that tunes those passes needs a per-frame drift check, not an event
  listener — a listener let grain come back on the next chat turn.
- **A CSS2DObject only removes its `<div>` when THAT object is detached.**
  Removing a *group* that contains labels does not cascade, so every rebuild of
  bands/categories/nodes left orphaned label elements in the DOM — frozen at
  their last projected position while the live chart panned underneath. On screen
  it reads as "a second copy of the chart that won't move", and nothing appears
  in the console. Any `dispose()` that tears down a group with labels must call
  `removeLabelElements()` (`orgchart-render/css2d.js`). `expansion.js` had always
  done this by hand; the rebuild helpers copied the geometry/material dispose
  shape and missed it.
- **A module-level helper can be shadowed by a local `const` inside one
  function.** `buildCategories()` has a local `const rail` for the rail mesh; a
  module-level `rail()` style helper called earlier in that same scope is a
  temporal-dead-zone error, minified to `Cannot access 'd' before
  initialization`. Named `railStyle()` now. **The 85 tests passed with this bug
  present** — they cover layout maths and treatment constants, not scene
  construction, so browser-only boot failures slip straight through. Exercise the
  real build path in node when touching a builder.
- **Retro cannot be reached by restyling the 3D scene.** Two attempts were made
  (light clear colour, flat materials, composer bypass) and both still read as
  "the dark galaxy with different paint", because lit spheres/rings/icosahedra do
  not become desktop icons whatever colour they are. Win3.11 is 1px bevels and
  icon grids — a DOM problem. Retro now hides the canvas and renders its own
  Program Manager desktop from the same layout data
  (`modules/retro-theme/program-manager.js`).
- **The repo is PUBLIC.** No credentials, real hostnames or management IPs in
  committed docs. `SSH-TERMINAL-HARDENING.md` was redacted for this; the values
  remain in history at `edc9ae8`, so the affected switch credentials should be
  treated as disclosed.

---

## 6. Known-dead / known-broken

- **The retired HUD 1.0 integration/device populations still have residual state
  and detail code in `main.js`.** Phase 1 no longer exposes controls that target
  those empty arrays: COMMAND now uses real org-chart category filters plus
  `All / Active / Attention` focus. Do not repopulate the old orbit geometry;
  remove the residual code upstream when the renderer contract is stable.
- **`src/app-shell/mobile-layout.js`, `graph-cache.js`, `register-sw.js` are
  orphaned** — nothing imports them. So mobile layout, long-press select, graph
  caching and the service worker are all inactive. Restoring them needs
  `applyReducedMotion` / `wireLongPressSelect`, which upstream's `main.js` lacks.
  Check for orphaned CSS when restoring these. `mobile-layout.js`'s
  `--topbar-height` publisher has been reinstated separately in `fork-local`
  (see §5) — do not duplicate it if the module is ever wired back up.
  Note `public/sw.js`, `manifest.webmanifest` and the icons all still ship and
  land in `dist/`, so the HUD advertises itself as installable while nothing
  registers the worker.
- **`/api/tokens/summary` `lastTurn`** only populates after a chat turn through
  `/api/chat`; null on a fresh restart is correct.

---

## 7. Upstream status

Maintainer has **accepted** the extension-point proposal.

| Item | State | Where |
|---|---|---|
| `/api/env` secrets fix | merged upstream | PR #190 |
| Module loader | branch pushed, PR not opened | `feat/hud-module-loader` (`5ce4de2`) |
| COMMAND trust-map Phase 1 | local, not filed | capability departments, interaction state, real focus controls, viewport framing |

Bodies to paste are in `docs/upstream/`. The PAT on this host is **read-only** on
`automateyournetwork/netclaw` (`permissions: pull` only), so PRs and issues must
be opened in the browser.

Both branches are cut from pristine `upstream/main` and contain **only** their own
change — no fork content. Keep it that way; untracked fork files are present on
disk, so always `git add` explicit paths on those branches, never `-A`.

---

## 8. Convergence upstream-readiness backlog

Priority order. Items 1–4 are prerequisites for anyone else running it.

1. ~~**Hardcoded devices**~~ — DONE 2026-07-29. `switches.match` / `switches.models` per site in `SITES_CONFIG`; default `.*` shows whatever the exporter reports.
2. ~~**`SITE` hardcoded**~~ — DONE 2026-07-29. Discovered from `GET /sites`,
   persisted in `localStorage`, selector rendered only when 2+ sites are
   authorised. Falls back to the previous single-site behaviour if discovery
   fails.
3. ~~**Postgres mandatory**~~ — DONE 2026-07-29. Optional: only the diary and
   triage use it. Reads return `unavailable` + reason, writes 503, `/healthz`
   reports `features.diary`, compose dependency is `required: false`,
   `CONVERGENCE_DB=off` disables it. Half-open breaker recovers without a
   restart.
4. ~~**No contract tests**~~ — DONE 2026-07-30. `ui/convergence-api/CONTRACT.md`
   documents the shapes; `tests/contract/test_convergence_api.py` enforces them.
   Skips when the API is unreachable. **Degraded-path assertions can pass
   vacuously against a healthy stack** — a mutation proved this — so use
   `CONVERGENCE_EXPECT_DEGRADED=1` with the store stopped to verify the fallback
   contract:

   ```bash
   docker compose -f deploy/convergence/docker-compose.yml stop postgres
   CONVERGENCE_EXPECT_DEGRADED=1 .venv/bin/python -m pytest \
       tests/contract/test_convergence_api.py -q
   ```
5. ~~**Retro theme**~~ — DONE 2026-07-30, as `modules/retro-theme/` rather than a
   Convergence-only skin, since it has to restyle HUD chrome (topbar, chat
   drawer, Knowledge panel, footer, SSH terminal). It owns `body.retro-311`;
   other modules ship a sheet keyed off that class. xterm needed JS, not CSS —
   canvas rendering means the palette comes from JS options, so `TerminalPanel`
   reads the theme from the DOM and listens for `netclaw:theme-changed`.
   **Rendered appearance is unverified** — no browser automation here.
6. ~~**Washed-out 3D scene**~~ — DONE 2026-07-30, `modules/scene-quality/`.
   See §5 for the diagnosis and the drift-hold requirement.
   **Rendered appearance is unverified.**

Distribution: upstream bundles 23 components in-repo and clones 17 externally.
Since Convergence is no longer a commercial product, **bundle it in-repo** as an
opt-in catalog entry (`scripts/lib/catalog.sh` + `component_install_convergence()`),
like `rag-mcp`. Do **not** propose a git submodule — submodules are unconditional,
which defeats the opt-in requirement.

---

## 9. Runtime facts

- HUD: `systemctl --user restart netclaw-hud` → `localhost:3001`, all interfaces.
- Gateway: `openclaw-gateway.service` → `:18789`, token from
  `${OPENCLAW_GATEWAY_TOKEN}`.
- convergence-api: `CONVERGENCE_API_URL=http://127.0.0.1:3080`.
- SSH terminal: **enabled**, using `NETCLAW_*` privilege-15 credentials. The app
  filter is the only guard and is best-effort by design — abbreviations, `do`,
  pasted blocks and EEM can evade line matching. Real enforcement needs a
  privilege-1 device account (`HUD_SSH_USERNAME`/`PASSWORD`); see
  `ui/netclaw-visual/docs/SSH-TERMINAL-HARDENING.md`, including why dropping
  `privilege level 15` from `line vty 5 15` must not happen before setting an
  enable secret.
- Audit trail: `~/.openclaw/hud-ssh-audit.log` (0600).
