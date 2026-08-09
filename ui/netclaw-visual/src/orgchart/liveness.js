/**
 * Peer liveness classification (feature 101, US3 — FR-012/016/017).
 *
 * Pure: no imports beyond freshness (also pure), no clock. `nowEpochS` injected.
 *
 * ## The defect this exists to fix
 *
 * `orgchart-render/nodes.js` treats peers as *structural*, so they skip the
 * four-state member treatment entirely and take their colour from
 * `colorForStructural()`:
 *
 *     if (node.severed) return 0xa85c5c;
 *     if (channelState === 'unreachable' || channelState === 'reconnecting')
 *                        return 0x86a9cc;
 *     return 0x8ad6ff;                       // <- the catch-all
 *
 * Three colours, one fixed form, no motion. It **never reads `stale`**, and
 * `channel_state: "unknown"` falls straight through to the healthy default.
 * Measured against the live feed, five of seven peers land in that catch-all —
 * Byrn, Nicholas, Hermes, AB and Carapace all render identically to a healthy
 * Nate. An operator cannot tell a peer that has been quiet for twelve days from
 * one with a live channel.
 *
 * Six states rather than three, because the catch-all was hiding three genuinely
 * different situations: normal-and-idle, gone-stale, and never-heard-from.
 */

import { freshnessOf, NEVER, STALE as STALE_JUDGEMENT } from './freshness.js';

export const LIVE = 'LIVE';
export const IDLE = 'IDLE';
export const STALE = 'STALE';
export const UNKNOWN = 'UNKNOWN';
export const UNREACHABLE = 'UNREACHABLE';
export const SEVERED = 'SEVERED';

/** Declared order, most-known-good first. Used by tests and by the render table. */
export const PEER_STATES = [LIVE, IDLE, STALE, UNKNOWN, UNREACHABLE, SEVERED];

/** Channel states meaning "was reachable, is not now". */
const UNREACHABLE_CHANNELS = new Set(['unreachable', 'reconnecting']);

/**
 * Classify a peer into exactly one of the six states.
 *
 * Precedence is strict and evaluated top-down. The order encodes two rules the
 * spec insists on:
 *
 *   1. SEVERED first — a severed peer is NEVER reported as anything else,
 *      whatever its other fields say (FR-017). Claiming a severed peer is live
 *      is the dangerous direction of the error.
 *   2. LIVE beats staleness — an `up` channel is direct evidence of reachability
 *      now, which outranks an old inventory. A peer can legitimately have a live
 *      channel and a stale inventory.
 *
 * UNKNOWN sits between STALE and UNREACHABLE deliberately: "we have never heard
 * from this peer" is not a failure (FR-016/017). AB and Carapace are in this
 * state and nothing is known to be wrong with either.
 *
 * @param {object} peer a peer row from /api/n2n peers[]
 * @param {number} nowEpochS current time in epoch seconds (injected)
 * @returns {'LIVE'|'IDLE'|'STALE'|'UNKNOWN'|'UNREACHABLE'|'SEVERED'}
 */
export function classifyPeer(peer, nowEpochS) {
  const row = peer && typeof peer === 'object' ? peer : {};
  const state = String(row.state || '').toLowerCase();
  const channel = String(row.channel_state || '').toLowerCase();

  // 1. Deliberately cut. Terminal until re-enrolled.
  if (state === 'severed') return SEVERED;

  // 2. A live channel is present-tense evidence and outranks inventory age.
  if (channel === 'up') return LIVE;

  // 3. Was reachable, is not now. Actionable.
  if (UNREACHABLE_CHANNELS.has(channel)) return UNREACHABLE;

  const fresh = freshnessOf(row, nowEpochS);

  // 4. Never told us anything — NOT a failure (FR-016/017).
  if (fresh.judgement === NEVER) return UNKNOWN;

  // 5. Federated, but what we know is old.
  if (fresh.judgement === STALE_JUDGEMENT) return STALE;

  // 6. Normal steady state: federated, no live channel, inventory fresh.
  return IDLE;
}

/**
 * Full view state for one peer (data-model.md §2).
 *
 * `label` is passed in rather than derived, because disambiguation is a
 * whole-list operation (two peers legitimately share "Hermes") and belongs to
 * normalize.js, which already owns it.
 *
 * @param {object} peer a peer row from /api/n2n peers[]
 * @param {number} nowEpochS injected clock
 * @param {object} [opts]
 * @param {string} [opts.label] pre-disambiguated label
 * @param {boolean} [opts.presentInFeed=true] false once the row vanishes (FR-045)
 */
export function peerViewState(peer, nowEpochS, opts = {}) {
  const row = peer && typeof peer === 'object' ? peer : {};
  return {
    identity: typeof row.identity === 'string' ? row.identity : '',
    label: opts.label || row.display_name || row.identity || 'unknown',
    state: classifyPeer(row, nowEpochS),
    freshness: freshnessOf(row, nowEpochS),
    chatEnabled: row.chat_enabled === true || row.chat_enabled === 1,
    inFlightTasks: Array.isArray(row.in_flight_tasks) ? row.in_flight_tasks : [],
    presentInFeed: opts.presentInFeed !== false,
  };
}

/** True when this state means an operator may need to act. */
export function isActionable(state) {
  return state === UNREACHABLE || state === SEVERED;
}
