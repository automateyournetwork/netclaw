import test from 'node:test';
import assert from 'node:assert/strict';
import { entities, age, freshness, observation, protectedWorkspace, selectedContext, relations } from './model.js';
import { previewSources } from './fixtures.js';
const now = Date.parse('2026-09-28T12:00:00Z');
test('protected workspace uses selected role and configuration instead of legacy gateway health', () => {
  const runtime = { role: 'border', label: 'Protected Border', readiness: { ready: true, executionVerified: false },
    capabilities: { protectedProfile: true, protectedOperations: true } };
  assert.deepEqual(protectedWorkspace(runtime), { name: 'Protected Border', role: 'Border', status: 'Approval workspace configured' });
  assert.equal(protectedWorkspace({ ...runtime, readiness: { ready: false } }).status, 'Approval workspace unavailable');
  assert.equal(protectedWorkspace({ ...runtime, role: 'unknown' }).role, 'Protected role unverified');
  assert.equal(protectedWorkspace({ capabilities: { protectedProfile: false } }), null);
});
test('mixed deployment separates members, edges, peers and non-executing advisors', () => {
  const rows = entities(previewSources(new Date(now).toISOString()).n2n.payload);
  assert.equal(rows.filter(r => r.kind === 'member').length,3);
  assert.equal(rows.filter(r => r.kind === 'edge').length,1);
  assert.equal(rows.filter(r => r.kind === 'advisor').length,1);
  assert.match(rows.find(r=>r.kind === 'advisor').authority,/cannot execute/);
  assert.equal(new Set(rows.map(r=>r.key)).size, rows.length);
  assert.equal(relations(rows).find(r=>r.target.startsWith('peer:')).kind,'External federation');
});
test('standalone and malformed optional feeds do not manufacture members',()=>{
  for (const feed of [{}, { members: null, peers: 'bad', advisors: {} }, { members: [null, { display_name: 'No identity' }] }]) assert.deepEqual(entities(feed),[]);
});
test('same-named identities stay distinct and duplicate edge records do not inflate counts',()=>{
  const rows=entities({ peers:[{identity:'a',display_name:'Same'},{identity:'b',display_name:'Same'},{identity:'a',state:'severed'}],members:[{member_id:'phone',node_type:'edge'}],edgeNodes:[{member_id:'phone',node_type:'edge'}] });
  assert.equal(rows.length,3);assert.equal(rows.find(r=>r.identity==='a').status,'severed');
});
test('refresh failure retains last successful data without a false zero',()=>{
  const old=observation(null,{members:[{member_id:'a'}]},null,'2026-09-28T11:00:00Z');
  const next=observation(old,null,true,'2026-09-28T12:00:00Z');
  assert.equal(next.payload.members.length,1);assert.equal(next.lastSuccess,old.lastSuccess);assert.equal(next.state,'unavailable');
  assert.equal(observation(old,{available:false}).state,'unavailable');
});
test('future and missing times are not fresh; explicit seconds timestamps work',()=>{
  assert.equal(age(undefined,now),'Time unknown');assert.equal(freshness(null,now),'unknown');
  assert.equal(freshness(now+120000,now),'stale');assert.equal(age(now/1000-30,now),'30s ago');
});
test('selected context retains source and is bounded',()=>{
  const context=selectedContext('fixture',{value:'x'.repeat(20000)},'fixture source','observed time');
  assert.match(context,/fixture source/);assert.match(context,/observed time/);assert.ok(context.length<12500);
});

test('production summary requires fresh complete control evidence; LAB bypass remains visible',async()=>{
  const {securitySummary}=await import('./model.js');
  const posture={mode:'production',state:'enforced',computed_at:Date.now()/1000,controls:['sandbox','model-guard','audit'].map(name=>({name,available:true}))};
  assert.equal(securitySummary({labMode:false},posture,true).enforced,true);
  assert.match(securitySummary({labMode:true},posture,true).label,/LAB bypass enabled/);
  for(const p of [{...posture,controls:[]},{...posture,computed_at:1},{...posture,controls:[{name:'sandbox',available:true}]}])assert.equal(securitySummary({},p,true).enforced,false);
  assert.equal(securitySummary({},posture,false).enforced,false);
  assert.match(securitySummary({}, {...posture,mode:'unknown'},true).label,/unknown/);
});

test('connection observation is explicit and never invents a heartbeat for offline members', () => {
  const now = '2026-11-01T21:00:00Z';
  const rows = entities({ generatedAt: now, members: [{ member_id: 'risk/mac', live: true }, { member_id: 'risk/offline', live: false }], peers: [{ identity: 'live-peer', channel_state: 'up', last_seen: 0 }, { identity: 'old-peer', state: 'severed', channel_state: 'unknown' }] });
  assert.equal(rows[0].seen, now); assert.equal(rows[0].seenKind, 'connection');
  assert.equal(rows[1].seen, null); assert.equal(rows[1].seenKind, 'unknown');
  assert.equal(rows[2].seen, now); assert.equal(rows[3].status, 'severed');
});
