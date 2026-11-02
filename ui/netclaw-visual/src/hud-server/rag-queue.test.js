import test from 'node:test';
import assert from 'node:assert/strict';
import { createRagQueue } from './rag-queue.js';

test('RAG status polling cannot start another server during ingestion', async () => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  const calls = [];
  const call = createRagQueue(async tool => { calls.push(tool); if (tool === 'rag_ingest') await gate; return tool; });
  const ingest = call('rag_ingest', { file_path: '/owned/document.txt' });
  const listing = call('rag_list');
  const repeated = call('rag_list');
  const stats = call('rag_stats');
  await new Promise(setImmediate);
  assert.deepEqual(calls, ['rag_ingest']);
  assert.equal(listing, repeated);
  release();
  assert.deepEqual(await Promise.all([ingest, listing, repeated, stats]), ['rag_ingest', 'rag_list', 'rag_list', 'rag_stats']);
  assert.deepEqual(calls, ['rag_ingest', 'rag_list', 'rag_stats']);
});

test('reads after a mutation wait for fresh state and writes are never coalesced', async () => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  let value = 0; const calls = [];
  const call = createRagQueue(async tool => { calls.push(tool); await gate; if (tool === 'rag_ingest') value++; return value; });
  const before = call('rag_list');
  const first = call('rag_ingest'); const second = call('rag_ingest');
  const after = call('rag_list');
  assert.notEqual(before, after); assert.notEqual(first, second);
  release();
  assert.deepEqual(await Promise.all([before, first, second, after]), [0, 1, 2, 2]);
  assert.deepEqual(calls, ['rag_list', 'rag_ingest', 'rag_ingest', 'rag_list']);
});

test('bounded queue refuses excess work and progresses after a failed call', async () => {
  let release; const gate = new Promise(resolve => { release = resolve; });
  const call = createRagQueue(async tool => { await gate; if (tool === 'rag_ingest') throw Error('index failure'); return tool; }, { maxPending: 2 });
  const failed = assert.rejects(call('rag_ingest'), /index failure/);
  const next = call('rag_list');
  await assert.rejects(call('rag_search'), /capacity/);
  release(); await failed; assert.equal(await next, 'rag_list');
  assert.equal(await call('rag_stats'), 'rag_stats');
});
