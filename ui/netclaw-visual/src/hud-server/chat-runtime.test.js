import test from 'node:test';
import assert from 'node:assert/strict';
import { createChatRuntime, gatewayEnvironment, gatewayCallTimeout } from './chat-runtime.js';
import { publicChatModels, resolveChatEffort, resolveChatModel } from './chat-models.js';
const config = { agents: { entries: { engineer: {} }, defaults: { model: 'p/default@private' } } };
const models = [{ provider: 'p', id: 'fast', available: true, thinkingDefault: 'low', thinkingLevels: [{ id: 'low' }, { id: 'high' }] },
  { provider: 'p', id: 'denied', available: false }];
test('slow-host discovery allowance is bounded and does not extend other gateway calls', () => {
  const env = { NETCLAW_GATEWAY_CATALOG_TIMEOUT_MS: '60000', NETCLAW_GATEWAY_SETTINGS_TIMEOUT_MS: '120000' };
  assert.equal(gatewayCallTimeout('models.list', env), 60000);
  assert.equal(gatewayCallTimeout('sessions.patch', env), 120000);
  assert.equal(gatewayCallTimeout('sessions.delete', env), 20000);
  assert.equal(gatewayCallTimeout('models.list', {}), 20000);
  for (const value of ['19999', '60001', 'Infinity', '30000.5', 'bad'])
    assert.equal(gatewayCallTimeout('models.list', { ...env, NETCLAW_GATEWAY_CATALOG_TIMEOUT_MS: value }), 20000);
});
test('available runtime choices and supported efforts are validated without leaking profiles', () => {
  const catalog = publicChatModels(config, models);
  assert.equal(catalog.models.length, 2);
  assert.doesNotMatch(JSON.stringify(catalog), /private/);
  const id = catalog.models[1].id;
  assert.equal(resolveChatModel(config, id, models), 'p/fast');
  assert.equal(resolveChatEffort(config, id, 'high', models), 'high');
  assert.equal(resolveChatEffort(config, id, '', models), '');
  assert.throws(() => resolveChatEffort(config, id, 'ultra', models));
  assert.throws(() => resolveChatEffort(config, id, {}, models));
  assert.throws(() => resolveChatModel(config, id, null));
});
test('runtime catalog coalesces calls and falls back safely on discovery failure', async () => {
  let calls = 0;
  const runtime = createChatRuntime(async (method, params) => { calls++; assert.deepEqual(params, {view:'configured'}); return { models }; });
  const rows = await Promise.all([runtime.catalog(config, '/nonexistent/config.json'), runtime.catalog(config, '/nonexistent/config.json')]);
  assert.equal(calls, 1); assert.equal(rows[0].length, 1);
  assert.equal(await createChatRuntime(async () => { throw Error(); }).catalog(config, '/absent/config.json'), null);
});
test('effort changes require a private key and confirmed session mutation; default clears override', async () => {
  const calls = [];
  const runtime = createChatRuntime(async (method, params, port) => {
    calls.push({ method, params, port }); return { ok: true, entry: { thinkingLevel: params.thinkingLevel } };
  });
  await assert.rejects(runtime.apply({ effort: 'low' }));
  await runtime.apply({ key: 'owned-key', model: 'p/fast', effort: 'low', port: 18789 });
  await runtime.apply({ key: 'owned-key', model: 'p/default', effort: '', port: 18789 });
  assert.deepEqual(calls[0], { method: 'sessions.patch', params: { key: 'owned-key', model: 'p/fast', thinkingLevel: 'low' }, port: 18789 });
  assert.equal(calls[1].params.thinkingLevel, null);
  await assert.rejects(createChatRuntime(async () => ({ ok: true, entry: { thinkingLevel: 'high' } })).apply({ key: 'owned-key', effort: 'low' }));
});

test('malformed discovery metadata cannot introduce selectable model references', () => {
  const catalog = publicChatModels(config, [{available:true}, {available:true,provider:'p',id:'bad\r\nheader'}]);
  assert.equal(catalog.models.length,1);
});

test('gateway target is pinned locally with credentials in environment and the HUD Node interpreter',()=>{
  const result=gatewayEnvironment({gateway:{auth:{token:'local-secret'}}},18789,'/private/config.json',{
    PATH:'/old-node/bin:/usr/bin',OPENCLAW_GATEWAY_URL:'wss://remote.example',OPENCLAW_GATEWAY_TOKEN:'wrong-token',OPENCLAW_GATEWAY_PASSWORD:'stale-password',
  },'/supported-node/bin/node');
  assert.equal(result.OPENCLAW_GATEWAY_URL,'ws://127.0.0.1:18789');
  assert.equal(result.OPENCLAW_GATEWAY_TOKEN,'local-secret');
  assert.equal(result.OPENCLAW_GATEWAY_PASSWORD,'');
  assert.ok(result.PATH.startsWith('/supported-node/bin:'));
  assert.equal(result.OPENCLAW_CONFIG_PATH,'/private/config.json');
  assert.throws(()=>gatewayEnvironment({gateway:{}},18789,'/config',{}));
  assert.throws(()=>gatewayEnvironment({gateway:{auth:{token:'x'}}},'18789','/config',{}));
});
