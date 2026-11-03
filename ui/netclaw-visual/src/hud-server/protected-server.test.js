import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import net from 'node:net';
import { createProtectedServer, readProtectedServerConfig, PROTECTED_CSP } from './protected-server.js';
import { buildProtectedManifest, loadProtectedAssets, sha256 } from './protected-assets.js';
import { ProtectedError } from './protected-client.js';
const ID = '00000000-0000-4000-8000-000000000172', ORIGIN = 'https://r03.example.test', COOKIE = 'c'.repeat(43), CSRF = 's'.repeat(43), TICKET = 't'.repeat(43);
function files(t) {
  const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-172-hud-'))); t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const write = (name, value) => { const target = path.join(root, name); fs.mkdirSync(path.dirname(target), { recursive: true, mode: 0o700 }); fs.writeFileSync(target, typeof value === 'string' ? value : JSON.stringify(value), { mode: 0o600 }); return target; };
  write('dist/index.html', '<!doctype html><script type="module" src="/assets/hud.js"></script><link href="/assets/hud.css" rel="stylesheet"><link rel="icon" href="/logos/logo.png">');
  write('dist/assets/hud.js', 'document.body.dataset.ready="true";'); write('dist/assets/hud.css', 'body{color:white}'); write('dist/logos/logo.png', 'fixture');
  write('dist/.vite/manifest.json', { 'index.html': { file: 'assets/hud.js', isEntry: true, css: ['assets/hud.css'] } });
  write('home/netclaw-hud/installation.json', { schemaVersion: 1, installationId: ID });
  write('home/netclaw-federation/protected-profile.json', { schemaVersion: 1, role: 'border', identity: { installation_id: ID } });
  write('home/netclaw-federation/protected-operator.json', { schemaVersion: 1, installationId: ID, port: 17777, generation: 'fixture', credentialVariable: 'NETCLAW_PROTECTED_OPERATOR_TOKEN' });
  write('home/netclaw-federation/protected-operator.env', 'NETCLAW_PROTECTED_OPERATOR_TOKEN=' + 'f'.repeat(43));
  const manifest = write('assets.json', buildProtectedManifest(path.join(root, 'dist')));
  const config = { schemaVersion: 1, installationId: ID, kind: 'openclaw', home: path.join(root, 'home'), origin: ORIGIN, host: '127.0.0.1', port: 18000, dist: path.join(root, 'dist'), manifest, manifestSha256: sha256(fs.readFileSync(manifest)) };
  const configFile = write('hud.json', config); return { root, write, config, configFile };
}
async function fixture(t) {
  const f = files(t), calls = [], state = { active: true, consumed: false, revokeDuringRead: false };
  const principal = { issuer: 'local', subject: ID, display_name: 'Fixture owner', roles: ['owner'] };
  const projection = () => ({ installation_id: ID, principal, auth_generation: 1, session_hash: sha256(COOKIE), csrf_token: CSRF, expires_ms: Date.now() + 60000 });
  const client = { async call(method, params) {
    calls.push({ method, params });
    if (method === 'owner.login') { if (state.consumed || params.ticket !== TICKET) throw new ProtectedError('ticket_refused', 401); state.consumed = true; return { cookie: COOKIE }; }
    if (method === 'owner.session') { if (!state.active || params.cookie !== COOKIE) throw new ProtectedError('session_refused', 401); return projection(); }
    if (method === 'owner.logout') { state.active = false; return {}; }
    assert.deepEqual(params.auth_context, { principal, auth_generation: 1, session_hash: sha256(COOKIE) });
    if (state.revokeDuringRead) state.active = false;
    return method === 'catalog' ? { revision: 'fixture', members: [] } : { operation_id: 'fixture-operation', client_nonce: 'fixture-nonce' };
  } };
  const server = createProtectedServer(readProtectedServerConfig(f.configFile), { client }); server.listen(0, '127.0.0.1'); await new Promise(resolve => server.once('listening', resolve));
  t.after(() => { server.closeAllConnections(); return new Promise(resolve => server.close(resolve)); });
  const headers = { Host: 'r03.example.test', Origin: ORIGIN, 'X-NetClaw-Installation': ID, Cookie: `__Host-nc_owner_${ID}=${COOKIE}`, 'Content-Type': 'application/json', 'X-NetClaw-CSRF': CSRF };
  const request = (target, method = 'GET', body, extra = {}) => new Promise((resolve, reject) => {
    const req = http.request({ hostname: '127.0.0.1', port: server.address().port, path: target, method, headers: { ...headers, ...extra } }, res => {
      const chunks = []; res.on('data', chunk => chunks.push(chunk)); res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks).toString() }));
    }); req.on('error', reject); req.end(body === undefined ? undefined : typeof body === 'string' ? body : JSON.stringify(body));
  });
  return { ...f, request, server, calls, state };
}
test('startup requires explicit owned identity, Border role, exact HTTPS config and existing bridge', t => {
  const f = files(t); assert.equal(readProtectedServerConfig(f.configFile).installation.installationId, ID);
  for (const change of [{ origin: 'http://r03.example.test' }, { origin: ORIGIN + '/' }, { host: '0.0.0.0' }, { kind: 'hermes' }, { extra: true }, { home: '' }, { port: 0 }, { manifestSha256: '0'.repeat(64) }]) { f.write('bad.json', { ...f.config, ...change }); assert.throws(() => readProtectedServerConfig(path.join(f.root, 'bad.json'))); }
  f.write('home/netclaw-federation/protected-profile.json', { schemaVersion: 1, role: 'member', identity: { installation_id: ID } }); assert.throws(() => readProtectedServerConfig(f.configFile));
  f.write('home/netclaw-federation/protected-profile.json', { schemaVersion: 1, role: 'border', identity: { installation_id: ID }, runtime: {} }); assert.throws(() => readProtectedServerConfig(f.configFile));
});
test('manifest excludes alternate pages and refuses edits, symlinks, malformed or oversized closure', t => {
  const f = files(t); f.write('dist/classic.html', 'not exposed'); f.write('dist/.env', 'not exposed');
  const manifest = buildProtectedManifest(f.config.dist); assert.deepEqual(manifest.files.map(row => row.path), ['assets/hud.css', 'assets/hud.js', 'index.html', 'logos/logo.png']);
  const loaded = loadProtectedAssets(f.config); f.write('dist/assets/hud.js', 'changed'); assert.match(loaded.get('/assets/hud.js').toString(), /dataset/); assert.throws(() => loadProtectedAssets(f.config), /changed/);
  fs.unlinkSync(path.join(f.root, 'dist/assets/hud.js')); fs.symlinkSync(path.join(f.root, 'dist/index.html'), path.join(f.root, 'dist/assets/hud.js')); assert.throws(() => buildProtectedManifest(f.config.dist), /symlink/);
  const unsafe = { schemaVersion: 1, entry: 'index.html', files: [...manifest.files, { path: '../private.js', size: 1, sha256: '0'.repeat(64) }] };
  const name = f.write('unsafe.json', unsafe); assert.throws(() => loadProtectedAssets({ ...f.config, manifest: name, manifestSha256: sha256(fs.readFileSync(name)) }));
});
test('asset count, per-file size and total memory bounds are enforced before serving', t => {
  const f = files(t), base = buildProtectedManifest(f.config.dist);
  for (const value of [{ ...base, files: Array(257).fill(base.files[0]) }, { ...base, files: [{ ...base.files[0], size: 8 * 1024 * 1024 + 1 }, ...base.files.slice(1)] }]) {
    const manifest = f.write('bounded.json', value);
    assert.throws(() => loadProtectedAssets({ ...f.config, manifest, manifestSha256: sha256(fs.readFileSync(manifest)) }));
  }
  const huge = Buffer.alloc(8 * 1024 * 1024), extra = [];
  for (let i = 0; i < 4; i++) { const name = `assets/large-${i}.js`; fs.writeFileSync(path.join(f.config.dist, name), huge); extra.push({ path: name, size: huge.length, sha256: sha256(huge) }); }
  const manifest = f.write('total.json', { ...base, files: [...base.files, ...extra] });
  assert.throws(() => loadProtectedAssets({ ...f.config, manifest, manifestSha256: sha256(fs.readFileSync(manifest)) }), /asset_total/);
});
test('anonymous surface is only entry/assets/bootstrap; exact method routes reject legacy, traversal, HEAD APIs and WebSocket', async t => {
  const f = await fixture(t);
  for (const target of ['/', '/index.html', '/assets/hud.js', '/api/runtime']) { const res = await f.request(target, 'GET', undefined, { Cookie: '' }); assert.equal(res.status, 200); assert.equal(res.headers['cache-control'], 'no-store'); assert.equal(res.headers['content-security-policy'], PROTECTED_CSP); }
  assert.equal((await f.request('/api/hud/operations/catalog', 'GET', undefined, { Cookie: '' })).status, 401);
  for (const target of ['/classic.html', '/canvas.html', '/assessment.html', '/.env', '/assets/../.env', '/%2eenv', '/assets/hud.js?x=1', '/api/chat', '/api/hud/operations/catalog/', '/api/hud/operations/op/decision/']) assert.ok((await f.request(target)).status >= 400, target);
  for (const target of ['/api/runtime', '/api/hud/owner/session', '/api/hud/operations/catalog', '/api/hud/operations/op']) assert.equal((await f.request(target, 'HEAD')).status, 405);
  assert.equal((await f.request('/', 'HEAD')).status, 200);
  const wire = await new Promise((resolve, reject) => { const socket = net.connect(f.server.address().port, '127.0.0.1', () => socket.end('GET /ws HTTP/1.1\r\nHost: r03.example.test\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n')); let text = ''; socket.on('data', b => { text += b; }); socket.on('error', reject); socket.on('end', () => resolve(text)); });
  assert.match(wire, /403 Forbidden/);
});
test('public authority cannot be supplied by forwarded headers; duplicate raw Host and Origin refuse', async t => {
  const f = await fixture(t);
  for (const headers of [{ Host: 'wrong', 'X-Forwarded-Host': 'r03.example.test', 'X-Forwarded-Proto': 'https' }, { Origin: 'https://wrong', 'X-Forwarded-Origin': ORIGIN }, { Origin: 'null' }, { 'Sec-Fetch-Site': 'cross-site' }]) assert.equal((await f.request('/api/runtime', 'GET', undefined, headers)).status, 403);
  for (const pair of ['Host: r03.example.test\r\nHost: r03.example.test', 'Host: r03.example.test\r\nOrigin: ' + ORIGIN + '\r\nOrigin: ' + ORIGIN]) {
    const result = await new Promise((resolve, reject) => { const socket = net.connect(f.server.address().port, '127.0.0.1', () => socket.end(`GET /api/runtime HTTP/1.1\r\n${pair}\r\nConnection: close\r\n\r\n`)); let response = ''; socket.on('data', chunk => { response += chunk; }); socket.on('end', () => resolve(response)); socket.on('error', reject); }); assert.match(result, /HTTP\/1\.1 (?:400|403)/);
  }
});
test('real HTTP facade preserves owner cookie, strict mutations, server-derived identity and post-I/O revocation', async t => {
  const f = await fixture(t);
  const login = await f.request('/api/hud/owner/session', 'POST', { ticket: TICKET }, { 'X-NetClaw-Owner-Bootstrap': '1', Cookie: '' });
  assert.equal(login.status, 200); assert.match(login.headers['set-cookie'][0], /^__Host-nc_owner_/); assert.match(login.headers['set-cookie'][0], /HttpOnly; SameSite=Strict;.*Secure/);
  assert.equal((await f.request('/api/hud/owner/session', 'POST', { ticket: TICKET }, { 'X-NetClaw-Owner-Bootstrap': '1' })).status, 401);
  const candidate = { client_nonce: 'fixture-nonce', catalog_revision: 'fixture', member_id: 'member', model_profile_id: 'model', tool: 'pyats_run_show_command', arguments: {} };
  assert.equal((await f.request('/api/hud/operations', 'POST', candidate, { 'X-NetClaw-CSRF': 'wrong' })).status, 403);
  assert.equal((await f.request('/api/hud/operations', 'POST', { ...candidate, principal: 'forged' })).status, 400);
  assert.equal((await f.request('/api/hud/operations', 'POST', candidate)).status, 200);
  assert.equal(f.calls.filter(row => row.method === 'prepare').length, 1);
  f.state.revokeDuringRead = true; assert.equal((await f.request('/api/hud/operations/catalog')).status, 401);
});
test('production connection and framing bounds are fixed, oversized bodies/headers refuse', async t => {
  const f = await fixture(t); assert.equal(f.server.maxConnections, 64); assert.equal(f.server.headersTimeout, 10000); assert.equal(f.server.requestTimeout, 30000); assert.equal(f.server.keepAliveTimeout, 5000);
  assert.equal((await f.request('/api/hud/owner/session', 'POST', 'x'.repeat(72 * 1024 + 1), { 'X-NetClaw-Owner-Bootstrap': '1' })).status, 413);
  assert.equal((await f.request('/api/runtime', 'GET', undefined, { 'X-Oversized': 'x'.repeat(17000) })).status, 400);
});
