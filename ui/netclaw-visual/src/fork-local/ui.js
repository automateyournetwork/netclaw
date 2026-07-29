/**
 * ─────────────────────────────────────────────────────────────────────────────
 * FORK-LOCAL UI WIRING — not part of upstream automateyournetwork/netclaw.
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * WHY THIS FILE EXISTS
 *   Same story as server.local.js, on the frontend. Upstream owns src/main.js
 *   and the HUD 2.0 rewrite (2ca395c) replaced it wholesale. That silently
 *   dropped two fork features whose *markup* is still in index.html and whose
 *   *modules* are still on disk — only the JS that wired them up was lost:
 *
 *     1. The COMMAND | CONVERGENCE tab router (src/app-shell/tab-router.js is
 *        fork-only and was left orphaned — nothing imported it, so clicking
 *        CONVERGENCE did nothing at all).
 *     2. The draggable / resizable NETCLAW TERMINAL drawer (initChatWindow,
 *        ~417 lines, including persisted geometry and snap levels).
 *
 *   Carrying those inline in main.js is what caused the loss in the first
 *   place, so they live here instead. Upstream never touches this path.
 *
 * CONTRACT WITH main.js
 *   One call at the end of upstream's wireUI():
 *
 *       registerForkUI({ dom, state });
 *
 *   That is the entire coupling. `dom` and `state` are the only two things the
 *   restored code borrows (verified by free-identifier analysis against
 *   upstream main.js — nothing else crosses the boundary).
 *
 *   Safe to delete: main.js guards the call, so removing this file just returns
 *   the HUD to pristine upstream behaviour.
 *
 * NOT RESTORED (deliberate, tracked)
 *   The fork's main.js also wired createMobileLayout(), wireLongPressSelect()
 *   and applyReducedMotion(). Those depend on further fork-only helpers that
 *   upstream's main.js does not define, so restoring them is a larger job than
 *   the two reported regressions and is intentionally out of scope here. Mobile
 *   layout and long-press select are therefore still inactive. See FORK-NOTES.
 *
 * MAINTENANCE NOTE
 *   initChatWindow's body is kept byte-identical to fork commit 30e2882
 *   (main.js:3280-3696), original indentation included, so it can be diffed
 *   against fork history. Do not reformat it casually.
 */

import { createTabRouter } from '../app-shell/tab-router.js';
import { HomeView } from '../views/home/HomeView.js';

export function registerForkUI(ctx) {
  const { dom, state } = ctx || {};
  if (!dom || !state) {
    console.error('[fork-ui] registerForkUI needs { dom, state } — skipping');
    return { ok: false, restored: [] };
  }

  const restored = [];

  try {
    initConvergenceTab(state);
    restored.push('convergence-tab');
  } catch (err) {
    console.error('[fork-ui] convergence tab failed:', err);
  }

  try {
    // Upstream's wireUI() attaches its own simple collapse handler to
    // #chat-toggle (main.js: "Chat toggle collapse/expand"). The fork's drawer
    // owns that button entirely — it drives snap levels, not a raw class
    // toggle — so leaving both attached makes them fight on every click.
    //
    // Replacing the node with a clone drops all existing listeners without
    // editing main.js, which keeps the coupling at exactly one hook call.
    // Depends on registerForkUI() being called at the END of wireUI(), after
    // upstream has attached. Harmless if upstream ever stops attaching.
    if (dom.chatToggle?.parentNode) {
      const fresh = dom.chatToggle.cloneNode(true);
      dom.chatToggle.replaceWith(fresh);
      dom.chatToggle = fresh;
    }
    initChatWindow(dom, state);
    restored.push('chat-drawer-move-resize');
  } catch (err) {
    console.error('[fork-ui] chat drawer failed:', err);
  }

  console.log(`[fork-ui] restored: ${restored.join(', ') || 'nothing'}`);
  return { ok: true, restored };
}

// ─────────────────────────────────────────────────────────────────────────────
// 067-convergence: COMMAND | CONVERGENCE top-level tabs.
// Markup lives in index.html (#app-tabs, #home-root); the router and HomeView
// are fork-only modules that upstream's main.js never imports.
// ─────────────────────────────────────────────────────────────────────────────
function initConvergenceTab(state) {
  const homeRoot = document.getElementById('home-root');
  if (!homeRoot) {
    console.warn('[fork-ui] #home-root missing — Convergence tab not mounted');
    return;
  }
  if (!state.homeView) {
    state.homeView = new HomeView(homeRoot);
    state.homeView.mount();
  }
  state.tabRouter = createTabRouter({
    onChange: (tab) => {
      state.appTab = tab;
      if (tab === 'home' && state.homeView) {
        // Re-paint topbar from cache and refresh (do NOT call syncTopbarMetrics()
        // with no args — that clears metrics to "—").
        state.homeView.syncTopbarMetrics(state.homeView.cache?.health || null);
        state.homeView.refresh(true);
      }
      // Force a resize when returning to Command so canvas matches viewport
      if (tab === 'command') {
        window.dispatchEvent(new Event('resize'));
      }
    },
  });
  state.tabRouter.wire();
}

