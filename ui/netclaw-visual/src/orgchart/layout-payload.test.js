import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createLayoutStore, pinNode, setCamera, setPosition } from './layout-store.js';
import {
  CAMERA_BOUNDS, LIMITS, SCHEMA_VERSION, applyPayload, clampCamera, toPayload, validateLayout,
} from './layout-payload.js';

/** FR-016, FR-018, FR-019, FR-033, FR-034, FR-047, SC-008. */

const V = { x: 1, y: 2, z: 0 };
const good = () => ({ version: SCHEMA_VERSION, activePreset: 'ring',
                      positions: { ring: { 'as65006-6.6.6.6': V } } });

test('a well-formed payload validates', () => {
  assert.deepEqual(validateLayout(good()), { ok: true });
});

test('FR-019: an unsupported version is rejected, not migrated', () => {
  const r = validateLayout({ ...good(), version: 999 });
  assert.equal(r.ok, false);
  assert.match(r.error, /version/);
});

test('unknown top-level keys are REJECTED, not ignored', () => {
  // Silent acceptance of junk is how a schema rots, and how unexpected data ends
  // up persisted.
  const r = validateLayout({ ...good(), somethingElse: true });
  assert.equal(r.ok, false);
  assert.match(r.error, /unknown top-level key/);
});

test('FR-038: unknown preset names are rejected in every position', () => {
  assert.equal(validateLayout({ ...good(), activePreset: 'free-form' }).ok, false);
  assert.equal(validateLayout({ version: 1, positions: { 'free-form': {} } }).ok, false);
  assert.equal(validateLayout({ version: 1, pinned: { nope: [] } }).ok, false);
});

test('FR-033: non-finite coordinates are rejected', () => {
  // NaN/Infinity reach three.js as invisible geometry corruption rather than an
  // error, so they must be caught here where they are still visible.
  for (const bad of [NaN, Infinity, -Infinity, 'x', null]) {
    const p = { version: 1, positions: { ring: { a: { x: bad, y: 0, z: 0 } } } };
    assert.equal(validateLayout(p).ok, false, String(bad));
  }
});

test('FR-033: oversized coordinates are rejected', () => {
  const p = { version: 1, positions: { ring: { a: { x: LIMITS.maxCoordinate + 1, y: 0, z: 0 } } } };
  const r = validateLayout(p);
  assert.equal(r.ok, false);
  assert.match(r.error, /finite and within/);
});

test('FR-033: entry count is bounded, with a SPECIFIC error', () => {
  const map = {};
  for (let i = 0; i < LIMITS.maxEntriesPerPreset + 12; i += 1) map[`n${i}`] = V;
  const r = validateLayout({ version: 1, positions: { ring: map } });
  assert.equal(r.ok, false);
  assert.match(r.error, /512 entries exceeds 500/, 'the operator must be able to act on it');
});

test('FR-033: total size is bounded per-route, not left to express.json 4mb', () => {
  const map = {};
  for (let i = 0; i < 400; i += 1) map[`node-${'x'.repeat(120)}-${i}`] = V;
  const r = validateLayout({ version: 1, positions: { ring: map } });
  assert.equal(r.ok, false);
});

test('FR-034: node ids that could act as path components are rejected', () => {
  for (const id of ['../etc/passwd', 'a/b', 'a\\b', '..', 'x\0y', 'y'.repeat(200)]) {
    const r = validateLayout({ version: 1, positions: { ring: { [id]: V } } });
    assert.equal(r.ok, false, `${JSON.stringify(id)} must be rejected`);
  }
});

test('FR-047: camera zoom is clamped to 072 bounds, not honoured', () => {
  const hi = clampCamera({ position: V, target: V, zoom: 999 });
  const lo = clampCamera({ position: V, target: V, zoom: 0.0001 });
  assert.equal(hi.zoom, CAMERA_BOUNDS.maxZoom);
  assert.equal(lo.zoom, CAMERA_BOUNDS.minZoom);
});

test('FR-048: an unusable camera returns null so the caller frames the chart', () => {
  for (const bad of [null, undefined, {}, { position: V, target: V, zoom: NaN },
                     { position: { x: NaN, y: 0, z: 0 }, target: V, zoom: 1 }]) {
    assert.equal(clampCamera(bad), null);
  }
});

test('SC-008: the EMITTED payload carries no federation state', () => {
  // Asserted on the emitted object, not on a promise about the serializer.
  const s = createLayoutStore('ring');
  setPosition(s, 'as65006-6.6.6.6', V);
  pinNode(s, 'r/cml');
  setCamera(s, { position: V, target: V, zoom: 2 });
  // Contaminate the store the way a careless refactor might.
  s.channel_state = 'up'; s.inventory = { docs: 1 }; s.pinned_key = 'SECRET';

  const text = JSON.stringify(toPayload(s, '2026-08-07T00:00:00Z'));
  for (const leak of ['channel_state', 'inventory', 'pinned_key', 'SECRET',
                      'token', 'endpoint_host', 'stale']) {
    assert.ok(!text.includes(leak), `${leak} leaked into the saved payload`);
  }
});

test('toPayload omits empty maps so a fresh save stays small', () => {
  const p = toPayload(createLayoutStore('ring'));
  assert.equal(p.positions, undefined);
  assert.equal(p.pinned, undefined);
  assert.equal(p.version, SCHEMA_VERSION);
});

test('round-trip: toPayload output always validates', () => {
  const s = createLayoutStore('grid');
  setPosition(s, 'a', V); pinNode(s, 'b');
  setCamera(s, { position: V, target: V, zoom: 1.5 });
  assert.deepEqual(validateLayout(toPayload(s, '2026-08-07T00:00:00Z')), { ok: true });
});

test('FR-016: ids that no longer exist are dropped, not fatal', () => {
  const s = createLayoutStore('ring');
  const { dropped } = applyPayload(s, {
    version: 1, activePreset: 'ring',
    positions: { ring: { alive: V, ghost: V } },
  }, ['alive']);
  assert.deepEqual(dropped, ['ghost']);
  assert.deepEqual(s.positions.ring, { alive: V });
});

test('FR-016: nodes absent from the payload keep computed positions', () => {
  const s = createLayoutStore('ring');
  applyPayload(s, { version: 1, positions: { ring: { a: V } } }, ['a', 'newcomer']);
  assert.equal(s.positions.ring.newcomer, undefined, 'sparse means "compute the rest"');
});

test('a restored layout is not marked unsaved', () => {
  const s = createLayoutStore('ring');
  applyPayload(s, good(), null);
  assert.equal(s.dirty, false);
});

test('malformed payloads do not throw', () => {
  for (const bad of [null, undefined, 42, 'x', [], { version: 1, positions: 'no' }]) {
    assert.doesNotThrow(() => validateLayout(bad));
    assert.doesNotThrow(() => applyPayload(createLayoutStore(), bad, null));
  }
});
