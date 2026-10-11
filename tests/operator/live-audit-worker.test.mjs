import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { installationFixture,nonce } from './fixtures.mjs';
import { ManagementService } from '../../ui/netclaw-visual/src/management/service.js';

test('actual installed GAIT and detached worker complete after facade disposal',{skip:process.env.NETCLAW_TEST_LIVE_GAIT!=='1'},async t=>{
  const f=installationFixture(),root=fileURLToPath(new URL('../../',import.meta.url));
  let observer;
  const service=new ManagementService({root,home:f.home,kind:f.kind});
  const revision=service.identity().configurationRevision;
  const prepared=await service.call('operator_change_prepare',{nonce:nonce(),action:'integration.configure',targets:[f.installationId],expectedRevision:revision,patch:{fields:[{key:'ANTHROPIC_API_KEY',intent:'replace'}]}});
  const admitted=await service.call('operator_change_apply',{nonce:nonce(),proposalId:prepared.proposalId,expectedRevision:revision,replacements:{ANTHROPIC_API_KEY:'SYNTHETIC_DETACHED_ONLY'}});
  await service.close();
  observer=new ManagementService({root,home:f.home,kind:f.kind});
  t.after(async()=>{await observer.close();f.cleanup();});
  let outcome;const deadline=Date.now()+15000;
  do{outcome=await observer.call('operator_operation_get',{operationId:admitted.operationId});if(['succeeded','failed','rolled-back','rollback-failed','unknown'].includes(outcome.state))break;await new Promise(r=>setTimeout(r,100));}while(Date.now()<deadline);
  assert.equal(outcome.state,'succeeded',JSON.stringify(outcome));
  assert.ok(fs.readFileSync(path.join(f.home,'.env'),'utf8').includes('SYNTHETIC_DETACHED_ONLY'));
  const audit=await observer.audit.log();assert.equal(audit.ok,true);
  assert.ok(!JSON.stringify(audit).includes('SYNTHETIC_DETACHED_ONLY'));
  const worker=JSON.parse(observer.journal._row(admitted.operationId).worker);
  const exitDeadline=Date.now()+5000;
  while(Date.now()<exitDeadline){try{process.kill(worker.pid,0);}catch{break;}await new Promise(r=>setTimeout(r,50));}
});