// ───────────────────────────────────────────────────────────────────────────
// NETCLAW TERMINAL drawer: move, resize, snap levels, persisted geometry.
// Byte-identical to fork 30e2882 main.js:3280-3696 apart from the signature
// (dom/state were closure captures there, parameters here).
// ───────────────────────────────────────────────────────────────────────────
function initChatWindow(dom, state) {
  const drawer = dom.chatDrawer;
  if (!drawer || !dom.chatToggle) return;

  const STORAGE_KEY = 'netclaw.hud.chatWindow.v1';
  const SNAP_KEY = 'netclaw.hud.chatSnap.v1';
  const header = document.getElementById('chat-header') || drawer.querySelector('.chat-header');
  let resizeHandle = document.getElementById('chat-resize');
  if (!resizeHandle) {
    resizeHandle = document.createElement('div');
    resizeHandle.id = 'chat-resize';
    resizeHandle.className = 'chat-resize-handle';
    resizeHandle.title = 'Drag to resize';
    resizeHandle.setAttribute('aria-hidden', 'true');
    drawer.appendChild(resizeHandle);
  }

  const minWDesktop = 320;
  const minH = 160;
  const collapsedH = 48;
  const SNAP_ORDER = ['collapsed', 'peek', 'expanded'];
  let expandedHeight = 320;
  /** @type {'collapsed'|'peek'|'expanded'} */
  let snapLevel = 'peek';
  let dragState = null;
  let resizeState = null;

  function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, n));
  }

  function viewport() {
    const vv = window.visualViewport;
    return {
      w: vv?.width ?? window.innerWidth,
      h: vv?.height ?? window.innerHeight,
      ox: vv?.offsetLeft ?? 0,
      oy: vv?.offsetTop ?? 0,
    };
  }

  function isCompactChrome() {
    return !!(state.mobileLayout?.isMobile?.() || state.mobileLayout?.isLandscape?.());
  }

  function minW() {
    return isCompactChrome() ? 260 : minWDesktop;
  }

  /** H010 snap heights for current viewport */
  function snapHeights() {
    const vp = viewport();
    const landscape = !!state.mobileLayout?.isLandscape?.();
    return {
      collapsed: collapsedH,
      peek: Math.max(120, Math.round(vp.h * (landscape ? 0.28 : 0.3))),
      expanded: Math.min(
        Math.round(vp.h * (landscape ? 0.48 : 0.55)),
        landscape ? 260 : 480,
      ),
    };
  }

  function toggleLabelForSnap(level) {
    if (level === 'collapsed') return '+';
    if (level === 'peek') return '□';
    return '_';
  }

  function applyGeometry({ left, top, width, height, collapsed }) {
    const vp = viewport();
    const w = clamp(width ?? (drawer.offsetWidth || 620), minW(), vp.w - 12);
    let h = height ?? (drawer.offsetHeight || 320);
    if (collapsed) {
      h = collapsedH;
    } else {
      h = clamp(h, minH, vp.h - 12);
      expandedHeight = h;
    }
    const l = clamp(left ?? vp.ox, vp.ox, Math.max(vp.ox, vp.ox + vp.w - w));
    const t = clamp(top ?? vp.oy, vp.oy, Math.max(vp.oy, vp.oy + vp.h - h));

    drawer.classList.add('chat-positioned');
    drawer.style.left = `${l}px`;
    drawer.style.top = `${t}px`;
    drawer.style.right = 'auto';
    drawer.style.bottom = 'auto';
    drawer.style.transform = 'none';
    drawer.style.width = `${w}px`;
    if (!collapsed) drawer.style.height = `${h}px`;
    else drawer.style.height = `${collapsedH}px`;
  }

  function currentGeometry() {
    const rect = drawer.getBoundingClientRect();
    return {
      left: rect.left,
      top: rect.top,
      width: rect.width,
      height: drawer.classList.contains('collapsed') ? expandedHeight : rect.height,
      collapsed: drawer.classList.contains('collapsed'),
      snap: snapLevel,
    };
  }

  function saveGeometry() {
    if (isCompactChrome()) {
      try {
        localStorage.setItem(SNAP_KEY, snapLevel);
      } catch {
        /* ignore */
      }
      return;
    }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(currentGeometry()));
    } catch {
      /* ignore */
    }
  }

  function loadGeometry() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function loadSnapLevel() {
    try {
      const s = localStorage.getItem(SNAP_KEY);
      if (SNAP_ORDER.includes(s)) return s;
    } catch {
      /* ignore */
    }
    return 'peek';
  }

  function ensurePositioned() {
    if (drawer.classList.contains('chat-positioned')) return;
    const rect = drawer.getBoundingClientRect();
    applyGeometry({
      left: rect.left,
      top: rect.top,
      width: rect.width,
      height: drawer.classList.contains('collapsed') ? expandedHeight : rect.height,
      collapsed: drawer.classList.contains('collapsed'),
    });
  }

  /** Dock as bottom sheet at a snap level (compact layouts). */
  function applySnap(level, { markUser = false } = {}) {
    if (!SNAP_ORDER.includes(level)) level = 'peek';
    snapLevel = level;
    drawer.dataset.snap = level;
    const heights = snapHeights();
    const h = heights[level];
    const collapsed = level === 'collapsed';
    drawer.classList.toggle('collapsed', collapsed);
    dom.chatToggle.textContent = toggleLabelForSnap(level);
    dom.chatToggle.title =
      level === 'collapsed'
        ? 'Expand terminal (peek)'
        : level === 'peek'
          ? 'Expand terminal (full sheet)'
          : 'Collapse terminal';

    const vp = viewport();
    const margin = state.mobileLayout?.isLandscape?.() ? 8 : 10;
    const width = Math.max(minW(), vp.w - margin * 2);
    const left = vp.ox + margin;
    const top = vp.oy + vp.h - h - margin;
    if (!collapsed) expandedHeight = h;
    applyGeometry({ left, top, width, height: h, collapsed });
    if (markUser) state.chatUserPositioned = true;
    saveGeometry();
  }

  function nearestSnap(height) {
    const heights = snapHeights();
    let best = 'peek';
    let bestDist = Infinity;
    for (const level of SNAP_ORDER) {
      const d = Math.abs(heights[level] - height);
      if (d < bestDist) {
        bestDist = d;
        best = level;
      }
    }
    return best;
  }

  function cycleSnap() {
    const idx = SNAP_ORDER.indexOf(snapLevel);
    const next = SNAP_ORDER[(idx + 1) % SNAP_ORDER.length];
    applySnap(next, { markUser: true });
  }

  /** Snap to bottom sheet when layout is mobile/landscape. */
  function applyMobileSheet(force = false) {
    if (!isCompactChrome()) return;
    if (!force && state.chatUserPositioned) {
      applySnap(snapLevel, { markUser: false });
      return;
    }
    // Landscape enter often collapses — respect that class if set by layout controller
    if (drawer.classList.contains('collapsed') && snapLevel !== 'collapsed') {
      snapLevel = 'collapsed';
    }
    applySnap(snapLevel, { markUser: false });
  }

  state.chatWindow = {
    applyMobileSheet,
    applyGeometry,
    currentGeometry,
    ensurePositioned,
    applySnap,
    cycleSnap,
  };

  // Initial geometry
  if (isCompactChrome()) {
    snapLevel = loadSnapLevel();
    // Fresh landscape auto-collapse from layout controller wins once
    if (drawer.classList.contains('collapsed')) snapLevel = 'collapsed';
    applySnap(snapLevel);
  } else {
    const saved = loadGeometry();
    if (saved && typeof saved.left === 'number' && typeof saved.top === 'number') {
      if (saved.collapsed) {
        drawer.classList.add('collapsed');
        snapLevel = 'collapsed';
        dom.chatToggle.textContent = '+';
      }
      if (typeof saved.height === 'number' && saved.height > collapsedH) {
        expandedHeight = saved.height;
        snapLevel = 'expanded';
      }
      applyGeometry(saved);
    }
  }

  // Collapse / expand — on compact, cycle snap points (H010)
  dom.chatToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    ensurePositioned();
    if (isCompactChrome()) {
      cycleSnap();
      return;
    }
    const willCollapse = !drawer.classList.contains('collapsed');
    if (willCollapse) {
      const rect = drawer.getBoundingClientRect();
      if (rect.height > collapsedH) expandedHeight = rect.height;
      drawer.classList.add('collapsed');
      snapLevel = 'collapsed';
      dom.chatToggle.textContent = '+';
      drawer.style.height = `${collapsedH}px`;
    } else {
      drawer.classList.remove('collapsed');
      snapLevel = 'expanded';
      dom.chatToggle.textContent = '_';
      drawer.style.height = `${expandedHeight}px`;
    }
    const geo = currentGeometry();
    applyGeometry({ ...geo, collapsed: drawer.classList.contains('collapsed') });
    saveGeometry();
  });

  // Drag from header
  if (header) {
    header.title = isCompactChrome()
      ? 'Drag to move · double-tap to cycle peek/expand'
      : 'Drag to move';

    header.addEventListener('pointerdown', (e) => {
      if (e.button !== 0) return;
      if (e.target.closest('button, a, input, textarea, select, .chat-header-actions')) return;
      e.preventDefault();
      ensurePositioned();
      // Expanding from collapsed via drag start on compact → peek
      if (isCompactChrome() && snapLevel === 'collapsed') {
        applySnap('peek', { markUser: true });
      }
      const rect = drawer.getBoundingClientRect();
      dragState = {
        id: e.pointerId,
        offsetX: e.clientX - rect.left,
        offsetY: e.clientY - rect.top,
        startY: e.clientY,
        startH: rect.height,
      };
      drawer.classList.add('dragging');
      header.setPointerCapture?.(e.pointerId);
    });

    header.addEventListener('pointermove', (e) => {
      if (!dragState || dragState.id !== e.pointerId) return;
      const vp = viewport();
      const w = drawer.offsetWidth;
      // On compact: vertical drag resizes toward snap; keep full width
      if (isCompactChrome()) {
        const dy = dragState.startY - e.clientY; // drag up → taller
        const nextH = clamp(dragState.startH + dy, collapsedH, Math.round(vp.h * 0.7));
        const width = Math.max(minW(), vp.w - 20);
        const left = vp.ox + 10;
        const top = vp.oy + vp.h - nextH - 10;
        drawer.classList.toggle('collapsed', nextH <= collapsedH + 8);
        drawer.style.width = `${width}px`;
        drawer.style.height = `${nextH}px`;
        drawer.style.left = `${left}px`;
        drawer.style.top = `${top}px`;
        expandedHeight = nextH;
        return;
      }
      const h = drawer.offsetHeight;
      const left = clamp(e.clientX - dragState.offsetX, vp.ox, vp.ox + vp.w - w);
      const top = clamp(e.clientY - dragState.offsetY, vp.oy, vp.oy + vp.h - h);
      drawer.style.left = `${left}px`;
      drawer.style.top = `${top}px`;
    });

    const endDrag = (e) => {
      if (!dragState || (e.pointerId != null && dragState.id !== e.pointerId)) return;
      const wasCompact = isCompactChrome();
      const endH = drawer.offsetHeight;
      dragState = null;
      drawer.classList.remove('dragging');
      state.chatUserPositioned = true;
      if (wasCompact) {
        applySnap(nearestSnap(endH), { markUser: true });
      } else {
        saveGeometry();
      }
    };
    header.addEventListener('pointerup', endDrag);
    header.addEventListener('pointercancel', endDrag);

    // Double-click / double-tap header cycles snaps on compact
    header.addEventListener('dblclick', (e) => {
      if (e.target.closest('button, .chat-header-actions')) return;
      if (!isCompactChrome()) return;
      e.preventDefault();
      cycleSnap();
    });
  }

  // Resize from corner handle
  resizeHandle.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;
    if (drawer.classList.contains('collapsed')) return;
    e.preventDefault();
    e.stopPropagation();
    ensurePositioned();
    const rect = drawer.getBoundingClientRect();
    resizeState = {
      id: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      startW: rect.width,
      startH: rect.height,
      startL: rect.left,
      startT: rect.top,
    };
    drawer.classList.add('resizing');
    resizeHandle.setPointerCapture?.(e.pointerId);
  });

  resizeHandle.addEventListener('pointermove', (e) => {
    if (!resizeState || resizeState.id !== e.pointerId) return;
    const vp = viewport();
    const width = clamp(
      resizeState.startW + (e.clientX - resizeState.startX),
      minW(),
      vp.ox + vp.w - resizeState.startL - 8,
    );
    const height = clamp(
      resizeState.startH + (e.clientY - resizeState.startY),
      minH,
      vp.oy + vp.h - resizeState.startT - 8,
    );
    drawer.style.width = `${width}px`;
    drawer.style.height = `${height}px`;
    expandedHeight = height;
  });

  const endResize = (e) => {
    if (!resizeState || (e.pointerId != null && resizeState.id !== e.pointerId)) return;
    const endH = drawer.offsetHeight;
    resizeState = null;
    drawer.classList.remove('resizing');
    state.chatUserPositioned = true;
    if (isCompactChrome()) {
      applySnap(nearestSnap(endH), { markUser: true });
    } else {
      saveGeometry();
    }
  };
  resizeHandle.addEventListener('pointerup', endResize);
  resizeHandle.addEventListener('pointercancel', endResize);

  const onVpChange = () => {
    if (isCompactChrome()) {
      applyMobileSheet(false);
      return;
    }
    if (!drawer.classList.contains('chat-positioned')) return;
    applyGeometry({ ...currentGeometry(), collapsed: drawer.classList.contains('collapsed') });
  };
  window.addEventListener('resize', onVpChange);
  window.visualViewport?.addEventListener('resize', onVpChange);
  window.visualViewport?.addEventListener('scroll', onVpChange);
}
