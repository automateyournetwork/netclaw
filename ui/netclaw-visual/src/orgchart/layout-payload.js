/**
 * Saved-layout payload: shape, validation, camera clamping (feature 102, US3 —
 * FR-018, FR-019, FR-033, FR-034, FR-047, FR-048).
 *
 * Pure: no imports beyond presets (also pure), no clock, no fs, no DOM.
 *
 * **Deliberately shared between client and server.** One implementation defines the
 * contract, so the browser cannot construct a payload the server would reject, and
 * the server cannot accept one the browser would not have produced. A second
 * validator on the server would drift from this one within a release.
 *
 * The write gate matters more here than in most places: this is the HUD's first
 * persistent client state, and `server.js` has a global `express.json({limit:'4mb'})`
 * that is far too permissive for a layout file (research R5). The bounds below are
 * per-route and are not allowed to rely on that global.
 */

import { PRESETS, isPresetId } from './presets.js';

export const SCHEMA_VERSION = 1;

export const LIMITS = {
  maxNodeIdLength: 128,
  maxCoordinate: 10000,
  maxEntriesPerPreset: 500,   // scene is ~40; generous and still bounded
  maxBytes: 256 * 1024,
};

/** Camera bounds mirror feature 072's camera.js constants (FR-047). */
export const CAMERA_BOUNDS = { minZoom: 0.35, maxZoom: 6 };

const TOP_LEVEL_KEYS = new Set([
  'version', 'savedAt', 'activePreset', 'positions', 'pinned', 'camera',
]);

/** Node ids are map keys only and MUST never be usable as a path component (FR-034). */
function validNodeId(id) {
  return typeof id === 'string'
    && id.length > 0
    && id.length <= LIMITS.maxNodeIdLength
    && !id.includes('/') && !id.includes('\\')
    && !id.includes('..')
    && !id.includes('\0');
}

function validCoord(v) {
  // NaN and Infinity propagate into three.js as invisible geometry corruption
  // rather than an error, so they are rejected here where they are still visible.
  return Number.isFinite(v) && Math.abs(v) <= LIMITS.maxCoordinate;
}

function validVec(p) {
  return !!p && typeof p === 'object'
    && validCoord(p.x) && validCoord(p.y) && validCoord(p.z);
}

/**
 * Validate a payload. Returns `{ ok: true }` or `{ ok: false, error }` with a
 * SPECIFIC reason — "positions.ring: 812 entries exceeds 500" beats "invalid
 * payload", because the operator has to be able to act on it.
 *
 * @param {*} payload
 * @returns {{ok: boolean, error?: string}}
 */
export function validateLayout(payload) {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    return { ok: false, error: 'payload must be an object' };
  }

  // Unknown keys are REJECTED, not ignored. Silent acceptance of junk is how a
  // schema rots, and it is also how unexpected data ends up persisted.
  for (const k of Object.keys(payload)) {
    if (!TOP_LEVEL_KEYS.has(k)) return { ok: false, error: `unknown top-level key '${k}'` };
  }

  if (payload.version !== SCHEMA_VERSION) {
    return { ok: false, error: `unsupported version ${payload.version} (expected ${SCHEMA_VERSION})` };
  }

  if (payload.activePreset !== undefined && !isPresetId(payload.activePreset)) {
    return { ok: false, error: `unknown activePreset '${payload.activePreset}'` };
  }

  if (payload.positions !== undefined) {
    if (typeof payload.positions !== 'object' || payload.positions === null) {
      return { ok: false, error: 'positions must be an object' };
    }
    for (const [preset, map] of Object.entries(payload.positions)) {
      if (!isPresetId(preset)) return { ok: false, error: `positions: unknown preset '${preset}'` };
      if (typeof map !== 'object' || map === null) {
        return { ok: false, error: `positions.${preset} must be an object` };
      }
      const entries = Object.entries(map);
      if (entries.length > LIMITS.maxEntriesPerPreset) {
        return {
          ok: false,
          error: `positions.${preset}: ${entries.length} entries exceeds ${LIMITS.maxEntriesPerPreset}`,
        };
      }
      for (const [id, vec] of entries) {
        if (!validNodeId(id)) return { ok: false, error: `positions.${preset}: invalid node id` };
        if (!validVec(vec)) {
          return { ok: false, error: `positions.${preset}.${id}: coordinates must be finite and within ±${LIMITS.maxCoordinate}` };
        }
      }
    }
  }

  if (payload.pinned !== undefined) {
    if (typeof payload.pinned !== 'object' || payload.pinned === null) {
      return { ok: false, error: 'pinned must be an object' };
    }
    for (const [preset, ids] of Object.entries(payload.pinned)) {
      if (!isPresetId(preset)) return { ok: false, error: `pinned: unknown preset '${preset}'` };
      if (!Array.isArray(ids)) return { ok: false, error: `pinned.${preset} must be an array` };
      if (ids.length > LIMITS.maxEntriesPerPreset) {
        return { ok: false, error: `pinned.${preset}: ${ids.length} entries exceeds ${LIMITS.maxEntriesPerPreset}` };
      }
      for (const id of ids) {
        if (!validNodeId(id)) return { ok: false, error: `pinned.${preset}: invalid node id` };
      }
    }
  }

  if (payload.camera !== undefined && payload.camera !== null) {
    const c = payload.camera;
    if (!validVec({ ...c.position, z: c.position?.z })) {
      return { ok: false, error: 'camera.position must be finite coordinates' };
    }
    if (!validVec({ ...c.target, z: c.target?.z })) {
      return { ok: false, error: 'camera.target must be finite coordinates' };
    }
    if (!Number.isFinite(c.zoom)) return { ok: false, error: 'camera.zoom must be finite' };
  }

  const size = JSON.stringify(payload).length;
  if (size > LIMITS.maxBytes) {
    return { ok: false, error: `payload ${size} bytes exceeds ${LIMITS.maxBytes}` };
  }

  return { ok: true };
}

