# HUD fork-local changes

How this fork's HUD additions survive `git merge upstream/main`.

## The problem

Upstream owns `server.js` and rewrites it freely. The HUD 2.0 rewrite
(`2ca395c`) deleted ~500 lines of endpoints this fork depends on. Because our
additions were inline in `server.js`, every pull produced a large conflict in a
file we don't own — and resolving it in upstream's favour silently dropped
features (the Convergence tab went blank, `/` started 404ing).

## The layout

| File | Owner | Contents |
|------|-------|----------|
| `server.js` | upstream | everything upstream ships, plus **43 lines** of fork patches in 2 spots |
| `server.local.js` | **this fork** | all fork endpoints + static/SPA serving |
| `src/views/home/HomeView.js` | **this fork** | Convergence tab (fork-only file) |
| `src/panels/KnowledgePanel.js` | shared | upstream file; fork adds URL-ingest + crawl UI |

Everything fork-specific that *can* live outside `server.js` does.

## The 3 patches in server.js

0. **Credential/config gate** (`requireTrustedClient`, mounted right after
   `express.json`). Upstream ships `/api/env/*` returning every `.env` key,
   `PUT /api/env` writing them, and `PUT /api/testbed/raw` able to repoint
   pyATS — all unauthenticated on an all-interfaces listener. Also drops the
   plaintext `value` field from `/api/env/:id` (the HUD only renders `masked`
   and `isSet`, so the cleartext was pure exposure).

   Default allows loopback + RFC1918/link-local, so a normal LAN is unaffected
   but a public exposure or tunnel is not. `HUD_TRUSTED_IPS` narrows it,
   `HUD_API_TOKEN` adds bearer auth. One `app.use([...])` mount rather than
   per-route edits, to keep the merge surface at a single line.

1. **The hook**, immediately before `server.listen()`:
   ```js
   const local = await import('./server.local.js');
   local.register(app, { /* 12 borrowed identifiers */ });
   ```
   Registered last so upstream routes take precedence and the SPA fallback
   lands at the bottom of the stack.

2. **`getGatewayConfig()` `${VAR}` resolution.** `openclaw.json` stores the
   token as `"${OPENCLAW_GATEWAY_TOKEN}"`. Upstream passes that string through
   verbatim, gets a 401 from `/v1/*`, and reports "gateway offline". This
   resolves it against `process.env` and the `.env` files.

   This one is a genuine upstream bug, not a fork preference — worth sending
   upstream as a PR, which would remove it from this list.

## What server.local.js provides

| Route | Consumed by |
|-------|-------------|
| `/api/home/status`, `/api/home/*` | Convergence tab; proxies to `CONVERGENCE_API_URL` |
| `GET`+`POST /api/models` | HomeView model SoT editor |
| `/api/rag/ingest-url`, `/api/rag/crawl-site` | KnowledgePanel fork additions |
| `/api/tokens/summary` | nothing currently — see below |
| static `dist/` + SPA fallback | the browser |

Nothing is hard-coded. The Convergence proxy reads `CONVERGENCE_API_URL` /
`CONVERGENCE_API_TOKEN`, falling back to `HOME_API_*` then
`NETWORK_GUARDIAN_*` aliases.

## Turning it off

```bash
HUD_LOCAL_EXTENSIONS=0 node server.js   # or delete server.local.js
```
Both give pristine upstream behaviour: fork routes 404, `/` 404s (upstream
serves the frontend via `vite preview` on :3000, not from the API process),
upstream routes unaffected, and no `[local]` log lines.

## After every `git merge upstream/main`

1. `node --check server.js && node --check server.local.js`
2. Restart and look for this line — it is the whole health check:
   ```
   [local] fork extensions loaded (6 route groups, frontend: dist/)
   ```
   If a merge removed or renamed one of the 12 borrowed identifiers,
   `assertCtx()` fails loudly and names them. Fix the ctx object at the hook.
3. Smoke-test:
   ```bash
   for p in / /api/home/status /api/models /api/tokens/summary /api/health; do
     echo "$(curl -s -o /dev/null -w '%{http_code}') $p"
   done
   ```
4. If `git merge` reports a conflict in `server.js`, take **upstream's whole
   file** and re-apply just the 2 patches above. Never hand-merge it.

## Notes / known gaps

- **`lastTurn` in `/api/tokens/summary` is always `null`.** Populating it
  required patching the middle of upstream's `/api/chat` handler — a guaranteed
  future conflict — and no `src/` file calls this endpoint today. Lifetime
  totals still work (they come from the token exporter). To restore it, pass a
  `getLastChatUsage()` through ctx rather than editing the chat handler.
