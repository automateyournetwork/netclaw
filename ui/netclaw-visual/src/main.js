import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { AfterimagePass } from 'three/addons/postprocessing/AfterimagePass.js';
import { FilmPass } from 'three/addons/postprocessing/FilmPass.js';
import { GlitchPass } from 'three/addons/postprocessing/GlitchPass.js';
import { RGBShiftShader } from 'three/addons/shaders/RGBShiftShader.js';

// ── HUD 2.0: top-down trust org chart (feature 072) ───────────────────────
// The orbit layout is replaced by these; everything else in this file —
// materials, ribbons, labels, picking, polling, panels — is preserved (FR-028).
import {
  mountOrgChart, updateOrgChart, searchOrgChart,
  pickableObjects, chartNodes, tickOrgChart, activateNode,
  mountA11y, toggleNodeExpansion,
  setSelectedNode, clearSelectedNode,
  applyLayoutPositions, previewNodePosition,
} from './orgchart-render/index.js';
// Feature 102: layout state. Pure modules — every decision about where things go
// and what may be persisted lives here, tested, not in the render layer.
import { attachDrag } from './orgchart-render/drag.js';
import { PRESETS, PRESET_LABELS } from './orgchart/presets.js';
import {
  createLayoutStore, setPosition, setPreset, resetPreset, setCamera,
  markSaved, isDirty,
} from './orgchart/layout-store.js';
import { toPayload, applyPayload, clampCamera } from './orgchart/layout-payload.js';
import {
  createChartCamera, createChartControls, resizeChartCamera, frameChart,
} from './orgchart-render/camera.js';
// Feature 101: pure view-model + poll-outcome logic. These live under orgchart/
// (never importing three.js) precisely so the decisions they make — what a peer's
// state means, how stale is stale, whether a failed poll is an outage — are
// unit-tested. The render modules here have no automated coverage.
import { peerDetailView } from './orgchart/peer-detail.js';
import {
  createFeedState, recordSuccess, recordFailure, staleIndicator, renderablePayload,
} from './orgchart/feed-state.js';
import { VignetteShader } from 'three/addons/shaders/VignetteShader.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import gsap from 'gsap';
import { KnowledgePanel } from './panels/KnowledgePanel.js';

// ── Quality budget modes ───────────────────────────────────────────
// Focus: minimal effects, best perf. Balanced: default. Broadcast: all effects.
const QUALITY_MODES = ['focus', 'balanced', 'broadcast'];
const QUALITY_LABELS = { focus: 'FOCUS', balanced: 'BALANCED', broadcast: 'BROADCAST' };

// ── iN2N "risk" HUD layout (feature 056) ────────────────────────────
// Design (per operator): the Border Claw sits at the CENTER of the universe;
// EXTERNAL (eN2N) peer claws arc to the NORTH (+Z); INTERNAL member claws arc to
// the SOUTH (-Z). Every claw — local, remote peer, and member — carries its own
// orbiting skill sprites. Distinct colors per class. Spacing is widened so the
// three tiers read clearly. This config is consumed by the scene-layout pass
// (createMemberCores / positionClawsByRole) — tune live against the HUD.

const state = {
  graph: null,
  scene: null,
  camera: null,
  renderer: null,
  labels: null,
  composer: null,
  controls: null,
  core: null,           // backward compat alias (set to localCore)
  cores: [],            // all core objects (local + peers)
  localCore: null,      // the local NetClaw core
  peerCores: [],        // peer core objects (Mac NetClaw, Router)
  peerLinks: [],        // inter-core tubes
  integrations: [],
  devices: [],
  skillSprites: [],
  hovered: null,
  selected: null,
  qualityMode: 'balanced',
  filters: {
    query: '',
    categories: new Set(),
    view: 'integrations',
  },
  mouse: new THREE.Vector2(),
  // Feature 101 (FR-041/042/043): poll-outcome memory for freeze-and-flag.
  feed: createFeedState(),
  // Feature 102: per-preset arrangement + dirty tracking.
  layout: createLayoutStore('orgchart'),
  dragging: null,
  raycaster: new THREE.Raycaster(),
  socket: null,
  clock: new THREE.Clock(),
  // Post-processing refs
  glitchPass: null,
  rgbShiftPass: null,
  afterimagePass: null,
  filmPass: null,
  bloomPass: null,
  vignettePass: null,
  smaaPass: null,
  // Particle flow system
  particleSystem: null,
  particleData: [],
  particleDummy: new THREE.Object3D(),
  // Terminal card pool
  terminalCards: [],
  // BGP topology
  bgp: null,
  n2n: null,
  // Chat session focus mode
  chatSession: {
    active: false,               // true when user has sent a message
    litIntegrations: new Set(),  // integration ids currently lit
    litTools: new Map(),         // tool name → { integrationId, spriteIndex }
  },
};

const dom = {
  loading: document.getElementById('loading'),
  loadingProgress: document.getElementById('loading-progress'),
  loadingText: document.getElementById('loading-text'),
  search: document.getElementById('search'),
  categoryList: document.getElementById('category-list'),
  settingsList: document.getElementById('settings-list'),
  detailPanel: document.getElementById('detail-panel'),
  tooltip: document.getElementById('tooltip'),
  footerSocket: document.getElementById('footer-socket'),
  footerModel: document.getElementById('footer-model'),
  footerGateway: document.getElementById('footer-gateway'),
  footerBudget: document.getElementById('footer-budget'),
  footerUpdated: document.getElementById('footer-updated'),
  chatDrawer: document.getElementById('chat-drawer'),
  chatMessages: document.getElementById('chat-messages'),
  chatForm: document.getElementById('chat-form'),
  chatInput: document.getElementById('chat-input'),
  chatToggle: document.getElementById('chat-toggle'),
  gatewayStatus: document.getElementById('gateway-status'),
  sidebarLeft: document.getElementById('sidebar-left'),
  sidebarRight: document.getElementById('sidebar-right'),
  footerPanel: document.getElementById('footer-panel'),
  toggleLeft: document.getElementById('toggle-left'),
  toggleRight: document.getElementById('toggle-right'),
  toggleFooter: document.getElementById('toggle-footer'),
  reopenLeft: document.getElementById('reopen-left'),
  reopenRight: document.getElementById('reopen-right'),
  reopenFooter: document.getElementById('reopen-footer'),
  stats: {
    integrations: document.getElementById('metric-integrations'),
    skills: document.getElementById('metric-skills'),
    devices: document.getElementById('metric-devices'),
    tools: document.getElementById('metric-tools'),
  },
};

// ── Quality mode switching ──────────────────────────────────────────
function setQualityMode(mode) {
  state.qualityMode = mode;
  const isFocus = mode === 'focus';
  const isBroadcast = mode === 'broadcast';

  // Afterimage: off in focus, off in balanced-idle, on in broadcast
  if (state.afterimagePass) state.afterimagePass.enabled = isBroadcast;
  // Film grain: off in focus, on in balanced+broadcast
  if (state.filmPass) state.filmPass.enabled = !isFocus;
  // RGB shift: off in focus, reduced in balanced, full in broadcast
  if (state.rgbShiftPass) {
    state.rgbShiftPass.enabled = !isFocus;
    state.rgbShiftPass.uniforms.amount.value = isBroadcast ? 0.0012 : 0.0008;
  }
  // SMAA: always on (cheap)
  // Bloom: reduced in focus
  if (state.bloomPass) {
    state.bloomPass.strength = isFocus ? 0.6 : 1.1;
  }
  // Shadows: off in focus
  if (state.renderer) {
    state.renderer.shadowMap.enabled = !isFocus;
  }

  // Update UI label
  const btn = document.getElementById('quality-toggle');
  if (btn) btn.textContent = QUALITY_LABELS[mode];
}

function cycleQualityMode() {
  const idx = QUALITY_MODES.indexOf(state.qualityMode);
  const next = QUALITY_MODES[(idx + 1) % QUALITY_MODES.length];
  setQualityMode(next);
}

// Temporarily enable cinematic effects during activations
function enableCinematicBurst() {
  if (state.qualityMode === 'broadcast') return; // already on
  if (state.afterimagePass) state.afterimagePass.enabled = true;
  if (state.filmPass) state.filmPass.enabled = true;
  // Restore after 6 seconds
  setTimeout(() => {
    if (state.qualityMode !== 'broadcast') {
      if (state.afterimagePass) state.afterimagePass.enabled = state.qualityMode !== 'focus';
      if (state.filmPass) state.filmPass.enabled = state.qualityMode !== 'focus';
    }
  }, 6000);
}

// ── Chat Focus Mode ─────────────────────────────────────────────
// When the user sends a message the scene dims so only the core is prominent.
// As activations arrive, each integration lights up sequentially and stays lit
// for the remainder of the session. "New Session" resets everything.

function enterChatFocus() {
  if (state.chatSession.active) return; // already in focus
  state.chatSession.active = true;

  // Dim every integration
  state.integrations.forEach((entry) => {
    gsap.to(entry.tubeMat.uniforms.uOpacity, { value: 0.04, duration: 0.6 });
    gsap.to(entry.halo.material, { opacity: 0.04, duration: 0.6 });
    gsap.to(entry.node.material.uniforms.uBrightness, { value: 0.15, duration: 0.6 });
    // Hide any visible skills
    entry.skillSprites.forEach((sprite) => {
      sprite.mesh.visible = false;
      sprite.label.visible = false;
      if (sprite.wire) sprite.wire.visible = false;
    });
  });

  // Dim devices
  state.devices.forEach((entry) => {
    gsap.to(entry.mesh.material, { opacity: 0.15, duration: 0.6 });
  });

  // Pulse the core so it stands out
  if (state.localCore) {
    gsap.to(state.localCore.nucleus.material, { emissiveIntensity: 3.0, duration: 0.8, ease: 'power2.out' });
    gsap.to(state.localCore.torus.material, { opacity: 1.0, duration: 0.6, ease: 'power2.out' });
  }
}

function lightIntegration(integrationId) {
  // Mark as lit so it stays visible for the rest of the session
  state.chatSession.litIntegrations.add(integrationId);

  const entry = state.integrations.find((e) => e.payload.id === integrationId);
  if (!entry || !entry.group.visible) return;

  // Phase 1: Trace tube from core → node
  gsap.fromTo(entry.tubeMat.uniforms.uOpacity,
    { value: 0.04 },
    { value: 1.0, duration: 0.8, ease: 'power2.out' },
  );

  // Phase 2: Light up the node
  gsap.to(entry.node.material.uniforms.uBrightness, {
    value: 2.5, delay: 0.8, duration: 0.5, ease: 'power2.out',
  });
  gsap.to(entry.halo.material, { opacity: 1.0, delay: 0.8, duration: 0.4, ease: 'power2.out' });

  // Scale burst on arrival
  gsap.fromTo(entry.group.scale,
    { x: 1, y: 1, z: 1 },
    { x: 1.5, y: 1.5, z: 1.5, delay: 0.8, duration: 0.4, yoyo: true, repeat: 1, ease: 'back.out(2)' },
  );

  // Fire beam
  fireActivationBeam(entry.basePosition, entry.payload.color);

  // Phase 3: Reveal skills and keep them visible (persistent session)
  setTimeout(() => {
    revealSkills(entry);
    // Pulse each skill sequentially
    entry.skillSprites.forEach((sprite, i) => {
      setTimeout(() => {
        if (sprite.mesh.visible && sprite.mesh.material) {
          gsap.to(sprite.mesh.material, {
            opacity: 1.0, duration: 0.3, ease: 'power2.out',
            onComplete: () => { gsap.to(sprite.mesh.material, { opacity: 0.66, duration: 0.5 }); },
          });
          gsap.fromTo(sprite.mesh.scale,
            { x: 1, y: 1, z: 1 },
            { x: 2.2, y: 2.2, z: 2.2, duration: 0.25, yoyo: true, repeat: 1, ease: 'back.out(3)' },
          );
        }
      }, i * 40 + 600);
    });
    // NOTE: skills stay visible — no hide timeout (persistent session)
  }, 1400);

  // Settle node to a dimmer-but-still-visible state after full animation
  setTimeout(() => {
    gsap.to(entry.tubeMat.uniforms.uOpacity, { value: 0.45, duration: 0.8 });
    gsap.to(entry.node.material.uniforms.uBrightness, { value: 1.4, duration: 0.8 });
    gsap.to(entry.halo.material, { opacity: 0.4, duration: 0.8 });
  }, 1400 + entry.skillSprites.length * 40 + 600 + 1500);
}

function lightDevice(deviceId) {
  const entry = state.devices.find((e) => e.payload.id === deviceId);
  if (!entry || !entry.mesh.visible) return;

  gsap.to(entry.mesh.material, {
    opacity: 1.0, emissiveIntensity: 2.0, duration: 0.3,
    yoyo: true, repeat: 3, ease: 'power2.inOut',
    onComplete: () => { entry.mesh.material.emissiveIntensity = 0.55; entry.mesh.material.opacity = 0.9; },
  });
  gsap.fromTo(entry.mesh.scale,
    { x: 1, y: 1, z: 1 },
    { x: 1.6, y: 1.6, z: 1.6, duration: 0.3, yoyo: true, repeat: 1, ease: 'back.out(2)' },
  );
  fireActivationBeam(entry.basePosition, 0x68f5b2);
}

function resetChatSession() {
  state.chatSession.active = false;
  state.chatSession.litIntegrations.clear();
  state.chatSession.litTools.clear();

  // Restore all integrations to default brightness
  state.integrations.forEach((entry) => {
    gsap.to(entry.tubeMat.uniforms.uOpacity, { value: 0.25, duration: 0.8 });
    gsap.to(entry.halo.material, { opacity: 0.26, duration: 0.8 });
    gsap.to(entry.node.material.uniforms.uBrightness, { value: 1.0, duration: 0.8 });
    // Hide any visible skills
    entry.skillSprites.forEach((sprite) => {
      sprite.mesh.visible = false;
      sprite.label.visible = false;
      if (sprite.wire) sprite.wire.visible = false;
    });
  });

  // Restore devices
  state.devices.forEach((entry) => {
    gsap.to(entry.mesh.material, { opacity: 0.9, duration: 0.8 });
  });

  // Restore core to normal
  if (state.localCore) {
    gsap.to(state.localCore.nucleus.material, { emissiveIntensity: 0.9, duration: 1.0 });
    gsap.to(state.localCore.torus.material, { opacity: 0.36, duration: 0.8 });
  }

  // Clear chat messages
  dom.chatMessages.innerHTML = '';
}

// ── Activation beam lines (reusable pool) ──────────────────────────
const activationBeams = [];
const BEAM_POOL_SIZE = 20;

// ── Pre-allocated scratch vectors (avoid per-frame allocations) ────
const _v0 = new THREE.Vector3();
const _v1 = new THREE.Vector3();
const _v2 = new THREE.Vector3();
const _v3 = new THREE.Vector3();

// ── Shared geometry cache (avoid duplicating identical geometries) ──
const _sharedGeo = {
  skillTetra: new THREE.TetrahedronGeometry(0.24, 0),
  coreShell: new THREE.IcosahedronGeometry(3.4, 1),
  coreNucleus: new THREE.IcosahedronGeometry(1.85, 3),
  deviceRouter: new THREE.CylinderGeometry(0.7, 0.7, 0.4, 8),
  deviceSwitch: new THREE.BoxGeometry(1.1, 0.42, 0.9),
};

// ── Shared material caches (avoid per-object material duplication) ──
const _skillMaterialCache = new Map();
function getSkillMaterial(color) {
  const key = typeof color === 'number' ? color : new THREE.Color(color).getHex();
  if (_skillMaterialCache.has(key)) return _skillMaterialCache.get(key).clone();
  const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.66 });
  _skillMaterialCache.set(key, mat);
  return mat.clone();
}

const _haloMaterialCache = new Map();
function getHaloMaterial(color) {
  const key = typeof color === 'number' ? color : new THREE.Color(color).getHex();
  if (_haloMaterialCache.has(key)) return _haloMaterialCache.get(key);
  const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.26 });
  _haloMaterialCache.set(key, mat);
  return mat;
}

