/**
 * H005 — last-good /api/graph snapshot for offline / degraded boot.
 * Stores only topology/config display data already returned by the HUD API
 * (no secrets). localStorage so a hard reload can still recover.
 */

const STORAGE_KEY = 'netclaw.hud.graphCache.v1';
const MAX_BYTES = 2_500_000; // soft cap — skip cache if graph is huge

/**
 * @param {object} graph
 * @returns {{ graph: object, cachedAt: string } | null}
 */
export function saveGraphCache(graph) {
  if (!graph || typeof graph !== 'object') return null;
  try {
    const payload = {
      cachedAt: new Date().toISOString(),
      graph,
    };
    const raw = JSON.stringify(payload);
    if (raw.length > MAX_BYTES) return null;
    localStorage.setItem(STORAGE_KEY, raw);
    return payload;
  } catch {
    return null;
  }
}

/**
 * @returns {{ graph: object, cachedAt: string } | null}
 */
export function loadGraphCache() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.graph || typeof parsed.graph !== 'object') return null;
    if (!parsed.cachedAt) parsed.cachedAt = null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearGraphCache() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Human-readable age for the stale banner.
 * @param {string|null} iso
 */
export function formatCacheAge(iso) {
  if (!iso) return 'unknown time';
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  const sec = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.round(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.round(sec / 3600)}h ago`;
  return new Date(t).toLocaleString();
}
