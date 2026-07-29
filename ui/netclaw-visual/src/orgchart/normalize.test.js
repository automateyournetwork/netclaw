import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { dedupePeers, resolveLabel, disambiguateLabels } from './normalize.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = resolve(HERE, '../../../../specs/072-hud-2-org-chart/fixtures');
const live = JSON.parse(readFileSync(resolve(FIXTURES, 'live-29.json'), 'utf8'));

test('the two Hermes peers are distinct identities, not a duplicate record (FR-014)', () => {
  // Implementation finding: the spec assumed one peer reported twice. In fact
  // these are two different AS numbers sharing a router-id and a display name —
  // Hermes re-enrolled, leaving the old severed entry behind.
  const hermes = live.peers.filter((p) => p.display_name === 'Hermes');
  assert.equal(hermes.length, 2);
  assert.notEqual(hermes[0].identity, hermes[1].identity, 'distinct identities');
  assert.deepEqual(hermes.map((p) => p.state).sort(), ['federated', 'severed']);

  // Both must therefore survive dedup — they are real, separate peers.
  const deduped = dedupePeers(live.peers);
  assert.equal(deduped.filter((p) => p.display_name === 'Hermes').length, 2);
});

test('dedupePeers collapses a genuine duplicate identity, most restrictive state wins', () => {
  const dupe = [
    { identity: 'as1-1.1.1.1', display_name: 'X', state: 'federated' },
    { identity: 'as1-1.1.1.1', display_name: 'X', state: 'severed' },
  ];
  const out = dedupePeers(dupe);
  assert.equal(out.length, 1);
  assert.equal(out[0].state, 'severed');
});

test('disambiguateLabels makes the two Hermes peers tellable apart (FR-014)', () => {
  const labelled = disambiguateLabels(dedupePeers(live.peers));
  const hermes = labelled.filter((l) => l.label.startsWith('Hermes'));
  assert.equal(hermes.length, 2);
  assert.notEqual(hermes[0].label, hermes[1].label, 'same-named peers must differ');
  for (const h of hermes) assert.match(h.label, /^Hermes \(as\d+\)$/);
});

test('disambiguateLabels leaves already-unique labels untouched', () => {
  const labelled = disambiguateLabels(dedupePeers(live.peers));
  const ab = labelled.find((l) => l.entity.display_name === 'AB');
  assert.equal(ab.label, 'AB', 'no qualifier on a unique name');
});

test('dedupePeers preserves distinct peers and first-seen order', () => {
  const deduped = dedupePeers(live.peers);
  const identities = deduped.map((p) => p.identity);
  assert.equal(new Set(identities).size, identities.length, 'no duplicate identities remain');
  assert.equal(deduped.length, live.peers.length, 'live fixture has no true identity duplicates');
});

test('dedupePeers does not mutate its input', () => {
  const before = JSON.stringify(live.peers);
  dedupePeers(live.peers);
  assert.equal(JSON.stringify(live.peers), before);
});

test('dedupePeers is total on junk input', () => {
  assert.deepEqual(dedupePeers(null), []);
  assert.deepEqual(dedupePeers(undefined), []);
  assert.deepEqual(dedupePeers([]), []);
  assert.equal(dedupePeers([null, undefined, 42]).length, 0);
});

test('both real edge nodes with display_name:null resolve to non-empty labels (FR-015)', () => {
  const edges = live.members.filter((m) => m.node_type === 'edge');
  assert.equal(edges.length, 2, 'fixture should contain 2 edge nodes');

  for (const edge of edges) {
    assert.equal(edge.display_name, null, 'fixture edge should have a null display_name');
    const label = resolveLabel(edge);
    assert.ok(label.length > 0, 'label must never be empty');
    assert.notEqual(label, 'unknown', 'member_id tail should be used, not the last-resort default');
    assert.ok(!label.includes('/'), 'label should be the tail, not the full member_id');
  }
});

test('resolveLabel precedence: display_name > member_id tail > identity > unknown', () => {
  assert.equal(resolveLabel({ display_name: 'pyats', member_id: 'r/x', identity: 'i' }), 'pyats');
  assert.equal(resolveLabel({ display_name: null, member_id: 'johns-risk/cml' }), 'cml');
  assert.equal(resolveLabel({ display_name: '   ', member_id: 'johns-risk/viz' }), 'viz');
  assert.equal(resolveLabel({ identity: 'as65003-3.3.3.3' }), 'as65003-3.3.3.3');
  assert.equal(resolveLabel({}), 'unknown');
  assert.equal(resolveLabel(null), 'unknown');
});

test('every member and peer in the live fixture gets a non-empty label', () => {
  for (const entity of [...live.members, ...dedupePeers(live.peers)]) {
    assert.ok(resolveLabel(entity).length > 0);
  }
});
