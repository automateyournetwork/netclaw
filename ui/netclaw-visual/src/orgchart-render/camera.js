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

/** Measure the unobstructed canvas rectangle between the HUD chrome. */
export function measureChartViewport({ topbar, leftPanel, rightPanel, footerPanel, chatDrawer } = {}) {
  const width = window.innerWidth;
  const height = window.innerHeight;
  const inset = { width, height, top: 0, right: 0, bottom: 0, left: 0 };
  const rect = (element) => {
    if (!element || element.classList.contains('collapsed')) return null;
    const style = window.getComputedStyle(element);
    if (style.display === 'none' || style.visibility === 'hidden') return null;
    const bounds = element.getBoundingClientRect();
    return bounds.width > 0 && bounds.height > 0 ? bounds : null;
  };

  const top = rect(topbar);
  if (top) inset.top = Math.max(0, top.bottom + 18);

  const left = rect(leftPanel);
  const right = rect(rightPanel);
  if (width > 900) {
    if (left) inset.left = Math.max(0, left.right + 18);
    if (right) inset.right = Math.max(0, width - right.left + 18);
  } else {
    if (left) inset.bottom = Math.max(inset.bottom, height - left.top + 18);
    if (right) inset.bottom = Math.max(inset.bottom, height - right.top + 18);
  }

  const footer = rect(footerPanel);
  if (footer && footer.bottom >= height - 24) {
    inset.bottom = Math.max(inset.bottom, height - footer.top + 18);
  }

  const chat = rect(chatDrawer);
  const dockLine = height - inset.bottom - 24;
  if (chat && chat.bottom >= dockLine) {
    inset.bottom = Math.max(inset.bottom, height - chat.top + 18);
  }
  return inset;
}

/** Frame all nodes inside the unobstructed viewport, not behind HUD panels. */
export function frameChart(camera, controls, nodes, viewport = {}) {
  if (!Array.isArray(nodes) || nodes.length === 0) {
    controls.target.set(0, 0, 0);
    camera.position.set(0, 0, 200);
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    controls.update();
    return;
  }

  let minX = Infinity; let maxX = -Infinity; let minY = Infinity; let maxY = -Infinity;
  for (const node of nodes) {
    minX = Math.min(minX, node.position.x); maxX = Math.max(maxX, node.position.x);
    minY = Math.min(minY, node.position.y); maxY = Math.max(maxY, node.position.y);
  }

  const width = Math.max(1, viewport.width || window.innerWidth);
  const height = Math.max(1, viewport.height || window.innerHeight);
  const left = Math.max(0, viewport.left || 0);
  const right = Math.max(0, viewport.right || 0);
  const top = Math.max(0, viewport.top || 0);
  const bottom = Math.max(0, viewport.bottom || 0);
  const usableWidth = Math.max(width * 0.2, width - left - right);
  const usableHeight = Math.max(height * 0.2, height - top - bottom);

  const contentX = (minX + maxX) / 2;
  const contentY = (minY + maxY) / 2;
  const spanX = Math.max(maxX - minX, 1) * 1.22;
  const spanY = Math.max(maxY - minY, 1) * 1.28;
  const aspect = (camera.right - camera.left) / (camera.top - camera.bottom);
  const zoomX = (FRUSTUM_HEIGHT * aspect * usableWidth) / (width * spanX);
  const zoomY = (FRUSTUM_HEIGHT * usableHeight) / (height * spanY);
  const zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoomX, zoomY));

  const worldWidth = FRUSTUM_HEIGHT * aspect / zoom;
  const worldHeight = FRUSTUM_HEIGHT / zoom;
  const usableCenterX = left + usableWidth / 2;
  const usableCenterY = top + usableHeight / 2;
  const cameraX = contentX - ((usableCenterX - width / 2) * worldWidth / width);
  const cameraY = contentY + ((usableCenterY - height / 2) * worldHeight / height);

  camera.zoom = zoom;
  camera.position.set(cameraX, cameraY, 200);
  camera.updateProjectionMatrix();
  controls.target.set(cameraX, cameraY, 0);
  controls.update();
}
