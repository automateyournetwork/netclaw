import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  createFeedState, isUsablePayload, recordFailure, recordSuccess,
  renderablePayload, staleIndicator,
} from './feed-state.js';

/**
 * FR-041/042/043 — freeze and flag.
 *
 * This is the file that stops the HUD fabricating an outage. If a failed poll
 * were allowed to recompute liveness, the mesh daemon going down would render all
 * seven peers as dead and send an operator chasing a total outage that does not
 * exist.
 *
 * The symmetric error is tested too: a SUCCESSFUL poll with zero peers is a real
 * empty state, not a failure.
 */

const T0 = 1786060000000;
const GOOD = { identity: 'as65001-4.4.4.4', peers: [{ identity: 'as65006-6.6.6.6' }], members: [] };

test('a successful poll caches the payload and clears degraded', () => {
  const f = recordSuccess(createFeedState(), GOOD, T0);
  assert.equal(f.lastGood, GOOD);
  assert.equal(f.lastGoodAt, T0);
  assert.equal(f.degraded, false);
  assert.equal(f.consecutiveFailures, 0);
});

test('FR-041: a failed poll does NOT touch lastGood', () => {
  const f = recordSuccess(createFeedState(), GOOD, T0);
  recordFailure(f, new Error('ECONNREFUSED'), T0 + 5000);
  assert.equal(f.lastGood, GOOD, 'the frozen payload must survive the failure');
  assert.equal(f.lastGoodAt, T0, 'the age reference must not move');
  assert.equal(f.degraded, true);
});

test('FR-041: the scene keeps rendering the last good payload while degraded', () => {
  const f = recordSuccess(createFeedState(), GOOD, T0);
  recordFailure(f, 'daemon down', T0 + 1000);
  assert.equal(renderablePayload(f), GOOD);
});

test('every failure mode is a failure: throw, non-2xx, unparseable', () => {
  for (const err of [new Error('fetch failed'), 'HTTP 502', new SyntaxError('Unexpected token')]) {
    const f = recordSuccess(createFeedState(), GOOD, T0);
    recordFailure(f, err, T0 + 1000);
    assert.equal(f.degraded, true);
    assert.equal(f.lastGood, GOOD);
  }
});

test('a wrongly-shaped 200 response is treated as a failure, not cached', () => {
  // Caching garbage would then freeze it and present it as authoritative.
  const f = recordSuccess(createFeedState(), GOOD, T0);
  recordSuccess(f, { peers: 'not-an-array' }, T0 + 1000);
  assert.equal(f.degraded, true);
  assert.equal(f.lastGood, GOOD, 'the previous good payload must be kept');
});

test('ZERO PEERS on a successful poll is NOT a failure', () => {
  // The symmetric error: conflating "the daemon says nothing is federated" with
  // "I could not reach the daemon" is the same class of mistake inverted.
  const empty = { identity: 'as65001-4.4.4.4', peers: [], members: [] };
  assert.equal(isUsablePayload(empty), true);
  const f = recordSuccess(createFeedState(), empty, T0);
  assert.equal(f.degraded, false);
  assert.equal(renderablePayload(f), empty);
  assert.equal(staleIndicator(f, T0).message, null, 'an empty fleet must not be flagged as stale');
});

test('consecutive failures accumulate and reset on success (FR-043)', () => {
  const f = recordSuccess(createFeedState(), GOOD, T0);
  recordFailure(f, 'x', T0 + 1000);
  recordFailure(f, 'x', T0 + 2000);
  recordFailure(f, 'x', T0 + 3000);
  assert.equal(f.consecutiveFailures, 3);

  recordSuccess(f, GOOD, T0 + 4000);
  assert.equal(f.consecutiveFailures, 0);
  assert.equal(f.degraded, false, 'FR-043: recovery needs no reload and no acknowledgement');
});

test('FR-042: the indicator reports the age of the last good poll', () => {
  const f = recordSuccess(createFeedState(), GOOD, T0);
  recordFailure(f, 'down', T0 + 90000);
  const ind = staleIndicator(f, T0 + 90000);
  assert.equal(ind.degraded, true);
  assert.equal(ind.staleForSeconds, 90);
  assert.equal(ind.everSucceeded, true);
  assert.match(ind.message, /90s ago/);
});

test('never-succeeded is reported differently from lost-contact', () => {
  // Showing an age of 0 for "we never reached the daemon" would be a fabricated
  // reassurance — it is a first-run/misconfiguration story, not a staleness one.
  const f = recordFailure(createFeedState(), 'ECONNREFUSED', T0);
  const ind = staleIndicator(f, T0);
  assert.equal(ind.everSucceeded, false);
  assert.equal(ind.staleForSeconds, null);
  assert.match(ind.message, /never reached/);
  assert.equal(renderablePayload(f), null, 'nothing to freeze — caller renders an empty state');
});

test('a healthy feed produces no indicator at all', () => {
  const f = recordSuccess(createFeedState(), GOOD, T0);
  const ind = staleIndicator(f, T0 + 1000);
  assert.equal(ind.degraded, false);
  assert.equal(ind.message, null);
});

test('isUsablePayload accepts only an object with a peers array', () => {
  assert.equal(isUsablePayload({ peers: [] }), true);
  for (const bad of [null, undefined, 42, 'x', {}, { peers: null }, { peers: {} }, []]) {
    assert.equal(isUsablePayload(bad), false, JSON.stringify(bad));
  }
});
