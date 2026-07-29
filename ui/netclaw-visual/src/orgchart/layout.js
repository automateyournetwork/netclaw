/**
 * Deterministic banded layout (R6, FR-001..007, FR-029, FR-033, FR-034).
 *
 * Pure: no three.js, no DOM, no clock, no randomness. Coordinates are plain
 * numbers; the render layer turns them into scene objects and may not
 * re-derive any of this.
 *
 * The graph is depth-2 by construction (Border -> category -> member), so this
 * is band assignment plus row packing — not a tree layout. Reingold-Tilford and
 * force-directed layouts both solve problems this graph does not have, and a
 * force simulation would actively violate FR-034's position stability.
 *
 *        y
 *        ^   ┌─────────────── EXTERNAL band (peers, eN2N) ────────────┐
 *   +40  │   │  o        o        o        o                          │
 *        │   └────────────────────────────────────────────────────────┘
 *   +18  │  ═══════════════ TRUST BOUNDARY ═══════════════════════════
 *        │        ┌────────┐                    ┌── EDGE LANE ──┐
 *     0  │        │ BORDER │  ╌╌╌╌ push ╌╌╌╌╌►  │  o   o        │
 *        │        └────────┘                    └───────────────┘
 *   -18  │  ─────────────── INTERNAL band (members, iN2N) ─────────────
 *        │   [cat]     [cat]     [cat]     [cat]   ← columns, wrapping
 *        │    o         o         o         o      ← members stack down
 *        v
 */

import { classifyHealth } from './health.js';
import { orderCategories, orderMembers } from './ordering.js';
import { resolveLabel, disambiguateLabels, dedupePeers } from './normalize.js';
import { categorizeMembers } from './categorize.js';

/** Layout constants. Named, not scattered as literals. */
export const LAYOUT = {
  boundaryY: 18,
  externalY: 40,
  externalSpacingX: 34,
  borderY: 0,
  internalTopY: -20,
  // The internal band fans WIDE. Members are the bulk of the chart and the
  // thing an operator scans, so they get horizontal room rather than being
  // packed into a narrow column stack under the Border. Wide + shallow beats
  // narrow + deep for scanning: the eye moves along a row far faster than it
  // walks down a column, and the orthographic camera auto-frames whatever
  // extent this produces (camera.frameChart).
  columnSpacingX: 38,
  memberSpacingY: 8,
  categoryHeaderOffsetY: -7,
  rowSpacingY: 58,
  // Wide cap so a typical deployment lays out in a SINGLE row — the widest,
  // cleanest fan. Rows are balanced when wrapping is unavoidable.
  maxColumnsPerRow: 20,
  edgeLaneX: 96,          // floor only; the real X is derived from the fan extent
  edgeSpacingY: 11,
  edgeLaneColumns: 2,
  edgeLaneSpacingX: 18,
};

/**
 * Compute the full chart layout.
 *
 * Every band is emitted even when empty — a NetClaw with no risk, no members
 * and no peers is the normal first state for a new operator, not an edge case
 * (FR-033), and after FR-030 there is nothing else left to draw.
 *
 * @param {object} n2n the /api/n2n payload
 * @param {Array<object>} integrationCatalog from /api/graph integrations[]
 * @param {number} nowEpochS injected clock
 * @param {object} [opts]
 * @returns {{nodes: Array<object>, bands: Array<object>, categories: Array<object>}}
 */
