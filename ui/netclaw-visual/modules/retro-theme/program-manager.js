/**
 * Program Manager — the RETRO renderer for the trust map.
 *
 * WHY THIS IS DOM AND NOT WEBGL
 *   Two attempts were made to reach a Windows 3.11 look by restyling the 3D
 *   scene: light clear colour, flat materials, no post-processing. Both failed
 *   for the same reason — lit spheres, rings and icosahedrons under spotlights
 *   do not read as desktop icons no matter what colour they are. Win3.11 is
 *   1px bevels, dithered title bars and icon grids: that is a DOM problem.
 *   So retro hides the canvas and draws its own thing from the SAME layout data.
 *
 * WHAT IT RENDERS
 *   - the teal desktop
 *   - one group window per department (draggable by its title bar)
 *   - claws as icons with labels, selectable, double-click to open detail
 *   - an "External Connections" window for eN2N peers
 *   - a "Mobile Edges" window when edge nodes exist
 *
 * DATA
 *   Reads state.orgLayout (nodes + categories) — the same computed layout the
 *   WebGL renderer uses. It never computes positions or classifies health.
 */

const WINDOW_KEY = 'netclaw.retro.progman.windows';

const HEALTH_LABEL = {
  HOT: 'running now',
  WARM: 'idle',
  COLD: 'not started',
  FAULT: 'unreachable',
};

function readWindows() {
  try {
    const raw = localStorage.getItem(WINDOW_KEY);
    const parsed = raw ? JSON.parse(raw) : null;
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeWindows(map) {
  try { localStorage.setItem(WINDOW_KEY, JSON.stringify(map)); } catch { /* non-fatal */ }
}

export function clearWindowLayout() {
  try { localStorage.removeItem(WINDOW_KEY); } catch { /* non-fatal */ }
}

/** 16-colour claw glyph. Shape/colour still separate the four health states. */
function iconFor(node) {
  const health = node.health || 'COLD';
  const glyph = document.createElement('span');
  glyph.className = `pm-glyph pm-glyph-${String(health).toLowerCase()} pm-glyph-${node.kind}`;
  glyph.setAttribute('aria-hidden', 'true');
  return glyph;
}

function makeIcon(node, onSelect) {
  const icon = document.createElement('button');
  icon.type = 'button';
  icon.className = 'pm-icon';
  icon.dataset.nodeId = node.id;
  icon.title = `${node.label} — ${HEALTH_LABEL[node.health] || 'unknown'}`
    + (node.toolCount ? ` · ${node.toolCount} tools` : '');

  const caption = document.createElement('span');
  caption.className = 'pm-icon-label';
  caption.textContent = node.label;

  icon.append(iconFor(node), caption);
  icon.addEventListener('click', () => {
    for (const other of document.querySelectorAll('.pm-icon.selected')) {
      other.classList.remove('selected');
    }
    icon.classList.add('selected');
    onSelect?.(node);
  });
  icon.addEventListener('dblclick', () => onSelect?.(node, true));
  return icon;
}

function makeWindow({ id, title, nodes, onSelect, saved, index }) {
  const win = document.createElement('section');
  win.className = 'pm-window';
  win.dataset.windowId = id;

  const bar = document.createElement('div');
  bar.className = 'pm-titlebar';
  const heading = document.createElement('span');
  heading.className = 'pm-title';
  heading.textContent = title;
  const counts = document.createElement('span');
  counts.className = 'pm-title-meta';
  const active = nodes.filter((n) => n.health === 'HOT' || n.health === 'WARM').length;
  const attention = nodes.filter((n) => n.health === 'FAULT').length;
  counts.textContent = `${nodes.length} · ${active} active${attention ? ` · ${attention} !` : ''}`;
  bar.append(heading, counts);

  const client = document.createElement('div');
  client.className = 'pm-client';
  if (!nodes.length) {
    const empty = document.createElement('p');
    empty.className = 'pm-empty';
    empty.textContent = 'No claws in this group yet.';
    client.appendChild(empty);
  } else {
    for (const node of nodes) client.appendChild(makeIcon(node, onSelect));
  }

  win.append(bar, client);

  // Cascade like Program Manager did, unless the operator has moved it.
  const left = saved?.left ?? 24 + (index % 3) * 268;
  const top = saved?.top ?? 20 + Math.floor(index / 3) * 176;
  win.style.left = `${left}px`;
  win.style.top = `${top}px`;
  return { win, bar };
}

function dragWindow(win, bar, desktop, onCommit) {
  bar.addEventListener('pointerdown', (event) => {
    if (event.button !== 0) return;
    const rect = win.getBoundingClientRect();
    const host = desktop.getBoundingClientRect();
    const offsetX = event.clientX - rect.left;
    const offsetY = event.clientY - rect.top;
    bar.setPointerCapture(event.pointerId);
    win.classList.add('pm-dragging');
    // Clicking a title bar raises the window, exactly as it should.
    for (const other of desktop.querySelectorAll('.pm-window')) other.style.zIndex = '1';
    win.style.zIndex = '2';

    const move = (moveEvent) => {
      const left = Math.max(0, Math.min(host.width - 60, moveEvent.clientX - host.left - offsetX));
      const top = Math.max(0, Math.min(host.height - 24, moveEvent.clientY - host.top - offsetY));
      win.style.left = `${left}px`;
      win.style.top = `${top}px`;
    };
    const end = () => {
      bar.removeEventListener('pointermove', move);
      bar.removeEventListener('pointerup', end);
      bar.removeEventListener('pointercancel', end);
      win.classList.remove('pm-dragging');
      onCommit(win.dataset.windowId, {
        left: parseFloat(win.style.left) || 0,
        top: parseFloat(win.style.top) || 0,
      });
    };
    bar.addEventListener('pointermove', move);
    bar.addEventListener('pointerup', end);
    bar.addEventListener('pointercancel', end);
    event.preventDefault();
  });
}

/**
 * Build (or rebuild) the desktop from the current layout.
 *
 * @param {{layout:object, onSelect:Function}} ctx
 */
export function renderProgramManager({ layout, onSelect }) {
  const app = document.getElementById('app');
  if (!app || !layout) return null;

  destroyProgramManager();

  const desktop = document.createElement('div');
  desktop.id = 'pm-desktop';
  desktop.className = 'pm-desktop';

  const nodes = layout.nodes || [];
  const saved = readWindows();
  const commit = (id, geometry) => {
    const map = readWindows();
    map[id] = geometry;
    writeWindows(map);
  };

  const groups = [];
  for (const category of layout.categories || []) {
    groups.push({
      id: `dept:${category.name}`,
      title: category.name,
      nodes: nodes.filter((node) => node.kind === 'member' && node.category === category.name),
    });
  }
  const peers = nodes.filter((node) => node.kind === 'peer');
  if (peers.length) groups.push({ id: 'external', title: 'External Connections', nodes: peers });
  const edges = nodes.filter((node) => node.kind === 'edge');
  if (edges.length) groups.push({ id: 'edges', title: 'Mobile Edges', nodes: edges });
  const border = nodes.find((node) => node.kind === 'border');
  if (border) groups.unshift({ id: 'border', title: 'This NetClaw (Border)', nodes: [border] });

  groups.forEach((group, index) => {
    const { win, bar } = makeWindow({ ...group, onSelect, saved: saved[group.id], index });
    dragWindow(win, bar, desktop, commit);
    desktop.appendChild(win);
  });

  app.appendChild(desktop);
  return desktop;
}

export function destroyProgramManager() {
  document.getElementById('pm-desktop')?.remove();
}

export function isProgramManagerMounted() {
  return !!document.getElementById('pm-desktop');
}
