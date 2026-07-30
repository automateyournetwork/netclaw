# HUD modules

Optional, self-contained additions to the HUD. A module can add API routes, UI,
or both, **without editing `server.js` or `src/main.js`**.

That constraint is the point. Before this existed, the only way to extend the
HUD was to patch those two files — so any downstream addition was either a merge
conflict in a file it didn't own, or silently discarded when the conflict was
resolved upstream's way. Silently, because the markup and modules survive; only
the wiring goes. A module is deletable by removing its directory, and absent
until someone opts in.

## Layout

```
modules/
  <id>/
    module.json      required — metadata + gating
    server.js        optional — export function register(app, ctx)
    ui.js            optional — export function registerUI(ctx)
    README.md        recommended — what it does, what it needs
```

Directories starting with `_` or `.` are skipped, so `_example/` ships as
documentation without loading.

## module.json

```json
{
  "id": "my-module",
  "name": "My Module",
  "description": "One line, shown in GET /api/modules.",
  "requiresEnv": ["MY_MODULE_URL", "MY_MODULE_TOKEN"]
}
```

`requiresEnv` is the gate. If any listed key is unset or empty — checked against
`process.env` first, then the merged `.env` files — the module is **discovered but
not registered**: no routes, no UI, no half-initialised state. It appears in
`GET /api/modules` as `configured: false` with the missing keys listed, which is
what makes "optional" mean optional rather than present-but-broken.

Omit `requiresEnv` (or use `[]`) for a module that needs no configuration.

## server.js

```js
export function register(app, ctx) {
  app.get('/api/my-module/status', (req, res) => {
    res.json({ ok: true });
  });
}
```

Called once, **after** all first-party routes, so those always take precedence.
May be `async`. Throwing is logged loudly and skips just that module — the HUD
still starts.

Namespace your routes under `/api/<id>/` to avoid collisions.

## ui.js

```js
export async function registerUI(ctx) {
  // ctx: { dom, state, setDetail, focusTarget }
}
```

Called once after the HUD has wired its own chrome. Import your own CSS from
here — `index.html` only `<link>`s `src/styles.css`, so a stylesheet without a
JS import silently does nothing:

```js
import './my-module.css';
```

Only called for configured modules, so guard clauses about missing config are
unnecessary.

## The ctx surface

Deliberately small, so it can stay stable.

**Server** (`register(app, ctx)`)

| Key | What |
|---|---|
| `ROOT` | repo root path |
| `TESTBED_FILE` | path to the pyATS testbed |
| `parseEnvFile()` | merged `.env` as an object |
| `readText(file)` | read a file, `''` if missing |
| `broadcastWS(type, payload)` | push an event to connected HUD clients |
| `getGatewayConfig()` | `{ port, token, chatCompletionsEnabled }` |
| `env(key)` | resolved value from `process.env` then `.env` files |

**Browser** (`registerUI(ctx)`)

| Key | What |
|---|---|
| `dom` | the HUD's element map |
| `state` | the HUD's shared state object |
| `setDetail(kind, payload)` | render into the selection panel |
| `focusTarget(position)` | move the camera |

Needing something not listed here is worth an issue rather than reaching into
globals — the whole value of a published surface is that it can be kept working.

## Shared conventions

Modules must not import each other. Where they need to cooperate, use a documented
convention instead:

| Convention | Owner | Purpose |
|---|---|---|
| `body.retro-311` class | `retro-theme` | a module may ship a sheet keyed off it to participate in the theme |
| `netclaw:theme-changed` event | `retro-theme` | `{ detail: { theme } }`, for what CSS cannot express |
| `netclaw:open-terminal` event | terminal provider | `{ detail: { device, ack } }`, ask for a session without importing the panel |

Each is a one-way announcement, so a module works whether or not its counterpart
is installed.

## Modules in this tree

| Module | Backend | Purpose |
|---|---|---|
| `convergence` | yes | site health portal; proxies to convergence-api |
| `retro-theme` | no | Windows 3.11 skin for the HUD; owns `body.retro-311` |
| `scene-quality` | no | retunes the 3D post-processing, with live controls |

`retro-theme` and `scene-quality` are UI-only: no `server.js`, `requiresEnv: []`.
They load always and do nothing until used, which is the right shape for
presentation concerns — gating a colour scheme or a contrast slider behind an env
var would mean editing `.env` and restarting to change how the UI looks.

## Installer integration

A module normally ships as an opt-in component: a `scripts/lib/catalog.sh` entry
plus a `component_install_<id>()` in `scripts/lib/install-steps.sh`, the same as
any bundled MCP server. Users select it with `--components <id>` or a profile.

## Checking what loaded

```bash
curl -s localhost:3001/api/modules | jq
```

The server logs one line per module at startup, and the browser console logs
what mounted, what was skipped as unconfigured, and what failed.