const _haloGeoCache = new Map();
function getHaloGeometry(innerR) {
  const key = innerR.toFixed(2);
  if (_haloGeoCache.has(key)) return _haloGeoCache.get(key);
  const geo = new THREE.TorusGeometry(innerR, 0.05, 12, 90);
  _haloGeoCache.set(key, geo);
  return geo;
}

function setLoading(progress, text) {
  dom.loadingProgress.style.width = `${progress}%`;
  dom.loadingText.textContent = text;
}

async function fetchGraph() {
  const response = await fetch('/api/graph');
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  return response.json();
}

function initScene() {
  const root = document.getElementById('scene-root');

  state.scene = new THREE.Scene();
  // Fog thinned: the chart is planar, so depth haze only dulled it.
  state.scene.fog = new THREE.FogExp2(0x081426, 0.0018);

  // HUD 2.0 (FR-012/013): orthographic and rotation-locked. A perspective
  // camera under free OrbitControls was the dominant cause of "hard to
  // navigate" — hierarchy only reads if the layout and the viewer agree on
  // which way is up. Ortho additionally renders equal-tier siblings at equal
  // size, which is what makes a chart read as a chart.
  state.camera = createChartCamera(window.innerWidth / window.innerHeight);

  state.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
  state.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  state.renderer.setSize(window.innerWidth, window.innerHeight);
  state.renderer.toneMapping = THREE.ACESFilmicToneMapping;
  state.renderer.toneMappingExposure = 1.55;   // HUD 2.0: brighter overall (operator feedback)
  state.renderer.shadowMap.enabled = true;
  state.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  root.appendChild(state.renderer.domElement);

  state.labels = new CSS2DRenderer();
  state.labels.setSize(window.innerWidth, window.innerHeight);
  state.labels.domElement.style.position = 'fixed';
  state.labels.domElement.style.inset = '0';
  state.labels.domElement.style.pointerEvents = 'none';
  root.appendChild(state.labels.domElement);

  // ── Post-processing pipeline (10 passes) ──────────────────────
  const sz = new THREE.Vector2(window.innerWidth, window.innerHeight);
  state.composer = new EffectComposer(state.renderer);
  // 1. Render
  state.composer.addPass(new RenderPass(state.scene, state.camera));
  // 2. Bloom
  state.bloomPass = new UnrealBloomPass(sz, 1.1, 0.55, 0.5);
  state.composer.addPass(state.bloomPass);
  // 3. Afterimage (motion trails)
  state.afterimagePass = new AfterimagePass(0.82);
  state.composer.addPass(state.afterimagePass);
  // 4. Film grain
  state.filmPass = new FilmPass(0.18);
  state.composer.addPass(state.filmPass);
  // 5. RGB shift (chromatic aberration)
  state.rgbShiftPass = new ShaderPass(RGBShiftShader);
  state.rgbShiftPass.uniforms.amount.value = 0.0008;
  state.composer.addPass(state.rgbShiftPass);
  // 6. Vignette
  state.vignettePass = new ShaderPass(VignetteShader);
  state.vignettePass.uniforms.offset.value = 0.95;
  state.vignettePass.uniforms.darkness.value = 1.4;
  state.composer.addPass(state.vignettePass);
  // 7. Glitch (disabled by default, fires during activations)
  state.glitchPass = new GlitchPass();
  state.glitchPass.enabled = false;
  state.composer.addPass(state.glitchPass);
  // 8. SMAA anti-aliasing
  state.smaaPass = new SMAAPass(window.innerWidth * state.renderer.getPixelRatio(), window.innerHeight * state.renderer.getPixelRatio());
  state.composer.addPass(state.smaaPass);
  // 9. Output (sRGB tone mapping)
  state.composer.addPass(new OutputPass());

  // Pan and zoom only — rotation is disabled so the bands can never invert
  // (FR-012, SC-003).
  state.controls = createChartControls(state.camera, state.renderer.domElement);

  // ── Enhanced lighting (Section E) ─────────────────────────────
  state.scene.add(new THREE.AmbientLight(0x7fb0e0, 1.15));  // lifted for the flat chart

  // Key light — overhead spotlight with shadows
  const keyLight = new THREE.SpotLight(0x65c3ff, 4.5, 120, Math.PI * 0.35, 0.4, 1.2);
  keyLight.position.set(0, 32, 12);
  keyLight.castShadow = true;
  keyLight.shadow.mapSize.set(1024, 1024);
  keyLight.shadow.camera.near = 8;
  keyLight.shadow.camera.far = 80;
  state.scene.add(keyLight);
  state.scene.add(keyLight.target);

  // Warm fill — side accent
  const warmLight = new THREE.SpotLight(0xff7b54, 2.2, 100, Math.PI * 0.5, 0.5, 1.5);
  warmLight.position.set(-28, -4, -16);
  state.scene.add(warmLight);

  // Rim back-light
  const rimLight = new THREE.SpotLight(0x9b7bff, 1.8, 100, Math.PI * 0.4, 0.3, 1.4);
  rimLight.position.set(18, 10, -24);
  state.scene.add(rimLight);

  addEnvironment();
}

