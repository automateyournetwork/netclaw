/**
 * Local layout persistence for the COMMAND chart.
 *
 * v2 stores DEPARTMENT positions alongside member positions, because a
 * department is the unit an operator actually rearranges — moving "Device
 * Automation" somewhere else has to move its header and every claw under it as
 * one object, and that has to survive a reload.
 *
 * A v1 document is discarded rather than migrated: it only ever held member
 * offsets from a layout whose default packing has since changed, so honouring
 * it would restore positions relative to a chart that no longer exists.
 */
export const POSITION_SCHEMA_VERSION = 2;
const STORAGE_PREFIX = 'netclaw.command.orgchart.layout';
const WORLD_LIMIT = 500;

function storageKey(identity) {
  return `${STORAGE_PREFIX}:${encodeURIComponent(identity || 'default')}`;
}

export function positionId(node) {
  return node?.kind === 'member' && node?.payload?.member_id
    ? `member:${node.payload.member_id}`
    : null;
}

function validCoordinate(value) {
  return Number.isFinite(value) && Math.abs(value) <= WORLD_LIMIT;
}

function validPoint(point) {
  return !!point && validCoordinate(point.x) && validCoordinate(point.y);
}

/** Immutable snapshot of the computed default, for RESET. */
export function snapshotDefaults(nodes, categories) {
  return {
    nodes: new Map(
      (nodes || [])
        .filter((node) => positionId(node))
        .map((node) => [positionId(node), { x: node.position.x, y: node.position.y, z: 0 }]),
    ),
    categories: new Map(
      (categories || []).map((category) => [
        category.name, { x: category.position.x, y: category.position.y, z: 0 },
      ]),
    ),
  };
}

/** Back-compat alias — member-only snapshot. */
export function snapshotDefaultPositions(nodes) {
  return snapshotDefaults(nodes, []).nodes;
}

function read(identity) {
  let raw;
  try { raw = localStorage.getItem(storageKey(identity)); } catch { return null; }
  if (!raw) return null;
  try {
    const document = JSON.parse(raw);
    if (document?.version !== POSITION_SCHEMA_VERSION) throw new Error('schema');
    return document;
  } catch {
    try { localStorage.removeItem(storageKey(identity)); } catch { /* storage unavailable */ }
    return null;
  }
}

/**
 * Overlay a saved layout onto freshly computed nodes/categories.
 *
 * Departments are applied as a DELTA against the default header position, so a
 * saved department keeps its claws in their relative arrangement even when the
 * computed default packing changes underneath it.
 */
export function applySavedLayout(identity, nodes, categories) {
  const document = read(identity);
  if (!document) return false;

  const savedCategories = document.categories || {};
  for (const category of categories || []) {
    const saved = savedCategories[category.name];
    if (!validPoint(saved)) continue;
    const dx = saved.x - category.position.x;
    const dy = saved.y - category.position.y;
    category.position = { x: saved.x, y: saved.y, z: 0 };
    for (const node of nodes || []) {
      if (node.kind !== 'member' || node.category !== category.name) continue;
      node.position = { x: node.position.x + dx, y: node.position.y + dy, z: 0 };
    }
  }

  // Per-claw offsets win over the department delta: an operator who placed one
  // claw deliberately meant that exact spot.
  const savedNodes = document.nodes || {};
  for (const node of nodes || []) {
    const id = positionId(node);
    const saved = id ? savedNodes[id] : null;
    if (!validPoint(saved)) continue;
    node.position = { x: saved.x, y: saved.y, z: 0 };
  }
  return true;
}

/** Back-compat alias — member-only apply (used for a single appended node). */
export function applySavedPositions(identity, nodes) {
  return applySavedLayout(identity, nodes, []);
}

export function saveLayout(identity, nodes, categories) {
  const savedNodes = {};
  for (const node of nodes || []) {
    const id = positionId(node);
    if (!id || !validPoint(node.position)) continue;
    savedNodes[id] = { x: node.position.x, y: node.position.y };
  }
  const savedCategories = {};
  for (const category of categories || []) {
    if (!validPoint(category.position)) continue;
    savedCategories[category.name] = { x: category.position.x, y: category.position.y };
  }
  try {
    localStorage.setItem(storageKey(identity), JSON.stringify({
      version: POSITION_SCHEMA_VERSION,
      nodes: savedNodes,
      categories: savedCategories,
    }));
    return true;
  } catch {
    return false;
  }
}

/** Back-compat alias. */
export function savePositions(identity, nodes) {
  return saveLayout(identity, nodes, []);
}

export function clearSavedPositions(identity) {
  try {
    localStorage.removeItem(storageKey(identity));
    return true;
  } catch {
    return false;
  }
}
