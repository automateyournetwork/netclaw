import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { installationFixture, nonce, auditFixture } from './fixtures.mjs';
import { bindInstallation } from '../../ui/netclaw-visual/src/management/identity.js';
import { Journal } from '../../ui/netclaw-visual/src/management/journal.js';
import { runOwnedOperation } from '../../ui/netclaw-visual/src/management/worker.js';

test('lost acknowledgement is unknown and a second worker cannot replay',async t=>{
  const f=installationFixture(t),binding=bindInstallation(f),journal=new Journal(path.join(f.statePath,'management'),f.installationId);t.after(()=>journal.close());
  const op=journal.admit(binding.principal,nonce(),'request',{});let effects=0;
  const args={journal,binding,operationId:op.operationId,audit:auditFixture(),reauthorize:async()=>{},dispatch:async()=>{effects++;throw Error('lost receipt');}};
  assert.equal((await runOwnedOperation(args)).state,'unknown');
  assert.equal((await runOwnedOperation(args)).dispatched,false);assert.equal(effects,1);
});
test('audit loss and withdrawn authority deny before worker dispatch',async t=>{
  for(const what of ['audit','authority']) {
    const f=installationFixture(t),binding=bindInstallation(f),journal=new Journal(path.join(f.statePath,'management'),f.installationId);t.after(()=>journal.close());
    const op=journal.admit(binding.principal,nonce(),'request',{}),audit=auditFixture();let effects=0;
    if(what==='audit')audit.available=false;
    const result=await runOwnedOperation({journal,binding,operationId:op.operationId,audit,reauthorize:async()=>{if(what==='authority')throw Error('withdrawn');},dispatch:async()=>{effects++;}});
    assert.equal(result.state,'failed');assert.equal(effects,0);
  }
});
