/**
 * Derive a member's org-chart category (FR-006, FR-006a).
 *
 * Pure: no imports, no I/O. The integration catalog is an ARGUMENT, never an
 * import — that is what makes Constitution Principle VI (multi-vendor
 * neutrality) testable rather than merely asserted: the same code must produce
 * a different, correct chart for a different operator's catalog.
 *
 * Why not `profile`? On the reference Border it is 1:1 with the member —
 * 28 distinct values across 29 members — so grouping by it yields 28 groups of
 * one. The middle tier has to be a *rule*, not a list of member names, because
 * NetClaw ships to operators whose members we have never seen.
 *
 * The rule:
 *   member.skills[] -> integration (skill starts with one of its prefixes)
 *                   -> integration.category
 *                   -> the most frequent category among that member's skills
 */

export const UNCATEGORISED = 'Uncategorised';

/**
 * Category for one member.
 *
 * Ties are broken by catalog order so the result is deterministic — two runs
 * over the same input must produce the same chart.
 *
 * @param {object} member a member from /api/n2n members[]
 * @param {Array<{category:string, prefixes:string[]}>} integrationCatalog
 * @returns {string} category name, or UNCATEGORISED — never empty, never throws
 */
export function categorizeMember(member, integrationCatalog) {
  if (!member || typeof member !== 'object') return UNCATEGORISED;
  if (!Array.isArray(integrationCatalog) || integrationCatalog.length === 0) return UNCATEGORISED;

  const skills = Array.isArray(member.skills) ? member.skills : [];
  if (skills.length === 0) return UNCATEGORISED;

  /** @type {Map<string, number>} votes per category */
  const votes = new Map();
  /** @type {Map<string, number>} first catalog index that voted, for tie-breaks */
  const firstSeen = new Map();

  for (const skill of skills) {
    if (typeof skill !== 'string') continue;

    for (let i = 0; i < integrationCatalog.length; i += 1) {
      const integration = integrationCatalog[i];
      if (!integration || !Array.isArray(integration.prefixes)) continue;

      const matches = integration.prefixes.some(
        (p) => typeof p === 'string' && p.length > 0 && skill.startsWith(p),
      );
      if (!matches) continue;

      const category = integration.category || UNCATEGORISED;
      votes.set(category, (votes.get(category) || 0) + 1);
      if (!firstSeen.has(category)) firstSeen.set(category, i);
      break; // first matching integration wins for this skill
    }
  }

  if (votes.size === 0) return UNCATEGORISED;

  let best = UNCATEGORISED;
  let bestVotes = -1;
  let bestIndex = Number.MAX_SAFE_INTEGER;
  for (const [category, count] of votes) {
    const index = firstSeen.get(category);
    if (count > bestVotes || (count === bestVotes && index < bestIndex)) {
      best = category;
      bestVotes = count;
      bestIndex = index;
    }
  }
  return best;
}

/**
 * Group members into categories (FR-006).
 *
 * Members with `node_type === 'edge'` are EXCLUDED — edge nodes belong in the
 * edge lane, not the member chart (FR-007), and categorising a phone by the
 * skills it happens to carry would place it in a column it does not belong to.
 *
 * @param {Array<object>} members
 * @param {Array<object>} integrationCatalog
 * @returns {Map<string, Array<object>>} category name -> members, insertion-ordered
 */
export function categorizeMembers(members, integrationCatalog) {
  /** @type {Map<string, Array<object>>} */
  const grouped = new Map();
  if (!Array.isArray(members)) return grouped;

  for (const member of members) {
    if (!member || typeof member !== 'object') continue;
    if (member.node_type === 'edge') continue;

    const category = categorizeMember(member, integrationCatalog);
    if (!grouped.has(category)) grouped.set(category, []);
    grouped.get(category).push(member);
  }
  return grouped;
}

/**
 * Extract the {category, prefixes} catalog from the shipped integration list.
 * Tolerates entries missing either field so a malformed catalog degrades to
 * UNCATEGORISED rather than throwing.
 *
 * @param {Array<object>} integrations
 * @returns {Array<{id:string, category:string, prefixes:string[]}>}
 */
export function toCatalog(integrations) {
  if (!Array.isArray(integrations)) return [];
  return integrations
    .filter((i) => i && typeof i === 'object' && Array.isArray(i.prefixes) && i.category)
    .map((i) => ({ id: i.id || '', category: i.category, prefixes: i.prefixes }));
}
