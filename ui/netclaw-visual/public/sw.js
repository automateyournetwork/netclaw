/**
 * NetClaw Visual HUD — minimal service worker (H004 / H005).
 *
 * Precaches app shell after install. For /api/graph: network-first, then
 * last good snapshot (no secrets). Other /api/* always network-only.
 * Does NOT cache chat, websocket, or env/credential endpoints.
 */
/* eslint-disable no-restricted-globals */

// Bump SHELL_CACHE when shipping UI fixes so navigations don't stick on stale index.html
const SHELL_CACHE = 'netclaw-hud-shell-v2';
const GRAPH_CACHE = 'netclaw-hud-graph-v1';
const GRAPH_URL_PATH = '/api/graph';

const SHELL_URLS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon-maskable-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      // Best-effort precache — hashed Vite assets are learned on first visit
      await Promise.all(
        SHELL_URLS.map(async (url) => {
          try {
            const res = await fetch(url, { cache: 'no-cache' });
            if (res.ok) await cache.put(url, res.clone());
          } catch {
            /* offline during install */
          }
        }),
      );
      self.skipWaiting();
    })(),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keep = new Set([SHELL_CACHE, GRAPH_CACHE]);
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => !keep.has(k)).map((k) => caches.delete(k)));
      await self.clients.claim();
    })(),
  );
});

function isGraphRequest(url) {
  try {
    const u = new URL(url);
    return u.pathname === GRAPH_URL_PATH || u.pathname.endsWith(GRAPH_URL_PATH);
  } catch {
    return false;
  }
}

function isApiRequest(url) {
  try {
    return new URL(url).pathname.startsWith('/api/');
  } catch {
    return false;
  }
}

async function networkFirstGraph(request) {
  const cache = await caches.open(GRAPH_CACHE);
  try {
    const fresh = await fetch(request);
    if (fresh.ok) {
      // Store a copy; strip auth-ish headers by reconstructing JSON body only
      const data = await fresh.clone().json();
      const body = JSON.stringify(data);
      const stored = new Response(body, {
        status: 200,
        statusText: 'OK',
        headers: {
          'Content-Type': 'application/json',
          'X-NetClaw-Graph-Cache': 'network',
          'X-NetClaw-Graph-Cached-At': new Date().toISOString(),
        },
      });
      await cache.put(GRAPH_URL_PATH, stored.clone());
      return fresh;
    }
    throw new Error(`graph ${fresh.status}`);
  } catch {
    const cached = await cache.match(GRAPH_URL_PATH);
    if (cached) {
      const headers = new Headers(cached.headers);
      headers.set('X-NetClaw-Graph-Cache', 'stale');
      const buf = await cached.arrayBuffer();
      return new Response(buf, {
        status: 200,
        statusText: 'OK (stale)',
        headers,
      });
    }
    return new Response(JSON.stringify({ error: 'graph unavailable offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/** Network-first for HTML so tab/metric JS fixes ship without a manual cache wipe. */
async function networkFirstNavigate(request) {
  const cache = await caches.open(SHELL_CACHE);
  try {
    const fresh = await fetch(request, { cache: 'no-cache' });
    if (fresh.ok) {
      cache.put(request, fresh.clone());
      // Also refresh bare index entries used as offline fallback
      try {
        const u = new URL(request.url);
        if (u.pathname === '/' || u.pathname.endsWith('/index.html')) {
          cache.put('/index.html', fresh.clone());
          cache.put('/', fresh.clone());
        }
      } catch {
        /* ignore */
      }
    }
    return fresh;
  } catch {
    const cached =
      (await cache.match(request, { ignoreSearch: true })) ||
      (await cache.match('/index.html')) ||
      (await cache.match('/'));
    if (cached) return cached;
    return new Response('NetClaw Visual offline', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}

async function cacheFirstShell(request) {
  const cache = await caches.open(SHELL_CACHE);
  const cached = await cache.match(request, { ignoreSearch: true });
  if (cached) {
    // Revalidate in background
    fetch(request)
      .then((res) => {
        if (res.ok) cache.put(request, res.clone());
      })
      .catch(() => {});
    return cached;
  }
  try {
    const fresh = await fetch(request);
    if (fresh.ok && request.method === 'GET') {
      // Cache same-origin static assets (including hashed /assets/*)
      const url = new URL(request.url);
      if (url.origin === self.location.origin && !isApiRequest(request.url)) {
        cache.put(request, fresh.clone());
      }
    }
    return fresh;
  } catch {
    // Offline navigation fallback
    const fallback = (await cache.match('/')) || (await cache.match('/index.html'));
    if (fallback) return fallback;
    return new Response('NetClaw Visual offline', {
      status: 503,
      headers: { 'Content-Type': 'text/plain' },
    });
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = request.url;
  if (isGraphRequest(url)) {
    event.respondWith(networkFirstGraph(request));
    return;
  }
  if (isApiRequest(url)) {
    // Never cache other APIs (home, chat proxies, credentials)
    return;
  }
  // Navigations: always prefer network so UI fixes (topbar metrics) apply quickly
  if (request.mode === 'navigate' || request.destination === 'document') {
    event.respondWith(networkFirstNavigate(request));
    return;
  }
  if (request.destination === 'script' || request.destination === 'style' || request.destination === 'image' || request.destination === 'font') {
    event.respondWith(cacheFirstShell(request));
  }
});

self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
