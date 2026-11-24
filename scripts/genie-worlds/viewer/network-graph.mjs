// Local graph contract shared by renderers. Never a Google projection input.
const fail = () => { throw new Error('invalid_local_graph'); };
const text = (s) => typeof s === 'string' && s.length > 0 && s.length <= 128 && !/[\x00-\x1f\x7f]/.test(s);
const fields = (o, keys) => o && typeof o === 'object' && !Array.isArray(o) && Object.keys(o).every(k => keys.includes(k));
const freeze = (o) => { Object.values(o).forEach(v => { if (v && typeof v === 'object') freeze(v); }); return Object.freeze(o); };
export function localGraph(input) {
  if (!fields(input, ['schema', 'classification', 'id', 'devices', 'interfaces', 'links', 'evidence', 'discovery', 'coverage', 'counters', 'interface_states']) || input.schema !== 1 || !['private', 'synthetic'].includes(input.classification) || !text(input.id)) fail();
  for (const [key, max] of [['devices',4],['interfaces',1024],['links',256],['evidence',2048]]) if (!Array.isArray(input[key]) || input[key].length > max) fail();
  const graph = structuredClone(input), ids = new Set();
  for (const e of [...graph.devices, ...graph.interfaces, ...graph.links, ...graph.evidence]) {
    if (!text(e.id) || ids.has(e.id)) fail(); ids.add(e.id);
  }
  const evidence = new Set(graph.evidence.map(e => e.id)), devices = new Set(graph.devices.map(e => e.id)), ports = new Map(graph.interfaces.map(e => [e.id,e]));
  const refs = (e) => Array.isArray(e.evidence_ids) && e.evidence_ids.length > 0 && e.evidence_ids.length <= 24 && e.evidence_ids.every(id => evidence.has(id));
  for (const e of graph.evidence) {
    if (!fields(e,['id','source','started_at','finished_at','sha256','outcome','device_ref','command','parser_version','observation_id','source_path']) || !text(e.source) || !/^[a-f0-9]{64}$/.test(e.sha256) || !['observed','empty','raw_only','parse_failed','timeout','unavailable','synthetic'].includes(e.outcome)) fail();
    if (![e.started_at,e.finished_at].every(t => typeof t === 'string' && t.length <= 32 && /^\d{4}-\d\d-\d\dT.*Z$/.test(t) && Number.isFinite(Date.parse(t))) || Date.parse(e.finished_at) < Date.parse(e.started_at)) fail();
    if (graph.classification === 'private' && e.outcome === 'synthetic') fail();
    if ('observation_id' in e || 'source_path' in e || 'device_ref' in e || 'command' in e || 'parser_version' in e) {
      if (!devices.has(e.device_ref) || !['command','parser_version','observation_id'].every(k=>text(e[k])) || !Array.isArray(e.source_path) || !e.source_path.length || e.source_path.length>16 || !e.source_path.every(text)) fail();
    }
  }
  for (const d of graph.devices) if (!fields(d,['id','label','role','evidence_ids']) || !text(d.label) || !['router','switch','unknown'].includes(d.role) || !refs(d)) fail();
  for (const p of graph.interfaces) {
    if (!fields(p,['id','device_id','label','status','evidence_ids','state_evidence_id']) || !devices.has(p.device_id) || !text(p.label) || !['up','down','unknown','conflict'].includes(p.status) || !refs(p)) fail();
    if ('state_evidence_id' in p) {
      const e=graph.evidence.find(e=>e.id===p.state_evidence_id);
      if (!e || !p.evidence_ids.includes(e.id) || e.device_ref!==p.device_id || e.outcome!=='observed' || !['show interfaces','show ip interface brief'].includes(e.command)) fail();
    }
  }
  for (const l of graph.links) {
    if (!fields(l,['id','endpoints','certainty','evidence_ids']) || !Array.isArray(l.endpoints) || l.endpoints.length !== 2 || !l.endpoints.every(p => ports.has(p)) || l.endpoints[0] === l.endpoints[1] || ports.get(l.endpoints[0]).device_id === ports.get(l.endpoints[1]).device_id || !['corroborated','one_sided','conflict','unknown','fictional'].includes(l.certainty) || !refs(l)) fail();
    if (graph.classification === 'private' && l.certainty === 'fictional') fail();
  }
  for (const key of ['discovery','coverage']) {
    if (!(key in graph)) continue;
    if (!Array.isArray(graph[key]) || graph[key].length > (key==='discovery'?256:128) || new Set(graph[key].map(r=>r.id)).size!==graph[key].length) fail();
  }
  for (const c of graph.discovery||[]) {
    if (!fields(c,['id','device_id','local_interface_id','remote_interface_id','remote_identities','remote_port','protocol','certainty','reason','stale','expired','expires_at','evidence_ids','discovery_evidence_id']) || !text(c.id) || !devices.has(c.device_id) || ports.get(c.local_interface_id)?.device_id!==c.device_id || (c.remote_interface_id!==null&&!ports.has(c.remote_interface_id)) || !['lldp','cdp'].includes(c.protocol) || !['one_sided','unknown','conflict'].includes(c.certainty) || !(c.reason===null||['unmatched_identity','conflicting_identity','ambiguous_identity','self_neighbor','unmatched_port','ambiguous_port','local_identity_unverified','stale','expired','expiry_unknown','competing_peer_claims'].includes(c.reason)) || typeof c.stale!=='boolean' || typeof c.expired!=='boolean' || !refs(c)) fail();
    if ('discovery_evidence_id' in c) {
      const e=graph.evidence.find(e=>e.id===c.discovery_evidence_id);
      if (!e || !c.evidence_ids.includes(e.id) || e.device_ref!==c.device_id || e.outcome!=='observed' || e.command!==`show ${c.protocol} neighbors detail`) fail();
    }
    const identity=(v,kinds)=>fields(v,['kind','value'])&&kinds.includes(v.kind)&&text(v.value);
    if (!Array.isArray(c.remote_identities)||!c.remote_identities.length||c.remote_identities.length>16||!c.remote_identities.every(v=>identity(v,['chassis_id','cdp_device_id','hostname']))||!identity(c.remote_port,['port_id','interface_name'])) fail();
    if (c.expires_at!==null && (typeof c.expires_at!=='string'||c.expires_at.length>32||!c.expires_at.endsWith('Z')||!Number.isFinite(Date.parse(c.expires_at)))) fail();
  }
  for (const c of graph.coverage||[]) {
    if (!fields(c,['id','device_ref','source','command','parser_version','started_at','finished_at','outcome','sha256','failure_reason','capture_outcome_unknown']) || !['id','source','command','parser_version'].every(k=>text(c[k])) || !devices.has(c.device_ref) || !['observed','empty','raw_only','parse_failed','timeout','unavailable'].includes(c.outcome)) fail();
    if (![c.started_at,c.finished_at].every(t=>typeof t==='string'&&t.length<=32&&t.endsWith('Z')&&Number.isFinite(Date.parse(t))) || Date.parse(c.finished_at)<Date.parse(c.started_at)) fail();
    if ('failure_reason' in c && ![null,'evidence_limit'].includes(c.failure_reason)) fail();
    if ('capture_outcome_unknown' in c && typeof c.capture_outcome_unknown!=='boolean') fail();
    if (!(typeof c.sha256==='string'&&/^[a-f0-9]{64}$/.test(c.sha256)) && !(c.sha256===null&&['timeout','unavailable'].includes(c.outcome))) fail();
  }
  if ('interface_states' in graph) {
    if (!Array.isArray(graph.interface_states) || graph.interface_states.length > 2048) fail();
    const seen = new Set();
    for (const s of graph.interface_states) {
      if (!fields(s,['observation_id','device_ref','interface_name','command','parser_version','sha256','started_at','finished_at','stale','state','source','resolved_interface_id','binding_reason']) || !text(s.interface_name) || typeof s.stale !== 'boolean') fail();
      const capture=(graph.coverage||[]).find(c=>c.id===s.observation_id);
      if (!capture || capture.outcome!=='observed' || capture.command!=='show interfaces' || !['device_ref','source','command','parser_version','sha256','started_at','finished_at'].every(k=>s[k]===capture[k])) fail();
      const key=JSON.stringify([s.observation_id,s.interface_name]);if(seen.has(key))fail();seen.add(key);
      if (s.resolved_interface_id===null) {
        if (!['unmatched_interface','ambiguous_interface'].includes(s.binding_reason)) fail();
      } else if (ports.get(s.resolved_interface_id)?.device_id!==s.device_ref || s.binding_reason!==null) fail();
      if (!fields(s.state,['enabled','oper_status','line_protocol'])) fail();
      for (const name of ['enabled','oper_status','line_protocol']) {
        const v=s.state[name];
        if (!fields(v,['value','source_path','certainty','reason'])) fail();
        if (v.source_path!==null && (!Array.isArray(v.source_path) || v.source_path.length!==2 || v.source_path[0]!==s.interface_name || v.source_path[1]!==name)) fail();
        if (v.certainty==='observed') {
          if (v.reason!==null || v.source_path===null || (name==='enabled'?typeof v.value!=='boolean':!['up','down'].includes(v.value))) fail();
        } else if (v.certainty!=='unknown' || v.value!==null || !['field_missing','invalid_state'].includes(v.reason) || (v.reason==='field_missing')!==(v.source_path===null)) fail();
      }
    }
  }
  if ('counters' in graph) {
    if (!Array.isArray(graph.counters)||graph.counters.length>512||new Set(graph.counters.map(r=>r.id)).size!==graph.counters.length) fail();
    const decimal=v=>typeof v==='string'&&/^(0|[1-9][0-9]{0,19})$/.test(v);
    const micro=v=>{const m=typeof v==='string'&&/^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d{1,6}))?Z$/.exec(v);return m&&Number.isFinite(Date.parse(m[1]+'Z'))?BigInt(Date.parse(m[1]+'Z'))*1000n+BigInt((m[2]||'').padEnd(6,'0')):null;};
    for (const r of graph.counters) {
      if (!fields(r,['id','interface_id','field','direction','sample_ids','sample_intervals','sample_evidence_ids','evidence_ids','continuity_evidence_id','capacity_evidence_id','value','delta','units','elapsed_seconds','certainty','reason','utilization_percent','utilization_reason','capacity','observed_samples'])||!text(r.id)||!ports.has(r.interface_id)||!text(r.field)||!['in','out'].includes(r.direction)) fail();
      const owner=ports.get(r.interface_id).device_id;
      if (!Array.isArray(r.evidence_ids)||r.evidence_ids.length>4||!Array.isArray(r.sample_ids)||r.sample_ids.length>2||!r.sample_ids.every(text)||!Array.isArray(r.sample_intervals)||!Array.isArray(r.sample_evidence_ids)||r.sample_intervals.length!==r.sample_ids.length||r.sample_evidence_ids.length!==r.sample_ids.length) fail();
      const proof=id=>{const e=graph.evidence.find(e=>e.id===id);if(!e||!r.evidence_ids.includes(id)||e.device_ref!==owner||e.outcome!=='observed'||!['show interfaces','show version'].includes(e.command)) fail();return e;};
      r.evidence_ids.forEach(proof);
      if('observed_samples' in r){
        if(!Array.isArray(r.observed_samples)||r.observed_samples.length>2||new Set(r.observed_samples.map(s=>s.slot)).size!==r.observed_samples.length)fail();
        for(const s of r.observed_samples){
          if(!fields(s,['slot','id','value','units','outcome','started_at','finished_at','sampled_at','evidence_id'])||!['first','second'].includes(s.slot)||!text(s.id)||!['bytes','packets','errors'].includes(s.units))fail();
          const e=proof(s.evidence_id),a=micro(s.started_at),b=micro(s.finished_at),t=micro(s.sampled_at);
          if(e.command!=='show interfaces'||e.started_at!==s.started_at||e.finished_at!==s.finished_at||a===null||b===null||a>b||(s.sampled_at!==null&&(t===null||t<a||t>b)))fail();
          if(s.outcome==='observed'){if(!decimal(s.value)||BigInt(s.value)>=2n**64n)fail();}
          else if(s.outcome!=='unknown'||s.value!==null)fail();
        }
      }
      const times=r.sample_intervals.map((v,i)=>{
        if(!fields(v,['started_at','finished_at','sampled_at']))fail();
        const e=proof(r.sample_evidence_ids[i]),a=micro(v.started_at),b=micro(v.finished_at),t=micro(v.sampled_at);
        if(e.command!=='show interfaces'||e.started_at!==v.started_at||e.finished_at!==v.finished_at||[a,b,t].includes(null)||a>t||t>b)fail();return [a,b,t];
      });
      for(const key of ['continuity_evidence_id','capacity_evidence_id'])if(key in r)proof(r[key]);
      if(r.certainty==='derived'){
        if(r.reason!==null||r.sample_ids.length!==2||r.sample_ids[0]===r.sample_ids[1]||r.sample_evidence_ids[0]===r.sample_evidence_ids[1]||!r.continuity_evidence_id||!decimal(r.delta)||!['bytes/s','packets/s','errors/s'].includes(r.units)||typeof r.value!=='number'||!Number.isFinite(r.value)||r.value<0)fail();
        if(proof(r.sample_evidence_ids[0]).observation_id===proof(r.sample_evidence_ids[1]).observation_id)fail();
        if(r.observed_samples){
          const values=['first','second'].map((slot,i)=>{const s=r.observed_samples.find(s=>s.slot===slot);if(!s||s.outcome!=='observed'||s.id!==r.sample_ids[i]||s.evidence_id!==r.sample_evidence_ids[i]||s.units+'/s'!==r.units||s.sampled_at!==r.sample_intervals[i].sampled_at)fail();return BigInt(s.value);});
          if(values[1]-values[0]!==BigInt(r.delta))fail();
        }
        const elapsed=Number(times[1][2]-times[0][2])/1e6;
        if(times[1][0]<times[0][1]||elapsed<=0||r.elapsed_seconds!==elapsed||Math.abs(r.value-Number(r.delta)/elapsed)>Math.max(1e-12,r.value*1e-12))fail();
      }else if(r.certainty!=='unknown'||r.value!==null||r.delta!==null||r.units!==null||r.elapsed_seconds!==null||!['missing_sample','invalid_sample','invalid_identity','missing_provenance','sample_unavailable','invalid_counter_kind','invalid_counter_value','invalid_interval','duplicate_sample','identity_or_counter_changed','continuity_unverified','counter_decreased'].includes(r.reason))fail();
      if('capacity' in r){
        if(!fields(r.capacity,['value','units','direction'])||!decimal(r.capacity.value)||BigInt(r.capacity.value)<=0n||r.capacity.units!=='bits/s'||r.capacity.direction!==r.direction||!r.capacity_evidence_id||r.units!=='bytes/s'||proof(r.capacity_evidence_id).command!=='show interfaces')fail();
      }
      if(r.utilization_percent!==null){
        if(r.certainty!=='derived'||!r.capacity||r.utilization_reason!==null||typeof r.utilization_percent!=='number'||!Number.isFinite(r.utilization_percent)||r.utilization_percent<0||r.utilization_percent>100||Math.abs(r.utilization_percent-r.value*800/Number(r.capacity.value))>1e-9)fail();
      }else if(!['rate_unknown','capacity_unavailable','capacity_unverified','counter_not_bytes','capacity_conflict'].includes(r.utilization_reason))fail();
      if(r.certainty==='unknown'&&(r.utilization_percent!==null||r.utilization_reason!=='rate_unknown'))fail();
    }
  }
  return freeze(graph);
}
export function graphLayout(graph) {
  const devices = [], interfaces = [], positions = new Map(); let y = 60;
  const sorted = [...graph.devices].sort((a,b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
  for (let row = 0; row < sorted.length; row += 2) {
    let rowHeight = 0;
    for (const [column,d] of sorted.slice(row,row+2).entries()) {
      const ps = graph.interfaces.filter(p => p.device_id === d.id).sort((a,b) => a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
      const x = column ? 650 : 50; let portY = y + Math.max(120,Math.ceil(d.label.length/28)*24+65);
      for (const p of ps) {
        const pos = { ...p, x: column ? x : x+400, y: portY, labelX: x+24 };
        positions.set(p.id,pos); interfaces.push(pos); portY += Math.max(1,Math.ceil(p.label.length/28))*24+28;
      }
      const height = Math.max(150,portY-y+10); rowHeight = Math.max(rowHeight,height);
      devices.push({...d,x,y,width:400,height});
    }
    y += rowHeight+110;
  }
  return { devices, interfaces, links: graph.links.map(l => ({...l,a:positions.get(l.endpoints[0]),b:positions.get(l.endpoints[1])})), width:1100, height:Math.max(500,y) };
}
