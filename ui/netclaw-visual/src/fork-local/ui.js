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
 *     1. The draggable / resizable NETCLAW TERMINAL drawer (initChatWindow,
 *        ~417 lines, including persisted geometry and snap levels).
 *     2. The footer token/cost strip and the ${VAR} model readout.
 *
 *   The COMMAND | CONVERGENCE tab router used to live here too. It has since
 *   moved to modules/convergence/, which owns its own tab button, container and
 *   stylesheet — see modules/README.md. What remains here is general HUD repair,
 *   not a module: it fixes first-party chrome rather than adding a feature.
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


const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
));

export function registerForkUI(ctx) {
  const { dom, state } = ctx || {};
  if (!dom || !state) {
    console.error('[fork-ui] registerForkUI needs { dom, state } — skipping');
    return { ok: false, restored: [] };
  }

  const restored = [];

  try {
    initTokenStrip();
    restored.push('footer-token-strip');
  } catch (err) {
    console.error('[fork-ui] token strip failed:', err);
  }

  try {
    initModelReadout();
    restored.push('model-readout');
  } catch (err) {
    console.error('[fork-ui] model readout failed:', err);
  }

  try {
    initDeviceLauncher();
    restored.push('device-launcher');
  } catch (err) {
    console.error('[fork-ui] device launcher failed:', err);
  }

  try {
    initTerminalProvider();
    restored.push('terminal-provider');
  } catch (err) {
    console.error('[fork-ui] terminal provider failed:', err);
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
// Device launcher — the entry point for the SSH terminal.
//
// The terminal button was originally added to setDetail('device'), which fires
// when a device node is clicked in the 3D scene. That path is dead in HUD 2.0:
// state.devices is initialised to [] and nothing ever populates it, because
// buildDevices() was one of the fork functions the merge dropped. The right
// sidebar's Focus → Devices button therefore hides the integrations and reveals
// nothing at all.
//
// Resurrecting the old 3D device nodes is the wrong fix — they used HUD 1.0's
// orbit/dendrite coordinate system and would fight the org chart renderer. So
// devices get a list in the Devices focus view instead, which is where an
// operator already expects to find them.
//
// The listener is additive: upstream's own .segmented-btn handler still runs and
// still sets state.filters.view / applyFilters(). We only paint the panel.
// ─────────────────────────────────────────────────────────────────────────────
function initDeviceLauncher() {
  const buttons = document.querySelectorAll('.segmented-btn');
  if (!buttons.length) return;
  buttons.forEach((btn) => {
    btn.addEventListener('click', () => {
      if (btn.dataset.view === 'devices') renderDeviceList();
    });
  });
}

async function renderDeviceList() {
  const panel = document.getElementById('detail-panel');
  if (!panel) return;
  panel.innerHTML = '<h2>Devices</h2><p>Loading testbed…</p>';

  let devices = [];
  let caps = null;
  try {
    const [g, c] = await Promise.all([
      fetch('/api/graph').then((r) => r.json()),
      fetch('/api/ssh/capabilities').then((r) => r.json()).catch(() => null),
    ]);
    devices = g.devices || [];
    caps = c;
  } catch (err) {
    panel.innerHTML = `<h2>Devices</h2><p class="config-notes">Could not load: ${esc(err.message)}</p>`;
    return;
  }

  if (!devices.length) {
    panel.innerHTML = '<h2>Devices</h2><p class="config-notes">No devices in testbed/testbed.yaml.</p>';
    return;
  }

  const sshOff = !caps?.enabled;
  const warnPriv15 = caps?.enabled && !caps?.dedicatedAccount;

  const rows = devices.map((d) => {
    const canSsh = String(d.protocol || '').toLowerCase() === 'ssh';
    const id = `dev-term-${d.id}`;
    return `
      <div class="info-card" style="margin-bottom:6px">
        <div class="eyebrow">${esc(d.type)} · ${esc(d.os)}</div>
        <strong>${esc(d.name)}</strong>
        ${canSsh
    ? `<button class="segmented-btn" data-device="${esc(d.name)}" id="${id}"
                 style="margin-top:6px;width:100%"${sshOff ? ' disabled' : ''}>
             ${sshOff ? 'Terminal disabled' : 'Open SSH terminal'}
           </button>`
    : '<p class="config-notes">No SSH connection defined.</p>'}
      </div>`;
  }).join('');

  panel.innerHTML = `
    <h2>Devices</h2>
    <p class="config-notes">${devices.length} in testbed/testbed.yaml.</p>
    ${sshOff
    ? '<p class="config-notes">Terminal is off. Set <code>HUD_SSH_ENABLED=1</code> and restart the HUD. See docs/SSH-TERMINAL-HARDENING.md.</p>'
    : ''}
    ${warnPriv15
    ? '<p class="config-notes" style="color:#fbbf5c">Using privilege-15 credentials — the app filter is the only guard. Set HUD_SSH_USERNAME to a privilege-1 account.</p>'
    : ''}
    ${rows}`;

  panel.querySelectorAll('button[data-device]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const name = btn.dataset.device;
      btn.disabled = true;
      const original = btn.textContent;
      btn.textContent = 'Opening…';
      try {
        const mod = await import('../panels/TerminalPanel.js');
        await mod.openTerminalPanel(name);
      } catch (err) {
        btn.textContent = `Failed: ${err.message}`;
        return;
      } finally {
        if (btn.textContent === 'Opening…') btn.textContent = original;
        btn.disabled = false;
      }
    });
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Terminal provider.
//
// Answers the `netclaw:open-terminal` event so callers never import the panel
// directly. modules/convergence/ uses this from its device table: it dispatches
// and waits for an ack, which keeps the two decoupled — Convergence works with
// no terminal present, and the terminal works with no Convergence.
//
// When the SSH terminal becomes its own module, this listener moves there and
// nothing else has to change. That is the point of the event.
// ─────────────────────────────────────────────────────────────────────────────
function initTerminalProvider() {
  window.addEventListener('netclaw:open-terminal', async (ev) => {
    const device = ev.detail?.device;
    const ack = typeof ev.detail?.ack === 'function' ? ev.detail.ack : () => {};
    if (!device) return ack(false);
    try {
      const mod = await import('../panels/TerminalPanel.js');
      await mod.openTerminalPanel(device);
      return ack(true);
    } catch (err) {
      console.error('[fork-ui] terminal failed to open:', err);
      return ack(false);
    }
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Footer token/cost strip.
//
// index.html carries #footer-tokens-{lifetime,last,opt,top}, but upstream's
// main.js never touches any of them — the wiring was fork-only, which is why
// they sit at "—". (It is also why /api/tokens/summary appeared to have no
// consumer after the merge: its consumer had been deleted along with it.)
//
// Lifetime / opt / top come from the exporter and need nothing else. `lastTurn`
// depends on upstream's /api/chat surfacing a usage block — see the FORK PATCH
// in server.js. Refresh is on a timer here rather than piggy-backing on the
// gateway probe (which is upstream's and not ours to hook).
// ─────────────────────────────────────────────────────────────────────────────
function formatTokenCount(n) {
  if (n == null || Number.isNaN(n)) return '—';
  const v = Number(n);
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}k`;
  return String(Math.round(v));
}

async function refreshTokenSummary() {
  const el = {
    lifetime: document.getElementById('footer-tokens-lifetime'),
    last: document.getElementById('footer-tokens-last'),
    opt: document.getElementById('footer-tokens-opt'),
    top: document.getElementById('footer-tokens-top'),
  };
  if (!el.lifetime && !el.last && !el.opt && !el.top) return;

  try {
    const res = await fetch('/api/tokens/summary');
    const data = await res.json();

    if (el.lifetime) {
      el.lifetime.textContent = data.lifetime
        ? `${formatTokenCount(data.lifetime.input)} in / ${formatTokenCount(data.lifetime.output)} out · ${formatTokenCount(data.lifetime.calls)} calls`
        : (data.exporterError ? `exporter offline (${data.exporterError})` : '—');
    }
    if (el.last) {
      el.last.textContent = data.lastTurn
        ? `${formatTokenCount(data.lastTurn.input)} in / ${formatTokenCount(data.lastTurn.output)} out`
        : '—';
    }
    if (el.opt) {
      const on = data.tokenOptimization?.enabled;
      const gcf = data.tokenOptimization?.gcfSerializationDefault;
      el.opt.textContent = on ? `ON${gcf ? ' · GCF' : ''}` : 'OFF';
      el.opt.style.color = on ? 'var(--ok)' : '#ff7b54';
    }
    if (el.top) {
      const top = (data.topModels || [])[0];
      el.top.textContent = top
        ? `top: ${top.model} (${formatTokenCount(top.input)} in)`
        : '';
    }
  } catch {
    if (el.lifetime) el.lifetime.textContent = '—';
  }
}

function initTokenStrip() {
  refreshTokenSummary();
  const t = setInterval(refreshTokenSummary, 15000);
  if (typeof window !== 'undefined') window.addEventListener('beforeunload', () => clearInterval(t));
}

// ─────────────────────────────────────────────────────────────────────────────
// Model readout: resolve ${VAR} references for display.
//
// openclaw.json stores the model as "${NETCLAW_BRAIN_MODEL}". Upstream renders
// that string verbatim into both the footer and the PRIMARY MODEL sidebar card,
// so operators see the template instead of the model. The fork resolved it
// server-side in buildSettings() via resolveEnvTemplates() + displayModelId(),
// both of which the merge dropped.
//
// Fixed client-side instead of re-patching upstream's buildGraph: the restored
// /api/models endpoint already reports resolved values. Deliberately a small
// explicit token map, NOT a general env-resolution endpoint — the config also
// contains "${OPENCLAW_GATEWAY_TOKEN}", and an endpoint that resolved arbitrary
// ${VAR} for the browser would hand out the gateway token.
//
// A MutationObserver re-applies after every graph refresh, since renderMetrics()
// rewrites both targets from the raw payload each time.
// ─────────────────────────────────────────────────────────────────────────────
const MODEL_TOKENS = [
  ['NETCLAW_BRAIN_MODEL', (m) => m.live?.defaultsPrimary || m.sot?.brain],
  ['NETCLAW_ALERT_TRIAGE_MODEL', (m) => m.sot?.alert],
  ['NETCLAW_ALERT_FALLBACK_MODEL', (m) => m.sot?.fallback],
];

/** anthropic/claude-sonnet-5 → claude-sonnet-5, matching the old displayModelId. */
function shortModelId(raw) {
  const s = String(raw ?? '').trim();
  if (!s) return '';
  return s.replace(/^[a-z0-9._-]+\//i, '');
}

async function initModelReadout() {
  let models = null;
  try {
    const res = await fetch('/api/models');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    models = await res.json();
  } catch (err) {
    // /api/models is gated by requireTrustedClient; an untrusted viewer just
    // keeps seeing the raw template rather than getting a broken readout.
    console.warn('[fork-ui] model readout unavailable:', err.message);
    return;
  }

  const map = new Map();
  for (const [name, pick] of MODEL_TOKENS) {
    const val = pick(models);
    if (val) map.set(name, shortModelId(val));
  }
  if (!map.size) return;

  const resolve = (text) => String(text ?? '').replace(
    /\$\{([A-Za-z_][A-Za-z0-9_]*)\}/g,
    (match, name) => map.get(name) ?? match,
  );

  const apply = () => {
    const footer = document.getElementById('footer-model');
    if (footer && footer.textContent.includes('${')) {
      footer.textContent = resolve(footer.textContent);
    }
    // PRIMARY MODEL / FALLBACK MODELS cards in the left sidebar.
    document.querySelectorAll('#settings-list .info-card').forEach((card) => {
      const strong = card.querySelector('strong');
      if (strong && strong.textContent.includes('${')) {
        strong.textContent = resolve(strong.textContent);
      }
    });
  };

  apply();

  const settings = document.getElementById('settings-list');
  if (settings) {
    new MutationObserver(apply).observe(settings, { childList: true, subtree: true });
  }
  const footer = document.getElementById('footer-model');
  if (footer) {
    new MutationObserver(apply).observe(footer, { childList: true, characterData: true, subtree: true });
  }
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
