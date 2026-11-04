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
const { OwnerClient, OwnerOperations, discoverCloudBorder, ownerOrigin, cloudInputOrigin, catalogChoices, ownerCanonical, reviewText, unexpiredReview } = await load('src/client/owner.ts');
const ID = '22222222-2222-4222-8222-222222222222', ORIGIN = 'https://border.example.test';
const principal = { issuer: 'local', subject: '33333333-3333-4333-8333-333333333333', display_name: 'Owner', roles: ['owner'] };
const labPrincipal = { issuer: 'open-lab', subject: '55555555-5555-4555-8555-555555555555', display_name: 'Unauthenticated lab operator', roles: ['lab-operator'] };
const cookie = '__Host-nc_owner_' + ID + '=' + 'c'.repeat(43), ticket = 't'.repeat(43), csrf = 's'.repeat(43);
const clone = v => structuredClone(v);
const catalog = { revision: 'catalog-1', members: [{ member: { member_id: 'risk/member' }, model_profiles: [{ profile_id: 'sonnet-4-6' }], tools: [{ tool: 'subnet_calculator', arguments: { cidr: '192.0.2.0/26' } }] }] };
const selection = catalogChoices(catalog)[0];
const storage = () => { const state = new Map(); return { state, get: (k, d) => state.has(k) ? clone(state.get(k)) : d, update: async (k, v) => { state.set(k, clone(v)); } }; };
function operation(nonce, operator = principal) {
  const review = { principal: operator, border: { installation_id: ID, identity: 'fixture-border' }, member: { member_id: 'risk/member' }, model_profile: { profile_id: 'sonnet-4-6' }, tool_call: { tool: selection.tool, arguments: selection.arguments }, limits: { expires_at_ms: Date.now() + 300000, max_tool_calls: 1 }, change_request_ref: null };
  return { operation_id: 'operation-' + nonce, client_nonce: nonce, revision: 1, state: 'review_pending', review,
    review_digest: createHash('sha256').update(ownerCanonical(review)).digest('hex'), allowed_actions: ['approve', 'deny'], reconciliation_required: false, may_have_executed: false, attempt_count: 0, result: null };
}
function fixture(t) {
  const calls = [], saved = [], operations = new Map();
  const state = { authenticated: true, runtimeId: ID, role: 'border', runtimeCapabilities: true, openLab: false, hook: undefined, lost: false };
  const session = () => ({ authenticated: true, installation_id: ID, principal, csrf_token: csrf, expires_ms: Date.now() + 60000 });
  const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', ...headers } });
  const original = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    assert.equal(new URL(url).origin, ORIGIN); assert.equal(init.redirect, 'error');
    const route = new URL(url).pathname, query = new URL(url).searchParams;
    const call = { route, method: init.method, headers: init.headers, body: init.body && JSON.parse(init.body) }; calls.push(call);
    if (state.hook) { const override = await state.hook(call, json); if (override) return override; }
    if (route === '/api/runtime') {
      if (init.headers['X-NetClaw-Installation'] !== undefined) assert.equal(init.headers['X-NetClaw-Installation'], ID);
      assert.equal(init.headers.Cookie, undefined, 'public identity probe must not disclose a saved session');
      return json({ ...(state.openLab ? { access: { mode: 'open-lab', principal: labPrincipal } } : {}), installationId: state.runtimeId, kind: 'openclaw', role: state.role, readiness: { ready: true }, capabilities: { protectedProfile: true, protectedOperations: true, protectedProduction: state.runtimeCapabilities } });
    }
    assert.equal(init.headers['X-NetClaw-Installation'], ID);
    if (state.openLab) {
      assert.equal(init.headers.Cookie, undefined); assert.equal(init.headers['X-NetClaw-CSRF'], undefined); assert.equal(init.headers['X-NetClaw-Owner-Bootstrap'], undefined);
      assert.ok(!route.startsWith('/api/hud/owner/'), 'Open lab must not call owner authentication');
    }
    if (init.method !== 'GET') {
      assert.equal(init.headers.Origin, ORIGIN); assert.equal(init.headers['Content-Type'], 'application/json');
      if (!state.openLab && !init.headers['X-NetClaw-Owner-Bootstrap']) assert.equal(init.headers['X-NetClaw-CSRF'], csrf);
    }
    if (route === '/api/hud/owner/session' && init.method === 'POST') {
      assert.equal(call.body.ticket, ticket); assert.equal(init.headers['X-NetClaw-Owner-Bootstrap'], '1');
      return json(session(), 200, { 'Set-Cookie': cookie + '; Path=/; HttpOnly; SameSite=Strict; Secure; Max-Age=60' });
    }
    if (!state.openLab && !state.authenticated) return json({ code: 'owner_session_required' }, 401);
    if (!state.openLab) assert.equal(init.headers.Cookie, cookie);
    if (route === '/api/hud/owner/session') {
      if (init.method === 'DELETE') return json({ authenticated: false }, 200, { 'Set-Cookie': cookie.split('=')[0] + '=; Path=/; HttpOnly; SameSite=Strict; Secure; Max-Age=0' });
      return json(session());
    }
    if (route === '/api/hud/operations/catalog') return json(catalog);
    if (route === '/api/hud/operations' && init.method === 'POST') {
      const op = operation(call.body.client_nonce, state.openLab ? labPrincipal : principal); operations.set(op.operation_id, op); return json(op);
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
  assert.equal(cloudInputOrigin(ORIGIN + '/'), ORIGIN); assert.equal(cloudInputOrigin(ORIGIN), ORIGIN);
  for (const bad of ['http://border.example.test/', ORIGIN + '/api/', ORIGIN + '/?x', ORIGIN + '/#x', 'https://user:secret@border.example.test/', ORIGIN + '//']) assert.throws(() => cloudInputOrigin(bad));
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
test('Name and HTTPS URL discover an explicit open lab, pin identity and execute exact review without authentication traffic or secrets', async t => {
  const f = fixture(t); f.state.openLab = true;
  const runtime = await discoverCloudBorder(ORIGIN); assert.equal(runtime.installationId, ID);
  assert.equal(f.calls[0].headers['X-NetClaw-Installation'], undefined);
  const writes = [], client = new OwnerClient(ORIGIN, runtime.installationId, async value => writes.push(value), () => {}, 'open-lab');
  t.after(() => client.close());
  await client.connect(); assert.equal(client.operationsReady, true); assert.equal(client.sessionState, undefined); assert.deepEqual(client.principal, labPrincipal);
  const ops = new OwnerOperations(client, storage()), op = await ops.prepare(catalogChoices(await client.catalog())[0]);
  assert.deepEqual(op.review.principal, labPrincipal);
  const done = await ops.decide(op, 'approve'); assert.equal(done.result.durable_ack, true);
  await assert.rejects(client.login(ticket), /does not use sign-in/);
  assert.deepEqual(writes, []);
  assert.ok(f.calls.every(c => !c.route.startsWith('/api/hud/owner/') && !c.headers.Cookie && !c.headers['X-NetClaw-CSRF'] && !c.headers['X-NetClaw-Owner-Bootstrap']));
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 1);
});
test('open-lab discovery and pinned connections refuse absent access, changed identity and auth fallback', async t => {
  const f = fixture(t); await assert.rejects(discoverCloudBorder(ORIGIN), /did not advertise/);
  f.state.openLab = true;
  const client = new OwnerClient(ORIGIN, ID, async () => { throw Error('No secret writes permitted'); }, () => {}, 'open-lab');
  t.after(() => client.close()); await client.connect();
  f.state.openLab = false;
  await assert.rejects(client.catalog(), /open-lab access changed/);
  assert.ok(f.calls.every(c => c.method === 'GET' && !c.route.startsWith('/api/hud/owner/')));
  f.state.openLab = true; f.state.runtimeId = '44444444-4444-4444-8444-444444444444';
  const pinned = new OwnerClient(ORIGIN, ID, undefined, undefined, 'open-lab'); t.after(() => pinned.close());
  await assert.rejects(pinned.connect(), /expected cloud Border/);
});
test('discovery refuses malformed lab access and redirects without sending credentials', async t => {
  const f = fixture(t);
  const runtime = { installationId: ID, kind: 'openclaw', role: 'border', capabilities: { protectedProfile: true, protectedOperations: true, protectedProduction: true } };
  for (const access of [{ mode: 'open-lab', principal }, { mode: 'open-lab', principal: { ...labPrincipal, roles: ['owner'] } }, { mode: 'protected', principal: labPrincipal }]) {
    f.state.hook = (c, json) => c.route === '/api/runtime' ? json({ ...runtime, access }) : undefined;
    await assert.rejects(discoverCloudBorder(ORIGIN), /did not advertise/);
  }
  f.state.hook = (_c, json) => json({}, 302, { Location: 'https://another.example.test' });
  await assert.rejects(discoverCloudBorder(ORIGIN), /did not advertise/);
  assert.ok(f.calls.every(c => c.method === 'GET' && c.headers.Cookie === undefined && c.headers['X-NetClaw-CSRF'] === undefined));
});
test('open lab recovers historical owner failure without reattribution or replay, then separately prepares a lab read after ACK', async t => {
  const f = fixture(t), store = storage(), old = new OwnerOperations(f.client, store); await f.client.login(ticket);
  const reviewed = await old.prepare(selection);
  f.state.hook = c => { if (c.route.endsWith('/decision')) throw Error('lost'); };
  await assert.rejects(old.decide(reviewed, 'approve'));
  f.operations.set(reviewed.operation_id, { ...reviewed, state: 'outcome_unknown', revision: 2, attempt_count: 1, may_have_executed: true, reconciliation_required: true, allowed_actions: ['reconcile'] });
  f.state.hook = undefined; f.state.openLab = true;
  const client = new OwnerClient(ORIGIN, ID, async () => { throw Error('No secret writes permitted'); }, () => {}, 'open-lab'); t.after(() => client.close());
  const resumed = new OwnerOperations(client, store), ref = resumed.references()[0], before = f.calls.length;
  const unknown = await resumed.recover(ref); assert.deepEqual(unknown.review.principal, principal);
  assert.ok(f.calls.slice(before).every(c => c.method === 'GET'));
  await assert.rejects(resumed.prepare(selection), /unresolved/);
  await assert.rejects(resumed.decide(reviewed, 'approve'), /already submitted/);
  f.state.hook = (c, json) => {
    if (!c.route.endsWith('/reconcile')) return;
    const failed = { ...unknown, state: 'failed', revision: 3, reconciliation_required: false, result: { verified: true, durable_ack: true, ack_delivery_pending: false, evidence: { status: 'FAILED' } } };
    f.operations.set(failed.operation_id, failed); return json(failed);
  };
  const failed = await resumed.reconcile(ref); assert.deepEqual(failed.review.principal, principal); assert.equal(failed.result.durable_ack, true);
  const next = await resumed.prepare(selection); assert.deepEqual(next.review.principal, labPrincipal);
  assert.deepEqual(resumed.references()[0], ref); assert.notEqual(next.client_nonce, ref.client_nonce);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 1);
  assert.ok(f.calls.slice(before).every(c => !c.route.startsWith('/api/hud/owner/') && !c.headers.Cookie && !c.headers['X-NetClaw-CSRF']));
});
test('historical unapproved reviews cannot gain a new decision and a fresh lab prepare must match the advertised principal', async t => {
  const f = fixture(t), store = storage(), old = new OwnerOperations(f.client, store); await f.client.login(ticket);
  const historical = await old.prepare(selection); f.state.openLab = true;
  const client = new OwnerClient(ORIGIN, ID, undefined, undefined, 'open-lab'); t.after(() => client.close());
  const resumed = new OwnerOperations(client, store); await resumed.recover(resumed.references()[0]);
  await assert.rejects(resumed.decide(historical, 'approve'), /recovery-only/);
  assert.equal(resumed.references()[0].decision_sent, undefined);
  const fresh = new OwnerOperations(client, storage());
  f.state.hook = (c, json) => c.route === '/api/hud/operations' && c.method === 'POST' ? json(operation(c.body.client_nonce, principal)) : undefined;
  await assert.rejects(fresh.prepare(selection), /does not belong/);
  assert.equal(f.calls.filter(c => c.route.endsWith('/decision')).length, 0);
});
for (const change of [{ runtimeId: '44444444-4444-4444-8444-444444444444' }, { role: 'member' }, { runtimeCapabilities: false }]) test('wrong identity/role/capability refuses before ticket disclosure ' + JSON.stringify(change), async t => {
  const f = fixture(t); Object.assign(f.state, change);
  await assert.rejects(f.client.login(ticket), /expected cloud/);
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
  await assert.rejects(discoverCloudBorder('https://127.0.0.1:' + server.address().port), /did not advertise/);
  const { HudClient } = await load('src/client/hud.ts');
  await assert.rejects(new HudClient('https://127.0.0.1:' + server.address().port, ID, undefined, 'remote-hud').connect());
  assert.equal(calls, 0);
});

