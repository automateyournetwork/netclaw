/**
 * Member health classification (FR-008, FR-008a).
 *
 * Pure: no imports, no clock. `nowEpochS` is injected by the caller, never read
 * from Date.now() here — otherwise the WARM/FAULT boundary is untestable.
 *
 * Four states rather than two, because COLD and FAULT are opposite situations
 * that a binary encoding would merge:
 *
 *   COLD  — never started. Normal. 22 of 29 members on the reference Border.
 *   FAULT — was reachable, no longer is. Needs attention. 2 of 29.
 *
 * Merging them buries a real fault inside a crowd of by-design-cold claws,
 * which is the specific failure this design exists to prevent.
 */

/** WARM/FAULT boundary, seconds (FR-008a). One named constant, not a literal. */
export const WARM_THRESHOLD_S = 900;

export const HOT = 'HOT';
export const WARM = 'WARM';
export const COLD = 'COLD';
export const FAULT = 'FAULT';

/** States that mean "the Border has given up on this member". */
const FAULT_STATES = new Set(['unreachable', 'quarantined', 'removed']);

/**
 * Classify a member into exactly one health state.
 *
 * Precedence is strict and evaluated top-down:
 *   1. HOT   — live === true, whatever else is set
 *   2. FAULT — explicit fault state, regardless of heartbeat age
 *   3. WARM  — seen within WARM_THRESHOLD_S
 *   4. FAULT — seen, but longer ago than the threshold
 *   5. COLD  — never seen at all (default)
 *
 * Note `live` is authoritative over `state`: the two disagree in live data
 * (5 members report `active` while only 4 report `live`).
 *
 * @param {object} member a member from /api/n2n members[]
 * @param {number} nowEpochS current time, seconds since epoch (injected)
 * @returns {'HOT'|'WARM'|'COLD'|'FAULT'}
 */
export function classifyHealth(member, nowEpochS) {
  if (!member || typeof member !== 'object') return COLD;

  if (member.live === true) return HOT;

  const state = String(member.state || '').toLowerCase();
  if (FAULT_STATES.has(state)) return FAULT;

  const age = member.heartbeat_age_s;
  if (age === null || age === undefined || Number.isNaN(Number(age))) {
    // Never seen. Inert by design, not broken.
    return COLD;
  }

  return Number(age) <= WARM_THRESHOLD_S ? WARM : FAULT;
}

/**
 * Count members per health state. Useful for ordering (heat) and the legend.
 *
 * @param {Array<object>} members
 * @param {number} nowEpochS
 * @returns {{HOT:number, WARM:number, COLD:number, FAULT:number}}
 */
export function healthTally(members, nowEpochS) {
  const tally = { [HOT]: 0, [WARM]: 0, [COLD]: 0, [FAULT]: 0 };
  if (!Array.isArray(members)) return tally;
  for (const m of members) tally[classifyHealth(m, nowEpochS)] += 1;
  return tally;
}
