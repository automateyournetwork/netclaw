/**
 * Make a panel draggable, resizable and remembered.
 *
 * Extracted rather than reusing initChatWindow(): that carries snap levels and
 * mobile-sheet behaviour specific to the chat drawer, and its body is kept
 * byte-identical to pre-merge history so it stays diffable. This is the smaller
 * shared case — move, resize, clamp, persist — with no opinion about content.
 *
 * Pointer events throughout, so touch and pen work without a second code path.
 *
 *   const win = makeFloating(panelEl, {
 *     handle:       panelEl.querySelector('.tp-head'),
 *     grip:         panelEl.querySelector('.tp-resize'),
 *     storageKey:   'netclaw.terminal.geometry',
 *     minWidth: 420, minHeight: 220,
 *     onResize:     () => refit(),
 *   });
 *   win.destroy();
 */

const MARGIN = 8; // keep this much of the panel on screen

function readGeometry(key) {
  if (!key) return null;
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const g = JSON.parse(raw);
    return ['left', 'top', 'width', 'height'].every((k) => Number.isFinite(g?.[k])) ? g : null;
  } catch {
    return null;
  }
}

function writeGeometry(key, g) {
  if (!key) return;
  try {
    localStorage.setItem(key, JSON.stringify(g));
  } catch {
    /* non-fatal — geometry just won't persist */
  }
}

const clamp = (n, lo, hi) => Math.min(Math.max(n, lo), hi);

export function makeFloating(el, opts = {}) {
  const {
    handle = el,
    grip = null,
    storageKey = null,
    minWidth = 320,
    minHeight = 180,
    onResize = null,
  } = opts;

  if (!el) return { destroy() {} };

  const listeners = [];
  const on = (target, type, fn, o) => {
    target.addEventListener(type, fn, o);
    listeners.push(() => target.removeEventListener(type, fn, o));
  };

  let maximized = false;
  let preMaximize = null;

  const vw = () => window.innerWidth;
  const vh = () => window.innerHeight;

  /** Apply geometry, clamped so the panel can never be dragged off-screen. */
  function place({ left, top, width, height }) {
    const w = clamp(width, minWidth, Math.max(minWidth, vw() - MARGIN * 2));
    const h = clamp(height, minHeight, Math.max(minHeight, vh() - MARGIN * 2));
    // Keep at least MARGIN of the panel reachable on every edge.
    const l = clamp(left, MARGIN - w + 60, vw() - 60);
    const t = clamp(top, MARGIN, vh() - 40);

    el.style.left = `${Math.round(l)}px`;
    el.style.top = `${Math.round(t)}px`;
    el.style.right = 'auto';
    el.style.bottom = 'auto';
    el.style.width = `${Math.round(w)}px`;
    el.style.height = `${Math.round(h)}px`;
    el.classList.add('is-floating');
    return { left: l, top: t, width: w, height: h };
  }

  function current() {
    const r = el.getBoundingClientRect();
    return { left: r.left, top: r.top, width: r.width, height: r.height };
  }

  function persist() {
    if (!maximized) writeGeometry(storageKey, current());
  }

  // Restore, or adopt whatever CSS laid out so the first drag does not jump.
  const saved = readGeometry(storageKey);
  place(saved || current());
  if (onResize) onResize();

  // ── drag ────────────────────────────────────────────────────────────────
  let drag = null;
  on(handle, 'pointerdown', (ev) => {
    // Never start a drag from a control inside the title bar.
    if (ev.target.closest('button, a, input, select, textarea, [data-no-drag]')) return;
    if (ev.button !== 0 || maximized) return;
    const g = current();
    drag = { dx: ev.clientX - g.left, dy: ev.clientY - g.top, w: g.width, h: g.height };
    handle.setPointerCapture?.(ev.pointerId);
    el.classList.add('is-dragging');
    ev.preventDefault();
  });
  on(handle, 'pointermove', (ev) => {
    if (!drag) return;
    place({
      left: ev.clientX - drag.dx,
      top: ev.clientY - drag.dy,
      width: drag.w,
      height: drag.h,
    });
  });
  const endDrag = () => {
    if (!drag) return;
    drag = null;
    el.classList.remove('is-dragging');
    persist();
  };
  on(handle, 'pointerup', endDrag);
  on(handle, 'pointercancel', endDrag);

  // ── resize ──────────────────────────────────────────────────────────────
  let sizing = null;
  if (grip) {
    on(grip, 'pointerdown', (ev) => {
      if (ev.button !== 0 || maximized) return;
      const g = current();
      sizing = { x: ev.clientX, y: ev.clientY, ...g };
      grip.setPointerCapture?.(ev.pointerId);
      el.classList.add('is-resizing');
      ev.preventDefault();
      ev.stopPropagation();
    });
    on(grip, 'pointermove', (ev) => {
      if (!sizing) return;
      place({
        left: sizing.left,
        top: sizing.top,
        width: sizing.width + (ev.clientX - sizing.x),
        height: sizing.height + (ev.clientY - sizing.y),
      });
      if (onResize) onResize();
    });
    const endSize = () => {
      if (!sizing) return;
      sizing = null;
      el.classList.remove('is-resizing');
      persist();
      if (onResize) onResize();
    };
    on(grip, 'pointerup', endSize);
    on(grip, 'pointercancel', endSize);
  }

  // ── maximize ────────────────────────────────────────────────────────────
  function setMaximized(next) {
    if (next === maximized) return;
    if (next) {
      preMaximize = current();
      maximized = true;
      el.classList.add('is-maximized');
      el.style.left = `${MARGIN}px`;
      el.style.top = `${MARGIN}px`;
      el.style.width = `${vw() - MARGIN * 2}px`;
      el.style.height = `${vh() - MARGIN * 2}px`;
    } else {
      maximized = false;
      el.classList.remove('is-maximized');
      place(preMaximize || current());
      persist();
    }
    if (onResize) onResize();
  }

  // Double-clicking the title bar toggles maximize, as it has since Windows 3.
  on(handle, 'dblclick', (ev) => {
    if (ev.target.closest('button, a, input, select, textarea')) return;
    setMaximized(!maximized);
  });

  // Keep the panel on screen when the viewport changes.
  on(window, 'resize', () => {
    if (maximized) {
      el.style.width = `${vw() - MARGIN * 2}px`;
      el.style.height = `${vh() - MARGIN * 2}px`;
    } else {
      place(current());
    }
    if (onResize) onResize();
  });

  return {
    place,
    persist,
    isMaximized: () => maximized,
    toggleMaximize: () => setMaximized(!maximized),
    destroy() {
      listeners.forEach((off) => off());
      listeners.length = 0;
    },
  };
}
