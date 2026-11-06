import test from 'node:test';
import assert from 'node:assert/strict';
import { load } from './load.mjs';
const { HudClient, endpoint } = await load('src/client/hud.ts');
const { remoteHudFeatures, remoteHudRoute } = await load('src/client/remote-hud.ts');
const origin = 'https://border.example.test', id = '22222222-2222-4222-8222-222222222222';
const runtime = () => ({kind:'openclaw', role:'border', installationId:id, readiness:{ready:true}, capabilities:{remoteHud:{schema:1,features:['overview','chat','canvas','rag','members','peers','skills','runtime','tokenomics','documentation','reference','logs','operations']}},access:{mode:'open-lab',principal:{issuer:'open-lab',subject:'55555555-5555-4555-8555-555555555555',display_name:'Unauthenticated lab operator',roles:['lab-operator']}}});
function fixture(t) {
  const calls=[], state={runtime:runtime(),hook:undefined}, original=globalThis.fetch;
  const json=(v,status=200,headers={})=>new Response(JSON.stringify(v),{status,headers:{'Content-Type':'application/json',...headers}});
  globalThis.fetch=async(url,init)=>{
    assert.equal(new URL(url).origin,origin); assert.equal(init.redirect,'error');
    assert.equal(init.headers['X-NetClaw-Installation'],id);
    assert.equal(init.headers.Cookie,undefined); assert.equal(init.headers['X-NetClaw-CSRF'],undefined);
    if(init.method!=='GET')assert.equal(init.headers.Origin,origin);
    const call={route:new URL(url).pathname,method:init.method,body:init.body,headers:init.headers};calls.push(call);
    assert.ok(!call.route.includes('/session'));
    const custom=await state.hook?.(call,json);if(custom)return custom;
    return json(call.route==='/api/runtime'?state.runtime:call.route==='/api/chat'?{fromGateway:true,response:'Fixture answer'}:{source:call.route});
  };
  t.after(()=>{globalThis.fetch=original;});
  const client=new HudClient(origin,id,()=>assert.fail('No secret/session write is permitted'),'remote-hud');
  t.after(()=>client.close());return {client,calls,state,json};
}
test('explicit remote HUD reuses normal Chat, Canvas and RAG transport without a session facade',async t=>{
  assert.throws(()=>endpoint(origin));assert.throws(()=>new HudClient(origin,undefined,undefined,'remote-hud'));
  const f=fixture(t);await f.client.connect();
  assert.equal(remoteHudFeatures(f.client.runtime).has('canvas'),true);
  for(const route of ['/api/n2n','/api/graph','/api/hud/runtime','/api/rag/stats','/api/rag/documents','/api/chat/models','/api/chat/conversations','/api/hud/documentation','/api/hud/reference','/api/hud/logs'])await f.client.request('GET',route);
  const c=await f.client.newConversation();let persisted=0;await f.client.send(c,'Ask selected Border','Selected Canvas context',async()=>persisted++);
  assert.equal(persisted,1);assert.equal(c.state,'completed');assert.equal(c.messages.at(-1).content,'Fixture answer');
  await f.client.upload('fixture.txt',new TextEncoder().encode('Explicit fixture document'),'text');
  const upload=f.calls.find(c=>c.route==='/api/rag/upload');assert.ok(upload.body instanceof FormData);assert.equal(upload.headers['Content-Type'],undefined);
  assert.equal(f.calls.filter(c=>c.route==='/api/chat').length,1);
  assert.throws(()=>f.client.restoreCookie('anything'),/does not use a session/);
});
test('remote HUD refuses absent features and all administration or cross-origin routes before network',async t=>{
  const f=fixture(t);await f.client.connect();const before=f.calls.length;
  for(const [method,route] of [['POST','/api/hud/session'],['PUT','/api/env'],['PUT','/api/mcp/configuration'],['POST','/api/n2n/chat'],['GET','/api/hud/configuration'],['GET','/api/hud/logs/../../env'],['GET','/api/hud/logs/%2e%2e'],['GET','https://elsewhere.test/api/runtime'],['GET','/api/graph?admin=true'],['GET','/api/hud/logs/runtime?q=a&q=b'],['GET','/api/hud/logs/runtime?severity=trace'],['GET','/api/hud/logs/runtime?path=etc']])await assert.rejects(f.client.request(method,route));
  assert.equal(f.calls.length,before);
  await f.client.request('GET','/api/hud/logs/runtime.log?q=warning&severity=warning');
  await f.client.request('POST','/api/chat/conversations/agent%3Amain/open',{});
  const limited=runtime();limited.capabilities.remoteHud.features=['overview'];
  assert.throws(()=>remoteHudRoute(limited,'POST','/api/chat'),/does not expose/);
  limited.capabilities.remoteHud.features=['overview','canvas'];assert.throws(()=>remoteHudFeatures(limited),/requires Chat/);
});
test('changed installation, access or removed workspace capability prevents a remote Chat submit',async t=>{
  const f=fixture(t);await f.client.connect();const c=await f.client.newConversation();f.state.runtime={...runtime(),installationId:'33333333-3333-4333-8333-333333333333'};
  await assert.rejects(f.client.send(c,'Must not dispatch'),/changed/);assert.equal(f.calls.filter(c=>c.route==='/api/chat').length,0);
  for(const mutate of [r=>delete r.capabilities.remoteHud,r=>r.access.mode='owner-session']){
    const r=runtime();mutate(r);assert.throws(()=>remoteHudFeatures(r));
  }
});
test('a dropped remote Chat response remains unknown and is never automatically resubmitted',async t=>{
  const f=fixture(t);await f.client.connect();const c=await f.client.newConversation();f.state.hook=call=>{if(call.route==='/api/chat')throw Error('Connection lost');};
  await assert.rejects(f.client.send(c,'Once'));assert.equal(c.state,'unknown');
  await assert.rejects(f.client.send(c,'Again'),/unresolved/);await f.client.status(c);
  assert.equal(f.calls.filter(c=>c.route==='/api/chat').length,1);
});
test('closing during a delayed identity response cannot revive remote workspace state',async t=>{
  const f=fixture(t);let respond;f.state.hook=(call,json)=>call.route==='/api/runtime'?new Promise(resolve=>{respond=()=>resolve(json(runtime()));}):undefined;
  const connecting=f.client.connect();while(!respond)await new Promise(r=>setImmediate(r));f.client.close();respond();
  await assert.rejects(connecting,/closed/);assert.equal(f.client.runtime,undefined);await assert.rejects(f.client.connect(),/closed/);
});
test('open-lab HUD rejects unexpected cookies without persisting them',async t=>{
  const f=fixture(t);f.state.hook=(_call,json)=>json(runtime(),200,{'Set-Cookie':'nc_hud_bad=secret'});
  await assert.rejects(f.client.connect(),/session cookie/);assert.equal(f.client.runtime,undefined);await assert.rejects(f.client.request('GET','/api/runtime'),/closed/);
});

