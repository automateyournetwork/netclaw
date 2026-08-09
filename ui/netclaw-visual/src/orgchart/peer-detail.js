/**
 * Peer detail panel view-model (feature 101, US1 — FR-002/003/004).
 *
 * Pure: no imports beyond liveness/freshness (both pure), no clock, no DOM.
 *
 * ## The defect
 *
 * `setDetail()` in main.js branches on six kinds — local-core, member-core,
 * integration, device, skill, peer-core — and the org-chart click path passes a
 * **seventh that does not exist**:
 *
 *     } else if (node.kind === 'peer') {
 *       setDetail('federation-peer', node.payload);   // no such branch
 *
 * It falls past all six into the `// Default: overview` block and renders the
 * generic "This NetClaw" summary. So the click *registers* and the panel *does*
 * repaint — with a different subject's content. That is why it reads as "not
 * clickable" even though the mesh is pickable and hover-scales correctly.
 *
 * ## Why not just point it at `peer-core`
 *
 * `peer-core` expects a BGP-session payload from /api/graph — `peer.as`,
 * `peer.routerId`, `peer.peerIp`, `peer.routesReceived`, `peer.adjRibIn`. The
 * org chart carries the /api/n2n shape instead (`identity`, `channel_state`,
 * `inventory_received_at`, `stale`, `in_flight_tasks`). Renaming the kind would
 * render a panel of `undefined`s. The /api/n2n shape is also the *richer* one for
 * federation, which is why the panel is built against it.
 *
 * Every field resolves to a value or an explicit placeholder — never `undefined`.
 */

import { peerViewState } from './liveness.js';

/** Shown instead of an empty cell, so a blank always means "we know it is empty". */
export const PLACEHOLDER = '—';

/** Human sentence per state. The panel says what the state *means*, not just its name. */
export const STATE_SUMMARY = {
  LIVE: 'Channel up now',
  IDLE: 'Federated, idle — nothing wrong',
  STALE: 'Federated, but what we know is old',
  UNKNOWN: 'Never sent an inventory — not a failure',
  UNREACHABLE: 'Was reachable, not now — may need attention',
  SEVERED: 'Deliberately severed',
};

function orPlaceholder(value) {
  if (value === null || value === undefined) return PLACEHOLDER;
  const s = String(value).trim();
  return s === '' ? PLACEHOLDER : s;
}

/**
 * Build the panel view-model for one peer.
 *
 * @param {object} peer a peer row from /api/n2n peers[]
 * @param {number} nowEpochS injected clock
 * @param {object} [opts]
 * @param {string} [opts.label] pre-disambiguated label from normalize.js
 * @param {boolean} [opts.presentInFeed=true] false once the row vanishes (FR-045)
 * @returns {object} view-model with no undefined values
 */
export function peerDetailView(peer, nowEpochS, opts = {}) {
  const view = peerViewState(peer, nowEpochS, opts);
  const row = peer && typeof peer === 'object' ? peer : {};

  return {
    // Heading uses the disambiguated label, but `identity` is always shown as its
    // own row: two peers legitimately share the display name "Hermes", so the
    // label alone cannot tell them apart.
    heading: orPlaceholder(view.label),
    identity: orPlaceholder(view.identity),

    state: view.state,
    stateSummary: STATE_SUMMARY[view.state] || PLACEHOLDER,
    // Raw channel_state kept alongside, so an operator can cross-reference the
    // panel against `n2n_health` output without translating.
    channelState: orPlaceholder(row.channel_state),

    inventoryAge: view.freshness.ageText,
    inventoryJudgement: view.freshness.judgement,
    inventoryReceivedAt: orPlaceholder(view.freshness.receivedAt),

    chatEnabled: view.chatEnabled,
    chatText: view.chatEnabled ? 'enabled' : 'disabled',

    // An empty task list renders as an explicit "none", never as a blank region
    // that could read as "failed to load".
    inFlightTasks: view.inFlightTasks,
    inFlightText: view.inFlightTasks.length === 0
      ? 'none'
      : `${view.inFlightTasks.length} in flight`,

    presentInFeed: view.presentInFeed,
    // FR-045: retained-but-gone must be stated, not implied by staleness.
    notInFeedNotice: view.presentInFeed
      ? null
      : 'No longer present in the feed — this is the last known state',
  };
}
