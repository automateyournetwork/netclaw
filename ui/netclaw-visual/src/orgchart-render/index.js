/**
 * Org-chart mount point — the single seam between main.js and HUD 2.0.
 *
 * main.js calls mountOrgChart() once and updateOrgChart() on each poll. Keeping
 * the surface this small is what makes FR-026's hard replace reviewable: the
 * orbit layout is removed from main.js, but nothing else in that 132 KB file
 * needs to understand how the chart is built.
 *
 * Position stability (FR-034) lives here: updateOrgChart repaints appearance
 * and NEVER recomputes layout. A claw that fails changes how it looks, never
 * where it is.
 */

import * as THREE from 'three';

import { computeLayout, appendMember } from '../orgchart/layout.js';
import { buildNodes, animateNodes, applyHighlight, TREATMENTS } from './nodes.js';
import { buildBands } from './bands.js';
import { buildLinks } from './links.js';
import { classifyHealth } from '../orgchart/health.js';
import { toggleExpansion, collapseAll, isExpanded, expandedCount } from './expansion.js';
import { buildA11yOverlay } from './a11y.js';

export { TREATMENTS };

/** Live chart state. Rebuilt only on explicit remount, never on a poll. */
const chart = {
  root: null,
  nodes: null,
  bands: null,
  links: null,
  layout: null,
  catalog: [],
  entries: [],
  search: '',
};

