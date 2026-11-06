import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import express from 'express';
import { readRemoteHudConfig, remoteHudFeatures, remoteHudRoute, remoteHudTimeout, createRemoteHud, remoteHudBackendBoundary, projectRemoteHud, REMOTE_HUD_FEATURES } from './remote-hud.js';
import { gatewayCallTimeout } from './chat-runtime.js';
const installation = {kind:'openclaw',installationId:'b164621c-a94e-4c28-a087-d9c9dabcce21'};
test('saved-history proxy outlasts both bounded native reads without extending unrelated routes', () => {
  const env = { NETCLAW_GATEWAY_HISTORY_TIMEOUT_MS: '60000', NETCLAW_GATEWAY_CATALOG_TIMEOUT_MS: '60000' };
  assert.ok(remoteHudTimeout('/api/chat/conversations/owned/open') > gatewayCallTimeout('chat.history', env) + gatewayCallTimeout('models.list', env));
  assert.equal(remoteHudTimeout('/api/chat/conversations'), 90000);
  assert.equal(remoteHudTimeout('/api/chat/conversations/owned/open?url=other'), 90000);
  assert.equal(remoteHudTimeout('/api/chat'), 590000);
  assert.equal(remoteHudTimeout('/api/n2n/chat'), 320000);
});
const listen = server => new Promise(resolve => server.listen(0,'127.0.0.1',()=>resolve(`http://127.0.0.1:${server.address().port}`)));
const close = server => { server.closeAllConnections(); return new Promise(resolve=>server.close(resolve)); };
function fixture(t) {
 const root=fs.mkdtempSync(path.join(fs.realpathSync(os.tmpdir()),'remote-hud-')); t.after(()=>fs.rmSync(root,{recursive:true,force:true}));
 const home=path.join(root,'control'),conversationHome=path.join(root,'conversation');
 fs.mkdirSync(path.join(home,'netclaw-federation'),{recursive:true,mode:0o700});fs.mkdirSync(conversationHome,{mode:0o700});
 const write=(file,value)=>fs.writeFileSync(file,JSON.stringify(value),{mode:0o600});
 write(path.join(home,'netclaw-federation/protected-profile.json'),{role:'border',identity:{installation_id:installation.installationId},access:{mode:'open-lab'}});
 const conversationConfig=path.join(conversationHome,'openclaw.json');write(conversationConfig,{gateway:{port:18000}});
 const config={schemaVersion:1,installationId:installation.installationId,upstream:'http://127.0.0.1:13005',conversationHome,conversationConfig,features:[...REMOTE_HUD_FEATURES]};
 const file=path.join(root,'workspace.json');write(file,config);
 return {config,file,write,installation:{...installation,home}};
}
test('explicit private workspace binds current installation and separate conversation state without modifying control profile', t=>{
 const f=fixture(t), before=fs.readFileSync(path.join(f.installation.home,'netclaw-federation/protected-profile.json'));
 const sha=crypto.createHash('sha256').update(fs.readFileSync(f.file)).digest('hex');
 assert.equal(readRemoteHudConfig(f.file,f.installation,sha).upstream,f.config.upstream);
 assert.deepEqual(fs.readFileSync(path.join(f.installation.home,'netclaw-federation/protected-profile.json')),before);
 assert.throws(()=>readRemoteHudConfig(f.file,f.installation,'0'.repeat(64)),/changed/);
 for(const patch of [{installationId:crypto.randomUUID()},{upstream:'https://example.com'},{upstream:'http://localhost:13005'},{upstream:'http://127.0.0.1:13005/path'},{upstream:'http://127.0.0.1:99999'},{conversationHome:f.installation.home},{features:['canvas']}]) {f.write(f.file,{...f.config,...patch});assert.throws(()=>readRemoteHudConfig(f.file,f.installation));}
 f.write(f.file,f.config);f.write(path.join(f.installation.home,'netclaw-federation/protected-profile.json'),{role:'border',identity:{installation_id:installation.installationId}});assert.throws(()=>readRemoteHudConfig(f.file,f.installation),/open_lab/);
});
test('feature declarations are finite and Canvas requires actual Chat',()=>{
 for(const features of [[],['chat','chat'],['admin'],['canvas'],null])assert.throws(()=>remoteHudFeatures(features));
 assert.deepEqual(remoteHudFeatures(['chat','canvas']),['chat','canvas']);
});
test('fixed normal route map includes real work panels and refuses native control, auth, peer execution and path tricks',()=>{
 const all=REMOTE_HUD_FEATURES;
 for(const p of ['/api/graph','/api/n2n','/api/bgp','/api/chat/models','/api/chat/conversations','/api/rag/documents','/api/rag/stats','/api/hud/runtime','/api/hud/tokenomics','/api/hud/documentation','/api/hud/documentation/doc:1','/api/hud/documentation/doc%3A1','/api/hud/reference','/api/hud/logs/gateway?q=warning&severity=warning'])assert.equal(remoteHudRoute('GET',p,all),true,p);
 for(const p of ['/api/chat','/api/chat/conversations/abc/open','/api/rag/search','/api/rag/upload'])assert.equal(remoteHudRoute('POST',p,all),true,p);
 for(const [m,p] of [['POST','/api/hud/session'],['POST','/api/n2n/chat'],['POST','/api/mcp/configuration'],['POST','/api/env/anthropic'],['POST','/api/terminal/terra'],['GET','/api/hud/management'],['GET','/api/env/anthropic'],['GET','/api/hud/logs/../../etc'],['GET','/api/hud/logs/%2Fetc'],['GET','/api/hud/logs/a%253Ab'],['GET','/api/hud/logs/gateway?q=a&q=b'],['GET','/api/hud/logs/gateway?file=/etc/passwd'],['GET','/api/chat/models?url=x'],['DELETE','/api/chat'],['HEAD','/api/graph']])assert.equal(remoteHudRoute(m,p,all),false,m+p);
 assert.equal(remoteHudRoute('POST','/api/chat',['overview']),false);
});
async function proxyFixture(t,{wrongIdentity=false,redirect=false}={}) {
 const requests=[];
 const upstream=http.createServer(async(req,res)=>{
  let raw='';for await(const chunk of req)raw+=chunk;requests.push({method:req.method,url:req.url,headers:req.headers,raw});
  res.setHeader('Content-Type','application/json');
  if(req.url==='/api/runtime')return res.end(JSON.stringify({kind:'openclaw',installationId:wrongIdentity?'other':installation.installationId,remoteHudBackend:{schema:1,features:['chat','rag','runtime']}}));
  if(redirect){res.writeHead(307,{Location:'https://example.com'});return res.end('{}');}
  res.setHeader('Set-Cookie','unexpected=never-forward');res.end(JSON.stringify({fromGateway:true,response:'actual fixture handler',body:raw}));
 });
 const origin=await listen(upstream),remote=createRemoteHud({upstream:origin,features:['chat','rag','runtime']},installation);
 const app=express();app.use(async(req,res)=>{if(!await remote.handle(req,res))res.status(404).json({code:'route_unavailable'});});
 const server=http.createServer(app),url=await listen(server);t.after(async()=>{await close(server);await close(upstream);});
 return {url,requests,remote};
}
test('normal proxy verifies backend identity and sends exact body without cookie/auth/forwarded headers or retries',async t=>{
 const f=await proxyFixture(t);
 const response=await fetch(f.url+'/api/chat',{method:'POST',headers:{'content-type':'application/json','x-netclaw-installation':installation.installationId,cookie:'old=credential',authorization:'Bearer private','x-forwarded-host':'evil'},body:'{"hudThread":"public-thread","message":"hello"}'});
 assert.equal(response.status,200);assert.equal((await response.json()).fromGateway,true);assert.equal(response.headers.get('set-cookie'),null);
 assert.equal(f.requests.length,2);const call=f.requests[1];assert.equal(call.raw,'{"hudThread":"public-thread","message":"hello"}');assert.equal(call.headers['x-netclaw-installation'],installation.installationId);
 for(const h of ['cookie','authorization','x-forwarded-host'])assert.equal(call.headers[h],undefined);
});
test('wrong installation or unexpected backend identity refuses before dispatching Chat',async t=>{
 const f=await proxyFixture(t,{wrongIdentity:true});
 assert.equal((await fetch(f.url+'/api/chat',{method:'POST',headers:{'x-netclaw-installation':'other'},body:'x'})).status,409);assert.equal(f.requests.length,0);
 assert.equal((await fetch(f.url+'/api/chat',{method:'POST',headers:{'x-netclaw-installation':installation.installationId},body:'x'})).status,503);assert.equal(f.requests.length,1);
});
test('upstream redirects do not forward the operation elsewhere or retry',async t=>{
 const f=await proxyFixture(t,{redirect:true});assert.equal((await fetch(f.url+'/api/chat',{method:'POST',headers:{'x-netclaw-installation':installation.installationId},body:'x'})).status,503);assert.equal(f.requests.length,2);
});
test('private normal backend independently refuses auth/native control and strips old credentials',()=>{
 const boundary=remoteHudBackendBoundary({features:['chat']},installation);let status,called=0;
 const res={status(n){status=n;return this;},json(){}};
 boundary({url:'/api/hud/session',method:'POST',headers:{}},res,()=>called++);assert.equal(status,404);assert.equal(called,0);
 const req={url:'/api/chat',method:'POST',headers:{'x-netclaw-installation':installation.installationId,cookie:'x',authorization:'x'}};boundary(req,res,()=>called++);assert.equal(called,1);assert.equal(req.headers.cookie,undefined);assert.equal(req.headers.authorization,undefined);
});
test('federation projection retains actual current member identity and omits private registry and arbitrary inventory values',()=>{
 const value=projectRemoteHud('/api/n2n',{available:true,identity:'border',endpointRegistry:{private:'path'},risk:{role:'border',enrollment_token:'secret'},members:[{member_id:'member',live:true,secret:'hidden',inventory:{harness:{type:'openclaw'},llm:{primary_model:'sonnet',key:'hidden'},mcp_servers:[{name:'netbox',tools:['get_object'],env:'hidden'}]}}]});
 assert.equal(value.members[0].member_id,'member');assert.equal(value.members[0].inventory.llm.primary_model,'sonnet');assert.equal(JSON.stringify(value).includes('hidden'),false);assert.equal(value.endpointRegistry,undefined);
});