function addEnvironment() {
  const ground = new THREE.GridHelper(180, 48, 0x17486f, 0x10273d);
  ground.position.y = -10;
  ground.material.transparent = true;
  ground.material.opacity = 0.2;
  ground.matrixAutoUpdate = false;
  ground.updateMatrix();
  state.scene.add(ground);

  // Animated ground rings with pulsing shader
  const ringUniforms = { uTime: { value: 0 } };
  for (let i = 1; i <= 5; i += 1) {
    const ringMat = new THREE.ShaderMaterial({
      uniforms: { ...ringUniforms, uIndex: { value: i } },
      vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: `
        uniform float uTime;
        uniform float uIndex;
        varying vec2 vUv;
        void main() {
          float angle = atan(vUv.y - 0.5, vUv.x - 0.5);
          float sweep = sin(angle * 2.0 + uTime * 0.8 + uIndex * 1.2) * 0.5 + 0.5;
          float pulse = 0.1 + sweep * 0.14;
          vec3 col = mod(uIndex, 2.0) > 0.5 ? vec3(0.18, 0.36, 0.53) : vec3(0.61, 0.30, 0.23);
          gl_FragColor = vec4(col, pulse);
        }
      `,
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
    });
    const ring = new THREE.Mesh(new THREE.RingGeometry(8 * i - 0.06, 8 * i + 0.06, 96), ringMat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = -9.98;
    ring.matrixAutoUpdate = false;
    ring.updateMatrix();
    ring.userData.ringUniforms = ringUniforms;
    state.scene.add(ring);
  }

  // Twinkling starfield with custom shader
  const STAR_COUNT = 3000;
  const starGeo = new THREE.BufferGeometry();
  const starPositions = new Float32Array(STAR_COUNT * 3);
  const starPhases = new Float32Array(STAR_COUNT);
  const starSizes = new Float32Array(STAR_COUNT);
  for (let i = 0; i < STAR_COUNT; i++) {
    starPositions[i * 3] = (Math.random() - 0.5) * 300;
    starPositions[i * 3 + 1] = (Math.random() - 0.15) * 200;
    starPositions[i * 3 + 2] = (Math.random() - 0.5) * 300;
    starPhases[i] = Math.random() * Math.PI * 2;
    starSizes[i] = 0.8 + Math.random() * 2.2;
  }
  starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
  starGeo.setAttribute('aPhase', new THREE.BufferAttribute(starPhases, 1));
  starGeo.setAttribute('aSize', new THREE.BufferAttribute(starSizes, 1));

  const starMat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 } },
    vertexShader: `
      attribute float aPhase;
      attribute float aSize;
      uniform float uTime;
      varying float vAlpha;
      void main() {
        vAlpha = 0.35 + 0.45 * sin(uTime * 1.1 + aPhase);
        vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
        gl_PointSize = aSize * (80.0 / -mvPosition.z);
        gl_Position = projectionMatrix * mvPosition;
      }
    `,
    fragmentShader: `
      varying float vAlpha;
      void main() {
        float d = length(gl_PointCoord - 0.5) * 2.0;
        if (d > 1.0) discard;
        float alpha = vAlpha * smoothstep(1.0, 0.3, d);
        gl_FragColor = vec4(0.53, 0.75, 1.0, alpha);
      }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  });
  const stars = new THREE.Points(starGeo, starMat);
  stars.userData.starUniforms = starMat.uniforms;
  stars.matrixAutoUpdate = false;
  stars.updateMatrix();
  state.scene.add(stars);

  // Store direct uniform references — avoids scene.traverse in animate loop
  state.envUniforms = { starTime: starMat.uniforms.uTime, ringTime: ringUniforms.uTime };
}

function makeLabel(text) {
  const element = document.createElement('div');
  element.className = 'label';
  element.textContent = text;
  return new CSS2DObject(element);
}

// Triangular layout positions for multi-core topology


// ── Holographic ShaderMaterial for integration nodes (Section D) ──
function createHolographicMaterial(color) {
  const c = new THREE.Color(color);
  return new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: c },
      uEmissive: { value: c.clone().multiplyScalar(0.7) },
      uBrightness: { value: 1.0 },
    },
    vertexShader: `
      varying vec3 vNormal;
      varying vec3 vWorldPos;
      varying vec2 vUv;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        vWorldPos = (modelMatrix * vec4(position, 1.0)).xyz;
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uTime;
      uniform vec3 uColor;
      uniform vec3 uEmissive;
      uniform float uBrightness;
      varying vec3 vNormal;
      varying vec3 vWorldPos;
      varying vec2 vUv;
      void main() {
        // Fresnel rim glow
        vec3 viewDir = normalize(cameraPosition - vWorldPos);
        float fresnel = pow(1.0 - abs(dot(viewDir, vNormal)), 2.5);
        // Horizontal scan lines
        float scanLine = sin(vWorldPos.y * 28.0 - uTime * 3.0) * 0.5 + 0.5;
        scanLine = smoothstep(0.3, 0.7, scanLine) * 0.2;
        // Data grid pattern
        float grid = step(0.96, fract(vWorldPos.x * 2.0)) + step(0.96, fract(vWorldPos.z * 2.0));
        grid *= 0.08;
        // Compose
        vec3 col = uColor * (0.6 + scanLine + grid);
        col += uEmissive * (0.55 + fresnel * 1.4);
        col += vec3(0.4, 0.75, 1.0) * fresnel * 0.6;
        col *= uBrightness;
        float alpha = clamp((0.85 + fresnel * 0.15) * uBrightness, 0.0, 1.0);
        gl_FragColor = vec4(col, alpha);
      }
    `,
    transparent: true,
    side: THREE.FrontSide,
    depthWrite: true,
  });
}

function createNodeMaterial(color) {
  return new THREE.MeshPhysicalMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.55,
    roughness: 0.18,
    metalness: 0.8,
    transparent: true,
    opacity: 0.9,
  });
}

// Device material with iridescence — shared instances per color
const _deviceMaterialCache = new Map();
function createDeviceMaterial(color) {
  const key = typeof color === 'number' ? color : new THREE.Color(color).getHex();
  if (_deviceMaterialCache.has(key)) return _deviceMaterialCache.get(key);
  const mat = new THREE.MeshPhysicalMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.55,
    roughness: 0.15,
    metalness: 0.85,
    iridescence: 0.6,
    clearcoat: 0.8,
    clearcoatRoughness: 0.1,
    transparent: true,
    opacity: 0.92,
  });
  _deviceMaterialCache.set(key, mat);
  return mat;
}

// ── Pre-allocated ribbon geometry for dynamic tubes ────────────────
// Replaces per-frame TubeGeometry rebuilds with in-place buffer updates.
// A ribbon is a flat strip with SEGMENTS+1 cross-sections, 2 verts each.
const RIBBON_SEGMENTS = 32;
const RIBBON_VERTS = (RIBBON_SEGMENTS + 1) * 2;
const RIBBON_INDICES_COUNT = RIBBON_SEGMENTS * 6;

function createRibbonGeometry(halfWidth) {
  const positions = new Float32Array(RIBBON_VERTS * 3);
  const uvs = new Float32Array(RIBBON_VERTS * 2);
  const indices = new Uint16Array(RIBBON_INDICES_COUNT);

  // Build index buffer (static — triangle strip as indexed triangles)
  for (let i = 0; i < RIBBON_SEGMENTS; i++) {
    const base = i * 2;
    const off = i * 6;
    indices[off] = base;
    indices[off + 1] = base + 1;
    indices[off + 2] = base + 2;
    indices[off + 3] = base + 1;
    indices[off + 4] = base + 3;
    indices[off + 5] = base + 2;
  }

  // Build UV buffer (static — u goes along the ribbon, v is 0/1 across)
  for (let i = 0; i <= RIBBON_SEGMENTS; i++) {
    const u = i / RIBBON_SEGMENTS;
    uvs[i * 4] = u;
    uvs[i * 4 + 1] = 0;
    uvs[i * 4 + 2] = u;
    uvs[i * 4 + 3] = 1;
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geo.setIndex(new THREE.BufferAttribute(indices, 1));
  geo.userData.halfWidth = halfWidth || 0.06;
  return geo;
}

// Reusable scratch for ribbon updates
const _ribbonPt = new THREE.Vector3();
const _ribbonTan = new THREE.Vector3();
const _ribbonUp = new THREE.Vector3(0, 1, 0);
const _ribbonSide = new THREE.Vector3();

function updateRibbonGeometry(geo, p0, p1, p2) {
  // Simple quadratic Bezier evaluation (replaces CatmullRomCurve3 + TubeGeometry)
  const positions = geo.attributes.position.array;
  const hw = geo.userData.halfWidth;

  for (let i = 0; i <= RIBBON_SEGMENTS; i++) {
    const t = i / RIBBON_SEGMENTS;
    const t1 = 1 - t;
    // Quadratic Bezier: P = (1-t)^2*P0 + 2(1-t)t*P1 + t^2*P2
    _ribbonPt.set(
      t1 * t1 * p0.x + 2 * t1 * t * p1.x + t * t * p2.x,
      t1 * t1 * p0.y + 2 * t1 * t * p1.y + t * t * p2.y,
      t1 * t1 * p0.z + 2 * t1 * t * p1.z + t * t * p2.z,
    );
    // Tangent: dP/dt = 2(1-t)(P1-P0) + 2t(P2-P1)
    _ribbonTan.set(
      2 * t1 * (p1.x - p0.x) + 2 * t * (p2.x - p1.x),
      2 * t1 * (p1.y - p0.y) + 2 * t * (p2.y - p1.y),
      2 * t1 * (p1.z - p0.z) + 2 * t * (p2.z - p1.z),
    ).normalize();
    // Side vector = tangent x up
    _ribbonSide.crossVectors(_ribbonTan, _ribbonUp).normalize().multiplyScalar(hw);
    // If tangent is nearly parallel to up, use a fallback
    if (_ribbonSide.lengthSq() < 0.001) {
      _ribbonSide.set(hw, 0, 0);
    }

    const idx = i * 6; // 2 verts * 3 components
    positions[idx] = _ribbonPt.x - _ribbonSide.x;
    positions[idx + 1] = _ribbonPt.y - _ribbonSide.y;
    positions[idx + 2] = _ribbonPt.z - _ribbonSide.z;
    positions[idx + 3] = _ribbonPt.x + _ribbonSide.x;
    positions[idx + 4] = _ribbonPt.y + _ribbonSide.y;
    positions[idx + 5] = _ribbonPt.z + _ribbonSide.z;
  }
  geo.attributes.position.needsUpdate = true;
  geo.computeBoundingSphere();
}

// ── Tube shader material for data-flow connections (Section F) ────
function createTubeMaterial(color) {
  const c = new THREE.Color(color);
  return new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: c },
      uOpacity: { value: 0.25 },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uTime;
      uniform vec3 uColor;
      uniform float uOpacity;
      varying vec2 vUv;
      void main() {
        // Flowing data packets
        float packet = smoothstep(0.38, 0.5, fract(vUv.x * 8.0 - uTime * 0.6));
        packet *= smoothstep(0.62, 0.5, fract(vUv.x * 8.0 - uTime * 0.6));
        // Edge glow
        float edge = 1.0 - abs(vUv.y - 0.5) * 2.0;
        edge = pow(edge, 0.6);
        // Compose
        vec3 col = uColor * (0.3 + packet * 1.5);
        float alpha = uOpacity * edge * (0.5 + packet * 0.8);
        gl_FragColor = vec4(col, alpha);
      }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}






// ── BGP Topology Visualization ────────────────────────────────────
// Peers are NEIGHBORS — same level as core, connected by horizontal peer links
function deduplicatePeers(peers) {
  const seen = new Map();
  for (const peer of peers) {
    const key = peer.as ? `as${peer.as}` : peer.peer;
    const existing = seen.get(key);
    if (!existing) {
      seen.set(key, { ...peer });
    } else {
      if (peer.type === 'claw') existing.type = 'claw';
      if (peer.routerId && !existing.routerId) existing.routerId = peer.routerId;
      existing.routesReceived = Math.max(existing.routesReceived || 0, peer.routesReceived || 0);
      if (peer.adjRibIn?.length > (existing.adjRibIn?.length || 0)) existing.adjRibIn = peer.adjRibIn;
      if (peer.state === 'Established') existing.state = 'Established';
    }
  }
  return [...seen.values()];
}






function renderSidebar(graph) {
  dom.categoryList.innerHTML = '';
  graph.categories.forEach((category) => {
    state.filters.categories.add(category.name);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'toggle-item';
    button.innerHTML = `
      <span class="swatch" style="color:${category.color}; background:${category.color};"></span>
      <span>${category.name}</span>
      <span class="toggle-meta">${category.count}</span>
    `;
    button.addEventListener('click', () => {
      if (state.filters.categories.has(category.name)) {
        state.filters.categories.delete(category.name);
        button.classList.add('off');
      } else {
        state.filters.categories.add(category.name);
        button.classList.remove('off');
      }
      applyFilters();
    });
    dom.categoryList.appendChild(button);
  });

  dom.settingsList.innerHTML = graph.settings
    .map((item) => `<div class="info-card"><div class="eyebrow">${item.label}</div><strong>${item.value}</strong></div>`)
    .join('');
}

function renderMetrics(graph) {
  dom.stats.integrations.textContent = graph.stats.integrationCount;
  dom.stats.skills.textContent = graph.stats.skillCount;
  dom.stats.devices.textContent = graph.stats.deviceCount;
  dom.stats.tools.textContent = graph.stats.toolEstimate;
  dom.footerModel.textContent = graph.config?.agents?.defaults?.model?.primary?.replace('anthropic/', '') || 'unknown';
  dom.footerGateway.textContent = graph.config?.gateway?.mode || 'unknown';
  dom.footerUpdated.textContent = new Date(graph.generatedAt).toLocaleTimeString();

  // Budget status poll (spec 109)
  pollBudgetStatus();
}

function applyFilters() {
  const query = state.filters.query.trim().toLowerCase();

  state.integrations.forEach((entry) => {
    const matchesCategory = state.filters.categories.has(entry.payload.category);
    const matchesQuery = !query || [entry.payload.name, entry.payload.description].join(' ').toLowerCase().includes(query);
    const visible = state.filters.view !== 'devices' && matchesCategory && matchesQuery;
    entry.group.visible = visible;
    entry.tube.visible = visible;
    entry.label.visible = visible;
    entry.skillSprites.forEach((sprite) => {
      sprite.mesh.visible = false;
      sprite.label.visible = false;
      if (sprite.wire) sprite.wire.visible = false;
    });
  });

  state.devices.forEach((entry) => {
    const matchesQuery = !query || [entry.payload.name, entry.payload.os, entry.payload.platform].join(' ').toLowerCase().includes(query);
    const visible = state.filters.view !== 'integrations' && matchesQuery;
    entry.mesh.visible = visible;
    entry.line.visible = visible;
    entry.label.visible = visible;
  });

  if (state.selected?.kind === 'integration') {
    const target = state.integrations.find((entry) => entry.payload.id === state.selected.id);
    if (target?.group.visible) {
      revealSkills(target);
    } else {
      clearSelection();
    }
  }

  if (state.selected?.kind === 'device') {
    const target = state.devices.find((entry) => entry.payload.id === state.selected.id);
    if (!target?.mesh.visible) clearSelection();
  }
}

function revealSkills(entry) {
  entry.skillSprites.forEach((sprite, i) => {
    sprite.mesh.visible = true;
    sprite.label.visible = true;
    if (sprite.wire) {
      sprite.wire.visible = true;
      // Grow-in animation
      gsap.fromTo(sprite.wireMat.uniforms.uProgress,
        { value: 0 },
        { value: 1, duration: 0.6, delay: i * 0.04, ease: 'power2.out' },
      );
      gsap.to(sprite.wireMat.uniforms.uOpacity,
        { value: 0.35, duration: 0.3, delay: i * 0.04 },
      );
    }
    // Pop-in skill node after wire reaches it
    gsap.fromTo(sprite.mesh.scale,
      { x: 0, y: 0, z: 0 },
      { x: 1, y: 1, z: 1, duration: 0.4, delay: i * 0.04 + 0.3, ease: 'back.out(2)' },
    );
  });
}

// ── N2N Federation view (feature 052) ────────────────────────────
// Finds the federation record for a claw peer by matching AS number.
function findFederationPeer(peer) {
  if (!state.n2n?.available) return null;
  return (state.n2n.peers || []).find((fp) => {
    const asMatch = fp.identity && peer.as && fp.identity.startsWith(`as${peer.as}-`);
    return asMatch;
  }) || null;
}

// 056 iN2N: this claw's own risk view (role + members) for the local-core panel.
function renderRiskSection() {
  const risk = state.n2n?.risk;
  if (!risk || risk.role === 'standalone') {
    return `<div class="n2n-section"><h3>Risk (iN2N)</h3>
      <p class="n2n-muted">Standalone claw — a risk of one, its own Border.</p></div>`;
  }
  if (risk.role === 'member') {
    return `<div class="n2n-section"><h3>Risk: ${risk.risk_name} (Member)</h3>
      <div class="detail-row"><span>Member</span><strong>${risk.self_member_id || '—'}</strong></div>
      <p class="n2n-muted">Focused specialist — dials the Border; not internet-facing.</p></div>`;
  }
  // Border: hub with member spokes
  const members = state.n2n?.members || [];
  const postureHtml = renderPostureBadge();
  const rows = members.map((m) => {
    const dot = m.live ? '<span class="n2n-fresh">●</span>' : '<span class="n2n-muted">○</span>';
    const stCls = m.state === 'active' ? 'federated'
      : (m.state === 'quarantined' || m.state === 'removed') ? 'not-federated' : 'consent-pending-local';
    return `<li>${dot} ${m.member_id}
      <span class="n2n-muted">(${m.profile || 'custom'})</span>
      <strong class="n2n-state-${stCls}">${m.state}</strong>
      <span class="n2n-muted">· ${m.specialty_count} specialty</span></li>`;
  }).join('') || '<li class="n2n-muted">no members — add with `netclaw risk add`</li>';
  return `<div class="n2n-section n2n-federated">
      <h3>Risk: ${risk.risk_name} (Border)</h3>
      ${postureHtml}
      <div class="detail-row"><span>Stacks</span><strong>${risk.enabled_stacks || '—'}</strong></div>
      <div class="detail-row"><span>Members</span><strong>${risk.members_active ?? 0}/${risk.member_count ?? 0} active</strong></div>
      <h4>Member spokes (${members.length})</h4>
      <ul class="n2n-list">${rows}</ul>
      ${renderGaitTrail()}
    </div>`;
}

// 065: chroma-to-chroma replication jobs — status/progress for in-flight and
// recent n2n_replicate/n2n_replicate_resync runs. Renders nothing on a
// pre-065 daemon or when no job has ever run.
function renderReplicationJobs() {
  const jobs = state.n2n?.replicationJobs || [];
  if (!jobs.length) return '';
  const stCls = (s) => (s === 'completed' ? 'federated'
    : s === 'failed' ? 'not-federated' : 'consent-pending-local');
  const rows = jobs.slice(0, 8).map((j) => `<li>
      <strong class="n2n-state-${stCls(j.state)}">${j.state}</strong>
      <span class="n2n-muted">${j.target_name || ''} · ${j.peer_identity || ''}</span>
      ${j.progress ? `<span class="n2n-muted">· ${j.progress}</span>` : ''}
      <span class="n2n-muted">· ${(j.updated_at || '').replace('T', ' ').replace('Z', '')}</span></li>`).join('');
  return `<h4>Replication jobs (chroma-to-chroma)</h4><ul class="n2n-list">${rows}</ul>`;
}

// 066: NetClaw Mobile edge nodes (node_type='edge' members) — connection
// state at a glance. Renders nothing on a pre-066 daemon or when no phone
// has ever enrolled.
function renderEdgeNodes() {
  const nodes = state.n2n?.edgeNodes || [];
  if (!nodes.length) return '';
  const stCls = (s) => (s === 'active' ? 'federated'
    : s === 'unreachable' ? 'not-federated' : 'consent-pending-local');
  const rows = nodes.slice(0, 8).map((n) => `<li>
      <span title="NetClaw Mobile edge node">📱</span>
      <strong class="n2n-state-${stCls(n.state)}">${n.state}</strong>
      <span class="n2n-muted">${n.display_name || n.member_id}</span>
      <span class="n2n-muted">· ${(n.updated_at || '').replace('T', ' ').replace('Z', '')}</span></li>`).join('');
  return `<h4>📱 NetClaw Mobile edge nodes (${nodes.length})</h4><ul class="n2n-list">${rows}</ul>`;
}

// 066: recent explicit Border-to-phone pushes (n2n_notify_phone). Renders
// nothing on a pre-066 daemon or when no push has ever been sent.
function renderRecentPushes() {
  const pushes = state.n2n?.recentPushes || [];
  if (!pushes.length) return '';
  const rows = pushes.slice(0, 8).map((p) => `<li>
      <strong>${p.target_name || 'text'}</strong>
      <span class="n2n-muted">→ ${p.peer_identity || ''}</span>
      <span class="n2n-muted">· ${(p.requested_at || '').replace('T', ' ').replace('Z', '')}</span></li>`).join('');
  return `<h4>Recent phone pushes</h4><ul class="n2n-list">${rows}</ul>`;
}

// 057: recent GAIT immutable audit events (delegation/enrollment/removal/quarantine).
function renderGaitTrail() {
  const events = state.n2n?.gait || [];
  if (!events.length) return '';
  const rows = events.slice(0, 8).map((e) => `<li>
      <strong>${e.event}</strong> <span class="n2n-muted">${e.subject || ''}</span>
      <span class="n2n-muted">· ${(e.ts || '').replace('T', ' ').replace('Z', '')}</span></li>`).join('');
  return `<h4>Audit trail (GAIT · immutable)</h4><ul class="n2n-list">${rows}</ul>`;
}

// 057: production posture badge — enforced (green) / degraded (amber, names the
// missing controls) / testing (grey). The Border NEVER shows enforced while a
// control is missing (FR-002). Renders nothing on a pre-057 daemon.
function renderPostureBadge() {
  const p = state.n2n?.posture;
  if (!p || !p.state) return '';
  const controls = (p.controls || [])
    .map((c) => `${c.available ? '✓' : '✗'} ${c.name}`).join(' · ');
  let cls = 'consent-pending-local', label = p.summary || p.state;
  if (p.state === 'enforced') cls = 'federated';
  else if (p.state === 'degraded') cls = 'not-federated';
  const model = p.model && p.model.primary
    ? `<div class="detail-row"><span>Model</span><strong>${p.model.primary}${p.model.guarded ? ' 🛡️' : ''}</strong></div>`
    : '';
  return `<div class="detail-row"><span>Posture</span>
      <strong class="n2n-state-${cls}">${label}</strong></div>
    <div class="detail-row"><span>Controls</span><span class="n2n-muted">${controls}</span></div>
    ${model}
    ${renderChannelSecurity()}`;
}

// 060: channel-security summary — trust models in use, degraded/legacy channels,
// and credentials aging into amber (<30d) / red (<14d). Renders nothing on a
// pre-060 daemon or when cert_mode is off.
function renderChannelSecurity() {
  const cs = state.n2n?.posture?.channel_security;
  if (!cs || !cs.mode || cs.mode === 'off') return '';
  const models = Object.entries(cs.by_trust_model || {})
    .map(([m, n]) => `${m}:${n}`).join(' · ') || 'none';
  const aging = [];
  if (cs.red) aging.push(`<span class="n2n-state-not-federated">${cs.red} red</span>`);
  if (cs.amber) aging.push(`<span class="consent-pending-local">${cs.amber} amber</span>`);
  if (cs.renewals_failing) aging.push(`${cs.renewals_failing} renewals failing`);
  const degraded = cs.degraded
    ? `<span class="n2n-state-not-federated">${cs.degraded} degraded/legacy</span>` : 'all secured';
  return `<div class="detail-row"><span>Channel security</span>
      <strong class="n2n-state-federated">🔒 ${cs.mode}</strong></div>
    <div class="detail-row"><span>Trust models</span><span class="n2n-muted">${models}</span></div>
    <div class="detail-row"><span>Channels</span><span class="n2n-muted">${degraded}</span></div>
    ${aging.length ? `<div class="detail-row"><span>Certs</span><span class="n2n-muted">${aging.join(' · ')}</span></div>` : ''}`;
}

// 057: a federated peer advertises its production posture + LLM capability in its
// A2A card — surface them so an operator sees a neighbour's security + model.
function renderPeerPostureLlm(inv) {
  let html = '';
  const p = inv.posture;
  if (p && p.state) {
    let cls = 'consent-pending-local';
    if (p.state === 'enforced') cls = 'federated';
    else if (p.state === 'degraded') cls = 'not-federated';
    html += `<div class="detail-row"><span>Peer posture</span>
      <strong class="n2n-state-${cls}">${p.summary || p.state}</strong></div>`;
  }
  const l = inv.llm;
  if (l && l.primary_model) {
    html += `<div class="detail-row"><span>Peer model</span>
      <strong>${l.primary_model}${l.guarded ? ' 🛡️' : ''}</strong></div>`;
  }
  return html;
}

function renderFederationSection(peer) {
  const fp = findFederationPeer(peer);
  if (!state.n2n?.available) {
    return `<div class="n2n-section"><h3>N2N Federation</h3>
      <p class="n2n-muted">Federation layer not enabled on this claw.</p></div>`;
  }
  if (!fp || fp.state !== 'federated') {
    const st = fp?.state || 'not federated';
    return `<div class="n2n-section"><h3>N2N Federation</h3>
      <div class="detail-row"><span>Status</span><strong class="n2n-state-${st.replace(/_/g,'-')}">${st.replace(/_/g,' ')}</strong></div>
      <p class="n2n-muted">Not federated — no capability inventory. Mutually consent to exchange skills &amp; tools.</p></div>`;
  }
  const inv = fp.inventory?.inventory || {};
  const badges = (inv.badges || []).map((b) => `<span class="n2n-badge">${b}</span>`).join('') || '<span class="n2n-muted">none</span>';
  const skills = (inv.skills || []).map((s) => `<li>${s.name}</li>`).join('') || '<li class="n2n-muted">none advertised</li>';
  const servers = (inv.mcp_servers || []).map((s) =>
    `<li>${s.name} <span class="n2n-muted">(${(s.tools || []).length} tools)</span></li>`).join('') || '<li class="n2n-muted">none advertised</li>';
  const fresh = fp.stale ? `<span class="n2n-stale">STALE</span>` : `<span class="n2n-fresh">fresh</span>`;
  const recv = fp.inventory_received_at || '—';
  // 053 US6: channel health + in-flight delegated tasks
  const chState = fp.channel_state || 'up';
  const chBadge = `<strong class="n2n-state-${chState === 'up' ? 'federated' : (chState === 'reconnecting' ? 'consent-pending-local' : 'not-federated')}">${chState}</strong>`;
  const tasks = fp.in_flight_tasks || [];
  const tasksHtml = tasks.length ? `
      <h4>In-flight tasks (${tasks.length})</h4>
      <ul class="n2n-list">${tasks.map((t) =>
        `<li>${t.target || t.task_id.slice(0, 8)} — <span class="n2n-fresh">${t.state}</span>${t.progress ? ` · ${t.progress}` : ''}</li>`).join('')}</ul>` : '';
  return `
    <div class="n2n-section n2n-federated">
      <h3>N2N Federation ${fresh}</h3>
      <div class="detail-row"><span>Status</span><strong class="n2n-state-federated">federated</strong></div>
      <div class="detail-row"><span>Channel</span>${chBadge}</div>
      <div class="detail-row"><span>Inventory</span><strong>v${inv.version ?? '—'} · ${recv}</strong></div>
      ${renderPeerPostureLlm(inv)}
      <div class="n2n-badges">${badges}</div>
      ${tasksHtml}
      <h4>Skills (${(inv.skills || []).length})</h4>
      <ul class="n2n-list">${skills}</ul>
      <h4>MCP Servers (${(inv.mcp_servers || []).length})</h4>
      <ul class="n2n-list">${servers}</ul>
      ${fp.chat_enabled ? `
        <h4>Claw-to-Claw Chat</h4>
        <div class="n2n-chat" id="n2n-chat-log"></div>
        <div class="n2n-chat-input">
          <input type="text" id="n2n-chat-text" placeholder="Ask ${fp.display_name || fp.identity}'s claw…" />
          <button id="n2n-chat-send">Send</button>
        </div>
      ` : `<p class="n2n-muted">Chat disabled for this peer.</p>`}
    </div>`;
}

function wireFederationChat(peer) {
  const fp = findFederationPeer(peer);
  if (!fp || fp.state !== 'federated' || !fp.chat_enabled) return;
  const btn = document.getElementById('n2n-chat-send');
  const input = document.getElementById('n2n-chat-text');
  const log = document.getElementById('n2n-chat-log');
  if (!btn || !input || !log) return;
  let sessionId = null;
  const send = async () => {
    const text = input.value.trim();
    if (!text) return;
    log.innerHTML += `<div class="n2n-msg n2n-me"><strong>you:</strong> ${text}</div>`;
    input.value = '';
    log.innerHTML += `<div class="n2n-msg n2n-pending" id="n2n-pending">…</div>`;
    log.scrollTop = log.scrollHeight;
    try {
      const r = await fetch('/api/n2n/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ peer: fp.identity, text, session_id: sessionId }),
      });
      const data = await r.json();
      sessionId = data.session_id || sessionId;
      document.getElementById('n2n-pending')?.remove();
      const reply = data.text || data.error || '(no response)';
      log.innerHTML += `<div class="n2n-msg n2n-peer"><strong>${fp.display_name || fp.identity}:</strong> ${reply}</div>`;
      log.scrollTop = log.scrollHeight;
    } catch (e) {
      document.getElementById('n2n-pending')?.remove();
      log.innerHTML += `<div class="n2n-msg n2n-err">error: ${e.message}</div>`;
    }
  };
  btn.addEventListener('click', send);
  input.addEventListener('keydown', (e) => { if (e.key === 'Enter') send(); });
}

/**
 * Scene-level stale-data indicator (feature 101, FR-042).
 *
 * Deliberately a banner rather than a per-node treatment: the peers are not
 * individually stale, our VIEW of all of them is. Marking each node would be the
 * very confusion FR-041 exists to prevent.
 */
function renderStaleBanner(ind) {
  let el = document.getElementById('feed-stale-banner');
  if (!ind.degraded) { el?.remove(); return; }
  if (!el) {
    el = document.createElement('div');
    el.id = 'feed-stale-banner';
    el.style.cssText = 'position:fixed;top:8px;left:50%;transform:translateX(-50%);'
      + 'z-index:9999;padding:6px 14px;border-radius:6px;font:12px/1.4 ui-monospace,monospace;'
      + 'background:rgba(120,80,20,.92);color:#ffe9c2;border:1px solid #d9a94a;'
      + 'pointer-events:none;letter-spacing:.04em';
    document.body.appendChild(el);
  }
  el.textContent = `⚠ ${ind.message}`
    + (ind.consecutiveFailures > 1 ? ` (${ind.consecutiveFailures} failed polls)` : '');
}

function setDetail(kind, payload, related = []) {
  if (kind === 'local-core') {
    dom.detailPanel.innerHTML = `
      <h2>This NetClaw</h2>
      <p>${state.n2n?.identity || 'local claw'}</p>
      ${renderRiskSection()}
      ${renderReplicationJobs()}
      ${renderEdgeNodes()}
      ${renderRecentPushes()}
    `;
    return;
  }

  if (kind === 'member-core') {
    const m = payload || {};
    const st = m.state || 'unknown';
    const stCls = m.live ? 'federated'
      : (st === 'quarantined' || st === 'removed') ? 'not-federated' : 'consent-pending-local';
    const skills = (m.skills || []).map((s) => `<li>${s}</li>`).join('')
      || '<li class="n2n-muted">—</li>';
    dom.detailPanel.innerHTML = `
      <h2>Member Claw</h2>
      <p>${m.member_id || '—'}</p>
      <div class="detail-grid">
        <div class="detail-row"><span>Risk</span><strong>${(state.n2n?.risk?.risk_name) || '—'}</strong></div>
        <div class="detail-row"><span>Profile</span><strong>${m.profile || '—'}</strong></div>
        <div class="detail-row"><span>State</span><strong class="n2n-state-${stCls}">${st}${m.live ? ' · live' : ''}</strong></div>
        <div class="detail-row"><span>Transport</span><strong>${m.transport_binding || '—'}</strong></div>
        <div class="detail-row"><span>Specialty skills</span><strong>${m.specialty_count ?? (m.skills || []).length}</strong></div>
      </div>
      <div class="n2n-section">
        <h4>Scope (${(m.skills || []).length})</h4>
        <ul class="n2n-list">${skills}</ul>
        <p class="n2n-muted">Delegated to over the internal transport; runs its own scoped model. No external comms.</p>
      </div>`;
    return;
  }

  if (kind === 'integration') {
    dom.detailPanel.innerHTML = `
      <h2>${payload.name}</h2>
      <p>${payload.description}</p>
      <div class="detail-grid">
        <div class="detail-row"><span>Category</span><strong>${payload.category}</strong></div>
        <div class="detail-row"><span>Transport</span><strong>${payload.transport}</strong></div>
        <div class="detail-row"><span>Skills</span><strong>${payload.skillCount}</strong></div>
        <div class="detail-row"><span>Tool Est.</span><strong>${payload.toolEstimate}</strong></div>
      </div>
      <div class="chip-wrap">
        ${related.slice(0, 18).map((skill) => `<span class="skill-chip">${skill.name}</span>`).join('')}
      </div>
      <div class="config-section" id="config-section">
        <h3>Configuration</h3>
        <div id="config-fields">Loading env vars...</div>
      </div>
    `;
    loadEnvConfig(payload.id);
    return;
  }

  if (kind === 'device') {
    dom.detailPanel.innerHTML = `
      <h2>${payload.name}</h2>
      <p>${payload.alias}</p>
      <div class="detail-grid">
        <div class="detail-row"><span>Type</span><strong>${payload.type}</strong></div>
        <div class="detail-row"><span>OS</span><strong>${payload.os}</strong></div>
        <div class="detail-row"><span>Platform</span><strong>${payload.platform}</strong></div>
        <div class="detail-row"><span>Endpoint</span><strong>${payload.protocol}:${payload.port}</strong></div>
        <div class="detail-row"><span>Address</span><strong>${payload.ip}</strong></div>
      </div>
      <div class="config-section">
        <h3>Testbed Config</h3>
        <p class="config-notes">Device defined in testbed/testbed.yaml. Edit the testbed to add/change devices, credentials, and connection settings.</p>
      </div>
    `;
    return;
  }

  if (kind === 'skill') {
    // Phase 1: Immediate render with available data
    dom.detailPanel.innerHTML = `
      <div class="skill-dashboard">
        <div class="skill-header">
          <h2>${payload.name}</h2>
          <p>${payload.description || 'Skill metadata loaded from the local workspace.'}</p>
        </div>
        <div class="detail-grid">
          <div class="detail-row"><span>Integration</span><strong>${payload.integrationId}</strong></div>
          <div class="detail-row"><span>Bins</span><strong>${payload.requiredBins.join(', ') || 'none'}</strong></div>
          <div class="detail-row"><span>Env</span><strong>${payload.requiredEnv.join(', ') || 'none'}</strong></div>
        </div>
        <div id="skill-full-content" class="skill-loading">
          <div class="skill-loading-text">Loading SKILL.md...</div>
        </div>
      </div>
    `;
    // Phase 2: Async fetch and render
    loadSkillDashboard(payload.id, payload.integrationId);
    return;
  }

  if (kind === 'peer-core') {
    const peer = payload;
    const entry = related;
    const isClaw = entry?.isClaw;
    const routes = peer.adjRibIn || [];
    const routeRows = routes.map((r) =>
      `<tr>
        <td>${r.prefix}</td>
        <td>${r.next_hop}</td>
        <td>${(r.as_path || []).join(' → ') || '—'}</td>
      </tr>`
    ).join('');

    dom.detailPanel.innerHTML = `
      <h2>${isClaw ? 'Peer Claw' : 'Peer Router'}</h2>
      <p>${peer.peer}</p>
      <div class="detail-grid">
        <div class="detail-row"><span>Type</span><strong>${isClaw ? 'NetClaw Mesh' : 'eBGP Router'}</strong></div>
        <div class="detail-row"><span>ASN</span><strong>${peer.as || '—'}</strong></div>
        <div class="detail-row"><span>Router ID</span><strong>${peer.routerId || '—'}</strong></div>
        <div class="detail-row"><span>State</span><strong class="bgp-state-${peer.state?.toLowerCase()}">${peer.state}</strong></div>
        <div class="detail-row"><span>Peer IP</span><strong>${peer.peerIp || '—'}</strong></div>
        <div class="detail-row"><span>Routes</span><strong>${peer.routesReceived}</strong></div>
      </div>
      ${isClaw ? renderFederationSection(peer) : ''}
      ${routes.length ? `
        <div class="bgp-routes-section">
          <h3>Adj-RIB-In</h3>
          <table class="bgp-route-table">
            <thead><tr><th>Prefix</th><th>Next Hop</th><th>AS Path</th></tr></thead>
            <tbody>${routeRows}</tbody>
          </table>
        </div>
      ` : ''}
    `;
    if (isClaw) wireFederationChat(peer);
    return;
  }

  // ── Feature 101 (US1): the eN2N peer inspector ──────────────────────────
  //
  // THE DEFECT THIS FIXES. The org-chart click path already passed
  // 'federation-peer' from two places (the pointer handler and the keyboard/a11y
  // handler), but no branch existed for it — so it fell past all six branches
  // into the default overview below and repainted the panel with the GENERIC
  // "This NetClaw" summary. The click registered, the panel repainted, and it
  // showed a different subject's content. That is why it read as "not clickable"
  // even though the mesh is pickable and hover-scales correctly.
  //
  // Deliberately NOT routed through 'peer-core': that branch expects a
  // /api/graph BGP-session payload (peer.as, routerId, peerIp, routesReceived,
  // adjRibIn) which is absent from the /api/n2n shape the org chart carries, so
  // reusing it would render a panel of undefineds. The /api/n2n shape is also
  // the richer one for federation.
  if (kind === 'federation-peer') {
    const nowEpochS = Math.floor(Date.now() / 1000);
    const v = peerDetailView(payload, nowEpochS, {
      label: payload?.__label,
      presentInFeed: payload?.__presentInFeed !== false,
    });

    const taskRows = v.inFlightTasks.map((t) => `
      <div class="detail-row"><span>${t.task_id || t.target_name || 'task'}</span>
        <strong>${t.state || '—'}${t.progress ? ` · ${t.progress}` : ''}</strong></div>
    `).join('');

    dom.detailPanel.innerHTML = `
      <h2>Peer Claw</h2>
      <p>${v.heading}</p>
      ${v.notInFeedNotice
        ? `<div class="n2n-state-not-federated" style="padding:6px 0">${v.notInFeedNotice}</div>`
        : ''}
      <div class="detail-grid">
        <div class="detail-row"><span>Identity</span><strong>${v.identity}</strong></div>
        <div class="detail-row"><span>State</span><strong class="n2n-state-${v.state.toLowerCase()}">${v.state}</strong></div>
        <div class="detail-row"><span>Meaning</span><strong>${v.stateSummary}</strong></div>
        <div class="detail-row"><span>Channel</span><strong>${v.channelState}</strong></div>
        <div class="detail-row"><span>Inventory</span><strong>${v.inventoryAge} · ${v.inventoryJudgement}</strong></div>
        <div class="detail-row"><span>Chat</span><strong>${v.chatText}</strong></div>
        <div class="detail-row"><span>In-flight tasks</span><strong>${v.inFlightText}</strong></div>
      </div>
      ${taskRows ? `<div class="detail-grid">${taskRows}</div>` : ''}
    `;
    return;
  }

  // FR-006: no kind may reach the default overview by accident.
  //
  // The silent fallthrough IS the bug fixed above — it renders a plausible panel
  // for the wrong subject, which is strictly worse than rendering nothing,
  // because the operator has no signal that anything went wrong. Anything not
  // explicitly handled is a programming error and must be loud, not plausible.
  if (kind !== undefined && kind !== null && kind !== 'overview') {
    const msg = `setDetail: unhandled kind '${kind}' — falling through to the generic
      overview would show another subject's content (feature 101 FR-006)`;
    if (import.meta?.env?.DEV) throw new Error(msg);
    console.error(msg);
  }

  // Default: overview with BGP summary if available
  const bgpSummary = state.bgp?.available ? `
    <div class="bgp-overview-section">
      <h3>BGP Topology</h3>
      <div class="detail-grid">
        <div class="detail-row"><span>Local AS</span><strong>${state.bgp.local.as}</strong></div>
        <div class="detail-row"><span>Router ID</span><strong>${state.bgp.local.routerId}</strong></div>
        <div class="detail-row"><span>Peers</span><strong>${state.bgp.peers.length}</strong></div>
        <div class="detail-row"><span>Loc-RIB</span><strong>${state.bgp.ribCount} routes</strong></div>
      </div>
    </div>
  ` : '';

  dom.detailPanel.innerHTML = `
    <h2>${state.graph.identity.name}</h2>
    <p>${state.graph.identity.summary}</p>
    <div class="detail-grid">
      <div class="detail-row"><span>Badge</span><strong>${state.graph.identity.badge}</strong></div>
      <div class="detail-row"><span>Integrations</span><strong>${state.graph.stats.integrationCount}</strong></div>
      <div class="detail-row"><span>Skills</span><strong>${state.graph.stats.skillCount}</strong></div>
      <div class="detail-row"><span>Devices</span><strong>${state.graph.stats.deviceCount}</strong></div>
    </div>
    ${bgpSummary}
  `;
}

