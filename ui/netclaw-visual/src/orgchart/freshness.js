/**
 * Inventory freshness in operator terms (feature 101, FR-004).
 *
 * Pure: no imports, no clock. `nowEpochS` is injected, never read from
 * Date.now() — otherwise every boundary here is untestable, the same reason
 * health.js takes it as a parameter.
 *
 * FR-004 forbids showing a bare timestamp. An operator should not have to do
 * date arithmetic to learn a peer went quiet twelve days ago, and
 * "2026-07-25T16:43:51Z" requires exactly that.
 *
 * The distinction that matters most here is **never vs zero**. A peer that has
 * never sent an inventory (AB, Carapace) has `inventory_received_at: null`. If
 * that renders as "just now" it reads as the healthiest possible value, which
 * is the inverse of the truth. So `ageSeconds` is `null`, not `0`, and
 * `judgement` is its own state.
 */

/** Age above which a peer is *aging* — visible before the daemon flips `stale`. */
export const AGING_THRESHOLD_S = 3600;        // 1 hour

/** Age above which we call it stale regardless of what the API flag says. */
export const STALE_THRESHOLD_S = 86400;       // 24 hours

export const FRESH = 'fresh';
export const AGING = 'aging';
export const STALE = 'stale';
export const NEVER = 'never';

/**
 * Parse an ISO-8601 `...Z` timestamp to epoch seconds.
 *
 * Deliberately narrow: the only producer is the daemon's `_now()`, which always
 * emits `%Y-%m-%dT%H:%M:%SZ`. Anything else is treated as absent rather than
 * guessed at, because a silently mis-parsed date would produce a confident wrong
 * age — worse than admitting we do not know.
 *
 * @param {string|null|undefined} iso
 * @returns {number|null} epoch seconds, or null if unusable
 */
export function parseStamp(iso) {
  if (typeof iso !== 'string' || iso.trim() === '') return null;
  const ms = Date.parse(iso);
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : null;
}

/**
 * Render an age as something an operator reads at a glance.
 *
 * @param {number|null} seconds
 * @returns {string}
 */
export function formatAge(seconds) {
  if (seconds === null || !Number.isFinite(seconds)) return 'never';
  const s = Math.max(0, Math.floor(seconds));
  if (s < 45) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

/**
 * Build the FreshnessView for one peer (data-model.md §3).
 *
 * `judgement` combines two inputs and takes the **pessimistic** reading:
 *   - derived age (so the HUD can say "aging" before the daemon flips `stale`)
 *   - the API's own `stale` flag (authoritative when set — the daemon knows
 *     things we do not, e.g. that a channel dropped)
 *
 * Pessimistic-wins mirrors normalize.js's `STATE_RESTRICTIVENESS`: claiming a
 * stale peer is fresh is the dangerous direction of the error.
 *
 * @param {object} peer a peer row from /api/n2n peers[]
 * @param {number} nowEpochS current time in epoch seconds (injected)
 * @returns {{receivedAt: string|null, ageSeconds: number|null, ageText: string,
 *            judgement: 'fresh'|'aging'|'stale'|'never'}}
 */
export function freshnessOf(peer, nowEpochS) {
  const row = peer && typeof peer === 'object' ? peer : {};
  const receivedAt = typeof row.inventory_received_at === 'string'
    ? row.inventory_received_at
    : null;

  const stamp = parseStamp(receivedAt);
  if (stamp === null) {
    // Never received, or a timestamp we refuse to guess at. Either way we have
    // no age — and `null` must never collapse to 0 (FR-004).
    return { receivedAt, ageSeconds: null, ageText: 'never', judgement: NEVER };
  }

  const ageSeconds = Math.max(0, nowEpochS - stamp);

  let judgement;
  if (ageSeconds >= STALE_THRESHOLD_S) judgement = STALE;
  else if (ageSeconds >= AGING_THRESHOLD_S) judgement = AGING;
  else judgement = FRESH;

  // The API flag can only make it worse, never better.
  if (row.stale === true && judgement !== STALE) judgement = STALE;

  return { receivedAt, ageSeconds, ageText: formatAge(ageSeconds), judgement };
}
