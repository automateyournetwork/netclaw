import test from 'node:test';
import assert from 'node:assert/strict';
import express from 'express';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { mountProtectedOperations, protectedHudConfig, protectedDocumentHeaders } from './protected-operations.js';
import { createProtectedClient, ProtectedError, readProtectedDescriptor, strictJson } from './protected-client.js';

const ID = '00000000-0000-4000-8000-000000000171', COOKIE = 'c'.repeat(43), CSRF = 's'.repeat(43), TICKET = 't'.repeat(43);
const SESSION_HASH = crypto.createHash('sha256').update(COOKIE).digest('hex');
const PRINCIPAL = { issuer: 'local', subject: ID, display_name: 'Fixture owner', roles: ['owner'] };
const CANDIDATE = { client_nonce: 'fixture-nonce', catalog_revision: 'r1', member_id: 'fixture-member', model_profile_id: 'fixture-model', tool: 'pyats_run_show_command', arguments: { device_name: 'fixture-router', command: 'show version', timeout: 30, retries: 1 } };
const REVIEW = { operation_id: 'fixture-operation', client_nonce: CANDIDATE.client_nonce, revision: 1, state: 'review_pending', review_digest: 'd'.repeat(64), review: { principal: PRINCIPAL }, allowed_actions: ['approve', 'deny'] };

