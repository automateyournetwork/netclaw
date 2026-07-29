# Proposal: an extension point for the HUD, so downstream additions survive a release

## The problem

`ui/netclaw-visual/server.js` and `src/main.js` are the only places a fork can add
HUD functionality. When those files are rewritten — as they were in the HUD 2.0
work (`2ca395c`) — every downstream addition is either a large merge conflict in a
file the fork does not own, or silently discarded when the conflict is resolved in
upstream's favour.

Silently is the important part. Merging our fork lost six API endpoints and four UI
features, and **none of them errored**. The markup was still in `index.html`, the
modules were still on disk; only the wiring was gone. Symptoms were things like "the
CONVERGENCE tab does nothing" and "the footer stopped populating" — hours of
bisecting to find that the cause was a missing import, not a bug.

This is not a complaint about the rewrite. It is a structural issue: there is
currently no way to add to the HUD without editing files upstream owns.

## Two upstream-side symptoms of the same root cause

Worth noting these are visible on a clean install, not just in forks:

1. **Focus → Devices is a dead control.** `index.html` ships
   `data-view="devices"`, and `main.js` references `state.devices` in 10 places
   (filters, click handling, the `setDetail('device')` branch), but nothing ever
   populates it — no `buildDevices`, no `devices.push`. Clicking Devices hides every
   integration and renders nothing, and that `setDetail` branch is unreachable. The
   data is present (`/api/graph` returns devices), so it looks like a scene builder
   that went missing in the rewrite. Happy to file this separately if useful.

2. **Orphaned CSS fails completely silently.** `index.html` only `<link>`s
   `src/styles.css`; anything under `src/styles/` needs a JS import. A stylesheet
   that loses its import produces an unstyled, invisible element — visually identical
   to a dead button — with nothing in the console.

## Proposal

A directory of self-contained modules, auto-discovered, no shared-file edits:

```
modules/
  <id>/
    module.json      { id, name, requiresEnv: [...] }
    server.js        export function register(app, ctx)
    ui.js            export function registerUI(ctx)
    README.md
```

- **Backend**: `server.js` scans `modules/*/server.js` and calls `register(app, ctx)`
  once, late, so upstream routes always take precedence.
- **Frontend**: `main.js` uses `import.meta.glob('../modules/*/ui.js')` — statically
  analysable, so absent modules cost nothing and are tree-shaken.
- **Gating**: `requiresEnv` in `module.json`. Unset → the module reports itself
  unconfigured and `registerUI` returns early, so its UI never renders. This is what
  makes a module genuinely optional rather than present-but-broken.
- **Contract**: `ctx` carries the handful of internals modules need. Assert them at
  registration so an upstream rename fails loudly and names the missing key, instead
  of half-loading.

Roughly 50 lines upstream, and it no-ops entirely when `modules/` is empty.

It would also compose with the existing installer: a module becomes a
`scripts/lib/catalog.sh` entry with a `component_install_<id>()`, exactly like
`rag-mcp` today. Users already opt in via `--profile` / `--components`.

## Prior art

We built this in a fork out of necessity and it works. All fork-specific code moved
into two owned files behind one hook each, cutting our footprint inside
upstream-owned files from roughly 500 lines to 43, in two isolated spots. The
`assertCtx()` pattern earned its keep immediately: it caught a helper we had assumed
was upstream's but was actually ours.

## What I'm offering

Happy to open a PR implementing the loader generically — no fork-specific content,
just the extension point plus a README and a trivial example module. I'd rather agree
the shape here first than send an unsolicited design.

Two open questions where I'd defer to you:

- Should modules be able to add top-level tabs, or only panels within existing views?
  Tabs are what our use case needs, but it is the more invasive option.
- `ctx` contents. Ours passes `ROOT`, `parseEnvFile`, `readText`, `broadcastWS`,
  `getGatewayConfig` and a few more. A deliberately minimal published surface would be
  better than exposing internals wholesale.
