import * as THREE from 'three';
import { TREATMENTS } from '../orgchart-render/nodes.js';

const STATUS_STYLE = {
  up: { color: TREATMENTS.HOT.color, emissive: TREATMENTS.HOT.emissive, intensity: 1.2, scale: 1.0 },
  down: { color: TREATMENTS.FAULT.color, emissive: TREATMENTS.FAULT.emissive, intensity: 1.5, scale: 1.08 },
  unreachable: { color: TREATMENTS.COLD.color, emissive: TREATMENTS.COLD.emissive, intensity: 0.75, scale: 0.88 },
};

function hashString(input) {
  let h = 2166136261;
  for (let i = 0; i < input.length; i += 1) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

export function captureTwinViewState(camera, controls) {
  if (!camera || !controls) return null;
  const camPos = camera.position;
  const target = controls.target;
  if (!camPos || !target || !Number.isFinite(camera.zoom)) return null;
  return {
    camera: { x: camPos.x, y: camPos.y, z: camPos.z, zoom: camera.zoom },
    target: { x: target.x, y: target.y, z: target.z },
  };
}

function setVec3(vec, xyz) {
  if (!vec || !xyz) return;
  if (typeof vec.set === 'function') {
    vec.set(xyz.x, xyz.y, xyz.z);
    return;
  }
  vec.x = xyz.x;
  vec.y = xyz.y;
  vec.z = xyz.z;
}

export function restoreTwinViewState(camera, controls, snapshot) {
  if (!snapshot || !camera || !controls) return false;
  const pos = camera.position;
  const target = controls.target;
  if (!pos || !target) return false;
  const cam = snapshot.camera;
  const tgt = snapshot.target;
  const changed = pos.x !== cam.x
    || pos.y !== cam.y
    || pos.z !== cam.z
    || camera.zoom !== cam.zoom
    || target.x !== tgt.x
    || target.y !== tgt.y
    || target.z !== tgt.z;
  if (!changed) return false;
  setVec3(pos, cam);
  camera.zoom = cam.zoom;
  camera.updateProjectionMatrix?.();
  setVec3(target, tgt);
  controls.update?.();
  return true;
}

export function createLiveTwinLayer({
  scene,
  makeLabel,
  camera = null,
  controls = null,
  snapshotUrl = '/api/twin/snapshot',
  statusUrl = '/api/twin/status',
}) {
  const root = new THREE.Group();
  root.name = 'astra-twin-live';
  const linkGroup = new THREE.Group();
  linkGroup.name = 'astra-twin-links';
  const nodeGroup = new THREE.Group();
  nodeGroup.name = 'astra-twin-nodes';
  root.add(linkGroup);
  root.add(nodeGroup);
  scene.add(root);

  const nodeGeo = new THREE.SphereGeometry(1.45, 18, 14);
  const nodeMaterials = {
    up: new THREE.MeshStandardMaterial({ color: STATUS_STYLE.up.color, emissive: STATUS_STYLE.up.emissive, emissiveIntensity: STATUS_STYLE.up.intensity, roughness: 0.32, metalness: 0.48 }),
    down: new THREE.MeshStandardMaterial({ color: STATUS_STYLE.down.color, emissive: STATUS_STYLE.down.emissive, emissiveIntensity: STATUS_STYLE.down.intensity, roughness: 0.4, metalness: 0.42 }),
    unreachable: new THREE.MeshStandardMaterial({ color: STATUS_STYLE.unreachable.color, emissive: STATUS_STYLE.unreachable.emissive, emissiveIntensity: STATUS_STYLE.unreachable.intensity, roughness: 0.7, metalness: 0.08 }),
  };

  let lastSeq = 0;
  let socket = null;
  let reconnectTimer = null;
  let statusPollTimer = null;
  let freshnessElement = null;
  let changeElement = null;
  let changeClearTimer = null;
  let disposed = false;
  let lastError = null;
  const nodeSlots = new Map();
  const nodes = new Map();
  const links = new Map();
  const flashes = new Map();

  function withPreservedView(updateFn) {
    const before = captureTwinViewState(camera, controls);
    updateFn();
    restoreTwinViewState(camera, controls, before);
  }

  function setDebug(error = lastError) {
    lastError = error;
    window.__astraTwinDebug = {
      nodeCount: nodes.size,
      linkCount: links.size,
      lastError,
    };
  }

  function ensureFreshnessElement() {
    if (freshnessElement) return freshnessElement;
    freshnessElement = document.getElementById('astra-twin-freshness');
    if (freshnessElement) return freshnessElement;
    freshnessElement = document.createElement('div');
    freshnessElement.id = 'astra-twin-freshness';
    freshnessElement.style.cssText = 'position:fixed;top:10px;right:10px;z-index:9999;'
      + 'padding:6px 10px;border-radius:8px;border:1px solid #334155;'
      + 'background:rgba(15,23,42,.9);color:#e2e8f0;font:12px/1.4 ui-monospace,monospace;'
      + 'letter-spacing:.02em;pointer-events:none;';
    document.body.appendChild(freshnessElement);
    return freshnessElement;
  }

  function ensureChangeElement() {
    if (changeElement) return changeElement;
    changeElement = document.getElementById('astra-twin-last-change');
    if (changeElement) return changeElement;
    changeElement = document.createElement('div');
    changeElement.id = 'astra-twin-last-change';
    changeElement.style.cssText = 'position:fixed;top:46px;right:10px;z-index:9999;'
      + 'padding:6px 10px;border-radius:8px;border:1px solid #164e63;'
      + 'background:rgba(8,47,73,.9);color:#cffafe;font:12px/1.4 ui-monospace,monospace;'
      + 'letter-spacing:.02em;pointer-events:none;transition:opacity .25s ease;'
      + 'opacity:0;';
    document.body.appendChild(changeElement);
    return changeElement;
  }

  function describeDeltaChange(delta) {
    if (!delta || typeof delta !== 'object') return null;
    if (delta.kind === 'node_added') return `Node added: ${delta.node?.label || delta.node?.id || 'unknown'}`;
    if (delta.kind === 'node_removed') return `Node removed: ${delta.node?.label || delta.node?.id || 'unknown'}`;
    if (delta.kind === 'node_status_changed') return `Node status: ${delta.node?.label || delta.node?.id || 'unknown'} -> ${delta.node?.status || 'unknown'}`;
    if (delta.kind === 'link_added') return `Link added: ${delta.link?.id || 'unknown'}`;
    if (delta.kind === 'link_removed') return `Link removed: ${delta.link?.id || 'unknown'}`;
    if (delta.kind === 'link_state_changed') return `Link state: ${delta.link?.id || 'unknown'} -> ${delta.link?.state || 'unknown'}`;
    return null;
  }

  function showChange(delta) {
    const text = describeDeltaChange(delta);
    if (!text) return;
    const el = ensureChangeElement();
    el.textContent = `Twin change | ${text}`;
    el.style.opacity = '1';
    if (changeClearTimer) clearTimeout(changeClearTimer);
    changeClearTimer = setTimeout(() => {
      changeClearTimer = null;
      el.style.opacity = '0';
    }, 3000);
  }

  function formatAge(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return 'just now';
    if (seconds < 60) return `${Math.round(seconds)}s ago`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
    return `${Math.round(seconds / 3600)}h ago`;
  }

  function renderFreshnessStatus({ stale, text }) {
    const el = ensureFreshnessElement();
    el.textContent = `Twin data ${stale ? 'STALE' : 'LIVE'} | ${text}`;
    if (stale) {
      el.style.borderColor = '#b45309';
      el.style.background = 'rgba(120,53,15,.92)';
      el.style.color = '#fde68a';
      return;
    }
    el.style.borderColor = '#14532d';
    el.style.background = 'rgba(20,83,45,.86)';
    el.style.color = '#dcfce7';
  }

  function staleThresholdSeconds(status) {
    const pollInterval = Number(status?.poll_interval_seconds);
    if (!Number.isFinite(pollInterval) || pollInterval <= 0) return 45;
    return Math.max(45, (pollInterval * 3) + 5);
  }

  function computeFreshness(status) {
    const threshold = staleThresholdSeconds(status);
    const iso = status?.last_successful_poll;
    if (!iso) {
      return {
        stale: true,
        text: `waiting for first successful poll (stale threshold ${threshold}s)`,
      };
    }
    const stampMs = Date.parse(iso);
    if (!Number.isFinite(stampMs)) {
      return {
        stale: true,
        text: 'collector reported invalid poll timestamp',
      };
    }
    const ageSeconds = Math.max(0, (Date.now() - stampMs) / 1000);
    const stale = ageSeconds > threshold;
    return {
      stale,
      text: `${formatAge(ageSeconds)} (threshold ${threshold}s)`,
    };
  }

  async function pollStatus() {
    try {
      const res = await fetch(statusUrl);
      if (!res.ok) throw new Error(`status HTTP ${res.status}`);
      const status = await res.json();
      const freshness = computeFreshness(status);
      if (Number(status?.consecutive_failures) > 0) {
        freshness.stale = true;
        freshness.text += `, ${status.consecutive_failures} failed poll(s)`;
      }
      renderFreshnessStatus(freshness);
    } catch (err) {
      renderFreshnessStatus({ stale: true, text: `status unavailable (${err.message})` });
    }
  }

  function startStatusPolling() {
    if (statusPollTimer) return;
    pollStatus();
    statusPollTimer = setInterval(() => {
      pollStatus();
    }, 10000);
  }

  function nodePosition(id) {
    if (nodeSlots.has(id)) return nodeSlots.get(id).clone();
    const n = nodes.size;
    const ring = Math.floor(n / 16) + 1;
    const idx = n % 16;
    const theta = (Math.PI * 2 * idx) / 16 + ((hashString(id) % 360) * Math.PI) / 1800;
    const radius = 22 + ring * 10;
    const pos = new THREE.Vector3(Math.cos(theta) * radius, -52 + ring * 4, Math.sin(theta) * radius);
    nodeSlots.set(id, pos);
    return pos.clone();
  }

  function styleForStatus(status) {
    return STATUS_STYLE[status] || STATUS_STYLE.unreachable;
  }

  function linkColorForState(state) {
    return state === 'up' ? 0x5ee6a6 : 0xff8b8b;
  }

  function createLinkEntry(link) {
    const from = nodes.get(link.source_node_id);
    const to = nodes.get(link.target_node_id);
    if (!from || !to) return null;
    const geometry = new THREE.BufferGeometry().setFromPoints([from.mesh.position.clone(), to.mesh.position.clone()]);
    const material = new THREE.LineBasicMaterial({
      color: linkColorForState(link.state),
      transparent: true,
      opacity: 0.64,
    });
    const line = new THREE.Line(geometry, material);
    line.renderOrder = -1;
    linkGroup.add(line);
    return { data: { ...link }, line, geometry, material };
  }

  function upsertNode(node) {
    const existing = nodes.get(node.id);
    const status = String(node.status || 'unreachable');
    const style = styleForStatus(status);
    if (!existing) {
      const mesh = new THREE.Mesh(nodeGeo, nodeMaterials[status] || nodeMaterials.unreachable);
      mesh.position.copy(nodePosition(node.id));
      mesh.scale.setScalar(style.scale);
      mesh.userData = { twinNodeId: node.id };
      const label = makeLabel(node.label || node.id);
      label.position.set(mesh.position.x, mesh.position.y - 4.2, mesh.position.z);
      nodeGroup.add(mesh);
      nodeGroup.add(label);
      nodes.set(node.id, { data: { ...node }, mesh, label, baseScale: style.scale });
      return;
    }
    existing.data = { ...existing.data, ...node };
    existing.mesh.material = nodeMaterials[status] || nodeMaterials.unreachable;
    existing.mesh.scale.setScalar(style.scale);
    existing.baseScale = style.scale;
    existing.label.element.textContent = node.label || node.id;
  }

  function removeNode(nodeId) {
    const entry = nodes.get(nodeId);
    if (!entry) return;
    nodeGroup.remove(entry.mesh);
    nodeGroup.remove(entry.label);
    nodes.delete(nodeId);
    for (const linkId of [...links.keys()]) {
      const l = links.get(linkId);
      if (!l) continue;
      if (l.data.source_node_id === nodeId || l.data.target_node_id === nodeId) removeLink(linkId);
    }
  }

  function upsertLink(link) {
    const existing = links.get(link.id);
    if (!existing) {
      const created = createLinkEntry(link);
      if (!created) return;
      links.set(link.id, created);
      return;
    }
    existing.data = { ...existing.data, ...link };
    existing.material.color = new THREE.Color(linkColorForState(link.state));
  }

  function removeLink(linkId) {
    const entry = links.get(linkId);
    if (!entry) return;
    linkGroup.remove(entry.line);
    entry.geometry.dispose();
    entry.material.dispose();
    links.delete(linkId);
  }

  function markChanged(id) {
    flashes.set(id, performance.now() + 2600);
  }

  function applyDelta(delta) {
    withPreservedView(() => {
      if (!delta || typeof delta !== 'object') return;
      if (typeof delta.seq === 'number' && delta.seq <= lastSeq) return;
      if (typeof delta.seq === 'number') lastSeq = delta.seq;
      switch (delta.kind) {
        case 'node_added':
          if (delta.node) {
            upsertNode(delta.node);
            markChanged(`node:${delta.node.id}`);
          }
          break;
        case 'node_removed':
          if (delta.node?.id) removeNode(delta.node.id);
          break;
        case 'node_status_changed':
          if (delta.node) {
            upsertNode(delta.node);
            markChanged(`node:${delta.node.id}`);
          }
          break;
        case 'link_added':
          if (delta.link) {
            upsertLink(delta.link);
            markChanged(`link:${delta.link.id}`);
          }
          break;
        case 'link_removed':
          if (delta.link?.id) removeLink(delta.link.id);
          break;
        case 'link_state_changed':
          if (delta.link) {
            upsertLink(delta.link);
            markChanged(`link:${delta.link.id}`);
          }
          break;
        default:
          break;
      }
      showChange(delta);
      setDebug();
    });
  }

  function reconcileSnapshot(snapshot) {
    withPreservedView(() => {
      const payload = snapshot && typeof snapshot === 'object' ? snapshot : {};
      const snapshotNodes = Array.isArray(payload.nodes) ? payload.nodes : [];
      const snapshotLinks = Array.isArray(payload.links) ? payload.links : [];

      const nodeIds = new Set(snapshotNodes.map((n) => n.id));
      const linkIds = new Set(snapshotLinks.map((l) => l.id));

      for (const staleNodeId of [...nodes.keys()]) {
        if (!nodeIds.has(staleNodeId)) removeNode(staleNodeId);
      }
      for (const staleLinkId of [...links.keys()]) {
        if (!linkIds.has(staleLinkId)) removeLink(staleLinkId);
      }

      for (const node of snapshotNodes) upsertNode(node);
      for (const link of snapshotLinks) upsertLink(link);

      if (typeof payload.seq === 'number') lastSeq = payload.seq;
      setDebug();
    });
  }

  async function fetchSnapshot() {
    const res = await fetch(snapshotUrl);
    if (!res.ok) throw new Error(`snapshot HTTP ${res.status}`);
    const snapshot = await res.json();
    reconcileSnapshot(snapshot);
    setDebug(null);
  }

  function scheduleReconnect() {
    if (disposed || reconnectTimer) return;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connectSocket();
    }, 3000);
  }

  function connectSocket() {
    if (disposed || socket) return;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    socket = new WebSocket(`${protocol}://${window.location.host}/ws/twin`);
    socket.addEventListener('message', async (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg?.type === 'twin:resync_required') {
          await fetchSnapshot();
          return;
        }
        if (msg?.type === 'twin:error') {
          setDebug(msg.error || 'twin ws error');
          return;
        }
        applyDelta(msg);
      } catch (err) {
        setDebug(`delta parse failed: ${err.message}`);
      }
    });
    socket.addEventListener('close', () => {
      socket = null;
      scheduleReconnect();
    });
    socket.addEventListener('error', () => {
      setDebug('twin websocket error');
    });
  }

  function tick() {
    const now = performance.now();
    for (const [id, until] of [...flashes.entries()]) {
      if (until < now) {
        flashes.delete(id);
        continue;
      }
      const age = 1 - ((until - now) / 2600);
      const glow = Math.max(0, 1 - age) * 0.65;
      if (id.startsWith('node:')) {
        const nodeId = id.slice(5);
        const entry = nodes.get(nodeId);
        if (entry?.mesh) {
          const pulse = 1 + glow * 0.35;
          entry.mesh.scale.setScalar(entry.baseScale * pulse);
        }
      } else if (id.startsWith('link:')) {
        const linkId = id.slice(5);
        const entry = links.get(linkId);
        if (entry?.material) entry.material.opacity = 0.64 + glow * 0.3;
      }
    }
    for (const [nodeId, entry] of nodes.entries()) {
      if (flashes.has(`node:${nodeId}`)) continue;
      if (entry?.mesh) entry.mesh.scale.setScalar(entry.baseScale);
    }
    for (const [linkId, entry] of links.entries()) {
      if (flashes.has(`link:${linkId}`)) continue;
      if (entry?.material) entry.material.opacity = 0.64;
    }
  }

  async function start() {
    try {
      await fetchSnapshot();
      requestAnimationFrame(() => setDebug(lastError));
    } catch (err) {
      setDebug(`snapshot failed: ${err.message}`);
    }
    connectSocket();
    startStatusPolling();
  }

  function dispose() {
    disposed = true;
    if (reconnectTimer) clearTimeout(reconnectTimer);
    if (statusPollTimer) clearInterval(statusPollTimer);
    statusPollTimer = null;
    if (changeClearTimer) clearTimeout(changeClearTimer);
    changeClearTimer = null;
    if (socket) socket.close();
    for (const linkId of [...links.keys()]) removeLink(linkId);
    for (const nodeId of [...nodes.keys()]) removeNode(nodeId);
    scene.remove(root);
    nodeGeo.dispose();
    Object.values(nodeMaterials).forEach((m) => m.dispose());
    freshnessElement?.remove();
    freshnessElement = null;
    changeElement?.remove();
    changeElement = null;
  }

  return {
    start,
    tick,
    dispose,
  };
}
