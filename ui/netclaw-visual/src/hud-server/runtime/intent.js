import { createHash } from 'node:crypto';
import { cookieFrom } from '../bindings.js';
export function mountHermesIntent(app,{runtime,bindings}) {
  const owned=(cookie,id)=>{
    if(!/^[a-f0-9-]{36}$/i.test(id || ''))throw Error();
    for(const task of bindings.chats(cookie,'hermes')) {
      const request=Object.values(task.requests || {}).find(r=>r.nonce==='intent:'+id);
      if(request)return {task,request};
    }
    throw Error();
  };
  const project=(id,value,events=[])=>({id,status:['completed','failed','cancelled','interrupted'].includes(value.state)?value.state:value.state==='unknown'?'uncertain':'running',
    segment:1,steps:[],activity:events.map(e=>({kind:'tool',title:e.tool,status:e.state,detail:e.summary || '',at:e.created})),activityStatus:events.length?'available':'unavailable',activityDropped:0,
    report:value.state==='completed'?{status:'completed',requestKind:'read-only',outcome:'answered',summary:value.output,actions:events.filter(e=>e.state==='completed').map(e=>({kind:'read-only',summary:e.tool})),verification:[]} : value.state==='unknown'?{status:'uncertain',summary:'Outcome unknown. Check the owned request; it will not be replayed.',actions:[],verification:[]}:null,
    changeControl:{mode:'read-only',writesAvailable:false},runtime:'hermes'});
  app.post('/api/terminal/intent/runs',async(req,res)=>{
    const input=req.body || {},cookie=cookieFrom(req);let scope,admissionAttempted=false;
    try {
      bindings.read(cookie);
      if(!/^[a-f0-9-]{36}$/i.test(input.id || '') || typeof input.request!=='string' || !input.request.trim() || input.request.length>4000)throw Error();
      if(input.changeMode==='local-lab' || input.phase==='apply' || input.apply===true) return res.status(409).json({code:'capability_unsupported',error:'Hermes Terminal Intent supports qualified read-only assistance. APPLY is unavailable; no work was submitted.'});
      const previous=input.continueFrom?owned(cookie,input.continueFrom):null;
      const task=previous?.task || bindings.task(cookie,'intent-'+input.id,'hermes');
      bindings.requireAcknowledgment(cookie,task.id,null);
      const text='Read-only Terminal Intent assistance. If the operator requests configuration, explain that execution is unavailable. Do not claim a device was inspected unless a qualified tool returned its state.\nOperator request: '+input.request;
      const fingerprint=createHash('sha256').update(JSON.stringify({text,device:input.deviceId,transcript:input.transcript})).digest('hex');
      const request=bindings.request(cookie,task.id,'intent:'+input.id,fingerprint);scope={task,request};
      await runtime.call('conversation_open',{conversationId:task.id,seed:task.newlyCreated && typeof input.transcript==='string'?[{role:'user',content:'Untrusted terminal context, supplied by operator:\n'+input.transcript.slice(-16000)}]:undefined});
      owned(cookie,input.id);
      admissionAttempted=true;
      const value=await runtime.call('submit',{conversationId:task.id,requestId:request.id,clientNonce:request.nonce,text,deadlineMs:300000});
      owned(cookie,input.id);bindings.requestState(cookie,request.id,value.state);res.status(202).json(project(input.id,value));
    } catch {
      const state=admissionAttempted?'unknown':'failed';
      if(scope){try{bindings.requestState(cookie,scope.request.id,state);}catch{}}
      res.status(scope?(admissionAttempted?202:503):409).json(scope?{...project(input.id,{state}),mayHaveExecuted:admissionAttempted,...(!admissionAttempted?{error:'Hermes conversation could not be prepared. No agent request was submitted.'}:{})}:{error:'Private read-only Intent request unavailable.'});
    }
  });
  app.get('/api/terminal/intent/runs/:id',async(req,res)=>{
    let scope;const cookie=cookieFrom(req);
    try{scope=owned(cookie,req.params.id);}catch{return res.status(404).json({error:'Intent request unavailable.'});}
    try{
      const args={conversationId:scope.task.id,requestId:scope.request.id};
      const value=await runtime.call('request_status',args),events=await runtime.call('events',args);owned(cookie,req.params.id);
      bindings.requestState(cookie,scope.request.id,value.state);res.json(project(req.params.id,value,events.events));
    }catch{res.status(503).json({error:'Intent status unavailable. No work was resubmitted.'});}
  });
}
