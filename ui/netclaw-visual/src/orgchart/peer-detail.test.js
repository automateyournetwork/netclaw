import { test } from 'node:test';
import assert from 'node:assert/strict';

import { PLACEHOLDER, STATE_SUMMARY, peerDetailView } from './peer-detail.js';
import { PEER_STATES } from './liveness.js';

/**
 * US1 / FR-002/003/004 and visual-contract §6 rule P2.
 *
 * The binding rule is **never render `undefined`**. That is not a style
 * preference: routing peers to the existing `peer-core` branch would have
 * produced exactly that, because it expects a /api/graph BGP payload
 * (peer.as, peer.routerId, peer.peerIp, peer.routesReceived) which is absent
 * from the /api/n2n shape the org chart carries.
 */

const NOW = Math.floor(Date.parse('2026-08-06T23:00:00Z') / 1000);

const NATE = {
  identity: 'as65006-6.6.6.6', display_name: 'Nate', state: 'federated',
  channel_state: 'up', stale: false, chat_enabled: 1,
  inventory_received_at: '2026-08-06T20:12:06Z', in_flight_tasks: [],
};

/** Walk every value in the view-model. */
function values(view) {
  return Object.entries(view).flatMap(([k, v]) =>
    Array.isArray(v) ? v.map((x, i) => [`${k}[${i}]`, x]) : [[k, v]]);
}

test('P2: no field is ever undefined, for any input', () => {
  const inputs = [
    NATE,
    {},                                   // entirely empty row
    undefined,                            // no row at all
    { identity: 'as65003-3.3.3.3' },      // identity only
    { ...NATE, channel_state: null, inventory_received_at: null, in_flight_tasks: null },
  ];
  for (const row of inputs) {
    const view = peerDetailView(row, NOW);
    for (const [key, v] of values(view)) {
      assert.notEqual(v, undefined, `${key} is undefined for input ${JSON.stringify(row)}`);
    }
  }
});

test('empty values render as an explicit placeholder, not a blank', () => {
  const view = peerDetailView({}, NOW);
  assert.equal(view.identity, PLACEHOLDER);
  assert.equal(view.channelState, PLACEHOLDER);
  assert.equal(view.inventoryReceivedAt, PLACEHOLDER);
});

test('FR-003: every required row is present', () => {
  const view = peerDetailView(NATE, NOW, { label: 'Nate' });
  for (const key of ['heading', 'identity', 'state', 'channelState',
                     'inventoryAge', 'inventoryJudgement', 'chatEnabled', 'inFlightTasks']) {
    assert.ok(key in view, `missing required row: ${key}`);
  }
  assert.equal(view.heading, 'Nate');
  assert.equal(view.identity, 'as65006-6.6.6.6');
  assert.equal(view.state, 'LIVE');
});

test('identity is shown separately so the two Hermes rows are distinguishable', () => {
  const fed = peerDetailView(
    { identity: 'as65008-8.8.8.8', display_name: 'Hermes', state: 'federated',
      channel_state: 'unknown', stale: true, inventory_received_at: '2026-07-23T00:34:20Z' },
    NOW, { label: 'Hermes (as65008)' });
  const sev = peerDetailView(
    { identity: 'as65007-8.8.8.8', display_name: 'Hermes', state: 'severed',
      channel_state: 'unknown', inventory_received_at: null },
    NOW, { label: 'Hermes (as65007)' });

  assert.notEqual(fed.identity, sev.identity);
  assert.notEqual(fed.state, sev.state);
  assert.notEqual(fed.heading, sev.heading);
});

test('FR-004: inventory age is operator-readable, never a bare timestamp', () => {
  const byrn = peerDetailView(
    { identity: 'as65099-10.255.255.1', state: 'federated', channel_state: 'unknown',
      stale: true, inventory_received_at: '2026-07-25T16:43:51Z' }, NOW);
  assert.match(byrn.inventoryAge, /\d+d ago/);
  assert.equal(byrn.inventoryJudgement, 'stale');
  assert.ok(!/^\d{4}-\d{2}-\d{2}/.test(byrn.inventoryAge), 'must not be a raw timestamp');
});

test('never-received reads as never, not as zero', () => {
  const ab = peerDetailView(
    { identity: 'as65003-3.3.3.3', state: 'federated', channel_state: 'unknown',
      inventory_received_at: null }, NOW);
  assert.equal(ab.inventoryAge, 'never');
  assert.equal(ab.inventoryJudgement, 'never');
  assert.equal(ab.state, 'UNKNOWN');
});

test('an empty task list renders an explicit "none"', () => {
  // A blank region could read as "failed to load" rather than "there are none".
  assert.equal(peerDetailView(NATE, NOW).inFlightText, 'none');
  const busy = peerDetailView(
    { ...NATE, in_flight_tasks: [{ task_id: 'a' }, { task_id: 'b' }] }, NOW);
  assert.equal(busy.inFlightText, '2 in flight');
});

test('chat state renders as words, not a raw integer', () => {
  assert.equal(peerDetailView({ ...NATE, chat_enabled: 1 }, NOW).chatText, 'enabled');
  assert.equal(peerDetailView({ ...NATE, chat_enabled: 0 }, NOW).chatText, 'disabled');
});

test('every state has a human summary — the panel says what it MEANS', () => {
  for (const s of PEER_STATES) {
    assert.ok(STATE_SUMMARY[s], `no summary for ${s}`);
    assert.notEqual(STATE_SUMMARY[s], PLACEHOLDER);
  }
});

test('FR-016/017: the UNKNOWN summary does not read as a failure', () => {
  assert.match(STATE_SUMMARY.UNKNOWN, /not a failure/i);
});

test('FR-045: a vanished peer carries an explicit notice', () => {
  const gone = peerDetailView(NATE, NOW, { presentInFeed: false });
  assert.equal(gone.presentInFeed, false);
  assert.ok(gone.notInFeedNotice, 'must state it is no longer present');
  assert.match(gone.notInFeedNotice, /last known/i);

  const here = peerDetailView(NATE, NOW);
  assert.equal(here.notInFeedNotice, null, 'no notice when the peer is present');
});

test('a malformed row does not throw', () => {
  for (const bad of [undefined, null, {}, 42, 'peer', []]) {
    assert.doesNotThrow(() => peerDetailView(bad, NOW));
  }
});

test('the view-model contains no BGP-shaped fields', () => {
  // Guards against someone "unifying" this with peer-core, which is what would
  // reintroduce the undefined-panel defect.
  const view = peerDetailView(NATE, NOW);
  for (const leaked of ['as', 'routerId', 'peerIp', 'routesReceived', 'adjRibIn']) {
    assert.ok(!(leaked in view), `${leaked} belongs to the /api/graph shape, not this panel`);
  }
});
