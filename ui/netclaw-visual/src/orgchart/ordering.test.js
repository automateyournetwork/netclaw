import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { orderCategories, orderMembers, categoryHeat, UNCATEGORISED } from './ordering.js';
import { categorizeMembers } from './categorize.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = resolve(HERE, '../../../../specs/072-hud-2-org-chart/fixtures');
const load = (n) => JSON.parse(readFileSync(resolve(FIXTURES, n), 'utf8'));

const live = load('live-29.json');
const catalog = load('integration-catalog.json');
const NOW = 1_785_000_000;

const hot = (id) => ({ member_id: id, display_name: id, live: true });
const cold = (id) => ({ member_id: id, display_name: id, live: false, state: 'provisioned' });

test('categories containing a live member lead (FR-006b)', () => {
  const ordered = orderCategories(
    new Map([
      ['Cold Group', [cold('a'), cold('b'), cold('c')]],
      ['Hot Group', [hot('x')]],
    ]),
    NOW,
  );
  assert.equal(ordered[0].name, 'Hot Group', 'heat beats size');
});

test('equal heat falls back to size', () => {
  const ordered = orderCategories(
    new Map([
      ['Small', [cold('a')]],
      ['Large', [cold('b'), cold('c'), cold('d')]],
    ]),
    NOW,
  );
  assert.equal(ordered[0].name, 'Large');
});

test('equal heat and size falls back to name, deterministically', () => {
  const input = new Map([
    ['Zulu', [cold('a')]],
    ['Alpha', [cold('b')]],
  ]);
  const first = orderCategories(input, NOW).map((c) => c.name);
  const second = orderCategories(input, NOW).map((c) => c.name);
  assert.deepEqual(first, ['Alpha', 'Zulu']);
  assert.deepEqual(first, second, 'repeat runs must agree');
});

test('Uncategorised sorts last even when it holds a HOT member', () => {
  // True of the reference Border: ipfabric is live but uncategorised.
  const ordered = orderCategories(
    new Map([
      [UNCATEGORISED, [hot('ipfabric'), hot('forward')]],
      ['Labs', [cold('cml')]],
    ]),
    NOW,
  );
  assert.equal(ordered.at(-1).name, UNCATEGORISED, 'residue bucket is always last');
  assert.ok(ordered.at(-1).heat > 0, 'even though it is the hottest group');
});

test('ordering the real Border puts hot groups first and Uncategorised last', () => {
  const grouped = categorizeMembers(live.members, catalog);
  const ordered = orderCategories(grouped, NOW);

  assert.ok(ordered.length > 5, 'the real Border yields many categories');
  assert.equal(ordered.at(-1).name, UNCATEGORISED);

  const realGroups = ordered.filter((c) => c.name !== UNCATEGORISED);
  const firstZeroHeat = realGroups.findIndex((c) => c.heat === 0);
  if (firstZeroHeat !== -1) {
    const after = realGroups.slice(firstZeroHeat);
    assert.ok(after.every((c) => c.heat === 0), 'no hot group may appear after a cold one');
  }
});

test('every member survives ordering — nothing dropped', () => {
  const grouped = categorizeMembers(live.members, catalog);
  const before = [...grouped.values()].flat().length;
  const after = orderCategories(grouped, NOW).reduce((n, c) => n + c.members.length, 0);
  assert.equal(after, before);
});

test('orderCategories is total on junk input', () => {
  assert.deepEqual(orderCategories(null, NOW), []);
  assert.deepEqual(orderCategories(undefined, NOW), []);
  assert.deepEqual(orderCategories(new Map(), NOW), []);
  assert.equal(orderCategories([['A', null]], NOW)[0].members.length, 0);
});

test('categoryHeat counts only HOT members', () => {
  assert.equal(categoryHeat([hot('a'), cold('b'), hot('c')], NOW), 2);
  assert.equal(categoryHeat([], NOW), 0);
  assert.equal(categoryHeat(null, NOW), 0);
});

test('within a category: HOT, then FAULT, then WARM, then COLD', () => {
  const members = [
    cold('d-cold'),
    { member_id: 'b-warm', display_name: 'b-warm', live: false, heartbeat_age_s: 10 },
    hot('a-hot'),
    { member_id: 'c-fault', display_name: 'c-fault', live: false, state: 'unreachable' },
  ];
  const ordered = orderMembers(members, NOW).map((m) => m.display_name);
  assert.deepEqual(ordered, ['a-hot', 'c-fault', 'b-warm', 'd-cold']);
});

test('FAULT ranks above WARM so a dead claw is not buried in its column', () => {
  const fault = { member_id: 'f', display_name: 'f', live: false, state: 'unreachable' };
  const warm = { member_id: 'w', display_name: 'w', live: false, heartbeat_age_s: 5 };
  assert.deepEqual(orderMembers([warm, fault], NOW).map((m) => m.display_name), ['f', 'w']);
});

test('orderMembers does not mutate its input', () => {
  const members = [cold('b'), hot('a')];
  const snapshot = JSON.stringify(members);
  orderMembers(members, NOW);
  assert.equal(JSON.stringify(members), snapshot);
});
