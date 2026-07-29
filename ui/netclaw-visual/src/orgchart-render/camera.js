/**
 * Orthographic, rotation-locked camera (FR-012, FR-013, R7).
 *
 * This is the actual fix for "clunky and hard to navigate" — more than the
 * theme is. HUD 1.0 used a PerspectiveCamera with unconstrained OrbitControls,
 * so any given frame showed the topology from an arbitrary angle. "External vs
 * internal" only reads if the layout and the viewer agree on which way is up,
 * and free rotation guarantees they do not.
 *
 * Orthographic additionally makes equal-tier siblings render at equal size,
 * which is the property that makes a chart read as a chart: under perspective
 * the far side of a row is smaller and reads as less important, which is a lie
 * the layout never intended to tell.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

/** World units visible vertically at zoom 1. Tuned to the layout's y-extent. */
export const FRUSTUM_HEIGHT = 150;
export const MIN_ZOOM = 0.35;
export const MAX_ZOOM = 6;

/**
 * Build the chart camera.
 *
 * @param {number} aspect width / height
 * @returns {THREE.OrthographicCamera}
 */
export function createChartCamera(aspect) {
  const h = FRUSTUM_HEIGHT / 2;
  const w = h * aspect;
  const camera = new THREE.OrthographicCamera(-w, w, h, -h, -500, 1000);
  // Straight down the -Z axis: the layout plane is XY, so this is a true
  // top-down read of the chart with no foreshortening.
  camera.position.set(0, 0, 200);
  camera.lookAt(0, 0, 0);
  camera.zoom = 1;
  camera.updateProjectionMatrix();
  return camera;
}

/**
 * Controls that pan and zoom but can never rotate (FR-012).
 *
 * @param {THREE.OrthographicCamera} camera
 * @param {HTMLElement} domElement
 * @returns {OrbitControls}
 */
export function createChartControls(camera, domElement) {
  const controls = new OrbitControls(camera, domElement);

  // The whole point. Without this the bands can be viewed upside down.
  controls.enableRotate = false;

  controls.enablePan = true;
  controls.enableZoom = true;
  controls.screenSpacePanning = true;
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minZoom = MIN_ZOOM;
  controls.maxZoom = MAX_ZOOM;

  // Left-drag pans. With rotation disabled the default left-drag would be dead
  // input, and pan is the only navigation a chart needs.
  controls.mouseButtons = {
    LEFT: THREE.MOUSE.PAN,
    MIDDLE: THREE.MOUSE.DOLLY,
    RIGHT: THREE.MOUSE.PAN,
  };
  controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_PAN };

  controls.target.set(0, 0, 0);
  controls.update();
  return controls;
}

/**
 * Keep the frustum correct across resizes.
 *
 * @param {THREE.OrthographicCamera} camera
 * @param {number} aspect
 */
export function resizeChartCamera(camera, aspect) {
  const h = FRUSTUM_HEIGHT / 2;
  camera.left = -h * aspect;
  camera.right = h * aspect;
  camera.top = h;
  camera.bottom = -h;
  camera.updateProjectionMatrix();
}

/**
 * Frame the chart so every node is visible on first paint (SC-001/002).
 * An operator should not have to hunt for the content before reading it.
 *
 * @param {THREE.OrthographicCamera} camera
 * @param {OrbitControls} controls
 * @param {Array<{position:{x:number,y:number}}>} nodes
 */
export function frameChart(camera, controls, nodes) {
  if (!Array.isArray(nodes) || nodes.length === 0) {
    controls.target.set(0, 0, 0);
    camera.position.set(0, 0, 200);
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    controls.update();
    return;
  }

  let minX = Infinity; let maxX = -Infinity; let minY = Infinity; let maxY = -Infinity;
  for (const n of nodes) {
    minX = Math.min(minX, n.position.x); maxX = Math.max(maxX, n.position.x);
    minY = Math.min(minY, n.position.y); maxY = Math.max(maxY, n.position.y);
  }

  const cx = (minX + maxX) / 2;
  const cy = (minY + maxY) / 2;
  const padding = 1.25;
  const spanY = Math.max(maxY - minY, 1) * padding;
  const spanX = Math.max(maxX - minX, 1) * padding;

  const aspect = (camera.right - camera.left) / (camera.top - camera.bottom);
  const zoom = Math.min(FRUSTUM_HEIGHT / spanY, (FRUSTUM_HEIGHT * aspect) / spanX);

  camera.zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));
  camera.position.set(cx, cy, 200);
  camera.updateProjectionMatrix();
  controls.target.set(cx, cy, 0);
  controls.update();
}
