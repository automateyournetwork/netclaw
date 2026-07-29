import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { computeLayout, appendMember, LAYOUT } from './layout.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = resolve(HERE, '../../../../specs/072-hud-2-org-chart/fixtures');
const load = (n) => JSON.parse(readFileSync(resolve(FIXTURES, n), 'utf8'));

const catalog = load('integration-catalog.json');
const NOW = 1_785_000_000;
const FIXTURE_NAMES = ['empty.json', 'single.json', 'live-29.json', 'scale-100.json', 'uncategorised.json'];

const key = (p) => `${p.x.toFixed(4)},${p.y.toFixed(4)},${p.z.toFixed(4)}`;

for (const name of FIXTURE_NAMES) {
  test(`[${name}] no two nodes share a position (SC-004)`, () => {
    const { nodes } = computeLayout(load(name), catalog, NOW);
    const seen = new Map();
    for (const n of nodes) {
      const k = key(n.position);
      assert.ok(!seen.has(k), `${n.id} overlaps ${seen.get(k)} at ${k}`);
      seen.set(k, n.id);
    }
  });

  test(`[${name}] every node has a non-empty label (FR-015)`, () => {
    const { nodes } = computeLayout(load(name), catalog, NOW);
    for (const n of nodes) {
      assert.ok(typeof n.label === 'string' && n.label.length > 0, `${n.id} has a blank label`);
    }
  });

  test(`[${name}] all four bands exist regardless of data (FR-033)`, () => {
    const { bands } = computeLayout(load(name), catalog, NOW);
    assert.deepEqual(bands.map((b) => b.id), ['external', 'boundary', 'edgeLane', 'internal']);
    assert.ok(bands.find((b) => b.isBoundary), 'the trust boundary is always drawn (FR-002)');
  });

  test(`[${name}] layout is deterministic`, () => {
    const a = computeLayout(load(name), catalog, NOW);
    const b = computeLayout(load(name), catalog, NOW);
    assert.deepEqual(a.nodes.map((n) => [n.id, key(n.position)]), b.nodes.map((n) => [n.id, key(n.position)]));
  });
}

test('empty install renders structure and CTAs, not a void (FR-033a)', () => {
  const { nodes, bands } = computeLayout(load('empty.json'), catalog, NOW);
  assert.equal(nodes.filter((n) => n.kind === 'member').length, 0);
  assert.equal(nodes.filter((n) => n.kind === 'border').length, 1, 'the Border still renders');
  for (const id of ['external', 'edgeLane', 'internal']) {
    const band = bands.find((b) => b.id === id);
    assert.equal(band.empty, true);
    assert.ok(band.emptyCta && band.emptyCta.length > 0, `${id} needs a CTA`);
  }
});

test('a non-Border install still renders the structure (FR-033b)', () => {
  const payload = { ...load('live-29.json'), risk: { role: 'member', risk_name: 'not-a-border' } };
  const { nodes, bands } = computeLayout(payload, catalog, NOW);
  assert.equal(bands.length, 4);
  assert.ok(nodes.length > 1, 'must not early-return to an empty scene');
});

test('external band sits above the boundary, internal below (FR-001/002)', () => {
  const { nodes, bands } = computeLayout(load('live-29.json'), catalog, NOW);
  const boundaryY = bands.find((b) => b.isBoundary).y;

  for (const n of nodes.filter((x) => x.kind === 'peer')) {
    assert.ok(n.position.y > boundaryY, `peer ${n.id} must be north of the boundary`);
  }
  for (const n of nodes.filter((x) => x.kind === 'member')) {
    assert.ok(n.position.y < boundaryY, `member ${n.id} must be south of the boundary`);
  }
  const border = nodes.find((n) => n.kind === 'border');
  assert.ok(border.position.y < boundaryY, 'the Border is inside its own boundary');
});

test('edge nodes go to the edge lane, never a member column (FR-007)', () => {
  const { nodes } = computeLayout(load('live-29.json'), catalog, NOW);
  const edges = nodes.filter((n) => n.kind === 'edge');
  assert.equal(edges.length, 2, 'both enrolled phones are placed');

  for (const e of edges) {
    assert.equal(e.band, 'edgeLane');
    assert.ok(e.position.x >= LAYOUT.edgeLaneX, 'edge lane is offset from the chart');
    assert.equal(e.category, undefined, 'an edge is never categorised');
  }
  const memberXs = new Set(nodes.filter((n) => n.kind === 'member').map((n) => n.position.x));
  for (const e of edges) assert.ok(!memberXs.has(e.position.x), 'edge must not sit in a member column');
});

