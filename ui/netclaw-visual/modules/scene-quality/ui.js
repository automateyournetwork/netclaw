/**
 * Scene Quality — retunes the 3D post-processing chain for contrast.
 *
 * THE DIAGNOSIS
 *   The scene reads as washed out at every quality mode, in both themes, because
 *   the wash is in WebGL rather than CSS. Four causes, in order of impact:
 *
 *   1. `toneMappingExposure = 1.55` with ACES Filmic. ACES already lifts
 *      midtones; over-exposing on top of it pushes most of the scene toward the
 *      shoulder of the curve, so everything trends milky and highlights clip.
 *   2. `UnrealBloomPass` threshold `0.5`. Anything brighter than mid-grey blooms,
 *      which at that exposure is nearly everything — so bloom stops being a glow
 *      on emissive nodes and becomes a full-frame haze. Quality modes only ever
 *      change bloom *strength*, never the threshold, so no mode escapes it.
 *   3. `alpha: true` with no clear colour. The canvas is transparent, so the
 *      body's radial gradients show *through* the scene and lift the black point.
 *      That is the soft grey bloom in the upper left.
 *   4. Film grain and RGB shift are both on at `balanced`, which softens edges
 *      and further reduces apparent contrast.
 *
 * WHY A MODULE AND NOT A PATCH
 *   Those numbers are upstream's, and the exposure carries the comment
 *   "HUD 2.0: brighter overall (operator feedback)" — someone deliberately turned
 *   it up. Overwriting a tuning decision in a file we do not own is the wrong
 *   move, so this adjusts the live objects through `ctx.state` after init instead.
 *   Delete the directory and upstream's values return.
 *
 *   It also means the values are adjustable at runtime, which matters: contrast
 *   is a judgement call on a specific display, and a slider beats someone
 *   guessing numbers they cannot see.
 *
 * REASSERTION
 *   Three separate upstream code paths write the same properties this module
 *   owns, and only one of them is a button click:
 *
 *     setQualityMode()        bloom strength, film/rgbShift/afterimage enabled,
 *                             rgbShift amount        — button *or* keyboard
 *     enableCinematicBurst()  film + afterimage forced on for 6s on activation,
 *                             then restored from the quality mode, not from here
 *     init order              the composer may not exist when registerUI runs
 *
 *   Listening for a click covered the first path only, so grain would come back
 *   on the next chat turn and stay. Instead a drift-correcting frame loop holds
 *   the settings: it compares the live values against the config each frame and
 *   writes only on a mismatch. Five float compares against a full
 *   post-processing chain is not a measurable cost, and unlike an interval it
 *   cannot leave a visible flash of an effect the operator turned off.
 *
 *   Bloom strength is the one value applied *relatively*: upstream drops it to
 *   0.6 from 1.1 in FOCUS, and that intent is worth keeping, so the slider is
 *   scaled by the same ratio rather than overriding the mode outright.
 */

import './scene-quality.css';

const STORAGE_KEY = 'netclaw.sceneQuality';

/**
 * Defaults chosen to restore black point and keep bloom on genuinely emissive
 * geometry only. Conservative rather than dramatic — the aim is a scene that
 * reads clearly, not a different art direction.
 */
const DEFAULTS = {
  exposure: 1.05,      // was 1.55 — ACES does the midtone lift already
  bloomStrength: 0.75, // was 1.1
  bloomThreshold: 0.85, // was 0.5 — only emissive nodes should glow
  bloomRadius: 0.4,    // was 0.55 — tighter, less veiling
  grain: 0.04,         // was 0.18
  aberration: 0.0003,  // was 0.0008
  backdrop: 0.92,      // clear-colour alpha; 0 = fully transparent (upstream)
  trails: 0.5,         // was 0.82 — afterimage damp, BROADCAST only. 0 disables.
};

/** Upstream's values, for the "Upstream defaults" button. */
const UPSTREAM = {
  exposure: 1.55, bloomStrength: 1.1, bloomThreshold: 0.5, bloomRadius: 0.55,
  grain: 0.18, aberration: 0.0008, backdrop: 0, trails: 0.82,
};

