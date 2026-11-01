import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import express from 'express';
import http from 'node:http';
import { Bindings } from './bindings.js';
import { createLocalAccess } from '../security/local-access.js';
import { createConvergenceReader, flowArguments, mountConvergence } from './convergence.js';

async function fixture(t, reader) {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'convergence-hud-'));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const installation = { installationId: '00000000-0000-4000-8000-000000000001', kind: 'openclaw' };
  const bindings = new Bindings(path.join(directory, 'bindings'), Date.now, installation), owner = bindings.create();
  let env = { CONVERGENCE_ENABLED: 'true', CONVERGENCE_SITE: 'fixture', CONVERGENCE_API_TOKEN: 'do-not-disclose' };
  const calls = [], app = express(); let allowed = () => false;
  mountConvergence(app, { bindings, getEnv: () => env, allowedRequest: req => allowed(req), read: async (...args) => {
    calls.push(args); return reader ? reader(...args) : { ok: true, data: { site: 'fixture', status: 'empty' } };
  } });
  const server = app.listen(0, '127.0.0.1'); await new Promise(resolve => server.once('listening', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const port = server.address().port, url = `http://127.0.0.1:${port}`;
  allowed = createLocalAccess({ api: port, ui: port + 1 }, { host: '127.0.0.1' });
  const headers = { cookie: `nc_hud=${owner}`, origin: url, 'X-NetClaw-Installation': installation.installationId };
  return { bindings, owner, calls, env, url, headers, directory, installation, setEnv: value => { env = value; } };
}

test('routes require trusted origin/Host and owned installation session before invoking MCP', async t => {
  const f = await fixture(t), route = f.url + '/api/hud/convergence/flows';
  assert.equal((await fetch(route)).status, 401);
  for (const headers of [{ ...f.headers, origin: 'https://evil.example' }, { ...f.headers, host: 'evil.example' }, { ...f.headers, 'sec-fetch-site': 'cross-site' }]) {
    const status = await new Promise((resolve, reject) => { const req = http.get(route, { headers }, res => { res.resume(); resolve(res.statusCode); }); req.on('error', reject); });
    assert.equal(status, 403);
  }
  assert.equal((await fetch(route, { headers: { ...f.headers, 'X-NetClaw-Installation': 'wrong' } })).status, 401);
  const foreign = new Bindings(path.join(f.directory, 'other'), Date.now, { ...f.installation, installationId: 'other' }).create();
  assert.equal((await fetch(route, { headers: { ...f.headers, cookie: `nc_hud=${foreign}` } })).status, 401);
  assert.equal(f.calls.length, 0);
  const response = await fetch(route, { headers: f.headers });
  assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'no-store');
  assert.deepEqual(f.calls, [['summary', { range: '1h' }]]);
  f.bindings.revoke(f.owner); assert.equal((await fetch(route, { headers: f.headers })).status, 401);
});

test('disabled status is configuration-only; query keys and evidence inputs fail before tool invocation', async t => {
  const f = await fixture(t); f.env.CONVERGENCE_ENABLED = 'false';
  const response = await fetch(f.url + '/api/hud/convergence/status', { headers: f.headers });
  assert.deepEqual(await response.json(), { enabled: false });
  assert.equal((await fetch(f.url + '/api/hud/convergence/flows', { headers: f.headers })).status, 409);
  assert.equal(f.calls.length, 0); f.env.CONVERGENCE_ENABLED = 'true';
  for (const suffix of ['?site=other', '?url=https://evil.example', '?range=1h&range=24h', '?exporter=invalid', '?range=7d', '/records?address=1.2.3.4&start=yesterday&end=tomorrow']) {
    assert.equal((await fetch(f.url + '/api/hud/convergence/flows' + suffix, { headers: f.headers })).status, 400);
  }
  assert.equal(f.calls.length, 0);
  const args = { address: '192.0.2.1', start: '2026-10-31T00:00:00Z', end: '2026-10-31T01:00:00Z', exporter: '127.0.0.1' };
  assert.equal((await fetch(f.url + '/api/hud/convergence/flows/records?' + new URLSearchParams(args), { headers: f.headers })).status, 200);
  assert.deepEqual(f.calls, [['evidence', args]]);
  assert.throws(() => flowArguments('evidence', { ...args, end: '2026-11-02T00:00:00Z' }));
});

