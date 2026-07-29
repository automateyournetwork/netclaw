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
export function buildLinks(layoutNodes, categories) {
  const group = new THREE.Group();
  group.name = 'orgchart-links';
  const disposables = [];

  const nodes = layoutNodes || [];
  const border = nodes.find((n) => n.kind === 'border');
  if (!border) return { group, dispose() {} };

  const origin = new THREE.Vector3(border.position.x, border.position.y, border.position.z);

  for (const node of nodes) {
    if (node === border) continue;

    const styleKey = styleForNode(node);
    const style = LINK_STYLES[styleKey];
    const target = new THREE.Vector3(node.position.x, node.position.y, node.position.z);

    // Members route via their category header so the chart reads as a chart —
    // an elbow through the column, not 100 straight lines to one point.
    let points;
    if (node.kind === 'member') {
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
  }

  return {
    group,
    dispose() { for (const d of disposables) d.dispose?.(); },
  };
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