// ── Config Editor: load env vars for an integration ────────────────
async function loadEnvConfig(integrationId) {
  const container = document.getElementById('config-fields');
  if (!container) return;

  try {
    const res = await fetch(`/api/env/${integrationId}`);
    if (!res.ok) {
      container.innerHTML = '<p class="config-notes">No env mapping for this integration.</p>';
      return;
    }
    const data = await res.json();

    if (data.fields.length === 0) {
      container.innerHTML = `<p class="config-notes">${data.notes}</p>`;
      return;
    }

    const testbedSection = (data.files && data.files.includes('testbed/testbed.yaml'))
      ? `<div class="testbed-section">
           <button class="config-save-btn testbed-toggle-btn" type="button" id="testbed-toggle">Edit Testbed YAML</button>
           <div id="testbed-editor" class="testbed-editor hidden">
             <textarea id="testbed-textarea" class="testbed-textarea" spellcheck="false">Loading...</textarea>
             <div class="config-save-row">
               <button class="config-save-btn" type="button" id="testbed-save">Save Testbed</button>
               <span class="config-save-status" id="testbed-save-status">Saved</span>
             </div>
           </div>
         </div>`
      : '';

    container.innerHTML = data.fields.map((field) => `
      <div class="config-field">
        <label>${field.key}</label>
        <input class="env-input" data-key="${field.key}" type="text"
               placeholder="${field.isSet ? field.masked : 'not set'}"
               value="" />
        <span class="env-status ${field.isSet ? 'set' : 'unset'}">${field.isSet ? 'configured' : 'not set'}</span>
      </div>
    `).join('') + `
      <p class="config-notes">${data.notes}</p>
      ${testbedSection}
      <div class="config-save-row">
        <button class="config-save-btn" type="button" id="config-save">Save Changes</button>
        <span class="config-save-status" id="config-save-status">Saved</span>
      </div>
    `;

    // Wire testbed editor toggle + save
    const testbedToggle = document.getElementById('testbed-toggle');
    if (testbedToggle) {
      testbedToggle.addEventListener('click', async () => {
        const editor = document.getElementById('testbed-editor');
        const textarea = document.getElementById('testbed-textarea');
        editor.classList.toggle('hidden');
        if (!editor.classList.contains('hidden') && textarea.value === 'Loading...') {
          try {
            const tbRes = await fetch('/api/testbed/raw');
            textarea.value = await tbRes.text();
          } catch { textarea.value = '# Could not load testbed'; }
        }
      });

      document.getElementById('testbed-save')?.addEventListener('click', async () => {
        const textarea = document.getElementById('testbed-textarea');
        const statusEl = document.getElementById('testbed-save-status');
        try {
          const tbSaveRes = await fetch('/api/testbed/raw', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: textarea.value }),
          });
          if (tbSaveRes.ok) {
            statusEl.classList.add('show');
            setTimeout(() => statusEl.classList.remove('show'), 2500);
          } else {
            const err = await tbSaveRes.json();
            statusEl.textContent = err.error || 'Save failed';
            statusEl.classList.add('show', 'error');
            setTimeout(() => { statusEl.classList.remove('show', 'error'); statusEl.textContent = 'Saved'; }, 4000);
          }
        } catch { /* save failed */ }
      });
    }

    document.getElementById('config-save')?.addEventListener('click', async () => {
      const inputs = container.querySelectorAll('.env-input');
      const updates = {};
      inputs.forEach((input) => {
        if (input.value.trim()) {
          updates[input.dataset.key] = input.value.trim();
        }
      });

      if (Object.keys(updates).length === 0) return;

      try {
        const saveRes = await fetch('/api/env', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ updates }),
        });
        if (saveRes.ok) {
          const statusEl = document.getElementById('config-save-status');
          statusEl.classList.add('show');
          // Update status indicators
          inputs.forEach((input) => {
            if (input.value.trim()) {
              const statusSpan = input.parentElement.querySelector('.env-status');
              statusSpan.textContent = 'configured';
              statusSpan.className = 'env-status set';
              input.placeholder = input.value.slice(0, 3) + '****';
              input.value = '';
            }
          });
          setTimeout(() => statusEl.classList.remove('show'), 2500);
        }
      } catch { /* save failed silently */ }
    });
  } catch {
    container.innerHTML = '<p class="config-notes">Could not load config.</p>';
  }
}

