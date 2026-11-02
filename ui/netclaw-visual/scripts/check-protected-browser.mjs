// Source qualification only: actual built pages/TLS/browser, synthetic authority/results.
// No existing runtime, real credential, provider or device is used.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import https from 'node:https';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { createProtectedServer, readProtectedServerConfig } from '../src/hud-server/protected-server.js';
import { buildProtectedManifest, sha256 } from '../src/hud-server/protected-assets.js';
import { ProtectedError } from '../src/hud-server/protected-client.js';

const args = process.argv.slice(2);
if (args.length !== 8 || args[0] !== '--playwright' || args[2] !== '--browser' || args[4] !== '--dist' || args[6] !== '--evidence' || [args[1], args[3], args[5], args[7]].some(value => !path.isAbsolute(value))) throw Error('Explicit --playwright MODULE --browser BINARY --dist DIR --evidence DIR required.');
const { chromium } = await import(pathToFileURL(args[1]));
fs.mkdirSync(args[7], { recursive: true, mode: 0o700 }); const evidence = fs.realpathSync(args[7]);
const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-172-browser-')));
const write = (name, value) => { const file = path.join(root, name); fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 }); fs.writeFileSync(file, typeof value === 'string' ? value : JSON.stringify(value), { mode: 0o600 }); return file; };
const ID = '00000000-0000-4000-8000-000000000172', COOKIE = 'c'.repeat(43), CSRF = 's'.repeat(43), TICKET = 't'.repeat(43);
const principal = { issuer: 'local', subject: ID, display_name: 'Synthetic owner', roles: ['owner'] };
const devices = ['R1', 'R2', 'SW1', 'SW2'], operations = new Map(), methods = [], checks = [];
const model = { profile_id: 'fixture-model', runtime_kind: 'openclaw', provider: 'synthetic', model: 'fixture-no-provider' };
const member = { member_id: 'fixture/onprem', installation_id: ID, key_id: 'fixture-member' };
const catalog = { revision: 'fixture-catalog', members: [{ member, model_profiles: [model], tools: devices.map(device => ({ tool: 'pyats_run_show_command', device_ref: device, arguments: { device_name: device, command: 'show version', retries: 1, timeout: 30 } })) }] };
let count = 0, ticketSpent = false, active = true, browser, api, tls;
const session = () => ({ principal, installation_id: ID, csrf_token: CSRF, session_hash: sha256(COOKIE), auth_generation: 1, expires_ms: Date.now() + 3600000 });
const client = { async call(method, params) {
  methods.push(method);
  if (method === 'owner.login') { if (ticketSpent || params.ticket !== TICKET) throw new ProtectedError('ticket_refused', 401); ticketSpent = true; return { cookie: COOKIE }; }
  if (method === 'owner.session') { if (!active || params.cookie !== COOKIE) throw new ProtectedError('session_refused', 401); return session(); }
  if (method === 'owner.logout') { active = false; return {}; }
  assert.deepEqual(params.auth_context, { principal, auth_generation: 1, session_hash: sha256(COOKIE) });
  if (method === 'catalog') return catalog;
  if (method === 'prepare') {
    const tool = catalog.members[0].tools.find(value => JSON.stringify(value.arguments) === JSON.stringify(params.arguments)); assert.ok(tool);
    const op = { operation_id: `fixture-operation-${++count}`, client_nonce: params.client_nonce, revision: 1, review_digest: 'd'.repeat(64), state: 'review_pending', attempt_count: 0, may_have_executed: false, reconciliation_required: false, allowed_actions: ['approve', 'deny'], review: { principal, border: { identity: 'fixture/border' }, member, model_profile: model, tool_call: tool, limits: { expires_at_ms: Date.now() + 300000, max_inference_calls: 2, max_tool_calls: 1 } } };
    operations.set(op.operation_id, op); return op;
  }
  const op = params.operation_id ? operations.get(params.operation_id) : [...operations.values()].find(value => value.client_nonce === params.client_nonce);
  if (!op) throw new ProtectedError('operation_not_found', 404);
  if (method === 'decision') { assert.equal(params.decision, 'approve'); assert.equal(op.state, 'review_pending'); Object.assign(op, { state: 'completed', allowed_actions: ['reconcile'], attempt_count: 1, may_have_executed: true, result: { verified: true, durable_ack: true, ack_delivery_pending: false, digest: 'synthetic-receipt', evidence: { operation_id: op.operation_id, output: { model_answer: 'Synthetic fixture only.', tool: { parsed: true, output: { version: { version: '17.fixture', os: 'IOS' } } } } } } }); }
  return op;
} };
try {
  const key = path.join(root, 'fixture.key'), cert = path.join(root, 'fixture.crt');
  execFileSync('/usr/bin/openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1', '-subj', '/CN=127.0.0.1', '-keyout', key, '-out', cert], { stdio: 'ignore' }); fs.chmodSync(key, 0o600);
  tls = https.createServer({ key: fs.readFileSync(key), cert: fs.readFileSync(cert) }, (req, res) => {
    const upstream = http.request({ host: '127.0.0.1', port: api.address().port, path: req.url, method: req.method, headers: req.headers }, response => { res.writeHead(response.statusCode, response.headers); response.pipe(res); });
    upstream.on('error', () => { res.writeHead(503); res.end(); }); req.pipe(upstream);
  }); tls.listen(0, '127.0.0.1'); await new Promise(resolve => tls.once('listening', resolve));
  const origin = `https://127.0.0.1:${tls.address().port}`;
  write('home/netclaw-hud/installation.json', { schemaVersion: 1, installationId: ID });
  write('home/netclaw-federation/protected-profile.json', { schemaVersion: 1, role: 'border', identity: { installation_id: ID } });
  write('home/netclaw-federation/protected-operator.json', { schemaVersion: 1, installationId: ID, port: 17777, generation: 'fixture', credentialVariable: 'NETCLAW_PROTECTED_OPERATOR_TOKEN' });
  write('home/netclaw-federation/protected-operator.env', 'NETCLAW_PROTECTED_OPERATOR_TOKEN=' + 'f'.repeat(43));
  const manifest = write('assets.json', buildProtectedManifest(args[5]));
  const configFile = write('hud.json', { schemaVersion: 1, installationId: ID, home: path.join(root, 'home'), kind: 'openclaw', origin, host: '127.0.0.1', port: 18000, dist: args[5], manifest, manifestSha256: sha256(fs.readFileSync(manifest)) });
  api = createProtectedServer(readProtectedServerConfig(configFile), { client }); api.listen(0, '127.0.0.1'); await new Promise(resolve => api.once('listening', resolve));
  browser = await chromium.launch({ executablePath: args[3], headless: true, args: ['--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run'] });
  const context = await browser.newContext({ ignoreHTTPSErrors: true, viewport: { width: 1440, height: 1100 } });
  const page = await context.newPage(), errors = [], requests = [], anonymousSessionRefusals = [];
  await context.route('**/*', route => route.request().url().startsWith(origin + '/') ? route.continue() : route.abort());
  page.on('pageerror', error => errors.push(error.message)); page.on('console', message => {
    if (message.type() !== 'error') return;
    if (message.location().url === origin + '/api/hud/owner/session' && /status of 401 \(Unauthorized\)/.test(message.text())) anonymousSessionRefusals.push('expected anonymous session 401');
    else errors.push(message.text());
  });
  page.on('request', request => requests.push({ method: request.method(), path: new URL(request.url()).pathname }));
  await page.goto(origin); await page.getByRole('heading', { name: 'Owner sign-in' }).waitFor();
  assert.equal((await page.request.get(origin + '/api/hud/operations/catalog', { headers: { 'X-NetClaw-Installation': ID } })).status(), 401); checks.push('anonymous operation refusal');
  await page.getByLabel('One-time owner ticket').fill(TICKET); await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await page.getByRole('button', { name: 'Prepare review', exact: true }).waitFor();
  const cookie = (await context.cookies()).find(value => value.name.startsWith('__Host-nc_owner_')); assert.ok(cookie?.secure && cookie.httpOnly && cookie.sameSite === 'Strict'); checks.push('actual Secure HttpOnly Strict __Host cookie');
  for (const device of devices) {
    await page.getByLabel('Read-only call').selectOption({ label: 'pyats_run_show_command · ' + device });
    await page.getByRole('button', { name: 'Prepare review', exact: true }).click();
    await page.getByRole('button', { name: 'Approve once', exact: true }).click();
    await page.getByRole('button', { name: 'Remove resolved reference', exact: true }).waitFor();
  }
  assert.equal(methods.filter(value => value === 'prepare').length, 4); assert.equal(methods.filter(value => value === 'decision').length, 4); assert.equal(await page.locator('tbody tr').count(), 4); checks.push('four separate synthetic reviews and approvals');
  assert.equal(await page.locator('tbody tr').filter({ hasText: 'IOS / 17.fixture' }).count(), 4); checks.push('verified structured version rows');
  const stored = await page.evaluate(() => Object.fromEntries(Object.keys(sessionStorage).map(key => [key, sessionStorage.getItem(key)])));
  const refs = JSON.parse(stored[`netclaw.protected.${ID}.operations.v2`]); assert.equal(refs.length, 4); assert.ok(refs.every(row => Object.keys(row).sort().join(',') === 'client_nonce,operation_id')); assert.ok(!JSON.stringify(stored).includes(COOKIE) && !JSON.stringify(stored).includes(CSRF) && !JSON.stringify(stored).includes(TICKET)); checks.push('browser storage contains identifiers only');
  const before = methods.filter(value => ['prepare', 'decision'].includes(value)).length;
  await page.reload(); await page.getByRole('button', { name: 'Remove resolved reference', exact: true }).waitFor(); assert.equal(await page.locator('tbody tr').count(), 4); assert.equal(methods.filter(value => ['prepare', 'decision'].includes(value)).length, before); checks.push('reload restores four references without new authority');
  assert.ok(!requests.some(row => ['/api/chat', '/api/n2n', '/api/gateway/status', '/api/hud/runtime', '/ws'].includes(row.path))); checks.push('no legacy automatic network requests');
  assert.deepEqual(errors, []); checks.push('production asset closure and CSP load without browser errors');
  await page.screenshot({ path: path.join(evidence, 'protected-four-results.png'), fullPage: true });
  fs.chmodSync(path.join(evidence, 'protected-four-results.png'), 0o600);
  await page.evaluate(() => { const script = document.createElement('script'); script.textContent = 'window.__inlineExecuted=true'; document.body.append(script); });
  assert.equal(await page.evaluate(() => window.__inlineExecuted), undefined); checks.push('actual CSP rejects inline script');
  fs.writeFileSync(path.join(evidence, 'browser-report.json'), JSON.stringify({ fixture: true, realProviderCalls: 0, realDeviceCalls: 0, tls: 'local self-signed fixture accepted only by test browser; not public CA evidence', edge: 'local Node HTTPS proxy; not deployed Caddy evidence', browserVersion: browser.version(), checks, anonymousSessionRefusals, operationCount: 4, prepareCalls: 4, decisionCalls: 4, sourceBuildManifestSha256: sha256(fs.readFileSync(manifest)) }, null, 2) + '\n', { mode: 0o600 });
  console.log(JSON.stringify({ passed: checks.length, operations: 4, fixture: true, realProviderCalls: 0, realDeviceCalls: 0 }));
} finally {
  if (browser) await browser.close();
  for (const server of [api, tls]) if (server) { server.closeAllConnections(); await new Promise(resolve => server.close(resolve)); }
  fs.rmSync(root, { recursive: true, force: true });
}
