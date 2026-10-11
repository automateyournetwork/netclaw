import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { installationFixture, nonce, auditFixture } from './fixtures.mjs';
import { bindInstallation } from '../../ui/netclaw-visual/src/management/identity.js';
import { Journal } from '../../ui/netclaw-visual/src/management/journal.js';
import { Proposals } from '../../ui/netclaw-visual/src/management/proposals.js';

function setup(t) {
  const fixture=installationFixture(t), binding=bindInstallation(fixture), journal=new Journal(path.join(fixture.statePath,'management'),fixture.installationId);
  t.after(()=>journal.close());
  const audit=auditFixture(); let applied=0, verified=true, recovered=true;
  const adapter={ qualified:true, resource:'configuration',
    prepare:async()=>({baseline:fs.readFileSync(fixture.configPath),rollback:fs.readFileSync(fixture.configPath),changeClass:'operator-local',impact:'Synthetic fixture only'}),
    apply:async()=>{applied++; fs.writeFileSync(fixture.configPath,'{"changed":true}');return{};},
    verify:async()=>({verified}),rollback:async(_proposal,bytes)=>{fs.writeFileSync(fixture.configPath,bytes);return{verified:recovered};} };
  const proposals=new Proposals({binding,journal,audit,adapters:{'settings.patch':adapter}});
  return {...fixture,binding,journal,audit,proposals,adapter,get applied(){return applied;},failVerify(){verified=false;},failRecovery(){recovered=false;}};
}
const prepare=f=>f.proposals.prepare(f.binding.principal,{nonce:nonce(),action:'settings.patch',targets:[f.installationId],expectedRevision:f.proposals.revision(),patch:{model:'synthetic'}});
test('proposal retains real private artifacts, has no effects, apply verifies and cannot replay',async t=>{
  const f=setup(t), original=fs.readFileSync(f.configPath), p=await prepare(f);
  assert.equal(f.applied,0);assert.deepEqual(fs.readFileSync(f.configPath),original);
  const input={proposalId:p.proposalId,expectedRevision:p.proposal.expectedRevision,nonce:nonce()};
  const result=await f.proposals.apply(f.binding.principal,input);assert.equal(result.state,'succeeded');assert.equal(f.applied,1);
  assert.equal((await f.proposals.apply(f.binding.principal,input)).operationId,result.operationId);assert.equal(f.applied,1);
  await assert.rejects(f.proposals.apply(f.binding.principal,{...input,nonce:nonce()}),{code:'DENIED'});assert.equal(f.applied,1);
});
test('audit loss denies before configuration writes',async t=>{
  const f=setup(t),p=await prepare(f);f.audit.available=false;
  await assert.rejects(f.proposals.apply(f.binding.principal,{proposalId:p.proposalId,expectedRevision:p.proposal.expectedRevision,nonce:nonce()}));assert.equal(f.applied,0);
});
test('external edits invalidate prepared proposals and preserve new content',async t=>{
  const f=setup(t),p=await prepare(f);fs.writeFileSync(f.configPath,'{"external":true}');
  await assert.rejects(f.proposals.apply(f.binding.principal,{proposalId:p.proposalId,expectedRevision:p.proposal.expectedRevision,nonce:nonce()}),{code:'STALE_REVISION'});assert.equal(f.applied,0);
});
test('verification failure runs real recovery; failure remains visible',async t=>{
  for(const failure of [false,true]) {
    const f=setup(t),original=fs.readFileSync(f.configPath),p=await prepare(f);f.failVerify();if(failure)f.failRecovery();
    const result=await f.proposals.apply(f.binding.principal,{proposalId:p.proposalId,expectedRevision:p.proposal.expectedRevision,nonce:nonce()});
    assert.equal(result.state,failure?'rollback-failed':'rolled-back');assert.equal(result.result.approvalClosed,false);assert.deepEqual(fs.readFileSync(f.configPath),original);
  }
});
test('assistant proposal is human-reviewable without granting assistant apply authority',async t=>{
  const f=setup(t),assistant={...f.binding.principal,surface:'assistant',principalId:'client',grantId:'g',generation:1,actions:['propose'],targets:[f.installationId],expiresAt:Date.now()+10000};
  const p=await f.proposals.prepare(assistant,{nonce:nonce(),action:'settings.patch',targets:[f.installationId],expectedRevision:f.proposals.revision(),patch:{model:'synthetic'}});
  await assert.rejects(f.proposals.apply(assistant,{proposalId:p.proposalId,expectedRevision:p.proposal.expectedRevision,nonce:nonce()}),{code:'DENIED'});
  assert.equal((await f.proposals.apply(f.binding.principal,{proposalId:p.proposalId,expectedRevision:p.proposal.expectedRevision,nonce:nonce()})).state,'succeeded');
  assert.equal(f.journal.record('proposal',p.proposalId,assistant).state,'verified');
});