// ── Rich Skill Dashboard (Part E) ──────────────────────────────────
function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

async function loadSkillDashboard(skillId, integrationId) {
  const container = document.getElementById('skill-full-content');
  if (!container) return;

  try {
    const res = await fetch(`/api/skill/${skillId}`);
    if (!res.ok) {
      container.innerHTML = '<p class="config-notes">No SKILL.md found for this skill.</p>';
      return;
    }
    const data = await res.json();
    renderSkillDashboard(container, data, integrationId);
  } catch {
    container.innerHTML = '<p class="config-notes">Could not load skill details.</p>';
  }
}

function renderSkillDashboard(container, data, integrationId) {
  const fm = data.frontmatter || {};
  const version = fm.version || '';
  const tags = fm.tags || [];
  const bins = fm.metadata?.openclaw?.requires?.bins || [];
  const env = fm.metadata?.openclaw?.requires?.env || [];

  let html = '';

  // Version + tags row
  if (version || tags.length > 0) {
    html += '<div class="skill-meta-row">';
    if (version) html += `<span class="skill-version">v${version}</span>`;
    tags.forEach((tag) => { html += `<span class="skill-tag">${escapeHtml(tag)}</span>`; });
    html += '</div>';
  }

  // Requirements section
  if (bins.length > 0 || env.length > 0) {
    html += '<div class="skill-requirements"><h3>Requirements</h3>';
    if (bins.length > 0) {
      html += '<div class="req-group"><span class="req-label">Bins</span>';
      bins.forEach((b) => { html += `<span class="req-chip bin">${escapeHtml(b)}</span>`; });
      html += '</div>';
    }
    if (env.length > 0) {
      html += '<div class="req-group"><span class="req-label">Env</span>';
      env.forEach((e) => { html += `<span class="req-chip env">${escapeHtml(e)}</span>`; });
      html += '</div>';
    }
    html += '</div>';
  }

  // Parsed sections from SKILL.md body
  data.sections.forEach((section) => {
    html += `<div class="skill-section"><h3>${escapeHtml(section.title)}</h3>`;

    if (section.text) {
      html += `<div class="skill-text">${escapeHtml(section.text)}</div>`;
    }

    section.tables.forEach((table) => {
      html += '<div class="skill-table-wrap"><table class="skill-table"><thead><tr>';
      table.headers.forEach((h) => { html += `<th>${escapeHtml(h)}</th>`; });
      html += '</tr></thead><tbody>';
      table.rows.forEach((row) => {
        html += '<tr>';
        row.forEach((cell) => { html += `<td>${escapeHtml(cell)}</td>`; });
        html += '</tr>';
      });
      html += '</tbody></table></div>';
    });

    section.codeBlocks.forEach((block) => {
      html += `<pre class="skill-code"><code>${escapeHtml(block.code)}</code></pre>`;
    });

    (section.subSections || []).forEach((sub) => {
      html += `<div class="skill-subsection"><h4>${escapeHtml(sub.title)}</h4>`;
      if (sub.text) html += `<div class="skill-text">${escapeHtml(sub.text)}</div>`;
      sub.tables.forEach((table) => {
        html += '<div class="skill-table-wrap"><table class="skill-table"><thead><tr>';
        table.headers.forEach((h) => { html += `<th>${escapeHtml(h)}</th>`; });
        html += '</tr></thead><tbody>';
        table.rows.forEach((row) => {
          html += '<tr>';
          row.forEach((cell) => { html += `<td>${escapeHtml(cell)}</td>`; });
          html += '</tr>';
        });
        html += '</tbody></table></div>';
      });
      sub.codeBlocks.forEach((block) => {
        html += `<pre class="skill-code"><code>${escapeHtml(block.code)}</code></pre>`;
      });
      html += '</div>';
    });

    html += '</div>';
  });

  // Raw markdown toggle
  html += `
    <div class="skill-raw-toggle">
      <button class="config-save-btn" type="button" id="raw-md-toggle">View Raw Markdown</button>
      <pre class="skill-raw-md hidden" id="raw-md-content">${escapeHtml(data.rawMarkdown)}</pre>
    </div>
  `;

  // Env config section
  if (env.length > 0) {
    html += `
      <div class="config-section" id="config-section">
        <h3>Configuration</h3>
        <div id="config-fields">Loading env vars...</div>
      </div>
    `;
  }

  container.innerHTML = html;
  container.classList.remove('skill-loading');

  // Wire the raw markdown toggle
  document.getElementById('raw-md-toggle')?.addEventListener('click', () => {
    const pre = document.getElementById('raw-md-content');
    if (!pre) return;
    pre.classList.toggle('hidden');
    document.getElementById('raw-md-toggle').textContent =
      pre.classList.contains('hidden') ? 'View Raw Markdown' : 'Hide Raw Markdown';
  });

  // Load env config if applicable
  if (env.length > 0) {
    loadEnvConfig(integrationId);
  }
}

// ── Chat System ────────────────────────────────────────────────────
function addChatMessage(role, text, activations) {
  const msg = document.createElement('div');
  msg.className = `chat-msg ${role}`;

  if (role === 'assistant') {
    let header = '';
    if (activations) {
      const tags = activations.integrations.map((id) => {
        const name = state.graph.integrations.find((i) => i.id === id)?.name || id;
        return `<span class="routing-tag">${name}</span>`;
      });
      const deviceTags = activations.devices.map((id) => {
        const name = state.graph.devices.find((d) => d.id === id)?.name || id;
        return `<span class="routing-tag device">${name}</span>`;
      });
      header = `<div style="margin-bottom:6px">${[...tags, ...deviceTags].join(' ')}</div>`;
    }
    msg.innerHTML = header + text;
  } else {
    msg.textContent = text;
  }

  dom.chatMessages.appendChild(msg);
  dom.chatMessages.scrollTop = dom.chatMessages.scrollHeight;
}

async function checkGatewayStatus() {
  try {
    const res = await fetch('/api/gateway/status');
    const data = await res.json();
    const el = dom.gatewayStatus;
    if (el) {
      if (data.online) {
        el.textContent = 'LIVE';
        el.className = 'gateway-indicator online';
        el.title = 'OpenClaw gateway and chat-completions endpoint are ready';
      } else if (data.reason === 'chat-completions-disabled') {
        el.textContent = 'CHAT API DISABLED';
        el.className = 'gateway-indicator offline';
        el.title = 'Enable gateway.http.endpoints.chatCompletions.enabled and restart OpenClaw';
      } else {
        el.textContent = 'OFFLINE';
        el.className = 'gateway-indicator offline';
        el.title = 'OpenClaw gateway is not reachable';
      }
    }
  } catch {
    if (dom.gatewayStatus) {
      dom.gatewayStatus.textContent = 'OFFLINE';
      dom.gatewayStatus.className = 'gateway-indicator offline';
      dom.gatewayStatus.title = 'OpenClaw gateway status could not be checked';
    }
  }
}

async function sendChatMessage(message) {
  addChatMessage('user', message);
  dom.chatInput.value = '';

  // Enter focus mode on first send (dims scene, highlights core)
  if (!state.chatSession.active) {
    enterChatFocus();
  }

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    const badge = data.fromGateway
      ? '<span class="chat-badge live">LIVE</span>'
      : '<span class="chat-badge heuristic">LOCAL</span>';
    const warning = !data.fromGateway
      ? '<div style="margin-bottom:4px;font-size:10px;color:#ff7b54">Gateway offline — showing local heuristic response</div>'
      : '';
    addChatMessage('assistant', badge + warning + data.response, data.activations);

    // Trigger activation visualization from HTTP response
    if (data.activations) {
      state._httpActivationPending = true;
      handleActivations(data.activations);
    }
  } catch (err) {
    addChatMessage('assistant', `Error: ${err.message}`);
  }
}

// ── 3D Activation Effects ──────────────────────────────────────────
function initBeamPool() {
  for (let i = 0; i < BEAM_POOL_SIZE; i++) {
    const geo = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(0, 0, 0),
      new THREE.Vector3(0, 0, 0),
    ]);
    const mat = new THREE.LineBasicMaterial({
      color: 0x65c3ff,
      transparent: true,
      opacity: 0,
    });
    const beam = new THREE.Line(geo, mat);
    beam.visible = false;
    state.scene.add(beam);
    activationBeams.push(beam);
  }
}

function fireActivationBeam(targetPosition, color) {
  const beam = activationBeams.find((b) => !b.visible);
  if (!beam) return;

  const positions = beam.geometry.attributes.position.array;
  const origin = state.localCore ? state.localCore.position : new THREE.Vector3(0, 0, 0);
  positions[0] = origin.x; positions[1] = origin.y; positions[2] = origin.z;
  positions[3] = targetPosition.x;
  positions[4] = targetPosition.y;
  positions[5] = targetPosition.z;
  beam.geometry.attributes.position.needsUpdate = true;
  beam.material.color.set(color);
  beam.material.opacity = 0.9;
  beam.visible = true;

  gsap.to(beam.material, {
    opacity: 0,
    duration: 1.8,
    ease: 'power2.out',
    onComplete: () => { beam.visible = false; },
  });
}

function activateIntegration(integrationId) {
  const entry = state.integrations.find((e) => e.payload.id === integrationId);
  if (!entry || !entry.group.visible) return;

  // Phase 1: Trace the tube from core → node (slow brightening)
  gsap.fromTo(entry.tubeMat.uniforms.uOpacity,
    { value: 0.04 },
    { value: 1.0, duration: 0.8, ease: 'power2.out' },
  );

  // Phase 2: After tube reaches, light up the node (delayed)
  gsap.to(entry.node.material.uniforms.uBrightness, {
    value: 2.5,
    delay: 0.8,
    duration: 0.5,
    ease: 'power2.out',
  });

  // Halo flare on arrival
  gsap.to(entry.halo.material, {
    opacity: 1.0,
    delay: 0.8,
    duration: 0.4,
    ease: 'power2.out',
  });

  // Scale burst on arrival
  gsap.fromTo(entry.group.scale,
    { x: 1, y: 1, z: 1 },
    { x: 1.5, y: 1.5, z: 1.5, delay: 0.8, duration: 0.4, yoyo: true, repeat: 1, ease: 'back.out(2)' },
  );

  // Fire beam from core to node
  fireActivationBeam(entry.basePosition, entry.payload.color);

  // Phase 3: After node lights up, trace dendrite wires out to each leaf skill
  // Delay so the user sees: core → tube → node → THEN wires grow → skills pop
  setTimeout(() => {
    revealSkills(entry);
  }, 1400);

  // Phase 4: Pulse each leaf skill sequentially after wires reach them
  const leafDelay = 1400; // after wire grow starts
  entry.skillSprites.forEach((sprite, i) => {
    const arrivalTime = leafDelay + i * 40 + 600; // wire grow (0.6s) + stagger
    setTimeout(() => {
      if (sprite.mesh.visible && sprite.mesh.material) {
        // Flash bright on arrival — scale pop + opacity flash
        gsap.to(sprite.mesh.material, {
          opacity: 1.0,
          duration: 0.3,
          ease: 'power2.out',
          onComplete: () => {
            gsap.to(sprite.mesh.material, { opacity: 0.66, duration: 0.5 });
          },
        });
        gsap.fromTo(sprite.mesh.scale,
          { x: 1, y: 1, z: 1 },
          { x: 2.2, y: 2.2, z: 2.2, duration: 0.25, yoyo: true, repeat: 1, ease: 'back.out(3)' },
        );
      }
    }, arrivalTime);
  });

  // Hide skills + wires after full trace animation completes (only outside chat session)
  if (!state.chatSession.active) {
    const totalLeafTime = 1400 + (entry.skillSprites.length * 40) + 600 + 2000;
    setTimeout(() => {
      if (state.selected?.kind !== 'integration' || state.selected?.id !== integrationId) {
        entry.skillSprites.forEach((sprite) => {
          sprite.mesh.visible = false;
          sprite.label.visible = false;
          if (sprite.wire) sprite.wire.visible = false;
        });
      }
    }, totalLeafTime);
  }
}

function activateDevice(deviceId) {
  const entry = state.devices.find((e) => e.payload.id === deviceId);
  if (!entry || !entry.mesh.visible) return;

  gsap.to(entry.mesh.material, {
    emissiveIntensity: 2.0,
    duration: 0.3,
    yoyo: true,
    repeat: 3,
    ease: 'power2.inOut',
    onComplete: () => { entry.mesh.material.emissiveIntensity = 0.55; },
  });

  gsap.fromTo(entry.mesh.scale,
    { x: 1, y: 1, z: 1 },
    { x: 1.6, y: 1.6, z: 1.6, duration: 0.3, yoyo: true, repeat: 1, ease: 'back.out(2)' }
  );

  fireActivationBeam(entry.basePosition, 0x68f5b2);
}

