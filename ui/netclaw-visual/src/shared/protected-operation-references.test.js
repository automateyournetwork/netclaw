import test from 'node:test';
import assert from 'node:assert/strict';
import { operationReferences, parsedVersion, removableOperation } from './protected-operation-references.js';
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
