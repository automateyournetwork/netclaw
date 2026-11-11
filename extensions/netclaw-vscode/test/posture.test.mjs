import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import { once } from 'node:events';
import { load } from './load.mjs';

const { validatePosture, fetchNodePosture, formatPosture, PostureError } = await load('src/client/posture.ts');
const GOOD = {
  schema_version: 1, node: 'nne1', region: 'northamerica-northeast1',
  sandbox: { name: 'netclaw-node', phase: 'Ready', policy_version: 3, policy_sha256: 'a'.repeat(64), landlock: 'hard_requirement' },
  components: [
    { name: 'border-role', inside_sandbox: true, state: 'running' },
    { name: 'hud-ingress', inside_sandbox: true, state: 'running' },
    { name: 'etcd-voter', inside_sandbox: false, disposition: 'host network; container policy', state: 'running' }],
  guard: { mode: 'action', state: 'running', fail_closed: true, last_block_ms: null },
  observed_at_ms: 1794300000000 };
const clone = () => JSON.parse(JSON.stringify(GOOD));

async function serve(handler) {
  const server = http.createServer(handler);
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  return { origin: `http://127.0.0.1:${server.address().port}`, close: () => { server.close(); server.closeAllConnections(); } };
}
const json = (res, body, headers = {}) => { res.writeHead(200, { 'content-type': 'application/json', ...headers }); res.end(typeof body === 'string' ? body : JSON.stringify(body)); };

test('validatePosture accepts the contract and refuses every deviation', () => {
  assert.equal(validatePosture(GOOD).node, 'nne1');
  const mutate = f => { const v = clone(); f(v); return v; };
  const cases = {
    'extra key': mutate(v => { v.extra = 1; }),
    'missing guard': mutate(v => { delete v.guard; }),
    'schema version': mutate(v => { v.schema_version = 2; }),
    'bad hash': mutate(v => { v.sandbox.policy_sha256 = 'zz'; }),
    'unknown phase': mutate(v => { v.sandbox.phase = 'Enforced'; }),
    'landlock claim': mutate(v => { v.sandbox.landlock = 'enforced'; }),
    'outside without disposition': mutate(v => { delete v.components[2].disposition; }),
    'inside with disposition': mutate(v => { v.components[0].disposition = 'x'; }),
    'outside claims enforced': mutate(v => { v.components[2].disposition = 'enforced by OpenShell'; }),
    'duplicate component': mutate(v => { v.components[1].name = 'border-role'; }),
    'no components': mutate(v => { v.components = []; }),
    'secret-looking value': mutate(v => { v.node = 'sk-ant-abc'; }),
    'secret-looking disposition': mutate(v => { v.components[2].disposition = 'api_key in env'; }),
    'guard mode': mutate(v => { v.guard.mode = 'off'; }),
    'negative observed time': mutate(v => { v.observed_at_ms = -1; }),
    'last_block_ms string': mutate(v => { v.guard.last_block_ms = 'x'; }),
  };
  for (const [name, value] of Object.entries(cases)) assert.throws(() => validatePosture(value), PostureError, name);
  for (const bad of [null, [], 'x', 5]) assert.throws(() => validatePosture(bad), PostureError);
});

test('fetchNodePosture reads a valid posture over the origin and sends a plain GET', async () => {
  let seen;
  const s = await serve((req, res) => { seen = { method: req.method, url: req.url, accept: req.headers.accept, cookie: req.headers.cookie }; json(res, GOOD); });
  try {
    const posture = await fetchNodePosture(s.origin);
    assert.equal(posture.sandbox.policy_version, 3);
    assert.deepEqual(seen, { method: 'GET', url: '/api/hud/posture', accept: 'application/json', cookie: undefined });
  } finally { s.close(); }
});

test('fetchNodePosture fails clearly and never implies confinement', async () => {
  const run = async (handler, pattern) => {
    const s = await serve(handler);
    try { await assert.rejects(fetchNodePosture(s.origin), e => e instanceof PostureError && pattern.test(e.message)); } finally { s.close(); }
  };
  await run((q, r) => { r.writeHead(404, { 'content-type': 'application/json' }); r.end('{"code":"posture_unavailable"}'); }, /does not publish a node posture.*Nothing is implied about its confinement/);
  await run((q, r) => { r.writeHead(503, { 'content-type': 'application/json' }); r.end('{"code":"posture_invalid"}'); }, /could not provide a valid node posture.*Nothing is implied/);
  await run((q, r) => { r.writeHead(302, { location: '/elsewhere' }); r.end(); }, /Could not reach/);
  await run((q, r) => json(r, GOOD, { 'set-cookie': 'a=1' }), /unexpected node posture response/);
  await run((q, r) => { r.writeHead(200, { 'content-type': 'text/html' }); r.end('<html>'); }, /unexpected node posture response/);
  await run((q, r) => json(r, '{not json'), /not valid JSON/);
  await run((q, r) => json(r, { ...clone(), pad: 'x'.repeat(20000) }), /larger than allowed/);
  await run((q, r) => json(r, { ...clone(), extra: 1 }), /does not match the contract/);
  await assert.rejects(fetchNodePosture('http://127.0.0.1:1'), e => e instanceof PostureError && /Could not reach/.test(e.message));
});

test('formatPosture lists inside and outside components with dispositions and never claims enforcement', () => {
  const text = formatPosture(GOOD, 'https://nne1-3d69b5.automateyournetwork.com');
  assert.match(text, /Node posture — nne1 · Montreal \(northamerica-northeast1\)/);
  assert.match(text, /Observed: 2026-.*an observation reported by the node, not authority/);
  assert.match(text, /Sandbox: netclaw-node · phase Ready · policy v3 · sha256 a{64} · Landlock hard_requirement/);
  assert.match(text, /Inside the sandbox \(2\):\n {2}- border-role \(running\)\n {2}- hud-ingress \(running\)/);
  assert.match(text, /Outside the sandbox \(1\):\n {2}- etcd-voter \(running\) — host network; container policy/);
  assert.match(text, /Guard: mode action · running · fail-closed yes · last block none recorded/);
  assert.match(text, /not proof that any control is enforced/);
  assert.ok(!/enforced by/i.test(text));
  const blocked = formatPosture({ ...GOOD, guard: { ...GOOD.guard, last_block_ms: 1794300001000 } }, 'https://ew1-f37491.automateyournetwork.com');
  assert.match(blocked, /Belgium/);
  assert.match(blocked, /last block 2026-/);
});

test('the command is declared, registered directly (read-only) and not added to the cloud command allow-list', () => {
  const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
  const entry = pkg.contributes.commands.find(c => c.command === 'netclaw.showNodePosture');
  assert.equal(entry?.title, 'Show Node Posture');
  assert.equal(entry?.category, 'NetClaw');
  const ext = fs.readFileSync('src/extension.ts', 'utf8');
  assert.match(ext, /registerCommand\("netclaw\.showNodePosture"/);
  assert.ok(!/register\("showNodePosture"/.test(ext), 'not routed through the cloud-gated register helper');
  assert.match(ext, /connection\.profile\?\.mode !== "remote-border"/);
  assert.match(ext, /fetchNodePosture\(origin\)/);
  const owner = fs.readFileSync('src/views/owner.ts', 'utf8');
  assert.ok(!owner.includes('showNodePosture'), 'the cloud command allow-list is unchanged');
});
