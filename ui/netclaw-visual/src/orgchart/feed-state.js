/**
 * Poll outcome tracking — freeze and flag (feature 101, FR-041/042/043).
 *
 * Pure: no imports, no clock, no fetch. Times are injected; the caller owns the
 * network. That is what makes the dangerous case testable.
 *
 * ## Why this is a separate module and not three lines in main.js
 *
 * The decision "is this a failure, and what do we show" is the most dangerous
 * logic in the feature. If a failed poll were allowed to recompute liveness, the
 * mesh daemon going down would render all seven peers as dead — an operator
 * would see a total outage that does not exist and go chasing it. A failed poll
 * is not evidence about peers; conflating "I cannot see" with "they are down" is
 * exactly the inversion this guards against.
 *
 * So it lives here, on the pure side, where it is unit-tested — the render layer
 * has no automated coverage at all.
 *
 * The symmetric error matters too: a **successful** poll returning zero peers is
 * a real, renderable state (fresh install), not a failure. Treating it as one
 * would be the same class of mistake in the opposite direction.
 */

export function createFeedState() {
  return {
    lastGood: null,
    lastGoodAt: null,
    consecutiveFailures: 0,
    degraded: false,
    lastError: null,
  };
}

/**
 * Is this payload a usable /api/n2n response?
 *
 * Requires `peers` to be an array. An empty array passes — that is the fresh
 * install case and it must reach the empty-state path, not the failure path.
 *
 * @param {*} payload
 * @returns {boolean}
 */
export function isUsablePayload(payload) {
  return !!payload && typeof payload === 'object' && Array.isArray(payload.peers);
}

/**
 * Record a successful poll.
 *
 * @param {object} feed state from createFeedState()
 * @param {object} payload parsed /api/n2n body
 * @param {number} nowMs injected clock
 * @returns {object} the same feed object, mutated
 */
export function recordSuccess(feed, payload, nowMs) {
  if (!isUsablePayload(payload)) {
    // Shaped wrong => treat as a failure rather than caching garbage that would
    // then be frozen and shown as authoritative.
    return recordFailure(feed, new Error('unusable payload shape'), nowMs);
  }
  feed.lastGood = payload;
  feed.lastGoodAt = nowMs;
  feed.consecutiveFailures = 0;
  feed.degraded = false;        // FR-043: recovery needs no reload, no acknowledgement
  feed.lastError = null;
  return feed;
}

/**
 * Record a failed poll — a throw, a non-2xx, or unparseable body.
 *
 * **Deliberately does not touch `lastGood`** (FR-041). The scene keeps rendering
 * the last known good state and no per-entity liveness is recomputed.
 *
 * @param {object} feed
 * @param {Error|string} error
 * @param {number} nowMs injected clock
 * @returns {object} the same feed object, mutated
 */
export function recordFailure(feed, error, nowMs) {
  feed.consecutiveFailures += 1;
  feed.degraded = true;
  feed.lastError = error instanceof Error ? error.message : String(error || 'unknown');
  // lastGood and lastGoodAt are untouched on purpose.
  return feed;
}

/**
 * What the scene-level indicator should say (FR-042).
 *
 * @param {object} feed
 * @param {number} nowMs injected clock
 * @returns {{degraded: boolean, staleForSeconds: number|null, everSucceeded: boolean,
 *            consecutiveFailures: number, message: string|null}}
 */
export function staleIndicator(feed, nowMs) {
  if (!feed.degraded) {
    return {
      degraded: false,
      staleForSeconds: null,
      everSucceeded: feed.lastGoodAt !== null,
      consecutiveFailures: 0,
      message: null,
    };
  }

  const everSucceeded = feed.lastGoodAt !== null;
  const staleForSeconds = everSucceeded
    ? Math.max(0, Math.floor((nowMs - feed.lastGoodAt) / 1000))
    : null;

  // Distinguish "we had data and lost contact" from "we never had any". The
  // second is a first-run/misconfiguration story, not a stale-data story, and
  // showing an age of 0 for it would be a fabricated reassurance.
  const message = everSucceeded
    ? `stale data — last good poll ${staleForSeconds}s ago`
    : 'no data — never reached the mesh daemon';

  return {
    degraded: true,
    staleForSeconds,
    everSucceeded,
    consecutiveFailures: feed.consecutiveFailures,
    message,
  };
}

/**
 * The payload the scene should render right now.
 *
 * Returns `lastGood` while degraded — that is the freeze half of freeze-and-flag.
 * Returns null only when nothing has ever succeeded, which the caller renders as
 * an empty/first-run state rather than as failure.
 *
 * @param {object} feed
 * @returns {object|null}
 */
export function renderablePayload(feed) {
  return feed.lastGood;
}
