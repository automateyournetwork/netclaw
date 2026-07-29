/**
 * Tool expand/collapse (FR-020 .. FR-025).
 *
 * Operator revision after seeing the MVP: expansion is now driven by the same
 * CLICK that selects, rather than only by a separate affordance. FR-020a's
 * original split (click = select, chevron = expand) was chosen in the abstract;
 * in use, one gesture that both shows the panel and reveals the tools is what
 * was actually wanted. The chevron behaviour is retained via toggleExpansion()
 * so the keyboard path (FR-032a) still has an explicit, non-pointer route.
 *
 * FR-022 is preserved and is the hard constraint: expanding NEVER reflows the
 * chart. Tools render as an overlay anchored to their node, claiming no layout
 * space, so no sibling moves and the operator never loses their place.
 */

import * as THREE from 'three';

/** node id -> { group, labels } for every currently expanded node. */
const expanded = new Map();

const MAX_VISIBLE_TOOLS = 12;

/**
 * Toggle a node's tool list.
 *
 * @param {THREE.Object3D} parentGroup scene group owning expansions
 * @param {object} node layout node (must carry .tools)
 * @param {THREE.Mesh} mesh the node's mesh, used as the anchor
 * @param {(text:string)=>object} makeLabel host CSS2D factory
 * @returns {boolean} true if now expanded
 */
export function toggleExpansion(parentGroup, node, mesh, makeLabel) {
  if (!node) return false;
  if (expanded.has(node.id)) {
    collapse(parentGroup, node.id);
    node.expanded = false;
    return false;
  }
  expand(parentGroup, node, mesh, makeLabel);
  node.expanded = true;
  return true;
}

function expand(parentGroup, node, mesh, makeLabel) {
  const tools = Array.isArray(node.tools) ? node.tools : [];
  const group = new THREE.Group();
  group.name = `expansion-${node.id}`;

  // Anchored to the node's own position, drawn slightly forward in z so it
  // overlays neighbours rather than displacing them (FR-022).
  group.position.set(node.position.x, node.position.y, node.position.z + 4);

  const shown = tools.slice(0, MAX_VISIBLE_TOOLS);
  const header = makeLabel(
    tools.length
      ? `${node.label} — ${tools.length} tool${tools.length === 1 ? '' : 's'}`
      : `${node.label} — no tools`,
  );
  header.element.classList.add('tool-header');
  header.position.set(0, -3.2, 0);
  group.add(header);

  shown.forEach((tool, i) => {
    const label = makeLabel(tool);
    label.element.classList.add('tool-item');
    // COLD and FAULT claws expand too: what a cold claw *would* bring is
    // exactly what decides whether to warm it (FR-025).
    if (node.health === 'COLD') label.element.classList.add('tool-item-cold');
    label.position.set(0, -5.4 - i * 2.1, 0);
    group.add(label);
  });

  if (tools.length > MAX_VISIBLE_TOOLS) {
    const more = makeLabel(`+${tools.length - MAX_VISIBLE_TOOLS} more`);
    more.element.classList.add('tool-item', 'tool-more');
    more.position.set(0, -5.4 - shown.length * 2.1, 0);
    group.add(more);
  }

  parentGroup.add(group);
  expanded.set(node.id, group);
}

function collapse(parentGroup, nodeId) {
  const group = expanded.get(nodeId);
  if (!group) return;
  parentGroup.remove(group);
  group.traverse((o) => { if (o.element?.remove) o.element.remove(); });
  expanded.delete(nodeId);
}

/** Multiple members may be expanded at once (FR-023). */
export function expandedCount() {
  return expanded.size;
}

export function isExpanded(nodeId) {
  return expanded.has(nodeId);
}

export function collapseAll(parentGroup) {
  for (const id of [...expanded.keys()]) collapse(parentGroup, id);
}
