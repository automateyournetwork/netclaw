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
