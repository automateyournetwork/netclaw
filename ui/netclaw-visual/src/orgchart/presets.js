/**
 * Layout presets — Ring and Grid geometry (feature 102, US2 — FR-038, FR-042).
 *
 * Pure: no imports, no clock, no DOM, no three.js.
 *
 * Both presets are derived from the band/category data `computeLayout()` already
 * produces (FR-042). They deliberately do NOT re-derive grouping: introducing a
 * second source of truth for "which band is this node in" is how the peer/member
 * distinction would drift between the org chart and everything else.
 *
 * `orgchart` is absent from this file on purpose — it is not a preset
 * *implementation*, it is the absence of one. Selecting it means "use whatever
 * computeLayout produced", which is why FR-010 can require byte-identical output.
 *
 * `freeform` is likewise absent: it starts from the org chart and every
 * subsequent position is the operator's, so it has no geometry of its own.
 */

/** The five presets. These strings are WIRE VALUES — persisted verbatim as JSON keys. */
export const PRESETS = ['orgchart', 'ring', 'grid', 'force', 'freeform'];

/** Human labels for the dropdown. Prose may hyphenate; the ids never do. */
export const PRESET_LABELS = {
  orgchart: 'Org chart',
  ring: 'Ring',
  grid: 'Grid',
  force: 'Force-directed',
  freeform: 'Free-form',
};

export function isPresetId(value) {
  return PRESETS.includes(value);
}

/** Geometry constants, named rather than inlined so the tests can assert on them. */
export const RING = {
  borderRadius: 0,        // the Border sits at the centre
  peerRadius: 46,         // peers on the inner ring — closest to the Border they trust
  memberRadius: 78,       // members further out
  edgeRadius: 100,        // edge nodes (phones) furthest — they are the most peripheral
  y: 0,
};

export const GRID = {
  columns: 8,
  spacingX: 26,
  spacingY: 18,
  originY: 34,
};

/**
 * Concentric rings around the Border, one ring per node kind.
 *
 * Answers "who is connected to me" better than the org chart does, because
 * distance-from-centre becomes the only variable and the bands stop competing
 * with it for vertical space.
 *
 * @param {Array<object>} layoutNodes from computeLayout().nodes
 * @returns {{[nodeId: string]: {x:number,y:number,z:number}}}
 */
export function ringLayout(layoutNodes) {
  const nodes = Array.isArray(layoutNodes) ? layoutNodes : [];
  const out = {};

  const byKind = { peer: [], member: [], edge: [] };
  for (const n of nodes) {
    if (n.kind === 'border') {
      out[n.id] = { x: 0, y: RING.y, z: 0 };   // Border at the centre
    } else if (byKind[n.kind]) {
      byKind[n.kind].push(n);
    }
  }

  const radii = { peer: RING.peerRadius, member: RING.memberRadius, edge: RING.edgeRadius };
  for (const kind of Object.keys(byKind)) {
    const ring = byKind[kind];
    const r = radii[kind];
    ring.forEach((n, i) => {
      // Start at -90° so the first node sits at the top, matching the org chart's
      // convention that "north" is where external things live.
      const angle = (-Math.PI / 2) + (i / Math.max(1, ring.length)) * Math.PI * 2;
      // The chart lives on the XY plane — computeLayout sets z:0 for every node and
      // the camera looks down -Z. Building the ring in XZ (the instinct from a
      // ground-plane scene) collapses it to a horizontal line from the camera's
      // viewpoint, which is exactly what shipped first.
      out[n.id] = {
        x: round(Math.cos(angle) * r),
        y: round(RING.y + Math.sin(angle) * r),
        z: 0,
      };
    });
  }
  return out;
}

/**
 * Uniform rows, bands ignored.
 *
 * Good for scanning 30 members, which the org chart makes hard because it demotes
 * cold members deliberately. Grid is the preset that says "show me everything with
 * equal weight" — the opposite of feature 072's visual-weight rules, and useful
 * precisely because it is the opposite.
 *
 * Ordering is by kind then by the order computeLayout produced, so the arrangement
 * is stable across polls rather than reshuffling when a member's health changes.
 *
 * @param {Array<object>} layoutNodes from computeLayout().nodes
 * @returns {{[nodeId: string]: {x:number,y:number,z:number}}}
 */
export function gridLayout(layoutNodes) {
  const nodes = Array.isArray(layoutNodes) ? layoutNodes : [];
  const order = { border: 0, peer: 1, member: 2, edge: 3 };
  const sorted = [...nodes].sort((a, b) => (order[a.kind] ?? 9) - (order[b.kind] ?? 9));

  const out = {};
  const span = (GRID.columns - 1) * GRID.spacingX;
  sorted.forEach((n, i) => {
    const col = i % GRID.columns;
    const row = Math.floor(i / GRID.columns);
    out[n.id] = {
      x: round(-span / 2 + col * GRID.spacingX),
      y: round(GRID.originY - row * GRID.spacingY),
      z: 0,
    };
  });
  return out;
}

/** Two decimals is well below visual resolution and keeps saved payloads small. */
function round(v) {
  return Math.round(v * 100) / 100;
}
