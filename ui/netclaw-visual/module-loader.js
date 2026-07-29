/**
 * HUD module loader (server side).
 *
 * Discovers optional modules under ui/netclaw-visual/modules/ and registers
 * their backend routes. A module is a self-contained directory that adds HUD
 * functionality without editing server.js or src/main.js.
 *
 *   modules/
 *     <id>/
 *       module.json    metadata + requiresEnv
 *       server.js      export function register(app, ctx)   (optional)
 *       ui.js          export function registerUI(ctx)      (optional)
 *       README.md
 *
 * Directories beginning with "_" or "." are skipped, so modules/_example/
 * can ship as documentation without loading.
 *
 * Design notes:
 *   - Registration happens LAST, just before server.listen(), so first-party
 *     routes always take precedence over a module's.
 *   - A module whose requiresEnv keys are unset is discovered but NOT
 *     registered. It is reported as unconfigured via GET /api/modules, and its
 *     UI does not mount. This is what makes a module genuinely optional rather
 *     than present-but-broken.
 *   - Load failures are logged loudly and skipped. One broken module must not
 *     take down the HUD, and it must not fail silently either.
 *   - ctx is a deliberately small published surface (see CTX_KEYS in server.js).
 *     Modules needing more should open an issue rather than reach into globals.
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MODULES_DIR = path.join(__dirname, 'modules');

/** @typedef {{id:string,name:string,description?:string,requiresEnv?:string[]}} ModuleManifest */

function readManifest(dir) {
  const file = path.join(MODULES_DIR, dir, 'module.json');
  if (!fs.existsSync(file)) return null;
  try {
    const m = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (!m.id) m.id = dir;
    return m;
  } catch (err) {
    console.error(`[modules] ${dir}/module.json is not valid JSON: ${err.message}`);
    return null;
  }
}

/** Directory names that are eligible to load. */
export function moduleDirs() {
  if (!fs.existsSync(MODULES_DIR)) return [];
  return fs.readdirSync(MODULES_DIR, { withFileTypes: true })
    .filter((e) => e.isDirectory() && !e.name.startsWith('_') && !e.name.startsWith('.'))
    .map((e) => e.name)
    .sort();
}

/**
 * A module is configured when every key in requiresEnv has a non-empty value,
 * checked against process.env first and then the merged .env files.
 */
function isConfigured(manifest, envLookup) {
  const required = Array.isArray(manifest.requiresEnv) ? manifest.requiresEnv : [];
  const missing = required.filter((k) => !envLookup(k));
  return { configured: missing.length === 0, missing };
}

/**
 * Discover modules and register the backend half of each configured one.
 *
 * @param {import('express').Express} app
 * @param {object} ctx  published helper surface handed to modules
 * @param {(key:string)=>string} envLookup
 * @returns {Promise<Array<{id:string,name:string,configured:boolean,missing:string[],routes:boolean,error?:string}>>}
 */
export async function loadModules(app, ctx, envLookup) {
  const loaded = [];

  for (const dir of moduleDirs()) {
    const manifest = readManifest(dir);
    if (!manifest) {
      loaded.push({
        id: dir, name: dir, configured: false, missing: [], routes: false,
        error: 'missing or invalid module.json',
      });
      continue;
    }

    const { configured, missing } = isConfigured(manifest, envLookup);
    const entry = {
      id: manifest.id,
      name: manifest.name || manifest.id,
      description: manifest.description || '',
      configured,
      missing,
      routes: false,
    };

    if (!configured) {
      console.log(`[modules] ${entry.id}: not configured (needs ${missing.join(', ')}) — skipped`);
      loaded.push(entry);
      continue;
    }

    const serverEntry = path.join(MODULES_DIR, dir, 'server.js');
    if (fs.existsSync(serverEntry)) {
      try {
        const mod = await import(`./modules/${dir}/server.js`);
        if (typeof mod.register === 'function') {
          await mod.register(app, ctx);
          entry.routes = true;
          console.log(`[modules] ${entry.id}: registered`);
        } else {
          entry.error = 'server.js does not export register()';
          console.error(`[modules] ${entry.id}: server.js does not export register()`);
        }
      } catch (err) {
        entry.error = err.message;
        console.error(`[modules] ${entry.id}: failed to load — ${err.message}`);
      }
    } else {
      console.log(`[modules] ${entry.id}: configured (frontend only)`);
    }

    loaded.push(entry);
  }

  return loaded;
}

/**
 * GET /api/modules — which modules exist and whether they are configured.
 * The frontend loader uses this to decide what to mount, so an unconfigured
 * module renders no UI at all.
 */
export function registerModuleIndex(app, loaded) {
  app.get('/api/modules', (req, res) => {
    res.json({
      modules: loaded.map(({ id, name, description, configured, missing, routes, error }) => ({
        id, name, description, configured, missing, routes, error: error || null,
      })),
    });
  });
}
