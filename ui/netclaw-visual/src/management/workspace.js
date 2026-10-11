import { randomUUID,createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { ArtifactStore } from './evidence.js';
import { authorize } from './policy.js';
import { invariant,fail,safeError } from './errors.js';
import { unbindImportedSession } from '../canvas-chat/assessment-link.js';
import {ownedDirectory,atomicPrivate} from './files.js';
import {RagToolError} from './rag.js';

const formats=new Set(['.pdf','.md','.markdown','.html','.htm','.txt','.docx','.xlsx','.pptx','.vsdx','.doc','.xls','.ppt','.vsd']);
const digest=value=>createHash('sha256').update(value).digest('hex');

export function importedCanvas(text){
  invariant(typeof text==='string'&&Buffer.byteLength(text)<=10*1024*1024);
  let value;try{value=JSON.parse(text);}catch{fail('INVALID_INPUT');}
  invariant(value?.v===1,'INCOMPATIBLE');invariant(Array.isArray(value.nodes)&&value.nodes.length<=500);
  const check=(item,depth=0)=>{
    invariant(depth<=30);
    if(item&&typeof item==='object')for(const [key,next] of Object.entries(item)){invariant(!['__proto__','prototype','constructor'].includes(key));check(next,depth+1);}
  };check(value);
  const ids=new Set();
  for(const node of value.nodes){invariant(typeof node.id==='string'&&node.id.length<=200&&!ids.has(node.id));ids.add(node.id);}
  for(const node of value.nodes){
    let current=node;const seen=new Set([node.id]);
    while(current.parentId){invariant(ids.has(current.parentId)&&!seen.has(current.parentId));seen.add(current.parentId);current=value.nodes.find(n=>n.id===current.parentId);}
  }
  const detached=unbindImportedSession(value);
  return {...detached,nodes:detached.nodes.map(node=>{
    const {conversationId,operationId,requestId,pendingRequest,activeRequest,terminalSessionId,...content}=node;
    return {...content,loading:false,imported:true};
  })};
}

export class Workspace {
  constructor({binding,journal,audit,clean,rag,start}){Object.assign(this,{binding,journal,audit,clean,rag,start});this.artifacts=new ArtifactStore(journal);}
  async call(principal,input){
    this.binding.assertCurrent();authorize(principal,'inspect',[this.binding.installationId]);
    invariant(principal.surface==='operator','DENIED');
    if(['rag-list','rag-search','rag-upload','rag-index','rag-context'].includes(input.action))return this.ragCall(principal,input);
    if(input.action==='canvas-export'){
      const record=this.journal.record('canvas',input.args.id,principal);
      return this.clean({id:input.args.id,name:record.name,content:JSON.parse(this.artifacts.read(principal,record.artifactId)),source:'Explicitly saved version-1 Canvas'});
    }
    if(!['rag-stage','canvas-import'].includes(input.action))fail('UNQUALIFIED');
    const value=input.action==='canvas-import'?importedCanvas(input.args.content):input.args.content;
    if(input.action==='rag-stage')invariant(typeof value==='string'&&Buffer.byteLength(value)<=1024*1024&&!value.includes('\0'));
    invariant(typeof input.nonce==='string');
    const operation=this.journal.admit(principal,input.nonce,input.action,{...input,args:{...input.args,content:undefined,contentDigest:digest(input.args.content)}});
    if(operation.result)return operation.result;
    this.journal.transition(operation.operationId,'running');
    try{
      await this.audit.record({operationId:operation.operationId,state:input.action});
      const id=randomUUID(),bytes=input.action==='canvas-import'?JSON.stringify(value):value;
      const artifact=this.artifacts.write(principal,bytes,input.action==='canvas-import'?'canvas':'context');
      const record={name:(input.args.name||'Selected content').slice(0,200),artifactId:artifact.id,size:artifact.size,createdAt:new Date().toISOString(),source:'Explicit operator selection'};
      const result=input.action==='canvas-import'?{id,name:record.name,version:1}:{contextId:id,name:record.name,size:artifact.size,indexed:false,reason:'Staged text is included only in a request that explicitly selects this context.'};
      this.journal.put(input.action==='canvas-import'?'canvas':'context',id,principal,input.action==='canvas-import'?record:{...record,reviewed:true,mediaType:'text/plain'});
      this.journal.transition(operation.operationId,'succeeded',result);return result;
    }catch(error){this.journal.transition(operation.operationId,'failed',safeError(error));throw error;}
  }
  async ragCall(principal,input){
    const args=input.args;
    if(input.action==='rag-list'){
      const listing=await this.rag.call('rag_list',{}),stats=await this.rag.call('rag_stats',{});
      const rows=[...(listing.documents||[]),...(listing.snapshots||[]),...(listing.replicas||[])];
      const offset=Number(input.cursor||0),limit=input.limit||100;invariant(Number.isSafeInteger(offset)&&offset>=0&&limit>0&&limit<=500);
      return this.clean({documents:rows.slice(offset,offset+limit),total:rows.length,...(offset+limit<rows.length?{nextCursor:String(offset+limit)}:{}),stats,
        uploads:this.journal.records('rag-upload',principal),operations:this.journal.list(principal).filter(o=>o.kind==='rag-index'),source:'Existing backend RAG store; retrieved documents are not current device observations.'});
    }
    if(input.action==='rag-search'){
      const collection=args.collection??'documents',k=args.k??5;
      invariant(typeof args.query==='string'&&args.query.trim().length>0&&args.query.length<=4000);
      invariant(typeof collection==='string'&&/^[\w.-]{1,128}$/.test(collection)&&!collection.includes('..'));
      invariant(Number.isInteger(k)&&k>=1&&k<=20);
      const data=this.clean(await this.rag.call('rag_search',{query:args.query.trim(),collection,k}));
      invariant(Array.isArray(data.results),'SOURCE_UNAVAILABLE');
      const searchId=randomUUID();this.journal.put('rag-search',searchId,principal,{...data,collection,observedAt:new Date().toISOString()});
      return {...data,searchId};
    }
    if(input.action==='rag-index'){
      const upload=this.journal.record('rag-upload',args.id,principal);invariant(upload.reviewed===true,'DENIED');
      const previous=this.journal.byNonce(principal,input.nonce);
      const op=this.journal.admit(principal,input.nonce,'rag-index',input);
      if(!previous)await this.start(op.operationId);
      return op;
    }
    let bytes,record,result;
    if(input.action==='rag-upload'){
      invariant(typeof args.name==='string'&&args.name.length<=200&&args.name===path.basename(args.name)&&!/[\x00-\x1f\\/]/.test(args.name)&&formats.has(path.extname(args.name).toLowerCase()));
      invariant(typeof args.content==='string'&&args.content.length<=14*1024*1024&&/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(args.content));
      bytes=Buffer.from(args.content,'base64');invariant(bytes.length>0&&bytes.length<=10*1024*1024&&bytes.toString('base64')===args.content);
      invariant(args.docType===undefined||['vendor','standard','customer','install-guide','other'].includes(args.docType));
      record={name:args.name,docType:args.docType||'other',reviewed:true,createdAt:new Date().toISOString()};
    }else{
      const search=this.journal.record('rag-search',args.id,principal);
      invariant(Array.isArray(args.indices)&&args.indices.length>0&&args.indices.length<=20&&new Set(args.indices).size===args.indices.length);
      const results=args.indices.map(i=>{invariant(Number.isInteger(i)&&i>=0&&i<search.results.length);return search.results[i];});
      bytes=Buffer.from(results.map(r=>[r.citation,r.low_confidence?'Low confidence retrieval.':null,r.staleness_notice||r.age_human,r.chunk_text].filter(Boolean).join('\n')).join('\n\n'));
      invariant(bytes.length<=1024*1024);
      record={name:`RAG: ${results.map(r=>r.title||'Result').join(', ').slice(0,150)}`,reviewed:true,mediaType:'text/plain',source:'Explicitly selected RAG results',collection:search.collection,citations:results.map(r=>r.citation),createdAt:new Date().toISOString()};
    }
    const op=this.journal.admit(principal,input.nonce,input.action,{...input,args:{...args,content:undefined,contentDigest:digest(bytes)}});
    if(op.result)return op.result;
    this.journal.transition(op.operationId,'running');
    try{
      await this.audit.record({operationId:op.operationId,state:input.action});
      const id=randomUUID(),artifact=this.artifacts.write(principal,bytes,input.action==='rag-upload'?'rag-upload':'context');
      this.journal.put(input.action==='rag-upload'?'rag-upload':'context',id,principal,{...record,artifactId:artifact.id,size:bytes.length,sha256:artifact.hash});
      result=input.action==='rag-upload'?{uploadId:id,name:record.name,size:bytes.length,sha256:artifact.hash,indexed:false}:{contextId:id,name:record.name,size:bytes.length,indexed:false};
      this.journal.transition(op.operationId,'succeeded',result);return result;
    }catch(error){this.journal.transition(op.operationId,'failed',safeError(error));throw error;}
  }
  async runIndex(operationId){
    const lease=this.journal.claim(operationId,{pid:process.pid,start:new Date().toISOString()});if(!lease)return;
    let dispatched=false,heartbeatFailed=false,intake;
    const timer=setInterval(()=>{try{this.journal.renew(operationId,lease);}catch{heartbeatFailed=true;}},5000);timer.unref();
    try{
      const input=this.journal.input(operationId,lease),principal=this.binding.principal;
      const upload=this.journal.record('rag-upload',input.args.id,principal);
      await this.audit.record({operationId,state:'before-rag-index'});this.binding.assertCurrent();
      const parent=path.join(this.journal.directory,'rag-intake');ownedDirectory(parent,{create:true});intake=fs.mkdtempSync(path.join(parent,'upload-'));
      const file=path.join(intake,upload.name);atomicPrivate(file,this.artifacts.read(principal,upload.artifactId));
      invariant(!heartbeatFailed,'UNKNOWN_OUTCOME');
      this.journal.event(operationId,'dispatch-intent',{source:'Existing rag_ingest integration'});dispatched=true;
      const result=await this.rag.call('rag_ingest',{file_path:file,title:upload.name,doc_type:upload.docType,source:`vscode:${upload.name}`,replace_existing:Boolean(input.args.expectedDocumentId),expected_document_id:input.args.expectedDocumentId||null});
      invariant(!heartbeatFailed,'UNKNOWN_OUTCOME');
      this.journal.attachReference(operationId,lease,result.document_id);
      await this.audit.record({operationId,state:'rag-index-completed'});
      this.journal.finish(operationId,lease,'succeeded',this.clean(result));
    }catch(error){
      const known=error instanceof RagToolError;
      this.journal.finish(operationId,lease,known||!dispatched?'failed':'unknown',known?{code:error.code,message:error.message}:safeError(error));
    }finally{clearInterval(timer);if(intake)fs.rmSync(intake,{recursive:true,force:true});}
  }
  snapshot(principal,conversationId){
    authorize(principal,'inspect',[this.binding.installationId]);
    if(conversationId){
      const conversation=this.journal.record('conversation',conversationId,principal);
      const requests=this.journal.conversationOperations(principal,conversationId).reverse().slice(-100).map(operation=>{
        const input=JSON.parse(this.journal._row(operation.operationId).input);
        return {...operation,prompt:input.prompt,contextIds:input.contextIds};
      });return this.clean({conversationId,...conversation,requests});
    }
    return this.clean({artifacts:this.journal.records('canvas',principal),contexts:this.journal.records('context',principal),conversations:this.journal.records('conversation',principal),contextPolicy:'Only explicitly selected content is staged. Staging is separate from RAG indexing.'});
  }
}