export function computeLayout(n2n, integrationCatalog, nowEpochS, opts = {}) {
  const cfg = { ...LAYOUT, ...opts };
  const payload = n2n && typeof n2n === 'object' ? n2n : {};
  const members = Array.isArray(payload.members) ? payload.members : [];

  const nodes = [];

  // ── External band: eN2N peers, north of the boundary (FR-003) ──
  const peers = disambiguateLabels(dedupePeers(payload.peers));
  const peerSpan = (peers.length - 1) * cfg.externalSpacingX;
  peers.forEach(({ entity, label }, i) => {
    nodes.push({
      id: entity.identity || `peer-${i}`,
      kind: 'peer',
      label,
      band: 'external',
      state: entity.state || 'unknown',
      channelState: entity.channel_state || 'unknown',
      severed: String(entity.state).toLowerCase() === 'severed',
      payload: entity,
      position: { x: -peerSpan / 2 + i * cfg.externalSpacingX, y: cfg.externalY, z: 0 },
    });
  });

  // ── Centre: the Border itself (FR-004) ──
  const risk = payload.risk || null;
  nodes.push({
    id: payload.identity || 'border',
    kind: 'border',
    label: (risk && risk.risk_name) || payload.identity || 'this claw',
    band: 'border',
    isBorder: true,
    payload: { ...(risk || {}), identity: payload.identity },
    position: { x: 0, y: cfg.borderY, z: 0 },
  });

  // ── Internal band: member claws in derived category columns (FR-005/006) ──
  const grouped = categorizeMembers(members, integrationCatalog);
  const ordered = orderCategories(grouped, nowEpochS);

  // Balance columns across rows rather than filling each to the cap. With 15
  // categories and a cap of 14 the naive split is 14 + 1, which looks broken;
  // balancing gives 8 + 7. Rows are still driven by the cap, so wide-and-
  // shallow is preserved.
  const rowsNeeded = Math.max(1, Math.ceil(ordered.length / cfg.maxColumnsPerRow));
  const perRow = Math.max(1, Math.ceil(ordered.length / rowsNeeded));

  const categories = [];
  ordered.forEach((category, index) => {
    const col = index % perRow;
    const row = Math.floor(index / perRow);
    const rowCount = Math.min(ordered.length - row * perRow, perRow);
    const rowSpan = (rowCount - 1) * cfg.columnSpacingX;
    const x = -rowSpan / 2 + col * cfg.columnSpacingX;
    const headerY = cfg.internalTopY - row * cfg.rowSpacingY;

    categories.push({ name: category.name, heat: category.heat, column: col, row, position: { x, y: headerY, z: 0 } });

    orderMembers(category.members, nowEpochS, resolveLabel).forEach((m, mi) => {
      nodes.push({
        id: m.member_id || `${category.name}-${mi}`,
        kind: 'member',
        label: resolveLabel(m),
        band: 'internal',
        category: category.name,
        health: classifyHealth(m, nowEpochS),
        heartbeatAgeS: m.heartbeat_age_s ?? null,
        toolCount: Array.isArray(m.skills) ? m.skills.length : 0,
        tools: Array.isArray(m.skills) ? [...m.skills] : [],
        expanded: false,
        payload: m,
        position: { x, y: headerY + cfg.categoryHeaderOffsetY - mi * cfg.memberSpacingY, z: 0 },
      });
    });
  });

  // ── Edge lane: mobile edges, inside the boundary, outside the chart (FR-007) ──
  // Placed AFTER the member columns so the lane can clear whatever width the
  // fan turned out to be. A fixed X would collide once the internal band was
  // widened — which is exactly what happened, and what the FR-007 test caught.
  const memberXs = nodes.filter((n) => n.kind === 'member').map((n) => n.position.x);
  const fanRight = memberXs.length ? Math.max(...memberXs) : 0;
  const laneX = Math.max(cfg.edgeLaneX, fanRight + cfg.columnSpacingX);

  const edges = members.filter((m) => m && m.node_type === 'edge');
  const perCol = Math.max(1, Math.ceil(edges.length / cfg.edgeLaneColumns));
  edges.forEach((m, i) => {
    const col = Math.floor(i / perCol);
    const row = i % perCol;
    nodes.push({
      id: m.member_id || `edge-${i}`,
      kind: 'edge',
      label: resolveLabel(m),
      band: 'edgeLane',
      health: classifyHealth(m, nowEpochS),
      heartbeatAgeS: m.heartbeat_age_s ?? null,
      toolCount: Array.isArray(m.skills) ? m.skills.length : 0,
      tools: Array.isArray(m.skills) ? [...m.skills] : [],
      expanded: false,
      payload: m,
      position: {
        x: laneX + col * cfg.edgeLaneSpacingX,
        y: cfg.borderY + 6 - row * cfg.edgeSpacingY,
        z: 0,
      },
    });
  });

  // ── Bands: always emitted, even when empty (FR-033) ──
  const bands = [
    {
      id: 'external',
      label: 'External — eN2N',
      y: cfg.externalY,
      empty: peers.length === 0,
      emptyCta: 'No federated peers. Connect one to extend the mesh.',
    },
    {
      id: 'boundary',
      label: 'Trust boundary',
      y: cfg.boundaryY,
      isBoundary: true,
      empty: false,
    },
    {
      id: 'edgeLane',
      label: 'Mobile edges',
      y: cfg.borderY,
      x: laneX,
      empty: edges.length === 0,
      emptyCta: 'No devices paired. Enrol a phone to receive pushes.',
    },
    {
      id: 'internal',
      label: 'Internal — iN2N',
      y: cfg.internalTopY,
      empty: ordered.length === 0,
      emptyCta: 'No members enrolled. Add a claw to delegate work to.',
    },
  ];

  return { nodes, bands, categories };
}

