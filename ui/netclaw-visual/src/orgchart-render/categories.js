import * as THREE from 'three';

import { removeLabelElements } from './css2d.js';

const ACTIVE_STATES = new Set(['HOT', 'WARM']);

const RAIL = {
  modern: { color: 0x5f83a8, opacity: 0.34, dim: 0.07 },
  retro: { color: 0x000000, opacity: 1, dim: 0.25 },
};

let theme = 'modern';

export function setCategoryTheme(next) {
  theme = next === 'retro' ? 'retro' : 'modern';
  return theme;
}

// NOT named rail(): buildCategories has a local `const rail` for the mesh, which
// shadows a module-level rail() and makes the call a temporal-dead-zone error.
function railStyle() {
  return RAIL[theme] || RAIL.modern;
}

export function summariseCategories(categories, nodes) {
  const members = (nodes || []).filter((node) => node.kind === 'member');
  return (categories || []).map((category) => {
    const owned = members.filter((node) => node.category === category.name);
    return {
      ...category,
      count: owned.length,
      active: owned.filter((node) => ACTIVE_STATES.has(node.health)).length,
      attention: owned.filter((node) => node.health === 'FAULT').length,
    };
  });
}

function summaryText(summary) {
  const claws = `${summary.count} claw${summary.count === 1 ? '' : 's'}`;
  const active = `${summary.active} active`;
  const attention = summary.attention ? ` · ${summary.attention} attention` : '';
  return `${summary.name}\n${claws} · ${active}${attention}`;
}

/** Render the capability departments that member links already route through. */
export function buildCategories(categories, nodes, makeLabel) {
  const group = new THREE.Group();
  group.name = 'orgchart-categories';
  const entries = [];
  const geometries = [];
  const materials = [];

  for (const summary of summariseCategories(categories, nodes)) {
    const owned = (nodes || []).filter(
      (node) => node.kind === 'member' && node.category === summary.name,
    );
    const bottomY = owned.length
      ? Math.min(...owned.map((node) => node.position.y)) - 3.5
      : summary.position.y - 8;
    const geometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(summary.position.x - 7, summary.position.y, -0.8),
      new THREE.Vector3(summary.position.x + 7, summary.position.y, -0.8),
      new THREE.Vector3(summary.position.x, summary.position.y - 0.8, -0.8),
      new THREE.Vector3(summary.position.x, bottomY, -0.8),
    ]);
    geometries.push(geometry);
    const material = new THREE.LineBasicMaterial({
      color: railStyle().color, transparent: true, opacity: railStyle().opacity,
    });
    materials.push(material);
    const rail = new THREE.LineSegments(geometry, material);
    group.add(rail);

    const label = makeLabel(summaryText(summary));
    label.element.classList.add('category-label');
    if (summary.attention) label.element.classList.add('category-label-attention');
    label.element.dataset.category = summary.name;
    label.position.set(summary.position.x, summary.position.y + 3.4, 0);
    group.add(label);

    // A real grab target for the DEPARTMENT. Dragging this moves the header and
    // every claw under it as one object, which is how an operator thinks about
    // "put Device Automation over there". Nearly invisible: the CSS2D card is
    // the thing you see, this is the thing you hit.
    const handleGeometry = new THREE.PlaneGeometry(16, 7);
    const handleMaterial = new THREE.MeshBasicMaterial({
      color: 0xffffff, transparent: true, opacity: 0.001, depthWrite: false,
    });
    geometries.push(handleGeometry);
    materials.push(handleMaterial);
    const handle = new THREE.Mesh(handleGeometry, handleMaterial);
    handle.position.set(summary.position.x, summary.position.y + 3.4, 0.4);
    handle.userData = { categoryName: summary.name, isCategoryHandle: true };
    group.add(handle);

    entries.push({ name: summary.name, label, rail, handle, summary });
  }

  return {
    group,
    entries,
    dispose() {
      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
      // Department headers are CSS2D: without this every rebuild (drag commit,
      // poll, theme switch) left a frozen duplicate card on screen.
      removeLabelElements(group);
    },
  };
}

/**
 * Re-aim the department rails IN PLACE.
 *
 * Must not rebuild: DragControls holds a live reference to the handle mesh, so
 * replacing the group mid-drag would leave it dragging a disposed object.
 */
export function updateCategoryRails(renderer, categories, nodes) {
  for (const entry of renderer?.entries || []) {
    const category = (categories || []).find((candidate) => candidate.name === entry.name);
    if (!category || !entry.rail?.geometry?.attributes?.position) continue;
    const owned = (nodes || []).filter(
      (node) => node.kind === 'member' && node.category === entry.name,
    );
    const { x, y } = category.position;
    const bottomY = owned.length
      ? Math.min(...owned.map((node) => node.position.y)) - 3.5
      : y - 8;
    const points = entry.rail.geometry.attributes.position;
    points.setXYZ(0, x - 7, y, -0.8);
    points.setXYZ(1, x + 7, y, -0.8);
    points.setXYZ(2, x, y - 0.8, -0.8);
    points.setXYZ(3, x, bottomY, -0.8);
    points.needsUpdate = true;
    entry.rail.geometry.computeBoundingSphere();
  }
}

export function updateCategorySummaries(renderer, categories, nodes) {
  const summaries = new Map(
    summariseCategories(categories, nodes).map((summary) => [summary.name, summary]),
  );
  if (summaries.size !== renderer?.entries?.length) return false;

  for (const entry of renderer.entries) {
    const summary = summaries.get(entry.name);
    if (!summary) return false;
    entry.summary = summary;
    entry.label.element.textContent = summaryText(summary);
    entry.label.element.classList.toggle('category-label-attention', summary.attention > 0);
  }
  return true;
}

export function highlightCategories(renderer, matches, focusing) {
  for (const entry of renderer?.entries || []) {
    const hit = !focusing || matches(entry.name);
    entry.label.element.style.opacity = hit ? '1' : '0.18';
    entry.rail.material.opacity = hit ? railStyle().opacity : railStyle().dim;
  }
}
