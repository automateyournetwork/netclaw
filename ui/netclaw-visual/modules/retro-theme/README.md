# Retro Theme (Windows 3.11)

Opt-in Program Manager era skin for the whole HUD. UI-only: no `server.js`, no
routes, `requiresEnv: []`.

It loads always and does nothing until toggled — gating a colour scheme behind an
env var would mean editing `.env` and restarting to change how the UI looks. The
toggle *is* the opt-in.

## Using it

A **RETRO** button appears in the topbar next to the tab strip. The choice is
remembered in `localStorage` under `netclaw.theme`.

## What it restyles

| Area | Selectors |
|---|---|
| Topbar | `.topbar`, `.topbar-brand-block`, `.app-tab`, `.metric` |
| Chat drawer | `.chat-drawer`, `.chat-header`, `.chat-messages`, `.chat-input`, `.chat-send` |
| Knowledge panel | `.knowledge-panel`, `.kp-*` |
| Footer | `.footer`, `.footer-row`, `#footer-*` |
| SSH terminal | `.tp-panel`, `.tp-head`, `.tp-side`, `.tp-term` + the xterm palette |

The 3D canvas is left alone deliberately — an org chart of glowing nodes has no
1992 equivalent, and dithering it would just look broken.

## The `body.retro-311` convention

This module owns one thing other code may rely on: the class `retro-311` on
`<body>`.

Any module may ship its own sheet keyed off `body.retro-311 …` to participate.
`modules/convergence/retro.css` does. That keeps each module's retro styling next
to the markup it applies to, instead of this module needing to know every other
module's class names.

A `netclaw:theme-changed` event is dispatched on `window` with
`{ detail: { theme: 'retro' | 'modern' } }` for anything that cannot be done in
CSS.

## Why xterm needs JavaScript

`xterm.js` renders to a canvas, so its colours come from JS options and CSS cannot
reach them. Without special handling the terminal stayed dark blue while
everything around it turned grey.

`src/panels/TerminalPanel.js` reads the theme from the DOM (`body.retro-311`) and
listens for `netclaw:theme-changed`, so an open session repaints instead of
needing to be reopened. Its retro palette is the 16 CGA colours on black — an
MS-DOS Prompt box.

## Design rules

Committing to the era means accepting things the modern sheet avoids:

- No rounded corners, gradients, shadows or transitions. Depth is 2px bevels —
  white/`#dfdfdf` top-left, `#808080`/black bottom-right.
- **No hover states.** Buttons invert their bevel on `:active`. Windows 3.1 had no
  hover, and adding it reads as anachronistic.
- Chrome is `#c0c0c0`, client areas are `#fff`, title bars are `#000080`, the
  desktop is teal.
- Status carries a text marker (`✓ ! ✗`) as well as colour. The 16-colour palette
  has no good amber, and olive-on-grey is genuinely hard to read.
- Selection is inverse video — the only selection style the era had.

## Known tradeoff

Chrome selectors are upstream's. If upstream renames them the skin degrades
**visually, never functionally** — nothing here changes behaviour. The colour
re-map goes through upstream's own CSS custom properties (`--bg`, `--text`,
`--line`, `--accent`, `--ok`), which is far more durable than overriding rules, so
a rename costs bevels rather than the whole theme.

## Removing it

Delete this directory. Nothing outside it references the class except
`modules/convergence/retro.css` (inert without it) and the xterm palette in
`TerminalPanel.js` (falls back to the modern theme).