/**
 * FOCUS mode ratio for bloom strength — upstream uses 0.6 where other modes use
 * 1.1. Kept as a ratio so the slider stays meaningful in every mode.
 */
const FOCUS_BLOOM_RATIO = 0.6 / 1.1;

const CONTROLS = [
  { key: 'exposure', label: 'Exposure', min: 0.5, max: 2, step: 0.05,
    hint: 'ACES tone mapping. Above ~1.2 the scene starts to wash out.' },
  { key: 'bloomThreshold', label: 'Bloom cutoff', min: 0, max: 1, step: 0.01,
    hint: 'How bright a pixel must be before it glows. The single biggest contrast lever.' },
  { key: 'bloomStrength', label: 'Bloom strength', min: 0, max: 2, step: 0.05,
    hint: 'How much the glow spreads.' },
  { key: 'bloomRadius', label: 'Bloom radius', min: 0, max: 1, step: 0.05,
    hint: 'Higher veils the frame; lower keeps the glow tight to the node.' },
  { key: 'backdrop', label: 'Backdrop', min: 0, max: 1, step: 0.02,
    hint: 'Opacity of the dark clear colour. 0 lets the page gradient bleed through the canvas.' },
  { key: 'grain', label: 'Film grain', min: 0, max: 0.4, step: 0.01, hint: 'Softens; 0 is sharpest.' },
  { key: 'aberration', label: 'Chromatic aberration', min: 0, max: 0.002, step: 0.0001,
    hint: 'Colour fringing. Costs edge clarity.' },
  { key: 'trails', label: 'Motion trails', min: 0, max: 0.95, step: 0.01,
    hint: 'Afterimage persistence, BROADCAST mode only. High values smear the scene; 0 turns it off.' },
];

function load() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULTS, ...JSON.parse(raw) } : { ...DEFAULTS };
  } catch {
    return { ...DEFAULTS };
  }
}

function save(cfg) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg));
  } catch {
    /* non-fatal */
  }
}

let cfg = { ...DEFAULTS };
let state = null;

/** Backdrop is the one setting with no readable counterpart, so track it. */
let appliedBackdrop = null;

/**
 * Push the current settings onto the live three.js objects, writing only where
 * the live value has drifted. Called every frame, so it must stay allocation-free
 * and must not touch the DOM.
 */
function apply() {
  if (!state) return;

  const isFocus = state.qualityMode === 'focus';
  const isBroadcast = state.qualityMode === 'broadcast';

  const r = state.renderer;
  if (r) {
    if (r.toneMappingExposure !== cfg.exposure) r.toneMappingExposure = cfg.exposure;
    // A dark clear colour restores the black point that the transparent canvas
    // was giving away to the page background behind it.
    if (appliedBackdrop !== cfg.backdrop) {
      try {
        r.setClearColor(0x050a12, cfg.backdrop);
        appliedBackdrop = cfg.backdrop;
      } catch { /* ignore */ }
    }
  }

  const bloom = state.bloomPass;
  if (bloom) {
    // Relative, so FOCUS keeps upstream's reduced bloom.
    const want = isFocus ? cfg.bloomStrength * FOCUS_BLOOM_RATIO : cfg.bloomStrength;
    if (bloom.strength !== want) bloom.strength = want;
    if (bloom.threshold !== cfg.bloomThreshold) bloom.threshold = cfg.bloomThreshold;
    if (bloom.radius !== cfg.bloomRadius) bloom.radius = cfg.bloomRadius;
  }

  const film = state.filmPass;
  if (film) {
    // Upstream keeps grain off in FOCUS; respect that, and treat 0 as "off"
    // everywhere so a cinematic burst cannot switch it back on.
    const on = cfg.grain > 0.001 && !isFocus;
    if (film.enabled !== on) film.enabled = on;
    // FilmPass uniform naming has moved around across three releases (it is
    // `intensity` in 0.170); set whichever exists rather than assuming one.
    const u = film.uniforms;
    const slot = u?.intensity || u?.nIntensity;
    if (slot && slot.value !== cfg.grain) slot.value = cfg.grain;
  }

  const rgb = state.rgbShiftPass;
  if (rgb) {
    const on = cfg.aberration > 0.00001 && !isFocus;
    if (rgb.enabled !== on) rgb.enabled = on;
    const amount = rgb.uniforms?.amount;
    if (amount && amount.value !== cfg.aberration) amount.value = cfg.aberration;
  }

  const after = state.afterimagePass;
  if (after) {
    // Upstream gates this to BROADCAST; only the persistence is ours, plus the
    // ability to switch it off entirely.
    const on = cfg.trails > 0.001 && isBroadcast;
    if (after.enabled !== on) after.enabled = on;
    const damp = after.uniforms?.damp;
    if (damp && damp.value !== cfg.trails) damp.value = cfg.trails;
  }
}

