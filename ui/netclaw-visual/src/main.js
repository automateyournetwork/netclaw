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
import { VignetteShader } from 'three/addons/shaders/VignetteShader.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';
import gsap from 'gsap';

// ── Quality budget modes ───────────────────────────────────────────
// Focus: minimal effects, best perf. Balanced: default. Broadcast: all effects.
const QUALITY_MODES = ['focus', 'balanced', 'broadcast'];
const QUALITY_LABELS = { focus: 'FOCUS', balanced: 'BALANCED', broadcast: 'BROADCAST' };

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
  state.scene.fog = new THREE.FogExp2(0x040a14, 0.006);

  state.camera = new THREE.PerspectiveCamera(48, window.innerWidth / window.innerHeight, 0.1, 260);
  state.camera.position.set(12, 55, 110);

  state.renderer = new THREE.WebGLRenderer({ antialias: false, alpha: true });
  state.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  state.renderer.setSize(window.innerWidth, window.innerHeight);
  state.renderer.toneMapping = THREE.ACESFilmicToneMapping;
  state.renderer.toneMappingExposure = 1.15;
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

  state.controls = new OrbitControls(state.camera, state.renderer.domElement);
  state.controls.enableDamping = true;
  state.controls.dampingFactor = 0.06;
  state.controls.minDistance = 12;
  state.controls.maxDistance = 180;
  state.controls.maxPolarAngle = Math.PI * 0.48;
  state.controls.target.set(CORE_CENTROID.x, CORE_CENTROID.y, CORE_CENTROID.z);

  // ── Enhanced lighting (Section E) ─────────────────────────────
  state.scene.add(new THREE.AmbientLight(0x4a7cb5, 0.35));

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
const CORE_POSITIONS = {
  local: new THREE.Vector3(-18, 0, 0),
  peer1: new THREE.Vector3(52, 0, -28),
  peer2: new THREE.Vector3(52, 0, 28),
  peer3: new THREE.Vector3(18, 0, -56),
};
const CORE_CENTROID = new THREE.Vector3(12, 0, 0);

