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
 *   `setQualityMode()` rewrites `bloomPass.strength` and toggles passes on every
 *   quality change, so settings are re-applied after the quality button is used.
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
};

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

/** Push the current settings onto the live three.js objects. */
function apply() {
  if (!state) return;

  if (state.renderer) {
    state.renderer.toneMappingExposure = cfg.exposure;
    // A dark clear colour restores the black point that the transparent canvas
    // was giving away to the page background behind it.
    try { state.renderer.setClearColor(0x050a12, cfg.backdrop); } catch { /* ignore */ }
  }

  if (state.bloomPass) {
    state.bloomPass.strength = cfg.bloomStrength;
    state.bloomPass.threshold = cfg.bloomThreshold;
    state.bloomPass.radius = cfg.bloomRadius;
  }

  if (state.filmPass) {
    state.filmPass.enabled = cfg.grain > 0.001;
    const u = state.filmPass.uniforms;
    // FilmPass uniform naming has moved around across three releases; set
    // whichever exists rather than assuming one.
    if (u?.intensity) u.intensity.value = cfg.grain;
    else if (u?.nIntensity) u.nIntensity.value = cfg.grain;
  }

  if (state.rgbShiftPass) {
    state.rgbShiftPass.enabled = cfg.aberration > 0.00001;
    if (state.rgbShiftPass.uniforms?.amount) {
      state.rgbShiftPass.uniforms.amount.value = cfg.aberration;
    }
  }
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
    cfg = {
      exposure: 1.55, bloomStrength: 1.1, bloomThreshold: 0.5, bloomRadius: 0.55,
      grain: 0.18, aberration: 0.0008, backdrop: 0,
    };
    apply(); save(cfg); sync();
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

  // setQualityMode() rewrites bloom strength and pass enablement, so re-assert
  // after the quality button is used. Next frame, so it lands after upstream's.
  document.getElementById('quality-toggle')?.addEventListener('click', () => {
    requestAnimationFrame(() => apply());
  });

  // The composer may be built after wireUI() on some paths; a couple of late
  // re-applies cost nothing and avoid a race with scene setup.
  setTimeout(apply, 300);
  setTimeout(apply, 1500);
}
