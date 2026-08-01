/**
 * 080-convergence — top-level COMMAND | HOME tab router.
 * Keeps Three.js mounted; toggles visibility + app mode class.
 */

export function createTabRouter({ onChange } = {}) {
  let current = 'command';

  const commandChrome = () => [
    document.getElementById('sidebar-left'),
    document.getElementById('sidebar-right'),
    document.getElementById('topbar-stats-command'),
  ];

  function setTab(tab) {
    if (tab !== 'command' && tab !== 'home') return current;
    current = tab;
    const app = document.getElementById('app');
    const homeRoot = document.getElementById('home-root');
    const statsHome = document.getElementById('topbar-stats-home');
    const statsCmd = document.getElementById('topbar-stats-command');

    document.querySelectorAll('.app-tab').forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.appTab === tab);
    });

    const isHome = tab === 'home';
    app?.classList.toggle('home-mode', isHome);

    if (homeRoot) {
      homeRoot.classList.toggle('hidden', !isHome);
      homeRoot.setAttribute('aria-hidden', isHome ? 'false' : 'true');
    }
    if (statsHome) statsHome.classList.toggle('hidden', !isHome);
    if (statsCmd) statsCmd.classList.toggle('hidden', isHome);

    // Sidebars are command-only; ensure reopen chips hide in home mode via CSS
    commandChrome().forEach((el) => {
      if (!el) return;
      if (isHome) {
        el.dataset.wasCollapsed = el.classList.contains('collapsed') ? '1' : '0';
      }
    });

    if (typeof onChange === 'function') onChange(tab);
    return current;
  }

  function wire() {
    document.querySelectorAll('.app-tab').forEach((btn) => {
      btn.addEventListener('click', () => setTab(btn.dataset.appTab));
    });
    setTab(current);
  }

  return {
    get tab() {
      return current;
    },
    setTab,
    wire,
    isHome: () => current === 'home',
  };
}