export function prefersReducedMotion() {
  return typeof window !== 'undefined'
    && typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Build the chart and add it to the scene.
 *
 * @param {THREE.Scene} scene
 * @param {object} n2n /api/n2n payload
 * @param {Array<object>} integrationCatalog from /api/graph integrations[]
 * @param {(text:string)=>object} makeLabel host CSS2D factory (FR-028)
 * @returns {{nodes:Array<object>, bands:Array<object>, categories:Array<object>}}
 */
export function mountOrgChart(scene, n2n, integrationCatalog, makeLabel) {
  unmountOrgChart(scene);

  const nowEpochS = Date.now() / 1000;
  const layout = computeLayout(n2n, integrationCatalog, nowEpochS);

  const root = new THREE.Group();
  root.name = 'orgchart';

  const bands = buildBands(layout.bands, makeLabel);
  const links = buildLinks(layout.nodes, layout.categories);
  const nodes = buildNodes(layout.nodes, makeLabel);

  root.add(bands.group, links.group, nodes.group);
  scene.add(root);

  Object.assign(chart, {
    root, nodes, bands, links, layout,
    catalog: integrationCatalog || [],
    entries: nodes.entries,
  });
  return layout;
}

/**
 * Attach the keyboard / screen-reader overlay (FR-032). Kept separate from
 * mountOrgChart so the scene can be built headlessly in tests without a DOM.
 *
 * @param {HTMLElement} container element covering the canvas
 * @param {{onSelect:Function, onToggle:Function}} handlers
 */
export function mountA11y(container, handlers) {
  if (!container || !chart.layout) return null;
  chart.a11y = buildA11yOverlay(container, chart.layout.nodes, handlers);
  return chart.a11y;
}

export function unmountOrgChart(scene) {
  if (!chart.root) return;
  scene.remove(chart.root);
  chart.nodes?.dispose?.();
  chart.bands?.dispose?.();
  chart.links?.dispose?.();
  chart.a11y?.destroy?.();
  Object.assign(chart, { root: null, nodes: null, bands: null, links: null, layout: null, entries: [] });
}

/**
 * Refresh from a poll (FR-034a): appearance only.
 *
 * Health, labels and links are updated in place. Positions are never
 * recalculated and categories are never re-ordered — doing so would re-pack the
 * chart under an operator who is reading it, which is exactly what FR-022 and
 * FR-031a exist to prevent elsewhere.
 *
 * A member that enrolled mid-session is appended via appendMember (FR-034b),
 * which places it without moving anything already on screen.
 *
 * @param {THREE.Scene} scene
 * @param {object} n2n
 * @param {(text:string)=>object} makeLabel
 */
export function updateOrgChart(scene, n2n, makeLabel) {
  if (!chart.layout) return;

  const nowEpochS = Date.now() / 1000;
  const members = Array.isArray(n2n?.members) ? n2n.members : [];
  const byId = new Map(members.map((m) => [m.member_id, m]));

  // 1. Repaint existing nodes.
  for (const entry of chart.entries) {
    const fresh = byId.get(entry.node.id);
    if (!fresh) continue;

    const health = classifyHealth(fresh, nowEpochS);
    if (health === entry.node.health) continue;

    entry.node.health = health;
    entry.node.payload = fresh;
    const t = TREATMENTS[health] || TREATMENTS.COLD;
    entry.material.color.setHex(t.color);
    entry.material.emissive.setHex(t.emissive);
    entry.material.emissiveIntensity = t.emissiveIntensity ?? 1.0;
    entry.material.roughness = health === 'COLD' ? 0.8 : 0.28;
    entry.mesh.scale.setScalar(entry.baseScale);
    entry.pulse = t.pulse;
  }

  // 2. Append genuinely new members (FR-034b) — nothing existing moves.
  const known = new Set(chart.entries.map((e) => e.node.id));
  for (const m of members) {
    if (!m?.member_id || known.has(m.member_id)) continue;

    const node = appendMember(chart.layout, m, chart.catalog, nowEpochS);
    if (!node) continue;

    const built = buildNodes([node], makeLabel);
    chart.nodes.group.add(...built.group.children);
    chart.entries.push(...built.entries);
    chart.layout.nodes.push(node);
  }

  chart.a11y?.sync?.(chart.layout.nodes);
}

/**
 * Search: highlight matches, dim the rest, in place (FR-031a/b).
 * Never hides and never re-packs — hiding would destroy the spatial memory the
 * whole layout exists to build.
 *
 * @param {string} query
 */
export function searchOrgChart(query) {
  chart.search = String(query || '').trim().toLowerCase();
  const q = chart.search;

  applyHighlight(chart.entries, (node) => {
    if (!q) return true;
    if (String(node.label || '').toLowerCase().includes(q)) return true;
    if (String(node.category || '').toLowerCase().includes(q)) return true;
    // A tool match must surface its owner even while collapsed (FR-031b).
    return (node.tools || []).some((t) => String(t).toLowerCase().includes(q));
  }, q.length > 0);
}

/** Meshes eligible for picking (click -> setDetail, FR-020a). */
export function pickableObjects() {
  return chart.entries.map((e) => e.mesh);
}

export function chartNodes() {
  return chart.layout ? chart.layout.nodes : [];
}

/**
 * Click handling: select AND reveal tools (operator revision to FR-020a).
 *
 * Returns the layout node so main.js can drive setDetail() unchanged — the
 * right-hand panel contract is untouched (FR-017/018).
 *
 * @param {THREE.Object3D} mesh the picked mesh
 * @param {(text:string)=>object} makeLabel
 * @returns {object|null} the layout node behind that mesh
 */
export function activateNode(mesh, makeLabel) {
  const node = mesh?.userData?.node;
  if (!node) return null;
  // Only members and edges carry tools; peers and the Border just select.
  if (node.kind === 'member' || node.kind === 'edge') {
    node.expanded = toggleExpansion(chart.root, node, mesh, makeLabel);
    // Keep the accessibility tree in step with the pointer path — otherwise a
    // screen-reader user gets a stale "collapsed" for a node someone expanded
    // with a mouse (FR-032b).
    const item = document.querySelector(
      `#orgchart-a11y .a11y-node[data-node-id="${CSS.escape(node.id)}"]`,
    );
    item?.setAttribute('aria-expanded', String(node.expanded));
  }
  return node;
}

/** Keyboard/affordance route to the same toggle (FR-032a). */
export function toggleNodeExpansion(nodeId, makeLabel) {
  const entry = chart.entries.find((e) => e.node.id === nodeId);
  if (!entry) return false;
  return toggleExpansion(chart.root, entry.node, entry.mesh, makeLabel);
}

export function collapseAllExpansions() {
  if (chart.root) collapseAll(chart.root);
}

export { isExpanded, expandedCount };

export function tickOrgChart(elapsed) {
  animateNodes(chart.entries, elapsed, prefersReducedMotion());
}