async function fixture(t, options = {}) {
  const state = { active: true, consumed: false, hook: null, loginCalls: 0 }, calls = [], config = { enabled: true, secure: false, origins: [] };
  const projection = () => ({ principal: PRINCIPAL, auth_generation: 1, session_hash: SESSION_HASH, csrf_token: CSRF, expires_ms: Date.now() + 3600000, installation_id: ID });
  const client = { async call(method, params) {
    calls.push({ method, params });
    if (method === 'owner.login') {
      state.loginCalls++;
      if (state.consumed || params.ticket !== TICKET) throw new ProtectedError('invalid_ticket', 401);
      state.consumed = true; return { ...projection(), cookie: COOKIE };
    }
    if (method === 'owner.session') {
      if (!state.active || params.cookie !== COOKIE) throw new ProtectedError('session_expired', 401);
      return projection();
    }
    if (method === 'owner.logout') { assert.equal(params.csrf_token, CSRF); state.active = false; return { revoked: true }; }
    assert.deepEqual(params.auth_context, { principal: PRINCIPAL, auth_generation: 1, session_hash: SESSION_HASH });
    if (state.hook) return state.hook(method, params);
    return method === 'catalog' ? { revision: 'r1', members: [] } : REVIEW;
  } };
  const app = express(); const mounted = mountProtectedOperations(app, { installation: { installationId: ID }, config: { ...config, ...options, origins: config.origins }, client });
  app.use(express.json()); app.use((req, _res, next) => { req.headers.cookie = 'nc_hud=legacy'; next(); }); app.get('/legacy', (_req, res) => res.json({ retained: true }));
  const server = app.listen(0, '127.0.0.1'); await new Promise(resolve => server.once('listening', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const url = `http://127.0.0.1:${server.address().port}`; config.origins.push(url);
  const headers = { Origin: url, 'X-NetClaw-Installation': ID, Cookie: `${mounted.cookieName}=${COOKIE}`, 'Content-Type': 'application/json', 'X-NetClaw-CSRF': CSRF };
  const request = (suffix, method = 'GET', body, extra = {}) => fetch(url + suffix, { method, headers: { ...headers, ...extra }, ...(body === undefined ? {} : { body: typeof body === 'string' ? body : JSON.stringify(body) }) });
  return { request, state, calls, headers, url, cookieName: mounted.cookieName };
}

test('profile requires explicit configured exact origins and never accepts wildcard/proxy assumptions', () => {
  assert.equal(protectedHudConfig({}).enabled, false);
  for (const origin of ['', '*', 'null', 'http://example.com', 'https://example.com/path', 'https://example.com/', 'https://a.test,http://localhost:3000']) assert.equal(protectedHudConfig({ N2N_PROTECTED_OPERATIONS: '1', NETCLAW_PROTECTED_HUD_ORIGINS: origin }).enabled, false);
  assert.equal(protectedHudConfig({ N2N_PROTECTED_OPERATIONS: '1', NETCLAW_PROTECTED_HUD_ORIGINS: 'http://127.0.0.1:3000' }).enabled, true);
  assert.equal(protectedHudConfig({ N2N_PROTECTED_OPERATIONS: '1', NETCLAW_PROTECTED_HUD_ORIGINS: 'https://example.com' }).secure, true);
});

test('protected entry document cannot be framed, while existing Canvas embedding and default profiles remain intact', () => {
  for (const [enabled, url, expected] of [[true, '/', true], [true, '/index.html?x=1', true], [true, '/canvas.html?embedded=1', false], [false, '/', false]]) {
    const headers = {}, response = { setHeader(key, value) { headers[key] = value; } }; let next = false;
    protectedDocumentHeaders(enabled)({ url }, response, () => { next = true; });
    assert.equal(next, true); assert.equal(headers['X-Frame-Options'], expected ? 'DENY' : undefined);
    if (expected) assert.equal(headers['Content-Security-Policy'], "frame-ancestors 'none'");
  }
});

test('legacy session cannot authorize operations; independent cookie survives the old rewrite', async t => {
  const f = await fixture(t);
  assert.equal((await f.request('/api/hud/operations/catalog', 'GET', undefined, { Cookie: 'nc_hud=legacy' })).status, 401);
  assert.equal((await f.request('/api/hud/operations/catalog')).status, 200);
  assert.equal((await fetch(f.url + '/legacy')).status, 200);
  const response = await f.request('/api/hud/owner/session');
  assert.equal(response.headers.get('cache-control'), 'no-store'); assert.equal(response.headers.get('x-frame-options'), 'DENY');
  const result = await response.json(); assert.equal(result.authenticated, true); assert.equal(result.session_hash, undefined); assert.equal(result.auth_generation, undefined);
});

test('login requires exact Origin, installation, explicit bootstrap and one-use ticket', async t => {
  const f = await fixture(t);
  const route = '/api/hud/owner/session', extra = { 'X-NetClaw-Owner-Bootstrap': '1' };
  for (const origin of ['null', 'https://evil.test', f.url + '/', f.url + ', ' + f.url]) assert.equal((await f.request(route, 'POST', { ticket: TICKET }, { ...extra, Origin: origin })).status, 403);
  const withoutOrigin = { ...f.headers, ...extra }; delete withoutOrigin.Origin;
  assert.equal((await fetch(f.url + route, { method: 'POST', headers: withoutOrigin, body: JSON.stringify({ ticket: TICKET }) })).status, 403);
  assert.equal((await f.request(route, 'POST', { ticket: TICKET }, { ...extra, 'X-NetClaw-Installation': 'foreign' })).status, 409);
  assert.equal((await f.request(route, 'POST', { ticket: TICKET })).status, 400);
  assert.equal(f.state.loginCalls, 0);
  const response = await f.request(route, 'POST', { ticket: TICKET }, extra);
  assert.equal(response.status, 200); assert.match(response.headers.get('set-cookie'), /HttpOnly; SameSite=Strict/); assert.doesNotMatch(response.headers.get('set-cookie'), /Domain=/);
  assert.equal((await f.request(route, 'POST', { ticket: TICKET }, extra)).status, 401);
});

test('Secure owner cookie is disjoint from local and legacy cookies', async t => {
  const f = await fixture(t, { secure: true });
  const response = await f.request('/api/hud/owner/session', 'POST', { ticket: TICKET }, { 'X-NetClaw-Owner-Bootstrap': '1' });
  assert.match(response.headers.get('set-cookie'), /^__Host-nc_owner_/); assert.match(response.headers.get('set-cookie'), /; Secure$/);
  assert.equal((await f.request('/api/hud/operations/catalog', 'GET', undefined, { Cookie: `nc_owner_${ID}=${COOKIE}` })).status, 401);
});

test('all authority mutations reject CSRF, cross-site, duplicate cookies, unknown fields and duplicate JSON keys', async t => {
  const f = await fixture(t);
  const count = () => f.calls.filter(call => !call.method.startsWith('owner.')).length;
  assert.equal((await f.request('/api/hud/operations', 'POST', CANDIDATE, { 'X-NetClaw-CSRF': 'wrong' })).status, 403);
  assert.equal((await f.request('/api/hud/operations', 'POST', CANDIDATE, { 'Sec-Fetch-Site': 'cross-site' })).status, 403);
  assert.equal((await f.request('/api/hud/operations/catalog', 'GET', undefined, { Cookie: `${f.cookieName}=${COOKIE}; ${f.cookieName}=${COOKIE}` })).status, 401);
  assert.equal((await f.request('/api/hud/operations', 'POST', { ...CANDIDATE, auth_context: { principal: PRINCIPAL } })).status, 400);
  assert.equal((await f.request('/api/hud/operations', 'POST', JSON.stringify(CANDIDATE).replace('"command":"show version"', '"command":"show version","command":"reload"'))).status, 400);
  assert.equal((await f.request('/api/hud/operations', 'POST', CANDIDATE, { 'Content-Type': 'text/plain' })).status, 400);
  assert.equal((await f.request('/api/hud/operations', 'POST', { ...CANDIDATE, arguments: { huge: 'x'.repeat(80000) } })).status, 413);
  assert.equal(count(), 0);
  assert.equal((await f.request('/api/hud/operations', 'POST', CANDIDATE)).status, 200);
  assert.equal(count(), 1);
});

test('fixed routes carry derived identity and no arbitrary method/tool/authority proxy', async t => {
  const f = await fixture(t);
  assert.equal((await f.request('/api/hud/operations/fixture-operation/decision', 'POST', { revision: 1, review_digest: 'd'.repeat(64), decision: 'approve' })).status, 200);
  assert.equal((await f.request('/api/hud/operations/fixture-operation/reconcile', 'POST', {})).status, 200);
  assert.equal((await f.request('/api/hud/operations/fixture-operation/revoke', 'POST', {})).status, 200);
  assert.equal((await f.request('/api/hud/operations?client_nonce=fixture-nonce')).status, 200);
  assert.equal((await f.request('/api/hud/operations?client_nonce=a&client_nonce=b')).status, 400);
  assert.equal((await f.request('/api/hud/operations/fixture-operation/reconcile', 'POST', { method: 'submit' })).status, 400);
  assert.equal((await f.request('/api/hud/operations/fixture-operation/submit', 'POST', {})).status, 404);
  assert.deepEqual(f.calls.filter(call => !call.method.startsWith('owner.')).map(call => call.method), ['decision', 'reconcile', 'revoke', 'status']);
});

test('revocation during I/O suppresses private output; backend errors are sanitized', async t => {
  const f = await fixture(t); let finish;
  f.state.hook = () => new Promise(resolve => { finish = resolve; });
  const pending = f.request('/api/hud/operations/fixture-operation');
  while (!finish) await new Promise(resolve => setTimeout(resolve, 1));
  f.state.active = false; finish({ secret_evidence: 'MUST-NOT-RETURN' });
  const response = await pending; assert.equal(response.status, 401); assert.doesNotMatch(await response.text(), /MUST-NOT-RETURN/);
  f.state.active = true; f.state.hook = () => { throw Error('PRIVATE-CREDENTIAL'); };
  const error = await f.request('/api/hud/operations/fixture-operation'); assert.equal(error.status, 503); assert.doesNotMatch(await error.text(), /PRIVATE-CREDENTIAL/);
});

test('logout revokes authority; login attempts are bounded without exposing ticket values', async t => {
  const f = await fixture(t);
  assert.equal((await f.request('/api/hud/owner/session', 'DELETE', {})).status, 200);
  assert.equal((await f.request('/api/hud/operations/catalog')).status, 401);
  for (let i = 0; i < 10; i++) await f.request('/api/hud/owner/session', 'POST', { ticket: 'q'.repeat(43) }, { 'X-NetClaw-Owner-Bootstrap': '1' });
  const response = await f.request('/api/hud/owner/session', 'POST', { ticket: TICKET }, { 'X-NetClaw-Owner-Bootstrap': '1' });
  assert.equal(response.status, 429); assert.doesNotMatch(await response.text(), new RegExp(TICKET));
});

test('disabled profile performs no bridge call and legacy route remains unchanged', async t => {
  const f = await fixture(t, { enabled: false });
  assert.equal((await f.request('/api/hud/operations/catalog')).status, 404); assert.equal(f.calls.length, 0);
  assert.equal((await fetch(f.url + '/legacy')).status, 200);
});

test('strict parser rejects duplicate keys at every depth without rewriting argument strings', () => {
  assert.throws(() => strictJson('{"a":[{"x":1,"x":2}]}'));
  assert.throws(() => strictJson('{"a":1,"\\u0061":2}'));
  assert.throws(() => strictJson('{} trailing'));
  assert.deepEqual(strictJson('{"arguments":{"command":" show version  "},"unicode":"Montréal"}'), { arguments: { command: ' show version  ' }, unicode: 'Montréal' });
});

test('private descriptor validates file ownership/mode/symlinks and contains no token', t => {
  const home = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'r02-hud-descriptor-')));
  t.after(() => fs.rmSync(home, { recursive: true, force: true }));
  const directory = path.join(home, 'netclaw-federation'); fs.mkdirSync(directory, { mode: 0o700 });
  const file = path.join(directory, 'protected-operator.json'), env = path.join(directory, 'protected-operator.env');
  const descriptor = { schemaVersion: 1, installationId: ID, port: 12345, generation: 1, credentialVariable: 'NETCLAW_PROTECTED_OPERATOR_TOKEN' };
  fs.writeFileSync(file, JSON.stringify(descriptor), { mode: 0o600 }); fs.writeFileSync(env, `NETCLAW_PROTECTED_OPERATOR_TOKEN=${'k'.repeat(43)}\n`, { mode: 0o600 });
  assert.equal(readProtectedDescriptor({ home, installationId: ID }).token, 'k'.repeat(43));
  assert.throws(() => readProtectedDescriptor({ home, installationId: 'foreign' }));
  fs.chmodSync(env, 0o644); assert.throws(() => readProtectedDescriptor({ home, installationId: ID })); fs.chmodSync(env, 0o600);
  fs.renameSync(env, env + '.real'); fs.symlinkSync(env + '.real', env); assert.throws(() => readProtectedDescriptor({ home, installationId: ID }));
});

