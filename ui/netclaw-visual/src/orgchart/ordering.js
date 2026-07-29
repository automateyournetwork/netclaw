/**
 * Category ordering (FR-006b, FR-034).
 *
 * Pure and deterministic: same input, same order, every time.
 *
 * Heat first, then size, then name. Heat ordering earns its place only on
 * arrival, when the operator has no spatial memory yet and the few live claws
 * should be where the eye lands. Afterwards it works against them — which is
 * why FR-034 requires this to be computed ONCE per session and never from the
 * poll path. A claw that fails changes how it looks, never where it is.
 */

import { classifyHealth, HOT } from './health.js';

export const UNCATEGORISED = 'Uncategorised';

/**
 * Count HOT members in a group — the "heat" that drives ordering.
 *
 * @param {Array<object>} members
 * @param {number} nowEpochS
 * @returns {number}
 */
export function categoryHeat(members, nowEpochS) {
  if (!Array.isArray(members)) return 0;
  return members.reduce((n, m) => n + (classifyHealth(m, nowEpochS) === HOT ? 1 : 0), 0);
}

/**
 * Order categories for layout.
 *
 * Rules, in order:
 *   1. `Uncategorised` always sorts last, whatever its heat. It is a residue
 *      bucket, not a peer of the real categories — even when it contains a hot
 *      member — which happens whenever a live claw's skills match no
 *      integration prefix.
 *   2. More HOT members first.
 *   3. Larger groups first.
 *   4. Name, ascending — the final tiebreak, so the result is deterministic.
 *
 * @param {Map<string, Array<object>>|Array<[string, Array<object>]>} categories
 * @param {number} nowEpochS
 * @returns {Array<{name: string, members: Array<object>, heat: number}>}
 */
export function orderCategories(categories, nowEpochS) {
  const entries = categories instanceof Map ? [...categories.entries()] : Array.isArray(categories) ? categories : [];

  return entries
    .filter((e) => Array.isArray(e) && typeof e[0] === 'string')
    .map(([name, members]) => ({
      name,
      members: Array.isArray(members) ? members : [],
      heat: categoryHeat(members, nowEpochS),
    }))
    .sort((a, b) => {
      const aResidue = a.name === UNCATEGORISED;
      const bResidue = b.name === UNCATEGORISED;
      if (aResidue !== bResidue) return aResidue ? 1 : -1;

      if (b.heat !== a.heat) return b.heat - a.heat;
      if (b.members.length !== a.members.length) return b.members.length - a.members.length;
      return a.name.localeCompare(b.name);
    });
}

/**
 * Order members within a category: HOT first, then FAULT (so a dead claw is
 * near the top of its column rather than buried), then WARM, then COLD; name
 * ascending within each state.
 *
 * @param {Array<object>} members
 * @param {number} nowEpochS
 * @param {(m: object) => string} labelOf
 * @returns {Array<object>} new array
 */
export function orderMembers(members, nowEpochS, labelOf = (m) => m.display_name || m.member_id || '') {
  const RANK = { HOT: 0, FAULT: 1, WARM: 2, COLD: 3 };
  if (!Array.isArray(members)) return [];
  return [...members].sort((a, b) => {
    const ra = RANK[classifyHealth(a, nowEpochS)];
    const rb = RANK[classifyHealth(b, nowEpochS)];
    if (ra !== rb) return ra - rb;
    return String(labelOf(a)).localeCompare(String(labelOf(b)));
  });
}
