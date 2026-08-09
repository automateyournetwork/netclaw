/**
 * Link rendering — six distinguishable styles (FR-010, FR-011).
 *
 * | style             | meaning                                    |
 * |-------------------|--------------------------------------------|
 * | en2n-healthy      | federated peer, channel up                 |
 * | en2n-unreachable  | federated peer, channel down               |
 * | en2n-severed      | trust withdrawn — visibly broken           |
 * | in2n-healthy      | member reachable                           |
 * | in2n-cold         | member inert by design                     |
 * | edge-push         | Border -> device, ASYMMETRIC (FR-011)      |
 *
 * The edge link is drawn differently on purpose: a member delegation is a round
 * trip, while the push channel only ever runs Border -> device. Drawing them
 * alike would imply a capability the phone does not have.
 */

import * as THREE from 'three';

export const LINK_STYLES = {
  'en2n-healthy': { color: 0x65c3ff, opacity: 0.55, dash: 0, width: 1 },
  'en2n-unreachable': { color: 0x5b7fa6, opacity: 0.3, dash: 1.6, width: 1 },
  'en2n-severed': { color: 0xff5d5d, opacity: 0.45, dash: 0.7, width: 1, broken: true },
  'in2n-healthy': { color: 0x37d67a, opacity: 0.45, dash: 0, width: 1 },
  'in2n-cold': { color: 0x3a4654, opacity: 0.22, dash: 1.2, width: 1 },
  'edge-push': { color: 0xe65733, opacity: 0.6, dash: 1.0, width: 1, arrow: true },
};

/**
 * Retro links: plain high-contrast draughtsman's lines on a light client area.
 * The dash pattern and the severed break are preserved — those carry meaning,
 * the glow did not.
 */
const RETRO_LINK_STYLES = {
  'en2n-healthy': { color: 0x000080, opacity: 1, dash: 0, width: 1 },
  'en2n-unreachable': { color: 0x808080, opacity: 1, dash: 1.6, width: 1 },
  'en2n-severed': { color: 0x800000, opacity: 1, dash: 0.7, width: 1, broken: true },
  'in2n-healthy': { color: 0x000000, opacity: 1, dash: 0, width: 1 },
  'in2n-cold': { color: 0x808080, opacity: 1, dash: 1.2, width: 1 },
  'edge-push': { color: 0x800000, opacity: 1, dash: 1.0, width: 1, arrow: true },
};

let theme = 'modern';

export function setLinkTheme(next) {
  theme = next === 'retro' ? 'retro' : 'modern';
  return theme;
}

function styles() {
  return theme === 'retro' ? RETRO_LINK_STYLES : LINK_STYLES;
}

/**
 * Choose a style for a node's link to the Border.
 *
 * @param {object} node
 * @returns {string} key into LINK_STYLES
 */
export function styleForNode(node) {
  if (node.kind === 'peer') {
    if (node.severed) return 'en2n-severed';
    const ch = String(node.channelState || '').toLowerCase();
    return ch === 'up' ? 'en2n-healthy' : 'en2n-unreachable';
  }
  if (node.kind === 'edge') return 'edge-push';
  return node.health === 'HOT' || node.health === 'WARM' ? 'in2n-healthy' : 'in2n-cold';
}

/**
 * Build links from the Border to every other node.
 *
 * @param {Array<object>} layoutNodes
 * @param {Array<object>} categories
 * @returns {{group: THREE.Group, dispose: Function}}
 */
/**
 * Feature 102: member links elbow through their category header, which is org-chart
 * furniture pinned at a fixed position. Under Ring/Grid/force the members move but
 * the headers cannot, so the elbows stretch across the whole scene to waypoints that
 * no longer mean anything. Route directly instead — the link still says exactly what
 * it said before (this member reports to the Border), just without a detour through
 * a landmark that is no longer there.
 */
