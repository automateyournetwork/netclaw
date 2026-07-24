/**
 * Mobile / narrow / landscape layout controller for the NetClaw Visual HUD.
 * Toggles #app.mobile-layout + #app.landscape-layout, auto-collapses chrome,
 * and exposes layout helpers for chat + 3D performance tuning.
 *
 * Also wires prefers-reduced-motion → #app.reduced-motion (H002).
 */

const PHONE_MQ = '(max-width: 720px)';
const NARROW_MQ = '(max-width: 900px)';
const COARSE_MQ = '(pointer: coarse)';
/** Short landscape: phone rotated or small laptop height */
const LANDSCAPE_SHORT_MQ = '(orientation: landscape) and (max-height: 520px)';
const LANDSCAPE_MQ = '(orientation: landscape)';
const REDUCED_MOTION_MQ = '(prefers-reduced-motion: reduce)';

/**
 * @param {object} opts
 * @param {(mobile: boolean, detail: object) => void} [opts.onChange]
 */
export function createMobileLayout({ onChange } = {}) {
  const phoneMq = window.matchMedia(PHONE_MQ);
  const narrowMq = window.matchMedia(NARROW_MQ);
  const coarseMq = window.matchMedia(COARSE_MQ);
  const landscapeShortMq = window.matchMedia(LANDSCAPE_SHORT_MQ);
  const landscapeMq = window.matchMedia(LANDSCAPE_MQ);
  const reducedMotionMq = window.matchMedia(REDUCED_MOTION_MQ);

  let applied = false;
  let wasLandscape = false;

  function snapshot() {
    const phone = phoneMq.matches;
    const narrow = narrowMq.matches;
    const coarse = coarseMq.matches;
    const mobile = phone || (narrow && coarse);
    const landscapeShort = landscapeShortMq.matches;
    const landscape =
      landscapeShort || (mobile && landscapeMq.matches);
    return {
      phone,
      narrow,
      coarse,
      mobile,
      landscape,
      landscapeShort,
      reducedMotion: reducedMotionMq.matches,
    };
  }

  function isMobile() {
    return snapshot().mobile;
  }

  function isLandscape() {
    return snapshot().landscape;
  }

  function prefersReducedMotion() {
    return snapshot().reducedMotion;
  }

  function applyA11y(detail) {
    const app = document.getElementById('app');
    if (!app) return;
    app.classList.toggle('reduced-motion', !!detail.reducedMotion);
    document.documentElement.classList.toggle('reduced-motion', !!detail.reducedMotion);
  }

  function applyChromeForMobile(mobile, landscape) {
    const app = document.getElementById('app');
    if (!app) return;

    app.classList.toggle('mobile-layout', mobile);
    app.classList.toggle('landscape-layout', landscape);
    app.dataset.layout = mobile ? 'mobile' : 'desktop';
    app.dataset.orientation = landscape ? 'landscape' : 'portrait';

    // Sidebars / footer: auto-collapse on mobile so the graph is usable;
    // reopen chips become the primary way back in.
    const pairs = [
      ['sidebar-left', 'reopen-left'],
      ['sidebar-right', 'reopen-right'],
      ['footer-panel', 'reopen-footer'],
    ];

    for (const [panelId, reopenId] of pairs) {
      const panel = document.getElementById(panelId);
      const reopen = document.getElementById(reopenId);
      if (!panel || !reopen) continue;

      if (mobile || landscape) {
        if (!panel.dataset.mobileManaged) {
          panel.dataset.wasCollapsedBeforeMobile = panel.classList.contains('collapsed') ? '1' : '0';
          panel.dataset.mobileManaged = '1';
        }
        panel.classList.add('collapsed');
        reopen.classList.add('visible');
      } else if (panel.dataset.mobileManaged === '1') {
        const was = panel.dataset.wasCollapsedBeforeMobile === '1';
        panel.classList.toggle('collapsed', was);
        reopen.classList.toggle('visible', was);
        delete panel.dataset.mobileManaged;
        delete panel.dataset.wasCollapsedBeforeMobile;
      }
    }
  }

  /**
   * Suggested chat geometry for the current viewport (bottom sheet on mobile).
   * Landscape uses a shorter sheet so the graph keeps ≥50% of the short axis.
   */
  function chatSheetGeometry() {
    const vv = window.visualViewport;
    const w = vv?.width ?? window.innerWidth;
    const h = vv?.height ?? window.innerHeight;
    const offsetTop = vv?.offsetTop ?? 0;
    const offsetLeft = vv?.offsetLeft ?? 0;
    const detail = snapshot();

    if (!detail.mobile && !detail.landscape) {
      return null; // desktop keeps user/drag defaults
    }

    const margin = detail.landscape ? 8 : 10;
    const width = Math.max(260, w - margin * 2);
    // Portrait ~42% height; landscape ~28% so graph stays dominant
    const frac = detail.landscape ? 0.28 : 0.42;
    const maxH = detail.landscape ? 220 : 360;
    const height = Math.min(Math.round(h * frac), maxH);
    const left = offsetLeft + margin;
    const top = offsetTop + h - height - margin - (detail.landscape ? 4 : 8);
    return { left, top, width, height, collapsed: false };
  }

  function apply() {
    const detail = snapshot();
    applyA11y(detail);
    applyChromeForMobile(detail.mobile, detail.landscape);

    // Entering landscape: collapse terminal to header strip once (H001)
    if (detail.landscape && !wasLandscape) {
      const drawer = document.getElementById('chat-drawer');
      const toggle = document.getElementById('chat-toggle');
      if (drawer && !drawer.classList.contains('collapsed')) {
        drawer.classList.add('collapsed');
        if (toggle) toggle.textContent = '+';
      }
    }
    wasLandscape = detail.landscape;

    applied = true;
    if (typeof onChange === 'function') onChange(detail.mobile, detail);
    return detail;
  }

  function wire() {
    const handler = () => apply();
    const mqs = [phoneMq, narrowMq, coarseMq, landscapeShortMq, landscapeMq, reducedMotionMq];
    for (const mq of mqs) {
      if (mq.addEventListener) mq.addEventListener('change', handler);
      else if (mq.addListener) mq.addListener(handler);
    }

    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', handler);
      window.visualViewport.addEventListener('scroll', handler);
    }

    apply();
  }

  return {
    wire,
    apply,
    isMobile,
    isLandscape,
    prefersReducedMotion,
    snapshot,
    chatSheetGeometry,
    get applied() {
      return applied;
    },
  };
}

/** DPR cap for mobile GPUs — keeps bloom/composer usable on phones. */
export function mobilePixelRatio() {
  const dpr = window.devicePixelRatio || 1;
  const coarse = window.matchMedia(COARSE_MQ).matches;
  const phone = window.matchMedia(PHONE_MQ).matches;
  const landscapeShort = window.matchMedia(LANDSCAPE_SHORT_MQ).matches;
  if (phone || landscapeShort) return Math.min(dpr, 1.5);
  if (coarse) return Math.min(dpr, 1.75);
  return Math.min(dpr, 2);
}

/**
 * Motion-safe duration helper (H002). Returns near-zero when reduced motion is on.
 * @param {number} seconds
 * @param {() => boolean} [isReduced]
 */
export function motionDuration(seconds, isReduced) {
  const reduced =
    typeof isReduced === 'function'
      ? isReduced()
      : window.matchMedia(REDUCED_MOTION_MQ).matches;
  if (reduced) return Math.min(0.01, seconds);
  return seconds;
}