/**
 * Clamp a restored camera into feature 072's configured range (FR-047).
 *
 * 072 constrained the camera deliberately so the hierarchy always reads; a saved
 * layout must not become a way around that. Returns null for an unusable pose so
 * the caller falls back to framing the chart (FR-048).
 */
export function clampCamera(camera) {
  if (!camera || typeof camera !== 'object') return null;
  const { position, target, zoom } = camera;
  if (!validVec(position) || !validVec(target) || !Number.isFinite(zoom)) return null;
  return {
    position: { ...position },
    target: { ...target },
    zoom: Math.min(CAMERA_BOUNDS.maxZoom, Math.max(CAMERA_BOUNDS.minZoom, zoom)),
  };
}

/**
 * Build the payload from a store. **Geometry and identifiers only** (FR-018) — this
 * function is the reason SC-008 can be asserted on the emitted object rather than on
 * a promise about the serializer.
 */
export function toPayload(store, nowIso) {
  const positions = {};
  const pinned = {};
  for (const p of PRESETS) {
    const map = store.positions?.[p] || {};
    if (Object.keys(map).length) positions[p] = map;
    const pins = [...(store.pinned?.[p] || [])].sort();
    if (pins.length) pinned[p] = pins;
  }
  const payload = { version: SCHEMA_VERSION, activePreset: store.activePreset };
  if (nowIso) payload.savedAt = nowIso;
  if (Object.keys(positions).length) payload.positions = positions;
  if (Object.keys(pinned).length) payload.pinned = pinned;
  if (store.camera) payload.camera = store.camera;
  return payload;
}

/**
 * Apply a saved payload onto a fresh store (FR-016).
 *
 * Tolerant by design: ids that no longer exist are dropped, and ids the payload does
 * not mention simply keep their computed position because the map is sparse. Neither
 * case is an error — a member enrolling or leaving between save and restore is
 * normal, not corruption.
 *
 * @returns {{store: object, dropped: string[]}}
 */
export function applyPayload(store, payload, knownNodeIds) {
  const known = knownNodeIds ? new Set(knownNodeIds) : null;
  const dropped = [];

  if (isPresetId(payload?.activePreset)) store.activePreset = payload.activePreset;

  for (const [preset, map] of Object.entries(payload?.positions || {})) {
    if (!isPresetId(preset)) continue;
    for (const [id, vec] of Object.entries(map)) {
      if (known && !known.has(id)) { dropped.push(id); continue; }
      if (validVec(vec)) store.positions[preset][id] = { x: vec.x, y: vec.y, z: vec.z };
    }
  }

  for (const [preset, ids] of Object.entries(payload?.pinned || {})) {
    if (!isPresetId(preset)) continue;
    for (const id of ids) {
      if (known && !known.has(id)) { dropped.push(id); continue; }
      store.pinned[preset].add(id);
    }
  }

  store.camera = clampCamera(payload?.camera);
  store.dirty = false;   // a freshly restored layout is not unsaved
  return { store, dropped };
}
