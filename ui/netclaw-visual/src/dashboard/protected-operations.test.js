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
async function setup(t, handler = () => {}, { enabled = true, authenticated = true, saved, retainMultiple = false } = {}) {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost:3000', runScripts: 'outside-only', pretendToBeVisual: true }), w = dom.window, calls = [];
  const props = { enabled, installationId: ID, retainMultiple }; let signedIn = authenticated;
  if (saved) w.sessionStorage.setItem(`netclaw.protected.${ID}.${Array.isArray(saved) ? 'operations.v2' : 'operation'}`, JSON.stringify(saved));
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
  assert.equal(f.button('Prepare review'), undefined); assert.equal(f.button('Discard rejected review'), undefined); f.w.remount(f.props);
  await until(() => f.body().includes('operation-171'));
  assert.equal(f.calls.filter(call => call.url === '/api/hud/operations' && call.method === 'POST').length, 1);
});

test('confirmed pre-admission refusal requires explicit discard and a fresh prepare nonce', async t => {
  let submissions = 0;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations' && options.method === 'POST') {
      if (++submissions === 1) return { status: 400, code: 'invalid_argument', admission: 'not_submitted' };
      return operation(options.body.client_nonce);
    }
  });
  await until(() => f.button('Prepare review')); f.button('Prepare review').click();
  await until(() => f.button('Discard rejected review') && !f.button('Discard rejected review').disabled);
  assert.match(f.body(), /rejected before submission/); assert.doesNotMatch(f.body(), /may have been accepted/);
  assert.equal(f.w.sessionStorage.length, 0); assert.equal(submissions, 1);
  assert.equal(f.button('Check status'), undefined); assert.equal(f.button('Approve once'), undefined);
  f.button('Discard rejected review').click(); await until(() => f.button('Prepare review') && !f.button('Prepare review').disabled);
  assert.equal(submissions, 1); f.button('Prepare review').click(); await until(() => f.button('Approve once'));
  const requests = f.calls.filter(call => call.method === 'POST' && call.url === '/api/hud/operations');
  assert.equal(requests.length, 2); assert.notEqual(requests[0].body.client_nonce, requests[1].body.client_nonce);
  assert.equal(f.calls.filter(call => call.url.endsWith('/decision')).length, 0);
});

test('reload after a confirmed unsubmitted draft does not strand its nonce or resubmit', async t => {
  const f = await setup(t, (url, options) => url === '/api/hud/operations' && options.method === 'POST'
    ? { status: 400, code: 'invalid_argument', admission: 'not_submitted' } : undefined);
  await until(() => f.button('Prepare review')); f.button('Prepare review').click();
  await until(() => f.button('Discard rejected review')); f.w.remount(f.props);
  await until(() => f.button('Prepare review'));
  assert.equal(f.w.sessionStorage.length, 0);
  assert.equal(f.calls.filter(call => call.method === 'POST' && call.url === '/api/hud/operations').length, 1);
});

for (const status of [400, 409, 503]) test(`prepare HTTP${status} without pre-admission proof preserves recovery identity`, async t => {
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations' && options.method === 'POST') return { status, code: 'fixture_refusal' };
    if (url.startsWith('/api/hud/operations?client_nonce=')) return { status: 404, admission: 'not_submitted' };
  });
  await until(() => f.button('Prepare review')); f.button('Prepare review').click();
  await until(() => f.button('Check status') && !f.button('Check status').disabled);
  assert.equal(f.button('Discard rejected review'), undefined); assert.equal(f.w.sessionStorage.length, 1);
  f.button('Check status').click(); await until(() => f.body().includes('No owned operation'));
  assert.equal(f.button('Discard rejected review'), undefined); assert.equal(f.w.sessionStorage.length, 1);
  assert.equal(f.calls.filter(call => call.method === 'POST' && call.url === '/api/hud/operations').length, 1);
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

