import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { strictJson } from './protected-client.js';

export const ASSET_LIMITS = Object.freeze({ entries: 256, asset: 8 * 1024 * 1024, total: 32 * 1024 * 1024 });
export const sha256 = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const plain = value => value && typeof value === 'object' && !Array.isArray(value);
const exact = (value, keys) => plain(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key));
export const assetPath = value => typeof value === 'string' && (value === 'index.html' || /^(?:assets|logos)\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-][A-Za-z0-9_.-]*\.(?:js|css|png|svg|jpg|jpeg|webp|woff2?)$/.test(value)) && !value.split('/').some(part => part.startsWith('.') || part.includes('..'));

export function noSymlink(target) {
  if (typeof target !== 'string' || !path.isAbsolute(target) || path.normalize(target) !== target) throw Error('invalid_path');
  let cursor = target;
  while (cursor !== path.dirname(cursor)) { if (fs.lstatSync(cursor).isSymbolicLink()) throw Error('symlink_refused'); cursor = path.dirname(cursor); }
}
export function boundedFile(target, limit, privateFile = false) {
  noSymlink(target);
  const before = fs.lstatSync(target);
  if (!before.isFile() || before.size > limit || privateFile && (before.uid !== process.getuid() || (before.mode & 0o777) !== 0o600)) throw Error('invalid_file');
  const fd = fs.openSync(target, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  try {
    const after = fs.fstatSync(fd);
    if (before.ino !== after.ino || before.dev !== after.dev || after.size > limit || privateFile && (after.uid !== process.getuid() || (after.mode & 0o777) !== 0o600)) throw Error('file_changed');
    const buffer = Buffer.alloc(limit + 1); let size = 0, count;
    while ((count = fs.readSync(fd, buffer, size, buffer.length - size, null)) > 0) { size += count; if (size > limit) throw Error('file_too_large'); }
    return buffer.subarray(0, size);
  } finally { fs.closeSync(fd); }
}

/** Build-time closure follows the Vite entry graph, plus literal HTML/CSS assets. */
export function buildProtectedManifest(dist) {
  noSymlink(dist);
  const graph = strictJson(boundedFile(path.join(dist, '.vite/manifest.json'), 1024 * 1024).toString('utf8'));
  if (!plain(graph) || graph['index.html']?.isEntry !== true) throw Error('missing_hud_entry');
  const names = new Set(['index.html']), visited = new Set();
  const add = name => { if (!assetPath(name)) throw Error('invalid_asset'); names.add(name); if (names.size > ASSET_LIMITS.entries) throw Error('asset_count'); };
  const visit = key => {
    if (visited.has(key)) return; visited.add(key);
    const row = graph[key]; if (!plain(row) || typeof row.file !== 'string') throw Error('invalid_build_graph');
    add(row.file);
    for (const key of ['css', 'assets']) for (const file of row[key] || []) add(file);
    for (const key of ['imports', 'dynamicImports']) for (const dependency of row[key] || []) visit(dependency);
  };
  visit('index.html');
  const html = boundedFile(path.join(dist, 'index.html'), ASSET_LIMITS.asset).toString('utf8');
  for (const match of html.matchAll(/\b(?:src|href)=["']([^"']+)["']/g)) {
    if (!match[1].startsWith('/') || match[1].startsWith('//')) throw Error('nonlocal_entry_asset');
    add(match[1].slice(1));
  }
  let total = 0;
  const files = [];
  for (const name of names) {
    const bytes = boundedFile(path.join(dist, name), ASSET_LIMITS.asset); total += bytes.length;
    if (total > ASSET_LIMITS.total) throw Error('asset_total');
    files.push({ path: name, sha256: sha256(bytes), size: bytes.length });
    if (name.endsWith('.css')) for (const match of bytes.toString('utf8').matchAll(/url\(\s*["']?([^\s"')]+)["']?\s*\)/g)) {
      if (match[1].startsWith('data:')) continue;
      const resolved = match[1].startsWith('/') ? match[1].slice(1) : path.posix.normalize(path.posix.join(path.posix.dirname(name), match[1]));
      add(resolved);
    }
  }
  return { schemaVersion: 1, entry: 'index.html', files: files.sort((a, b) => a.path.localeCompare(b.path)) };
}

/** Pin bytes once at startup; later filesystem edits cannot change a response. */
export function loadProtectedAssets({ dist, manifest, manifestSha256 }) {
  noSymlink(dist);
  if (!/^[a-f0-9]{64}$/.test(manifestSha256)) throw Error('invalid_manifest_digest');
  const raw = boundedFile(manifest, 128 * 1024);
  if (sha256(raw) !== manifestSha256) throw Error('manifest_changed');
  const value = strictJson(raw.toString('utf8'));
  if (!exact(value, ['schemaVersion', 'entry', 'files']) || value.schemaVersion !== 1 || value.entry !== 'index.html' || !Array.isArray(value.files) || value.files.length < 2 || value.files.length > ASSET_LIMITS.entries) throw Error('invalid_manifest');
  const files = new Map(); let total = 0;
  for (const row of value.files) {
    if (!exact(row, ['path', 'size', 'sha256']) || !assetPath(row.path) || files.has('/' + row.path) || !Number.isSafeInteger(row.size) || row.size < 0 || row.size > ASSET_LIMITS.asset || !/^[a-f0-9]{64}$/.test(row.sha256)) throw Error('invalid_asset');
    total += row.size; if (total > ASSET_LIMITS.total) throw Error('asset_total');
    const bytes = boundedFile(path.join(dist, row.path), ASSET_LIMITS.asset);
    if (bytes.length !== row.size || sha256(bytes) !== row.sha256) throw Error('asset_changed');
    files.set('/' + row.path, bytes);
  }
  if (!files.has('/index.html')) throw Error('missing_entry');
  return files;
}
