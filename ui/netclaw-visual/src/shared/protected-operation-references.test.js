import test from 'node:test';
import assert from 'node:assert/strict';
import { operationReferences, operationSelection, parsedVersion, removableOperation, verifiedResultSummary } from './protected-operation-references.js';
const storage = () => { const rows = new Map(); return { getItem: key => rows.get(key) ?? null, setItem: (key, value) => rows.set(key, value), removeItem: key => rows.delete(key), rows }; };
const terminal = (i = 0) => ({ client_nonce: `nonce-${i}`, operation_id: `op-${i}`, state: 'completed', reconciliation_required: false, may_have_executed: true, attempt_count: 1, result: { verified: true, durable_ack: true, ack_delivery_pending: false } });
test('migration preserves original IDs, and collection stores only bounded references', () => {
  const s = storage(); s.setItem('netclaw.protected.install.operation', JSON.stringify({ client_nonce: 'nonce-0', operation_id: 'op-0' }));
  const refs = operationReferences('install', s); assert.equal(refs.read().length, 1); assert.equal(s.getItem('netclaw.protected.install.operation'), null);
  refs.put({ client_nonce: 'nonce-1', operation_id: 'op-1', principal: 'never-persist', result: 'never-persist' });
  assert.equal(refs.read().length, 2); assert.doesNotMatch([...s.rows.values()].join(''), /never-persist/);
  assert.throws(() => refs.put({ client_nonce: 'nonce-0', operation_id: 'changed' }), /identity changed/);
  assert.throws(() => refs.put({ client_nonce: 'new-nonce', operation_id: 'op-0' }), /identity changed/);
});
test('32-reference capacity never evicts an unresolved ID and only explicit resolved removal frees a slot', () => {
  const refs = operationReferences('install', storage()); for (let i = 0; i < 32; i++) refs.put(terminal(i));
  assert.throws(() => refs.put({ client_nonce: 'overflow' }), /capacity/); assert.equal(refs.read().length, 32);
  assert.throws(() => refs.remove({ ...terminal(), state: 'outcome_unknown' }), /Unresolved/);
  assert.throws(() => refs.remove({ ...terminal(), result: { ...terminal().result, ack_delivery_pending: true } }), /Unresolved/);
  refs.remove(terminal()); refs.put({ client_nonce: 'new-nonce' }); assert.equal(refs.read().length, 32);
});
test('safe pre-dispatch refusal removal requires all explicit absence-of-effect fields', () => {
  for (const state of ['refused', 'denied', 'revoked']) {
    const value = { state, attempt_count: 0, may_have_executed: false, reconciliation_required: false, result: null };
    assert.equal(removableOperation(value), true);
    for (const change of [{ attempt_count: 1 }, { may_have_executed: true }, { reconciliation_required: true }, { result: {} }]) assert.equal(removableOperation({ ...value, ...change }), false);
  }
  assert.equal(removableOperation({ state: 'failed', attempt_count: 0, may_have_executed: false, reconciliation_required: false }), false);
});
test('only a proven local pre-submission failure may discard a nonce without an ID', () => {
  const refs = operationReferences('install', storage()); refs.put({ client_nonce: 'draft' }); refs.discardUnsubmitted('draft'); assert.deepEqual(refs.read(), []);
  refs.put({ client_nonce: 'admitted', operation_id: 'op' }); assert.throws(() => refs.discardUnsubmitted('admitted'), /admitted/);
});
test('malformed or conflicting storage is refused without replacing retained authority references', () => {
  const s = storage(), key = 'netclaw.protected.install.operations.v2'; s.setItem(key, '[{"client_nonce":"one","secret":"bad"}]');
  assert.throws(() => operationReferences('install', s).read(), /invalid/); assert.match(s.getItem(key), /secret/);
  s.setItem(key, JSON.stringify([{ client_nonce: 'one', operation_id: 'a' }])); s.setItem('netclaw.protected.install.operation', JSON.stringify({ client_nonce: 'one', operation_id: 'b' }));
  assert.throws(() => operationReferences('install', s).read(), /conflict/); assert.match(s.getItem(key), /"a"/);
});
test('version projection uses the actual signed tool payload path and never model text or guessed labels', () => {
  const value = { result: { verified: true, evidence: { output: { model_answer: 'invented', tool: { parsed: true, output: { version: { version: '17.18.2', os: 'IOS' } } } } } } };
  assert.deepEqual(parsedVersion(value), { version: '17.18.2', os: 'IOS' });
  for (const edited of [{ result: { ...value.result, verified: false } }, { result: { verified: true, evidence: { output: { version: { version: 'wrong' }, parsed: true } } } }]) assert.deepEqual(parsedVersion(edited), { version: null, os: null });
  value.result.evidence.output.tool.parsed = false; assert.equal(parsedVersion(value).version, null);
  value.result.evidence.output.tool.parsed = true; value.result.evidence.output.tool.output.version.version = 'x'.repeat(201); assert.equal(parsedVersion(value).version, null);
  value.result.evidence.output.tool.output.version = []; assert.deepEqual(parsedVersion(value), { version: null, os: null });
});

