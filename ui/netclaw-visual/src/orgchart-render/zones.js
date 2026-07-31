import * as THREE from 'three';

import { removeLabelElements } from './css2d.js';

const PALETTES = {
  modern: {
    external: { fill: 0x0a2740, opacity: 0.28, border: 0x4a6fa5 },
    internal: { fill: 0x0a241a, opacity: 0.24, border: 0x3f6b52 },
  },
  retro: {
    external: { fill: 0xc0c0c0, opacity: 1, border: 0x808080 },
    internal: { fill: 0xffffff, opacity: 1, border: 0x000000 },
  },
};

function zoneBounds(bands, nodes) {
  const boundaryY = bands.find((band) => band.isBoundary)?.y ?? 18;
  const positions = (nodes || []).map((node) => node.position).filter(Boolean);
  const minX = positions.length ? Math.min(...positions.map((p) => p.x)) : 0;
  const maxX = positions.length ? Math.max(...positions.map((p) => p.x)) : 0;
  const external = (nodes || []).filter((node) => node.kind === 'peer');
  const internal = (nodes || []).filter((node) => node.kind !== 'peer');
  return {
    left: Math.min(-110, minX - 18),
    right: Math.max(110, maxX + 18),
    boundaryY,
    externalTop: Math.max(58, ...external.map((node) => node.position.y + 14)),
    internalBottom: Math.min(-70, ...internal.map((node) => node.position.y - 18)),
  };
}

function makeZone(id, left, right, top, bottom, makeLabel, disposables) {
  const group = new THREE.Group();
  group.name = `trust-zone-${id}`;
  const width = right - left;
  const height = top - bottom;
  const fill = new THREE.MeshBasicMaterial({ transparent: true, depthWrite: false, depthTest: false });
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(width, height), fill);
  plane.position.set((left + right) / 2, (top + bottom) / 2, -8);
  plane.renderOrder = -20;
  group.add(plane);
  const outline = new THREE.LineBasicMaterial({ transparent: true, depthWrite: false, depthTest: false });
  const points = [[left, top], [right, top], [right, bottom], [left, bottom]].map(([x, y]) => new THREE.Vector3(x, y, -7.9));
  const border = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), outline);
  border.renderOrder = -19;
  group.add(border);
  const label = makeLabel(id === 'external' ? 'EXTERNAL TRUST ZONE' : 'INTERNAL DELEGATION ZONE');
  label.element.classList.add('band-label', `band-label-${id}`);
  label.position.set(left + 5, top - 4, -7);
  group.add(label);
  disposables.push(plane.geometry, fill, border.geometry, outline);
  return { group, fill, outline };
}

export function buildTrustZones(bands, nodes, makeLabel, initialTheme = 'modern') {
  const disposables = [];
  const group = new THREE.Group();
  group.name = 'trust-zones';
  const bounds = zoneBounds(bands || [], nodes || []);
  const external = makeZone(
    'external', bounds.left, bounds.right, bounds.externalTop, bounds.boundaryY + 1.5,
    makeLabel, disposables,
  );
  const internal = makeZone(
    'internal', bounds.left, bounds.right, bounds.boundaryY - 1.5, bounds.internalBottom,
    makeLabel, disposables,
  );
  group.add(external.group, internal.group);

  const setTheme = (theme) => {
    const palette = PALETTES[theme === 'retro' ? 'retro' : 'modern'];
    for (const [id, zone] of Object.entries({ external, internal })) {
      zone.fill.color.setHex(palette[id].fill);
      zone.fill.opacity = palette[id].opacity;
      zone.outline.color.setHex(palette[id].border);
      zone.outline.opacity = theme === 'retro' ? 1 : 0.42;
    }
  };
  setTheme(initialTheme);

  return {
    group,
    setTheme,
    dispose() {
      disposables.forEach((item) => item.dispose?.());
      removeLabelElements(group);
    },
  };
}