function handleActivations(activations) {
  // Trigger post-processing effects + cinematic burst for quality modes
  triggerActivationEffects();
  enableCinematicBurst();

  // Enter chat focus mode if not already active — dims the whole scene
  if (!state.chatSession.active) {
    enterChatFocus();
  }

  // Sequential integration activation — each one lights up in order and stays lit
  const stagger = 2600;
  activations.integrations.forEach((id, i) => {
    setTimeout(() => lightIntegration(id), 600 + i * stagger);
  });

  // Activate devices after integrations
  const devicesStart = 600 + activations.integrations.length * stagger;
  activations.devices.forEach((id, i) => {
    setTimeout(() => lightDevice(id), devicesStart + i * 400);
  });
}

// ── Specific tool call highlighting (Section H) ─────────────────
function handleToolCall(payload) {
  const { tool, integration, output } = payload;
  const entry = state.integrations.find((e) => e.payload.id === integration);
  if (!entry || !entry.group.visible) return;

  // Find the specific skill sprite matching this tool name
  const matchedSprite = entry.skillSprites.find((sprite) => {
    const skillId = sprite.payload.id || '';
    const toolNorm = tool.replace(/_/g, '-');
    return skillId === toolNorm || skillId === tool || skillId.includes(toolNorm) || toolNorm.includes(skillId);
  });

  if (matchedSprite) {
    // Track this tool in the session
    state.chatSession.litTools.set(tool, { integrationId: integration });
    // Ensure integration is also tracked as lit
    state.chatSession.litIntegrations.add(integration);

    // Show full dendrite tree for this integration
    revealSkills(entry);

    // Highlight matched skill's dendrite wire
    if (matchedSprite.wireMat) {
      gsap.to(matchedSprite.wireMat.uniforms.uOpacity, {
        value: 1.0, duration: 0.3, yoyo: true, repeat: 3,
        ease: 'power2.inOut',
        onComplete: () => { matchedSprite.wireMat.uniforms.uOpacity.value = 0.35; },
      });
    }

    // Scale burst + glow on the matched skill
    gsap.fromTo(matchedSprite.mesh.scale,
      { x: 1, y: 1, z: 1 },
      { x: 2.5, y: 2.5, z: 2.5, duration: 0.4, ease: 'back.out(3)' }
    );
    gsap.to(matchedSprite.mesh.material, {
      opacity: 1.0,
      duration: 0.3,
      yoyo: true,
      repeat: 3,
      ease: 'power2.inOut',
      onComplete: () => {
        matchedSprite.mesh.material.opacity = 0.66;
        gsap.to(matchedSprite.mesh.scale, { x: 1, y: 1, z: 1, duration: 0.5 });
      },
    });

    // Only hide after delay if NOT in a chat session (session keeps skills persistent)
    if (!state.chatSession.active) {
      setTimeout(() => {
        if (state.selected?.kind !== 'integration' || state.selected?.id !== integration) {
          entry.skillSprites.forEach((sprite) => {
            sprite.mesh.visible = false;
            sprite.label.visible = false;
            if (sprite.wire) sprite.wire.visible = false;
          });
        }
      }, 5000);
    }
  }

  // Integration node pulse
  gsap.to(entry.node.material.uniforms?.uTime || {}, {});
  gsap.fromTo(entry.group.scale,
    { x: 1, y: 1, z: 1 },
    { x: 1.3, y: 1.3, z: 1.3, duration: 0.25, yoyo: true, repeat: 1, ease: 'back.out(2)' }
  );

  // Tube flare
  if (entry.tubeMat) {
    gsap.to(entry.tubeMat.uniforms.uOpacity, {
      value: 0.9,
      duration: 0.3,
      yoyo: true,
      repeat: 1,
      ease: 'power2.inOut',
      onComplete: () => { entry.tubeMat.uniforms.uOpacity.value = 0.25; },
    });
  }

  // Fire beam
  fireActivationBeam(entry.basePosition, entry.payload.color);

  // Show floating terminal card with output
  if (output || tool) {
    showTerminalCard(tool, output, integration);
  }
}

function focusTarget(target) {
  const point = target.clone();
  gsap.to(state.controls.target, {
    x: point.x,
    y: point.y,
    z: point.z,
    duration: 1,
    ease: 'power2.out',
  });
  gsap.to(state.camera.position, {
    x: point.x + 8,
    y: point.y + 6,
    z: point.z + 10,
    duration: 1,
    ease: 'power2.out',
  });
}

function clearSelection() {
  // Restore trace path highlights if previous selection was a skill
  if (state.selected?.kind === 'skill') {
    restoreTracePath();
  }
  state.selected = null;
  // Feature 101 (FR-008): selection is a scene channel now, so clearing the
  // selection must clear it there too — otherwise the ring is left orphaned
  // on a node the panel no longer describes.
  clearSelectedNode();
  setDetail('overview');
  state.integrations.forEach((entry) => {
    entry.node.material.uniforms.uBrightness.value = 1.0;
    entry.halo.material.opacity = 0.26;
    entry.tubeMat.uniforms.uOpacity.value = 0.25;
    entry.skillSprites.forEach((sprite) => {
      sprite.mesh.visible = false;
      sprite.label.visible = false;
      if (sprite.wire) sprite.wire.visible = false;
      sprite.mesh.material.color.set(entry.payload.color);
      sprite.mesh.material.opacity = 0.66;
      sprite.mesh.scale.setScalar(1);
    });
  });
  state.devices.forEach((entry) => {
    entry.mesh.material.emissiveIntensity = 0.55;
  });
  // Reset peer cores
  state.peerCores.forEach((core) => {
    core.nucleus.material.emissiveIntensity = 0.9;
    if (core.routeDendrites) {
      core.routeDendrites.forEach((rd) => { rd.label.visible = false; });
    }
  });
}

// ── Trace path highlighting (Part D) ────────────────────────────────
function highlightTracePath(entry, skillId) {
  // Dim all other integrations
  state.integrations.forEach((other) => {
    if (other === entry) return;
    gsap.to(other.tubeMat.uniforms.uOpacity, { value: 0.06, duration: 0.4 });
    gsap.to(other.node.material.uniforms.uBrightness, { value: 0.25, duration: 0.4 });
    gsap.to(other.halo.material, { opacity: 0.05, duration: 0.4 });
  });

  // 1. Core pulse
  if (state.localCore) {
    gsap.to(state.localCore.nucleus.material, { emissiveIntensity: 2.0, duration: 0.5, ease: 'power2.out' });
    gsap.to(state.localCore.torus.material, { opacity: 0.8, duration: 0.3 });
  }

  // 2. Core→Integration tube: brighten
  gsap.to(entry.tubeMat.uniforms.uOpacity, { value: 0.9, duration: 0.4, ease: 'power2.out' });

  // 3. Dendrite wires: brighten selected, dim others
  const matchedSprite = entry.skillSprites.find((s) => s.payload.id === skillId);
  entry.skillSprites.forEach((sprite) => {
    if (sprite.payload.id === skillId && sprite.wireMat) {
      gsap.to(sprite.wireMat.uniforms.uOpacity, { value: 1.0, duration: 0.3 });
    } else if (sprite.wireMat) {
      gsap.to(sprite.wireMat.uniforms.uOpacity, { value: 0.08, duration: 0.3 });
    }
  });

  // 4. Skill leaf: scale up and glow cyan
  if (matchedSprite) {
    gsap.to(matchedSprite.mesh.scale, { x: 2.0, y: 2.0, z: 2.0, duration: 0.4, ease: 'back.out(2)' });
    matchedSprite.mesh.material.color.set(0x00ffff);
    matchedSprite.mesh.material.opacity = 1.0;
  }
}

function restoreTracePath() {
  if (state.localCore) {
    gsap.to(state.localCore.nucleus.material, { emissiveIntensity: 0.9, duration: 0.5 });
    gsap.to(state.localCore.torus.material, { opacity: 0.36, duration: 0.3 });
  }
  state.integrations.forEach((entry) => {
    gsap.to(entry.tubeMat.uniforms.uOpacity, { value: 0.25, duration: 0.4 });
    gsap.to(entry.node.material.uniforms.uBrightness, { value: 1.0, duration: 0.4 });
    gsap.to(entry.halo.material, { opacity: 0.26, duration: 0.4 });
    entry.skillSprites.forEach((sprite) => {
      sprite.mesh.material.color.set(entry.payload.color);
      sprite.mesh.material.opacity = 0.66;
      gsap.to(sprite.mesh.scale, { x: 1, y: 1, z: 1, duration: 0.3 });
      if (sprite.wireMat) {
        gsap.to(sprite.wireMat.uniforms.uOpacity, { value: 0.35, duration: 0.3 });
      }
    });
  });
}

function selectObject(hit) {
  clearSelection();
  if (!hit) return;

  const { type, payload } = hit.userData;
  if (type === 'integration') {
    const entry = state.integrations.find((item) => item.payload.id === payload.id);
    if (!entry) return;
    entry.node.material.uniforms.uBrightness.value = 1.5;
    entry.halo.material.opacity = 0.78;
    revealSkills(entry);
    focusTarget(entry.basePosition);
    setDetail('integration', payload, entry.skills);
    state.selected = { kind: 'integration', id: payload.id };
    return;
  }

  if (type === 'device') {
    const entry = state.devices.find((item) => item.payload.id === payload.id);
    if (!entry) return;
    entry.mesh.material.emissiveIntensity = 1.1;
    focusTarget(entry.basePosition);
    setDetail('device', payload);
    state.selected = { kind: 'device', id: payload.id };
    return;
  }

  if (type === 'skill') {
    // Find the parent integration for this skill
    const parentEntry = state.integrations.find(
      (e) => e.skillSprites.some((s) => s.payload.id === payload.id),
    );
    if (parentEntry) {
      parentEntry.node.material.uniforms.uBrightness.value = 1.5;
      parentEntry.halo.material.opacity = 0.78;
      revealSkills(parentEntry);
      state.selected = { kind: 'skill', id: payload.id, integrationId: parentEntry.payload.id };
      highlightTracePath(parentEntry, payload.id);

      // Focus camera on the skill position
      const matchedSprite = parentEntry.skillSprites.find((s) => s.payload.id === payload.id);
      if (matchedSprite) {
        const targetPos = parentEntry.basePosition.clone().add(matchedSprite.localPosition);
        focusTarget(targetPos);
      }
    }
    setDetail('skill', payload);
    return;
  }

}

function getInteractiveObjects() {
  const nodes = [];
  state.integrations.forEach((entry) => {
    if (entry.group.visible) nodes.push(entry.node);
  });
  state.devices.forEach((entry) => {
    if (entry.mesh.visible) nodes.push(entry.mesh);
  });
  state.skillSprites.forEach((sprite) => {
    if (sprite.mesh.visible) nodes.push(sprite.mesh);
  });
  state.cores.forEach((core) => nodes.push(core.nucleus));
  return nodes;
}

function onPointerMove(event) {
  state.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
  state.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

  state.raycaster.setFromCamera(state.mouse, state.camera);
  const hit = state.raycaster.intersectObjects(getInteractiveObjects())[0];
  if (!hit) {
    dom.tooltip.classList.remove('visible');
    document.body.style.cursor = 'default';
    if (state.hovered) {
      state.hovered.scale.setScalar(1);
      state.hovered = null;
    }
    return;
  }

  const { userData } = hit.object;
  let title = userData.payload?.name || 'NetClaw Core';
  let subtitle = userData.payload?.description || userData.payload?.ip || 'Core runtime';
  // Check if this is a core nucleus (local or peer)
  const hoveredCore = state.cores.find((c) => c.nucleus === hit.object);
  if (hoveredCore) {
    if (hoveredCore === state.localCore) {
      title = 'NetClaw (Local)';
      subtitle = `AS ${state.bgp?.local?.as || '?'} • ${state.bgp?.peers?.length || 0} peers`;
    } else if (hoveredCore.peerPayload) {
      const p = hoveredCore.peerPayload;
      title = hoveredCore.isClaw ? `NetClaw AS${p.as}` : `Router ${p.routerId || p.peer}`;
      subtitle = `${p.state} • ${p.routesReceived} routes`;
    }
  }
  dom.tooltip.innerHTML = `<strong>${title}</strong><br>${subtitle}`;
  dom.tooltip.style.left = `${event.clientX + 18}px`;
  dom.tooltip.style.top = `${event.clientY + 18}px`;
  dom.tooltip.classList.add('visible');
  document.body.style.cursor = 'pointer';

  if (state.hovered && state.hovered !== hit.object) state.hovered.scale.setScalar(1);
  state.hovered = hit.object;
  state.hovered.scale.setScalar(1.22);
}

function onClick(event) {
  if (event.target.closest('.panel') || event.target.closest('.tooltip') || event.target.closest('.panel-reopen')) return;
  state.raycaster.setFromCamera(state.mouse, state.camera);

  // ── HUD 2.0 picking (feature 072) ────────────────────────────────────
  // One click both selects (right-hand panel, contract unchanged) and reveals
  // the claw's tools. The original FR-020a split click from expand; after
  // seeing the MVP the operator asked for a single gesture, and expansion is
  // an overlay so FR-022 still holds — no sibling ever moves.
  const chartHit = state.raycaster.intersectObjects(pickableObjects(), false)[0];
  if (chartHit) {
    const node = activateNode(chartHit.object, makeLabel);
    if (node) {
      clearSelection();
      // Feature 101 (US2): channel 5. Set AFTER clearSelection, which clears it.
      setSelectedNode(node.id);
      if (node.kind === 'border') {
        setDetail('local-core');
        state.selected = { kind: 'local-core' };
      } else if (node.kind === 'peer') {
        // Pass the layout node's label: disambiguation is a whole-list operation
        // (two peers legitimately share "Hermes") and normalize.js already did it.
        setDetail('federation-peer', { ...node.payload, __label: node.label });
        state.selected = { kind: 'federation-peer', peer: node.id };
      } else {
        setDetail('member-core', node.payload);
        state.selected = { kind: 'member-core', member: node.id };
      }
      return;
    }
  }

  const hit = state.raycaster.intersectObjects(getInteractiveObjects())[0];
  if (!hit) {
    clearSelection();
    return;
  }

  // Check if any core nucleus was clicked
  const hitCore = state.cores.find((c) => c.nucleus === hit.object);
  if (hitCore) {
    if (hitCore === state.localCore) {
      clearSelection();
      focusTarget(state.localCore.position.clone());
      setDetail('local-core');            // 056: show this claw's risk view (role + member spokes)
      state.selected = { kind: 'local-core' };
    } else if (hitCore.isMember) {
      // 056: member claw selected — focus it and show its detail
      clearSelection();
      hitCore.nucleus.material.emissiveIntensity = 1.8;
      focusTarget(hitCore.position.clone());
      setDetail('member-core', hitCore.memberPayload);
      state.selected = { kind: 'member-core', member: hitCore.memberPayload?.member_id };
    } else {
      // Peer core selected — show detail
      clearSelection();
      hitCore.nucleus.material.emissiveIntensity = 1.8;
      if (hitCore.routeDendrites) {
        hitCore.routeDendrites.forEach((rd) => { rd.label.visible = true; });
      }
      focusTarget(hitCore.position.clone());
      setDetail('peer-core', hitCore.peerPayload, hitCore);
      state.selected = { kind: 'peer-core', peer: hitCore.peerPayload?.peer };
    }
    return;
  }

  selectObject(hit.object);
}

