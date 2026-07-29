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
| `modules/<id>/` | fork | optional features (Convergence) |
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
#   [fork-ui] restored: footer-token-strip, model-readout, device-launcher,
#                       terminal-provider, chat-drawer-move-resize
#   [modules] UI mounted: convergence
```

After `npm run build` the bundle hashes change — **hard refresh (Ctrl+Shift+R)**
or you will be looking at a cached, apparently-broken HUD.

---

## 5. Hard-won gotchas

- **The env loader reads BOTH `~/.openclaw/.env` and the repo `.env`.** Commenting
  a variable in one is not enough to test the unconfigured path. This made the
  module-gating test look broken.
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
- **The repo is PUBLIC.** No credentials, real hostnames or management IPs in
  committed docs. `SSH-TERMINAL-HARDENING.md` was redacted for this; the values
  remain in history at `edc9ae8`, so the affected switch credentials should be
  treated as disclosed.

---

## 6. Known-dead / known-broken

- **`Focus → Devices` shows nothing.** Upstream's `index.html` ships
  `data-view="devices"` and `main.js` references `state.devices` in 10 places,
  but nothing populates it — `buildDevices()` did not survive the org-chart
  rewrite. So the `setDetail('device')` branch is unreachable, including the
  Console button in there. This is an upstream bug, reproducible on a clean
  install; the maintainer confirmed the org chart intentionally replaced the
  orbit view. Reaching the terminal works via CONVERGENCE → Devices → Console,
  and the sidebar launcher in `fork-local`.
- **`mobile-layout.js`, `graph-cache.js`, `register-sw.js` are orphaned** on disk
  — nothing imports them. So mobile layout, long-press select, graph caching and
  the service worker are all inactive. Restoring them needs
  `applyReducedMotion` / `wireLongPressSelect`, which upstream's `main.js` lacks.
  Check for orphaned CSS when restoring these.
- **`/api/tokens/summary` `lastTurn`** only populates after a chat turn through
  `/api/chat`; null on a fresh restart is correct.

---

## 7. Upstream status

Maintainer has **accepted** the extension-point proposal.

| Item | State | Where |
|---|---|---|
| `/api/env` secrets fix | branch pushed, PR not opened | `fix/env-endpoint-leaks-secrets` (`ebdfde1`) |
| Module loader | branch pushed, PR not opened | `feat/hud-module-loader` (`5ce4de2`) |
| Dead `Focus → Devices` | not filed | offer as separate issue |

Bodies to paste are in `docs/upstream/`. The PAT on this host is **read-only** on
`automateyournetwork/netclaw` (`permissions: pull` only), so PRs and issues must
be opened in the browser.

Both branches are cut from pristine `upstream/main` and contain **only** their own
change — no fork content. Keep it that way; untracked fork files are present on
disk, so always `git add` explicit paths on those branches, never `-A`.

---

## 8. Convergence upstream-readiness backlog

Priority order. Items 1–4 are prerequisites for anyone else running it.

1. **Hardcoded devices** — `ui/convergence-api/src/routes/devices.js` has 7
   `HomeSwitch.*` PromQL references and a literal `switchModels` lookup. Makes
   the module visibly broken for anyone else, which is worse than absent.
2. **`SITE` hardcoded** to `'home'` in `modules/convergence/HomeView.js`. The API
   is already multi-site (`SITES_CONFIG`, `getSiteConfig`); only the client isn't.
3. **Postgres mandatory** for the diary. Should degrade so the module can be tried
   without a database.
4. **No contract tests.** The view guesses response shapes
   (`d.edge || d.firewall`, `d.devices || d || d.items`), so the contract lives
   nowhere. `tests/contract/` already exists.
5. **Retro theme** — opt-in Windows 3.11 skin. Now easy: the module owns
   `home.css`, so it is an alternate stylesheet plus a body class, persisted in
   `localStorage`, with no changes outside the module.

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
