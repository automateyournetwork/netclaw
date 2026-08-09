import { test } from 'node:test';
import assert from 'node:assert/strict';
import { GRID, PRESETS, PRESET_LABELS, RING, gridLayout, isPresetId, ringLayout } from './presets.js';

/** FR-038, FR-042. The preset ids are WIRE VALUES — persisted verbatim as JSON keys. */

const NODES = [
  { id: 'border', kind: 'border' },
  { id: 'as65006-6.6.6.6', kind: 'peer' }, { id: 'as65099-10.255.255.1', kind: 'peer' },
  { id: 'as65003-3.3.3.3', kind: 'peer' },
  { id: 'r/cml', kind: 'member' }, { id: 'r/pyats', kind: 'member' }, { id: 'r/viz', kind: 'member' },
  { id: 'r/phone', kind: 'edge' },
];

test('FR-038: exactly five presets, with the literal wire ids', () => {
  assert.deepEqual(PRESETS, ['orgchart', 'ring', 'grid', 'force', 'freeform']);
  // The hyphenated prose forms must never be valid identifiers.
  for (const bad of ['free-form', 'org-chart', 'orgChart', 'Force-directed']) {
    assert.equal(isPresetId(bad), false, `${bad} must not be a valid PresetId`);
  }
});

test('every preset has a human label for the dropdown', () => {
  for (const p of PRESETS) assert.ok(PRESET_LABELS[p], `no label for ${p}`);
});

test('orgchart and freeform have no geometry of their own', () => {
  // orgchart IS computeLayout's output; freeform starts from it. Neither is
  // implemented here, and that absence is deliberate (FR-010).
  assert.equal(typeof ringLayout, 'function');
  assert.equal(typeof gridLayout, 'function');
});

test('ring: every node gets a position, Border at the centre', () => {
  const out = ringLayout(NODES);
  assert.equal(Object.keys(out).length, NODES.length);
  assert.deepEqual(out.border, { x: 0, y: RING.y, z: 0 });
});

test('ring: is drawn on the XY plane the chart actually uses', () => {
  // The first implementation built the ring in XZ, which collapses to a horizontal
  // line from a camera looking down -Z. The test asserted the same wrong plane, so
  // it passed while the feature was visibly broken. Assert the plane explicitly.
  const out = ringLayout(NODES);
  assert.ok(Object.values(out).every((p) => p.z === 0), 'every node must sit at z=0');
  const ys = new Set(Object.values(out).map((p) => p.y));
  assert.ok(ys.size > 1, 'a ring must vary in Y, not just X');
});

test('ring: kinds occupy distinct radii, peers closest to the Border', () => {
  const out = ringLayout(NODES);
  const r = (id) => Math.hypot(out[id].x, out[id].y - RING.y);
  assert.ok(Math.abs(r('as65006-6.6.6.6') - RING.peerRadius) < 0.5);
  assert.ok(Math.abs(r('r/cml') - RING.memberRadius) < 0.5);
  assert.ok(Math.abs(r('r/phone') - RING.edgeRadius) < 0.5);
  assert.ok(r('as65006-6.6.6.6') < r('r/cml'), 'peers must sit inside members');
});

test('ring: nodes of one kind do not collide', () => {
  const out = ringLayout(NODES);
  const peers = ['as65006-6.6.6.6', 'as65099-10.255.255.1', 'as65003-3.3.3.3'].map((i) => out[i]);
  for (let i = 0; i < peers.length; i += 1)
    for (let j = i + 1; j < peers.length; j += 1)
      assert.ok(Math.hypot(peers[i].x - peers[j].x, peers[i].y - peers[j].y) > 1);
});

test('grid: uniform rows, bands ignored', () => {
  const out = gridLayout(NODES);
  assert.equal(Object.keys(out).length, NODES.length);
  const ys = new Set(Object.values(out).map((p) => p.y));
  assert.ok(ys.size <= Math.ceil(NODES.length / GRID.columns) + 1);
  assert.ok(Object.values(out).every((p) => p.z === 0), 'grid is planar');
});

test('grid: ordering is stable and does not depend on health', () => {
  // Sorting by kind then computeLayout order means a health change cannot reshuffle
  // the grid on the next poll.
  const a = gridLayout(NODES);
  const b = gridLayout(NODES.map((n) => ({ ...n, health: 'FAULT' })));
  assert.deepEqual(a, b);
});

test('FR-042: neither preset invents membership', () => {
  // Both consume the kinds computeLayout assigned; nothing is re-derived.
  const out = ringLayout(NODES.map((n) => ({ ...n, kind: 'member' })));
  assert.equal(Object.keys(out).length, NODES.length);
});

test('empty and malformed input do not throw', () => {
  for (const bad of [[], null, undefined, 'x']) {
    assert.doesNotThrow(() => ringLayout(bad));
    assert.doesNotThrow(() => gridLayout(bad));
  }
});
