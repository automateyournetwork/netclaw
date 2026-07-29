# Convergence

Site health portal for the HUD — WAN and Wi-Fi status, device inventory, an event
diary, and an operator triage panel. Adds a `CONVERGENCE` tab alongside `COMMAND`.

Proxies to [convergence-api](../../../convergence-api/); the browser never talks
to it directly, so its URL and token stay server-side.

## Enabling

```
CONVERGENCE_API_URL=http://127.0.0.1:3080
CONVERGENCE_API_TOKEN=<token matching the API's API_KEYS entry>
```

Aliases accepted for dual-run and legacy installs: `HOME_API_URL`/`HOME_API_TOKEN`,
`NETWORK_GUARDIAN_URL`/`NETWORK_GUARDIAN_TOKEN`.

Only `CONVERGENCE_API_URL` is required to load the module. Without a token the
tab mounts but `/api/home/status` reports `configured: false`, which the view
surfaces rather than failing blankly.

Restart the HUD, then:

```bash
curl -s localhost:3001/api/modules | jq '.modules[] | select(.id=="convergence")'
```

With the URL unset the module is skipped entirely: no routes, no tab, no CSS in
the bundle.

## What it owns

| File | Role |
|---|---|
| `server.js` | `/api/home/status` + the `/api/home/*` proxy |
| `ui.js` | creates the tab button and container, mounts the view |
| `HomeView.js` | the view — overview, wifi, devices, diary, triage, models subviews |
| `tab-router.js` | `COMMAND` \| `CONVERGENCE` switching |
| `home.css` | module-owned stylesheet |

Nothing under `src/` references this directory. Deleting it removes Convergence.

## Dependencies on the rest of the HUD

Two, both deliberately loose:

- **`/api/models`** backs the Models subview. It is a first-party route with
  another consumer (the footer model readout), so it deliberately does not live
  here. If it is absent the subview degrades; nothing else breaks.
- **`netclaw:open-terminal`** is dispatched by the devices table's Console
  action, rather than importing a terminal panel. The button only renders when
  `/api/ssh/capabilities` reports enabled, and the dispatch waits for an ack, so
  Convergence works with no terminal present and vice versa.

Neither is an import, so this module does not break when either is missing.

## Switch inventory

Driven by an optional `switches` block per site in `SITES_CONFIG`:

```json
"switches": {
  "match":  "sw-.*",
  "models": { "sw-01": "Cisco C9300-48P" }
}
```

`match` defaults to `.*` — every device reporting `interface_status`. Narrow it
only if that metric also carries non-switches. `models` is display-only; absent
entries fall back to a metric label, then a generic string.

Previously both were hardcoded to one lab's device names, so the devices table
was empty for any other deployment.

## Backlog

- **`SITE` is hardcoded** to `'home'` in `HomeView.js`. The API is already
  multi-site (`SITES_CONFIG`, `getSiteConfig`); only the client isn't.
- **Postgres is mandatory** for the diary. Should degrade so the module can be
  tried without a database.
- **No contract tests.** The view tolerates several response shapes
  (`d.edge || d.firewall`, `d.devices || d || d.items`), which means the contract
  isn't pinned anywhere.
- **Retro theme option** — an opt-in Windows 3.11 style skin. Feasible as an
  alternate stylesheet plus a body class, since the module owns its own CSS.