const devices = ['R1', 'R2', 'SW1', 'SW2'];
const fourCatalog = { ...catalog, members: [{ ...catalog.members[0], tools: devices.map(device => ({ ...catalog.members[0].tools[0], device_ref: device, arguments: { ...args, device_name: device } })) }] };
function deviceOperation(nonce, device, number, changes = {}) {
  const original = operation(nonce);
  return { ...original, operation_id: `operation-${number}`, review: { ...original.review, tool_call: { ...original.review.tool_call, device_ref: device, arguments: { ...args, device_name: device } } }, ...changes };
}
const receipt = (version = '17.18.2') => ({ verified: true, durable_ack: true, ack_delivery_pending: false, digest: 'fixture-digest', evidence: { output: { model_answer: 'not used for facts', tool: { parsed: true, output: { version: { version, os: 'IOS' } } } } } });
function input(f, selector, value, event = 'input') {
  const field = f.w.document.querySelector(selector);
  Object.getOwnPropertyDescriptor((field.tagName === 'SELECT' ? f.w.HTMLSelectElement : f.w.HTMLInputElement).prototype, 'value').set.call(field, value);
  field.dispatchEvent(new f.w.Event(event, { bubbles: true }));
}
test('production four-device reviews remain independent and reload restores all receipts by status only', async t => {
  const operations = new Map(); let count = 0;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations/catalog') return fourCatalog;
    if (url === '/api/hud/operations' && options.method === 'POST') { const op = deviceOperation(options.body.client_nonce, options.body.arguments.device_name, ++count); operations.set(op.operation_id, op); return op; }
    const id = url.split('/')[4], previous = operations.get(id);
    if (previous && url.endsWith('/decision')) { const done = { ...previous, state: 'completed', may_have_executed: true, attempt_count: 1, allowed_actions: [], result: receipt() }; operations.set(id, done); return done; }
    if (previous) return previous;
  }, { retainMultiple: true });
  await until(() => f.button('Prepare review') && !f.button('Prepare review').disabled);
  for (let i = 0; i < devices.length; i++) {
    // Each selector is under a separate label: select by its label text.
    const select = [...f.w.document.querySelectorAll('label')].find(label => label.textContent.startsWith('Read-only call')).querySelector('select');
    select.value = String(i); select.dispatchEvent(new f.w.Event('change', { bubbles: true }));
    await until(() => !f.button('Prepare review').disabled); f.button('Prepare review').click();
    await until(() => f.button('Approve once') && !f.button('Approve once').disabled);
    assert.match(f.w.document.querySelector('[aria-label="Immutable operation review"]').textContent, new RegExp(devices[i]));
    f.button('Approve once').click(); f.button('Approve once').click(); await until(() => f.button('Remove resolved reference'));
  }
  assert.equal(f.calls.filter(row => row.url.endsWith('/decision')).length, 4);
  assert.equal(f.w.document.querySelectorAll('tbody tr').length, 4); assert.match(f.body(), /IOS \/ 17.18.2/);
  const saved = JSON.parse(f.w.sessionStorage.getItem(`netclaw.protected.${ID}.operations.v2`)); assert.equal(saved.length, 4); assert.equal(new Set(saved.map(row => row.client_nonce)).size, 4); assert.ok(saved.every(row => Object.keys(row).sort().join(',') === 'client_nonce,operation_id'));
  const boundary = f.calls.length; f.w.remount(f.props); await until(() => f.w.document.querySelectorAll('tbody tr').length === 4 && !f.body().includes('Awaiting confirmation'));
  assert.ok(f.calls.slice(boundary).every(row => row.method === 'GET')); assert.equal(count, 4);
});
test('production unknown row stays retained, does not retry, and preserves another device selection', async t => {
  let current;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations/catalog') return fourCatalog;
    if (url === '/api/hud/operations' && options.method === 'POST') return current = deviceOperation(options.body.client_nonce, 'R1', 1);
    if (url.endsWith('/decision')) { current = { ...current, state: 'reconciliation_required', may_have_executed: true, reconciliation_required: true, allowed_actions: ['reconcile'] }; throw Error('lost'); }
    if (url === '/api/hud/operations/operation-1') return current;
  }, { retainMultiple: true });
  await until(() => f.button('Prepare review') && !f.button('Prepare review').disabled); f.button('Prepare review').click(); await until(() => f.button('Approve once') && !f.button('Approve once').disabled); f.button('Approve once').click();
  await until(() => f.body().includes('nothing was resent')); assert.equal(f.button('Remove resolved reference'), undefined); assert.equal(f.button('Prepare review').disabled, true);
  const select = [...f.w.document.querySelectorAll('label')].find(label => label.textContent.startsWith('Read-only call')).querySelector('select'); select.value = '1'; select.dispatchEvent(new f.w.Event('change', { bubbles: true })); await until(() => !f.button('Prepare review').disabled);
  f.w.remount(f.props); await until(() => f.body().includes('reconciliation_required'));
  assert.equal(f.calls.filter(row => row.url.endsWith('/decision')).length, 1); assert.equal(f.calls.filter(row => row.url === '/api/hud/operations' && row.method === 'POST').length, 1);
});
test('production typed-ID recovery is an authenticated status read and rejects a substituted operation', async t => {
  const f = await setup(t, url => url === '/api/hud/operations/retained-id' ? deviceOperation('retained-nonce', 'R1', 1, { operation_id: 'retained-id', state: 'completed', allowed_actions: [], result: receipt() }) : url === '/api/hud/operations/foreign-id' ? deviceOperation('foreign-nonce', 'R2', 2) : undefined, { retainMultiple: true });
  await until(() => f.button('Recover existing operation'));
  input(f, 'input', 'retained-id'); await until(() => !f.button('Recover existing operation').disabled); f.button('Recover existing operation').click(); await until(() => f.body().includes('retained-id') && f.body().includes('Execution evidence'));
  assert.equal(f.w.document.querySelectorAll('tbody tr').length, 1); assert.ok(f.calls.every(row => row.method === 'GET'));
  input(f, 'input', 'foreign-id'); await until(() => !f.button('Recover existing operation').disabled); f.button('Recover existing operation').click(); await until(() => f.body().includes('identity changed'));
  assert.equal(f.w.document.querySelectorAll('tbody tr').length, 1); assert.doesNotMatch(f.body(), /foreign-nonce/);
});
test('production pending ACK cannot be removed and unverified or malformed parsed fields stay unavailable', async t => {
  const values = [deviceOperation('n1', 'R1', 1, { state: 'completed', result: { ...receipt(), ack_delivery_pending: true } }), deviceOperation('n2', 'R2', 2, { state: 'completed', result: { ...receipt('invented'), verified: false } })];
  const f = await setup(t, url => values.find(value => url === '/api/hud/operations/' + value.operation_id), { retainMultiple: true, saved: values.map(({ client_nonce, operation_id }) => ({ client_nonce, operation_id })) });
  await until(() => f.body().includes('ACK delivery pending')); assert.equal(f.button('Remove resolved reference'), undefined); assert.doesNotMatch(f.body(), /invented/);
  assert.match(f.w.document.querySelectorAll('tbody tr')[1].textContent, /Unavailable \/ Unavailable/);
});

