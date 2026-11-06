import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { buildProtectedManifest, sha256 } from './protected-assets.js';
import { createProtectedServer, readProtectedServerConfig } from './protected-server.js';
import { peerChatBody } from './cloud-federation.js';
import { remoteHudRoute, projectRemoteHud } from './remote-hud.js';

const ID = '00000000-0000-4000-8000-000000000177', origin = 'https://r06.example.test';
const listen = server => new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const stop = server => { server.closeAllConnections(); return new Promise(resolve => server.close(resolve)); };
function files(t) {
  const root = fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()), 'r06-cloud-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  const write = (name, value) => { const file = path.join(root, name); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value), { mode: 0o600 }); return file; };
  write('home/netclaw-hud/installation.json', { schemaVersion: 1, installationId: ID });
  write('home/netclaw-federation/ordinary-cloud.json', { schemaVersion: 1, installationId: ID, role: 'border', access: { mode: 'open-lab' } });
  for (const name of ['index.html','canvas.html']) write('dist/' + name, '<script type="module" src="/assets/hud.js"></script>');
  write('dist/assets/hud.js', '/* fixture */');
  write('dist/.vite/manifest.json', Object.fromEntries(['index.html','canvas.html'].map(name => [name, { file: 'assets/hud.js', isEntry: true }])));
  const dist = path.join(root, 'dist'), manifest = write('assets.json', buildProtectedManifest(dist, { workspace: true }));
  const conversationConfig = write('conversation/openclaw.json', {});
  const workspace = { schemaVersion: 1, mode: 'ordinary-federation', installationId: ID, upstream: 'http://127.0.0.1:13005', conversationHome: path.dirname(conversationConfig), conversationConfig, features: ['overview','peers','chat'] };
  const workspacePath = write('workspace.json', workspace);
  const config = { schemaVersion: 1, mode: 'ordinary-federation', installationId: ID, kind: 'openclaw', home: path.join(root, 'home'), origin, host: '127.0.0.1', port: 18000, dist, manifest, manifestSha256: sha256(fs.readFileSync(manifest)), access: { mode: 'open-lab' }, workspace: { path: workspacePath, sha256: sha256(fs.readFileSync(workspacePath)) }, daemonUrl: 'http://127.0.0.1:8179' };
  const file = write('cloud.json', config);
  return { root, write, config, workspace, file };
}

test('explicit ordinary config refuses identity, mode, protected markers and boundary drift', t => {
  const f = files(t);
  assert.equal(readProtectedServerConfig(f.file).mode, 'ordinary-federation');
  for (const change of [{ mode: 'protected' }, { daemonUrl: 'http://example.test:8179' }, { daemonUrl: f.workspace.upstream }, { origin: origin + '/' }, { installationId: 'other' }, { extra: true }, { access: { mode: 'owner' } }]) {
    f.write('bad.json', { ...f.config, ...change });
    assert.throws(() => readProtectedServerConfig(path.join(f.root, 'bad.json')));
  }
  f.write('home/netclaw-federation/protected-profile.json', {});
  assert.throws(() => readProtectedServerConfig(f.file), /protected/);
});

test('ordinary edge advertises truthful capability, forwards peer chat once, blocks controls and foreign origins', async t => {
  const f = files(t), calls = [];
  const backend = http.createServer(async (req, res) => {
    let body = ''; for await (const chunk of req) body += chunk;
    calls.push({ path: req.url, body, headers: req.headers });
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify(req.url === '/api/runtime' ? { kind: 'openclaw', installationId: ID, remoteHudBackend: { schema: 1, mode: 'ordinary-federation', features: f.workspace.features } } : { source: 'as65002-192.0.2.2', trust: 'remote-untrusted', text: 'fixture' }));
  });
  await listen(backend); t.after(() => stop(backend));
  f.workspace.upstream = `http://127.0.0.1:${backend.address().port}`;
  f.write('workspace.json', f.workspace); f.config.workspace.sha256 = sha256(fs.readFileSync(f.config.workspace.path)); f.write('cloud.json', f.config);
  const server = createProtectedServer(readProtectedServerConfig(f.file), { client: { call: () => assert.fail('No enrollment/native operation expected') } });
  await listen(server); t.after(() => stop(server));
  const request = (route, method = 'GET', body, headers = {}) => new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port: server.address().port, path: route, method, headers: { Host: 'r06.example.test', Origin: origin, 'X-NetClaw-Installation': ID, 'Content-Type': 'application/json', ...headers } }, res => {
      let text = ''; res.on('data', chunk => text += chunk); res.on('end', () => resolve({ status: res.statusCode, value: JSON.parse(text) }));
    }); req.on('error', reject); req.end(body ? JSON.stringify(body) : undefined);
  });
  const runtime = (await request('/api/runtime')).value;
  assert.deepEqual(runtime.capabilities.externalFederation, { schema: 1, execution: 'ordinary', peerChat: true });
  assert.equal(runtime.capabilities.protectedProfile, undefined);
  assert.equal(runtime.access.principal.display_name, 'Unauthenticated lab operator');
  const body = { peer: 'as65002-192.0.2.2', text: 'hello' };
  assert.equal((await request('/api/n2n/chat', 'POST', body)).status, 200);
  assert.equal(calls.filter(v => v.path === '/api/n2n/chat').length, 1);
  assert.equal((await request('/api/n2n/chat', 'POST', body, { Origin: 'https://foreign.test' })).status, 403);
  assert.equal((await request('/api/n2n/chat', 'POST', body, { 'X-NetClaw-Installation': 'other' })).status, 409);
  for (const route of ['/api/hud/operations/catalog','/api/hud/owner/session','/api/mcp/configuration','/api/env','/api/n2n/consent']) assert.equal((await request(route)).status, 404);
  assert.equal(calls.filter(v => v.path === '/api/n2n/chat').length, 1);
});

test('peer chat route requires explicit mode; payload and peer projection are bounded', () => {
  assert.equal(remoteHudRoute('POST', '/api/n2n/chat', ['peers']), false);
  assert.equal(remoteHudRoute('POST', '/api/n2n/chat', ['peers'], true), true);
  assert.equal(remoteHudRoute('POST', '/api/n2n/chat?peer=x', ['peers'], true), false);
  for (const body of [{ peer: 'http://elsewhere', text: 'x' }, { peer: 'as65001-192.0.2.1', text: 'x', command: 'exec' }, { peer: 'as65001-192.0.2.1', text: 'x'.repeat(65537) }, { peer: 'as65001-192.0.2.1', text: 'x', session_id: '../other' }]) assert.throws(() => peerChatBody(body));
  const value = projectRemoteHud('/api/n2n', { peers: [{ identity: 'peer', chat_enabled: true, inventory: { version: 2, stale: false, skills: [{ name: 'subnet-calculator', invocable: true, private: 'hidden' }] } }] });
  assert.equal(value.peers[0].chat_enabled, true); assert.equal(value.peers[0].inventory.version, 2);
  assert.equal(value.peers[0].inventory.skills[0].private, undefined);
});
