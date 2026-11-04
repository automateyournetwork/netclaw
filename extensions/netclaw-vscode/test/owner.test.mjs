import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import https from 'node:https';
import { once } from 'node:events';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { build } from 'esbuild';
import { pathToFileURL } from 'node:url';
import { load } from './load.mjs';
const { OwnerClient, OwnerOperations, ownerOrigin, catalogChoices, ownerCanonical, reviewText, unexpiredReview } = await load('src/client/owner.ts');
const ID = '22222222-2222-4222-8222-222222222222', ORIGIN = 'https://border.example.test';
const principal = { issuer: 'local', subject: '33333333-3333-4333-8333-333333333333', display_name: 'Owner', roles: ['owner'] };
const cookie = '__Host-nc_owner_' + ID + '=' + 'c'.repeat(43), ticket = 't'.repeat(43), csrf = 's'.repeat(43);
const clone = v => structuredClone(v);
const catalog = { revision: 'catalog-1', members: [{ member: { member_id: 'risk/member' }, model_profiles: [{ profile_id: 'sonnet-4-6' }], tools: [{ tool: 'subnet_calculator', arguments: { cidr: '192.0.2.0/26' } }] }] };
const selection = catalogChoices(catalog)[0];
const storage = () => { const state = new Map(); return { state, get: (k, d) => state.has(k) ? clone(state.get(k)) : d, update: async (k, v) => { state.set(k, clone(v)); } }; };
function operation(nonce) {
  const review = { principal, border: { installation_id: ID, identity: 'fixture-border' }, member: { member_id: 'risk/member' }, model_profile: { profile_id: 'sonnet-4-6' }, tool_call: { tool: selection.tool, arguments: selection.arguments }, limits: { expires_at_ms: Date.now() + 300000, max_tool_calls: 1 }, change_request_ref: null };
  return { operation_id: 'operation-' + nonce, client_nonce: nonce, revision: 1, state: 'review_pending', review,
    review_digest: createHash('sha256').update(ownerCanonical(review)).digest('hex'), allowed_actions: ['approve', 'deny'], reconciliation_required: false, may_have_executed: false, attempt_count: 0, result: null };
}
function fixture(t) {
  const calls = [], saved = [], operations = new Map();
  const state = { authenticated: true, runtimeId: ID, role: 'border', runtimeCapabilities: true, hook: undefined, lost: false };
  const session = () => ({ authenticated: true, installation_id: ID, principal, csrf_token: csrf, expires_ms: Date.now() + 60000 });
  const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', ...headers } });
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    assert.equal(new URL(url).origin, ORIGIN); assert.equal(init.redirect, 'error');
    const route = new URL(url).pathname, query = new URL(url).searchParams;
    const call = { route, method: init.method, headers: init.headers, body: init.body && JSON.parse(init.body) }; calls.push(call);
    if (state.hook) { const override = await state.hook(call, json); if (override) return override; }
    assert.equal(init.headers['X-NetClaw-Installation'], ID);
    if (route === '/api/runtime') {
      assert.equal(init.headers.Cookie, undefined, 'public identity probe must not disclose a saved session');
      return json({ installationId: state.runtimeId, kind: 'openclaw', role: state.role, readiness: { ready: true }, capabilities: { protectedProfile: true, protectedOperations: true, protectedProduction: state.runtimeCapabilities } });
    }
    if (init.method !== 'GET') {
      assert.equal(init.headers.Origin, ORIGIN); assert.equal(init.headers['Content-Type'], 'application/json');
      if (!init.headers['X-NetClaw-Owner-Bootstrap']) assert.equal(init.headers['X-NetClaw-CSRF'], csrf);
    }
    if (route === '/api/hud/owner/session' && init.method === 'POST') {
      assert.equal(call.body.ticket, ticket); assert.equal(init.headers['X-NetClaw-Owner-Bootstrap'], '1');
      return json(session(), 200, { 'Set-Cookie': cookie + '; Path=/; HttpOnly; SameSite=Strict; Secure; Max-Age=60' });
    }
    if (!state.authenticated) return json({ code: 'owner_session_required' }, 401);
    assert.equal(init.headers.Cookie, cookie);
    if (route === '/api/hud/owner/session') {
      if (init.method === 'DELETE') return json({ authenticated: false }, 200, { 'Set-Cookie': cookie.split('=')[0] + '=; Path=/; HttpOnly; SameSite=Strict; Secure; Max-Age=0' });
      return json(session());
    }
    if (route === '/api/hud/operations/catalog') return json(catalog);
    if (route === '/api/hud/operations' && init.method === 'POST') {
      const op = operation(call.body.client_nonce); operations.set(op.operation_id, op); return json(op);
    }
    const id = route.split('/')[4];
    let op = id ? operations.get(id) : [...operations.values()].find(v => v.client_nonce === query.get('client_nonce'));
    if (!op) return json({ code: 'operation_not_found' }, 404);
    if (route.endsWith('/decision')) {
      assert.equal(call.body.revision, op.revision); assert.equal(call.body.review_digest, op.review_digest);
      op = { ...op, state: 'completed', revision: 2, attempt_count: 1, may_have_executed: true, allowed_actions: ['reconcile'], result: { verified: true, durable_ack: true, ack_delivery_pending: false, evidence: { audit_refs: { member: 'gait-test' }, output: { addresses: 64 } } } };
      operations.set(op.operation_id, op);
    }
    return json(op);
  };
  t.after(() => { globalThis.fetch = original; });
  const client = new OwnerClient(ORIGIN, ID, async c => saved.push(c), () => { state.lost = true; });
  t.after(() => client.close());
  return { client, calls, operations, saved, state, session, json };
}
test('cloud origin is explicit HTTPS and local endpoint policy remains unchanged', async () => {
  assert.equal(ownerOrigin(ORIGIN), ORIGIN);
  for (const bad of ['http://border.example.test', ORIGIN + '/', ORIGIN + '/api', ORIGIN + '?x', ORIGIN + '#x', 'https://user:secret@border.example.test', 'https://BORDER.example.test', ' https://border.example.test', 'https:\\border.example.test']) assert.throws(() => ownerOrigin(bad));
  assert.throws(() => new OwnerClient(ORIGIN, 'missing'));
  const { endpoint } = await load('src/client/hud.ts');
  assert.throws(() => endpoint(ORIGIN)); assert.equal(endpoint('http://localhost:3001'), 'http://127.0.0.1:3001');
});
test('verified identity precedes owner login; strict cookie is securely stored, CSRF never persisted', async t => {
  const f = fixture(t); const session = await f.client.login(ticket);
  assert.equal(session.principal.subject, principal.subject); assert.equal(session.csrf_token, undefined);
  assert.deepEqual(f.saved, [cookie]); assert.equal(f.calls[0].route, '/api/runtime');
  assert.equal((await f.client.catalog()).revision, catalog.revision);
  await f.client.logout(); assert.equal(f.saved.at(-1), ''); assert.equal(f.client.sessionState, undefined);
});
for (const change of [{ runtimeId: '44444444-4444-4444-8444-444444444444' }, { role: 'member' }, { runtimeCapabilities: false }]) test('wrong identity/role/capability refuses before ticket disclosure ' + JSON.stringify(change), async t => {
  const f = fixture(t); Object.assign(f.state, change);
  await assert.rejects(f.client.login(ticket), /expected protected/);
  assert.equal(f.calls.filter(c => c.method !== 'GET').length, 0); assert.ok(!JSON.stringify(f.calls).includes(ticket));
});
test('wrong cookie scope and invalid/expired owner claims fail closed without response disclosure', async t => {
  const f = fixture(t);
  for (const change of [{ expires_ms: 1 }, { principal: { ...principal, roles: ['admin'] } }, { installation_id: 'foreign' }, { csrf_token: 'bad' }]) {
    f.state.hook = (c, json) => c.route === '/api/hud/owner/session' && c.method === 'POST' ? json({ ...f.session(), ...change }, 200, { 'Set-Cookie': cookie + '; Path=/; HttpOnly; SameSite=Strict; Secure' }) : undefined;
    await assert.rejects(f.client.login(ticket)); assert.equal(f.client.sessionState, undefined); assert.equal(f.saved.at(-1), '');
  }
  for (const bad of [cookie + '; Path=/; HttpOnly; SameSite=Strict', cookie + '; Path=/; HttpOnly; SameSite=Strict; Secure; Domain=example.test', '__Host-nc_owner_foreign=' + 'c'.repeat(43) + '; Path=/; HttpOnly; SameSite=Strict; Secure']) {
    f.state.hook = (c, json) => c.method === 'POST' ? json(f.session(), 200, { 'Set-Cookie': bad }) : undefined;
    await assert.rejects(f.client.login(ticket), e => !e.message.includes('cccc') && !e.message.includes(ticket));
  }
});
test('owner revocation clears session and prevents prepare/decision requests', async t => {
  const f = fixture(t); await f.client.login(ticket); f.state.authenticated = false;
  await assert.rejects(f.client.prepare({}), /expired or was revoked/);
  assert.equal(f.client.sessionState, undefined); assert.equal(f.saved.at(-1), '');
  assert.equal(f.calls.filter(c => c.route === '/api/hud/operations' && c.method === 'POST').length, 0);
});
test('close during delayed secure storage cannot restore owner authority or return a late session', async t => {
  fixture(t);
  let entered, release;
  const waiting = new Promise(resolve => { entered = resolve; });
  const client = new OwnerClient(ORIGIN, ID, async value => { if (value) { entered(); await new Promise(resolve => { release = resolve; }); } });
  const login = client.login(ticket);
  await waiting; client.close(); release();
  await assert.rejects(login, /closed/); assert.equal(client.sessionState, undefined); assert.equal(client.runtime, undefined);
});
test('close while identity response is delayed cannot accept a late runtime', async t => {
  const f = fixture(t); let entered, release;
  const waiting = new Promise(resolve => { entered = resolve; });
  f.state.hook = async c => { if (c.route === '/api/runtime') { entered(); await new Promise(resolve => { release = resolve; }); } };
  const connected = f.client.connect(); await waiting; f.client.close(); release();
  await assert.rejects(connected, /closed/); assert.equal(f.client.runtime, undefined);
});
test('nonce is durable before prepare; complete exact review, one decision and restart recovery preserve effect count', async t => {
  const f = fixture(t), store = storage(), ops = new OwnerOperations(f.client, store);
  await f.client.login(ticket);
  f.state.hook = c => { if (c.route === '/api/hud/operations' && c.method === 'POST') assert.equal(ops.references()[0].client_nonce, c.body.client_nonce); };
  const op = await ops.prepare(selection); assert.deepEqual(JSON.parse(reviewText(op)).review, op.review);
  const done = await ops.decide(op, 'approve'); assert.equal(done.result.durable_ack, true);
  await assert.rejects(ops.decide(op, 'approve'), /already submitted/);
  const restored = new OwnerOperations(f.client, store); assert.equal((await restored.recover(restored.references()[0])).state, 'completed');
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 1);
  assert.equal(f.calls.filter(c => c.route === '/api/hud/operations' && c.method === 'POST').length, 1);
  const persisted = JSON.stringify([...store.state.values()]);
  for (const secret of [ticket, csrf, '192.0.2.0', 'addresses', 'gait-test', 'review_digest', 'risk/member']) assert.ok(!persisted.includes(secret));
});
test('lost prepare response recovers original nonce and cannot prepare a replacement while unresolved', async t => {
  const f = fixture(t), store = storage(), ops = new OwnerOperations(f.client, store); await f.client.login(ticket);
  f.state.hook = c => { if (c.route === '/api/hud/operations' && c.method === 'POST') { const op = operation(c.body.client_nonce); f.operations.set(op.operation_id, op); throw Error('secret-wire-error'); } };
  await assert.rejects(ops.prepare(selection), e => /nothing was resent/.test(e.message) && !e.message.includes('secret-wire-error'));
  assert.equal(ops.references().length, 1); assert.equal(ops.references()[0].operation_id, undefined);
  const resumed = new OwnerOperations(f.client, store); const op = await resumed.recover(resumed.references()[0]); assert.equal(op.state, 'review_pending');
  await assert.rejects(resumed.prepare(selection), /unresolved/);
  assert.equal(f.calls.filter(c => c.route === '/api/hud/operations' && c.method === 'POST').length, 1);
});
test('verified failed receipt and delivered ACK recover GET-only and permit a separately selected read while retaining the old reference', async t => {
  const f = fixture(t), store = storage(), ops = new OwnerOperations(f.client, store); await f.client.login(ticket);
  const prepared = await ops.prepare(selection), done = await ops.decide(prepared, 'approve');
  // The protected service has verified the signed FAILED receipt and delivered its ACK.
  f.operations.set(done.operation_id, { ...done, state: 'failed', result: { ...done.result, evidence: { status: 'FAILED' } } });
  const oldRef = ops.references()[0], beforeRecovery = f.calls.length;
  const restarted = new OwnerOperations(f.client, store), failed = await restarted.recover(oldRef);
  assert.equal(failed.state, 'failed'); assert.equal(failed.result.verified, true); assert.equal(failed.result.durable_ack, true);
  assert.equal(failed.result.ack_delivery_pending, false);
  assert.ok(f.calls.slice(beforeRecovery).every(c => c.method === 'GET'));
  assert.equal(f.calls.filter(c => c.route === '/api/hud/operations' && c.method === 'POST').length, 1, 'Recovery must not prepare automatically');
  const selectedAgain = catalogChoices(await f.client.catalog())[0];
  const next = await restarted.prepare(selectedAgain);
  assert.notEqual(next.client_nonce, oldRef.client_nonce); assert.notEqual(next.operation_id, oldRef.operation_id);
  assert.deepEqual(restarted.references()[0], oldRef); assert.equal(restarted.references().length, 2);
  assert.equal(oldRef.decision_sent, true);
  assert.equal(f.calls.filter(c => c.route === '/api/hud/operations' && c.method === 'POST').length, 2);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 1, 'New preparation must not replay approval');
});
test('failed or unknown work blocks a new read when any receipt or ACK condition is incomplete', async t => {
  const f = fixture(t), ops = new OwnerOperations(f.client, storage()); await f.client.login(ticket);
  const prepared = await ops.prepare(selection), done = await ops.decide(prepared, 'approve'), ref = ops.references()[0];
  for (const change of [
    { result: null },
    { result: { verified: true } },
    { result: { ...done.result, verified: false } },
    { result: { ...done.result, durable_ack: false } },
    { result: { ...done.result, ack_delivery_pending: true } },
    { reconciliation_required: true },
    { state: 'outcome_unknown' },
  ]) {
    f.operations.set(done.operation_id, { ...done, state: 'failed', ...change });
    const before = f.calls.length;
    await assert.rejects(ops.prepare(selection), /unresolved/);
    assert.ok(f.calls.slice(before).every(c => c.method === 'GET'));
    assert.deepEqual(ops.references(), [ref]);
  }
  assert.equal(f.calls.filter(c => c.route === '/api/hud/operations' && c.method === 'POST').length, 1);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 1);
});
test('only proven pre-admission rejection can be explicitly discarded after restart', async t => {
  const f = fixture(t), store = storage(), ops = new OwnerOperations(f.client, store); await f.client.login(ticket);
  f.state.hook = (c, json) => c.route === '/api/hud/operations' && c.method === 'POST' ? json({ admission: 'not_submitted' }, 403) : undefined;
  await assert.rejects(ops.prepare(selection), /before submission/);
  const ref = ops.references()[0]; assert.equal(ref.not_submitted, true);
  const resumed = new OwnerOperations(f.client, store);
  await assert.rejects(resumed.prepare(selection), /explicitly discard/);
  await resumed.discardUnsubmitted(ref); assert.deepEqual(resumed.references(), []);
  f.state.hook = undefined;
  const op = await resumed.prepare(selection); assert.notEqual(op.client_nonce, ref.client_nonce);
  await assert.rejects(resumed.discardUnsubmitted(resumed.references()[0]), /Unknown work/);
});
test('a later404 never supplies evidence to discard an ambiguous preparation', async t => {
  const f = fixture(t), ops = new OwnerOperations(f.client, storage()); await f.client.login(ticket);
  f.state.hook = (c, json) => c.route === '/api/hud/operations' && c.method === 'POST' ? json({ code: 'unavailable' }, 503) : undefined;
  await assert.rejects(ops.prepare(selection)); const ref = ops.references()[0]; assert.equal(ref.not_submitted, undefined);
  await assert.rejects(ops.recover(ref), /HTTP 404/);
  await assert.rejects(ops.discardUnsubmitted(ref), /Unknown work/); assert.equal(ops.references().length, 1);
});
test('expired review has no approval action and cannot spend a decision marker or reach decision transport', async t => {
  const f = fixture(t), ops = new OwnerOperations(f.client, storage()); await f.client.login(ticket);
  const prepared = await ops.prepare(selection), expired = clone(prepared);
  expired.review.limits.expires_at_ms = Date.now() - 1;
  expired.review_digest = createHash('sha256').update(ownerCanonical(expired.review)).digest('hex');
  f.operations.set(expired.operation_id, expired);
  assert.equal(unexpiredReview(expired), false);
  await assert.rejects(ops.decide(expired, 'approve'), /expired/);
  assert.equal(ops.references()[0].decision_sent, undefined);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 0);
  await assert.rejects(f.client.decision(expired.operation_id, expired.revision, expired.review_digest, 'approve', expired.review.limits.expires_at_ms), /expired/);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 0);
});
test('lost decision persists sent marker before transport and cannot replay after restart', async t => {
  const f = fixture(t), store = storage(), ops = new OwnerOperations(f.client, store); await f.client.login(ticket);
  const op = await ops.prepare(selection);
  f.state.hook = c => { if (c.route.endsWith('/decision')) { assert.equal(ops.references()[0].decision_sent, true); throw Error('lost'); } };
  await assert.rejects(ops.decide(op, 'approve'), /nothing was resent/);
  const resumed = new OwnerOperations(f.client, store); await resumed.recover(resumed.references()[0]);
  await assert.rejects(resumed.decide(op, 'approve'), /already submitted/);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 1);
});
test('changed review, foreign response and duplicate clicks cannot produce authority', async t => {
  const f = fixture(t), ops = new OwnerOperations(f.client, storage()); await f.client.login(ticket);
  const op = await ops.prepare(selection);
  const changed = clone(op); changed.review.limits.max_tool_calls = 2;
  assert.throws(() => reviewText(changed), /digest/);
  f.operations.set(op.operation_id, { ...op, revision: 2 });
  await assert.rejects(ops.decide(op, 'approve'), /review changed/);
  f.operations.set(op.operation_id, { ...op, client_nonce: 'foreign' });
  await assert.rejects(ops.recover(ops.references()[0]), /does not belong/);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 0);
  const next = new OwnerOperations(f.client, storage());
  const [a, b] = await Promise.allSettled([next.prepare(selection), next.prepare(selection)]);
  assert.equal(a.status, 'fulfilled'); assert.equal(b.status, 'rejected');
});
test('persistence failure prevents prepare; unsupported catalog selections cannot substitute arguments', async t => {
  const f = fixture(t); await f.client.login(ticket);
  const ops = new OwnerOperations(f.client, { get: (_k, v) => v, update: async () => { throw Error('disk unavailable'); } });
  await assert.rejects(ops.prepare(selection), /disk unavailable/);
  const normal = new OwnerOperations(f.client, storage());
  await assert.rejects(normal.prepare({ ...selection, arguments: { cidr: '10.0.0.0/24' } }), /selection changed/);
  assert.equal(f.calls.filter(c => c.route === '/api/hud/operations' && c.method === 'POST').length, 0);
});
test('invalid TLS is rejected by the native transport without reaching HTTP', async t => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-owner-tls-'));
  execFileSync('/usr/bin/openssl', ['req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', path.join(directory, 'key.pem'), '-out', path.join(directory, 'cert.pem'), '-days', '1', '-subj', '/CN=localhost'], { stdio: 'ignore' });
  let calls = 0;
  const server = https.createServer({ key: fs.readFileSync(path.join(directory, 'key.pem')), cert: fs.readFileSync(path.join(directory, 'cert.pem')) }, (_req, res) => { calls++; res.end('{}'); });
  server.listen(0, '127.0.0.1'); await once(server, 'listening');
  t.after(() => { server.closeAllConnections(); server.close(); fs.rmSync(directory, { recursive: true }); });
  await assert.rejects(new OwnerClient('https://127.0.0.1:' + server.address().port, ID).connect(), /not confirmed/);
  assert.equal(calls, 0);
});