const cloudTools = [
  { tool: 'netbox_get_object_by_id', device_ref: 'NetBox device 7', endpoint_sha256: 'e'.repeat(64), arguments: { object_type: 'dcim.device', object_id: 7, fields: ['id', 'name', 'status', 'site', 'device_type', 'last_updated'], brief: false } },
  { tool: 'netbox_get_object_by_id', device_ref: 'NetBox prefix 7', endpoint_sha256: 'e'.repeat(64), arguments: { object_type: 'ipam.prefix', object_id: 7, fields: ['id', 'prefix', 'status', 'vrf', 'last_updated'], brief: false } },
  { tool: 'subnet_calculator', device_ref: 'Subnet 198.51.100.0/24', endpoint_sha256: 'e'.repeat(64), arguments: { cidr: '198.51.100.0/24' } },
];
const cloudCatalog = { ...catalog, members: [{ ...catalog.members[0], member: { ...catalog.members[0].member, member_id: 'risk/cloud-member' }, tools: cloudTools }] };
const cloudOutputs = [{ id: 7, name: 'demo-router' }, { id: 7, prefix: '198.51.100.0/24' }, { network_address: '198.51.100.0', prefix_length: 24, num_addresses: 256, usable_hosts_count: 254 }];
function cloudOperation(nonce, index, id, changes = {}) {
  const original = operation(nonce);
  return { ...original, operation_id: id, review: { ...original.review, member: cloudCatalog.members[0].member, tool_call: cloudTools[index] }, ...changes };
}
function cloudReceipt(index, output = cloudOutputs[index]) {
  return { verified: true, durable_ack: true, ack_delivery_pending: false, digest: 'fixture-native-digest', evidence: { output: {
    model_answer: 'fixture-only-private-response', tool: { schemaVersion: 1, tool: cloudTools[index].tool, arguments: structuredClone(cloudTools[index].arguments), output,
      endpoint_sha256: 'e'.repeat(64), source_sha256: 'a'.repeat(64), skill_sha256: 'b'.repeat(64), mcp_schema_sha256: 'c'.repeat(64), mcp_calls: 1 },
  } } };
}
function selectCall(f, index) {
  const select = [...f.w.document.querySelectorAll('label')].find(label => label.textContent.startsWith('Read-only call')).querySelector('select');
  select.value = String(index); select.dispatchEvent(new f.w.Event('change', { bubbles: true }));
}
test('production mixed NetBox and subnet approvals retain exact identities and reload only reads status', async t => {
  const operations = new Map(); let count = 0;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations/catalog') return cloudCatalog;
    if (url === '/api/hud/operations' && options.method === 'POST') {
      const index = cloudTools.findIndex(tool => tool.tool === options.body.tool && JSON.stringify(tool.arguments) === JSON.stringify(options.body.arguments));
      assert.notEqual(index, -1); const op = cloudOperation(options.body.client_nonce, index, `cloud-${++count}`); operations.set(op.operation_id, { op, index }); return op;
    }
    const row = operations.get(url.split('/')[4]);
    if (row && url.endsWith('/decision')) return row.op = { ...row.op, state: 'completed', may_have_executed: true, attempt_count: 1, allowed_actions: [], result: cloudReceipt(row.index) };
    if (row) return row.op;
  }, { retainMultiple: true });
  await until(() => f.button('Prepare review') && !f.button('Prepare review').disabled);
  assert.doesNotMatch(f.body(), /on-prem|Each device requires/);
  for (let index = 0; index < 3; index++) {
    selectCall(f, index); await until(() => !f.button('Prepare review').disabled); f.button('Prepare review').click();
    await until(() => f.button('Approve once') && !f.button('Approve once').disabled);
    const review = JSON.parse(f.w.document.querySelector('[aria-label="Immutable operation review"]').textContent);
    assert.deepEqual(review.tool_call, cloudTools[index]); f.button('Approve once').click(); await until(() => f.button('Remove resolved reference'));
  }
  const rows = [...f.w.document.querySelectorAll('tbody tr')].map(row => row.textContent);
  assert.match(rows[0], /NetBox device demo-router · ID 7/); assert.match(rows[1], /NetBox prefix 198.51.100.0\/24 · ID 7/); assert.match(rows[2], /198.51.100.0\/24 · 254 usable hosts/);
  const stored = JSON.parse(f.w.sessionStorage.getItem(`netclaw.protected.${ID}.operations.v2`));
  assert.equal(stored.length, 3); assert.ok(stored.every(row => Object.keys(row).sort().join(',') === 'client_nonce,operation_id'));
  assert.doesNotMatch(JSON.stringify([...Object.keys(f.w.sessionStorage).map(key => f.w.sessionStorage.getItem(key))]), /demo-router|private-response|object_type|cidr|csrf/);
  const boundary = f.calls.length; f.w.remount(f.props); await until(() => f.w.document.querySelectorAll('tbody tr').length === 3 && !f.body().includes('Awaiting confirmation'));
  assert.ok(f.calls.slice(boundary).every(row => row.method === 'GET')); assert.equal(count, 3);
  assert.equal(f.calls.filter(row => row.url.endsWith('/decision')).length, 3);
});
test('unknown NetBox selection stays blocked while distinct same-member prefix and subnet remain eligible', async t => {
  let current;
  const f = await setup(t, (url, options) => {
    if (url === '/api/hud/operations/catalog') return cloudCatalog;
    if (url === '/api/hud/operations' && options.method === 'POST') return current = cloudOperation(options.body.client_nonce, 0, 'cloud-unknown');
    if (url.endsWith('/decision')) {
      current = { ...current, state: 'reconciliation_required', may_have_executed: true, reconciliation_required: true, allowed_actions: ['reconcile'] }; throw Error('lost response');
    }
    if (url === '/api/hud/operations/cloud-unknown') return current;
  }, { retainMultiple: true });
  await until(() => f.button('Prepare review') && !f.button('Prepare review').disabled); f.button('Prepare review').click();
  await until(() => f.button('Approve once') && !f.button('Approve once').disabled); f.button('Approve once').click(); await until(() => f.body().includes('nothing was resent'));
  assert.equal(f.button('Prepare review').disabled, true); assert.equal(f.button('Remove resolved reference'), undefined);
  selectCall(f, 1); await until(() => !f.button('Prepare review').disabled);
  selectCall(f, 2); await until(() => f.w.document.querySelector('[aria-label="Candidate arguments"]').textContent.includes('cidr')); assert.equal(f.button('Prepare review').disabled, false);
  selectCall(f, 0); await until(() => f.button('Prepare review').disabled);
  const boundary = f.calls.length; f.w.remount(f.props); await until(() => f.body().includes('reconciliation_required'));
  assert.equal(f.button('Prepare review').disabled, true); assert.ok(f.calls.slice(boundary).every(row => row.method === 'GET'));
  assert.equal(f.calls.filter(row => row.url.endsWith('/decision')).length, 1); assert.equal(f.calls.filter(row => row.url === '/api/hud/operations' && row.method === 'POST').length, 1);
});
test('native cloud summaries escape source markup and exclude unverified or mismatched evidence', async t => {
  const hostile = '<img src=x onerror=alert(1)>', values = [
    cloudOperation('cloud-safe-nonce', 0, 'cloud-safe', { state: 'completed', result: cloudReceipt(0, { id: 7, name: hostile }) }),
    cloudOperation('cloud-unverified-nonce', 0, 'cloud-unverified', { state: 'completed', result: { ...cloudReceipt(0, { id: 7, name: 'unverified-native-name' }), verified: false } }),
    cloudOperation('cloud-mismatch-nonce', 1, 'cloud-mismatch', { state: 'completed', result: cloudReceipt(1, { id: 99, prefix: '203.0.113.0/24' }) }),
  ];
  const f = await setup(t, url => values.find(value => url === '/api/hud/operations/' + value.operation_id), { retainMultiple: true, saved: values.map(({ client_nonce, operation_id }) => ({ client_nonce, operation_id })) });
  await until(() => f.body().includes('Verified result') && f.body().includes(hostile));
  assert.equal(f.w.document.querySelectorAll('img,script').length, 0); assert.doesNotMatch(f.body(), /unverified-native-name/);
  const rows = [...f.w.document.querySelectorAll('tbody tr')];
  assert.match(rows[0].textContent, /<img src=x onerror=alert\(1\)>/); assert.match(rows[1].textContent, /Unavailable/); assert.match(rows[2].textContent, /Unavailable/); assert.doesNotMatch(rows[2].textContent, /203\.0\.113/);
});
