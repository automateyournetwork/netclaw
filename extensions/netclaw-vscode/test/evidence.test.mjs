import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { load } from './load.mjs';
const {operationEvidence,presentOperationDocument}=await load('src/client/evidence.ts');
const fixtures=JSON.parse(fs.readFileSync(new URL('../../../ui/netclaw-visual/src/shared/operation-evidence.fixture.json',import.meta.url)));
test('native documents separate authoritative IPv4/IPv6 facts from inaccurate preserved model commentary',()=>{
 const before=JSON.stringify(fixtures);
 for(const [i,summary] of ['192.0.2.0/26 · 62 usable hosts','2001:db8::/48 · 1208925819614629174706176 addresses'].entries()){
  const v=operationEvidence(fixtures[i]);assert.equal(v['Verified native summary'],summary);assert.deepEqual(v['Authoritative tool facts'],fixtures[i].result.evidence.output.tool.output);assert.equal(v['Unverified model commentary'],fixtures[i].result.evidence.output.model_answer);
  assert.equal(presentOperationDocument(fixtures[i]).result,fixtures[i].result);
 }
 const parent={parent_id:'parent',children:fixtures};const shown=presentOperationDocument(parent);assert.equal(shown.children,parent.children);assert.equal(shown.result_interpretation.length,2);assert.equal(JSON.stringify(fixtures),before);
});
test('unverified or mismatched normalized facts do not become authoritative',()=>{
 for(const change of [v=>v.result.verified=false,v=>v.result.evidence.output.tool.independent_verification=false,v=>v.result.evidence.output.tool.output.usable_count='64',v=>v.result.evidence.output.tool.arguments.cidr='other']){const v=structuredClone(fixtures[0]);change(v);assert.equal(operationEvidence(v)['Authoritative tool facts'],null);}
});
