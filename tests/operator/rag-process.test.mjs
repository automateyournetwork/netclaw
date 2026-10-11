import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {installationFixture,nonce} from './fixtures.mjs';
import {ManagementService} from '../../ui/netclaw-visual/src/management/service.js';

test('real RAG MCP, cached embeddings, detached indexing and retrieved citations survive facade exit',{
  skip:!process.env.NETCLAW_TEST_RAG_PYTHON||!process.env.NETCLAW_TEST_RAG_CACHE||process.env.NETCLAW_TEST_LIVE_GAIT!=='1',timeout:180000,
},async t=>{
  const f=installationFixture(),root=fileURLToPath(new URL('../../',import.meta.url));
  fs.appendFileSync(path.join(f.home,'.env'),`RAG_MCP_PYTHON=${process.env.NETCLAW_TEST_RAG_PYTHON}\nHF_HOME=${process.env.NETCLAW_TEST_RAG_CACHE}\n`);
  let service=new ManagementService({root,home:f.home,kind:f.kind}),worker;
  t.after(async()=>{await service.close();if(worker){const deadline=Date.now()+5000;while(Date.now()<deadline){try{process.kill(worker,0);}catch{break;}await new Promise(r=>setTimeout(r,50));}}f.cleanup();});
  const before=await service.call('operator_workspace',{action:'rag-list',args:{}});assert.equal(before.total,0);
  const content='# Reviewable networking reference\n\nThe lab change window is violet Thursday at 10:00 UTC. Verify the baseline before applying the reviewed plan.\n';
  const upload=await service.call('operator_workspace',{action:'rag-upload',nonce:nonce(),args:{name:'qualification-guide.md',content:Buffer.from(content).toString('base64'),docType:'customer'}});
  const input={action:'rag-index',nonce:nonce(),args:{id:upload.uploadId}};
  const admitted=await service.call('operator_workspace',input);await service.close();
  service=new ManagementService({root,home:f.home,kind:f.kind});
  let outcome;const deadline=Date.now()+150000;
  do{outcome=await service.call('operator_operation_get',{operationId:admitted.operationId});if(['succeeded','failed','unknown'].includes(outcome.state))break;await new Promise(r=>setTimeout(r,250));}while(Date.now()<deadline);
  worker=JSON.parse(service.journal._row(admitted.operationId).worker||'null')?.pid;
  assert.equal(outcome.state,'succeeded',JSON.stringify(outcome));
  assert.equal((await service.call('operator_workspace',input)).operationId,admitted.operationId);
  const listing=await service.call('operator_workspace',{action:'rag-list',args:{}});assert.equal(listing.total,1);assert.equal(listing.documents[0].ingest_status,'ready');
  const search=await service.call('operator_workspace',{action:'rag-search',args:{query:'When is the lab change window?',collection:'documents',k:3}});
  assert.ok(search.results.length);assert.match(search.results[0].citation,/qualification-guide/);assert.match(search.results[0].chunk_text,/violet Thursday/);
  const selected=await service.call('operator_workspace',{action:'rag-context',nonce:nonce(),args:{id:search.searchId,indices:[0]}});
  assert.ok(service.workspace.snapshot(service.binding.principal).contexts.some(c=>c.id===selected.contextId));
  assert.equal((await service.audit.log()).ok,true);
});