function animate() {
  requestAnimationFrame(animate);
  const elapsed = state.clock.getElapsedTime();
  const frozen = !!state.selected;

  // HUD 2.0 node pulses. Motion is a redundant channel (R8) — the four health
  // states are already separable by form and colour — so honouring reduced
  // motion simply skips it without weakening the encoding.
  tickOrgChart(elapsed, state.camera);

  // Track time offset for freeze: when frozen, hold rotations at the moment of freeze
  if (frozen && state._frozenAt == null) state._frozenAt = elapsed;
  if (!frozen) state._frozenAt = null;
  const rotTime = frozen ? state._frozenAt : elapsed;

  // Orbit core animation removed with the orbit layout (FR-027). HUD 2.0's
  // node motion is driven by tickOrgChart() above; state.cores is no longer
  // populated, so nothing here had anything left to move.
  const coresMovedThisFrame = false;

  // Update peer-link ribbons in-place when cores move (no alloc, no dispose)
  if (coresMovedThisFrame && state.peerLinks.length > 0) {
    let linkIdx = 0;
    for (let a = 0; a < state.cores.length; a++) {
      for (let b = a + 1; b < state.cores.length; b++) {
        if (linkIdx >= state.peerLinks.length) break;
        const link = state.peerLinks[linkIdx];
        const posA = state.cores[a].position;
        const posB = state.cores[b].position;
        _v0.copy(posA);
        _v1.set((posA.x + posB.x) * 0.5, Math.max(posA.y, posB.y) + 3.0, (posA.z + posB.z) * 0.5);
        _v2.copy(posB);
        updateRibbonGeometry(link.tube.geometry, _v0, _v1, _v2);
        linkIdx++;
      }
    }
  }

  // Animate peer-link tubes
  state.peerLinks.forEach((link) => {
    if (link.mat.uniforms?.uTime) link.mat.uniforms.uTime.value = elapsed;
  });

  const coreAnchor = state.localCore ? state.localCore.position : _v3.set(0, 0, 0);

  state.integrations.forEach((entry, index) => {
    if (!entry.group.visible) return;
    const offset = index * 0.27;
    const orb = entry.orbit;

    // Orbit: advance theta when not frozen
    if (!frozen && orb) {
      orb.theta0 += orb.orbitSpeed;
      orb.phi0 += orb.axisTilt * 0.0004;
      orb.phi0 = Math.max(0.15, Math.min(Math.PI - 0.15, orb.phi0));

      entry.group.position.set(
        coreAnchor.x + orb.radius * Math.sin(orb.phi0) * Math.cos(orb.theta0),
        orb.radius * Math.cos(orb.phi0),
        coreAnchor.z + orb.radius * Math.sin(orb.phi0) * Math.sin(orb.theta0),
      );
      entry.basePosition.copy(entry.group.position);

      // Update ribbon geometry in-place (no alloc, no dispose)
      const gp = entry.group.position;
      const midY = Math.max(gp.y, coreAnchor.y) + 4.5;
      _v0.copy(coreAnchor);
      _v1.set((coreAnchor.x + gp.x) * 0.5, midY, (coreAnchor.z + gp.z) * 0.5);
      _v2.copy(gp);
      updateRibbonGeometry(entry.tube.geometry, _v0, _v1, _v2);
      // Update the spline curve for particle flow
      if (entry.curve) {
        entry.curve.points[0].copy(coreAnchor);
        entry.curve.points[1].copy(_v1);
        entry.curve.points[2].copy(gp);
      }
    }

    // Gentle bob + spin — frozen when selected
    entry.group.position.y = entry.basePosition.y + Math.sin(rotTime * 0.7 + offset) * 0.48;
    entry.node.rotation.y = rotTime * 0.4 + offset;
    entry.halo.rotation.z = rotTime * 0.55 + offset;

    // Update holographic material time uniform
    if (entry.node.material.uniforms?.uTime) {
      entry.node.material.uniforms.uTime.value = elapsed;
    }

    // Update tube shader time
    if (entry.tubeMat?.uniforms?.uTime) {
      entry.tubeMat.uniforms.uTime.value = elapsed;
    }

    // Dendrite positioning (virus-tree layout) — uses scratch _v0 to avoid allocs
    entry.skillSprites.forEach((sprite) => {
      if (!sprite.mesh.visible) return;
      _v0.copy(entry.group.position).add(sprite.localPosition);
      sprite.mesh.position.copy(_v0);
      sprite.mesh.rotation.y = rotTime * 0.8;
      sprite.mesh.rotation.x = rotTime * 0.3;
      sprite.label.position.set(_v0.x, _v0.y + 0.5, _v0.z);
      if (sprite.wire && sprite.wire.visible) {
        sprite.wire.position.copy(entry.group.position);
      }
      if (sprite.wireMat?.uniforms?.uTime) {
        sprite.wireMat.uniforms.uTime.value = elapsed;
      }
    });
  });

  state.devices.forEach((entry, index) => {
    if (!entry.mesh.visible) return;
    entry.mesh.rotation.y = rotTime * 0.15 + index;
    entry.mesh.material.emissiveIntensity = 0.55 + Math.sin(rotTime * 1.4 + index) * 0.15;
    // Update device wire shader time
    if (entry.wireMat?.uniforms?.uTime) {
      entry.wireMat.uniforms.uTime.value = elapsed;
    }
  });


  // Update environment shader uniforms (stars + rings) — direct refs, no traverse
  if (state.envUniforms) {
    state.envUniforms.starTime.value = elapsed;
    state.envUniforms.ringTime.value = elapsed;
  }

  // Animate particle data flow (Section G)
  updateParticleFlow(elapsed);

  state.controls.update();
  state.composer.render();
  state.labels.render(state.scene, state.camera);
}

/**
 * Banner for fixture mode (FR-033c). A synthetic topology must never be
 * mistakable for live data — in a security tool a fabricated claw read as real
 * is a hazard.
 */
function markFixtureMode(name) {
  const el = document.createElement('div');
  el.id = 'fixture-banner';
  el.textContent = `FIXTURE: ${name} — synthetic data, not this Border`;
  document.body.appendChild(el);
}

function onResize() {
  // Orthographic: no .aspect property — the frustum bounds must be recomputed
  // instead, or a resize silently stretches the chart (FR-013).
  resizeChartCamera(state.camera, window.innerWidth / window.innerHeight);
  state.renderer.setSize(window.innerWidth, window.innerHeight);
  state.labels.setSize(window.innerWidth, window.innerHeight);
  state.composer.setSize(window.innerWidth, window.innerHeight);
}

function connectSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  state.socket = socket;

  // Knowledge (RAG) panel — mounted once, rebound to each new socket on reconnect
  if (!state.knowledgePanel) {
    state.knowledgePanel = new KnowledgePanel(socket);
    document.body.appendChild(state.knowledgePanel.render());
  } else {
    state.knowledgePanel.socket = socket;
    state.knowledgePanel.connectSocket();
  }

  socket.addEventListener('open', () => {
    dom.footerSocket.textContent = 'CONNECTED';
    dom.footerSocket.style.color = 'var(--ok)';
  });

  socket.addEventListener('message', (event) => {
    const message = JSON.parse(event.data);
    if (message.type === 'graph:heartbeat') {
      dom.footerUpdated.textContent = new Date(message.payload.generatedAt).toLocaleTimeString();
      if (state.localCore) {
        gsap.fromTo(state.localCore.nucleus.scale, { x: 1, y: 1, z: 1 }, { x: 1.12, y: 1.12, z: 1.12, duration: 0.22, yoyo: true, repeat: 1 });
      }
    }
    // Chat activation events from server (skip if HTTP response already triggered it)
    if (message.type === 'chat:activations' && !state._httpActivationPending) {
      handleActivations(message.payload.activations);
    }
    state._httpActivationPending = false;
    // Specific tool call visualization (Section H)
    if (message.type === 'chat:tool_call') {
      handleToolCall(message.payload);
    }
    if (message.type === 'config:updated') {
      // Reload graph data on config change
      fetchGraph().then((graph) => {
        state.graph = graph;
        renderMetrics(graph);
      }).catch(() => {});
    }
    // Live BGP state updates
    if (message.type === 'bgp:state') {
      const bgp = message.payload;
      state.bgp = bgp;
      // Update peer core payload state
      state.peerCores.forEach((core) => {
        if (!core.peerPayload) return;
        const updated = bgp.peers.find((p) => p.as === core.peerPayload.as);
        if (updated) {
          const wasEstablished = core.peerPayload.state === 'Established';
          const nowEstablished = updated.state === 'Established';
          core.peerPayload = { ...core.peerPayload, ...updated };
          if (!wasEstablished && nowEstablished) {
            gsap.fromTo(core.nucleus.material, { emissiveIntensity: 3.0 }, { emissiveIntensity: 0.9, duration: 1.0 });
          }
        }
      });
    }
  });

  socket.addEventListener('close', () => {
    dom.footerSocket.textContent = 'RETRYING';
    dom.footerSocket.style.color = '#ffb703';
    window.setTimeout(connectSocket, 2500);
  });
}

function wireUI() {
  dom.search.addEventListener('input', (event) => {
    state.filters.query = event.target.value;
    applyFilters();
    // HUD 2.0 (FR-031/031a): match members, categories and tool names by
    // highlighting and dimming IN PLACE. Never hides, never re-packs — hiding
    // would re-flow the chart and destroy the spatial memory the layout exists
    // to build.
    searchOrgChart(event.target.value);
  });

  document.querySelectorAll('.segmented-btn').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.segmented-btn').forEach((candidate) => candidate.classList.remove('active'));
      button.classList.add('active');
      state.filters.view = button.dataset.view;
      applyFilters();
      if (state.filters.view === 'overview') {
        // Re-frame the whole chart rather than the old orbit centroid.
        frameChart(state.camera, state.controls, chartNodes());
      }
    });
  });

  // Chat form
  dom.chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const message = dom.chatInput.value.trim();
    if (!message) return;
    sendChatMessage(message);
  });

  // New Session button — resets chat and scene state
  const newSessionBtn = document.getElementById('new-session');
  if (newSessionBtn) {
    newSessionBtn.addEventListener('click', resetChatSession);
  }

  // Chat toggle collapse/expand
  dom.chatToggle.addEventListener('click', () => {
    dom.chatDrawer.classList.toggle('collapsed');
    dom.chatToggle.textContent = dom.chatDrawer.classList.contains('collapsed') ? '+' : '_';
  });

  // Panel collapse/expand
  function togglePanel(panel, reopenBtn, arrowCollapsed, arrowExpanded) {
    panel.classList.toggle('collapsed');
    const isCollapsed = panel.classList.contains('collapsed');
    reopenBtn.classList.toggle('visible', isCollapsed);
  }

  dom.toggleLeft.addEventListener('click', () => togglePanel(dom.sidebarLeft, dom.reopenLeft));
  dom.toggleRight.addEventListener('click', () => togglePanel(dom.sidebarRight, dom.reopenRight));
  dom.toggleFooter.addEventListener('click', () => togglePanel(dom.footerPanel, dom.reopenFooter));

  dom.reopenLeft.addEventListener('click', () => {
    dom.sidebarLeft.classList.remove('collapsed');
    dom.reopenLeft.classList.remove('visible');
  });
  dom.reopenRight.addEventListener('click', () => {
    dom.sidebarRight.classList.remove('collapsed');
    dom.reopenRight.classList.remove('visible');
  });
  dom.reopenFooter.addEventListener('click', () => {
    dom.footerPanel.classList.remove('collapsed');
    dom.reopenFooter.classList.remove('visible');
  });

  // Quality budget toggle
  const qualityToggle = document.getElementById('quality-toggle');
  if (qualityToggle) {
    qualityToggle.addEventListener('click', cycleQualityMode);
  }

  window.addEventListener('pointermove', onPointerMove);
  window.addEventListener('click', onClick);
  window.addEventListener('resize', onResize);
}

// ── GPU Particle Data Flow (Section G) ──────────────────────────
const PARTICLES_PER_TUBE = 12;

function initParticleFlow() {
  const count = state.integrations.length * PARTICLES_PER_TUBE;
  if (count === 0) return;

  const geo = new THREE.SphereGeometry(0.06, 6, 6);
  const mat = new THREE.MeshBasicMaterial({
    color: 0x65c3ff,
    transparent: true,
    opacity: 0.85,
    blending: THREE.AdditiveBlending,
  });
  const mesh = new THREE.InstancedMesh(geo, mat, count);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.frustumCulled = false;
  state.scene.add(mesh);
  state.particleSystem = mesh;

  // Set up per-instance colors
  const colorAttr = new Float32Array(count * 3);
  let particleIndex = 0;
  state.integrations.forEach((entry) => {
    const c = new THREE.Color(entry.payload.color);
    for (let p = 0; p < PARTICLES_PER_TUBE; p++) {
      colorAttr[particleIndex * 3] = c.r;
      colorAttr[particleIndex * 3 + 1] = c.g;
      colorAttr[particleIndex * 3 + 2] = c.b;
      state.particleData.push({
        integrationIndex: state.integrations.indexOf(entry),
        t: Math.random(), // position along curve [0..1]
        speed: 0.15 + Math.random() * 0.25,
        wobblePhase: Math.random() * Math.PI * 2,
        wobbleAmp: 0.1 + Math.random() * 0.2,
      });
      particleIndex++;
    }
  });
  mesh.instanceColor = new THREE.InstancedBufferAttribute(colorAttr, 3);
}

function updateParticleFlow(elapsed) {
  if (!state.particleSystem) return;
  const dummy = state.particleDummy;

  for (let i = 0; i < state.particleData.length; i++) {
    const pd = state.particleData[i];
    const entry = state.integrations[pd.integrationIndex];
    if (!entry || !entry.group.visible) {
      dummy.scale.set(0, 0, 0);
      dummy.updateMatrix();
      state.particleSystem.setMatrixAt(i, dummy.matrix);
      continue;
    }

    // Advance position along tube curve
    pd.t += pd.speed * 0.004;
    if (pd.t > 1) pd.t -= 1;

    const pos = entry.curve.getPointAt(pd.t);
    // Perpendicular wobble
    const wobble = Math.sin(elapsed * 2.0 + pd.wobblePhase) * pd.wobbleAmp;
    pos.y += wobble;

    // Scale: small at endpoints, larger in middle
    const scaleFactor = Math.sin(pd.t * Math.PI) * 1.5 + 0.3;

    dummy.position.copy(pos);
    dummy.scale.setScalar(scaleFactor);
    dummy.updateMatrix();
    state.particleSystem.setMatrixAt(i, dummy.matrix);
  }
  state.particleSystem.instanceMatrix.needsUpdate = true;
}

// ── Activation chromatic spike (subtle) ─────────────────────────
function triggerActivationEffects() {
  // Subtle chromatic aberration spike only — no glitch pass (too disruptive)
  if (state.rgbShiftPass) {
    gsap.to(state.rgbShiftPass.uniforms.amount, {
      value: 0.0025,
      duration: 0.12,
      yoyo: true,
      repeat: 1,
      ease: 'power2.out',
      onComplete: () => { state.rgbShiftPass.uniforms.amount.value = 0.0008; },
    });
  }
}

// ── Terminal Card Pool (Section H) ──────────────────────────────
const TERMINAL_CARD_POOL_SIZE = 8;

function initTerminalCardPool() {
  for (let i = 0; i < TERMINAL_CARD_POOL_SIZE; i++) {
    const el = document.createElement('div');
    el.className = 'terminal-card';
    el.style.cssText = `
      pointer-events: none;
      background: rgba(4, 10, 20, 0.88);
      border: 1px solid rgba(101, 195, 255, 0.35);
      border-radius: 8px;
      padding: 8px 10px;
      max-width: 220px;
      font-family: 'IBM Plex Mono', monospace;
      font-size: 10px;
      color: #e7f1ff;
      opacity: 0;
      backdrop-filter: blur(6px);
      box-shadow: 0 4px 20px rgba(0,0,0,0.4), inset 0 1px 0 rgba(101,195,255,0.1);
    `;
    const label = new CSS2DObject(el);
    label.visible = false;
    state.scene.add(label);
    state.terminalCards.push({ element: el, label, inUse: false });
  }
}