function buildCore(identity, position, labelText, colorTint) {
  const pos = position || new THREE.Vector3(0, 0, 0);
  const lbl = labelText || identity.name.toUpperCase();
  const tint = colorTint || 0x66ccff;
  const tintColor = new THREE.Color(tint);
  const group = new THREE.Group();

  // Shell — custom shader wireframe with fresnel + scan-lines (uniform-based color)
  const shellMat = new THREE.ShaderMaterial({
    uniforms: { uTime: { value: 0 }, uTintColor: { value: tintColor.clone() } },
    vertexShader: `
      varying vec3 vNormal;
      varying vec3 vWorldPos;
      void main() {
        vNormal = normalize(normalMatrix * normal);
        vWorldPos = (modelMatrix * vec4(position, 1.0)).xyz;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform float uTime;
      uniform vec3 uTintColor;
      varying vec3 vNormal;
      varying vec3 vWorldPos;
      void main() {
        vec3 viewDir = normalize(cameraPosition - vWorldPos);
        float fresnel = pow(1.0 - abs(dot(viewDir, vNormal)), 3.0);
        float scan = sin(vWorldPos.y * 18.0 - uTime * 2.5) * 0.5 + 0.5;
        scan = smoothstep(0.4, 0.6, scan) * 0.3;
        vec3 col = uTintColor * (0.15 + fresnel * 0.8 + scan);
        gl_FragColor = vec4(col, 0.12 + fresnel * 0.35);
      }
    `,
    transparent: true,
    wireframe: true,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const shell = new THREE.Mesh(_sharedGeo.coreShell, shellMat);
  group.add(shell);

  // Nucleus — thin glass shell
  const nucleus = new THREE.Mesh(
    _sharedGeo.coreNucleus,
    new THREE.MeshPhysicalMaterial({
      color: tint,
      emissive: tint,
      emissiveIntensity: 0.9,
      roughness: 0.05,
      metalness: 0.1,
      iridescence: 1.0,
      iridescenceIOR: 1.8,
      transmission: 0.95,
      ior: 1.5,
      thickness: 0.3,
      clearcoat: 1.0,
      clearcoatRoughness: 0.05,
      transparent: true,
      opacity: 0.15,
      depthWrite: false,
    }),
  );
  nucleus.renderOrder = 1;
  group.add(nucleus);

  const torus = new THREE.Mesh(
    new THREE.TorusGeometry(4.7, 0.08, 12, 120),
    new THREE.MeshBasicMaterial({ color: 0xff7b54, transparent: true, opacity: 0.36 }),
  );
  torus.rotation.x = Math.PI / 2.8;
  group.add(torus);

  const torus2 = new THREE.Mesh(
    new THREE.TorusGeometry(5.2, 0.05, 12, 120),
    new THREE.MeshBasicMaterial({ color: tint, transparent: true, opacity: 0.22 }),
  );
  torus2.rotation.x = Math.PI / 1.6;
  torus2.rotation.y = Math.PI / 3;
  group.add(torus2);

  const label = makeLabel(lbl);
  label.position.set(0, 5.4, 0);
  group.add(label);

  // Logo sprite inside the nucleus
  const logoTexture = new THREE.TextureLoader().load('/logos/netclaw.png');
  logoTexture.colorSpace = THREE.SRGBColorSpace;
  const logoSprite = new THREE.Sprite(
    new THREE.SpriteMaterial({
      map: logoTexture,
      transparent: true,
      opacity: 0.85,
      depthWrite: false,
      depthTest: false,
      blending: THREE.AdditiveBlending,
    }),
  );
  logoSprite.scale.set(2.8, 2.8 * 0.55, 1);
  logoSprite.position.set(0, 0, 0);
  logoSprite.renderOrder = 10;
  group.add(logoSprite);

  group.position.copy(pos);
  group.userData = { type: 'core' };
  state.scene.add(group);

  return { group, shell, nucleus, torus, torus2, logoSprite, position: pos.clone() };
}

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

function buildIntegrations(graph) {
  const grouped = graph.categories.map((category) => ({
    ...category,
    nodes: graph.integrations.filter((integration) => integration.category === category.name),
  }));

  const radiusBase = 34;
  const coreAnchor = state.localCore ? state.localCore.position : new THREE.Vector3(0, 0, 0);

  // Flatten all integrations into a single ordered list (grouped by category)
  const allIntegrations = [];
  grouped.forEach((bucket) => bucket.nodes.forEach((n) => allIntegrations.push(n)));
  const totalN = allIntegrations.length;
  const goldenRatio = (1 + Math.sqrt(5)) / 2;

  // Build a look-up with spherical coords + unstable orbit parameters
  const orbitMap = new Map();
  allIntegrations.forEach((integration, i) => {
    // Fibonacci sphere — even distribution across a full sphere
    const theta0 = 2 * Math.PI * i / goldenRatio;
    const phi0 = Math.acos(1 - 2 * (i + 0.5) / totalN);
    const radius = radiusBase + (i % 3) * 2.5;
    // Unique slow orbit speed + slight polar drift
    const orbitSpeed = 0.0012 + (((i * 7 + 3) % 13) / 13) * 0.0018;
    const axisTilt = ((i * 11 + 5) % 17) / 17 * 0.15 - 0.075;
    const position = new THREE.Vector3(
      coreAnchor.x + radius * Math.sin(phi0) * Math.cos(theta0),
      radius * Math.cos(phi0),
      coreAnchor.z + radius * Math.sin(phi0) * Math.sin(theta0),
    );
    orbitMap.set(integration.id, { position, theta0, phi0, radius, orbitSpeed, axisTilt });
  });

  grouped.forEach((bucket) => {
    bucket.nodes.forEach((integration) => {
      const orbitData = orbitMap.get(integration.id);
      const position = orbitData.position;

      const group = new THREE.Group();
      group.position.copy(position);

      const size = 0.7 + Math.min(integration.skillCount * 0.045, 1.4);
      // Use holographic shader material for integration nodes
      const holoMat = createHolographicMaterial(integration.color);
      const node = new THREE.Mesh(new THREE.OctahedronGeometry(size, 1), holoMat);
      node.castShadow = true;
      group.add(node);

      const halo = new THREE.Mesh(
        getHaloGeometry(size + 0.45),
        new THREE.MeshBasicMaterial({ color: integration.color, transparent: true, opacity: 0.26 }),
      );
      halo.rotation.x = Math.PI / 2;
      group.add(halo);

      const label = makeLabel(integration.name);
      label.position.set(0, size + 1.25, 0);
      group.add(label);

      // Logo sprite — only for integrations with a logo file in public/logos/
      const LOGO_IDS = new Set(['pyats']);
      if (LOGO_IDS.has(integration.id)) {
        const logoTex = new THREE.TextureLoader().load(`/logos/${integration.id}.png`);
        logoTex.colorSpace = THREE.SRGBColorSpace;
        const logoSprite = new THREE.Sprite(
          new THREE.SpriteMaterial({
            map: logoTex,
            transparent: true,
            opacity: 0.8,
            depthWrite: false,
            depthTest: false,
            blending: THREE.AdditiveBlending,
          }),
        );
        logoSprite.scale.set(size * 1.6, size * 1.6 * 0.5, 1);
        logoSprite.position.set(0, 0, 0);
        logoSprite.renderOrder = 10;
        group.add(logoSprite);
      }

      // Connection ribbon with data-flow shader (replaces per-frame TubeGeometry)
      const ribbonGeo = createRibbonGeometry(0.06);
      const midY = Math.max(position.y, 0) + 4.5;
      _v0.copy(coreAnchor);
      _v1.set((coreAnchor.x + position.x) * 0.5, midY, (coreAnchor.z + position.z) * 0.5);
      _v2.copy(position);
      updateRibbonGeometry(ribbonGeo, _v0, _v1, _v2);
      const tubeMat = createTubeMaterial(integration.color);
      const tube = new THREE.Mesh(ribbonGeo, tubeMat);
      // Keep a CatmullRomCurve3 for particle flow (updated on orbit)
      const curve = new THREE.CatmullRomCurve3([
        coreAnchor.clone(), _v1.clone(), position.clone(),
      ]);
      state.scene.add(tube);

      const skills = graph.skills.filter((skill) => skill.integrationId === integration.id);
      const skillSprites = createSkillSprites(position, skills, integration.color, position);

      group.userData = { type: 'integration', payload: integration };
      node.userData = { type: 'integration', payload: integration };
      state.scene.add(group);

      state.integrations.push({
        group,
        node,
        halo,
        tube,
        tubeMat,
        curve,
        label,
        basePosition: position.clone(),
        payload: integration,
        skills,
        skillSprites,
        orbit: orbitData,
      });
    });
  });
}

// ── Virus-tree dendrite layout (Part B) ─────────────────────────────
function computeDendritePositions(skillCount, integrationPosition) {
  const positions = [];
  if (skillCount === 0) return positions;
  const baseRadius = 4.0;
  const radiusSpread = 1.8;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));

  // Direction from core to integration — skills fan OUTWARD
  const outDir = integrationPosition.clone().normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const quat = new THREE.Quaternion().setFromUnitVectors(up, outDir);

  for (let i = 0; i < skillCount; i++) {
    const t = i / Math.max(skillCount - 1, 1);
    const theta = goldenAngle * i;
    const phi = Math.acos(1 - t * 0.85); // ~60deg cone
    const radius = baseRadius + (i % 3) * (radiusSpread / 3);
    const localPos = new THREE.Vector3(
      radius * Math.sin(phi) * Math.cos(theta),
      radius * Math.cos(phi),
      radius * Math.sin(phi) * Math.sin(theta),
    );
    localPos.applyQuaternion(quat);
    positions.push(localPos);
  }
  return positions;
}

