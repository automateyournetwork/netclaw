import test from 'node:test';
import assert from 'node:assert/strict';
import {selectionDetails} from '../../scripts/genie-worlds/viewer/selection.mjs';
const graph={classification:'synthetic',devices:[{id:'a',label:'North hall',role:'router',evidence_ids:['e']},{id:'b',label:'South hall',role:'switch',evidence_ids:['e']}],interfaces:[{id:'a1',device_id:'a',label:'GigabitEthernet0/0/1',status:'unknown',evidence_ids:['e']},{id:'b1',device_id:'b',label:'Ethernet1/20',status:'down',evidence_ids:['e']}],links:[{id:'link',endpoints:['a1','b1'],certainty:'one_sided',evidence_ids:['e']}],evidence:[{id:'e',source:'Synthetic capture',started_at:'2026-01-01T00:00:00Z',finished_at:'2026-01-01T00:00:01Z',outcome:'synthetic',sha256:'a'.repeat(64)}]};
test('link inspector exposes both complete endpoint identities without asserting health',()=>{
 const detail=selectionDetails(graph,'link',Date.parse('2026-01-01T00:10:01Z'));
 assert(detail.rows.some(([k,v])=>k==='Endpoint 1'&&v.includes('North hall')&&v.includes('GigabitEthernet0/0/1')&&v.includes('a1')));
 assert(detail.rows.some(([k,v])=>k==='Endpoint 2'&&v.includes('Ethernet1/20')));
 assert(detail.rows.some(([k,v])=>k==='Recorded certainty'&&v==='One-sided claim'));
 assert(detail.rows.some(([k,v])=>k==='Current link health'&&v==='Unknown — discovery does not establish health'));
 assert.equal(detail.observations[0].freshness,'Stale · 10m old');assert.equal(detail.raw.evidence[0].stale,true);
 assert.deepEqual(detail.raw.endpoints,['a1','b1']);assert.equal(detail.raw.classification,'synthetic');
});
test('interface summary keeps unknown status and unavailable counters distinct from zero',()=>{
 const detail=selectionDetails(graph,'a1',Date.parse('2026-01-01T00:00:02Z'));
 assert(detail.rows.some(([k,v])=>k==='Snapshot status'&&v==='unknown'));
 assert(detail.rows.some(([k,v])=>k==='Counters'&&v.startsWith('Unavailable')));
 assert(detail.rows.some(([k,v])=>k==='Device'&&v==='North hall (a)'));
 assert.equal(detail.observations[0].freshness,'Recent · 1s old');assert.equal(detail.raw.evidence[0].stale,false);
});
test('future observation time remains unknown and cannot become fresh by clamping',()=>{
 const detail=selectionDetails(graph,'a',Date.parse('2025-01-01T00:00:00Z'));
 assert.equal(detail.observations[0].freshness,'Unknown age · observation is in the future');
 assert.equal(detail.raw.evidence[0].age_seconds,null);assert.equal(detail.raw.evidence[0].stale,null);
 assert.throws(()=>selectionDetails(graph,'missing'),/unknown_entity/);
});
test('down state and discovery retain their distinct times, provenance and certainty',()=>{
 for(const [start,end,relation] of [['2025-12-31T23:59:58Z','2025-12-31T23:59:59Z','before discovery'],['2026-01-01T00:00:02Z','2026-01-01T00:00:03Z','after discovery'],['2026-01-01T00:00:00Z','2026-01-01T00:00:01Z','capture intervals overlap'],['2026-01-01T00:00:01.000001Z','2026-01-01T00:00:01.000002Z','after discovery']]){
  const g=structuredClone(graph);g.interfaces[1].state_evidence_id='state';
  g.evidence.push({...g.evidence[0],id:'state',started_at:start,finished_at:end});
  g.discovery=[{id:'claim',local_interface_id:'a1',remote_interface_id:'b1',protocol:'lldp',certainty:'one_sided',remote_identities:[{kind:'hostname',value:'South hall'}],remote_port:{value:'Ethernet1/20'},evidence_ids:['e'],discovery_evidence_id:'e'}];
  const d=selectionDetails(g,'link',Date.parse('2026-01-01T00:10:00Z'));
  assert.equal(d.raw.stateComparisons[0].relation,relation);assert(d.rows.some(([k,v])=>k.startsWith('State / discovery')&&v.includes('stale')));
  assert(d.raw.evidence.some(e=>e.id==='state'));assert.equal(g.links[0].certainty,'one_sided');
  delete g.discovery[0].discovery_evidence_id;assert.equal(selectionDetails(g,'link').raw.stateComparisons.length,0);
 }
});
test('counter selection distinguishes reset, valid zero, capacity conflict and future age',()=>{
 const g=structuredClone(graph);
 const base={id:'counter',interface_id:'a1',field:'in_octets',direction:'in',sample_ids:['one','two'],sample_intervals:[{started_at:'2026-01-01T00:00:00Z',finished_at:'2026-01-01T00:00:01Z',sampled_at:'2026-01-01T00:00:01Z'}],evidence_ids:['e'],value:null,reason:'counter_decreased',utilization_percent:null,utilization_reason:'rate_unknown'};
 g.counters=[base];let d=selectionDetails(g,'a1',Date.parse('2025-01-01T00:00:00Z'));
 assert(d.rows.some(([k,v])=>v==='Unavailable · counter decreased'));assert(d.rows.some(([k,v])=>k==='Counter age'&&v==='Unknown age'));
 g.counters=[{...base,value:0,delta:'0',units:'bytes/s',elapsed_seconds:10,reason:null,utilization_reason:'capacity_unavailable'}];
 d=selectionDetails(g,'a1',Date.parse('2026-01-01T00:10:00Z'));assert(d.rows.some(([k,v])=>v==='0 bytes/s · delta 0 over 10s'));assert(d.rows.some(([k,v])=>k==='Counter age'&&v.startsWith('Stale')));
 g.counters[0]={...g.counters[0],value:100,delta:'1000',utilization_reason:'capacity_conflict',capacity:{value:'1',units:'bits/s'}};
 d=selectionDetails(g,'a1');assert(d.rows.some(([k,v])=>k==='Utilization'&&v==='Unavailable · capacity conflict · sourced capacity 1 bits/s'));
 assert.equal(selectionDetails(g,'b1').raw.counters.length,0);
});

