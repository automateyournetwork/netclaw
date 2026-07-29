import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { classifyHealth, healthTally, WARM_THRESHOLD_S } from './health.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = resolve(HERE, '../../../../specs/072-hud-2-org-chart/fixtures');
const live = JSON.parse(readFileSync(resolve(FIXTURES, 'live-29.json'), 'utf8'));
const NOW = 1_785_000_000;

test('the four states are reachable', () => {
  assert.equal(classifyHealth({ live: true }, NOW), 'HOT');
  assert.equal(classifyHealth({ live: false, heartbeat_age_s: 60 }, NOW), 'WARM');
  assert.equal(classifyHealth({ live: false, state: 'provisioned' }, NOW), 'COLD');
  assert.equal(classifyHealth({ live: false, state: 'unreachable' }, NOW), 'FAULT');
});

test('null heartbeat means COLD, never FAULT — the highest-value distinction (FR-008)', () => {
  // A claw that never started is normal. A claw that died needs attention.
  // Conflating them buries 2 real faults inside 22 by-design-cold members.
  assert.equal(classifyHealth({ live: false, state: 'provisioned', heartbeat_age_s: null }, NOW), 'COLD');
  assert.equal(classifyHealth({ live: false, state: 'provisioned' }, NOW), 'COLD');
  assert.notEqual(classifyHealth({ live: false, heartbeat_age_s: null }, NOW), 'FAULT');
});

test('WARM/FAULT boundary is exactly WARM_THRESHOLD_S, inclusive (FR-008a)', () => {
  assert.equal(WARM_THRESHOLD_S, 900);
  assert.equal(classifyHealth({ live: false, heartbeat_age_s: WARM_THRESHOLD_S - 1 }, NOW), 'WARM');
  assert.equal(classifyHealth({ live: false, heartbeat_age_s: WARM_THRESHOLD_S }, NOW), 'WARM');
  assert.equal(classifyHealth({ live: false, heartbeat_age_s: WARM_THRESHOLD_S + 1 }, NOW), 'FAULT');
});

test('live=true wins over every other field', () => {
  assert.equal(classifyHealth({ live: true, state: 'unreachable', heartbeat_age_s: 99999 }, NOW), 'HOT');
  assert.equal(classifyHealth({ live: true, state: 'quarantined' }, NOW), 'HOT');
});

test('an explicit fault state beats a fresh heartbeat', () => {
  // Border said unreachable; a recent heartbeat does not override that.
  assert.equal(classifyHealth({ live: false, state: 'unreachable', heartbeat_age_s: 1 }, NOW), 'FAULT');
  assert.equal(classifyHealth({ live: false, state: 'quarantined', heartbeat_age_s: 1 }, NOW), 'FAULT');
});

test('state=active but live=false is not HOT — the real 5-vs-4 disagreement', () => {
  // The live Border reports 5 members `active` while only 4 are `live`.
  // Health must key off `live`, so the fifth must not render as running.
  assert.notEqual(classifyHealth({ live: false, state: 'active' }, NOW), 'HOT');
  assert.equal(classifyHealth({ live: false, state: 'active' }, NOW), 'COLD');
  assert.equal(classifyHealth({ live: false, state: 'active', heartbeat_age_s: 30 }, NOW), 'WARM');
});

test('classifyHealth is total on junk input', () => {
  for (const junk of [null, undefined, 42, 'x', {}, { heartbeat_age_s: 'abc' }]) {
    assert.ok(['HOT', 'WARM', 'COLD', 'FAULT'].includes(classifyHealth(junk, NOW)));
  }
});

test('classifyHealth is pure — same input, same output', () => {
  const m = { live: false, heartbeat_age_s: 100 };
  assert.equal(classifyHealth(m, NOW), classifyHealth(m, NOW));
  assert.equal(classifyHealth(m, NOW + 10_000), 'WARM', 'nowEpochS must not change an age-based verdict');
});

test('live fixture tallies to its known shape', () => {
  const tally = healthTally(live.members, NOW);
  const total = tally.HOT + tally.WARM + tally.COLD + tally.FAULT;
  assert.equal(total, live.members.length, 'every member classified exactly once');
  assert.equal(tally.HOT, live.members.filter((m) => m.live).length);
  assert.ok(tally.COLD >= 20, 'the provisioned majority must be COLD');
});

// Derived from the fixture rather than hardcoded. An earlier version asserted
// "FAULT >= 2" because both edge nodes were unreachable when the spec was
// written; by capture time one had reconnected, so the count had already
// drifted. What must hold is the *rule*, not yesterday's tally.
test('every member the Border gave up on classifies as FAULT, never COLD (FR-008)', () => {
  const givenUp = live.members.filter(
    (m) => !m.live && ['unreachable', 'quarantined', 'removed'].includes(m.state),
  );
  assert.ok(givenUp.length > 0, 'fixture should contain at least one such member');

  for (const m of givenUp) {
    assert.equal(classifyHealth(m, NOW), 'FAULT', `${m.member_id} must be FAULT`);
  }

  const tally = healthTally(live.members, NOW);
  assert.ok(tally.FAULT >= givenUp.length, 'no fault may be swallowed into COLD');
});

test('the two health populations stay separable in the live fixture', () => {
  // COLD (never started, normal) and FAULT (died, needs attention) must both
  // be present and distinct — that is the entire reason for four states.
  const tally = healthTally(live.members, NOW);
  assert.ok(tally.COLD > 0 && tally.FAULT > 0, 'both populations present');
  assert.notEqual(tally.COLD + tally.FAULT, tally.COLD, 'FAULT is not merged into COLD');
});

test('scale fixture exercises all four states', () => {
  const big = JSON.parse(readFileSync(resolve(FIXTURES, 'scale-100.json'), 'utf8'));
  const tally = healthTally(big.members, NOW);
  for (const state of ['HOT', 'WARM', 'COLD', 'FAULT']) {
    assert.ok(tally[state] > 0, `${state} should be present in scale-100`);
  }
});