export function buildLinks(layoutNodes, categories, useCategoryRouting = true) {
  const group = new THREE.Group();
  group.name = 'orgchart-links';
  const disposables = [];

  const nodes = layoutNodes || [];
  const border = nodes.find((n) => n.kind === 'border');
  if (!border) return { group, dispose() {}, flows: [] };

  // Feature 101 (US4): flow markers for peers with a LIVE channel only.
  const flows = [];

  const origin = new THREE.Vector3(border.position.x, border.position.y, border.position.z);

  for (const node of nodes) {
    if (node === border) continue;

    const styleKey = styleForNode(node);
    const style = styles()[styleKey];
    const target = new THREE.Vector3(node.position.x, node.position.y, node.position.z);

    // Members route via their category header so the chart reads as a chart —
    // an elbow through the column, not 100 straight lines to one point.
    let points;
    if (node.kind === 'member' && useCategoryRouting) {
      const cat = (categories || []).find((c) => c.name === node.category);
      const via = cat
        ? new THREE.Vector3(cat.position.x, cat.position.y + 2, cat.position.z)
        : new THREE.Vector3(target.x, origin.y - 10, 0);
      points = [origin, new THREE.Vector3(origin.x, via.y + 6, 0), via, target];
    } else if (style.broken) {
      // A severed link is drawn with its middle missing — the break is the
      // message, so it must survive greyscale (SC-007) rather than rely on red.
      const a = origin.clone().lerp(target, 0.32);
      const b = origin.clone().lerp(target, 0.68);
      group.add(makeLine([origin, a], style, disposables));
      group.add(makeLine([b, target], style, disposables));
      continue;
    } else {
      points = [origin, target];
    }

    group.add(makeLine(points, style, disposables));
    if (style.arrow) group.add(makeArrow(origin, target, style, disposables));

    // Feature 101 (US4/FR-018): only a LIVE channel flows. IDLE, STALE, UNKNOWN,
    // UNREACHABLE and SEVERED are all static, so motion means exactly one thing:
    // this link is carrying capability right now.
    //
    // FR-019: /api/n2n exposes no per-link direction, so flow runs peer -> Border
    // to represent inbound capability availability, and that choice is recorded
    // here rather than left for a reader to infer from the animation.
    if (node.kind === 'peer' && node.peerState === 'LIVE') {
      const geo = new THREE.SphereGeometry(0.42, 10, 8);
      const mat = new THREE.MeshBasicMaterial({
        color: style.color, transparent: true, opacity: 0.95, toneMapped: false,
      });
      disposables.push(geo, mat);
      for (let i = 0; i < 3; i += 1) {
        const dot = new THREE.Mesh(geo, mat);
        dot.renderOrder = 2;
        group.add(dot);
        // `phase` staggers the three dots so the link reads as a stream rather
        // than one dot looping.
        flows.push({ dot, from: target.clone(), to: origin.clone(), phase: i / 3 });
      }
    }
  }

  return {
    group,
    flows,
    dispose() { for (const d of disposables) d.dispose?.(); },
  };
}

/**
 * Advance the flow markers (feature 101, US4).
 *
 * FR-020: with reduced motion preferred the dots are PARKED at fixed points along
 * the link instead of hidden. A viewer who cannot see motion still sees that this
 * link is marked and the stale ones are not, so the live/not-live distinction
 * survives — which is what makes flow a redundant channel rather than the only
 * one carrying liveness.
 *
 * @param {Array<object>} flows from buildLinks().flows
 * @param {number} elapsed seconds
 * @param {boolean} reducedMotion
 */
export function animateFlows(flows, elapsed, reducedMotion) {
  for (const f of flows || []) {
    const t = reducedMotion ? (0.2 + f.phase * 0.3) : ((elapsed * 0.35 + f.phase) % 1);
    f.dot.position.lerpVectors(f.from, f.to, t);
  }
}

function makeLine(points, style, disposables) {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = style.dash
    ? new THREE.LineDashedMaterial({
        color: style.color, transparent: true, opacity: style.opacity,
        dashSize: style.dash, gapSize: style.dash * 0.8,
      })
    : new THREE.LineBasicMaterial({
        color: style.color, transparent: true, opacity: style.opacity,
      });
  disposables.push(geometry, material);
  const line = new THREE.Line(geometry, material);
  if (style.dash) line.computeLineDistances();
  line.renderOrder = -1;
  return line;
}

/** Direction marker for the asymmetric push channel (FR-011). */
function makeArrow(origin, target, style, disposables) {
  const dir = target.clone().sub(origin).normalize();
  const at = target.clone().sub(dir.clone().multiplyScalar(4));
  const geometry = new THREE.ConeGeometry(0.9, 2.4, 8);
  const material = new THREE.MeshBasicMaterial({
    color: style.color, transparent: true, opacity: style.opacity,
  });
  disposables.push(geometry, material);
  const cone = new THREE.Mesh(geometry, material);
  cone.position.copy(at);
  cone.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir);
  return cone;
}
