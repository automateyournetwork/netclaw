import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { DEFAULTS, forceLayout, hashId } from './force-layout.js';

/**
 * FR-039 (determinism), FR-040 (bounded, stops), FR-041 (pinning).
 *
 * The determinism test is the whole of FR-039 and is only possible because the
 * solver is pure — solve twice, assert deep equality. No screenshot could show it.
 */

const NODES = ['border', 'as65006-6.6.6.6', 'as65099-10.255.255.1', 'r/cml', 'r/pyats', 'r/viz']
  .map((id) => ({ id }));
const LINKS = [['border', 'as65006-6.6.6.6'], ['border', 'as65099-10.255.255.1'],
               ['border', 'r/cml'], ['border', 'r/pyats'], ['border', 'r/viz']];

test('FR-039: identical input produces identical output', () => {
  const a = forceLayout({ nodes: NODES, links: LINKS });
  const b = forceLayout({ nodes: NODES, links: LINKS });
  assert.deepEqual(a, b, 'a layout that differs between runs makes spatial memory impossible');
});

test('FR-039: input array ORDER does not change the result', () => {
  // Without an internal sort, float accumulation order differs and the same graph
  // yields different output — a violation that is very hard to spot by eye.
  const a = forceLayout({ nodes: NODES, links: LINKS });
  const b = forceLayout({ nodes: [...NODES].reverse(), links: [...LINKS].reverse() });
  assert.deepEqual(a, b);
});

test('FR-039: no Math.random or clock read in the module CODE', () => {
  // Strip comments first: the module's own docblock explains WHY Math.random is
  // disqualifying, and a naive source grep flags that explanation as a violation.
  // The property under test is "no call", not "no mention".
  const raw = readFileSync(new URL('./force-layout.js', import.meta.url), 'utf8');
  const code = raw
    .replace(/\/\*[\s\S]*?\*\//g, '')      // block comments
    .replace(/(^|[^:])\/\/.*$/gm, '$1');    // line comments
  assert.ok(!/Math\.random/.test(code), 'Math.random defeats determinism');
  assert.ok(!/\bnew Date\b|Date\.now|performance\.now/.test(code),
    'clock reads defeat determinism');
});

test('hashId is stable and differs between identities', () => {
  assert.equal(hashId('as65006-6.6.6.6'), hashId('as65006-6.6.6.6'));
  assert.notEqual(hashId('as65006-6.6.6.6'), hashId('as65007-7.7.7.7'));
});

test('FR-040: returns a plain map and schedules nothing', () => {
  const out = forceLayout({ nodes: NODES, links: LINKS });
  assert.equal(typeof out, 'object');
  assert.ok(!(out instanceof Promise), 'must not be async — there is no tick loop to await');
  for (const p of Object.values(out)) {
    assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y), 'finite coordinates only');
    assert.equal(p.z, 0);
  }
});

test('FR-040: iteration count is fixed, not energy-thresholded', () => {
  // A threshold is data-dependent and can fail to converge; a count is bounded by
  // construction, which is what "bounded time" actually requires.
  assert.equal(typeof DEFAULTS.iterations, 'number');
  assert.ok(DEFAULTS.iterations > 0 && DEFAULTS.iterations <= 2000);
});

test('FR-041: pinned nodes stay exactly where pinned', () => {
  const pinnedPositions = { 'r/cml': { x: 25, y: -12 } };
  const out = forceLayout({ nodes: NODES, links: LINKS, pinned: ['r/cml'], pinnedPositions });
  assert.equal(out['r/cml'].x, 25);
  assert.equal(out['r/cml'].y, -12);
});

test('FR-041: pinning one node does not freeze the others', () => {
  const withPin = forceLayout({ nodes: NODES, links: LINKS, pinned: ['r/cml'],
                                pinnedPositions: { 'r/cml': { x: 25, y: -12 } } });
  const free = forceLayout({ nodes: NODES, links: LINKS });
  assert.notDeepEqual(withPin['r/pyats'], free['r/pyats'], 'unpinned nodes still solve');
});

test('every node receives a position', () => {
  const out = forceLayout({ nodes: NODES, links: LINKS });
  for (const n of NODES) assert.ok(out[n.id], `${n.id} missing`);
});

test('coincident seeds do not produce NaN', () => {
  // The repulsion guard exists for this; NaN would reach three.js as invisible
  // geometry corruption rather than an error.
  const out = forceLayout({ nodes: [{ id: 'a' }, { id: 'a' }], links: [] });
  for (const p of Object.values(out)) assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y));
});

test('links referencing unknown nodes are ignored, not fatal', () => {
  assert.doesNotThrow(() => forceLayout({ nodes: NODES, links: [['border', 'ghost']] }));
});

test('empty and malformed input do not throw', () => {
  for (const bad of [{}, { nodes: [] }, null, undefined]) {
    assert.doesNotThrow(() => forceLayout(bad));
  }
  assert.deepEqual(forceLayout({ nodes: [] }), {});
});
