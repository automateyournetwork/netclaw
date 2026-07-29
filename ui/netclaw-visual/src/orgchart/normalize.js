/**
 * Peer de-duplication and label resolution.
 *
 * Pure: imports nothing, touches no DOM, no clock, no randomness.
 * See specs/072-hud-2-org-chart/contracts/layout-contract.md.
 *
 * FR-014 — de-duplicate peers by identity, and disambiguate peers that share a
 * display name.
 *
 * The spec originally assumed the live feed returned one peer twice with
 * conflicting states. Implementation showed otherwise: the two "Hermes" rows
 * carry *different* identities (as65007-8.8.8.8 and as65008-8.8.8.8) — the same
 * router-id re-enrolled under a new AS, leaving the old severed entry behind.
 * They are genuinely two peers, so dedup-by-identity correctly keeps both, and
 * the real defect is that they render as two indistinguishable "Hermes" nodes.
 * Hence two functions: dedupePeers guards against true duplicates, and
 * disambiguateLabels makes same-named distinct peers tellable apart.
 *
 * FR-015 — both enrolled edge nodes carry `display_name: null`; without a
 * fallback they render as blank labels.
 */

/**
 * Peer connection states, most restrictive first. A peer reported in two
 * states is shown in the more restrictive one: claiming a severed peer is
 * federated is the dangerous direction of the error, so ties resolve toward
 * the pessimistic reading.
 */
const STATE_RESTRICTIVENESS = ['severed', 'quarantined', 'unreachable', 'reconnecting', 'federated'];

function restrictiveness(state) {
  const i = STATE_RESTRICTIVENESS.indexOf(String(state || '').toLowerCase());
  // Unknown states sort as least restrictive but still lose to any known one.
  return i === -1 ? STATE_RESTRICTIVENESS.length : i;
}

/**
 * Collapse peers sharing an `identity` into one entry (FR-014).
 * Preserves first-seen order; the surviving entry keeps the most restrictive
 * `state` seen across duplicates.
 *
 * @param {Array<object>} peers
 * @returns {Array<object>} new array, inputs not mutated
 */
export function dedupePeers(peers) {
  if (!Array.isArray(peers)) return [];

  /** @type {Map<string, object>} */
  const byIdentity = new Map();

  for (const peer of peers) {
    if (!peer || typeof peer !== 'object') continue;
    const key = peer.identity || peer.display_name || JSON.stringify(peer);
    const existing = byIdentity.get(key);

    if (!existing) {
      byIdentity.set(key, { ...peer });
      continue;
    }
    // Same peer seen twice — keep the more restrictive state.
    if (restrictiveness(peer.state) < restrictiveness(existing.state)) {
      byIdentity.set(key, { ...existing, state: peer.state });
    }
  }

  return [...byIdentity.values()];
}

/**
 * Resolve a never-empty display label (FR-015).
 *
 * Precedence: display_name -> tail of member_id after "/" -> identity ->
 * "unknown". Total: never throws, never returns "".
 *
 * @param {object} entity a peer or member
 * @returns {string}
 */
export function resolveLabel(entity) {
  if (!entity || typeof entity !== 'object') return 'unknown';

  const name = typeof entity.display_name === 'string' ? entity.display_name.trim() : '';
  if (name) return name;

  const memberId = typeof entity.member_id === 'string' ? entity.member_id.trim() : '';
  if (memberId) {
    const tail = memberId.split('/').pop().trim();
    if (tail) return tail;
  }

  const identity = typeof entity.identity === 'string' ? entity.identity.trim() : '';
  if (identity) return identity;

  return 'unknown';
}

/**
 * Make same-named entities tellable apart (FR-014).
 *
 * Two distinct peers legitimately sharing a display name (a claw re-enrolled
 * under a new AS, leaving the old entry severed) would otherwise render as two
 * identical labels. Entities whose label is already unique are returned
 * untouched — disambiguation must not add noise to the common case.
 *
 * @param {Array<object>} entities peers and/or members
 * @returns {Array<{entity: object, label: string}>} same order as input
 */
export function disambiguateLabels(entities) {
  if (!Array.isArray(entities)) return [];

  const resolved = entities
    .filter((e) => e && typeof e === 'object')
    .map((entity) => ({ entity, label: resolveLabel(entity) }));

  const counts = new Map();
  for (const { label } of resolved) counts.set(label, (counts.get(label) || 0) + 1);

  return resolved.map(({ entity, label }) => {
    if (counts.get(label) === 1) return { entity, label };

    // Collision. Qualify with whatever distinguishes them, shortest first.
    const identity = typeof entity.identity === 'string' ? entity.identity : '';
    const qualifier = identity.split('-')[0] || identity || entity.member_id || '';
    return { entity, label: qualifier ? `${label} (${qualifier})` : label };
  });
}
