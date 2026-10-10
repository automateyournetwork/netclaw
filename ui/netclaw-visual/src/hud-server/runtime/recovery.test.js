import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import express from 'express';
import { Bindings } from '../bindings.js';
import { mountHermesChat } from './routes.js';
import { mountHermesIntent } from './intent.js';
test('v2 binding rejects another installation and migrates legacy OpenClaw only', t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'bindings-148-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const legacy=new Bindings(dir),cookie=legacy.create();legacy.task(cookie,'old');
 const hermes=new Bindings(dir,Date.now,{kind:'hermes',installationId:'B'});assert.throws(()=>hermes.read(cookie));
 const current=new Bindings(dir,Date.now,{kind:'openclaw',installationId:'A'});assert.equal(current.read(cookie).version,2);assert.ok(fs.existsSync(current.file(cookie)+'.v1-backup'));
 assert.throws(()=>new Bindings(dir,Date.now,{kind:'openclaw',installationId:'C'}).read(cookie));
 // Explicit rollback restores the untouched legacy binding, then migration is repeatable.
 const backup=fs.readFileSync(current.file(cookie)+'.v1-backup');
 fs.writeFileSync(current.file(cookie),backup);
 assert.equal(new Bindings(dir).read(cookie).version,1);
 assert.equal(current.read(cookie).version,2);
 assert.deepEqual(fs.readFileSync(current.file(cookie)+'.v1-backup'),backup);
});

test('Intent preparation failure is known nonexecution, admission failure remains uncertain',async t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'intent-148-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const bindings=new Bindings(dir,Date.now,{kind:'hermes',installationId:'A'}),cookie=bindings.create();
 let failAt='conversation_open';const calls=[];
 const runtime={call:async name=>{calls.push(name);if(name===failAt)throw Error('controlled failure');return {};}};
 const app=express();app.use(express.json());mountHermesIntent(app,{runtime,bindings});
 const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));t.after(()=>server.close());
 const send=id=>fetch(`http://127.0.0.1:${server.address().port}/api/terminal/intent/runs`,{method:'POST',headers:{Cookie:'nc_hud='+cookie,'Content-Type':'application/json'},body:JSON.stringify({id,request:'Read-only acceptance'})});
 const failed=await send('11111111-1111-4111-8111-111111111111');
 assert.equal(failed.status,503);assert.equal((await failed.json()).mayHaveExecuted,false);assert.deepEqual(calls,['conversation_open']);
 failAt='submit';const unknown=await send('22222222-2222-4222-8222-222222222222');
 assert.equal(unknown.status,202);assert.equal((await unknown.json()).mayHaveExecuted,true);
 assert.deepEqual(calls,['conversation_open','conversation_open','submit']);
});
test('owned request routes reject foreign owners before upstream and recheck after I/O',async t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'routes-148-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));
 const bindings=new Bindings(dir,Date.now,{kind:'hermes',installationId:'A'}),cookie=bindings.create(),foreign=bindings.create();
 const task=bindings.task(cookie,'t','hermes'),request=bindings.request(cookie,task.id,'n','hash');
 let calls=0,revoke=false;
 const runtime={call:async()=>{calls++;if(revoke)bindings.revoke(cookie);return {state:'completed',output:'PRIVATE'};}};
 const app=express();app.use(express.json());mountHermesChat(app,{runtime,bindings});const server=app.listen(0,'127.0.0.1');await new Promise(r=>server.once('listening',r));t.after(()=>server.close());
 const url=`http://127.0.0.1:${server.address().port}/api/chat/requests/${request.id}`;
 assert.equal((await fetch(url,{headers:{Cookie:'nc_hud='+foreign}})).status,404);assert.equal(calls,0);
 revoke=true;const response=await fetch(url,{headers:{Cookie:'nc_hud='+cookie}});assert.equal(response.status,503);assert.ok(!(await response.text()).includes('PRIVATE'));
});
