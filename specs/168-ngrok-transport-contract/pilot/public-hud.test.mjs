import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import { createViewer } from './public-hud.mjs';
const host='r01-gcp-montreal.lobsternet.automateyournetwork.com';
async function setup(fetcher){
  const dist=await mkdtemp(path.join(os.tmpdir(),'r01-full-hud-'));
  await mkdir(path.join(dist,'assets'));await writeFile(path.join(dist,'assets/app.js'),'/* built */');
  for(const page of ['index','canvas','classic'])await writeFile(path.join(dist,page+'.html'),'<head></head><body>'+page+'</body>');
  await writeFile(path.join(dist,'.env'),'SECRET');
  const server=await createViewer({dist,fetcher});await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const base='http://127.0.0.1:'+server.address().port;
  return {server,request:(route='',options={})=>new Promise((resolve,reject)=>{const req=http.request(base+route,{method:options.method||'GET',headers:{Host:host,...options.headers}},res=>{const chunks=[];res.on('data',c=>chunks.push(c));res.on('end',()=>resolve(new Response(Buffer.concat(chunks),{status:res.statusCode,headers:res.headers})));});req.on('error',reject);req.end(options.body);}),close:async()=>{server.closeAllConnections();await new Promise(r=>server.close(r));await rm(dist,{recursive:true});},base};
}
test('full workspace publishes pages and scoped chat while preserving private APIs and origin checks',async()=>{
  const calls=[];const app=await setup(async(url,options)=>{calls.push({url,options});return Response.json({response:'actual answer'},{headers:{'Set-Cookie':'nc_hud=test; HttpOnly; SameSite=Strict; Path=/'}});});
  try{
    for(const page of ['/','/canvas.html?embedded=1','/classic.html','/assets/app.js'])assert.equal((await app.request(page)).status,200,page);
    assert.match(await(await app.request('/lab-config.js')).text(),/NETCLAW_PUBLIC_LAB=true/);
    assert.doesNotMatch(await(await app.request('/lab-config.js')).text(),/READ_ONLY/);
    const reply=await app.request('/api/chat',{method:'POST',headers:{Origin:'https://'+host,'Content-Type':'application/json',Cookie:'nc_hud=test',Authorization:'Bearer private'},body:JSON.stringify({message:'question',hudThread:'thread'})});
    assert.equal(reply.status,200);assert.match(reply.headers.get('set-cookie'),/Secure/);assert.equal((await reply.json()).response,'actual answer');
    assert.equal(calls[0].options.headers.cookie,'nc_hud=test');assert.equal(calls[0].options.headers.authorization,undefined);assert.equal(calls[0].options.headers.origin,undefined);
    for(const route of ['/api/env/key','/api/testbed/raw','/api/hud/logs/private','/.env','/assets/%2e%2e/.env','/api/n2n?target=/api/env','//api/n2n','/api/%6e2n'])assert.equal((await app.request(route)).status,404,route);
    for(const route of ['/api/env','/api/n2n/chat','/api/terminal/intent','/api/budget/config'])assert.equal((await app.request(route,{method:'POST'})).status,405,route);
    assert.equal((await app.request('/api/chat',{method:'POST',headers:{Origin:'https://untrusted.example'}})).status,403);
    assert.equal((await app.request('/api/runtime',{headers:{Host:'evil.example'}})).status,403);
    assert.equal(calls.length,1,'refused requests never reach the private API');
    await new Promise((resolve,reject)=>{const req=http.request(app.base,{headers:{Host:host,Connection:'Upgrade',Upgrade:'websocket'}});req.on('response',r=>{try{assert.equal(r.statusCode,403);r.resume();resolve();}catch(e){reject(e);}});req.on('upgrade',()=>reject(Error('Unexpected upgrade')));req.on('error',reject);req.end();});
  }finally{await app.close();}
});
test('inventory retains member model, tools and live state without credential fields',async()=>{
  const app=await setup(async()=>Response.json({available:true,generatedAt:'2026-11-01T21:00:00Z',members:[{member_id:'risk/onprem',display_name:'On-prem Mac',live:true,skills:['subnet-calculator'],token:'SECRET',inventory:{received_at:123,llm:{primary_model:'anthropic/claude-sonnet-5-5',apiKey:'SECRET'},mcp_servers:[{name:'subnet-calc-mcp',tools:['subnet_calculator'],env:{KEY:'SECRET'}}]}}],peers:[{identity:'as64519',inventory:{inventory:{mcp_servers:[],llm:{primary_model:'none'}}}}]}));
  try{const data=await(await app.request('/api/n2n')).json();assert.equal(data.members[0].inventory.llm.primary_model,'anthropic/claude-sonnet-5-5');assert.equal(data.members[0].inventory.mcp_servers[0].tools[0],'subnet_calculator');assert.equal(data.members[0].live,true);assert.equal(data.peers[0].inventory.llm.primary_model,'none');assert.doesNotMatch(JSON.stringify(data),/SECRET|apiKey|token|env/);}finally{await app.close();}
});
test('upstream failure never publishes its private diagnostic',async()=>{const app=await setup(async()=>{throw Error('SECRET');});try{const r=await app.request('/api/n2n');assert.equal(r.status,503);assert.doesNotMatch(await r.text(),/SECRET/);}finally{await app.close();}});
