/**
 * Keyboard and screen-reader access (FR-032 .. FR-032c).
 *
 * A WebGL canvas exposes no focusable elements — without this the chart is
 * pointer-only, which excludes keyboard and assistive-technology users
 * entirely. The standard remedy is a DOM overlay of focusable, labelled
 * elements positioned over the canvas; that is what this builds.
 *
 * The overlay is the accessibility tree, not decoration: each item carries the
 * node's accessible name AND its health state as TEXT (FR-032b), because
 * FR-009a's encoding is colour, form and motion — none of which a screen
 * reader can convey.
 */

import { TREATMENTS } from './nodes.js';

const BAND_ORDER = ['external', 'border', 'edgeLane', 'internal'];

/**
 * Build (or rebuild) the focusable overlay.
 *
 * @param {HTMLElement} container element covering the canvas
 * @param {Array<object>} nodes layout nodes
 * @param {{onSelect:Function, onToggle:Function}} handlers
 * @returns {{destroy: Function, sync: Function}}
 */
export function buildA11yOverlay(container, nodes, handlers) {
  container.querySelector('#orgchart-a11y')?.remove();

  const root = document.createElement('div');
  root.id = 'orgchart-a11y';
  root.setAttribute('role', 'tree');
  root.setAttribute('aria-label', 'NetClaw trust org chart');

  // Grouped by band so Tab moves between regions and arrows move within one —
  // the structure a chart implies, made real for non-pointer users.
  const groups = new Map(BAND_ORDER.map((b) => [b, []]));
  for (const node of nodes || []) {
    if (!groups.has(node.band)) groups.set(node.band, []);
    groups.get(node.band).push(node);
  }

  const items = [];
  for (const [band, bandNodes] of groups) {
    if (!bandNodes.length) continue;

    const group = document.createElement('div');
    group.setAttribute('role', 'group');
    group.setAttribute('aria-label', bandLabel(band));

    bandNodes.forEach((node, i) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'a11y-node';
      item.setAttribute('role', 'treeitem');
      item.dataset.nodeId = node.id;
      item.dataset.band = band;
      // Roving tabindex: one stop per band, arrows move within it.
      item.tabIndex = i === 0 ? 0 : -1;
      item.textContent = describe(node);

      if (node.kind === 'member' || node.kind === 'edge') {
        item.setAttribute('aria-expanded', String(!!node.expanded));
      }

      item.addEventListener('click', () => handlers.onSelect?.(node));
      item.addEventListener('keydown', (e) => onKeyDown(e, node, items, handlers));
      group.appendChild(item);
      items.push({ node, item });
    });

    root.appendChild(group);
  }

  container.appendChild(root);

  return {
    destroy() { root.remove(); },
    /** Re-announce state after a poll changed health (FR-034a repaints). */
    sync(updated) {
      for (const { node, item } of items) {
        const fresh = updated?.find?.((n) => n.id === node.id) || node;
        item.textContent = describe(fresh);
        if (fresh.kind === 'member' || fresh.kind === 'edge') {
          item.setAttribute('aria-expanded', String(!!fresh.expanded));
        }
      }
    },
  };
}

function bandLabel(band) {
  return {
    external: 'External peers, outside the trust boundary',
    border: 'This Border',
    edgeLane: 'Mobile edge devices',
    internal: 'Internal member claws',
  }[band] || band;
}

/**
 * The accessible name. State is spelled out because colour, form and motion
 * cannot be perceived here (FR-032b).
 */
function describe(node) {
  const parts = [node.label];

  if (node.kind === 'peer') {
    parts.push(node.severed ? 'severed' : `peer, channel ${node.channelState || 'unknown'}`);
  } else if (node.kind === 'border') {
    parts.push('this Border');
  } else {
    const t = TREATMENTS[node.health];
    parts.push(t ? t.label : String(node.health || 'unknown').toLowerCase());
    if (node.category) parts.push(`in ${node.category}`);
    if (node.toolCount) parts.push(`${node.toolCount} tool${node.toolCount === 1 ? '' : 's'}`);
  }
  return parts.join(' — ');
}

function onKeyDown(event, node, items, handlers) {
  const siblings = items.filter((i) => i.item.dataset.band === event.currentTarget.dataset.band);
  const index = siblings.findIndex((i) => i.item === event.currentTarget);

  const move = (next) => {
    event.preventDefault();
    const target = siblings[(next + siblings.length) % siblings.length];
    for (const s of siblings) s.item.tabIndex = -1;
    target.item.tabIndex = 0;
    target.item.focus();
  };

  switch (event.key) {
    case 'ArrowRight': case 'ArrowDown': return move(index + 1);
    case 'ArrowLeft': case 'ArrowUp': return move(index - 1);
    case 'Home': return move(0);
    case 'End': return move(siblings.length - 1);
    case 'Enter': case ' ':
      event.preventDefault();
      return handlers.onSelect?.(node);
    // A separate, explicit expand route — the pointer path folds expand into
    // click, but a keyboard user needs to inspect without toggling (FR-032a).
    case 'e': case 'E': {
      event.preventDefault();
      const nowExpanded = handlers.onToggle?.(node);
      // aria-expanded MUST track the real state. Without this a screen reader
      // announces "collapsed" over an expanded node — the state is conveyed
      // visually and nowhere else, which is precisely what FR-032b forbids.
      node.expanded = !!nowExpanded;
      event.currentTarget.setAttribute('aria-expanded', String(node.expanded));
      return nowExpanded;
    }
    default:
  }
  return undefined;
}

/**
 * Whether motion should be suppressed (FR-032c).
 *
 * Motion is a redundant channel by design (R8) — form and colour temperature
 * already separate all four states — so suppressing it cannot collapse the
 * encoding, and SC-007's greyscale test covers the same property.
 */
export function reducedMotion() {
  return typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true;
}
