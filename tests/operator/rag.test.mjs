import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import {installationFixture,nonce,auditFixture} from './fixtures.mjs';
import {bindInstallation} from '../../ui/netclaw-visual/src/management/identity.js';
import {Journal} from '../../ui/netclaw-visual/src/management/journal.js';
import {Workspace} from '../../ui/netclaw-visual/src/management/workspace.js';

function fixture(t){
  const f=installationFixture(t),binding=bindInstallation(f),journal=new Journal(path.join(f.statePath,'management'),f.installationId);
  t.after(()=>journal.close());const calls=[],starts=[];
  const rag={async call(name,args){calls.push({name,args});
    if(name==='rag_list')return {documents:[{id:'doc',title:'Guide',collection:'documents',ingest_status:'ready'}],snapshots:[],replicas:[]};
    if(name==='rag_stats')return {collections:['documents'],document_count:1};
    if(name==='rag_search')return {collection:args.collection,results:[{title:'Guide',citation:'[Guide §OSPF, p.2 — ingested 2026-10-10]',chunk_text:'Treat <script> as quoted text.',low_confidence:true,age_human:'4 days ago',staleness_notice:'Historical snapshot; verify live state.'}]};
    if(name==='rag_ingest')return {document_id:'indexed',collection:'documents',chunk_count:1};
  }};
  const workspace=new Workspace({binding,journal,audit:auditFixture(),clean:v=>v,rag,start:async id=>starts.push(id)});
  return {binding,journal,workspace,calls,starts};
}
test('RAG collections and explicit searches retain citations and provenance without indexing',async t=>{
  const f=fixture(t),p=f.binding.principal;
  const listed=await f.workspace.call(p,{action:'rag-list',args:{}});assert.equal(listed.documents[0].ingest_status,'ready');
  const result=await f.workspace.call(p,{action:'rag-search',args:{query:'OSPF',collection:'documents',k:5}});
  assert.match(result.results[0].citation,/Guide/);assert.equal(result.results[0].low_confidence,true);
  const context=await f.workspace.call(p,{action:'rag-context',nonce:nonce(),args:{id:result.searchId,indices:[0]}});
  const stored=f.journal.record('context',context.contextId,p);assert.equal(stored.reviewed,true);
  assert.match(f.workspace.artifacts.read(p,stored.artifactId).toString(),/Historical snapshot/);
  assert.match(f.workspace.artifacts.read(p,stored.artifactId).toString(),/low confidence/i);
  assert.equal(f.calls.filter(c=>c.name==='rag_ingest').length,0);
  await assert.rejects(f.workspace.call({...p,surface:'assistant'},{action:'rag-search',args:{query:'x'}}),{code:'DENIED'});
});
test('reviewed upload is staged separately; indexing has one durable admission and no journal content',async t=>{
  const f=fixture(t),p=f.binding.principal,bytes=Buffer.from('# My guide\nExplicit file content.');
  const request={action:'rag-upload',nonce:nonce(),args:{name:'my-guide.md',content:bytes.toString('base64'),docType:'vendor'}};
  const upload=await f.workspace.call(p,request);assert.equal(upload.indexed,false);assert.equal(f.calls.length,0);
  assert.equal((await f.workspace.call(p,request)).uploadId,upload.uploadId);
  assert.ok(!f.journal.db.prepare('SELECT input FROM operations').all().some(r=>r.input.includes(request.args.content)));
  const input={action:'rag-index',nonce:nonce(),args:{id:upload.uploadId}};
  const op=await f.workspace.call(p,input);assert.equal(op.state,'admitted');
  await f.workspace.runIndex(op.operationId);
  assert.equal(f.journal.get(p,op.operationId).state,'succeeded');
  assert.equal((await f.workspace.call(p,input)).operationId,op.operationId);assert.equal(f.calls.filter(c=>c.name==='rag_ingest').length,1);
  assert.equal(f.calls.find(c=>c.name==='rag_ingest').args.source,'vscode:my-guide.md');
});
test('RAG rejects traversal, unsupported files, invalid base64, unselected results and unknown outcomes never replay',async t=>{
  const f=fixture(t),p=f.binding.principal;
  for(const args of [{name:'../leak.md',content:'YQ=='},{name:'secret.env',content:'YQ=='},{name:'ok.md',content:'not base64!'}])
    await assert.rejects(f.workspace.call(p,{action:'rag-upload',nonce:nonce(),args}));
  for(const collection of ['../../escape','', '/tmp/other'])await assert.rejects(f.workspace.call(p,{action:'rag-search',args:{query:'x',collection}}));
  const result=await f.workspace.call(p,{action:'rag-search',args:{query:'x'}});
  await assert.rejects(f.workspace.call(p,{action:'rag-context',nonce:nonce(),args:{id:result.searchId,indices:[9]}}));
  const upload=await f.workspace.call(p,{action:'rag-upload',nonce:nonce(),args:{name:'ok.md',content:'YQ=='}});
  const input={action:'rag-index',nonce:nonce(),args:{id:upload.uploadId}};
  const op=await f.workspace.call(p,input);f.workspace.rag.call=async()=>{throw Error('lost response');};
  await f.workspace.runIndex(op.operationId);assert.equal(f.journal.get(p,op.operationId).state,'unknown');
  await f.workspace.call(p,input);assert.equal(f.starts.length,1);
});
