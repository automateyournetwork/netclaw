import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
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
