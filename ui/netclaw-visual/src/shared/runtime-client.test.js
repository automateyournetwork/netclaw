import test from 'node:test';
import assert from 'node:assert/strict';
const memory=()=>{const map=new Map();return {getItem:k=>map.has(k)?map.get(k):null,setItem:(k,v)=>map.set(k,String(v)),removeItem:k=>map.delete(k),map};};
const idA='11111111-1111-4111-8111-111111111111',idB='22222222-2222-4222-8222-222222222222';
const moduleFor=()=>import('./runtime-client.js?test='+Math.random());
test('runtime storage never imports OpenClaw content into Hermes and preserves both installations',async t=>{
 const oldFetch=globalThis.fetch;t.after(()=>globalThis.fetch=oldFetch);const storage=memory();storage.setItem('chat','legacy-private');
 const api=await moduleFor();let meta={kind:'hermes',installationId:idA};globalThis.fetch=async()=>({ok:true,json:async()=>meta});
 await api.bootstrapRuntime();assert.equal(api.runtimeStorage(storage).getItem('chat'),null);api.runtimeStorage(storage).setItem('chat','Hermes A');
 meta={kind:'hermes',installationId:idB};await api.bootstrapRuntime();assert.equal(api.runtimeStorage(storage).getItem('chat'),null);
 meta={kind:'hermes',installationId:idA};await api.bootstrapRuntime();assert.equal(api.runtimeStorage(storage).getItem('chat'),'Hermes A');
 meta={kind:'openclaw',installationId:idB};await api.bootstrapRuntime();assert.equal(api.runtimeStorage(storage).getItem('chat'),'legacy-private');assert.equal(storage.getItem('chat'),'legacy-private');
 meta={kind:'openclaw',installationId:idA};await api.bootstrapRuntime();assert.equal(api.runtimeStorage(storage).getItem('chat'),null);
});
test('unknown request survives refresh; observation never submits again and late result recovers',async t=>{
 const oldFetch=globalThis.fetch,oldWindow=globalThis.window;t.after(()=>{globalThis.fetch=oldFetch;globalThis.window=oldWindow;});globalThis.window={sessionStorage:memory()};let posts=0,state='unknown';
 globalThis.fetch=async(url,options={})=>{if(url==='/api/runtime')return {ok:true,json:async()=>({kind:'hermes',installationId:idA})};if(options.method==='POST'){posts++;return {ok:true,json:async()=>({requestId:'owned',state:'queued'})};}return {ok:true,json:async()=>({requestId:'owned',state,fromGateway:state==='completed',output:'Recovered'})};};
 const api=await moduleFor();await api.bootstrapRuntime();await assert.rejects(api.sendChat({hudThread:'t',message:'work'}),/Outcome unknown/);assert.equal(posts,1);
 const refreshed=await moduleFor();await refreshed.bootstrapRuntime();await assert.rejects(refreshed.sendChat({hudThread:'t',message:'work'}),/unresolved/);assert.equal(posts,1);
 state='completed';assert.equal((await refreshed.observeRequest('t')).output,'Recovered');assert.equal(posts,1);assert.equal(refreshed.pendingRequest('t'),null);
});

test('open tab refuses a changed runtime before submission and keeps the original storage binding',async t=>{
 const oldFetch=globalThis.fetch;t.after(()=>globalThis.fetch=oldFetch);let meta={kind:'hermes',installationId:idA},posts=0;
 globalThis.fetch=async(_url,options={})=>{if(options.method==='POST')posts++;return {ok:true,json:async()=>meta};};
 const api=await moduleFor();await api.bootstrapRuntime();const storage=memory(),bound=api.runtimeStorage(storage);bound.setItem('draft','private A');
 meta={kind:'hermes',installationId:idB};await assert.rejects(api.sendChat({hudThread:'t',message:'private A'}),/selected runtime changed/);assert.equal(posts,0);
 await api.bootstrapRuntime();assert.equal(bound.getItem('draft'),'private A');assert.equal(api.runtimeStorage(storage).getItem('draft'),null);
});
