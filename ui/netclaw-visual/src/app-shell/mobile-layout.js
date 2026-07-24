/**
 * Mobile / narrow layout controller for the NetClaw Visual HUD.
 * Toggles #app.mobile-layout, auto-collapses chrome, and exposes
 * layout helpers for chat + 3D performance tuning.
 */

const PHONE_MQ = '(max-width: 720px)';
const NARROW_MQ = '(max-width: 900px)';
const COARSE_MQ = '(pointer: coarse)';

/**
 * @param {object} opts
 * @param {(mobile: boolean, detail: { phone: boolean, narrow: boolean, coarse: boolean }) => void} [opts.onChange]
 */
export function createMobileLayout({ onChange } = {}) {
  const phoneMq = window.matchMedia(PHONE_MQ);
  const narrowMq = window.matchMedia(NARROW_MQ);
  const coarseMq = window.matchMedia(COARSE_MQ);

  let applied = false;

  function snapshot() {
    return {
      phone: phoneMq.matches,
      narrow: narrowMq.matches,
      coarse: coarseMq.matches,
      mobile: phoneMq.matches || (narrowMq.matches && coarseMq.matches),
    };
  }

  function isMobile() {
    return snapshot().mobile;
  }

  function applyChromeForMobile(mobile) {
    const app = document.getElementById('app');
    if (!app) return;

    app.classList.toggle('mobile-layout', mobile);
    app.dataset.layout = mobile ? 'mobile' : 'desktop';

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

      if (mobile) {
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
   */
  function chatSheetGeometry() {
    const vv = window.visualViewport;
    const w = vv?.width ?? window.innerWidth;
    const h = vv?.height ?? window.innerHeight;
    const offsetTop = vv?.offsetTop ?? 0;
    const offsetLeft = vv?.offsetLeft ?? 0;
    const mobile = isMobile();

    if (!mobile) {
      return null; // desktop keeps user/drag defaults
    }

    const margin = 10;
    const width = Math.max(280, w - margin * 2);
    const height = Math.min(Math.round(h * 0.42), 360);
    const left = offsetLeft + margin;
    // Sit above home-indicator / footer chip band
    const top = offsetTop + h - height - margin - 8;
    return { left, top, width, height, collapsed: false };
  }

  function apply() {
    const detail = snapshot();
    applyChromeForMobile(detail.mobile);
    applied = true;
    if (typeof onChange === 'function') onChange(detail.mobile, detail);
    return detail;
  }

  function wire() {
    const handler = () => apply();
    // Safari still needs addListener in some older WebViews
    for (const mq of [phoneMq, narrowMq, coarseMq]) {
      if (mq.addEventListener) mq.addEventListener('change', handler);
      else if (mq.addListener) mq.addListener(handler);
    }

    // iOS keyboard / URL bar show-hide
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
  if (phone) return Math.min(dpr, 1.5);
  if (coarse) return Math.min(dpr, 1.75);
  return Math.min(dpr, 2);
}
