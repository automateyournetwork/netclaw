import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { categorizeMember, categorizeMembers, toCatalog, UNCATEGORISED } from './categorize.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = resolve(HERE, '../../../../specs/072-hud-2-org-chart/fixtures');
const load = (n) => JSON.parse(readFileSync(resolve(FIXTURES, n), 'utf8'));

const live = load('live-29.json');
const catalog = load('integration-catalog.json');

test('the shipped catalog supplies a real middle tier', () => {
  assert.ok(catalog.length > 50, 'catalog should be substantial');
  const categories = new Set(catalog.map((c) => c.category));
  assert.ok(categories.size > 10, 'many distinct categories');
});

test('live members auto-categorise at the measured rate (FR-006)', () => {
  const grouped = categorizeMembers(live.members, catalog);
  const agents = live.members.filter((m) => m.node_type !== 'edge');

  let placed = 0;
  for (const [name, members] of grouped) {
    if (name !== UNCATEGORISED) placed += members.length;
  }
  // Measured 25/27 agent members at spec time. Assert the floor, not the exact
  // number — the catalog gains prefixes over time and that should not fail CI.
  assert.ok(placed >= 24, `expected >=24 categorised agent members, got ${placed}`);
  assert.ok(placed / agents.length > 0.85, 'coverage should exceed 85%');
});

test('edge nodes are excluded from the member chart entirely (FR-007)', () => {
  const grouped = categorizeMembers(live.members, catalog);
  const all = [...grouped.values()].flat();
  assert.equal(all.filter((m) => m.node_type === 'edge').length, 0);
  assert.equal(all.length, live.members.filter((m) => m.node_type !== 'edge').length);
});

test('no member is ever dropped — unmatched go to Uncategorised (FR-006a)', () => {
  const unc = load('uncategorised.json');
  const grouped = categorizeMembers(unc.members, catalog);
  const agents = unc.members.filter((m) => m.node_type !== 'edge');

  assert.equal(grouped.size, 1, 'a catalog matching nothing yields one bucket');
  assert.ok(grouped.has(UNCATEGORISED));
  assert.equal(grouped.get(UNCATEGORISED).length, agents.length, 'nothing dropped');
});

test('an empty or missing catalog degrades to Uncategorised, never throws', () => {
  for (const bad of [[], null, undefined, 'nope', [{}, { prefixes: 'x' }]]) {
    const grouped = categorizeMembers(live.members, bad);
    const names = [...grouped.keys()];
    assert.deepEqual(names, [UNCATEGORISED], `catalog ${JSON.stringify(bad)} should degrade`);
  }
});

test('a member with no skills is Uncategorised, not dropped', () => {
  assert.equal(categorizeMember({ member_id: 'r/x', skills: [] }, catalog), UNCATEGORISED);
  assert.equal(categorizeMember({ member_id: 'r/x' }, catalog), UNCATEGORISED);
  assert.equal(categorizeMember({ member_id: 'r/x', skills: [1, null] }, catalog), UNCATEGORISED);
});

// Constitution Principle VI made falsifiable: the catalog is an argument, so
// a different operator's catalog must produce a different, correct chart from
// the same code and the same members.
test('a different catalog produces a different correct chart (vendor neutrality)', () => {
  const members = [
    { member_id: 'r/a', skills: ['acme-deploy', 'acme-verify'] },
    { member_id: 'r/b', skills: ['zeta-scan'] },
  ];
  const catalogA = [
    { id: 'acme', category: 'Provisioning', prefixes: ['acme-'] },
    { id: 'zeta', category: 'Security', prefixes: ['zeta-'] },
  ];
  const catalogB = [
    { id: 'acme', category: 'Vendor A Stack', prefixes: ['acme-'] },
    { id: 'zeta', category: 'Vendor A Stack', prefixes: ['zeta-'] },
  ];

  const a = categorizeMembers(members, catalogA);
  assert.deepEqual([...a.keys()].sort(), ['Provisioning', 'Security']);

  const b = categorizeMembers(members, catalogB);
  assert.deepEqual([...b.keys()], ['Vendor A Stack']);
  assert.equal(b.get('Vendor A Stack').length, 2);

  // Same code, same members, different catalog, different correct answer.
  assert.notDeepEqual([...a.keys()], [...b.keys()]);
});

test('most frequent category wins; ties break deterministically by catalog order', () => {
  const cat = [
    { id: 'x', category: 'Alpha', prefixes: ['x-'] },
    { id: 'y', category: 'Beta', prefixes: ['y-'] },
  ];
  assert.equal(categorizeMember({ skills: ['x-1', 'x-2', 'y-1'] }, cat), 'Alpha', 'majority wins');

  const tie = { skills: ['y-1', 'x-1'] };
  assert.equal(categorizeMember(tie, cat), 'Alpha', 'tie breaks to earlier catalog entry');
  assert.equal(categorizeMember(tie, cat), categorizeMember(tie, cat), 'deterministic');
});

test('categorizeMembers does not mutate its inputs', () => {
  const before = JSON.stringify(live.members);
  categorizeMembers(live.members, catalog);
  assert.equal(JSON.stringify(live.members), before);
});

test('toCatalog tolerates a malformed integration list', () => {
  assert.deepEqual(toCatalog(null), []);
  assert.deepEqual(toCatalog([{ id: 'a' }, { category: 'C' }]), []);
  assert.equal(toCatalog([{ id: 'a', category: 'C', prefixes: ['a-'] }]).length, 1);
});

test('scale fixture categorises without loss', () => {
  const big = load('scale-100.json');
  const grouped = categorizeMembers(big.members, catalog);
  const total = [...grouped.values()].flat().length;
  assert.equal(total, big.members.filter((m) => m.node_type !== 'edge').length);
});
