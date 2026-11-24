import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {verifyClusterDescriptor, verifyFederatedOperation, clusterReviewMatches, clusterCanDecide} from './cluster-binding.js';
const f=JSON.parse(fs.readFileSync(new URL('../../../../tests/fixtures/ha-198/federated-client.json',import.meta.url)));
const fresh=()=>structuredClone(f.operation), options={now:f.now_ms};

test('peer review needs a verified exact ingress endorsement; receiver authority stays separate',async()=>{
 const local=(await verifyClusterDescriptor(f.descriptor,{acceptedAnchor:f.descriptor.anchor_key_id,...options})).descriptor;
 const op=fresh();assert.equal(clusterReviewMatches(local,op.review,f.principal),false);
 await verifyFederatedOperation(local,op,f.principal,options);
 assert.equal(clusterReviewMatches(local,op.review,f.principal),true);
 assert.equal(clusterCanDecide(local,op),true);
 assert.notEqual(op.review.principal.subject,f.principal.subject);
 assert.notEqual(op.review.cluster.cluster_id,local.cluster_id);
 assert.equal(clusterCanDecide({...local,authority:{...local.authority,epoch:local.authority.epoch+1}},op),false);
 assert.equal(clusterCanDecide({...local,authority:{...local.authority,state:'no_quorum'}},op),false);
 op.remote.authority.epoch++;assert.equal(clusterCanDecide(local,op),false);
 op.review.member.member_id='changed';assert.equal(clusterReviewMatches(local,op.review,f.principal),false);
});

test('missing proof, forged signature, peer pin, DTO and operator substitutions fail closed',async()=>{
 for(const mutate of [o=>delete o.remote.client_binding,o=>o.remote.client_binding.endorsement.signature='A'.repeat(96),o=>o.remote.client_binding.endorsement.key_id='a'.repeat(64),o=>o.remote.client_binding.manifest.manifest.organization='forged',o=>o.review.tool_call.arguments={},o=>o.client_nonce='changed',o=>o.operation_id='00000000-0000-4000-8000-000000000000',o=>o.remote.authority.epoch++,o=>o.allowed_actions=['approve','deny','invented']]){
  const op=fresh();mutate(op);await assert.rejects(verifyFederatedOperation(f.descriptor,op,f.principal,options));
  assert.equal(clusterReviewMatches(f.descriptor,op.review,f.principal),false);
 }
 await assert.rejects(verifyFederatedOperation(f.descriptor,fresh(),{...f.principal,subject:'foreign'},options));
 await assert.rejects(verifyFederatedOperation({...f.descriptor,generation:'00000000-0000-4000-8000-000000000000'},fresh(),f.principal,options));
});

test('even a valid ingress signature cannot override receiver/origin/principal bindings',async()=>{
 for(const row of f.signed_negative)await assert.rejects(verifyFederatedOperation(f.descriptor,structuredClone(row.operation),f.principal,options),undefined,row.case);
});

test('serialized endorsements are reverified; clones are not implicitly decision-capable',async()=>{
 const op=fresh();await verifyFederatedOperation(f.descriptor,op,f.principal,options);
 const clone=structuredClone(op);assert.equal(clusterCanDecide(f.descriptor,clone),false);
 await verifyFederatedOperation(f.descriptor,clone,f.principal,options);assert.equal(clusterCanDecide(f.descriptor,clone),true);
 const local={operation_id:'ordinary'};assert.equal(await verifyFederatedOperation(f.descriptor,local,f.principal,options),local);
});