function showTerminalCard(toolName, output, integrationId) {
  const card = state.terminalCards.find((c) => !c.inUse);
  if (!card) return;

  const entry = state.integrations.find((e) => e.payload.id === integrationId);
  if (!entry || !entry.curve) return;

  card.inUse = true;
  card.label.visible = true;

  // Truncate output to 4 lines
  const lines = (output || '').split('\n').slice(0, 4).join('\n');
  const truncated = lines.length > 200 ? lines.slice(0, 200) + '...' : lines;
  card.element.innerHTML = `
    <div style="color: #65c3ff; margin-bottom: 4px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; font-size: 9px;">${toolName}</div>
    <pre style="margin:0; white-space: pre-wrap; word-break: break-all; opacity: 0.8; line-height: 1.4;">${truncated || 'executing...'}</pre>
  `;

  // Animate along the tube curve from core outward
  const duration = 2500;
  const startTime = performance.now();
  const startT = 0.1;
  const endT = 0.85;

  card.element.style.opacity = '0';
  gsap.to(card.element, { opacity: 1, duration: 0.3 });

  function step() {
    const now = performance.now();
    const progress = Math.min((now - startTime) / duration, 1);
    const t = startT + (endT - startT) * progress;
    const pos = entry.curve.getPointAt(t);
    card.label.position.set(pos.x, pos.y + 1.2, pos.z);

    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      gsap.to(card.element, {
        opacity: 0,
        duration: 0.5,
        onComplete: () => {
          card.label.visible = false;
          card.inUse = false;
        },
      });
    }
  }
  requestAnimationFrame(step);
}

async function boot() {
  try {
    setLoading(12, 'Loading graph data');
    state.graph = await fetchGraph();

    setLoading(30, 'Fetching BGP topology');
    try {
      const bgpRes = await fetch('/api/bgp');
      state.bgp = await bgpRes.json();
    } catch { state.bgp = null; }

    // N2N federation state (feature 052) — optional, degrades gracefully
    // ?fixture=<name> substitutes a committed /api/n2n fixture for the live
    // feed (T004). Client-side on purpose: server.js stays untouched, so no
    // endpoint is added and the API surface never widens (FR-019). Opt-in
    // only, and marked on screen — FR-033c forbids a synthetic topology
    // appearing without the operator asking for it.
    state.fixtureName = new URLSearchParams(location.search).get('fixture');
    try {
      const url = state.fixtureName
        ? `/fixtures/${state.fixtureName}.json`
        : '/api/n2n';
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      recordSuccess(state.feed, await res.json(), Date.now());
      state.n2n = renderablePayload(state.feed);
    } catch (e) {
      // First load failed: nothing to freeze. state.n2n stays null and the
      // existing empty/first-run path renders — NOT a fabricated outage.
      recordFailure(state.feed, e, Date.now());
      state.n2n = null;
    }
    if (state.fixtureName) markFixtureMode(state.fixtureName);

    setLoading(36, 'Spinning up scene');
    initScene();

    // Build local core — shifted left to make room for peer cores.
    // NCFED overlay claws with a live channel render as claw cores even when
    // their direct BGP session is down: the overlay (not BGP) carries chat/
    // tasks/inventory, and claw BGP sessions are inbound-only here — so a
    // fully federated claw was invisible whenever the BGP leg was down.
    // The orbit scene built local/peer cores from the BGP + overlay peer list
    // here. HUD 2.0 renders peers from /api/n2n in the external band instead
    // (FR-003), so that derivation and its cores are gone with the orbit
    // layout (FR-027). state.bgp is still fetched and still drives the panel.

    setLoading(58, 'Laying out the trust org chart');
    // ── HUD 2.0 (feature 072) ────────────────────────────────────────────
    // Phase 7 complete: the orbit layout and the integration/device scene
    // populations are deleted, not dormant (FR-027, FR-030c).
    // The integration and device populations leave the scene entirely
    // (FR-030): the HUD was drawing a capability catalogue and a managed
    // estate on top of a trust topology. Integrations now surface as member
    // tool expansion; devices remain in the right-hand panel (FR-030b).
    //
    // The category taxonomy arrives as DATA, not an import — /api/graph
    // already serves integrations[] with category and prefixes, which is what
    // keeps FR-006 vendor-neutral for every operator, not just this one.
    state.orgCatalog = (state.graph?.integrations || [])
      .filter((i) => i && i.category && Array.isArray(i.prefixes))
      .map((i) => ({ id: i.id, category: i.category, prefixes: i.prefixes }));

    state.orgLayout = mountOrgChart(state.scene, state.n2n, state.orgCatalog, makeLabel);
    frameChart(state.camera, state.controls, chartNodes());

    // ── Feature 102: interactive layout ──────────────────────────────────
    await restoreSavedLayout();
    applyLayoutPositions(state.layout);
    mountLayoutControls();
    state.dragging = attachDrag({
      domElement: state.renderer.domElement,
      camera: state.camera,
      controls: state.controls,
      pickables: () => pickableObjects(),
      onDragMove: (id, pos) => previewNodePosition(id, pos),
      onDragged: (id, pos) => {
        // Operator intent is recorded against the ACTIVE preset only (FR-049),
        // and pinned under `force` so a later solve leaves it alone (FR-041).
        setPosition(state.layout, id, pos);
        if (state.layout.activePreset === 'force') state.layout.pinned.force.add(id);
        applyLayoutPositions(state.layout);
        renderDirtyIndicator();
      },
    });

    // Keyboard + screen-reader access (FR-032). A WebGL canvas has no
    // focusable elements, so the chart needs a real DOM tree over it.
    mountA11y(document.getElementById('scene-root'), {
      onSelect: (node) => {
        if (node.kind === 'border') { setDetail('local-core'); state.selected = { kind: 'local-core' }; }
        else if (node.kind === 'peer') { setDetail('federation-peer', { ...node.payload, __label: node.label }); state.selected = { kind: 'federation-peer', peer: node.id }; }
        else { setDetail('member-core', node.payload); state.selected = { kind: 'member-core', member: node.id }; }
      },
      onToggle: (node) => toggleNodeExpansion(node.id, makeLabel),
    });

    setLoading(72, 'Placing bands');

    setLoading(78, 'Initializing activation beams');
    initBeamPool();

    setLoading(82, 'Spawning particle flow');
    initParticleFlow();
    initTerminalCardPool();

    setLoading(83, 'Compiling shaders');
    state.renderer.compile(state.scene, state.camera);

    setLoading(84, 'Setting quality budget');
    setQualityMode('balanced');

    setLoading(86, 'Wiring command deck');
    renderSidebar(state.graph);
    renderMetrics(state.graph);
    setDetail('overview');
    wireUI();
    applyFilters();

    setLoading(94, 'Bringing telemetry online');
    connectSocket();
    checkGatewayStatus();
    setInterval(checkGatewayStatus, 15000);
    // Refresh N2N federation state so claw nodes reflect consent/inventory/sever (FR-026)
    setInterval(async () => {
      // Feature 101 (FR-041/042/043): freeze and flag.
      //
      // The pre-101 `catch { /* keep last */ }` froze by accident but never SAID
      // so, and it could not detect a 200 carrying a wrongly-shaped body. A
      // failed poll must never recompute liveness — if it did, the mesh daemon
      // going down would render all seven peers dead and send an operator
      // chasing an outage that does not exist. The decision logic lives in the
      // tested pure module; this is only the wiring.
      const nowMs = Date.now();
      try {
        const res = await fetch('/api/n2n');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        recordSuccess(state.feed, await res.json(), nowMs);
      } catch (e) {
        recordFailure(state.feed, e, nowMs);
      }
      // Only ever adopt a payload that actually succeeded. While degraded this
      // keeps returning the last good one, which is the freeze half.
      const frozen = renderablePayload(state.feed);
      if (frozen) {
        // FR-045: a peer selected when its row disappears keeps its panel, marked
        // as gone, and loses its scene selection. Detected here because it needs
        // the previous poll for comparison.
        const before = new Set((state.n2n?.peers || []).map((p) => p.identity));
        const after = new Set((frozen.peers || []).map((p) => p.identity));
        if (state.selected?.kind === 'federation-peer'
            && before.has(state.selected.peer) && !after.has(state.selected.peer)) {
          const gone = (state.n2n.peers || []).find((p) => p.identity === state.selected.peer);
          if (gone) {
            setDetail('federation-peer', { ...gone, __presentInFeed: false });
            clearSelection();
            state.selected = { kind: 'federation-peer', peer: gone.identity, stillPresent: false };
          }
        }
        state.n2n = frozen;
      }
      renderStaleBanner(staleIndicator(state.feed, nowMs));
      // The detail panel only renders on click (setDetail is never called
      // again just because state.n2n refreshed) -- if "This NetClaw" is the
      // panel currently open, re-render it in place so edge-node liveness/
      // approvals/replication jobs don't require a manual re-click to see.
      if (state.selected?.kind === 'local-core') setDetail('local-core');
      // A member (e.g. a phone) enrolling after load is appended by
      // updateOrgChart via appendMember, without moving anything (FR-034b).
      // HUD 2.0: repaint health and append newly-enrolled members. Positions
      // are never recomputed and categories are never re-ordered — a claw that
      // fails changes how it looks, never where it is (FR-034a).
      updateOrgChart(state.scene, state.n2n, makeLabel);
    }, 30000);
    animate();

    setLoading(100, 'Visual layer online');
    setTimeout(() => dom.loading.classList.add('hidden'), 300);
  } catch (error) {
    dom.loadingText.textContent = `Boot failure: ${error.message}`;
    throw error;
  }
}

/**
 * Feature 102 (US2/US3): preset dropdown, save control, unsaved indicator.
 *
 * Deliberately a small floating control cluster rather than a panel — FR-028
 * forbids altering the chat interface or the right-hand information bar.
 */
function mountLayoutControls() {
  if (document.getElementById('layout-controls')) return;
  const box = document.createElement('div');
  box.id = 'layout-controls';
  box.style.cssText = 'position:fixed;top:96px;left:50%;transform:translateX(-50%);z-index:60;'
    + 'display:flex;gap:8px;align-items:center;padding:6px 10px;border-radius:8px;'
    + 'background:rgba(12,20,30,.82);border:1px solid rgba(120,180,240,.28);'
    + 'font:12px/1.3 ui-monospace,monospace;color:#cfe6ff';

  const sel = document.createElement('select');
  sel.id = 'layout-preset';
  sel.style.cssText = 'background:#0d1621;color:#cfe6ff;border:1px solid #2b4257;'
    + 'border-radius:4px;padding:3px 6px;font:inherit';
  for (const id of PRESETS) {
    const o = document.createElement('option');
    o.value = id; o.textContent = PRESET_LABELS[id];
    sel.appendChild(o);
  }
  sel.value = state.layout.activePreset;
  sel.addEventListener('change', () => {
    setPreset(state.layout, sel.value);
    applyLayoutPositions(state.layout);
    renderDirtyIndicator();
  });

  const reset = mkButton('Reset', 'Discard manual positions for this preset only', () => {
    resetPreset(state.layout);
    applyLayoutPositions(state.layout);
    renderDirtyIndicator();
  });
  const save = mkButton('Save', 'Save this arrangement and viewpoint', saveLayout);
  const discard = mkButton('Discard saved', 'Delete the saved layout on the server', discardLayout);

  const dirty = document.createElement('span');
  dirty.id = 'layout-dirty';
  dirty.style.cssText = 'color:#ffd27a;min-width:74px';

  box.append(document.createTextNode('Layout'), sel, reset, save, discard, dirty);
  document.body.appendChild(box);
  renderDirtyIndicator();
}

function mkButton(label, title, onClick) {
  const b = document.createElement('button');
  b.textContent = label; b.title = title;
  b.style.cssText = 'background:#16283a;color:#cfe6ff;border:1px solid #2b4257;'
    + 'border-radius:4px;padding:3px 8px;font:inherit;cursor:pointer';
  b.addEventListener('click', onClick);
  return b;
}

/**
 * FR-052: unsaved state must be visible ON SCREEN, not only at unload — browsers
 * suppress the unload dialog on tab discard, crash, OS shutdown and without prior
 * interaction, so the indicator is the primary signal and the dialog is a backstop.
 */
function renderDirtyIndicator() {
  const el = document.getElementById('layout-dirty');
  if (el) el.textContent = isDirty(state.layout) ? '● unsaved' : '';
}

/** FR-051: fires ONLY on genuine unsaved change — a warning that cries wolf gets dismissed. */
window.addEventListener('beforeunload', (e) => {
  if (!isDirty(state.layout)) return;
  e.preventDefault();
  e.returnValue = '';
});

async function saveLayout() {
  // Camera pose travels with the arrangement (FR-018): restoring positions without
  // the framing they were designed for delivers half the feature.
  setCamera(state.layout, {
    position: { ...state.camera.position },
    target: { ...state.controls.target },
    zoom: state.camera.zoom,
  });
  const payload = toPayload(state.layout, new Date().toISOString());
  try {
    const res = await fetch('/api/layout', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `HTTP ${res.status}`);
    }
    markSaved(state.layout);          // FR-053: only a SUCCESSFUL save clears dirty
  } catch (e) {
    // FR-035: keep the arrangement in memory and keep it marked unsaved. A failed
    // write must never present as a successful one.
    console.error('layout save failed', e);
    alert(`Layout save failed: ${e.message}\nYour arrangement is still here and still unsaved.`);
  }
  renderDirtyIndicator();
}

async function discardLayout() {
  try {
    await fetch('/api/layout', { method: 'DELETE' });
  } catch (e) {
    console.error('layout discard failed', e);
  }
  state.layout = createLayoutStore('orgchart');
  applyLayoutPositions(state.layout);
  renderDirtyIndicator();
}

/** FR-016/019/047/048: tolerant restore. */
async function restoreSavedLayout() {
  try {
    const res = await fetch('/api/layout');
    if (!res.ok) return;
    const body = await res.json();
    if (body?.empty) {
      if (body.warning) console.warn('saved layout ignored:', body.warning);
      return;
    }
    const known = (chartNodes() || []).map((n) => n.id);
    const { dropped } = applyPayload(state.layout, body, known);
    if (dropped.length) console.info(`saved layout: ignored ${dropped.length} stale node id(s)`);
    const cam = clampCamera(state.layout.camera);
    if (cam) {
      state.camera.position.set(cam.position.x, cam.position.y, cam.position.z);
      state.controls.target.set(cam.target.x, cam.target.y, cam.target.z);
      state.camera.zoom = cam.zoom;
      state.camera.updateProjectionMatrix();
      state.controls.update();
    }
  } catch (e) {
    // FR-019: fall back to computed and say so, never render a broken scene.
    console.warn('saved layout unavailable, using computed layout:', e.message);
  }
}

boot();

// ── Budget status polling (spec 109) ──────────────────────────────────────────
//
// Polls /api/budget/status every 10s and updates the footer indicator.
// Color coding: green (ok) → amber (>50%) → red (>80%) → pulsing red (halted).

async function pollBudgetStatus() {
  if (!dom.footerBudget) return;
  try {
    const res = await fetch('/api/budget/status');
    if (!res.ok) { dom.footerBudget.textContent = '--'; return; }
    const data = await res.json();

    const cost = data.sessionCostUsd?.toFixed(2) ?? '0.00';
    const cap = data.sessionBudgetUsd?.toFixed(2) ?? '5.00';
    dom.footerBudget.textContent = `$${cost} / $${cap}`;

    // Color coding
    dom.footerBudget.classList.remove('budget-ok', 'budget-warning', 'budget-critical', 'budget-halted');
    if (data.status === 'halted') {
      dom.footerBudget.classList.add('budget-halted');
      dom.footerBudget.title = 'Session budget exhausted — say "continue" to extend';
    } else if (data.status === 'critical') {
      dom.footerBudget.classList.add('budget-critical');
      dom.footerBudget.title = `${data.percentUsed}% of session budget used`;
    } else if (data.status === 'warning') {
      dom.footerBudget.classList.add('budget-warning');
      dom.footerBudget.title = `${data.percentUsed}% of session budget used`;
    } else {
      dom.footerBudget.classList.add('budget-ok');
      dom.footerBudget.title = `Session budget: ${data.percentUsed}% used`;
    }
  } catch {
    dom.footerBudget.textContent = '--';
  }
}

// Poll budget every 10 seconds
setInterval(pollBudgetStatus, 10_000);
