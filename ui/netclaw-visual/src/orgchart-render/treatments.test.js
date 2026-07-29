import { test } from 'node:test';
import assert from 'node:assert/strict';

import { TREATMENTS } from './nodes.js';

/**
 * SC-007 / SC-010 as a permanent test rather than a one-off screenshot.
 *
 * The claim is that the four health states stay distinguishable in greyscale
 * and with motion suppressed. That is a property of the design constants, not
 * of any particular frame, so it belongs here where it is checked on every run
 * — a screenshot only proves the state of one build on one machine.
 */

const STATES = ['HOT', 'WARM', 'COLD', 'FAULT'];

/** ITU-R BT.709 relative luminance — what a greyscale conversion produces. */
function luminance(hex) {
  const r = (hex >> 16) & 0xff;
  const g = (hex >> 8) & 0xff;
  const b = hex & 0xff;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

test('all four states are defined', () => {
  for (const s of STATES) assert.ok(TREATMENTS[s], `${s} missing`);
});

test('SC-007: every pair of states is separable by luminance alone', () => {
  // If two states converge in greyscale, a colour-blind operator or a
  // greyscale screenshot cannot tell them apart — colour would be doing the
  // work alone, which FR-009a forbids.
  const MIN_DELTA = 18;
  for (let i = 0; i < STATES.length; i += 1) {
    for (let j = i + 1; j < STATES.length; j += 1) {
      const a = STATES[i]; const b = STATES[j];
      const delta = Math.abs(luminance(TREATMENTS[a].color) - luminance(TREATMENTS[b].color));
      assert.ok(
        delta >= MIN_DELTA,
        `${a} and ${b} differ by only ${delta.toFixed(1)} luminance — indistinguishable in greyscale`,
      );
    }
  }
});

test('SC-007: every state has a distinct silhouette', () => {
  // Shape is the channel that survives both greyscale AND reduced motion, so
  // it must be unique per state on its own.
  const shapes = STATES.map((s) => TREATMENTS[s].shape);
  assert.equal(new Set(shapes).size, STATES.length, `shapes collide: ${shapes.join(', ')}`);
});

test('SC-010: the encoding survives motion suppression (FR-032c)', () => {
  // Motion must be REDUNDANT — states that share a pulse value must still be
  // separable by shape and luminance, or suppressing motion collapses them.
  for (let i = 0; i < STATES.length; i += 1) {
    for (let j = i + 1; j < STATES.length; j += 1) {
      const a = TREATMENTS[STATES[i]]; const b = TREATMENTS[STATES[j]];
      if (a.pulse !== b.pulse) continue;
      assert.notEqual(a.shape, b.shape, `${STATES[i]}/${STATES[j]} share a pulse AND a shape`);
      assert.ok(
        Math.abs(luminance(a.color) - luminance(b.color)) >= 18,
        `${STATES[i]}/${STATES[j]} share a pulse and are too close in luminance`,
      );
    }
  }
});

test('FR-009b: FAULT is the most salient state after HOT', () => {
  const { HOT, WARM, COLD, FAULT } = TREATMENTS;
  assert.ok(FAULT.scale > WARM.scale, 'FAULT must out-scale WARM');
  assert.ok(FAULT.scale > COLD.scale, 'FAULT must out-scale COLD');
  assert.ok(FAULT.emissiveIntensity > WARM.emissiveIntensity, 'FAULT must out-glow WARM');
  assert.ok(FAULT.emissiveIntensity > COLD.emissiveIntensity, 'FAULT must out-glow COLD');
  assert.ok(FAULT.pulse > 0, 'FAULT must move — it demands attention');
  assert.ok(HOT.pulse > 0, 'HOT must read as alive');
});

test('FR-009: COLD reads as inert but never as absent', () => {
  // Lifting COLD off near-black was deliberate: an operator has to see what
  // capacity exists before deciding to warm it. "Distinctly cold" is not
  // "invisible".
  const l = luminance(TREATMENTS.COLD.color);
  assert.ok(l > 45, `COLD luminance ${l.toFixed(1)} is too dark to read as present`);
  assert.ok(l < luminance(TREATMENTS.HOT.color), 'COLD must still be dimmer than HOT');
  assert.equal(TREATMENTS.COLD.pulse, 0, 'COLD must be still');
});

test('every state carries screen-reader text (FR-032b)', () => {
  for (const s of STATES) {
    assert.ok(TREATMENTS[s].label?.length > 3, `${s} needs a human-readable label`);
  }
});
