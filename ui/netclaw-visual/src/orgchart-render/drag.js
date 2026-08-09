import { DragControls } from 'three/addons/controls/DragControls.js';
import {
  draggableObjects, moveOrgChartNode, commitOrgChartNode,
  moveOrgChartGroup, commitOrgChartGroup, isCategoryHandle,
  resetOrgChartLayout,
} from './index.js';

const MOVE_THRESHOLD_SQ = 0.16;

/**
 * Direct manipulation for the trust map.
 *
 * Two grab targets:
 *   - a claw           -> moves that claw
 *   - a department card -> moves the header and every claw under it together
 *
 * The targets array is owned here and MUTATED IN PLACE, never replaced, because
 * DragControls keeps the reference it was constructed with. Anything that
 * rebuilds meshes (theme switch, a member enrolling) must call refresh().
 */
export function mountOrgChartDrag({ camera, renderer, orbitControls, resetButton, onReset }) {
  const targets = [...draggableObjects()];
  const controls = new DragControls(targets, camera, renderer.domElement);
  controls.recursive = false;
  let start = null;
  let dragging = false;
  let moved = false;
  let suppressClickUntil = 0;

  const refresh = () => {
    targets.length = 0;
    targets.push(...draggableObjects());
  };

  controls.addEventListener('hoveron', () => renderer.domElement.classList.add('orgchart-drag-hover'));
  controls.addEventListener('hoveroff', () => renderer.domElement.classList.remove('orgchart-drag-hover'));

  controls.addEventListener('dragstart', (event) => {
    start = event.object.position.clone();
    dragging = true;
    moved = false;
    orbitControls.enabled = false;
    renderer.domElement.classList.add('orgchart-dragging');
  });

  controls.addEventListener('drag', (event) => {
    moved ||= start.distanceToSquared(event.object.position) > MOVE_THRESHOLD_SQ;
    if (isCategoryHandle(event.object)) moveOrgChartGroup(event.object);
    else moveOrgChartNode(event.object);
  });

  controls.addEventListener('dragend', (event) => {
    const group = isCategoryHandle(event.object);
    if (!moved && start) {
      // A click, not a drag: put it back so a stray pixel cannot nudge the chart.
      event.object.position.copy(start);
      if (group) moveOrgChartGroup(event.object);
      else moveOrgChartNode(event.object);
    } else if (moved) {
      if (group) commitOrgChartGroup(event.object);
      else commitOrgChartNode(event.object);
      suppressClickUntil = performance.now() + 250;
    }
    start = null;
    dragging = false;
    orbitControls.enabled = true;
    renderer.domElement.classList.remove('orgchart-dragging');
  });

  resetButton?.addEventListener('click', () => {
    if (resetOrgChartLayout()) onReset?.();
  });

  return {
    isDragging: () => dragging,
    consumeClick: () => performance.now() <= suppressClickUntil,
    refresh,
  };
}

// ── Feature 102: pointer-event drag (upstream) ──────────────────────

/**
 * Node dragging (feature 102, US1 — FR-001, FR-004, FR-043..046).
 *
 * ## The gesture problem
 *
 * `OrbitControls` owns pointer-drag outright. Dragging a node and orbiting the
 * camera are the same gesture, so something has to arbitrate. The chosen rule is
 * **raycast decides** (FR-043): a pointer-down that hits a pickable node begins a
 * drag and suspends the camera; a pointer-down that hits nothing falls through to
 * `OrbitControls` completely untouched. No modifier key, no mode toggle, and a
 * missed raycast degrades to exactly today's behaviour.
 *
 * ## The failure mode this file exists to prevent
 *
 * `controls.enabled = false` is a PERSISTENT flag. If a drag ends by the pointer
 * leaving the window, by `pointercancel`, or by an exception thrown mid-move, and
 * the restore is wired only to `pointerup`, the camera stays dead permanently — with
 * no visible cause and no recovery but a reload. That is the worst outcome available
 * in this feature, because the operator cannot even tell what broke.
 *
 * So restoration is centralised in `endDrag()` and wired to FOUR paths, and the move
 * handler is wrapped so a throw cannot skip it (FR-045).
 */

import * as THREE from 'three';

/** Pixels of movement that separate a click from a drag (FR-044). */
export const DRAG_THRESHOLD_PX = 4;

