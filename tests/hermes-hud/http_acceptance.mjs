import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHermesRuntime } from '../../ui/netclaw-visual/src/hud-server/runtime/hermes.js';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const listener=net.createServer();await new Promise(r=>listener.listen(0,'127.0.0.1',r));const port=listener.address().port;await new Promise(r=>listener.close(r));
const server=spawn(process.execPath,['server.js'],{cwd:path.join(root,'ui/netclaw-visual'),env:{...process.env,NETCLAW_RUNTIME:'hermes',HUD_PORT:String(port),HUD_UI_PORT:String(port+1)},stdio:['ignore','pipe','pipe']});
let log='';server.stderr.on('data',b=>{log+=b.toString();});
const origin=`http://127.0.0.1:${port}`;
let cookie;
const call=(url,method='GET',body,owner=cookie)=>fetch(origin+url,{method,headers:{'Content-Type':'application/json',...(owner?{Cookie:owner}:{})},...(body?{body:JSON.stringify(body)}:{})});
try {
  const direct=createHermesRuntime({home:process.env.HERMES_HOME,installationId:'11111111-1111-4111-8111-111111111111'},root);
  try { await assert.rejects(direct.call('status',{unexpected:'refuse'})); await direct.call('conversation_open',{conversationId:'mcp-probe'}); }
  catch(error) { console.error('Synthetic MCP probe',error.message,error.cause);throw error; }
  finally {await direct.close();}
  let ready=false;
  for(let n=0;n<100;n++){try{if((await call('/api/health')).ok){ready=true;break;}}catch{}await new Promise(r=>setTimeout(r,100));}
  assert.ok(ready,log);
  const metadata=await (await call('/api/runtime')).json();assert.equal(metadata.kind,'hermes');assert.equal(metadata.readiness.ready,true,JSON.stringify(metadata));
  const auth=await call('/api/hud/session','POST',{});cookie=auth.headers.get('set-cookie').split(';')[0];
  const foreign=(await call('/api/hud/session','POST',{},'')).headers.get('set-cookie').split(';')[0];
  assert.equal((await call('/api/pal/local/status')).status,200);
  assert.equal((await call('/api/n2n')).status,409);
  assert.equal((await call('/api/budget/config','PUT',{budget:1})).status,409);
  assert.equal((await call('/api/sessions')).status,404);
  const switched=await fetch(origin+'/api/chat/requests',{method:'POST',headers:{'Content-Type':'application/json','X-NetClaw-Installation':'wrong',Cookie:cookie},body:JSON.stringify({hudThread:'wrong',message:'never'})});assert.equal(switched.status,409);
  assert.equal((await call('/api/chat/requests','POST',{hudThread:'rejected',message:'text',chatModel:'unqualified'})).status,400);
  const admitted=await call('/api/chat/requests','POST',{hudThread:'node-owner',clientNonce:'node-nonce',message:'SUBNET'});
  assert.equal(admitted.status,202);const first=await admitted.json();assert.ok(first.requestId);
  assert.equal((await call('/api/chat/requests/'+first.requestId,'GET',null,foreign)).status,404);
  let result;
  for(let n=0;n<150;n++){result=await(await call('/api/chat/requests/'+first.requestId)).json();if(['completed','failed','unknown'].includes(result.state))break;await new Promise(r=>setTimeout(r,100));}
  assert.equal(result.state,'completed',JSON.stringify(result));assert.ok(result.fromGateway);assert.match(result.response,/CANARY/);
  const events=await(await call('/api/chat/requests/'+first.requestId+'/events')).json();assert.ok(events.events.some(e=>e.state==='completed' && e.tool.includes('subnet_calculator')));
  const duplicate=await(await call('/api/chat/requests','POST',{hudThread:'node-owner',clientNonce:'node-nonce',message:'SUBNET'})).json();assert.equal(duplicate.requestId,first.requestId);
  const chats=await(await call('/api/chat/conversations')).json();assert.equal(chats.conversations.length,1);
  const conversation=chats.conversations[0].id;
  assert.equal((await call('/api/chat/conversations/'+conversation+'/open','POST',{},foreign)).status,404);
  const history=await(await call('/api/chat/conversations/'+conversation+'/open','POST',{})).json();assert.equal(history.messages.length,2);
  await call('/api/hud/session/revoke','POST',{});assert.equal((await call('/api/chat/requests/'+first.requestId)).status,404);
  console.log('PASS actual HTTP → MCP → protected Hermes → real subnet MCP; owner/revocation/nonce/capability checks');
} finally {
  if (server.exitCode === null && server.signalCode === null) {
    const exited = new Promise(r => server.once('exit', r));
    server.kill('SIGTERM'); await exited;
  }
}
