import { randomUUID } from 'node:crypto';
import { authorize } from './policy.js';
import { invariant, safeError } from './errors.js';
import { ArtifactStore } from './evidence.js';

const finished=new Set(['succeeded','failed','cancelled','denied','expired']);
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));

/** Owned admissions are independent of an editor, MCP connection, or webview. */
export class Conversations {
  constructor({binding,journal,audit,runtime,start,clean}) {
    Object.assign(this,{binding,journal,audit,runtime,start,clean});this.artifacts=new ArtifactStore(journal);
  }
  authority(principal) {
    this.binding.assertCurrent();authorize(principal,'delegate',[this.binding.installationId]);
    // An ordinary operator runtime is not an attenuated assistant runtime.
    invariant(principal.surface==='operator','UNQUALIFIED');
  }
  async open(principal,input) {
    this.authority(principal);invariant(!input.model&&!input.effort,'UNQUALIFIED');
    if(input.conversationId)this.journal.record('conversation',input.conversationId,principal);
    const op=this.journal.admit(principal,input.nonce,'conversation-open',input);
    if(op.result)return op.result;
    const conversationId=input.conversationId||randomUUID();
    if(!input.conversationId)this.journal.put('conversation',conversationId,principal,{runtime:this.binding.kind,createdAt:new Date().toISOString(),view:input.view});
    this.journal.transition(op.operationId,'running');this.journal.transition(op.operationId,'succeeded',{conversationId});
    return {conversationId};
  }
  async submit(principal,input) {
    this.authority(principal);const conversation=this.journal.record('conversation',input.conversationId,principal);
    invariant(conversation.runtime===this.binding.kind,'IDENTITY_CHANGED');
    const admittedInput={...input,contextIds:input.contextIds||[]};
    // Look up a retained nonce before runtime readiness, busy or expiry checks.
    if(this.journal.byNonce(principal,input.nonce))return this.journal.admit(principal,input.nonce,'conversation-request',admittedInput);
    invariant(typeof input.prompt==='string'&&input.prompt.trim()&&Buffer.byteLength(input.prompt)<=65536);
    let contextBytes=0;
    for(const id of admittedInput.contextIds){
      const context=this.journal.record('context',id,principal);invariant(context.reviewed===true,'DENIED');
      contextBytes+=context.size;invariant(contextBytes<=20*1024*1024);
      this.artifacts.read(principal,context.artifactId);
    }
    const readiness=await this.runtime.readiness();invariant(readiness.ready===true,'UNQUALIFIED');
    const lock=this.journal.lock(`conversation:${input.conversationId}`,principal.principalId);
    let operation;
    try {
      const active=this.journal.conversationOperations(principal,input.conversationId).find(row=>!finished.has(row.state));
      invariant(!active,active?.state==='unknown'?'UNKNOWN_OUTCOME':'BUSY');
      operation=this.journal.admit(principal,input.nonce,'conversation-request',admittedInput);
      await this.audit.record({operationId:operation.operationId,state:'request-admitted'});
      this.authority(principal);
      await this.start(operation.operationId);
      return this.journal.get(principal,operation.operationId);
    } catch(error) {
      if(operation&&this.journal.get(principal,operation.operationId).state==='admitted')this.journal.transition(operation.operationId,'failed',safeError(error));
      throw error;
    } finally {this.journal.unlock(`conversation:${input.conversationId}`,lock);}
  }
  context(principal,input) {
    const parts=[input.prompt];
    for(const id of input.contextIds){
      const context=this.journal.record('context',id,principal);invariant(context.reviewed===true&&context.mediaType==='text/plain','UNQUALIFIED');
      const bytes=this.artifacts.read(principal,context.artifactId);
      parts.push(`\nExplicitly selected context (${context.name}):\n${bytes.toString('utf8')}`);
    }
    const text=parts.join('\n');invariant(Buffer.byteLength(text)<=1024*1024,'UNSUPPORTED');return text;
  }
  async run(operationId) {
    const principal=this.binding.principal;this.authority(principal);
    const row=this.journal._row(operationId);invariant(row.kind==='conversation-request');
    this.journal._owned(principal,row);
    const lease=this.journal.claim(operationId,{pid:process.pid,start:new Date().toISOString()});
    if(!lease)return this.journal.get(principal,operationId);
    let dispatched=false,heartbeatError=false;
    const timer=setInterval(()=>{try{this.journal.renew(operationId,lease);}catch{heartbeatError=true;}},5000);timer.unref();
    try {
      const input=this.journal.input(operationId,lease),text=this.context(principal,input);
      this.journal.record('conversation',input.conversationId,principal);
      await this.audit.record({operationId,state:'before-dispatch'});this.authority(principal);
      await this.runtime.open({conversationId:input.conversationId});
      this.authority(principal);invariant(!heartbeatError,'UNKNOWN_OUTCOME');
      if(this.journal.get(principal,operationId).state==='cancellation-requested'){
        await this.audit.record({operationId,state:'cancelled-before-dispatch'});
        return this.journal.finish(operationId,lease,'cancelled',{source:'Cancellation observed before inference dispatch'});
      }
      // The stable request ID is also the runtime's idempotency/correlation key.
      this.journal.attachReference(operationId,lease,operationId);
      this.journal.event(operationId,'dispatch-intent',{runtime:this.binding.kind});dispatched=true;
      await this.runtime.submit({conversationId:input.conversationId,requestId:operationId,nonce:row.nonce,text});
      const deadline=Date.now()+900000;
      while(Date.now()<deadline){
        this.authority(principal);invariant(!heartbeatError,'UNKNOWN_OUTCOME');
        const observed=await this.runtime.observe({conversationId:input.conversationId,requestId:operationId});
        this.authority(principal);
        const result=this.clean({runtime:this.binding.kind,source:observed.source||'Owned runtime request',...observed});
        if(finished.has(observed.state)){
          this.journal.event(operationId,'runtime-observation',{state:observed.state,source:result.source});
          await this.audit.record({operationId,state:observed.state});
          return this.journal.finish(operationId,lease,observed.state,result);
        }
        if(observed.state==='unknown')break;
        await pause(500);
      }
      return this.journal.finish(operationId,lease,'unknown',{code:'UNKNOWN_OUTCOME',runtime:this.binding.kind});
    } catch(error) {
      return this.journal.finish(operationId,lease,dispatched?'unknown':'failed',dispatched?{code:'UNKNOWN_OUTCOME'}:safeError(error));
    } finally {clearInterval(timer);await this.runtime.close();}
  }
  async reconcile(principal,operationId) {
    this.authority(principal);const operation=this.journal.get(principal,operationId);
    if(operation.kind!=='conversation-request'||operation.state!=='unknown'||!operation.externalReference)return operation;
    const input=JSON.parse(this.journal._row(operationId).input);
    const result=await this.runtime.observe({conversationId:input.conversationId,requestId:operationId});
    this.authority(principal);
    if(!finished.has(result.state))return operation;
    await this.audit.record({operationId,state:'reconciled'});
    return this.journal.reconcile(operationId,operation.externalReference,result.state,this.clean(result));
  }
  async cancel(principal,input) {
    this.authority(principal);authorize(principal,'cancel',[this.binding.installationId]);
    const operation=this.journal.get(principal,input.operationId);invariant(operation.kind==='conversation-request','DENIED');
    const cancel=this.journal.admit(principal,input.nonce,'conversation-cancel',input);
    if(cancel.result)return cancel.result;
    await this.audit.record({operationId:input.operationId,state:'cancellation-requested'});
    this.journal.transition(cancel.operationId,'running');
    try {
      const current=this.journal.get(principal,input.operationId);
      if(current.state==='admitted')this.journal.transition(input.operationId,'cancelled',{source:'Not dispatched'});
      else if(current.state==='running'||current.state==='cancellation-requested'){
        if(current.state==='running')this.journal.transition(input.operationId,'cancellation-requested');
        const request=JSON.parse(this.journal._row(input.operationId).input);
        await this.runtime.cancel({conversationId:request.conversationId,requestId:input.operationId});
      }
      const result=this.journal.get(principal,input.operationId);
      this.journal.transition(cancel.operationId,'succeeded',result);return result;
    } catch(error){this.journal.transition(cancel.operationId,'failed',safeError(error));throw error;}
  }
}