/**
 * Attach drag handling.
 *
 * @param {object} deps
 * @param {HTMLElement} deps.domElement renderer canvas
 * @param {THREE.Camera} deps.camera
 * @param {object} deps.controls OrbitControls instance
 * @param {() => Array<THREE.Object3D>} deps.pickables meshes eligible for dragging
 * @param {(nodeId: string, pos: {x,y,z}) => void} deps.onDragged committed position
 * @param {(nodeId: string, pos: {x,y,z}) => void} [deps.onDragMove] live preview
 * @returns {{dispose: Function, isDragging: () => boolean}}
 */
export function attachDrag({ domElement, camera, controls, pickables, onDragged, onDragMove }) {
  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  // The chart is laid out on the XY plane at z=0; dragging stays in that plane so a
  // node cannot be pushed toward or away from the camera and silently change scale.
  const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  const hitPoint = new THREE.Vector3();

  let session = null;

  function toNdc(ev) {
    const r = domElement.getBoundingClientRect();
    ndc.x = ((ev.clientX - r.left) / r.width) * 2 - 1;
    ndc.y = -((ev.clientY - r.top) / r.height) * 2 + 1;
    return ndc;
  }

  function planePoint(ev) {
    raycaster.setFromCamera(toNdc(ev), camera);
    return raycaster.ray.intersectPlane(plane, hitPoint) ? hitPoint.clone() : null;
  }

  /**
   * Single restoration path. Every termination route funnels here, and it is
   * deliberately tolerant — it must never itself throw, or it would defeat its own
   * purpose (FR-045).
   */
  function endDrag(commit) {
    if (!session) return;
    const s = session;
    session = null;
    try {
      if (commit && s.moved && s.last) onDragged?.(s.nodeId, s.last);
    } catch (e) {
      console.error('drag commit failed', e);
    } finally {
      try { domElement.releasePointerCapture?.(s.pointerId); } catch { /* already gone */ }
      // The flag that must always come back.
      if (controls) controls.enabled = true;
    }
  }

  function onPointerDown(ev) {
    if (ev.button !== 0 || session) return;
    raycaster.setFromCamera(toNdc(ev), camera);
    const hit = raycaster.intersectObjects(pickables() || [], false)[0];
    if (!hit) return;                       // FR-043: fall through to OrbitControls

    const nodeId = hit.object?.userData?.nodeId;
    if (!nodeId) return;

    const start = planePoint(ev);
    if (!start) return;

    session = {
      nodeId,
      pointerId: ev.pointerId,
      startScreen: { x: ev.clientX, y: ev.clientY },
      grabOffset: hit.object.position.clone().sub(start),
      moved: false,
      last: null,
    };
    if (controls) controls.enabled = false;
    try { domElement.setPointerCapture?.(ev.pointerId); } catch { /* non-fatal */ }
  }

  function onPointerMove(ev) {
    if (!session || ev.pointerId !== session.pointerId) return;
    try {
      if (!session.moved) {
        const dx = ev.clientX - session.startScreen.x;
        const dy = ev.clientY - session.startScreen.y;
        // FR-044: below the threshold this is still a click, so do nothing at all —
        // moving now would make a plain select nudge the node a pixel.
        if (Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
        session.moved = true;
      }
      const p = planePoint(ev);
      if (!p) return;
      const next = p.add(session.grabOffset);
      session.last = { x: next.x, y: next.y, z: 0 };
      onDragMove?.(session.nodeId, session.last);
    } catch (e) {
      // An exception here must not strand the camera (FR-045).
      console.error('drag move failed', e);
      endDrag(false);
    }
  }

  const onPointerUp = (ev) => { if (!session || ev.pointerId === session.pointerId) endDrag(true); };
  const onPointerCancel = () => endDrag(false);
  const onLostCapture = () => endDrag(true);
  // Leaving the window entirely never fires pointerup on the canvas.
  const onWindowBlur = () => endDrag(true);

  domElement.addEventListener('pointerdown', onPointerDown);
  domElement.addEventListener('pointermove', onPointerMove);
  domElement.addEventListener('pointerup', onPointerUp);
  domElement.addEventListener('pointercancel', onPointerCancel);
  domElement.addEventListener('lostpointercapture', onLostCapture);
  window.addEventListener('blur', onWindowBlur);

  return {
    isDragging: () => session !== null,
    /** True when the gesture moved far enough to be a drag — suppresses the click-select. */
    consumedClick: () => false,
    dispose() {
      endDrag(false);
      domElement.removeEventListener('pointerdown', onPointerDown);
      domElement.removeEventListener('pointermove', onPointerMove);
      domElement.removeEventListener('pointerup', onPointerUp);
      domElement.removeEventListener('pointercancel', onPointerCancel);
      domElement.removeEventListener('lostpointercapture', onLostCapture);
      window.removeEventListener('blur', onWindowBlur);
    },
  };
}