- **Route bodies in `server.local.js` are byte-identical to pre-merge
  `server.js` (fork commit `30e2882`)**, original indentation included, so they
  can be diffed against fork history if a shared helper signature changes.
  Don't reformat them casually.
- **The bind address was never the problem.** `server.listen(port)` with no
  host already binds all interfaces (`::` dual-stack), so upstream is
  LAN-reachable as shipped. An earlier fix here added an explicit `0.0.0.0`;
  it was unnecessary and has been dropped.
- **The HUD still has no real authentication.** Patch 0 removes the
  free-for-all on the credential and config-write surface, but everything else
  (`/api/graph`, `/api/chat`, `/api/bgp`, RAG, sessions) is open to anyone who
  can reach the port. Proper auth belongs at the ingress, alongside the other
  `*.internal.byrnbaker.me` services — not as per-route middleware in a
  browser app with no login flow.
- **Rotate any credential that was served by `/api/env/*`** before the gate
  landed. It returned plaintext to any LAN client.

## SSH terminal panel (fork feature)

| File | Role |
|------|------|
| `ssh-terminal.js` | PTY via `ssh2`, scrollback buffer, command filter, `/ask` |
| `src/panels/TerminalPanel.js` + `.css` | xterm.js panel + selection assistant |
| `docs/SSH-TERMINAL-HARDENING.md` | device-side hardening, apply before enabling |

Registered from `server.local.js`, so it survives upstream pulls like the rest.
Added three identifiers to the ctx contract: `TESTBED_FILE`,
`getGatewayConfig`, `requireTrustedClient`.

**Off by default.** `HUD_SSH_ENABLED=1` to turn on. Without
`HUD_SSH_USERNAME`/`HUD_SSH_PASSWORD` it falls back to `NETCLAW_*`, which on
these switches is privilege 15 — the panel shows a warning badge when that
happens.

Output is SSE (`GET /api/ssh/:id/stream`), input is POST. Not a WebSocket:
upstream owns `path: '/ws'`, and a second path-scoped `WebSocketServer` on the
same http server aborts the handshake before ours is reached. Full reasoning in
the header of `ssh-terminal.js`.

The command filter is best-effort on an interactive stream, not a boundary —
device-side privilege is. VLAN 3 / `Vlan3` stays blocked even with
`HUD_SSH_ALLOW_CONFIG=1`. Audit log at `~/.openclaw/hud-ssh-audit.log` (0600).

## Frontend: the same problem, same fix

`src/main.js` is upstream's too, and the HUD 2.0 rewrite replaced it wholesale.
That silently dropped two fork features whose **markup was still in
`index.html`** and whose **modules were still on disk** — only the wiring was
gone, so they failed silently rather than erroring:

| Lost | Symptom | Cause |
|------|---------|-------|
| COMMAND \| CONVERGENCE tab router | clicking CONVERGENCE did nothing | `src/app-shell/tab-router.js` is fork-only; nothing imported it |
| Draggable/resizable NETCLAW TERMINAL | drawer could not be moved or resized | `initChatWindow()` (~417 lines) existed only in the fork's `main.js` |

Restored into `src/fork-local/ui.js` (fork-owned) with **one hook** at the end of
upstream's `wireUI()`:

```js
registerForkUI({ dom, state });
```

`dom` and `state` are the only things that cross the boundary, confirmed by
free-identifier analysis against upstream's `main.js`.

The hook **must stay last in `wireUI()`**: `registerForkUI` replaces
`#chat-toggle` with a clone to drop upstream's own collapse handler, which
otherwise fights the fork drawer's snap logic on every click. Cloning avoids
editing `main.js` further, keeping the coupling to a single call.

Deleting `src/fork-local/ui.js` reverts to pristine upstream.

### Still not restored

The fork's `main.js` also wired `createMobileLayout()`, `wireLongPressSelect()`
and `applyReducedMotion()`. Those pull in further fork-only helpers absent from
upstream's `main.js`, so **mobile layout and long-press select remain inactive**.
`src/app-shell/mobile-layout.js`, `graph-cache.js` and `register-sw.js` are all
still orphaned on disk. Out of scope for the two reported regressions; pick up
when mobile matters.

### Post-merge check for the frontend

`npm run build`, then confirm the restored code survived tree-shaking:

```bash
cd dist/assets && B=$(ls hud-*.js)
for s in "fork-ui] restored" chat-positioned home-mode syncTopbarMetrics; do
  echo "$s -> $(grep -c "$s" "$B")"
done
```
In the browser console you should see `[fork-ui] restored: convergence-tab,
chat-drawer-move-resize`.
