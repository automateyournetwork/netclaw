import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { installationFixture,nonce,auditFixture } from './fixtures.mjs';
import { bindInstallation } from '../../ui/netclaw-visual/src/management/identity.js';
import { Journal } from '../../ui/netclaw-visual/src/management/journal.js';
import { configurationAdapters,configurationSnapshot,patchEnvironment } from '../../ui/netclaw-visual/src/management/configuration.js';
import { Proposals } from '../../ui/netclaw-visual/src/management/proposals.js';
import { updateEnvironment } from '../../ui/netclaw-visual/src/security/private-files.js';

test('env edit preserves unrelated bytes and handles multiline legacy spans',()=>{
  const source='# keep CRLF\r\nUNRELATED="a\nb"\nANTHROPIC_API_KEY="old\nkey"\nTAIL=x\n';
  assert.equal(patchEnvironment(source,{ANTHROPIC_API_KEY:'new'}),'# keep CRLF\r\nUNRELATED="a\nb"\nTAIL=x\nANTHROPIC_API_KEY="new"\n');
});
test('configuration inventory contains presence, never synthetic secrets',t=>{
  const f=installationFixture(t),binding=bindInstallation(f);fs.appendFileSync(binding.envPath,'ANTHROPIC_API_KEY="SYNTHETIC_SECRET_150"\n');
  assert.ok(!JSON.stringify(configurationSnapshot(binding)).includes('SYNTHETIC_SECRET_150'));
});
test('secret proposal carries only intent; apply keeps blank/mask, replaces and explicitly clears',async t=>{
  const f=installationFixture(t),binding=bindInstallation(f),journal=new Journal(path.join(f.statePath,'management'),f.installationId);t.after(()=>journal.close());
  fs.appendFileSync(binding.envPath,'ANTHROPIC_API_KEY="SYNTHETIC_OLD"\n');
  const p=new Proposals({binding,journal,audit:auditFixture(),adapters:configurationAdapters(binding)});
  for(const [intent,value,expected] of [['replace','', 'SYNTHETIC_OLD'],['replace','****','SYNTHETIC_OLD'],['replace','SYNTHETIC_NEW','SYNTHETIC_NEW'],['clear',undefined,'']]){
    const proposal=await p.prepare(binding.principal,{nonce:nonce(),action:'integration.configure',targets:[f.installationId],expectedRevision:p.revision(),patch:{fields:[{key:'ANTHROPIC_API_KEY',intent}]}});
    assert.ok(!JSON.stringify(proposal).includes('SYNTHETIC_OLD'));
    const result=await p.apply(binding.principal,{nonce:nonce(),proposalId:proposal.proposalId,expectedRevision:proposal.proposal.expectedRevision,...(value===undefined?{}:{replacements:{ANTHROPIC_API_KEY:value}})});
    assert.equal(result.state,'succeeded');assert.equal(result.result.pendingRestart,true);
    assert.ok(fs.readFileSync(binding.envPath,'utf8').includes(`ANTHROPIC_API_KEY="${expected}"`));
    assert.equal(fs.statSync(binding.envPath).mode&0o777,0o600);
  }
});
test('executable injection and broad lab bypass cannot be configured through managed fields',async t=>{
  const f=installationFixture(t),binding=bindInstallation(f),adapter=configurationAdapters(binding)['integration.configure'];
  for(const key of ['NODE_OPTIONS','PYTHONPATH','PYATS_MCP_SCRIPT','NETCLAW_LAB_MODE','N2N_RISK_MODE']){
    await assert.rejects(adapter.prepare({targets:[f.installationId],patch:{fields:[{key,intent:'replace',value:'anything'}]}}),{code:'UNSUPPORTED'});
  }
});
test('existing HUD environment writer respects the management process lock',t=>{
  const f=installationFixture(t),journal=new Journal(path.join(f.statePath,'management'),f.installationId);t.after(()=>journal.close());
  const token=journal.lock('configuration','extension');
  assert.throws(()=>updateEnvironment(path.join(f.home,'.env'),{ANTHROPIC_API_KEY:'synthetic'}),{code:'BUSY'});
  journal.unlock('configuration',token);updateEnvironment(path.join(f.home,'.env'),{ANTHROPIC_API_KEY:'synthetic'});
  assert.ok(fs.readFileSync(path.join(f.home,'.env'),'utf8').includes('ANTHROPIC_API_KEY=synthetic'));
});
