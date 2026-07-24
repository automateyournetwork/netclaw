/**
 * H004 — register the NetClaw Visual service worker when available.
 * No-op on file:// or unsupported browsers.
 */

export function registerServiceWorker() {
  if (typeof window === 'undefined') return;
  if (!('serviceWorker' in navigator)) return;
  // Only secure contexts (https / localhost)
  if (!window.isSecureContext) return;

  const register = async () => {
    try {
      const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
      // Optional: reload once when a new SW takes control (commented — less disruptive)
      reg.addEventListener('updatefound', () => {
        const worker = reg.installing;
        if (!worker) return;
        worker.addEventListener('statechange', () => {
          if (worker.state === 'installed' && navigator.serviceWorker.controller) {
            // New version ready; next visit picks it up via skipWaiting + clients.claim
            console.info('[netclaw-hud] Service worker updated');
          }
        });
      });
      return reg;
    } catch (err) {
      console.warn('[netclaw-hud] SW registration failed', err);
      return null;
    }
  };

  // After load so we don't contend with first paint
  if (document.readyState === 'complete') {
    register();
  } else {
    window.addEventListener('load', () => register(), { once: true });
  }
}
