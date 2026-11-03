import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import crypto from 'node:crypto';
// Independent synthetic HTTP fixture; no owner, provider or device is invoked.
const root=process.env.NETCLAW_171_TEST_SOURCE || new URL('../../',import.meta.url).pathname;
const {protectedLegacyBoundary,selectedEnvironmentFiles,protectedHudConfig,mountProtectedOperations}=await import(pathToFileURL(path.join(root,'ui/netclaw-visual/src/hud-server/protected-operations.js')));
const express=(await import(pathToFileURL(path.join(root,'ui/netclaw-visual/node_modules/express/index.js')))).default;
for(const kind of ['openclaw','hermes'])for(const profile of [false,true])test(`selected environment ${kind} protected=${profile}`,()=>{
 const home='/fixture/'+kind+'/.env',repo='/fixture/repository/.env';
 assert.deepEqual(selectedEnvironmentFiles({kind,envPath:home},repo,profile),kind==='hermes'||profile?[home]:[home,repo]);
});
for(const profile of [false,true])test(`real HTTP legacy boundary requested=${profile}`,async()=>{
 const app=express();app.use(protectedLegacyBoundary(profile));app.use((_req,res)=>res.json({legacyReached:true}));
 const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
 try {
  const url='http://127.0.0.1:'+server.address().port;
  for(const route of ['/api/chat','/api/terminal/execute','/api/settings/environment','/api/n2n/chat/send','/api//chat','/api/chat/']){
   const result=await fetch(url+route,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
   assert.equal(result.status,profile?403:200);
   const body=await result.json();assert.equal(body.legacyReached,profile?undefined:true);
   if(profile)assert.equal(result.headers.get('cache-control'),'no-store');
  }
  const result=await fetch(url+'/api/runtime');assert.equal(result.status,200);
 }finally{await new Promise(resolve=>server.close(resolve));}
});
test('missing protected origins does not reopen legacy routes',async()=>{
 const environment={N2N_PROTECTED_OPERATIONS:'1'}, config=protectedHudConfig(environment);
 assert.equal(config.enabled,false);
 const app=express();
 mountProtectedOperations(app,{installation:{installationId:'fixture',home:'/fixture/private'},config,client:{async call(){throw Error('must not call owner backend when misconfigured')}}});
 app.use(protectedLegacyBoundary(environment.N2N_PROTECTED_OPERATIONS==='1'));
 app.use((_req,res)=>res.json({legacyReached:true}));
 const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
 try{
  const url='http://127.0.0.1:'+server.address().port;
  assert.equal((await fetch(url+'/api/chat',{method:'POST'})).status,403);
  const protectedRoute=await fetch(url+'/api/hud/operations/catalog');assert.equal(protectedRoute.status,404);
  assert.equal((await protectedRoute.json()).code,'protected_operations_disabled');
 }finally{await new Promise(resolve=>server.close(resolve));}
});

test('real HTTP preparation accepts enrolled slash member IDs without widening nonce IDs',async()=>{
 const installation={installationId:'fixture-installation',home:'/fixture/private'};
 const cookie='c'.repeat(43),csrf='s'.repeat(43),calls=[];
 const principal={issuer:'local',subject:'fixture-owner',display_name:'Fixture owner',roles:['owner']};
 const session={installation_id:installation.installationId,csrf_token:csrf,
  session_hash:crypto.createHash('sha256').update(cookie).digest('hex'),principal,
  auth_generation:1,expires_ms:Date.now()+60000};
 const app=express();
 mountProtectedOperations(app,{installation,config:{enabled:true,origins:['http://127.0.0.1:3000'],secure:false},client:{
  async call(method,params){
   if(method==='owner.session')return session;
   assert.equal(method,'prepare');calls.push(params);return {operation_id:'fixture-operation',member_id:params.member_id};
  }
 }});
 const server=app.listen(0,'127.0.0.1');await new Promise(resolve=>server.once('listening',resolve));
 const body={client_nonce:'fixture-nonce',catalog_revision:'fixture-revision',member_id:'risk/member',
  model_profile_id:'fixture-profile',tool:'pyats_run_show_command',arguments:{command:'show version'}};
 const headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:3000',
  'X-NetClaw-Installation':installation.installationId,'X-NetClaw-CSRF':csrf,
  'Cookie':'nc_owner_'+installation.installationId+'='+cookie};
 try{
  const url='http://127.0.0.1:'+server.address().port+'/api/hud/operations';
  const result=await fetch(url,{method:'POST',headers,body:JSON.stringify(body)});
  assert.equal(result.status,200);assert.equal((await result.json()).member_id,'risk/member');
  assert.equal(calls.length,1);assert.equal(calls[0].member_id,'risk/member');
  assert.deepEqual(calls[0].auth_context.principal,principal);
  const refused=await fetch(url,{method:'POST',headers,body:JSON.stringify({...body,client_nonce:'bad/nonce'})});
  assert.equal(refused.status,400);assert.equal(calls.length,1);
 }finally{await new Promise(resolve=>server.close(resolve));}
});
