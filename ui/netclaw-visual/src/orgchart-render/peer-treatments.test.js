import { test } from 'node:test';
import assert from 'node:assert/strict';

import { PEER_TREATMENTS, TREATMENTS } from './nodes.js';
import { PEER_STATES } from '../orgchart/liveness.js';

/**
 * visual-contract.md §3 rules R1–R5, as a permanent test rather than a screenshot.
 *
 * These are properties of the design constants, so they hold on every run instead
 * of for one build on one machine. Feature 072 proved the value: its
 * treatments.test.js caught COLD landing within 10 luminance of FAULT, a
 * collision a screenshot review had passed.
 */

/** ITU-R BT.709 relative luminance — what a greyscale conversion produces. */
function luminance(hex) {
  const r = (hex >> 16) & 0xff;
  const g = (hex >> 8) & 0xff;
  const b = hex & 0xff;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Same threshold feature 072 settled on. */
const MIN_DELTA = 18;

test('every classified peer state has a treatment', () => {
  for (const s of PEER_STATES) {
    assert.ok(PEER_TREATMENTS[s], `no treatment for ${s}`);
  }
  assert.equal(Object.keys(PEER_TREATMENTS).length, PEER_STATES.length);
});

test('R1: no two states are conveyed by the same channel combination', () => {
  // The real requirement. Six states cannot all clear >=18 luminance within one
  // usable range, so the contract says form and affix must carry the difference
  // where colour cannot — this asserts the COMBINATION is unique, which is what
  // an operator actually distinguishes.
  const seen = new Map();
  for (const [state, t] of Object.entries(PEER_TREATMENTS)) {
    const key = `${t.shape}|${t.color}|${t.pulse > 0}|${t.affix}`;
    assert.ok(!seen.has(key),
      `${state} and ${seen.get(key)} are visually identical (${key})`);
    seen.set(key, state);
  }
});

test('R1: states sharing a form are separable by luminance alone', () => {
  // Where form does NOT distinguish two states, colour must — otherwise the pair
  // collapses in greyscale with nothing else to fall back on.
  const byShape = new Map();
  for (const [state, t] of Object.entries(PEER_TREATMENTS)) {
    if (!byShape.has(t.shape)) byShape.set(t.shape, []);
    byShape.get(t.shape).push(state);
  }
  for (const [shape, states] of byShape) {
    for (let i = 0; i < states.length; i += 1) {
      for (let j = i + 1; j < states.length; j += 1) {
        const a = states[i]; const b = states[j];
        const delta = Math.abs(
          luminance(PEER_TREATMENTS[a].color) - luminance(PEER_TREATMENTS[b].color));
        const motionDiffers = (PEER_TREATMENTS[a].pulse > 0) !== (PEER_TREATMENTS[b].pulse > 0);
        assert.ok(delta >= MIN_DELTA || motionDiffers,
          `${a} and ${b} share form '${shape}', differ by only ${delta.toFixed(1)} `
          + 'luminance, and neither pulses — indistinguishable in a greyscale still');
      }
    }
  }
});

test('R2: LIVE and IDLE are each distinguishable from STALE', () => {
  // The pairs an operator acts on, checked explicitly rather than only as part of
  // the sweep: mistaking stale data for a live channel is the whole defect.
  for (const good of ['LIVE', 'IDLE']) {
    const delta = Math.abs(
      luminance(PEER_TREATMENTS[good].color) - luminance(PEER_TREATMENTS.STALE.color));
    assert.ok(delta >= MIN_DELTA,
      `${good} vs STALE differ by only ${delta.toFixed(1)} luminance`);
    assert.notEqual(PEER_TREATMENTS[good].shape, PEER_TREATMENTS.STALE.shape);
    assert.equal(PEER_TREATMENTS.STALE.affix, 'stale', 'STALE must carry a text affix');
  }
});

test('R2: LIVE and IDLE are distinguishable from each other', () => {
  // These two are deliberately close in colour (both healthy) — so motion and
  // scale must separate them, or a live channel looks merely idle.
  const a = PEER_TREATMENTS.LIVE; const b = PEER_TREATMENTS.IDLE;
  assert.ok(a.pulse > 0 && b.pulse === 0, 'LIVE must pulse and IDLE must not');
  assert.notEqual(a.scaleMul, b.scaleMul);
});

test('R3: UNKNOWN is not in the alarm hue family', () => {
  // FR-016/017. "We have never heard from AB" must not read as "AB is broken".
  const u = PEER_TREATMENTS.UNKNOWN;
  const r = (u.color >> 16) & 0xff;
  const g = (u.color >> 8) & 0xff;
  const b = u.color & 0xff;
  assert.ok(b >= r, `UNKNOWN colour is warm (r=${r} > b=${b}) — reads as alarm`);
  assert.equal(u.pulse, 0, 'UNKNOWN must not pulse — pulsing signals urgency');
  assert.ok(u.affix.includes('never'), 'the affix must say never, not failed');
});

test('R3: the actionable states ARE warm and urgent', () => {
  // The converse of the rule above: if nothing is warm, the encoding cannot
  // signal "act on this" at all.
  for (const s of ['UNREACHABLE', 'SEVERED']) {
    const t = PEER_TREATMENTS[s];
    const r = (t.color >> 16) & 0xff;
    const b = t.color & 0xff;
    assert.ok(r > b, `${s} should read warm/alarming (r=${r}, b=${b})`);
  }
  assert.ok(PEER_TREATMENTS.UNREACHABLE.pulse > 0, 'UNREACHABLE is urgent — it pulses');
});

test('R4: every peer state keeps a peer-family silhouette', () => {
  // Band membership must still read at a glance; state modulates the octahedron
  // rather than borrowing a member shape.
  const memberShapes = new Set(Object.values(TREATMENTS).map((t) => t.shape));
  for (const [state, t] of Object.entries(PEER_TREATMENTS)) {
    if (t.shape === 'ring') continue;   // ring is shared with FAULT ON PURPOSE:
                                        // "needs attention" should look the same
                                        // in both bands (see the pulse-rate note
                                        // in animateNodes).
    assert.ok(t.shape.startsWith('peer'),
      `${state} uses '${t.shape}', which is not a peer-family silhouette`);
    assert.ok(!memberShapes.has(t.shape) || t.shape === 'ring',
      `${state} borrows the member shape '${t.shape}'`);
  }
});

test('R5: affixes are short, lowercase, and only on non-healthy states', () => {
  assert.equal(PEER_TREATMENTS.LIVE.affix, '', 'a healthy peer needs no affix');
  assert.equal(PEER_TREATMENTS.IDLE.affix, '', 'idle is normal — no affix');
  for (const s of ['STALE', 'UNKNOWN', 'UNREACHABLE', 'SEVERED']) {
    const a = PEER_TREATMENTS[s].affix;
    assert.ok(a.length > 0 && a.length <= 12, `${s} affix '${a}' is not concise`);
    assert.equal(a, a.toLowerCase());
  }
});

test('FR-014: no state is carried by colour alone', () => {
  // Strip colour entirely and every state must still be unique.
  const keys = Object.entries(PEER_TREATMENTS)
    .map(([, t]) => `${t.shape}|${t.pulse > 0}|${t.affix}|${t.scaleMul}`);
  assert.equal(new Set(keys).size, keys.length,
    'two states become identical once colour is removed');
});

test('every treatment carries a human-readable label', () => {
  for (const [s, t] of Object.entries(PEER_TREATMENTS)) {
    assert.ok(t.label && t.label.length > 3, `${s} has no usable label`);
  }
});

test('member TREATMENTS are untouched by this feature (FR-013)', () => {
  // Regression guard: US3 must extend, not replace, feature 072's scheme.
  assert.deepEqual(Object.keys(TREATMENTS), ['HOT', 'WARM', 'COLD', 'FAULT']);
  assert.equal(TREATMENTS.HOT.color, 0x4dff9b);
  assert.equal(TREATMENTS.COLD.color, 0x5f6d80);
  assert.equal(TREATMENTS.FAULT.color, 0xff7a7a);
});
