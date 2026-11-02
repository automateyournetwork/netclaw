import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { JSDOM } from 'jsdom';

const directory = new URL('.', import.meta.url).pathname;
const built = await build({ stdin: { contents: `import React from 'react';import {createRoot} from 'react-dom/client';import View from './ApprovedOperationsView.jsx';let root=createRoot(document.getElementById('root'));window.show=props=>root.render(<View {...props}/>);window.remount=props=>{root.unmount();root=createRoot(document.getElementById('root'));window.show(props);};window.remove=()=>root.unmount();`, resolveDir: directory, loader: 'jsx' }, bundle: true, write: false, format: 'iife', define: { 'process.env.NODE_ENV': '"production"' }, plugins: [{ name: 'css-fixture', setup(builder) { builder.onLoad({ filter: /protected-operations\.css$/ }, () => ({ contents: '', loader: 'js' })); } }] });
const ID = '00000000-0000-4000-8000-000000000171';
const principal = { issuer: 'local', subject: ID, display_name: 'Fixture owner', roles: ['owner'] };
const args = { device_name: 'fixture-router', command: 'show version', timeout: 30, retries: 1 };
const catalog = { revision: 'catalog-1', members: [{ member: { member_id: 'onprem-fixture', key_id: 'member-key', installation_id: ID }, model_profiles: [{ profile_id: 'sonnet-fixture', provider: 'anthropic', model: 'fixture-model' }], tools: [{ tool: 'pyats_run_show_command', arguments: args, device_ref: 'fixture-router' }] }] };
function operation(nonce, changes = {}) { return { operation_id: 'operation-171', client_nonce: nonce, revision: 1, state: 'review_pending', review_digest: 'd'.repeat(64), attempt_count: 0, may_have_executed: false, reconciliation_required: false, review: { principal, border: { identity: 'fixture-border' }, member: catalog.members[0].member, model_profile: catalog.members[0].model_profiles[0], tool_call: { tool: 'pyats_run_show_command', arguments: args, arguments_sha256: 'a'.repeat(64) }, limits: { expires_at_ms: Date.now() + 600000, max_tool_calls: 1, max_inference_calls: 2 } }, allowed_actions: ['approve', 'deny'], ...changes }; }
async function until(predicate) { const end = Date.now() + 3000; while (!predicate()) { if (Date.now() > end) assert.fail('UI condition did not become ready'); await new Promise(resolve => setTimeout(resolve, 5)); } }
async function setup(t, handler = () => {}, { enabled = true, authenticated = true, saved } = {}) {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost:3000', runScripts: 'outside-only', pretendToBeVisual: true }), w = dom.window, calls = [];
  const props = { enabled, installationId: ID }; let signedIn = authenticated;
  if (saved) w.sessionStorage.setItem(`netclaw.protected.${ID}.operation`, JSON.stringify(saved));
  const session = () => ({ authenticated: true, principal, csrf_token: 'csrf-private-fixture', expires_ms: Date.now() + 3600000, installation_id: ID });
  w.fetch = async (url, options = {}) => {
    const method = options.method || 'GET', body = options.body ? JSON.parse(options.body) : undefined;
    calls.push({ url, method, body, headers: options.headers });
    const override = await handler(url, { ...options, method, body });
    let value = override;
    if (value === undefined && url === '/api/hud/owner/session') {
      if (method === 'POST') { signedIn = true; value = session(); }
      else if (method === 'DELETE') { signedIn = false; value = { authenticated: false }; }
      else value = signedIn ? session() : { status: 401, code: 'session_required' };
    }
    if (value === undefined && url === '/api/hud/operations/catalog') value = catalog;
    assert.notEqual(value, undefined, `No fixture for ${method} ${url}`);
    return { status: value.status || 200, ok: !value.status || value.status < 400, json: async () => value };
  };
  w.eval(built.outputFiles[0].text); w.show(props);
  t.after(() => { w.remove(); w.close(); });
  const body = () => w.document.body.textContent, button = label => [...w.document.querySelectorAll('button')].find(value => value.textContent === label);
  return { w, calls, body, button, props };
}

test('disabled protected view has no owner, catalog or operation requests', async t => {
  const f = await setup(t, () => assert.fail('No request allowed'), { enabled: false });
  await until(() => f.body().includes('not enabled')); assert.equal(f.calls.length, 0);
});

test('owner ticket uses password form and explicit bootstrap; tokens never enter browser storage', async t => {
  const f = await setup(t, () => {}, { authenticated: false });
  await until(() => f.button('Sign in'));
  const input = f.w.document.querySelector('input'); assert.equal(input.type, 'password');
  Object.getOwnPropertyDescriptor(f.w.HTMLInputElement.prototype, 'value').set.call(input, 'ticket-private-fixture'); input.dispatchEvent(new f.w.Event('input', { bubbles: true }));
  await until(() => !f.button('Sign in').disabled); f.button('Sign in').click();
  await until(() => f.button('Prepare review'));
  const login = f.calls.find(call => call.method === 'POST');
  assert.deepEqual(login.body, { ticket: 'ticket-private-fixture' }); assert.equal(login.headers['X-NetClaw-Owner-Bootstrap'], '1'); assert.equal(login.headers['X-NetClaw-Installation'], ID);
  assert.equal(f.w.sessionStorage.length, 0); assert.equal(f.w.localStorage.length, 0); assert.doesNotMatch(f.body(), /ticket-private|csrf-private/);
});

