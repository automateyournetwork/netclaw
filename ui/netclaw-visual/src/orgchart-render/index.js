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
import {
  buildNodes, animateNodes, applyHighlight, nodeLabelText, formatAge, syncEntryPosition,
  setEntryHovered, setEntrySelected, setNodeTheme, applyNodeTheme, applyEntryAppearance,
  TREATMENTS,
} from './nodes.js';
import { buildBands, setBandTheme } from './bands.js';
import { buildLinks, setLinkTheme } from './links.js';
import { buildTrustZones } from './zones.js';
import {
  buildCategories, summariseCategories, updateCategorySummaries, highlightCategories,
  updateCategoryRails, setCategoryTheme,
} from './categories.js';
import { classifyHealth } from '../orgchart/health.js';
import {
  applySavedLayout, applySavedPositions, saveLayout, clearSavedPositions,
  snapshotDefaults, positionId,
} from '../orgchart/positions.js';
import {
  toggleExpansion, collapseAll, isExpanded, expandedCount, updateExpansionPosition,
} from './expansion.js';
import { buildA11yOverlay } from './a11y.js';

export { TREATMENTS };

/** Live chart state. Rebuilt only on explicit remount, never on a poll. */
const chart = {
  root: null,
  nodes: null,
  bands: null,
  links: null,
  zones: null,
  categories: null,
  theme: 'modern',
  layout: null,
  catalog: [],
  entries: [],
  dynamicNodes: [],
  search: '',
  statusFilter: 'all',
  categoryFilter: null,
  hovered: null,
  selected: null,
  draggables: [],
  defaultPositions: new Map(),
  storageIdentity: 'default',
  makeLabel: null,
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
  const storageIdentity = layout.nodes.find((node) => node.kind === 'border')?.id || 'default';
  const defaults = snapshotDefaults(layout.nodes, layout.categories);
  const defaultPositions = defaults.nodes;
  const defaultCategoryPositions = defaults.categories;
  applySavedLayout(storageIdentity, layout.nodes, layout.categories);

  const root = new THREE.Group();
  root.name = 'orgchart';

  // Trust ZONES (not just a boundary line): External and Internal are drawn as
  // labelled regions, so the hierarchy survives without a giant horizontal bar
  // carrying the whole meaning.
  const zones = buildTrustZones(layout.bands, layout.nodes, makeLabel, chart.theme);
  const bands = buildBands(layout.bands, makeLabel);
  const links = buildLinks(layout.nodes, layout.categories);
  const categories = buildCategories(layout.categories, layout.nodes, makeLabel);
  const nodes = buildNodes(layout.nodes, makeLabel);

  root.add(zones.group, bands.group, links.group, categories.group, nodes.group);
  scene.add(root);

  Object.assign(chart, {
    root, nodes, bands, links, zones, categories, layout,
    catalog: integrationCatalog || [],
    entries: nodes.entries,
    dynamicNodes: [],
    search: '',
    statusFilter: 'all',
    categoryFilter: new Set(layout.categories.map((category) => category.name)),
    hovered: null,
    selected: null,
    draggables: nodes.entries.filter((entry) => entry.node.kind === 'member').map((entry) => entry.mesh),
    defaultPositions,
    defaultCategoryPositions,
    storageIdentity,
    makeLabel,
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
  chart.dynamicNodes.forEach((built) => built.dispose?.());
  chart.bands?.dispose?.();
  chart.links?.dispose?.();
  chart.zones?.dispose?.();
  chart.categories?.dispose?.();
  chart.a11y?.destroy?.();
  // chart.theme is intentionally preserved: the operator's theme choice is not
  // owned by the chart lifecycle.
  Object.assign(chart, {
    root: null, nodes: null, bands: null, links: null, zones: null, categories: null,
    layout: null, entries: [], dynamicNodes: [], hovered: null, selected: null,
    draggables: [], defaultPositions: new Map(), defaultCategoryPositions: new Map(),
    storageIdentity: 'default', makeLabel: null,
  });
}

function rebuildRails() {
  updateCategoryRails(chart.categories, chart.layout?.categories, chart.layout?.nodes);
}

function rebuildBands() {
  if (!chart.root || !chart.layout || !chart.makeLabel) return;
  chart.root.remove(chart.bands.group);
  chart.bands.dispose();
  chart.bands = buildBands(chart.layout.bands, chart.makeLabel);
  chart.root.add(chart.bands.group);
}

/**
 * Retheme the whole chart IN PLACE (theme-adaptive topology).
 *
 * Nothing is remounted and no position is recomputed, so a claw the operator
 * dragged stays exactly where they put it across a theme switch — same
 * guarantee the poll path already has to honour (FR-034a).
 *
 * @param {'modern'|'retro'} next
 */
export function setOrgChartTheme(next) {
  const theme = next === 'retro' ? 'retro' : 'modern';
  chart.theme = theme;
  setNodeTheme(theme);
  setLinkTheme(theme);
  setBandTheme(theme);
  setCategoryTheme(theme);
  if (!chart.root) return theme;   // stored; applied when the chart mounts

  chart.zones?.setTheme(theme);
  applyNodeTheme(chart.entries);
  rebuildBands();
  rebuildLinks();
  rebuildCategories();
  return theme;
}

export function orgChartTheme() {
  return chart.theme;
}

function rebuildLinks() {
  if (!chart.root || !chart.layout) return;
  chart.root.remove(chart.links.group);
  chart.links.dispose();
  chart.links = buildLinks(chart.layout.nodes, chart.layout.categories);
  chart.root.add(chart.links.group);
}

function rebuildCategories() {
  if (!chart.root || !chart.layout || !chart.makeLabel) return;
  chart.root.remove(chart.categories.group);
  chart.categories.dispose();
  chart.categories = buildCategories(chart.layout.categories, chart.layout.nodes, chart.makeLabel);
  chart.root.add(chart.categories.group);
  applyVisibilityState();
}

export function draggableObjects() {
  // Individual claws AND department handles. A department is the unit an
  // operator rearranges most often, so it has to be grabbable in its own right.
  return [
    ...chart.draggables,
    ...(chart.categories?.entries || []).map((entry) => entry.handle).filter(Boolean),
  ];
}

/**
 * Move a whole department: header, drag handle and every claw under it.
 *
 * @param {THREE.Object3D} handle the dragged category handle
 * @returns {string|null} the department name
 */
export function moveOrgChartGroup(handle) {
  const name = handle?.userData?.categoryName;
  if (!name || !chart.layout) return null;
  const entry = (chart.categories?.entries || []).find((candidate) => candidate.name === name);
  const category = (chart.layout.categories || []).find((candidate) => candidate.name === name);
  if (!entry || !category) return null;

  // The handle sits above the header; derive the header position back from it.
  const targetX = Math.max(-220, Math.min(220, handle.position.x));
  const targetY = Math.max(-260, Math.min(40, handle.position.y - 3.4));
  const dx = targetX - category.position.x;
  const dy = targetY - category.position.y;
  if (dx === 0 && dy === 0) return name;

  category.position = { x: targetX, y: targetY, z: 0 };
  for (const member of chart.entries) {
    if (member.node.kind !== 'member' || member.node.category !== name) continue;
    member.node.position = {
      x: member.node.position.x + dx,
      y: member.node.position.y + dy,
      z: 0,
    };
    syncEntryPosition(member);
    updateExpansionPosition(member.node.id, member.node.position);
  }

  entry.label.position.set(targetX, targetY + 3.4, 0);
  handle.position.set(targetX, targetY + 3.4, 0.4);
  rebuildLinks();
  rebuildRails();
  return name;
}

export function commitOrgChartGroup(handle) {
  const name = moveOrgChartGroup(handle);
  if (!name) return null;
  saveLayout(chart.storageIdentity, chart.layout.nodes, chart.layout.categories);
  return name;
}

export function isCategoryHandle(object) {
  return !!object?.userData?.isCategoryHandle;
}

export function moveOrgChartNode(mesh) {
  const entry = chart.entries.find((candidate) => candidate.mesh === mesh);
  if (!entry || entry.node.kind !== 'member') return null;

  entry.node.position.x = Math.max(-220, Math.min(220, mesh.position.x));
  entry.node.position.y = Math.max(-260, Math.min(8, mesh.position.y));
  entry.node.position.z = 0;
  syncEntryPosition(entry);
  updateExpansionPosition(entry.node.id, entry.node.position);
  rebuildLinks();
  rebuildRails();
  return entry.node;
}

export function commitOrgChartNode(mesh) {
  const node = moveOrgChartNode(mesh);
  if (!node) return null;
  // Summaries/rails update in place rather than rebuilding: a rebuild would
  // swap out the department handle meshes that DragControls is holding.
  updateCategorySummaries(chart.categories, chart.layout.categories, chart.layout.nodes);
  saveLayout(chart.storageIdentity, chart.layout.nodes, chart.layout.categories);
  return node;
}

export function resetOrgChartLayout() {
  if (!chart.layout) return false;
  clearSavedPositions(chart.storageIdentity);

  for (const category of chart.layout.categories || []) {
    const position = chart.defaultCategoryPositions.get(category.name);
    if (position) category.position = { ...position };
  }
  for (const entry of chart.entries) {
    if (entry.node.kind !== 'member') continue;
    const position = chart.defaultPositions.get(positionId(entry.node));
    if (!position) continue;
    entry.node.position = { ...position };
    syncEntryPosition(entry);
    updateExpansionPosition(entry.node.id, entry.node.position);
  }
  for (const entry of chart.categories?.entries || []) {
    const position = chart.defaultCategoryPositions.get(entry.name);
    if (!position) continue;
    entry.label.position.set(position.x, position.y + 3.4, 0);
    entry.handle?.position.set(position.x, position.y + 3.4, 0.4);
  }
  rebuildLinks();
  rebuildRails();
  return true;
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
  const byId = new Map(members.map((member) => [member.member_id, member]));

  for (const entry of chart.entries) {
    const fresh = byId.get(entry.node.id);
    if (!fresh) continue;

    const previousHealth = entry.node.health;
    const health = classifyHealth(fresh, nowEpochS);
    Object.assign(entry.node, {
      health,
      heartbeatAgeS: fresh.heartbeat_age_s ?? null,
      toolCount: Array.isArray(fresh.skills) ? fresh.skills.length : 0,
      tools: Array.isArray(fresh.skills) ? [...fresh.skills] : [],
      payload: fresh,
    });
    entry.mesh.userData.payload = fresh;
    entry.label.element.textContent = nodeLabelText(entry.node);

    // Repaint through the theme-aware helper: writing TREATMENTS directly here
    // silently reverted one node to modern colours mid-session while retro was
    // active, which is exactly the class of bug a single source of truth avoids.
    if (health !== previousHealth) applyEntryAppearance(entry);
  }

  const known = new Set(chart.entries.map((entry) => entry.node.id));
  let appended = false;
  for (const member of members) {
    if (!member?.member_id || known.has(member.member_id)) continue;
    const node = appendMember(chart.layout, member, chart.catalog, nowEpochS);
    if (!node) continue;

    const id = positionId(node);
    if (id) chart.defaultPositions.set(id, { ...node.position });
    applySavedPositions(chart.storageIdentity, [node]);
    const built = buildNodes([node], makeLabel);
    chart.nodes.group.add(...built.group.children);
    chart.entries.push(...built.entries);
    chart.dynamicNodes.push(built);
    chart.draggables.push(...built.entries.filter((entry) => entry.node.kind === 'member').map((entry) => entry.mesh));
    known.add(member.member_id);
    appended = true;
  }

  if (appended) {
    rebuildLinks();
    rebuildCategories();
  } else if (!updateCategorySummaries(chart.categories, chart.layout.categories, chart.layout.nodes)) {
    rebuildCategories();
  }
  if (appended && chart.categoryFilter) {
    for (const category of chart.layout.categories) chart.categoryFilter.add(category.name);
  }

  applyVisibilityState();
  chart.a11y?.sync?.(chart.layout.nodes);
}

/**
 * Search: highlight matches, dim the rest, in place (FR-031a/b).
 * Never hides and never re-packs — hiding would destroy the spatial memory the
 * whole layout exists to build.
 *
 * @param {string} query
 */
function matchesSearch(node) {
  const query = chart.search;
  if (!query) return true;
  if (String(node.label || '').toLowerCase().includes(query)) return true;
  if (String(node.category || '').toLowerCase().includes(query)) return true;
  return (node.tools || []).some((tool) => String(tool).toLowerCase().includes(query));
}

function matchesStatus(node) {
  if (chart.statusFilter === 'all' || node.kind === 'border') return true;
  if (chart.statusFilter === 'active') {
    if (node.kind === 'peer') return String(node.channelState).toLowerCase() === 'up';
    return node.health === 'HOT' || node.health === 'WARM';
  }
  if (chart.statusFilter === 'attention') {
    if (node.kind === 'peer') {
      return node.severed || String(node.channelState).toLowerCase() !== 'up';
    }
    return node.health === 'FAULT';
  }
  return true;
}

function matchesCategory(node) {
  if (node.kind !== 'member' || !chart.categoryFilter) return true;
  return chart.categoryFilter.has(node.category);
}

function applyVisibilityState() {
  const focusing = !!chart.search
    || chart.statusFilter !== 'all'
    || (chart.categoryFilter && chart.categoryFilter.size < (chart.layout?.categories?.length || 0));
  const matches = (node) => matchesSearch(node) && matchesStatus(node) && matchesCategory(node);
  applyHighlight(chart.entries, matches, focusing);
  highlightCategories(chart.categories, (name) => {
    const members = chart.entries.filter((entry) => entry.node.category === name);
    return chart.categoryFilter?.has(name) && members.some((entry) => matches(entry.node));
  }, focusing);
}

export function searchOrgChart(query) {
  chart.search = String(query || '').trim().toLowerCase();
  applyVisibilityState();
}

export function filterOrgChart({ status, categories } = {}) {
  if (status) chart.statusFilter = ['all', 'active', 'attention'].includes(status) ? status : 'all';
  if (categories) chart.categoryFilter = new Set(categories);
  applyVisibilityState();
}

export function chartSummary() {
  return summariseCategories(chart.layout?.categories, chart.layout?.nodes);
}

/** Only focused nodes are pickable; dimmed context cannot steal a click. */
export function pickableObjects() {
  return chart.entries.filter((entry) => entry.isMatch).map((entry) => entry.mesh);
}

export function chartNodes() {
  return chart.layout ? chart.layout.nodes : [];
}

export function hoverOrgChartNode(mesh) {
  const entry = chart.entries.find((candidate) => candidate.mesh === mesh);
  if (!entry) return null;
  if (chart.hovered && chart.hovered !== entry) setEntryHovered(chart.hovered, false);
  chart.hovered = entry;
  setEntryHovered(entry, true);
  return { node: entry.node, ...tooltipForNode(entry.node) };
}

export function clearOrgChartHover() {
  if (chart.hovered) setEntryHovered(chart.hovered, false);
  chart.hovered = null;
}

export function selectOrgChartNode(nodeId) {
  if (chart.selected) setEntrySelected(chart.selected, false);
  chart.selected = chart.entries.find((entry) => entry.node.id === nodeId) || null;
  if (chart.selected) setEntrySelected(chart.selected, true);
  return chart.selected?.node || null;
}

export function clearOrgChartSelection() {
  if (chart.selected) setEntrySelected(chart.selected, false);
  chart.selected = null;
}

function tooltipForNode(node) {
  if (node.kind === 'border') {
    return { title: node.label, subtitle: 'Trust anchor · delegation root' };
  }
  if (node.kind === 'peer') {
    const state = node.severed ? 'severed' : `channel ${node.channelState || 'unknown'}`;
    return { title: node.label, subtitle: `External eN2N peer · ${state}` };
  }
  const role = node.kind === 'edge' ? 'Mobile edge' : `${node.category || 'Uncategorised'} member`;
  const health = TREATMENTS[node.health]?.label || String(node.health || 'unknown').toLowerCase();
  const seen = node.heartbeatAgeS == null ? '' : ` · seen ${formatAge(node.heartbeatAgeS)}`;
  return { title: node.label, subtitle: `${role} · ${health}${seen}` };
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