test('revocation or disable during asynchronous read discards data', async t => {
  let finish; const f = await fixture(t, () => new Promise(resolve => { finish = resolve; }));
  const pending = fetch(f.url + '/api/hud/convergence/flows', { headers: f.headers });
  while (!finish) await new Promise(resolve => setTimeout(resolve, 1));
  f.bindings.revoke(f.owner); finish({ ok: true, data: { site: 'fixture', secret: 'not-returned' } });
  const response = await pending; assert.equal(response.status, 401); assert.doesNotMatch(await response.text(), /not-returned/);
});

test('wrong-site payloads and upstream diagnostics never leak through route errors', async t => {
  let result = { ok: true, data: { site: 'wrong', secret: 'do-not-disclose' } };
  const f = await fixture(t, () => result), route = f.url + '/api/hud/convergence/flows';
  let response = await fetch(route, { headers: f.headers }); assert.equal(response.status, 502); assert.doesNotMatch(await response.text(), /do-not-disclose/);
  result = { ok: false, error: { code: 'unauthorized', message: 'do-not-disclose' } };
  response = await fetch(route, { headers: f.headers }); assert.equal(response.status, 403); assert.doesNotMatch(await response.text(), /do-not-disclose/);
});

test('reader invokes only fixed MCP component tools with bounded execution and redacted errors', async () => {
  const env = { CONVERGENCE_ENABLED: 'true', CONVERGENCE_SITE: 'fixture', CONVERGENCE_API_TOKEN: 'private' }; let call;
  const reader = createConvergenceReader('/source path', () => env, (...args) => {
    call = args; args[3](null, JSON.stringify({ structuredContent: { ok: true, data: { site: 'fixture', status: 'empty' } } }));
  });
  assert.equal((await reader('summary', { range: '1h' })).ok, true);
  assert.equal(call[0], 'python3'); assert.equal(call[1][2], 'convergence_flow_summary');
  assert.match(call[1][1], /component-launch\.py.*convergence-read/); assert.equal(call[2].timeout, 28000);
  assert.equal(call[2].env.CONVERGENCE_API_TOKEN, 'private');
  assert.equal((await reader('arbitrary', {})).error.code, 'invalid_argument');
  for (const [failure, expected] of [[{ killed: true, message: 'private' }, 'timeout'], [Error('private'), 'unavailable']]) {
    const failed = createConvergenceReader('/source', () => env, (...args) => args[3](failure));
    assert.deepEqual(await failed('summary', {}), { ok: false, error: { code: expected, message: expected === 'timeout' ? 'Convergence did not respond before the deadline.' : 'Convergence is unavailable.' } });
  }
});

test('expired session and configuration disable during read fail closed', async t => {
  let finish; const f = await fixture(t, () => new Promise(resolve => { finish = resolve; }));
  const route = f.url + '/api/hud/convergence/flows';
  const pending = fetch(route, { headers: f.headers });
  while (!finish) await new Promise(resolve => setTimeout(resolve, 1));
  f.env.CONVERGENCE_ENABLED = 'false'; finish({ ok: true, data: { site: 'fixture', records: ['must not return'] } });
  let response = await pending; assert.equal(response.status, 409); assert.doesNotMatch(await response.text(), /must not return/);
  f.env.CONVERGENCE_ENABLED = 'true';
  const state = f.bindings.read(f.owner); state.expires = Date.now() - 1; f.bindings.save(f.owner, state);
  response = await fetch(route, { headers: f.headers }); assert.equal(response.status, 401); assert.equal(f.calls.length, 1);
});