test('complete immutable review precedes approval, derives exact arguments and keeps only IDs in storage', async t => {
  let current;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations' && options.method === 'POST') return current = operation(options.body.client_nonce);
    if (url.endsWith('/decision')) return current = { ...current, state: 'dispatch_pending', allowed_actions: ['revoke'], attempt_count: 1, may_have_executed: true };
  });
  await until(() => f.button('Prepare review'));
  assert.equal(f.button('Approve once'), undefined); f.button('Prepare review').click();
  await until(() => f.button('Approve once') && !f.button('Approve once').disabled);
  const review = f.w.document.querySelector('[aria-label="Immutable operation review"]').textContent;
  for (const value of ['Fixture owner', 'member-key', 'fixture-model', 'show version', 'retries', 'max_inference_calls']) assert.ok(review.includes(value));
  const prepare = f.calls.find(call => call.url === '/api/hud/operations'); assert.deepEqual(prepare.body.arguments, args); assert.equal(prepare.body.auth_context, undefined);
  f.button('Approve once').click(); f.button('Approve once').click();
  await until(() => f.body().includes('dispatch_pending'));
  const decisions = f.calls.filter(call => call.url.endsWith('/decision')); assert.equal(decisions.length, 1); assert.deepEqual(decisions[0].body, { revision: 1, review_digest: 'd'.repeat(64), decision: 'approve' }); assert.equal(decisions[0].headers['X-NetClaw-CSRF'], 'csrf-private-fixture');
  const stored = JSON.parse(f.w.sessionStorage.getItem(f.w.sessionStorage.key(0))); assert.deepEqual(Object.keys(stored).sort(), ['client_nonce', 'operation_id']); assert.doesNotMatch(JSON.stringify(stored), /csrf|ticket|arguments|principal|model/);
});

test('lost decision response disables approval and refresh recovers same operation without resubmitting', async t => {
  let current, lost = false;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations' && options.method === 'POST') return current = operation(options.body.client_nonce);
    if (url.endsWith('/decision')) { lost = true; current = { ...current, state: 'reconciliation_required', may_have_executed: true, reconciliation_required: true, allowed_actions: ['reconcile'] }; throw Error('lost response'); }
    if (url === '/api/hud/operations/operation-171' || url.endsWith('/reconcile')) return current;
  });
  await until(() => f.button('Prepare review')); f.button('Prepare review').click(); await until(() => f.button('Approve once') && !f.button('Approve once').disabled);
  f.button('Approve once').click(); await until(() => lost && f.body().includes('nothing was resent'));
  assert.equal(f.button('Approve once').disabled, true); assert.equal(f.button('Prepare a new review'), undefined);
  f.w.remount(f.props); await until(() => f.body().includes('reconciliation_required'));
  assert.equal(f.calls.filter(call => call.url.endsWith('/decision')).length, 1); assert.equal(f.calls.filter(call => call.url === '/api/hud/operations' && call.method === 'POST').length, 1);
  f.button('Reconcile existing operation').click(); await until(() => f.calls.some(call => call.url.endsWith('/reconcile')));
  assert.equal(f.calls.filter(call => call.url.endsWith('/decision')).length, 1);
});

test('lost prepare is recovered by original nonce; authority is never recreated on remount', async t => {
  let current;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations' && options.method === 'POST') { current = operation(options.body.client_nonce); throw Error('lost prepare'); }
    if (url.startsWith('/api/hud/operations?client_nonce=')) { assert.equal(decodeURIComponent(url.split('=')[1]), current.client_nonce); return current; }
  });
  await until(() => f.button('Prepare review')); f.button('Prepare review').click(); await until(() => f.body().includes('nothing was resent'));
  assert.equal(f.button('Prepare review'), undefined); f.w.remount(f.props);
  await until(() => f.body().includes('operation-171'));
  assert.equal(f.calls.filter(call => call.url === '/api/hud/operations' && call.method === 'POST').length, 1);
});

test('receipt verification and durable ACK remain distinct and evidence is escaped', async t => {
  const result = operation('saved-nonce', { state: 'completed', attempt_count: 1, allowed_actions: [], result: { verified: true, durable_ack: true, ack_delivery_pending: true, digest: 'result-digest', evidence: { output: '<img src=x onerror=alert(1)>' } } });
  const f = await setup(t, url => url === '/api/hud/operations/operation-171' ? result : undefined, { saved: { client_nonce: 'saved-nonce', operation_id: 'operation-171' } });
  await until(() => f.body().includes('Execution evidence'));
  assert.match(f.body(), /Signature and bindings verifiedYes/); assert.match(f.body(), /acknowledgement durably storedYes/); assert.match(f.body(), /Pending reconciliation/);
  assert.equal(f.w.document.querySelectorAll('img').length, 0); assert.match(f.w.document.querySelector('[aria-label="Verified execution evidence"]').textContent, /<img/);
});

test('session expiry during status read removes private review and retains only recovery IDs', async t => {
  let expired = false;
  const f = await setup(t, url => url === '/api/hud/operations/operation-171' ? expired ? { status: 401 } : operation('saved-nonce') : undefined, { saved: { client_nonce: 'saved-nonce', operation_id: 'operation-171' } });
  await until(() => f.body().includes('Immutable approval review')); expired = true; f.button('Check status').click();
  await until(() => f.body().includes('Owner sign-in'));
  assert.doesNotMatch(f.body(), /member-key|Immutable approval review/); assert.equal(f.w.sessionStorage.length, 1);
});

test('foreign operation recovery never displays private response or enables a decision', async t => {
  const f = await setup(t, url => url === '/api/hud/operations/operation-171' ? operation('foreign-nonce', { operation_id: 'foreign-operation' }) : undefined, { saved: { client_nonce: 'saved-nonce', operation_id: 'operation-171' } });
  await until(() => f.body().includes('identity changed'));
  assert.doesNotMatch(f.body(), /Immutable approval review|foreign-operation|member-key/); assert.equal(f.button('Approve once'), undefined);
});
