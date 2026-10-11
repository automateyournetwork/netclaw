import { randomUUID } from 'node:crypto';
import WebSocket from 'ws';
import { readOwned } from './files.js';
import { environment } from './configuration.js';
import { invariant, fail } from './errors.js';
import { createHermesRuntime } from '../hud-server/runtime/hermes.js';
import { gatewayAgentId } from '../hud-server/gateway-agent.js';

/** Fixed loopback gateway transport. Payloads and credentials never enter argv. */
export class ManagementGateway {
  constructor(binding){this.binding=binding;this.pending=new Map();}
  async connect(){
    if(this.socket?.readyState===WebSocket.OPEN&&this.connected)return;
    this.binding.assertCurrent();
    const config=JSON.parse(readOwned(this.binding.configPath)),env=environment(this.binding);
    const port=config.gateway?.port||18789;invariant(Number.isInteger(port)&&port>0&&port<=65535);
    const resolve=value=>typeof value==='string'&&/^\$\{[A-Z_][A-Z0-9_]*\}$/.test(value)?env[value.slice(2,-1)]:undefined;
    const mode=config.gateway?.auth?.mode||'token';
    const credential=mode==='password'?(resolve(config.gateway?.auth?.password)||env.OPENCLAW_GATEWAY_PASSWORD):(resolve(config.gateway?.auth?.token)||env.OPENCLAW_GATEWAY_TOKEN);
    invariant(credential,'UNAUTHENTICATED');
    const ws=new WebSocket(`ws://127.0.0.1:${port}`,{maxPayload:1024*1024,followRedirects:false,handshakeTimeout:10000});this.socket=ws;
    this.connected=false;
    const challenge=new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{ws.terminate();reject(Error('Handshake unavailable'));},10000);
      const first=bytes=>{try{const frame=JSON.parse(bytes.toString());invariant(frame.type==='event'&&frame.event==='connect.challenge','UNAUTHENTICATED');clearTimeout(timer);resolve();}catch{clearTimeout(timer);reject(Error('Handshake unavailable'));}};
      ws.once('message',first);ws.once('error',()=>{clearTimeout(timer);reject(Error('Gateway unavailable'));});
      ws.once('close',()=>{clearTimeout(timer);reject(Error('Gateway closed'));});
    });
    ws.on('message',bytes=>{
      let frame;try{frame=JSON.parse(bytes.toString());}catch{ws.terminate();return;}
      if(frame.type!=='res')return;
      const pending=this.pending.get(frame.id);if(!pending)return;
      if(pending.final&&frame.ok&&frame.payload?.status==='accepted')return;
      this.pending.delete(frame.id);clearTimeout(pending.timer);
      if(frame.ok)pending.resolve(frame.payload);else pending.reject(Error('Gateway method refused'));
    });
    ws.on('close',()=>{this.connected=false;for(const pending of this.pending.values()){clearTimeout(pending.timer);pending.reject(Error('Gateway connection closed'));}this.pending.clear();});
    ws.on('error',()=>{});
    try {
      await challenge;
      await this.send('connect',{minProtocol:3,maxProtocol:4,client:{id:'gateway-client',version:'150',platform:process.platform,mode:'backend'},role:'operator',scopes:['operator.read','operator.write'],auth:{[mode==='password'?'password':'token']:credential}},10000);
      this.connected=true;
    }catch{ws.terminate();fail('SOURCE_UNAVAILABLE');}
  }
  send(method,params,timeout=15000,final=false){
    invariant(this.socket?.readyState===WebSocket.OPEN,'SOURCE_UNAVAILABLE');
    const id=randomUUID();
    return new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>{this.pending.delete(id);reject(Error('Gateway deadline exceeded'));},timeout);
      this.pending.set(id,{resolve,reject,timer,final});
      this.socket.send(JSON.stringify({type:'req',id,method,params}),error=>{if(error){clearTimeout(timer);this.pending.delete(id);reject(error);}});
    });
  }
  async call(method,params,timeout,final){
    invariant(['health','agent','agent.wait','chat.abort','chat.history','models.list','sessions.patch'].includes(method),'DENIED');
    await this.connect();return this.send(method,params,timeout,final);
  }
  async close(){this.socket?.close();}
}

export function createManagementRuntime(binding,root){
  if(binding.kind==='hermes'){
    const runtime=createHermesRuntime(binding,root,{env:{...process.env,...environment(binding)}});
    const conversationId=id=>`management-${id}`;
    return {kind:'hermes',
      async readiness(){const value=await runtime.call('status');invariant(value.installationId===binding.installationId&&value.protected===true,'IDENTITY_CHANGED');return {ready:value.ready===true,grantEnforced:false,source:'Protected Hermes companion',version:value.release};},
      open:input=>runtime.call('conversation_open',{conversationId:conversationId(input.conversationId)}),
      async submit(input){const value=await runtime.call('submit',{conversationId:conversationId(input.conversationId),requestId:input.requestId,clientNonce:input.nonce,text:input.text,deadlineMs:900000});invariant(value.state!=='unknown','UNKNOWN_OUTCOME');return {reference:input.requestId};},
      async observe(input){const value=await runtime.call('request_status',{conversationId:conversationId(input.conversationId),requestId:input.requestId});return {...value,state:({completed:'succeeded',interrupted:'unknown',waiting_approval:'running',queued:'running',stopping:'cancellation-requested'})[value.state]||value.state,source:'Protected Hermes request ledger'};},
      cancel:input=>runtime.call('stop',{conversationId:conversationId(input.conversationId),requestId:input.requestId}),
      close:()=>runtime.close(),
    };
  }
  const gateway=new ManagementGateway(binding),completed=new Map();
  const config=JSON.parse(readOwned(binding.configPath)),agentId=gatewayAgentId(config);
  const sessionKey=id=>`agent:${agentId}:netclaw-management:${id}`;
  return {kind:'openclaw',
    async readiness(){await gateway.call('health',{});return {ready:true,grantEnforced:false,source:'Authenticated local OpenClaw gateway'};},
    async open(){},
    async submit(input){
      const result=await gateway.call('agent',{message:input.text,agentId,sessionKey:sessionKey(input.conversationId),deliver:false,timeout:900,idempotencyKey:input.requestId},930000,true);
      invariant(result.status==='ok','UNKNOWN_OUTCOME');
      const payload=result.result||result;
      const output=(payload.payloads||[]).filter(p=>typeof p.text==='string').map(p=>p.text).join('\n');
      completed.set(input.requestId,{state:'succeeded',output,usage:payload.meta?.usage||payload.meta?.agentMeta?.usage||null,source:'OpenClaw final agent response'});
      return {reference:input.requestId};
    },
    async observe(input){
      if(completed.has(input.requestId))return completed.get(input.requestId);
      const value=await gateway.call('agent.wait',{runId:input.requestId,timeoutMs:1000});
      if(value.status==='ok')return {state:'succeeded',output:null,outputUnavailable:true,source:'OpenClaw authoritative run status',reason:'Completion confirmed after transport loss; no final response was retained by the management worker.'};
      if(value.status==='error')return {state:'failed',source:'OpenClaw authoritative run status'};
      return {state:'unknown',source:'OpenClaw run status',reason:'No terminal result is available; never resubmit uncertain work.'};
    },
    cancel:input=>gateway.call('chat.abort',{sessionKey:sessionKey(input.conversationId),agentId,runId:input.requestId,preserveSideRuns:true}),
    close:()=>gateway.close(),
  };
}