async function nativeModules() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-owner-native-'));
  const file = path.join(directory, 'native.mjs');
  await build({ stdin: { contents: "export {Profiles,hostContext} from './src/state/profiles'; export {Connection} from './src/connection/connect'; export {Management} from './src/state/management'; export {assertCloudCommand,ownerDecisionDetail} from './src/views/owner';", resolveDir: process.cwd() }, outfile: file, bundle: true, platform: 'node', format: 'esm', target: 'node22', logLevel: 'silent', plugins: [{ name: 'vscode-fixture', setup(b) {
    b.onResolve({ filter: /^vscode$/ }, () => ({ path: 'vscode', namespace: 'fixture' }));
    b.onLoad({ filter: /.*/, namespace: 'fixture' }, () => ({ contents: "export const env={remoteName:undefined}; export const workspace={isTrusted:true}; export class EventEmitter {event=()=>({dispose(){}});fire(){}dispose(){}};", loader: 'js' }));
  } }] });
  return import(pathToFileURL(file).href);
}
test('native confirmation stays compact while binding the complete immutable review document', async () => {
  const { ownerDecisionDetail } = await nativeModules(), op = operation('view-test');
  const detail = ownerDecisionDetail(ORIGIN, ID, op);
  assert.ok(detail.includes(op.operation_id) && detail.includes(op.review_digest) && detail.includes('Revision: ' + op.revision));
  assert.ok(detail.length < 1000 && detail.split('\n').length < 12);
  assert.deepEqual(JSON.parse(reviewText(op)).review, op.review);
  op.review.limits.max_tool_calls = 2; assert.throws(() => ownerDecisionDetail(ORIGIN, ID, op), /digest/);
});
test('profile, direct handler and local lifecycle boundaries retain existing local state', async t => {
  const { Profiles, hostContext, Connection, Management, assertCloudCommand } = await nativeModules();
  const store = storage(), profiles = new Profiles(store);
  const local = await profiles.save({ label: 'Existing local', url: 'http://localhost:3001' });
  const cloud = await profiles.save({ label: 'Cloud', url: ORIGIN, mode: 'remote-border', installationId: ID, harness: 'openclaw' });
  assert.equal(profiles.list().length, 2); assert.equal(profiles.list()[0].url, 'http://127.0.0.1:3001');
  await assert.rejects(profiles.save({ ...cloud, installationId: undefined }));
  await assert.rejects(profiles.save({ ...cloud, mode: undefined }));
  for (const name of ['startClaw', 'stopClaw', 'bindWorkspace', 'saveRestartClaw', 'openChat', 'configureMcp', 'manageAssistants', 'setupClaw', 'setupAssistant', 'openNativeRuntime']) assert.throws(() => assertCloudCommand(name, true), /local profile/);
  assert.doesNotThrow(() => assertCloudCommand('ownerPrepare', true));
  assert.doesNotThrow(() => assertCloudCommand('startClaw', false));
  const f = fixture(t), secrets = new Map();
  const connection = new Connection({ get: async k => secrets.get(k), store: async (k, v) => secrets.set(k, v), delete: async k => secrets.delete(k) });
  t.after(() => connection.dispose());
  await connection.connect(cloud); assert.equal(connection.ready, true); assert.throws(() => connection.bound(), /protected owner/);
  const b = connection.ownerBound();
  const management = new Management(store, () => connection.profile?.mode === 'remote-border');
  await management.select(local); assert.equal(management.selected, undefined); assert.throws(() => management.bound());
  await assert.rejects(management.saveBinding({ profile: cloud }), /cannot acquire/);
  connection.disconnect(); assert.throws(() => b.current(), /changed/);
  assert.equal(profiles.list()[0].id, local.id); assert.equal(profiles.list()[0].context, hostContext());
});
