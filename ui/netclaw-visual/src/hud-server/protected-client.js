import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';

const METHODS = new Set(['owner.login', 'owner.session', 'owner.logout', 'catalog', 'prepare', 'combined_prepare', 'combined_status', 'combined_cancel', 'decision', 'status', 'reconcile', 'revoke', 'mobile.enrollment.info', 'mobile.enrollment.issue', 'mobile.enrollment.status']);
export class ProtectedError extends Error {
  constructor(code = 'unavailable', status = 503) { super(code); this.code = code; this.status = status; }
}

/** JSON.parse alone silently accepts duplicate authority fields. */
export function strictJson(source) {
  let at = 0;
  const space = () => { while (/\s/.test(source[at] || '') && at < source.length) at++; };
  const string = () => {
    const start = at++;
    while (at < source.length) {
      if (source[at] === '\\') { at += 2; continue; }
      if (source[at++] === '"') return JSON.parse(source.slice(start, at));
    }
    throw Error('Invalid JSON');
  };
  const value = depth => {
    if (depth > 64) throw Error('JSON nesting exceeds limit');
    space(); const token = source[at];
    if (token === '"') { string(); return; }
    if (token === '{' || token === '[') {
      const object = token === '{', end = object ? '}' : ']'; at++; space();
      if (source[at] === end) { at++; return; }
      const keys = new Set();
      while (at < source.length) {
        if (object) {
          if (source[at] !== '"') throw Error('Invalid JSON');
          const key = string(); if (keys.has(key)) throw Error('Duplicate JSON key'); keys.add(key);
          space(); if (source[at++] !== ':') throw Error('Invalid JSON');
        }
        value(depth + 1); space();
        if (source[at] === end) { at++; return; }
        if (source[at++] !== ',') throw Error('Invalid JSON'); space();
      }
      throw Error('Invalid JSON');
    }
    const match = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(source.slice(at));
    if (!match) throw Error('Invalid JSON'); at += match[0].length;
  };
  value(0); space(); if (at !== source.length) throw Error('Invalid JSON');
  return JSON.parse(source);
}

function ownedStat(target, directory = false) {
  const stat = fs.lstatSync(target);
  if (stat.isSymbolicLink() || (directory ? !stat.isDirectory() : !stat.isFile()) || stat.uid !== process.getuid() || (stat.mode & 0o777) !== (directory ? 0o700 : 0o600)) throw Error('Private file ownership');
  return stat;
}
function readPrivate(file, limit) {
  const before = ownedStat(file), fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
  try {
    const after = fs.fstatSync(fd);
    if (after.ino !== before.ino || after.dev !== before.dev || after.size > limit || after.uid !== process.getuid() || (after.mode & 0o777) !== 0o600) throw Error('Private file changed');
    const buffer = Buffer.alloc(limit + 1); let size = 0, count;
    while ((count = fs.readSync(fd, buffer, size, buffer.length - size, null)) > 0) { size += count; if (size > limit) throw Error('Private file too large'); }
    return buffer.subarray(0, size).toString('utf8');
  } finally { fs.closeSync(fd); }
}

export function readProtectedDescriptor(installation) {
  try {
    const directory = path.join(installation.home, 'netclaw-federation');
    // A symlink in the selected-home chain cannot redirect the private bridge.
    let cursor = directory;
    while (cursor !== path.dirname(cursor)) { if (fs.lstatSync(cursor).isSymbolicLink()) throw Error('Symlink parent'); cursor = path.dirname(cursor); }
    ownedStat(directory, true);
    const descriptor = strictJson(readPrivate(path.join(directory, 'protected-operator.json'), 4096));
    const keys = ['schemaVersion', 'installationId', 'port', 'generation', 'credentialVariable'];
    if (!descriptor || Object.keys(descriptor).length !== keys.length || keys.some(key => !Object.hasOwn(descriptor, key)) || descriptor.schemaVersion !== 1 || descriptor.installationId !== installation.installationId || !Number.isInteger(descriptor.port) || descriptor.port < 1 || descriptor.port > 65535 || !(typeof descriptor.generation === 'string' && descriptor.generation.length > 0 && descriptor.generation.length <= 200 || Number.isSafeInteger(descriptor.generation) && descriptor.generation > 0) || descriptor.credentialVariable !== 'NETCLAW_PROTECTED_OPERATOR_TOKEN') throw Error('Invalid bridge');
    const environment = readPrivate(path.join(directory, 'protected-operator.env'), 4096);
    const rows = environment.split(/\r?\n/).filter(line => line.trim() && !line.trim().startsWith('#'));
    if (rows.length !== 1) throw Error('Invalid credential file');
    const match = /^NETCLAW_PROTECTED_OPERATOR_TOKEN=([A-Za-z0-9_-]{32,256})$/.exec(rows[0]);
    if (!match) throw Error('Invalid credential');
    return { ...descriptor, token: match[1] };
  } catch { throw new ProtectedError('bridge_unavailable'); }
}

export function createProtectedClient(installation, { readDescriptor = readProtectedDescriptor, timeout = 30000 } = {}) {
  return { async call(method, params) {
    if (!METHODS.has(method)) throw new ProtectedError('invalid_method', 400);
    const binding = readDescriptor(installation), body = JSON.stringify({ method, params });
    if (Buffer.byteLength(body) > 1024 * 1024) throw new ProtectedError('payload_too_large', 413);
    return new Promise((resolve, reject) => {
      let deadline;
      const fail = () => { clearTimeout(deadline); reject(new ProtectedError('bridge_unavailable')); };
      const request = http.request({ hostname: '127.0.0.1', port: binding.port, path: '/operator', method: 'POST', headers: { Authorization: `Bearer ${binding.token}`, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(body) } }, response => {
        const chunks = []; let size = 0;
        response.on('data', chunk => { size += chunk.length; if (size > 1024 * 1024) { response.destroy(); fail(); } else chunks.push(chunk); });
        response.on('error', fail);
        response.on('end', () => {
          try {
            // A restart/rebind during an awaited request invalidates its response.
            const active = readDescriptor(installation);
            if (active.generation !== binding.generation || active.port !== binding.port || active.token !== binding.token) throw Error('Bridge changed');
            const value = strictJson(Buffer.concat(chunks).toString('utf8'));
            clearTimeout(deadline);
            if (response.statusCode >= 200 && response.statusCode < 300 && value.ok === true && Object.hasOwn(value, 'result')) return resolve(value.result);
            const status = [400, 401, 403, 404, 409, 413, 429, 503].includes(response.statusCode) ? response.statusCode : 503;
            const code = /^[a-z][a-z0-9_]{0,79}$/.test(value.error?.code || '') ? value.error.code : 'bridge_unavailable';
            reject(new ProtectedError(code, status));
          } catch { fail(); }
        });
      });
      deadline = setTimeout(() => { request.destroy(); fail(); }, timeout);
      request.setTimeout(timeout, () => { request.destroy(); fail(); });
      request.on('error', fail); request.end(body);
    });
  } };
}