test('independent parser fields retain unknowns, scope, age and unbound provenance',()=>{
 const g=structuredClone(graph);const s={observation_id:'capture',device_ref:'a',interface_name:'GigabitEthernet0/0/1',source:'Synthetic parser',command:'show interfaces',parser_version:'fixture',sha256:'f'.repeat(64),started_at:'2026-01-01T00:00:00Z',finished_at:'2026-01-01T00:00:01Z',stale:false,resolved_interface_id:'a1',binding_reason:null,state:{enabled:{value:false,certainty:'observed',reason:null,source_path:['GigabitEthernet0/0/1','enabled']},oper_status:{value:null,certainty:'unknown',reason:'field_missing',source_path:null},line_protocol:{value:null,certainty:'unknown',reason:'invalid_state',source_path:['GigabitEthernet0/0/1','line_protocol']}}};g.interface_states=[s];
 const before=structuredClone(g),d=selectionDetails(g,'link',Date.parse('2026-01-01T00:10:01Z'));
 assert(d.rows.some(([k,v])=>k==='enabled'&&v.startsWith('false · observed')));assert(d.rows.some(([k,v])=>k==='oper_status'&&v==='Unknown · field missing'));assert(d.rows.some(([k,v])=>k==='State source'&&v.includes('Stale · 10m')));assert.equal(d.raw.interfaceStates[0].sha256,'f'.repeat(64));assert.deepEqual(g,before);
 assert(selectionDetails(g,'a',Date.parse('2025-01-01T00:00:00Z')).rows.some(([k,v])=>k==='State source'&&v.endsWith('Unknown age')));
 assert.equal(selectionDetails(g,'b1').raw.interfaceStates.length,0);
 s.resolved_interface_id=null;s.binding_reason='unmatched_interface';assert.equal(selectionDetails(g,'link').raw.interfaceStates.length,0);assert(selectionDetails(g,'a').rows.some(([k,v])=>v.includes('Unbound interface · unmatched interface')));
});
