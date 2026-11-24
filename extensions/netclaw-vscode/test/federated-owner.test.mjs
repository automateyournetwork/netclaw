import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {load} from './load.mjs';
import {verifyClusterDescriptor} from '../../../ui/netclaw-visual/src/shared/cluster-binding.js';
const {OwnerClient}=await load('src/client/owner.ts');
const f=JSON.parse(fs.readFileSync('../../tests/fixtures/ha-198/federated-client.json'));

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
  response.review.tool_call.arguments={forged:true};await assert.rejects(c.status({operation_id:response.operation_id}));
  response=structuredClone(f.operation);delete response.remote.client_binding;await assert.rejects(c.status({operation_id:response.operation_id}));
 }finally{c.close();globalThis.fetch=previous;Date.now=clock;}
});
