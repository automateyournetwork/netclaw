import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  clearPosition, createLayoutStore, getPosition, isDirty, isPinned, markSaved,
  pinNode, pinnedIds, resetPreset, setCamera, setPosition, setPreset,
} from './layout-store.js';

/** FR-014, FR-049, FR-050, FR-051, FR-053. */

const P = { x: 1, y: 2, z: 3 };

test('FR-049: positions are scoped per preset', () => {
  const s = createLayoutStore('freeform');
  setPosition(s, 'r/cml', P);
  assert.deepEqual(getPosition(s, 'r/cml'), P);
  setPreset(s, 'orgchart');
  assert.equal(getPosition(s, 'r/cml'), null, 'a freeform drag must not move the org chart');
});

test('FR-014: switching preset and back preserves positions exactly', () => {
  const s = createLayoutStore('ring');
  setPosition(s, 'r/cml', P);
  setPreset(s, 'grid'); setPreset(s, 'force'); setPreset(s, 'ring');
  assert.deepEqual(getPosition(s, 'r/cml'), P, 'switching must never destroy positions');
});

test('FR-014: nothing is destroyed, so no confirm or undo is needed', () => {
  const s = createLayoutStore('ring');
  setPosition(s, 'a', P);
  setPreset(s, 'grid');
  setPosition(s, 'b', { x: 9, y: 9, z: 0 });
  setPreset(s, 'ring');
  assert.deepEqual(getPosition(s, 'a'), P);
  setPreset(s, 'grid');
  assert.deepEqual(getPosition(s, 'b'), { x: 9, y: 9, z: 0 });
});

test('FR-050: maps are sparse — absent means "use the computed position"', () => {
  const s = createLayoutStore('ring');
  assert.equal(getPosition(s, 'never-moved'), null);
  setPosition(s, 'moved', P);
  assert.equal(Object.keys(s.positions.ring).length, 1, 'only moved nodes are stored');
});

test('FR-050: resetting one preset leaves the others untouched', () => {
  const s = createLayoutStore('ring');
  setPosition(s, 'a', P);
  setPreset(s, 'grid'); setPosition(s, 'a', { x: 5, y: 5, z: 0 });
  resetPreset(s, 'grid');
  assert.equal(getPosition(s, 'a'), null);
  setPreset(s, 'ring');
  assert.deepEqual(getPosition(s, 'a'), P, 'reset is scoped, not global');
});

test('FR-041 + FR-049: pins are per preset and do not leak', () => {
  const s = createLayoutStore('force');
  pinNode(s, 'r/cml');
  assert.equal(isPinned(s, 'r/cml'), true);
  setPreset(s, 'ring');
  assert.equal(isPinned(s, 'r/cml'), false, 'pinning under force must not leak elsewhere');
});

test('pinnedIds is sorted, so serialization is stable', () => {
  const s = createLayoutStore('force');
  pinNode(s, 'z'); pinNode(s, 'a'); pinNode(s, 'm');
  assert.deepEqual(pinnedIds(s), ['a', 'm', 'z']);
});

test('FR-051: any change marks the store dirty', () => {
  for (const mutate of [
    (s) => setPosition(s, 'a', P),
    (s) => setPreset(s, 'grid'),
    (s) => setCamera(s, { position: P, target: P, zoom: 1 }),
    (s) => pinNode(s, 'a'),
  ]) {
    const s = createLayoutStore('ring');
    assert.equal(isDirty(s), false, 'a fresh store is clean');
    mutate(s);
    assert.equal(isDirty(s), true);
  }
});

test('FR-053: only a successful save clears dirty', () => {
  const s = createLayoutStore('ring');
  setPosition(s, 'a', P);
  assert.equal(isDirty(s), true);
  markSaved(s);
  assert.equal(isDirty(s), false);
  // A failed save simply does not call markSaved, so dirty survives — which is what
  // stops a failed write presenting as a successful one (FR-035).
  setPosition(s, 'b', P);
  assert.equal(isDirty(s), true);
});

test('switching to the same preset is a no-op and does not dirty', () => {
  const s = createLayoutStore('ring');
  setPreset(s, 'ring');
  assert.equal(isDirty(s), false);
});

test('an unknown preset id is rejected rather than creating a bucket', () => {
  const s = createLayoutStore('ring');
  setPreset(s, 'free-form');            // hyphenated form is NOT a valid id
  assert.equal(s.activePreset, 'ring');
  assert.equal(s.positions['free-form'], undefined);
});

test('non-finite coordinates are refused', () => {
  const s = createLayoutStore('ring');
  for (const bad of [{ x: NaN, y: 0, z: 0 }, { x: Infinity, y: 0, z: 0 }, null]) {
    setPosition(s, 'a', bad);
  }
  assert.equal(getPosition(s, 'a'), null);
});

test('clearPosition removes one node without touching others', () => {
  const s = createLayoutStore('ring');
  setPosition(s, 'a', P); setPosition(s, 'b', P);
  clearPosition(s, 'a');
  assert.equal(getPosition(s, 'a'), null);
  assert.deepEqual(getPosition(s, 'b'), P);
});