test('bridge allows fixed methods only, bounds responses and rejects descriptor rotation', async t => {
  let behavior = 'good';
  const app = express(); app.use(express.json()); app.post('/operator', (req, res) => {
    assert.equal(req.headers.authorization, 'Bearer private-fixture'); assert.equal(req.body.method, 'catalog');
    if (behavior === 'large') return res.send('x'.repeat(1024 * 1024 + 1));
    if (behavior === 'error') return res.status(503).json({ ok: false, error: { code: 'unavailable', message: 'private-exception' } });
    if (behavior === 'rotate') binding = { ...binding, generation: 2 };
    res.json({ ok: true, result: { revision: 'r1', members: [] } });
  });
  const server = app.listen(0, '127.0.0.1'); await new Promise(resolve => server.once('listening', resolve)); t.after(() => new Promise(resolve => server.close(resolve)));
  let binding = { port: server.address().port, generation: 1, token: 'private-fixture' };
  const client = createProtectedClient({ installationId: ID }, { readDescriptor: () => binding });
  await assert.rejects(client.call('arbitrary', {}), error => error.code === 'invalid_method');
  assert.deepEqual(await client.call('catalog', {}), { revision: 'r1', members: [] });
  for (behavior of ['error', 'large', 'rotate']) await assert.rejects(client.call('catalog', {}), error => error.status === 503 && !error.message.includes('private-exception'));
});