test('edge lane wraps instead of stacking — the HUD 1.0 overflow bug (spec Edge Cases)', () => {
  const many = {
    identity: 'as1-1.1.1.1',
    peers: [],
    risk: { risk_name: 'r' },
    members: Array.from({ length: 9 }, (_, i) => ({
      member_id: `r/phone-${i}`, display_name: `phone-${i}`, node_type: 'edge',
      live: false, state: 'unreachable',
    })),
  };
  const { nodes } = computeLayout(many, catalog, NOW);
  const edges = nodes.filter((n) => n.kind === 'edge');
  assert.equal(edges.length, 9);

  const positions = new Set(edges.map((e) => key(e.position)));
  assert.equal(positions.size, 9, 'nine phones must occupy nine distinct positions');
  assert.ok(new Set(edges.map((e) => e.position.x)).size > 1, 'lane must wrap into columns');
});

test('appendMember leaves every existing coordinate byte-identical (FR-034b)', () => {
  const layout = computeLayout(load('live-29.json'), catalog, NOW);
  const before = layout.nodes.map((n) => [n.id, key(n.position)]);

  const added = appendMember(
    layout,
    { member_id: 'johns-risk/newcomer', display_name: 'newcomer', live: true, skills: ['pyats-health-check'] },
    catalog,
    NOW,
  );

  assert.ok(added, 'a node was added');
  const after = layout.nodes.map((n) => [n.id, key(n.position)]);
  assert.deepEqual(after.slice(0, before.length), before, 'no existing node moved');
  assert.equal(after.length, before.length + 1);
});

test('appendMember does not duplicate an existing member', () => {
  const layout = computeLayout(load('live-29.json'), catalog, NOW);
  const existing = layout.nodes.find((n) => n.kind === 'member');
  const n = layout.nodes.length;
  assert.equal(appendMember(layout, { member_id: existing.id }, catalog, NOW), null);
  assert.equal(layout.nodes.length, n);
});

test('appendMember places an edge node in the lane, not a column', () => {
  const layout = computeLayout(load('live-29.json'), catalog, NOW);
  const node = appendMember(
    layout, { member_id: 'risk/phone-new', node_type: 'edge', live: true }, catalog, NOW,
  );
  assert.equal(node.kind, 'edge');
  assert.equal(node.band, 'edgeLane');
  assert.ok(node.position.x >= LAYOUT.edgeLaneX);
});

test('appendMember into an unseen category does not re-pack existing rows', () => {
  const layout = computeLayout(load('live-29.json'), catalog, NOW);
  const before = layout.nodes.map((n) => key(n.position));
  appendMember(
    layout,
    { member_id: 'r/exotic', display_name: 'exotic', skills: ['zzz-unknown-prefix'] },
    [{ id: 'z', category: 'Brand New Category', prefixes: ['zzz-'] }],
    NOW,
  );
  assert.deepEqual(layout.nodes.slice(0, before.length).map((n) => key(n.position)), before);
});

test('scale fixture places 100+ members without collision (FR-029)', () => {
  const { nodes, categories } = computeLayout(load('scale-100.json'), catalog, NOW);
  const members = nodes.filter((n) => n.kind === 'member');
  assert.ok(members.length >= 100, `expected >=100 members, got ${members.length}`);
  assert.equal(new Set(nodes.map((n) => key(n.position))).size, nodes.length, 'no overlap at the ceiling');
  assert.ok(categories.length > 1, 'categories are laid out');
});

test('categories wrap into rows past maxColumnsPerRow', () => {
  const { categories } = computeLayout(load('scale-100.json'), catalog, NOW);
  if (categories.length > LAYOUT.maxColumnsPerRow) {
    assert.ok(categories.some((c) => c.row > 0), 'must wrap rather than run off-screen');
    const rows = new Set(categories.map((c) => c.row));
    assert.ok(rows.size > 1);
  }
});

test('members carry their tools and a tool count for collapsed display (FR-021/024)', () => {
  const { nodes } = computeLayout(load('live-29.json'), catalog, NOW);
  const withTools = nodes.filter((n) => n.kind === 'member' && n.toolCount > 0);
  assert.ok(withTools.length > 0);
  for (const n of withTools) {
    assert.equal(n.toolCount, n.tools.length);
    assert.equal(n.expanded, false, 'collapsed is the default (FR-020)');
  }
});

test('computeLayout is total on junk input', () => {
  for (const junk of [null, undefined, {}, { members: 'nope', peers: 42 }]) {
    const out = computeLayout(junk, catalog, NOW);
    assert.equal(out.bands.length, 4, 'bands always render');
    assert.ok(Array.isArray(out.nodes));
  }
});

test('computeLayout does not mutate the payload', () => {
  const payload = load('live-29.json');
  const before = JSON.stringify(payload);
  computeLayout(payload, catalog, NOW);
  assert.equal(JSON.stringify(payload), before);
});
