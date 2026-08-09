/**
 * Per-preset position memory (feature 102, US1/US2 — FR-014, FR-049, FR-050,
 * FR-051, FR-053).
 *
 * Pure: no imports, no clock, no DOM, no three.js.
 *
 * ## Why positions are sparse and scoped per preset
 *
 * **Sparse** — a node absent from the map uses its computed/preset position. A full
 * snapshot would freeze every node at whatever the layout computed on the day it was
 * saved, so a member enrolling later would land on top of a stale neighbour and a
 * departing member would leave a hole. "The operator moved these; compute the rest"
 * is what makes FR-016's add/remove tolerance fall out for free instead of needing
 * reconciliation logic.
 *
 * **Per preset** (FR-049) — a node dragged in free-form must not move in the org
 * chart. Scoping also means switching presets never has to destroy anything, which
 * is what dissolved FR-014's original "warned about OR undoable" either/or: with
 * nothing destroyed, neither a confirm dialog nor an undo stack is needed.
 */

import { PRESETS, isPresetId } from './presets.js';

export function createLayoutStore(activePreset = 'orgchart') {
  const positions = {};
  const pinned = {};
  for (const p of PRESETS) { positions[p] = {}; pinned[p] = new Set(); }
  return {
    activePreset: isPresetId(activePreset) ? activePreset : 'orgchart',
    positions,
    pinned,
    camera: null,
    dirty: false,
  };
}

/** Switch preset. Changes `activePreset` only — never clears a position map (FR-014). */
export function setPreset(store, presetId) {
  if (!isPresetId(presetId) || store.activePreset === presetId) return store;
  store.activePreset = presetId;
  store.dirty = true;
  return store;
}

/** Record an operator-placed position for the ACTIVE preset (FR-049). */
export function setPosition(store, nodeId, position) {
  if (!nodeId || !position) return store;
  const { x, y, z } = position;
  if (![x, y, z].every(Number.isFinite)) return store;
  store.positions[store.activePreset][nodeId] = { x, y, z };
  store.dirty = true;
  return store;
}

/**
 * Position for a node under the active preset, or `null` when the operator has not
 * moved it — `null` means "use the computed/preset position", which is the whole
 * point of the map being sparse (FR-050).
 */
export function getPosition(store, nodeId) {
  return store.positions[store.activePreset]?.[nodeId] ?? null;
}

/** Clear one node's manual position under the active preset. */
export function clearPosition(store, nodeId) {
  if (store.positions[store.activePreset]?.[nodeId]) {
    delete store.positions[store.activePreset][nodeId];
    store.dirty = true;
  }
  return store;
}

/**
 * Reset the active preset to computed positions, discarding manual placement there
 * and nowhere else (FR-050). This is what makes "Org chart" a non-destructive way
 * back from any arranged state.
 */
export function resetPreset(store, presetId = store.activePreset) {
  if (!isPresetId(presetId)) return store;
  store.positions[presetId] = {};
  store.pinned[presetId] = new Set();
  store.dirty = true;
  return store;
}

/** Pin a node under the active preset — force-solver only (FR-041), scoped (FR-049). */
export function pinNode(store, nodeId) {
  store.pinned[store.activePreset].add(nodeId);
  store.dirty = true;
  return store;
}

export function isPinned(store, nodeId, presetId = store.activePreset) {
  return store.pinned[presetId]?.has(nodeId) === true;
}

/** Pinned ids for a preset, as a plain sorted array — stable for serialization. */
export function pinnedIds(store, presetId = store.activePreset) {
  return [...(store.pinned[presetId] || [])].sort();
}

export function setCamera(store, camera) {
  store.camera = camera ? { ...camera } : null;
  store.dirty = true;
  return store;
}

/**
 * FR-053: only a SUCCESSFUL save clears dirty. A failed save must leave it set, so a
 * failed write can never present as a successful one (FR-035).
 */
export function markSaved(store) { store.dirty = false; return store; }
export function isDirty(store) { return store.dirty === true; }
