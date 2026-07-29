/**
 * HUD module loader (browser side).
 *
 * Counterpart to ../module-loader.js. Mounts the UI half of each configured
 * module. See modules/README.md for the module contract.
 *
 * Discovery uses import.meta.glob, which Vite resolves at build time, so:
 *   - modules that do not exist cost nothing
 *   - a module whose UI is never mounted is still code-split out
 *   - there is no dynamic path concatenation for the bundler to give up on
 *
 * "Configured" is decided by the server (it owns .env), so we ask
 * GET /api/modules rather than duplicating the rule in the browser. A module
 * that is present but unconfigured mounts nothing — no tab, no panel, no
 * half-initialised UI.
 */

// Negative patterns keep `_`/`.`-prefixed directories out of the bundle entirely,
// so modules/_example/ costs nothing at build time. The runtime filter below is
// kept as a second line of defence rather than relying on glob semantics alone.
// eslint-disable-next-line import/no-unresolved
const MODULE_UIS = import.meta.glob([
  '../modules/*/ui.js',
  '!../modules/_*/ui.js',
  '!../modules/.*/ui.js',
]);

/** '../modules/foo/ui.js' -> 'foo' */
function idFromPath(p) {
  const m = /\/modules\/([^/]+)\/ui\.js$/.exec(p);
  return m ? m[1] : null;
}

/**
 * @param {object} ctx published surface handed to module UIs
 * @returns {Promise<{mounted:string[], skipped:string[], failed:string[]}>}
 */
export async function loadModuleUIs(ctx) {
  const result = { mounted: [], skipped: [], failed: [] };

  const paths = Object.keys(MODULE_UIS)
    .filter((p) => {
      const id = idFromPath(p);
      return id && !id.startsWith('_') && !id.startsWith('.');
    });
  if (!paths.length) return result;

  let index = { modules: [] };
  try {
    const res = await fetch('/api/modules');
    if (res.ok) index = await res.json();
  } catch {
    // Server unreachable — mount nothing rather than guess at configuration.
    return result;
  }
  const configured = new Set(
    (index.modules || []).filter((m) => m.configured).map((m) => m.id),
  );

  for (const p of paths) {
    const id = idFromPath(p);
    if (!configured.has(id)) {
      result.skipped.push(id);
      continue;
    }
    try {
      const mod = await MODULE_UIS[p]();
      if (typeof mod.registerUI === 'function') {
        await mod.registerUI(ctx);
        result.mounted.push(id);
      } else {
        result.failed.push(id);
        console.error(`[modules] ${id}: ui.js does not export registerUI()`);
      }
    } catch (err) {
      result.failed.push(id);
      console.error(`[modules] ${id}: UI failed to mount — ${err.message}`);
    }
  }

  if (result.mounted.length || result.failed.length || result.skipped.length) {
    console.log(
      `[modules] UI mounted: ${result.mounted.join(', ') || 'none'}`
      + (result.skipped.length ? ` · unconfigured: ${result.skipped.join(', ')}` : '')
      + (result.failed.length ? ` · failed: ${result.failed.join(', ')}` : ''),
    );
  }
  return result;
}