// ── Dendrite wire shader (Part C) ───────────────────────────────────
function createDendriteMaterial(color) {
  const c = new THREE.Color(color);
  return new THREE.ShaderMaterial({
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: c },
      uOpacity: { value: 0.0 },
      uProgress: { value: 0.0 },
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
      uniform float uProgress;
      varying vec2 vUv;
      void main() {
        if (vUv.x > uProgress) discard;
        float pulse = smoothstep(0.38, 0.5, fract(vUv.x * 12.0 - uTime * 0.8));
        pulse *= smoothstep(0.62, 0.5, fract(vUv.x * 12.0 - uTime * 0.8));
        float edge = 1.0 - abs(vUv.y - 0.5) * 2.0;
        edge = pow(edge, 0.8);
        vec3 col = uColor * (0.4 + pulse * 1.2);
        float alpha = uOpacity * edge * (0.4 + pulse * 0.6);
        gl_FragColor = vec4(col, alpha);
      }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
}

function createSkillSprites(anchor, skills, color, integrationPosition) {
  const clampedSkills = skills.slice(0, 18);
  const dendrites = computeDendritePositions(clampedSkills.length, integrationPosition);

  return clampedSkills.map((skill, index) => {
    const mesh = new THREE.Mesh(_sharedGeo.skillTetra, getSkillMaterial(color));
    mesh.visible = false;
    mesh.userData = { type: 'skill', payload: skill };
    state.scene.add(mesh);

    const label = makeLabel(skill.name);
    label.visible = false;
    state.scene.add(label);

    // Dendrite wire from integration to skill
    const localPos = dendrites[index];
    const midPos = localPos.clone().multiplyScalar(0.5);
    midPos.y += 0.3; // slight arc
    const wireCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(0, 0, 0),
      midPos,
      localPos.clone(),
    ]);
    const wireGeo = new THREE.TubeGeometry(wireCurve, 16, 0.02, 4, false);
    const wireMat = createDendriteMaterial(color);
    const wire = new THREE.Mesh(wireGeo, wireMat);
    wire.visible = false;
    state.scene.add(wire);

    const sprite = {
      mesh,
      label,
      payload: skill,
      localPosition: localPos,
      anchor: anchor.clone(),
      wire,
      wireMat,
      wireCurve,
    };
    state.skillSprites.push(sprite);
    return sprite;
  });
}