test('ordinary federation explicitly enables peer chat and refuses mode changes without retry', async t => {
  const f = fixture(t);
  f.state.runtime.capabilities.externalFederation = {schema:1,execution:'ordinary',peerChat:true};
  await f.client.connect();
  await f.client.request('POST','/api/n2n/chat',{peer:'as65002-192.0.2.2',text:'once'});
  assert.equal(f.calls.filter(c=>c.route==='/api/n2n/chat').length,1);
  f.state.runtime = runtime();
  Object.assign(f.state.runtime.capabilities,{protectedProfile:true,protectedOperations:true,protectedProduction:true});
  await assert.rejects(f.client.verifyIdentity(),/mode changed/);
  await assert.rejects(f.client.request('POST','/api/n2n/chat',{}),/closed/);
  assert.equal(f.calls.filter(c=>c.route==='/api/n2n/chat').length,1);
});

test('ordinary federation cannot mix protected claims or add unrecognized capability fields', () => {
  for (const change of [{protectedProfile:true},{protectedOperations:false}]) {
    const r=runtime();r.capabilities.externalFederation={schema:1,execution:'ordinary',peerChat:true};Object.assign(r.capabilities,change);
    assert.throws(()=>remoteHudFeatures(r),/inconsistent/);
  }
  const r=runtime();r.capabilities.externalFederation={schema:1,execution:'ordinary',peerChat:true,admin:true};
  assert.throws(()=>remoteHudFeatures(r),/inconsistent/);
});

test('Name and URL discovery accepts ordinary capability without claiming protected authority', async t => {
  const {discoverCloudBorder,OwnerClient} = await load('src/client/owner.ts');
  const original=globalThis.fetch, r=runtime();
  r.capabilities.externalFederation={schema:1,execution:'ordinary',peerChat:true};
  globalThis.fetch=async()=>new Response(JSON.stringify(r),{headers:{'Content-Type':'application/json'}});
  t.after(()=>globalThis.fetch=original);
  assert.equal((await discoverCloudBorder(origin)).capabilities.externalFederation.execution,'ordinary');
  const client=new OwnerClient(origin,id,()=>assert.fail('No session writes'));
  await client.connect();assert.equal(client.openLab,true);assert.equal(client.operationsReady,false);
  client.close();
});
