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

test('Standard Chat receipt preserves original identity across lost admission, refresh and repeated recovery',async t=>{
 const oldFetch=globalThis.fetch,oldWindow=globalThis.window;t.after(()=>{globalThis.fetch=oldFetch;globalThis.window=oldWindow;});
 globalThis.window={sessionStorage:memory()};let posts=0;const anchor={count:0,sha256:'a'.repeat(64)};
 globalThis.fetch=async(url,options={})=>{
  if(url==='/api/runtime')return {ok:true,json:async()=>({kind:'hermes',installationId:idA})};
  if(options.method==='POST'){
   posts++;assert.equal(JSON.parse(options.body).submission,undefined);
   if(posts===1)throw TypeError('lost admission response');
   return {ok:true,json:async()=>({requestId:'second',state:'queued'})};
  }
  if(url.startsWith('/api/chat/requests?'))return {ok:true,json:async()=>({requestId:'owned',submission:{prompt:'forged'}})};
  return {ok:true,json:async()=>({requestId:posts===1?'owned':'second',state:'completed',response:'answer',submission:{prompt:'forged'},nonce:'forged'})};
 };
 const api=await moduleFor();await api.bootstrapRuntime();
 await assert.rejects(api.sendChat({hudThread:'t',message:'ORIGINAL'},undefined,anchor),/lost admission/);
 assert.equal(api.pendingRequest('t').submission.prompt,'ORIGINAL');
 const refreshed=await moduleFor();await refreshed.bootstrapRuntime();const result=await refreshed.observeRequest('t');
 assert.equal(result.submission.prompt,'ORIGINAL');assert.deepEqual(result.submission.anchor,anchor);
 assert.notEqual(result.submission.nonce,'forged');assert.equal(refreshed.pendingRequest('t').state,'completed');
 assert.equal((await refreshed.observeRequest('t')).requestId,'owned');assert.equal(posts,1);
 await refreshed.sendChat({hudThread:'t',message:'NEXT'},undefined,anchor);assert.equal(posts,2);
 assert.equal(refreshed.pendingRequest('t').submission.prompt,'NEXT');
});

test('reviewed capacity release is distinct from acknowledgment, cancellable and preserves receipt',async t=>{
 const oldFetch=globalThis.fetch,oldWindow=globalThis.window;t.after(()=>{globalThis.fetch=oldFetch;globalThis.window=oldWindow;});
 let accept=false,fail=false;const confirmations=[],posts=[];globalThis.window={sessionStorage:memory(),confirm:text=>{confirmations.push(text);return accept;}};
 globalThis.fetch=async(url,options={})=>{
  if(url==='/api/runtime')return {ok:true,json:async()=>({kind:'hermes',installationId:idA})};
  if(options.method==='POST'){posts.push([url,JSON.parse(options.body)]);return {ok:!fail,json:async()=>({thread:'fresh'})};}
  return {ok:true,json:async()=>({requestId:'owned',state:'unknown',capacityReleaseEligible:true})};
 };
 const api=await moduleFor();await api.bootstrapRuntime();api.restoreOwnedRequest('old',{requestId:'owned',state:'unknown'});
 await assert.rejects(api.observeRequest('old'),/Outcome unknown/);
 assert.equal(await api.newConversation('old',{releaseCapacity:true}),null);assert.equal(posts.length,0);
 assert.match(confirmations[0],/history and tool evidence/);assert.match(confirmations[0],/still run alongside/);
 accept=true;await api.newConversation('old');assert.deepEqual(posts[0][1],{acknowledgedUncertainRequestId:'owned'});
 fail=true;await assert.rejects(api.newConversation('old',{releaseCapacity:true}),/unresolved request/);
 assert.equal(api.pendingRequest('old').requestId,'owned');
 fail=false;await api.newConversation('old',{releaseCapacity:true});
 assert.deepEqual(posts.at(-1),['/api/chat/conversations',{acknowledgedUncertainRequestId:'owned',releaseUncertainCapacity:true}]);
 assert.equal(api.pendingRequest('old').state,'unknown');
 api.restoreOwnedRequest('other',{requestId:'other',state:'running'});
 await assert.rejects(api.newConversation('other',{releaseCapacity:true}),/owned unknown/);
 assert.equal(posts.length,3);
});


test('explicit full lab conversation bootstrap and writes never request session or retain credential headers',async t=>{
 const oldFetch=globalThis.fetch;t.after(()=>globalThis.fetch=oldFetch);const calls=[];
 globalThis.fetch=async(url,options={})=>{calls.push([url,options]);return {ok:true,json:async()=>url==='/api/runtime'?{kind:'openclaw',installationId:idA,access:{mode:'open-lab'},capabilities:{remoteHud:{schema:1,features:['chat']}}}:{fromGateway:true,response:'fixture'}};};
 const api=await moduleFor();await api.bootstrapRuntime();await api.ensureConversationContext();await api.sendChat({hudThread:'public',message:'hello'});
 await api.workspaceFetch('/api/rag/search',{method:'POST',credentials:'include',headers:{Cookie:'old',Authorization:'Bearer old','X-CSRF-Token':'old'}});
 assert.equal(calls.some(([url])=>url.includes('/session')),false);assert.ok(calls.every(([,o])=>o.credentials==='omit'));
 const headers=calls.at(-1)[1].headers;for(const name of ['Cookie','Authorization','X-CSRF-Token'])assert.equal(headers.has(name),false);assert.equal(headers.get('X-NetClaw-Installation'),idA);
});
