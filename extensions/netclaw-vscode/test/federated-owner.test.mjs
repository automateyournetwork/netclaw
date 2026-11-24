import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {build} from 'esbuild';
import {load} from './load.mjs';
import {verifyClusterDescriptor} from '../../../ui/netclaw-visual/src/shared/cluster-binding.js';
const {OwnerClient}=await load('src/client/owner.ts');
const f=JSON.parse(fs.readFileSync('../../tests/fixtures/ha-198/federated-client.json'));
const viewFile=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'netclaw-peer-review-')),'view.mjs');
await build({entryPoints:['src/views/owner.ts'],outfile:viewFile,bundle:true,platform:'node',format:'esm',logLevel:'silent',plugins:[{name:'native-dialog-fixture',setup(b){
 b.onResolve({filter:/^vscode$/},()=>({path:'vscode',namespace:'fixture'}));
 b.onLoad({filter:/.*/,namespace:'fixture'},()=>({contents:'export const window={showInformationMessage:(...args)=>globalThis.__peerReviewDialog(...args)};',loader:'js'}));
}}]});
const {OwnerWorkflow}=await import(pathToFileURL(viewFile).href);

test('native owner verifies the peer endorsement before accepting remote status or decision eligibility',async()=>{
 const previous=globalThis.fetch,clock=Date.now;let response=structuredClone(f.operation);
 Date.now=()=>f.now_ms;
 const binding=await verifyClusterDescriptor(f.descriptor,{acceptedAnchor:f.descriptor.anchor_key_id,now:f.now_ms});
 const runtime={installationId:f.descriptor.installation_id,kind:'openclaw',role:'border',capabilities:{protectedProfile:true,protectedOperations:true,protectedProduction:true},access:{mode:'open-lab',principal:f.principal},cluster:f.descriptor};
 globalThis.fetch=async url=>new Response(JSON.stringify(new URL(url).pathname==='/api/runtime'?runtime:response),{status:200,headers:{'content-type':'application/json'}});
 const c=new OwnerClient(f.descriptor.manifest.manifest.nodes[0].endpoints.https,f.descriptor.installation_id,async()=>{},()=>{},'open-lab',binding);
 c.access={mode:'open-lab',principal:f.principal};
 try{
  const op=await c.status({operation_id:response.operation_id,client_nonce:response.client_nonce});
  assert.equal(c.reviewMatches(op.review),true);assert.equal(c.operationPrincipalMatches(op),true);assert.equal(c.canDecide(op),true);
  assert.notEqual(op.review.principal.subject,c.principal.subject);
  const dialogs=[];globalThis.__peerReviewDialog=async(...args)=>{dialogs.push(args);};
  const view=Object.create(OwnerWorkflow.prototype);view.document=async()=>{};view.showResult=async()=>{};
  const scope={client:c,operations:{references:()=>[]},current:()=>{}};
  await view.review(scope,op);
  assert.equal(dialogs.length,1);assert.equal(dialogs[0][1],'Review decision','Signed receiving-cluster principal must reach native review');
  dialogs.length=0;await view.review(scope,structuredClone(op));
  assert.equal(dialogs.length,0,'Unverified cloned endorsement must not enable native review');
  response.review.tool_call.arguments={forged:true};await assert.rejects(c.status({operation_id:response.operation_id}));
  response=structuredClone(f.operation);delete response.remote.client_binding;await assert.rejects(c.status({operation_id:response.operation_id}));
 }finally{c.close();globalThis.fetch=previous;Date.now=clock;delete globalThis.__peerReviewDialog;}
});