function buildDevices(graph) {
  // Devices hang off the pyATS integration node (testbed.yaml devices)
  const pyatsEntry = state.integrations.find((e) => e.payload.id === 'pyats');
  const anchor = pyatsEntry ? pyatsEntry.basePosition.clone() : new THREE.Vector3(0, 0, 0);

  // Compute outward direction from core to pyATS
  const outDir = anchor.clone().normalize();
  const up = new THREE.Vector3(0, 1, 0);
  const quat = new THREE.Quaternion().setFromUnitVectors(up, outDir);

  const deviceRadius = 6.5;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));

  graph.devices.forEach((device, index) => {
    const t = index / Math.max(graph.devices.length - 1, 1);
    const theta = goldenAngle * index;
    const phi = Math.acos(1 - t * 0.7);
    const localOffset = new THREE.Vector3(
      deviceRadius * Math.sin(phi) * Math.cos(theta),
      deviceRadius * Math.cos(phi),
      deviceRadius * Math.sin(phi) * Math.sin(theta),
    );
    localOffset.applyQuaternion(quat);
    const position = anchor.clone().add(localOffset);

    const isRouter = device.type.toLowerCase().includes('router');
    const color = isRouter ? 0x68f5b2 : 0xffb703;
    const geometry = isRouter ? _sharedGeo.deviceRouter : _sharedGeo.deviceSwitch;
    const mesh = new THREE.Mesh(geometry, createDeviceMaterial(color));
    mesh.position.copy(position);
    mesh.castShadow = true;
    mesh.userData = { type: 'device', payload: device };
    state.scene.add(mesh);

    // Wire from pyATS node to device
    const midPos = anchor.clone().add(localOffset.clone().multiplyScalar(0.5));
    midPos.y += 0.5;
    const wireCurve = new THREE.CatmullRomCurve3([anchor.clone(), midPos, position.clone()]);
    const wireGeo = new THREE.TubeGeometry(wireCurve, 16, 0.03, 4, false);
    const wireMat = createDendriteMaterial(color);
    wireMat.uniforms.uOpacity.value = 0.2;
    wireMat.uniforms.uProgress.value = 1.0;
    const line = new THREE.Mesh(wireGeo, wireMat);
    state.scene.add(line);

    const label = makeLabel(device.name);
    label.position.set(position.x, position.y + 1.4, position.z);
    state.scene.add(label);

    state.devices.push({
      mesh, line, label, payload: device,
      basePosition: position.clone(),
      localOffset,
      wireMat,
      pyatsAnchor: pyatsEntry,
    });
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

function buildPeerRoutes(peerCore, peer) {
  const routes = peer.adjRibIn || [];
  peerCore.routeDendrites = [];
  const pos = peerCore.position;
  const outDir = pos.clone().normalize();
  const baseAngle = Math.atan2(outDir.x, outDir.z);

  routes.forEach((route, ri) => {
    const routeSpread = Math.PI * 0.6;
    const routeAngle = baseAngle + ((ri / Math.max(routes.length - 1, 1)) - 0.5) * routeSpread;
    const routeOffset = new THREE.Vector3(
      Math.sin(routeAngle) * 5.0,
      -1.5 - ri * 0.6,
      Math.cos(routeAngle) * 5.0,
    );
    const routePos = pos.clone().add(routeOffset);
    const routeMid = pos.clone().add(routeOffset.clone().multiplyScalar(0.5));
    routeMid.y += 0.3;
    const routeCurve = new THREE.CatmullRomCurve3([pos.clone(), routeMid, routePos]);
    const routeGeo = new THREE.TubeGeometry(routeCurve, 8, 0.02, 4, false);
    const isIPv6 = route.prefix.includes(':');
    const routeColor = isIPv6 ? 0x00e5ff : 0x68f5b2;
    const routeMat = createDendriteMaterial(routeColor);
    routeMat.uniforms.uOpacity.value = 0.25;
    routeMat.uniforms.uProgress.value = 1.0;
    const routeWire = new THREE.Mesh(routeGeo, routeMat);
    state.scene.add(routeWire);

    const routeLabel = makeLabel(route.prefix);
    routeLabel.position.copy(routePos);
    routeLabel.visible = false;
    state.scene.add(routeLabel);

    peerCore.routeDendrites.push({ wire: routeWire, mat: routeMat, label: routeLabel, route, position: routePos });
  });
}

function buildPeerLinks() {
  const allCores = state.cores;
  for (let i = 0; i < allCores.length; i++) {
    for (let j = i + 1; j < allCores.length; j++) {
      const posA = allCores[i].position;
      const posB = allCores[j].position;
      const ribbonGeo = createRibbonGeometry(0.08);
      _v0.copy(posA);
      _v1.set((posA.x + posB.x) * 0.5, Math.max(posA.y, posB.y) + 3.0, (posA.z + posB.z) * 0.5);
      _v2.copy(posB);
      updateRibbonGeometry(ribbonGeo, _v0, _v1, _v2);
      const linkMat = createTubeMaterial(0xe040fb);
      linkMat.uniforms.uOpacity.value = 0.4;
      const link = new THREE.Mesh(ribbonGeo, linkMat);
      state.scene.add(link);
      state.peerLinks.push({ tube: link, mat: linkMat, from: i, to: j });
    }
  }
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
  return `
    <div class="n2n-section n2n-federated">
      <h3>N2N Federation ${fresh}</h3>
      <div class="detail-row"><span>Status</span><strong class="n2n-state-federated">federated</strong></div>
      <div class="detail-row"><span>Inventory</span><strong>v${inv.version ?? '—'} · ${recv}</strong></div>
      <div class="n2n-badges">${badges}</div>
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

function setDetail(kind, payload, related = []) {
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
      } else {
        el.textContent = 'OFFLINE';
        el.className = 'gateway-indicator offline';
      }
    }
  } catch {
    if (dom.gatewayStatus) {
      dom.gatewayStatus.textContent = 'OFFLINE';
      dom.gatewayStatus.className = 'gateway-indicator offline';
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

  // Track time offset for freeze: when frozen, hold rotations at the moment of freeze
  if (frozen && state._frozenAt == null) state._frozenAt = elapsed;
  if (!frozen) state._frozenAt = null;
  const rotTime = frozen ? state._frozenAt : elapsed;

  // Animate all core nodes (local + peers)
  let coresMovedThisFrame = false;
  state.cores.forEach((core, idx) => {
    const offset = idx * 0.3;

    // Orbit core around centroid when not frozen
    if (!frozen && core.orbit) {
      core.orbit.angle += core.orbit.speed;
      const ox = core.orbit.center.x + core.orbit.radius * Math.cos(core.orbit.angle);
      const oz = core.orbit.center.z + core.orbit.radius * Math.sin(core.orbit.angle);
      core.group.position.set(ox, core.orbit.y, oz);
      core.position.set(ox, core.orbit.y, oz);
      coresMovedThisFrame = true;
    }

    core.shell.rotation.y = rotTime * 0.18 + offset;
    core.shell.rotation.x = rotTime * 0.08 + offset * 0.5;
    core.torus.rotation.z = rotTime * 0.28 + offset;
    if (core.torus2) core.torus2.rotation.z = -rotTime * 0.22 + offset;
    // Shader time always advances (keeps glow alive)
    if (core.shell.material.uniforms) {
      core.shell.material.uniforms.uTime.value = elapsed;
    }
    core.nucleus.material.emissiveIntensity = 0.7 + Math.sin(elapsed * 2.1 + offset) * 0.25;
    // Animate peer route dendrites — move with core
    if (core.routeDendrites) {
      core.routeDendrites.forEach((rd) => {
        if (rd.mat.uniforms?.uTime) rd.mat.uniforms.uTime.value = elapsed;
      });
    }
  });

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

function onResize() {
  state.camera.aspect = window.innerWidth / window.innerHeight;
  state.camera.updateProjectionMatrix();
  state.renderer.setSize(window.innerWidth, window.innerHeight);
  state.labels.setSize(window.innerWidth, window.innerHeight);
  state.composer.setSize(window.innerWidth, window.innerHeight);
}

function connectSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws`);
  state.socket = socket;

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
  });

  document.querySelectorAll('.segmented-btn').forEach((button) => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.segmented-btn').forEach((candidate) => candidate.classList.remove('active'));
      button.classList.add('active');
      state.filters.view = button.dataset.view;
      applyFilters();
      if (state.filters.view === 'overview') {
        focusTarget(CORE_CENTROID.clone());
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
    try {
      const n2nRes = await fetch('/api/n2n');
      state.n2n = await n2nRes.json();
    } catch { state.n2n = null; }

    setLoading(36, 'Spinning up scene');
    initScene();

    // Build local core — shifted left to make room for peer cores
    const hasPeers = state.bgp?.available && state.bgp.peers.length > 0;
    const localPos = hasPeers ? CORE_POSITIONS.local : new THREE.Vector3(0, 0, 0);
    const localCore = buildCore(state.graph.identity, localPos, state.graph.identity.name.toUpperCase(), 0x66ccff);
    // Orbit data for local core — orbits around the centroid
    const lcDist = localPos.distanceTo(CORE_CENTROID);
    localCore.orbit = {
      center: CORE_CENTROID.clone(),
      radius: lcDist,
      angle: Math.atan2(localPos.z - CORE_CENTROID.z, localPos.x - CORE_CENTROID.x),
      y: localPos.y,
      speed: 0.0008,
    };
    state.localCore = localCore;
    state.core = localCore; // backward compat
    state.cores.push(localCore);

    // Build peer cores as equal central nodes
    if (hasPeers) {
      const uniquePeers = deduplicatePeers(state.bgp.peers);
      const peerPositions = [CORE_POSITIONS.peer1, CORE_POSITIONS.peer2, CORE_POSITIONS.peer3];
      uniquePeers.slice(0, 3).forEach((peer, i) => {
        const isClaw = peer.type === 'claw';
        const label = isClaw
          ? `NETCLAW AS${peer.as || '?'}`
          : `ROUTER ${peer.routerId || peer.peerIp || peer.peer}`;
        const tint = isClaw ? 0xe040fb : 0x00e5ff;
        const peerCore = buildCore(state.graph.identity, peerPositions[i], label, tint);
        peerCore.peerPayload = peer;
        peerCore.isClaw = isClaw;
        // Orbit data — orbits around the centroid
        const pDist = peerPositions[i].distanceTo(CORE_CENTROID);
        peerCore.orbit = {
          center: CORE_CENTROID.clone(),
          radius: pDist,
          angle: Math.atan2(peerPositions[i].z - CORE_CENTROID.z, peerPositions[i].x - CORE_CENTROID.x),
          y: peerPositions[i].y,
          speed: 0.0006 + i * 0.0003,
        };
        state.peerCores.push(peerCore);
        state.cores.push(peerCore);

        // Build route dendrites from this peer
        buildPeerRoutes(peerCore, peer);
      });
      // Connect all cores with peer-link tubes
      buildPeerLinks();
    }

    setLoading(58, 'Rendering integration lattice');
    buildIntegrations(state.graph);

    setLoading(72, 'Placing device ring');
    buildDevices(state.graph);

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
      try { state.n2n = await (await fetch('/api/n2n')).json(); } catch { /* keep last */ }
    }, 30000);
    animate();

    setLoading(100, 'Visual layer online');
    setTimeout(() => dom.loading.classList.add('hidden'), 300);
  } catch (error) {
    dom.loadingText.textContent = `Boot failure: ${error.message}`;
    throw error;
  }
}

boot();
