import { createHash, randomUUID } from 'node:crypto';
import { cookieFrom, safeId } from '../bindings.js';
const terminal = new Set(['completed','failed','cancelled','interrupted','unknown']);
const hash = value => createHash('sha256').update(JSON.stringify(value)).digest('hex');
export function mountHermesChat(app, { runtime, bindings }) {
  const own = (req, id = req.params.id) => bindings.ownedRequest(cookieFrom(req), id);
  const failure = res => res.status(503).json({ error: 'Hermes is unavailable. Check Runtime status. An admitted request may still be running; check its status before sending more work.', code: 'runtime_unavailable' });
  const projection = value => ({ ...value, response: value.output || '', fromGateway: value.state === 'completed', runtimeKind: 'hermes', assessmentRefs: [], assessmentBinding: 'unbound' });
  app.get('/api/chat/requests', (req,res) => {
    try {
      const task=bindings.lookupTask(cookieFrom(req),req.query.hudThread,'hermes');
      const record=Object.values(task?.requests || {}).find(r => r.nonce === req.query.nonce);
      if(!record) throw Error();
      res.json({requestId:record.id});
    } catch { res.status(404).json({error:'Request unavailable.'}); }
  });
  app.post('/api/chat/conversations', async (req,res) => {
    try {
      const cookie=cookieFrom(req), acknowledgment=req.body?.acknowledgedUncertainRequestId;
      bindings.read(cookie);
      if (acknowledgment) bindings.ownedRequest(cookie,acknowledgment);
      const thread='chat-'+randomUUID(), task=bindings.task(cookie,thread,'hermes');
      bindings.requireAcknowledgment(cookie,task.id,acknowledgment);
      await runtime.call('conversation_open',{conversationId:task.id,...(acknowledgment ? {acknowledgedUncertainRequestId:acknowledgment} : {})});
      bindings.ownedChat(cookie,task.id,'hermes');
      bindings.acknowledge(cookie,acknowledgment);
      res.status(201).json({id:task.id,thread});
    } catch { res.status(409).json({error:'Conversation cannot be opened. Check the owned request status.'}); }
  });
  app.get('/api/chat/models', async (_req,res) => {
    try { const status = await runtime.call('status'); res.json({ models: [{ id: '', label: status.model || 'Hermes configured model' }], defaultModel: '', supportsEffort: false, selectionSupported: false }); } catch { failure(res); }
  });
  app.post('/api/chat/usage', (req,res) => { try { bindings.read(cookieFrom(req)); res.json({ available: false, reason: 'Hermes usage is reported per completed request.' }); } catch { res.status(401).json({ error: 'Private chat session unavailable.' }); } });
  app.get('/api/chat/conversations', (req,res) => {
    try { res.json({ conversations: bindings.chats(cookieFrom(req),'hermes').map(t => ({ id:t.id, thread:t.publicThread, title:t.title || 'Chat', updatedAt:t.updatedAt || t.createdAt })), sourceAvailable:true }); }
    catch { res.status(401).json({ error:'Private chat session unavailable.' }); }
  });
  app.post('/api/chat/conversations/:id/open', async (req,res) => {
    try {
      const cookie=cookieFrom(req), task=bindings.ownedChat(cookie,req.params.id,'hermes');
      const history=await runtime.call('history',{ conversationId:task.id });
      bindings.ownedChat(cookie,task.id,'hermes');
      res.json({ id:task.id,thread:bindings.resumeChat(cookie,task.id,'hermes').publicThread,messages:history.messages,chatModel:'',chatEffort:'',truncated:history.hasMore });
    } catch { res.status(404).json({ error:'Owned Hermes transcript unavailable.' }); }
  });
  const submit = async (req,res) => {
    let task, request, cookie, text, seed, admissionAttempted=false, release = () => {};
    try {
      cookie=cookieFrom(req); bindings.read(cookie);
      if (!safeId(req.body?.hudThread)) throw Error();
      if (req.body.chatModel || req.body.chatEffort || req.body.attachments?.length) return res.status(400).json({ error:'Hermes does not support model locks, effort overrides or attachments in this HUD release.',code:'capability_unsupported' });
      const context=req.body.context || req.body.messages || [];
      if (!Array.isArray(context) || context.length>200 || context.some(m => !['user','assistant'].includes(m?.role) || typeof m.content !== 'string') || JSON.stringify(context).length>1048576) throw Error();
      text=req.body.message || [...context].reverse().find(m => m.role==='user')?.content;
      if (typeof text !== 'string' || !text.trim() || text.length>65536) throw Error();
      task=bindings.task(cookie,req.body.hudThread,'hermes');
      // Fork seed is immutable and used only for the new conversation's first turn.
      seed=context.map(({role,content})=>({role,content}));
      if (seed.at(-1)?.role==='user') seed.pop();
      release=bindings.begin(cookie,task.id);
      const acknowledgment=req.body.acknowledgedUncertainRequestId;
      if (acknowledgment) bindings.ownedRequest(cookie,acknowledgment);
      bindings.requireAcknowledgment(cookie,task.id,acknowledgment);
      request=bindings.request(cookie,task.id,req.body.clientNonce || randomUUID(),hash({text,seed}));
      bindings.describeChat(cookie,task.id,'hermes',{title:text});
    } catch { release(); return res.status(409).json({ error:'Private conversation unavailable, invalid or busy.' }); }
    try {
      await runtime.call('conversation_open',{ conversationId:task.id, ...(task.newlyCreated ? {seed} : {}), ...(req.body.acknowledgedUncertainRequestId ? {acknowledgedUncertainRequestId:req.body.acknowledgedUncertainRequestId} : {}) });
      bindings.ownedRequest(cookie,request.id);
      admissionAttempted=true;
      let value=await runtime.call('submit',{ conversationId:task.id,requestId:request.id,clientNonce:request.nonce,text });
      bindings.ownedRequest(cookie,request.id);
      bindings.acknowledge(cookie,req.body.acknowledgedUncertainRequestId);
      bindings.requestState(cookie,request.id,value.state);
      // The legacy route waits for a bounded confirmed reply. On timeout it
      // returns the admitted request for observation, never a synthetic answer.
      if(req.path==='/api/chat') {
        const until=Date.now()+30000;
        while(!terminal.has(value.state) && Date.now()<until) {
          await new Promise(resolve=>setTimeout(resolve,500));
          value=await runtime.call('request_status',{conversationId:task.id,requestId:request.id});
          bindings.ownedRequest(cookie,request.id);
        }
        bindings.requestState(cookie,request.id,value.state);
      }
      res.status(value.state==='completed'?200:202).json(projection(value));
    } catch(error) {
      if(!admissionAttempted) {try{bindings.requestState(cookie,request.id,'failed');}catch{}return res.status(503).json({requestId:request.id,state:'failed',mayHaveExecuted:false,fromGateway:false,code:error.code || 'runtime_unavailable',error:'Hermes conversation could not be prepared. No agent request was submitted. Check Runtime status.'});}
      try {bindings.requestState(cookie,request.id,'unknown');}catch{} res.status(202).json({ requestId:request.id,state:'unknown',code:'outcome_unknown',fromGateway:false,mayHaveExecuted:true,error:'Submission outcome is unknown. Check this request; do not resend it.' }); }
    finally { release(); }
  };
  app.post('/api/chat',submit);
  app.post('/api/chat/requests',submit);
  for (const [method,suffix,operation] of [['get','','request_status'],['get','/events','events'],['post','/stop','stop'],['post','/approval','approval']]) {
    app[method]('/api/chat/requests/:id'+suffix,async(req,res)=>{
      let scope;
      try { scope=own(req); } catch { return res.status(404).json({error:'Request unavailable.'}); }
      try {
        const args={conversationId:scope.task.id,requestId:scope.request.id};
        if(operation==='events') args.cursor=Number(req.query.cursor || 0);
        if(operation==='approval') Object.assign(args,{approvalId:req.body?.approvalId,choice:req.body?.choice});
        const value=await runtime.call(operation,args); own(req);
        if(value.state)bindings.requestState(cookieFrom(req),scope.request.id,value.state);
        res.set('Cache-Control','no-store').json(operation==='events' ? value : projection(value));
      } catch { failure(res); }
    });
  }
  app.get('/api/chat/history',(_req,res)=>res.status(400).json({error:'Open an owned conversation to read its history.'}));
}
