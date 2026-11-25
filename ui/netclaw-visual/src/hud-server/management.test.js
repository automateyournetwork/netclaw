import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { openclawAgents, clearAgentCatalog, AGENT_CATALOG_MAX_AGE_MS } from './management.js';

function fixture(t) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'netclaw-agents-'));
  t.after(() => { clearAgentCatalog(); fs.rmSync(dir, { recursive: true, force: true }); });
  clearAgentCatalog();
  const cli = path.join(dir, 'openclaw');
  const config = path.join(dir, 'openclaw.json');
  fs.writeFileSync(cli, '#!/bin/sh\n');
  fs.writeFileSync(config, '{"agents":{"list":[{"id":"main"}]}}');
  const env = { HOME: dir, OPENCLAW_HOME: dir, OPENCLAW_STATE_DIR: dir, OPENCLAW_CONFIG_PATH: config };
  const calls = [];
  const run = async () => { calls.push(1); return [{ id: 'main', isDefault: true, workspace: `${dir}/w${calls.length}`, identity: { name: 'Private' } }]; };
  return { dir, cli, config, env, calls, run };
}

test('agent catalog runs the CLI once while the config is unchanged and keeps only binding fields', async t => {
  const f = fixture(t);
  const first = await openclawAgents(f.cli, f.env, { run: f.run });
  const second = await openclawAgents(f.cli, f.env, { run: f.run });
  assert.equal(f.calls.length, 1);
  assert.equal(second, first);
  assert.ok(Object.isFrozen(first) && Object.isFrozen(first[0]));
  assert.deepEqual(first, [{ id: 'main', isDefault: true, workspace: `${f.dir}/w1` }]);
});

test('a config change, a different profile or the maximum age starts a new run', async t => {
  const f = fixture(t);
  let clock = 1000; const now = () => clock;
  await openclawAgents(f.cli, f.env, { run: f.run, now });
  fs.writeFileSync(f.config, '{"agents":{"list":[{"id":"main"},{"id":"lab"}]}}');
  const changed = await openclawAgents(f.cli, f.env, { run: f.run, now });
  assert.equal(f.calls.length, 2); assert.equal(changed[0].workspace, `${f.dir}/w2`);
  await openclawAgents(f.cli, { ...f.env, OPENCLAW_PROFILE: 'other' }, { run: f.run, now });
  assert.equal(f.calls.length, 3);
  await openclawAgents(f.cli, { ...f.env, OPENCLAW_PROFILE: 'other' }, { run: f.run, now });
  assert.equal(f.calls.length, 3);
  clock += AGENT_CATALOG_MAX_AGE_MS;
  await openclawAgents(f.cli, { ...f.env, OPENCLAW_PROFILE: 'other' }, { run: f.run, now });
  assert.equal(f.calls.length, 4);
});

test('concurrent callers share one run', async t => {
  const f = fixture(t);
  let release; const gate = new Promise(r => { release = r; });
  const run = async () => { f.calls.push(1); await gate; return [{ id: 'main' }]; };
  const results = Promise.all([1, 2, 3].map(() => openclawAgents(f.cli, f.env, { run })));
  release();
  const [a, b, c] = await results;
  assert.equal(f.calls.length, 1);
  assert.equal(a, b); assert.equal(b, c);
});

test('a failed run is not kept', async t => {
  const f = fixture(t);
  let fail = true;
  const run = async () => { f.calls.push(1); if (fail) throw Error('cli failed'); return [{ id: 'main' }]; };
  await assert.rejects(openclawAgents(f.cli, f.env, { run }), /cli failed/);
  fail = false;
  assert.deepEqual(await openclawAgents(f.cli, f.env, { run }), [{ id: 'main', isDefault: undefined, workspace: undefined }]);
  assert.equal(f.calls.length, 2);
});

test('a config change during a run is not cached under the new config', async t => {
  const f = fixture(t);
  let release; const gate = new Promise(r => { release = r; });
  const run = async () => { f.calls.push(1); if (f.calls.length === 1) await gate; return [{ id: 'main', workspace: `w${f.calls.length}` }]; };
  const slow = openclawAgents(f.cli, f.env, { run });
  fs.writeFileSync(f.config, '{"agents":{"list":[{"id":"changed"}]}}');
  release(); await slow;
  const fresh = await openclawAgents(f.cli, f.env, { run });
  assert.equal(f.calls.length, 2); assert.equal(fresh[0].workspace, 'w2');
});
