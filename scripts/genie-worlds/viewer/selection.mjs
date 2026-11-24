// Local evidence presentation shared by both exact graph renderers. No network effects.
const certainty={corroborated:'Reciprocal evidence',one_sided:'One-sided claim',conflict:'Conflicting evidence',unknown:'Unknown',fictional:'Fictional connection'};
const ageLabel=seconds=>seconds<60?`${seconds}s`:seconds<3600?`${Math.floor(seconds/60)}m`:seconds<86400?`${Math.floor(seconds/3600)}h`:`${Math.floor(seconds/86400)}d`;
// Native normalization preserves microseconds; Date.parse alone loses this order.
const micros=value=>{const m=/^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?Z$/.exec(value);return m?BigInt(Date.parse(m[1]+'Z'))*1000n+BigInt((m[2]||'').padEnd(6,'0')):null;};
const timing=(state,source)=>{
 const [a,b,c,d]=[state.started_at,state.finished_at,source.started_at,source.finished_at].map(micros);
 return [a,b,c,d].includes(null)?'timing comparison unavailable':b<c?'before discovery':a>d?'after discovery':'capture intervals overlap';
};
export function selectionDetails(graph,id,now=Date.now()){
 const item=[...graph.devices,...graph.interfaces,...graph.links].find(e=>e.id===id);
 if(!item)throw Error('unknown_entity');
 const device=id=>{const d=graph.devices.find(d=>d.id===id);return `${d.label} (${d.id})`;};
 const rows=[['Entity ID',id],['Data',graph.classification==='synthetic'?'Synthetic fixture · no measured device state':'Private local snapshot']];
 if(item.endpoints){
  rows.push(['Recorded certainty',certainty[item.certainty]],['Current link health','Unknown — discovery does not establish health']);
  item.endpoints.forEach((id,i)=>{const p=graph.interfaces.find(p=>p.id===id);rows.push([`Endpoint ${i+1}`,`${device(p.device_id)} / ${p.label} (${p.id}) · snapshot status: ${p.status}`]);});
 }else if(item.device_id){rows.push(['Device',device(item.device_id)],['Interface',item.label],['Snapshot status',item.status]);}
 else rows.push(['Device',item.label],['Role',item.role]);
 const portIds=item.endpoints|| (item.device_id?[item.id]:graph.interfaces.filter(p=>p.device_id===id).map(p=>p.id));
 const interfaceStates=(graph.interface_states||[]).filter(s=>portIds.includes(s.resolved_interface_id)||(!item.device_id&&!item.endpoints&&s.device_ref===id));
 if(graph.interface_states&&!interfaceStates.length)rows.push(['Parser state observations','No supplied state observations for this selection; current health remains unknown']);
 for(const s of interfaceStates){
  const age=now-Date.parse(s.finished_at),freshness=!Number.isFinite(age)||age<0?'Unknown age':`${age>300000?'Stale':'Recent'} · ${ageLabel(Math.floor(age/1000))} old`;
  rows.push([`Parser state · ${s.interface_name}`,`${s.resolved_interface_id||'Unbound interface'}${s.binding_reason?' · '+s.binding_reason.replaceAll('_',' '):''} · separate parser fields; no combined health inferred`]);
  for(const [name,v] of Object.entries(s.state))rows.push([name,v.certainty==='observed'?`${v.value} · observed · ${v.source_path.join(' → ')}`:`Unknown · ${v.reason.replaceAll('_',' ')}${v.source_path?' · '+v.source_path.join(' → '):''}`]);
  rows.push(['State source',`${s.source} / ${s.command} / ${s.parser_version} / ${s.observation_id} · ${s.started_at} → ${s.finished_at} · ${freshness}`]);
 }
 const counters=(graph.counters||[]).filter(c=>portIds.includes(c.interface_id));
 if(!counters.length)rows.push(['Counters','Unavailable for this selection; no rate or utilization inferred']);
 for(const c of counters){
  const p=graph.interfaces.find(p=>p.id===c.interface_id);
  rows.push([`Counter · ${p.label} · ${c.direction} · ${c.field}`,c.value===null?`Unavailable · ${c.reason.replaceAll('_',' ')}`:`${c.value} ${c.units} · delta ${c.delta} over ${c.elapsed_seconds}s`]);
  for(const slot of ['first','second']){
   const s=c.observed_samples?.find(s=>s.slot===slot),e=graph.evidence.find(e=>e.id===s?.evidence_id);
   rows.push([`Observed ${slot} count`,s?`${s.value===null?'Unknown counter value':`${s.value} ${s.units}`} · ${s.started_at} → ${s.finished_at} · ${s.sampled_at?`sampled ${s.sampled_at}`:'sample instant unknown'} · ${e?.source} / ${e?.command} / ${e?.observation_id} / ${e?.source_path?.join(' → ')}`:'No qualified observation supplied']);
  }
  const finish=c.observed_samples?.at(-1)?.finished_at||c.sample_intervals.at(-1)?.finished_at,age=now-Date.parse(finish);
  rows.push(['Counter age',!Number.isFinite(age)||age<0?'Unknown age':`${age>300000?'Stale':'Recent'} snapshot · ${ageLabel(Math.floor(age/1000))} old`]);
  rows.push(['Utilization',c.utilization_percent===null?`Unavailable · ${c.utilization_reason.replaceAll('_',' ')}${c.capacity?` · sourced capacity ${c.capacity.value} ${c.capacity.units}`:''}`:`${c.utilization_percent}% · ${c.direction} · capacity ${c.capacity.value} ${c.capacity.units}`]);
  c.sample_intervals.forEach((v,i)=>rows.push([`Sample ${c.sample_ids[i]}`,`${v.started_at} → ${v.finished_at} · sampled ${v.sampled_at}`]));
 }
 const discovery=(graph.discovery||[]).filter(c=>portIds.includes(c.local_interface_id)||portIds.includes(c.remote_interface_id));
 const deviceIds=new Set(portIds.map(pid=>graph.interfaces.find(p=>p.id===pid)?.device_id));
 if(!item.endpoints&&!item.device_id)deviceIds.add(id);
 const coverage=(graph.coverage||[]).filter(c=>deviceIds.has(c.device_ref));
 if(graph.discovery&&!discovery.length)rows.push(['Discovery','No supplied claims for this selection; this does not establish absence of neighbors']);
 if(graph.coverage&&!coverage.length)rows.push(['Read coverage','No supplied collection records for this selection']);
 for(const c of discovery)rows.push([`${c.protocol.toUpperCase()} claim ${c.id}`,`${c.local_interface_id} → ${c.remote_interface_id||'Unresolved endpoint'} · ${c.reason||c.certainty}${c.stale?' · stale':''}${c.expired?' · expired':''} · remote claim: ${c.remote_identities.map(i=>`${i.kind}=${i.value}`).join(', ')} / ${c.remote_port.value}`]);
 const stateComparisons=[];
 for(const c of discovery){
  const sources=[graph.evidence.find(e=>e.id===c.discovery_evidence_id)].filter(Boolean);
  for(const pid of [c.local_interface_id,c.remote_interface_id]){
   const p=graph.interfaces.find(p=>p.id===pid),state=graph.evidence.find(e=>e.id===p?.state_evidence_id);
   if(!state||!['down','conflict'].includes(p.status))continue;
   for(const source of sources){
    const relation=timing(state,source);
    const age=now-Date.parse(state.finished_at),freshness=age<0?'unknown age':age>300000?'stale':'recent';
    rows.push([`State / discovery · ${p.label}`,`${p.status} snapshot · ${relation} · ${freshness} state evidence. ${c.protocol.toUpperCase()} is a neighbor claim, not current link health.`]);
    stateComparisons.push({claim_id:c.id,interface_id:p.id,status:p.status,relation,state_evidence_id:state.id,discovery_evidence_id:source.id});
   }
  }
 }
 for(const c of coverage)rows.push([`Read ${c.device_ref} · ${c.command}`,`${c.outcome}${c.capture_outcome_unknown?' · capture outcome unknown':''}${c.failure_reason?' · '+c.failure_reason:''} · ${c.started_at} → ${c.finished_at}`]);
 const evidence=[...new Set([...item.evidence_ids,...discovery.flatMap(c=>c.evidence_ids),...stateComparisons.map(c=>c.state_evidence_id),...counters.flatMap(c=>c.evidence_ids)])].map(id=>{
  const e=graph.evidence.find(e=>e.id===id),delta=now-Date.parse(e.finished_at),age=Number.isFinite(delta)&&delta>=0?Math.floor(delta/1000):null;
  return {...e,age_seconds:age,stale:age===null?null:delta>300000};
 });
 const observations=evidence.map(e=>({source:e.command?`${e.source} · ${e.command}`:e.source,outcome:e.outcome,interval:`${e.started_at} → ${e.finished_at}`,freshness:e.age_seconds===null?'Unknown age · observation is in the future':`${e.stale?'Stale':'Recent'} · ${ageLabel(e.age_seconds)} old`}));
 return {title:`${item.label||item.id} · ${item.status||item.certainty||item.role}`,rows,observations,raw:{entity_id:id,classification:graph.classification,...(item.endpoints?{endpoints:item.endpoints}:{}),evidence,discovery,coverage,stateComparisons,interfaceStates,counters}};
}
export function showSelection(graph,id,root=document){
 const detail=selectionDetails(graph,id),doc=root.ownerDocument||root;
 root.getElementById('selection').textContent=detail.title;
 const summary=root.getElementById('selection-summary');summary.replaceChildren();
 const dl=doc.createElement('dl');
 for(const [label,value]of detail.rows){const dt=doc.createElement('dt'),dd=doc.createElement('dd');dt.textContent=label;dd.textContent=value;dl.append(dt,dd);}summary.append(dl);
 for(const observation of detail.observations){const card=doc.createElement('section');card.className='observation-summary';
  for(const value of [observation.source,`${observation.outcome} · ${observation.freshness}`,observation.interval]){const p=doc.createElement('p');p.textContent=value;card.append(p);}summary.append(card);}
 root.getElementById('provenance').textContent=JSON.stringify(detail.raw,null,2);
 const panel=summary.closest('aside');if(panel)panel.scrollTop=0;
}
