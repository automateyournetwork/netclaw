/**
 * Bands, the trust boundary, the edge lane, and empty states
 * (FR-001, FR-002, FR-007, FR-033).
 *
 * The trust boundary is an explicitly DRAWN object, not implied whitespace
 * (FR-002). It is the most important line in the diagram — it is the thing
 * that makes "external" mean something — and distance alone does not say it.
 *
 * Bands render even when empty (FR-033). A NetClaw with no risk, no members
 * and no peers is the normal first state for a new operator, and after FR-030
 * removed the integration and device populations there is nothing else left to
 * draw. An empty chart must read as "nothing here yet", never as a failure.
 */

import * as THREE from 'three';

const BAND_WIDTH = 220;

const STYLE = {
  external: { color: 0x4a6fa5, dash: 2.2, gap: 1.6 },
  internal: { color: 0x3f6b52, dash: 2.2, gap: 1.6 },
  edgeLane: { color: 0xe65733, dash: 1.4, gap: 1.2 },
  boundary: { color: 0xffc857, dash: 0, gap: 0 },
};

/**
 * @param {Array<object>} bands from computeLayout().bands
 * @param {(text:string)=>object} makeLabel host CSS2D label factory
 * @returns {{group: THREE.Group, dispose: Function}}
 */
export function buildBands(bands, makeLabel) {
  const group = new THREE.Group();
  group.name = 'orgchart-bands';
  const disposables = [];

  for (const band of bands || []) {
    if (band.id === 'edgeLane') {
      group.add(buildEdgeLane(band, makeLabel, disposables));
      continue;
    }
    if (band.isBoundary) {
      group.add(buildBoundary(band, makeLabel, disposables));
      continue;
    }
    group.add(buildBandRule(band, makeLabel, disposables));
  }

  return {
    group,
    dispose() { for (const d of disposables) d.dispose?.(); },
  };
}

/** The trust boundary: a solid double rule, the strongest line in the chart. */
function buildBoundary(band, makeLabel, disposables) {
  const g = new THREE.Group();
  g.name = 'trust-boundary';

  for (const dy of [-0.9, 0.9]) {
    const geometry = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-BAND_WIDTH / 2, band.y + dy, -1),
      new THREE.Vector3(BAND_WIDTH / 2, band.y + dy, -1),
    ]);
    const material = new THREE.LineBasicMaterial({
      color: STYLE.boundary.color, transparent: true, opacity: 0.75,
    });
    disposables.push(geometry, material);
    g.add(new THREE.Line(geometry, material));
  }

  const label = makeLabel('TRUST BOUNDARY');
  label.element.classList.add('band-label', 'band-label-boundary');
  label.position.set(-BAND_WIDTH / 2 + 6, band.y + 3.4, 0);
  g.add(label);
  return g;
}

/** A dashed rule delimiting a band, with its name and (if empty) its CTA. */
function buildBandRule(band, makeLabel, disposables) {
  const g = new THREE.Group();
  g.name = `band-${band.id}`;
  const style = STYLE[band.id] || STYLE.external;

  const geometry = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(-BAND_WIDTH / 2, band.y, -2),
    new THREE.Vector3(BAND_WIDTH / 2, band.y, -2),
  ]);
  const material = new THREE.LineDashedMaterial({
    color: style.color, dashSize: style.dash, gapSize: style.gap,
    transparent: true, opacity: 0.4,
  });
  const line = new THREE.Line(geometry, material);
  line.computeLineDistances();
  disposables.push(geometry, material);
  g.add(line);

  const label = makeLabel(band.label);
  label.element.classList.add('band-label');
  label.position.set(-BAND_WIDTH / 2 + 6, band.y + 2.6, 0);
  g.add(label);

  if (band.empty && band.emptyCta) g.add(emptyState(band, band.emptyCta, makeLabel));
  return g;
}

/** The edge lane: bracketed, offset, clearly not part of the member chart. */
function buildEdgeLane(band, makeLabel, disposables) {
  const g = new THREE.Group();
  g.name = 'edge-lane';
  const x = band.x ?? 46;
  const style = STYLE.edgeLane;

  const material = new THREE.LineDashedMaterial({
    color: style.color, dashSize: style.dash, gapSize: style.gap,
    transparent: true, opacity: 0.5,
  });
  disposables.push(material);

  // An open bracket rather than a closed box — the lane belongs to the Border,
  // it is not a separate enclosure.
  const pts = [
    new THREE.Vector3(x - 8, band.y + 10, -2),
    new THREE.Vector3(x + 26, band.y + 10, -2),
    new THREE.Vector3(x + 26, band.y - 26, -2),
    new THREE.Vector3(x - 8, band.y - 26, -2),
  ];
  const geometry = new THREE.BufferGeometry().setFromPoints(pts);
  disposables.push(geometry);
  const line = new THREE.Line(geometry, material);
  line.computeLineDistances();
  g.add(line);

  const label = makeLabel(band.label);
  label.element.classList.add('band-label', 'band-label-edge');
  label.position.set(x - 8, band.y + 12.5, 0);
  g.add(label);

  if (band.empty && band.emptyCta) {
    const cta = makeLabel(band.emptyCta);
    cta.element.classList.add('band-empty');
    cta.position.set(x + 9, band.y - 8, 0);
    g.add(cta);
  }
  return g;
}

/**
 * Empty-band copy (FR-033a). Names what belongs here and how to get it —
 * an empty band should teach a first-time operator the trust model, not
 * look like a broken load.
 */
function emptyState(band, text, makeLabel) {
  const cta = makeLabel(text);
  cta.element.classList.add('band-empty');
  const dy = band.id === 'external' ? 8 : -10;
  cta.position.set(0, band.y + dy, 0);
  return cta;
}
