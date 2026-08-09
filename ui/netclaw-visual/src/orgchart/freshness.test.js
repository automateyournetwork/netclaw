import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  AGING_THRESHOLD_S, STALE_THRESHOLD_S,
  formatAge, freshnessOf, parseStamp,
} from './freshness.js';

/**
 * FR-004: inventory freshness in operator terms, never a bare timestamp.
 *
 * The assertion that matters most is never-vs-zero. A peer that has never sent an
 * inventory rendering as "just now" would read as the healthiest possible value
 * while meaning the opposite — and two of seven live peers (AB, Carapace) are in
 * exactly that state.
 */

const NOW = 1786060000;   // fixed injected clock

test('never-received yields null age and the never judgement, not zero', () => {
  const f = freshnessOf({ inventory_received_at: null }, NOW);
  assert.equal(f.ageSeconds, null, 'null must not collapse to 0');
  assert.equal(f.judgement, 'never');
  assert.equal(f.ageText, 'never');
  assert.notEqual(f.ageText, 'just now', 'never must never read as the freshest value');
});

test('a missing field is treated the same as null', () => {
  assert.equal(freshnessOf({}, NOW).judgement, 'never');
  assert.equal(freshnessOf(undefined, NOW).judgement, 'never');
});

test('an unparseable timestamp is never guessed at', () => {
  // A silently mis-parsed date produces a confident wrong age, which is worse
  // than admitting we do not know.
  for (const bad of ['not-a-date', '', '   ', '2026-13-45T99:99:99Z']) {
    assert.equal(freshnessOf({ inventory_received_at: bad }, NOW).judgement, 'never', bad);
  }
});

test('parseStamp returns epoch seconds for the daemon format', () => {
  assert.equal(parseStamp('2026-08-06T20:12:08Z'), Math.floor(Date.parse('2026-08-06T20:12:08Z') / 1000));
  assert.equal(parseStamp(null), null);
  assert.equal(parseStamp(42), null);
});

test('judgement derives from age across both thresholds', () => {
  const at = (age) => {
    const iso = new Date((NOW - age) * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
    return freshnessOf({ inventory_received_at: iso }, NOW).judgement;
  };
  assert.equal(at(60), 'fresh');
  assert.equal(at(AGING_THRESHOLD_S - 10), 'fresh');
  assert.equal(at(AGING_THRESHOLD_S + 10), 'aging');
  assert.equal(at(STALE_THRESHOLD_S - 10), 'aging');
  assert.equal(at(STALE_THRESHOLD_S + 10), 'stale');
});

test('the API stale flag can only make the judgement worse, never better', () => {
  const iso = new Date((NOW - 60) * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
  // Fresh by age, but the daemon says stale — the daemon knows things we do not
  // (e.g. a dropped channel), and claiming a stale peer is fresh is the dangerous
  // direction of the error.
  assert.equal(freshnessOf({ inventory_received_at: iso, stale: true }, NOW).judgement, 'stale');
  // And it cannot rescue a genuinely old inventory.
  const old = new Date((NOW - STALE_THRESHOLD_S - 100) * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
  assert.equal(freshnessOf({ inventory_received_at: old, stale: false }, NOW).judgement, 'stale');
});

test('formatAge renders operator terms across every band', () => {
  assert.equal(formatAge(null), 'never');
  assert.equal(formatAge(0), 'just now');
  assert.equal(formatAge(44), 'just now');
  assert.equal(formatAge(600), '10m ago');
  assert.equal(formatAge(7200), '2h ago');
  assert.equal(formatAge(86400 * 12), '12d ago');
});

test('formatAge never emits a bare ISO timestamp', () => {
  for (const s of [0, 100, 10000, 1000000]) {
    assert.ok(!/\d{4}-\d{2}-\d{2}/.test(formatAge(s)), `FR-004 violated for ${s}`);
  }
});

test('a future timestamp clamps to zero rather than going negative', () => {
  const future = new Date((NOW + 5000) * 1000).toISOString().replace(/\.\d{3}Z$/, 'Z');
  const f = freshnessOf({ inventory_received_at: future }, NOW);
  assert.equal(f.ageSeconds, 0);
  assert.equal(f.ageText, 'just now');
});

test('the real Byrn row reads as stale, not fresh', () => {
  // Live data 2026-08-06: inventory from 2026-07-25, stale flag set.
  const f = freshnessOf(
    { inventory_received_at: '2026-07-25T16:43:51Z', stale: true },
    Math.floor(Date.parse('2026-08-06T23:00:00Z') / 1000));
  assert.equal(f.judgement, 'stale');
  assert.match(f.ageText, /\d+d ago/, 'twelve days must render in days, not seconds');
});
