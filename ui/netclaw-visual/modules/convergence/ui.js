/**
 * Convergence module — browser half.
 *
 * Owns everything the tab needs: its stylesheet, its tab button, its container,
 * and the view itself. Nothing in src/ references this module, so deleting this
 * directory removes Convergence entirely.
 *
 * That self-containment is deliberate. Convergence previously relied on
 * index.html markup plus wiring inside src/main.js, and a HUD rewrite silently
 * dropped the wiring — the tab rendered and did nothing, because the button and
 * container survived while the code that made them work did not. Creating both
 * from here means the button cannot exist without the code behind it.
 */

// Module-owned stylesheet. index.html only <link>s src/styles.css, so a
// stylesheet without a JS import silently does nothing — which is exactly how
// this view once ended up unstyled and invisible behind the canvas.
import './home.css';
// Opt-in Windows 3.11 skin. Entirely scoped under .home-root.retro-311, so
// loading it has no effect until the operator toggles the theme.
import './retro.css';
import { createTabRouter } from './tab-router.js';
import { HomeView } from './HomeView.js';

const TAB_ID = 'home';
const TAB_LABEL = 'CONVERGENCE';

/**
 * Ensure the tab button exists. Uses the existing one if the host page already
 * ships it, otherwise creates it — so the module works whether or not the HUD
 * happens to include the markup.
 */
function ensureTabButton() {
  const nav = document.getElementById('app-tabs');
  if (!nav) return false;

  const existing = nav.querySelector(`[data-app-tab="${TAB_ID}"]`);
  if (existing) return true;

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'app-tab';
  btn.dataset.appTab = TAB_ID;
  btn.title = 'NetClaw Convergence — site ops';
  btn.textContent = TAB_LABEL;
  nav.appendChild(btn);
  return true;
}

/**
 * Create the topbar slot the section selector mounts into.
 *
 * The topbar is `display: flex; justify-content: space-between` with two
 * children — the brand block and whichever metrics block is visible — so it has
 * a wide empty middle column. Inserting before the metrics puts the selector
 * there without changing either neighbour's layout.
 *
 * Returns false if there is no topbar, in which case HomeView keeps the controls
 * inside the panel as before.
 */
function ensureTopbarSlot() {
  const topbar = document.querySelector('.topbar');
  if (!topbar) return false;
  if (document.getElementById('home-topbar-slot')) return true;

  const slot = document.createElement('div');
  slot.id = 'home-topbar-slot';
  slot.className = 'home-topbar-slot';

  const stats = topbar.querySelector('.topbar-stats');
  if (stats) topbar.insertBefore(slot, stats);
  else topbar.appendChild(slot);
  return true;
}

/** Ensure the view container exists. */
function ensureRoot() {
  let root = document.getElementById('home-root');
  if (root) return root;

  root = document.createElement('div');
  root.id = 'home-root';
  root.className = 'home-root hidden';
  root.setAttribute('aria-hidden', 'true');
  (document.getElementById('app') || document.body).appendChild(root);
  return root;
}

export async function registerUI(ctx) {
  const { state } = ctx;

  if (!ensureTabButton()) {
    console.warn('[convergence] #app-tabs not found — tab not mounted');
    return;
  }
  const root = ensureRoot();
  // Must exist before HomeView.mount(), which looks for it.
  ensureTopbarSlot();

  if (!state.homeView) {
    state.homeView = new HomeView(root);
    state.homeView.mount();
  }

  state.tabRouter = createTabRouter({
    onChange: (tab) => {
      state.appTab = tab;
      if (tab === TAB_ID && state.homeView) {
        // Re-paint from cache first. Calling syncTopbarMetrics() with no args
        // clears the metrics to "—", so pass the cached health explicitly.
        state.homeView.syncTopbarMetrics(state.homeView.cache?.health || null);
        state.homeView.refresh(true);
      }
      if (tab === 'command') {
        // Canvas needs a resize when returning, or it keeps the home-mode size.
        window.dispatchEvent(new Event('resize'));
      }
    },
  });
  state.tabRouter.wire();
}
