/**
 * Retro Theme — Windows 3.11 skin for the whole HUD.
 *
 * UI-only module: no server.js, no routes, `requiresEnv: []`. It loads always
 * and does nothing until the operator toggles it, which is the appropriate
 * opt-in shape for a theme — gating it behind an env var would mean editing
 * .env and restarting to change a colour scheme.
 *
 * WHY THIS IS ITS OWN MODULE
 *   The skin started inside modules/convergence/, scoped to that view. Extending
 *   it to the topbar, chat drawer, Knowledge panel and footer means restyling
 *   first-party HUD chrome, which is not Convergence's business. A module that
 *   reaches out to restyle its host is a boundary violation; a theme module doing
 *   it is just doing its job.
 *
 * THE CONVENTION
 *   This module owns exactly one thing other code may rely on: the class
 *   `retro-311` on <body>. Any module may ship its own sheet keyed off
 *   `body.retro-311 …` to participate — modules/convergence/retro.css does. That
 *   keeps each module's retro styling next to the markup it applies to, instead
 *   of this module needing to know every other module's class names.
 *
 * KNOWN TRADEOFF
 *   Chrome selectors (.topbar, .chat-drawer, .knowledge-panel, .footer) are
 *   upstream's. If upstream renames them the skin degrades visually — never
 *   functionally, since nothing here changes behaviour. The colour re-map is
 *   done through upstream's own CSS custom properties, which is markedly more
 *   durable than overriding rules, so a rename costs bevels rather than the
 *   whole theme.
 */

import './retro-chrome.css';

const STORAGE_KEY = 'netclaw.theme';
const CLASS = 'retro-311';
const EVENT = 'netclaw:theme-changed';

function readStored() {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'retro' ? 'retro' : 'modern';
  } catch {
    return 'modern';
  }
}

function writeStored(theme) {
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* non-fatal — the choice just won't persist */
  }
}

let current = 'modern';

function apply(theme) {
  current = theme === 'retro' ? 'retro' : 'modern';
  document.body.classList.toggle(CLASS, current === 'retro');

  const btn = document.getElementById('retro-theme-toggle');
  if (btn) {
    btn.textContent = current === 'retro' ? 'MODERN' : 'RETRO';
    btn.setAttribute('aria-pressed', current === 'retro' ? 'true' : 'false');
    btn.title = current === 'retro'
      ? 'Return to the modern theme'
      : 'Switch to the Windows 3.11 theme';
  }

  // Announced so other modules can react without importing this one.
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { theme: current } }));
}

/**
 * Put the toggle on the same line as the tab strip.
 *
 * Appending to `#app-tabs`' parent is the obvious move and it is wrong: the
 * parent is `.topbar-brand-block`, which is `flex-direction: column`, so the
 * toggle became a fourth stacked row and made the topbar ~23px taller plus a
 * 10px gap. Anything positioned below the topbar then sat under it — see
 * initTopbarHeight in src/fork-local/ui.js for why that was not self-correcting.
 *
 * So wrap the tab strip and the toggle in a row instead. `#app-tabs` is moved,
 * not recreated, so its id, children and listeners survive — main.js queries it
 * by id and delegates from its buttons.
 */
function mountToggle() {
  if (document.getElementById('retro-theme-toggle')) return true;

  const tabs = document.getElementById('app-tabs');
  const topbar = document.querySelector('.topbar');
  let host = null;

  if (tabs?.parentElement) {
    const row = document.createElement('div');
    row.className = 'retro-tab-row';
    tabs.parentElement.insertBefore(row, tabs);
    row.appendChild(tabs);
    host = row;
  } else if (topbar) {
    // No tab strip (Convergence not installed): a direct topbar child is a
    // flex row item, so it still costs no extra height.
    host = topbar;
  }
  if (!host) return false;

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.id = 'retro-theme-toggle';
  btn.className = 'retro-theme-toggle';
  btn.addEventListener('click', () => {
    const next = current === 'retro' ? 'modern' : 'retro';
    writeStored(next);
    apply(next);
  });
  host.appendChild(btn);
  return true;
}

export async function registerUI() {
  if (!mountToggle()) {
    console.warn('[retro-theme] no .topbar found — toggle not mounted');
  }
  // Honour the stored preference on load, so the choice survives a refresh.
  apply(readStored());
}

/** Exposed for other modules/tests that want the current theme without the DOM. */
export function currentTheme() {
  return current;
}