async function nativeModules() {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-owner-native-'));
  const file = path.join(directory, 'native.mjs');
  await build({ stdin: { contents: "export {Profiles,hostContext} from './src/state/profiles'; export {Connection,selectConnectionProfile} from './src/connection/connect'; export {Management} from './src/state/management'; export {assertCloudCommand,ownerDecisionDetail} from './src/views/owner';", resolveDir: process.cwd() }, outfile: file, bundle: true, platform: 'node', format: 'esm', target: 'node22', logLevel: 'silent', plugins: [{ name: 'vscode-fixture', setup(b) {
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
test('selected open-lab row opens its overview without disconnecting or touching secrets; a different pinned identity switches authority', async t => {
  const { Profiles, Connection, selectConnectionProfile } = await nativeModules();
  const f = fixture(t); f.state.openLab = true;
  const store = storage(), profiles = new Profiles(store);
  const cloud = await profiles.save({ label: 'Cloud', url: ORIGIN, mode: 'remote-border', access: 'open-lab', installationId: ID, harness: 'openclaw' });
  const forbidden = async () => { throw Error('Open-lab connection must not access SecretStorage'); };
  const connection = new Connection({ get: forbidden, store: forbidden, delete: forbidden }); t.after(() => connection.dispose());
  await connection.connect(cloud);
  const bound = connection.ownerBound(), client = connection.owner, generation = connection.generation;
  const operations = new OwnerOperations(client, store); await operations.prepare(selection);
  const retained = JSON.stringify([...store.state]), before = f.calls.length;
  let switches = 0, views = 0;
  const connect = async p => { switches++; await connection.connect(p); };
  const overview = async () => { views++; await connection.owner.connect(); };
  await selectConnectionProfile({ ...cloud }, connection, connect, overview);
  await selectConnectionProfile({ ...cloud }, connection, connect, overview);
  assert.equal(switches, 0); assert.equal(views, 2); assert.equal(connection.generation, generation); assert.equal(connection.owner, client);
  bound.current(); assert.equal(JSON.stringify([...store.state]), retained);
  assert.ok(f.calls.slice(before).every(c => c.route === '/api/runtime' && c.method === 'GET'));
  const other = { ...cloud, id: 'different-profile', installationId: '44444444-4444-4444-8444-444444444444' };
  f.state.hook = (c, json) => c.route === '/api/runtime' ? json({ installationId: other.installationId, kind: 'openclaw', role: 'border', access: { mode: 'open-lab', principal: labPrincipal }, capabilities: { protectedProfile: true, protectedOperations: true, protectedProduction: true } }) : undefined;
  await selectConnectionProfile(other, connection, connect, overview);
  assert.equal(switches, 1); assert.equal(views, 3); assert.equal(connection.profile.installationId, other.installationId);
  assert.notEqual(connection.owner, client); assert.throws(() => bound.current(), /changed/);
  assert.equal(JSON.stringify([...store.state]), retained);
  assert.ok(f.calls.slice(before).every(c => c.method === 'GET' && !c.route.startsWith('/api/hud/owner/')));
});
test('Name and URL reconnect reuse the exact cloud profile and retained reference while preserving local profiles', async () => {
  const { Profiles } = await nativeModules(), store = storage(), profiles = new Profiles(store);
  const local = await profiles.save({ label: 'Existing local', url: 'http://localhost:3001' });
  const old = await profiles.save({ label: 'Prior cloud label', url: ORIGIN, mode: 'remote-border', installationId: ID, harness: 'openclaw' });
  const key = 'owner-operations.' + createHash('sha256').update(ORIGIN + '|' + ID).digest('hex');
  const reference = [{ client_nonce: 'retained-nonce', operation_id: 'retained-operation', decision_sent: true }]; await store.update(key, reference);
  const connected = await profiles.saveCloud('GCP Border', ORIGIN + '/', ID);
  assert.equal(connected.id, old.id); assert.equal(connected.access, 'open-lab'); assert.equal(connected.installationId, ID);
  assert.equal(profiles.list().length, 2); assert.deepEqual(profiles.list().find(p => p.id === local.id), local);
  assert.deepEqual(store.get(key), reference);
  const beforeChangedIdentity = JSON.stringify([...store.state]);
  await assert.rejects(profiles.saveCloud('Same address, changed identity', ORIGIN + '/', '44444444-4444-4444-8444-444444444444'), /identity changed/);
  assert.equal(JSON.stringify([...store.state]), beforeChangedIdentity);
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

test('advertised remote workspace binds the existing HUD panels while retaining separate protected authority', async t => {
  const { Connection, Profiles, assertCloudCommand } = await nativeModules();
  const f = fixture(t); f.state.openLab = true;
  const features = ['overview', 'chat', 'canvas', 'rag', 'members', 'peers', 'skills', 'runtime', 'tokenomics', 'documentation', 'reference', 'logs', 'operations'];
  f.state.hook = (call, json) => {
    if (call.route === '/api/runtime') return json({ installationId: ID, kind: 'openclaw', role: 'border', access: { mode: 'open-lab', principal: labPrincipal }, readiness: { ready: true }, capabilities: { protectedProfile: true, protectedOperations: true, protectedProduction: true, remoteHud: { schema: 1, features } } });
    if (call.route === '/api/n2n') return json({ members: [{ id: 'actual-fixture-member' }] });
  };
  const store = storage(), profiles = new Profiles(store), profile = await profiles.saveCloud('Cloud', ORIGIN, ID);
  const connection = new Connection({ get: async () => assert.fail('No session read'), store: async () => assert.fail('No session write'), delete: async () => assert.fail('No session delete') });
  t.after(() => connection.dispose()); await connection.connect(profile);
  const bound = connection.bound(), owner = connection.ownerBound();
  assert.equal(bound.client.transport, 'remote-hud'); assert.notEqual(bound.client, owner.client);
  assert.deepEqual((await bound.client.request('GET', '/api/n2n')).members, [{ id: 'actual-fixture-member' }]);
  for (const name of ['openChat','openCanvas','openRag','openPeers','openSkills']) assert.doesNotThrow(() => assertCloudCommand(name, true, [], connection.identity));
  for (const name of ['startClaw','bindWorkspace','configureMcp','prepareChange','manageAssistants','openNativeRuntime','openPeerChat']) assert.throws(() => assertCloudCommand(name, true, [], connection.identity), /local profile/);
  assert.doesNotThrow(() => assertCloudCommand('openDomain', true, ['overview'], connection.identity));
  assert.throws(() => assertCloudCommand('openDomain', true, ['configuration'], connection.identity));
  connection.disconnect(); assert.throws(() => bound.current(), /changed/); assert.throws(() => owner.current(), /changed/);
});