/**
 * Hold the settings against the three upstream paths that rewrite them. A frame
 * loop rather than event listeners because one of those paths is a 6s timeout
 * inside `enableCinematicBurst()` with no observable trigger.
 */
let holding = false;
function startHold() {
  if (holding) return;
  holding = true;
  const tick = () => {
    apply();
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function buildPanel() {
  const host = document.body;
  if (document.getElementById('sq-panel')) return;

  const btn = document.createElement('button');
  btn.type = 'button';
  btn.id = 'sq-toggle';
  btn.className = 'sq-toggle';
  btn.textContent = 'VISUALS';
  btn.title = 'Tune the 3D scene (contrast, bloom, grain)';

  const panel = document.createElement('div');
  panel.id = 'sq-panel';
  panel.className = 'sq-panel hidden';
  panel.innerHTML = `
    <div class="sq-head">
      <span>Scene quality</span>
      <button type="button" class="sq-x" id="sq-close" title="Close">✕</button>
    </div>
    <div class="sq-body">
      ${CONTROLS.map((c) => `
        <label class="sq-row" title="${c.hint}">
          <span class="sq-label">${c.label}</span>
          <input type="range" class="sq-range" data-key="${c.key}"
                 min="${c.min}" max="${c.max}" step="${c.step}">
          <output class="sq-val" data-out="${c.key}"></output>
        </label>`).join('')}
      <div class="sq-actions">
        <button type="button" class="sq-btn" id="sq-reset">Recommended</button>
        <button type="button" class="sq-btn" id="sq-upstream">Upstream defaults</button>
      </div>
      <p class="sq-note">Saved locally. Delete <code>modules/scene-quality/</code> to restore upstream behaviour.</p>
    </div>`;

  host.appendChild(btn);
  host.appendChild(panel);

  const sync = () => {
    for (const c of CONTROLS) {
      const input = panel.querySelector(`input[data-key="${c.key}"]`);
      const out = panel.querySelector(`output[data-out="${c.key}"]`);
      if (input) input.value = String(cfg[c.key]);
      if (out) out.textContent = Number(cfg[c.key]).toFixed(c.step < 0.001 ? 4 : 2);
    }
  };

  panel.addEventListener('input', (ev) => {
    const key = ev.target?.dataset?.key;
    if (!key) return;
    cfg[key] = parseFloat(ev.target.value);
    apply();
    save(cfg);
    sync();
  });

  btn.addEventListener('click', () => panel.classList.toggle('hidden'));
  panel.querySelector('#sq-close').addEventListener('click', () => panel.classList.add('hidden'));
  panel.querySelector('#sq-reset').addEventListener('click', () => {
    cfg = { ...DEFAULTS }; apply(); save(cfg); sync();
  });
  // An explicit way back to upstream's look, so this is never a one-way door.
  panel.querySelector('#sq-upstream').addEventListener('click', () => {
    cfg = { ...UPSTREAM }; apply(); save(cfg); sync();
  });

  sync();
}

export async function registerUI(ctx) {
  state = ctx?.state;
  if (!state) {
    console.warn('[scene-quality] no state in ctx — nothing to tune');
    return;
  }
  cfg = load();
  apply();
  buildPanel();
  // Covers the quality cycle (button or key), the cinematic burst, and the case
  // where the composer is not built yet when this runs.
  startHold();
}