const deviceArguments = { object_type: 'dcim.device', object_id: 7, fields: ['id', 'name', 'status', 'site', 'device_type', 'last_updated'], brief: false };
const prefixArguments = { object_type: 'ipam.prefix', object_id: 9, fields: ['id', 'prefix', 'status', 'vrf', 'last_updated'], brief: false };
const nativeOperation = (name, args, output) => ({
  review: { member: { member_id: 'risk/cloud-netbox' }, tool_call: { tool: name, arguments: args, endpoint_sha256: 'e'.repeat(64) } },
  result: { verified: true, evidence: { output: { model_answer: 'invented model summary', tool: {
    schemaVersion: 1, tool: name, arguments: structuredClone(args), output, endpoint_sha256: 'e'.repeat(64),
    source_sha256: 'a'.repeat(64), skill_sha256: 'b'.repeat(64), mcp_schema_sha256: 'c'.repeat(64), mcp_calls: 1,
  } } } },
});
test('full selection identity distinguishes members, tools and every argument while ignoring object key order', () => {
  const call = { tool: 'netbox_get_object_by_id', arguments: deviceArguments };
  const original = operationSelection('risk/cloud-netbox', call);
  assert.ok(original);
  const reordered = Object.fromEntries(Object.entries(deviceArguments).reverse());
  assert.equal(operationSelection('risk/cloud-netbox', { ...call, arguments: reordered, device_ref: 'different label' }), original);
  for (const change of [{ object_id: 8 }, { fields: [...deviceArguments.fields].reverse() }, { brief: true }, { extra: true }]) {
    assert.notEqual(operationSelection('risk/cloud-netbox', { ...call, arguments: { ...deviceArguments, ...change } }), original);
  }
  assert.notEqual(operationSelection('risk/other-member', call), original);
  assert.notEqual(operationSelection('risk/cloud-netbox', { ...call, tool: 'different_tool' }), original);
  assert.equal(operationSelection('risk/cloud-netbox', { ...call, arguments: { bad: undefined } }), null);
  const cycle = {}; cycle.self = cycle;
  assert.equal(operationSelection('risk/cloud-netbox', { ...call, arguments: cycle }), null);
  assert.equal(operationSelection('risk/cloud-netbox', { ...call, arguments: { text: 'x'.repeat(65536) } }), null);
});
test('verified native summaries bind exact approved source, object and calculator arguments', () => {
  const device = nativeOperation('netbox_get_object_by_id', deviceArguments, { id: 7, name: 'demo-router' });
  const prefix = nativeOperation('netbox_get_object_by_id', prefixArguments, { id: 9, prefix: '198.51.100.0/24' });
  const subnet = nativeOperation('subnet_calculator', { cidr: '198.51.100.0/24' }, { network_address: '198.51.100.0', prefix_length: 24, num_addresses: 256, usable_hosts_count: 254 });
  assert.equal(verifiedResultSummary(device), 'NetBox device demo-router · ID 7');
  assert.equal(verifiedResultSummary(prefix), 'NetBox prefix 198.51.100.0/24 · ID 9');
  assert.equal(verifiedResultSummary(subnet), '198.51.100.0/24 · 254 usable hosts');
  for (const value of [device, prefix, subnet]) {
    for (const mutate of [
      v => { v.result.verified = false; },
      v => { v.result.evidence.output.tool.tool = 'unapproved'; },
      v => { v.result.evidence.output.tool.arguments.extra = true; },
      v => { v.result.evidence.output.tool.endpoint_sha256 = 'd'.repeat(64); },
      v => { v.result.evidence.output.tool.skill_sha256 = 'not-a-digest'; },
      v => { v.result.evidence.output.tool.mcp_calls = 2; },
      v => { v.result.evidence.output.tool.schemaVersion = '1'; },
      v => { v.result.evidence.output.tool.output = ['invalid']; },
    ]) {
      const changed = structuredClone(value); mutate(changed); assert.equal(verifiedResultSummary(changed), 'Unavailable');
    }
  }
});
test('native summaries refuse malformed, mismatched or excessive typed source fields', () => {
  for (const output of [{ id: 8, name: 'wrong' }, { id: 7, name: 'x'.repeat(201) }, { id: 7, name: 'line\nbreak' }, { id: 7, name: {} }]) {
    assert.equal(verifiedResultSummary(nativeOperation('netbox_get_object_by_id', deviceArguments, output)), 'Unavailable');
  }
  for (const value of ['999.1.2.3/24', '198.51.100.1/24', '198.51.100.0/99', '2001:db8::/129', '<script>/24']) {
    assert.equal(verifiedResultSummary(nativeOperation('netbox_get_object_by_id', prefixArguments, { id: 9, prefix: value })), 'Unavailable');
  }
  assert.equal(verifiedResultSummary(nativeOperation('netbox_get_object_by_id', prefixArguments, { id: 9, prefix: '2001:db8::/48' })), 'NetBox prefix 2001:db8::/48 · ID 9');
  for (const args of [{ ...deviceArguments, brief: true }, { ...deviceArguments, fields: [] }, { ...deviceArguments, object_type: 'dcim.site' }]) {
    assert.equal(verifiedResultSummary(nativeOperation('netbox_get_object_by_id', args, { id: 7, name: 'unexpected' })), 'Unavailable');
  }
  for (const [cidr, output] of [
    ['0.0.0.0/24', { network_address: '0.0.0.0', prefix_length: 24, num_addresses: 256, usable_hosts_count: 254 }],
    ['255.255.255.252/30', { network_address: '255.255.255.252', prefix_length: 30, num_addresses: 4, usable_hosts_count: 2 }],
    ['198.51.100.1/24', { network_address: '198.51.100.0', prefix_length: 24, num_addresses: 256, usable_hosts_count: 254 }],
    ['198.51.100.0/24', { network_address: '198.51.100.0', prefix_length: 24, num_addresses: 256, usable_hosts_count: '254' }],
    ['198.51.100.0/24', { network_address: '198.51.100.0', prefix_length: 24, num_addresses: 256, usable_hosts_count: 255 }],
  ]) assert.equal(verifiedResultSummary(nativeOperation('subnet_calculator', { cidr }, output)), 'Unavailable');
});

test('R07 send markers advance before I/O and survive old status projections', () => {
  const s = storage(), refs = operationReferences('install', s), value = { client_nonce: 'nonce', operation_id: 'operation' };
  refs.put(value); refs.markSent(value, 'decision'); refs.put(value);
  assert.equal(refs.read()[0].decision_sent, true);
  assert.throws(() => refs.markSent(value, 'decision'), /already/);
  refs.markSent(value, 'revoke'); refs.put(value);
  assert.equal(refs.read()[0].revoke_sent, true);
});
