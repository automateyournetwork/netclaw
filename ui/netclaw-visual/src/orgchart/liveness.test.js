import { test } from 'node:test';
import assert from 'node:assert/strict';

import {
  IDLE, LIVE, PEER_STATES, SEVERED, STALE, UNKNOWN, UNREACHABLE,
  classifyPeer, isActionable, peerViewState,
} from './liveness.js';

/**
 * US3 / FR-012/016/017.
 *
 * Driven by the REAL live feed as of 2026-08-06, because the defect is only
 * visible against real data: five of seven peers fall into
 * `colorForStructural`'s healthy catch-all and render identically to Nate. Each
 * of those five is asserted here by name.
 */

const NOW = Math.floor(Date.parse('2026-08-06T23:00:00Z') / 1000);

/** The live /api/n2n peers[] rows, trimmed to the fields classification reads. */
const FEED = {
  nate: {
    identity: 'as65006-6.6.6.6', display_name: 'Nate', state: 'federated',
    channel_state: 'up', stale: false, inventory_received_at: '2026-08-06T20:12:06Z',
  },
  byrn: {
    identity: 'as65099-10.255.255.1', display_name: 'Byrn', state: 'federated',
    channel_state: 'unknown', stale: true, inventory_received_at: '2026-07-25T16:43:51Z',
  },
  nicholas: {
    identity: 'as65007-7.7.7.7', display_name: 'Nicholas', state: 'federated',
    channel_state: 'unknown', stale: true, inventory_received_at: '2026-07-18T17:04:37Z',
  },
  hermesFederated: {
    identity: 'as65008-8.8.8.8', display_name: 'Hermes', state: 'federated',
    channel_state: 'unknown', stale: true, inventory_received_at: '2026-07-23T00:34:20Z',
  },
  hermesSevered: {
    identity: 'as65007-8.8.8.8', display_name: 'Hermes', state: 'severed',
    channel_state: 'unknown', stale: null, inventory_received_at: null,
  },
  ab: {
    identity: 'as65003-3.3.3.3', display_name: 'AB', state: 'federated',
    channel_state: 'unknown', stale: null, inventory_received_at: null,
  },
  carapace: {
    identity: 'as65100-10.0.0.1', display_name: 'Carapace', state: 'federated',
    channel_state: 'unknown', stale: null, inventory_received_at: null,
  },
};

test('all six states are declared', () => {
  assert.equal(PEER_STATES.length, 6);
  for (const s of [LIVE, IDLE, STALE, UNKNOWN, UNREACHABLE, SEVERED]) {
    assert.ok(PEER_STATES.includes(s), s);
  }
});

test('the live feed classifies into four distinct states', () => {
  assert.equal(classifyPeer(FEED.nate, NOW), LIVE);
  assert.equal(classifyPeer(FEED.byrn, NOW), STALE);
  assert.equal(classifyPeer(FEED.nicholas, NOW), STALE);
  assert.equal(classifyPeer(FEED.hermesFederated, NOW), STALE);
  assert.equal(classifyPeer(FEED.hermesSevered, NOW), SEVERED);
  assert.equal(classifyPeer(FEED.ab, NOW), UNKNOWN);
  assert.equal(classifyPeer(FEED.carapace, NOW), UNKNOWN);
});

test('THE DEFECT: the five catch-all peers no longer match healthy Nate', () => {
  // Every one of these hit `return 0x8ad6ff` in colorForStructural and rendered
  // identically to a peer with a live channel.
  const nate = classifyPeer(FEED.nate, NOW);
  for (const [name, row] of Object.entries({
    byrn: FEED.byrn, nicholas: FEED.nicholas, hermes: FEED.hermesFederated,
    ab: FEED.ab, carapace: FEED.carapace,
  })) {
    assert.notEqual(classifyPeer(row, NOW), nate,
      `${name} still classifies the same as healthy Nate — the defect is not fixed`);
  }
});

test('FR-016/017: UNKNOWN is distinct from both healthy and dead', () => {
  const unknown = classifyPeer(FEED.ab, NOW);
  assert.notEqual(unknown, LIVE);
  assert.notEqual(unknown, IDLE);
  assert.notEqual(unknown, UNREACHABLE);
  assert.notEqual(unknown, SEVERED);
  assert.equal(unknown, UNKNOWN);
});

test('FR-017: UNKNOWN is not actionable — never heard from is not a fault', () => {
  assert.equal(isActionable(UNKNOWN), false);
  assert.equal(isActionable(STALE), false);
  assert.equal(isActionable(UNREACHABLE), true);
  assert.equal(isActionable(SEVERED), true);
});

test('FR-017: a severed peer is never reported as anything else', () => {
  // Severed wins over every other signal, including a live channel — claiming a
  // severed peer is live is the dangerous direction of the error.
  const contradictory = {
    ...FEED.nate, state: 'severed', channel_state: 'up', stale: false,
  };
  assert.equal(classifyPeer(contradictory, NOW), SEVERED);
});

test('a live channel outranks a stale inventory', () => {
  // Legitimate combination: channel came up before the inventory refreshed.
  const row = { ...FEED.byrn, channel_state: 'up' };
  assert.equal(classifyPeer(row, NOW), LIVE);
});

test('unreachable and reconnecting both classify as UNREACHABLE', () => {
  for (const channel of ['unreachable', 'reconnecting']) {
    assert.equal(classifyPeer({ ...FEED.byrn, channel_state: channel }, NOW), UNREACHABLE);
  }
});

test('IDLE is the normal steady state, not an error', () => {
  const row = {
    identity: 'as65010-10.10.10.10', state: 'federated', channel_state: 'unknown',
    stale: false, inventory_received_at: '2026-08-06T22:55:00Z',
  };
  assert.equal(classifyPeer(row, NOW), IDLE);
});

test('classification is case-insensitive on API strings', () => {
  assert.equal(classifyPeer({ ...FEED.nate, channel_state: 'UP' }, NOW), LIVE);
  assert.equal(classifyPeer({ ...FEED.hermesSevered, state: 'SEVERED' }, NOW), SEVERED);
});

test('a malformed row does not throw', () => {
  for (const bad of [undefined, null, {}, 42, 'peer']) {
    assert.doesNotThrow(() => classifyPeer(bad, NOW));
  }
});

test('peerViewState carries identity separately from label', () => {
  // Two peers share the display name "Hermes"; the panel needs identity to tell
  // them apart.
  const a = peerViewState(FEED.hermesFederated, NOW, { label: 'Hermes (as65008)' });
  const b = peerViewState(FEED.hermesSevered, NOW, { label: 'Hermes (as65007)' });
  assert.notEqual(a.identity, b.identity);
  assert.notEqual(a.state, b.state);
});

test('peerViewState defaults presentInFeed true and honours false (FR-045)', () => {
  assert.equal(peerViewState(FEED.nate, NOW).presentInFeed, true);
  assert.equal(peerViewState(FEED.nate, NOW, { presentInFeed: false }).presentInFeed, false);
});

test('chat_enabled accepts both boolean and SQLite integer forms', () => {
  assert.equal(peerViewState({ ...FEED.nate, chat_enabled: 1 }, NOW).chatEnabled, true);
  assert.equal(peerViewState({ ...FEED.nate, chat_enabled: 0 }, NOW).chatEnabled, false);
  assert.equal(peerViewState({ ...FEED.nate, chat_enabled: true }, NOW).chatEnabled, true);
});
