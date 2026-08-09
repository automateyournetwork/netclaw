/**
 * Deterministic force-directed layout (feature 102, US2 — FR-039, FR-040, FR-041).
 *
 * Pure: no imports, no clock, no randomness, no three.js.
 *
 * ## Why this is hand-written rather than d3-force
 *
 * Two requirements rule out every off-the-shelf force library:
 *
 *   FR-039 — the same topology MUST produce the same arrangement every run. Force
 *            libraries seed initial positions with Math.random(), so the HUD would
 *            look different on every load and spatial memory becomes impossible.
 *   FR-040 — it MUST settle and STOP. Libraries tick continuously, which is exactly
 *            the system-initiated movement FR-027 forbids, and it would compete with
 *            the render budget forever.
 *
 * Adding a dependency and then fighting both of its defaults is more code and more
 * risk than the ~90 lines below.
 *
 * ## How determinism is achieved
 *
 * Initial positions come from a hash of the node's own identity string, spread onto
 * a circle. Identity is stable across restarts — it is the same property spec 101
 * relied on to disambiguate the two peers both named "Hermes". No Math.random, no
 * Date, nothing environmental. That makes FR-039 a one-line test: solve twice,
 * assert deep equality.
 *
 * Iteration count is fixed rather than energy-thresholded. A threshold is
 * data-dependent and can fail to converge; a count is bounded by construction, which
 * is what FR-040 actually asks for.
 */

export const DEFAULTS = {
  iterations: 300,
  repulsion: 9000,     // node-node separation
  attraction: 0.006,   // link spring
  centering: 0.012,    // pull toward origin so the graph cannot drift away
  damping: 0.85,
  maxStep: 6,          // per-iteration clamp; stops one bad frame flinging a node
};

/**
 * FNV-1a, 32-bit. Chosen for being short, dependency-free and stable across engines —
 * the point is reproducibility, not cryptographic quality.
 *
 * @param {string} str
 * @returns {number} unsigned 32-bit
 */
export function hashId(str) {
  let h = 0x811c9dc5;
  const s = String(str);
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/**
 * Deterministic starting position for one node, spread on a circle by its hash.
 * Two different identities land in different places; the same identity always lands
 * in the same place.
 */
function seedPosition(id, index, count) {
  const h = hashId(id);
  const angle = ((h % 3600) / 3600) * Math.PI * 2;
  // Radius also derived from the hash so nodes do not all start on one circle,
  // which would make the first iterations degenerate.
  const radius = 30 + ((h >>> 12) % 40);
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, z: 0 };
}

/**
 * Solve a force-directed arrangement. Runs to completion and returns; there is no
 * tick loop and nothing is scheduled (FR-040).
 *
 * @param {object} input
 * @param {Array<{id:string}>} input.nodes
 * @param {Array<[string,string]>} input.links source/target id pairs
 * @param {Iterable<string>} [input.pinned] ids held fixed (FR-041)
 * @param {object} [opts] overrides for DEFAULTS
 * @returns {{[nodeId: string]: {x:number,y:number,z:number}}}
 */
export function forceLayout(input, opts = {}) {
  const cfg = { ...DEFAULTS, ...opts };
  const nodes = Array.isArray(input?.nodes) ? input.nodes : [];
  const links = Array.isArray(input?.links) ? input.links : [];
  const pinned = new Set(input?.pinned || []);
  if (nodes.length === 0) return {};

  // Sort by id so iteration order — and therefore floating-point accumulation
  // order — is identical regardless of how the caller ordered its array. Without
  // this, the same graph could produce different output from a differently-ordered
  // input, which would violate FR-039 in a way that is very hard to spot.
  const ordered = [...nodes].sort((a, b) => String(a.id).localeCompare(String(b.id)));

  const pos = new Map();
  const vel = new Map();
  ordered.forEach((n, i) => {
    pos.set(n.id, seedPosition(n.id, i, ordered.length));
    vel.set(n.id, { x: 0, y: 0 });
  });

  // Pinned nodes are held at their supplied positions and act as anchors.
  for (const [id, p] of Object.entries(input?.pinnedPositions || {})) {
    if (pos.has(id)) pos.set(id, { x: p.x, y: p.y, z: 0 });
  }

  const ids = ordered.map((n) => n.id);
  const linkPairs = links.filter(([a, b]) => pos.has(a) && pos.has(b));

  for (let iter = 0; iter < cfg.iterations; iter += 1) {
    // Repulsion — every pair, O(n²). At ~40 nodes that is 1600 pair-checks per
    // iteration, trivially fast, and a quadtree would add complexity for no gain.
    for (let i = 0; i < ids.length; i += 1) {
      for (let j = i + 1; j < ids.length; j += 1) {
        const a = pos.get(ids[i]); const b = pos.get(ids[j]);
        let dx = a.x - b.x; let dy = a.y - b.y;
        let d2 = dx * dx + dy * dy;
        if (d2 < 0.01) { dx = 0.1; dy = 0.1; d2 = 0.02; }   // coincident guard
        const f = cfg.repulsion / d2;
        const d = Math.sqrt(d2);
        const fx = (dx / d) * f; const fy = (dy / d) * f;
        vel.get(ids[i]).x += fx; vel.get(ids[i]).y += fy;
        vel.get(ids[j]).x -= fx; vel.get(ids[j]).y -= fy;
      }
    }

    // Attraction along links
    for (const [a, b] of linkPairs) {
      const pa = pos.get(a); const pb = pos.get(b);
      const dx = pb.x - pa.x; const dy = pb.y - pa.y;
      vel.get(a).x += dx * cfg.attraction; vel.get(a).y += dy * cfg.attraction;
      vel.get(b).x -= dx * cfg.attraction; vel.get(b).y -= dy * cfg.attraction;
    }

    // Centering + integrate
    for (const id of ids) {
      const p = pos.get(id);
      const v = vel.get(id);
      v.x -= p.x * cfg.centering;
      v.y -= p.y * cfg.centering;
      v.x *= cfg.damping;
      v.y *= cfg.damping;

      if (pinned.has(id)) { v.x = 0; v.y = 0; continue; }   // FR-041

      p.x += clamp(v.x, cfg.maxStep);
      p.y += clamp(v.y, cfg.maxStep);
    }
  }

  const out = {};
  for (const id of ids) {
    const p = pos.get(id);
    out[id] = { x: round(p.x), y: round(p.y), z: 0 };
  }
  return out;
}

function clamp(v, max) {
  return v > max ? max : (v < -max ? -max : v);
}

/** Rounded so tiny float differences never surface as "different" arrangements. */
function round(v) {
  return Math.round(v * 100) / 100;
}