/**
 * Add a member that enrolled mid-session (FR-034b).
 *
 * Appends within its category WITHOUT moving any existing node — position
 * stability is a hard guarantee, and a member arriving must not shuffle the
 * chart under an operator who is reading it.
 *
 * @param {{nodes:Array<object>, categories:Array<object>}} layout mutated in place
 * @param {object} member
 * @param {Array<object>} integrationCatalog
 * @param {number} nowEpochS
 * @returns {object|null} the new node, or null if it was already present
 */
export function appendMember(layout, member, integrationCatalog, nowEpochS) {
  if (!layout || !Array.isArray(layout.nodes) || !member) return null;
  const id = member.member_id;
  if (id && layout.nodes.some((n) => n.id === id)) return null;

  const cfg = LAYOUT;

  if (member.node_type === 'edge') {
    const existing = layout.nodes.filter((n) => n.kind === 'edge');
    const node = {
      id: id || `edge-${existing.length}`,
      kind: 'edge',
      label: resolveLabel(member),
      band: 'edgeLane',
      health: classifyHealth(member, nowEpochS),
      heartbeatAgeS: member.heartbeat_age_s ?? null,
      toolCount: Array.isArray(member.skills) ? member.skills.length : 0,
      payload: member,
      position: {
        x: cfg.edgeLaneX + Math.floor(existing.length / 8) * cfg.edgeLaneSpacingX,
        y: cfg.borderY + 6 - (existing.length % 8) * cfg.edgeSpacingY,
        z: 0,
      },
    };
    layout.nodes.push(node);
    return node;
  }

  const [categoryName] = [...categorizeMembers([member], integrationCatalog).keys()];
  const category = (layout.categories || []).find((c) => c.name === categoryName);
  const siblings = layout.nodes.filter((n) => n.kind === 'member' && n.category === categoryName);

  // An unseen category appends to the right of the last column rather than
  // re-packing rows — again, nothing existing may move.
  const anchor = category
    ? category.position
    : { x: (Math.max(0, ...(layout.categories || []).map((c) => c.position.x)) || 0) + cfg.columnSpacingX, y: cfg.internalTopY };

  if (!category) {
    (layout.categories ||= []).push({
      name: categoryName, heat: 0, column: -1, row: 0, position: { ...anchor, z: 0 },
    });
  }

  const node = {
    id: id || `${categoryName}-${siblings.length}`,
    kind: 'member',
    label: resolveLabel(member),
    band: 'internal',
    category: categoryName,
    health: classifyHealth(member, nowEpochS),
    heartbeatAgeS: member.heartbeat_age_s ?? null,
    toolCount: Array.isArray(member.skills) ? member.skills.length : 0,
    tools: Array.isArray(member.skills) ? [...member.skills] : [],
    expanded: false,
    payload: member,
    position: {
      x: anchor.x,
      y: anchor.y + cfg.categoryHeaderOffsetY - siblings.length * cfg.memberSpacingY,
      z: 0,
    },
  };
  layout.nodes.push(node);
  return node;
}
