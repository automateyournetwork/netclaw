import test from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { installationFixture,nonce,auditFixture } from './fixtures.mjs';
import { bindInstallation } from '../../ui/netclaw-visual/src/management/identity.js';
import { Journal } from '../../ui/netclaw-visual/src/management/journal.js';
import { Workspace } from '../../ui/netclaw-visual/src/management/workspace.js';

function fixture(t){const f=installationFixture(t),binding=bindInstallation(f),journal=new Journal(path.join(f.statePath,'management'),f.installationId);t.after(()=>journal.close());return {binding,journal,workspace:new Workspace({binding,journal,audit:auditFixture(),clean:v=>v})};}
test('explicit staged text has owned provenance and cannot be selected by another client',async t=>{
  const f=fixture(t),input={action:'rag-stage',nonce:nonce(),args:{name:'Selected text',content:'192.0.2.0/28'}};
  const result=await f.workspace.call(f.binding.principal,input);
  assert.equal(result.contextId,(await f.workspace.call(f.binding.principal,input)).contextId);
  const context=f.journal.record('context',result.contextId,f.binding.principal);assert.equal(context.reviewed,true);assert.equal(context.size,12);
  assert.throws(()=>f.journal.record('context',result.contextId,{surface:'assistant',principalId:'other',grantId:randomUUID()}),{code:'DENIED'});
});
test('versioned Canvas import preserves content and removes execution authority',async t=>{
  const f=fixture(t),original={v:1,nodes:[{id:'root',title:'Retained',hudThread:'foreign',conversationId:'foreign',kind:'chat',messages:[{role:'assistant',content:'quoted <script>text</script>',assessmentRefs:['foreign']}]}],drafts:{root:'draft'},quotes:{},attachments:{}};
  const input={action:'canvas-import',nonce:nonce(),args:{name:'Investigation',content:JSON.stringify(original)}};
  const imported=await f.workspace.call(f.binding.principal,input);
  const exported=await f.workspace.call(f.binding.principal,{action:'canvas-export',args:{id:imported.id}});
  assert.equal(exported.content.nodes[0].title,'Retained');assert.equal(exported.content.drafts.root,'draft');
  assert.equal(exported.content.nodes[0].hudThread,undefined);assert.equal(exported.content.nodes[0].conversationId,undefined);
  assert.equal(exported.content.nodes[0].messages[0].assessmentRefs,undefined);assert.equal(exported.content.nodes[0].messages[0].assessmentBinding,'unbound');
  assert.equal(original.nodes[0].hudThread,'foreign');
  await assert.rejects(f.workspace.call(f.binding.principal,{...input,nonce:nonce(),args:{content:'{"v":2,"nodes":[]}'}}),{code:'INCOMPATIBLE'});
});
test('Canvas rejects duplicate nodes, cycles, executable object keys and over-limit context',async t=>{
  const f=fixture(t);
  for(const content of ['{"v":1,"nodes":[{"id":"x"},{"id":"x"}]}','{"v":1,"nodes":[{"id":"x","parentId":"x"}]}','{"v":1,"nodes":[],"__proto__":{}}'])
    await assert.rejects(f.workspace.call(f.binding.principal,{action:'canvas-import',nonce:nonce(),args:{content}}));
  await assert.rejects(f.workspace.call(f.binding.principal,{action:'rag-stage',nonce:nonce(),args:{name:'x',content:'a'.repeat(1024*1024+1)}}));
});
