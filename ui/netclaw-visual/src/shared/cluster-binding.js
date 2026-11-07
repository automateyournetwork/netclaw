/** Public HA identity checks shared by browser and editor. Observations are never permits. */
const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
const HASH = /^[a-f0-9]{64}$/;
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
const check = (yes, code = 'invalid_cluster_descriptor') => { if (!yes) throw Object.assign(Error(code), { code }); };
const exact = (v, keys) => object(v) && Object.keys(v).sort().join() === keys.split(' ').sort().join();
const integer = (v, min = 0, max = Number.MAX_SAFE_INTEGER) => Number.isSafeInteger(v) && v >= min && v <= max;
const uuid = v => typeof v === 'string' && UUID.test(v);
const hash = v => typeof v === 'string' && HASH.test(v);
const identifier = v => typeof v === 'string' && v.length > 0 && v.length <= 200 && !/[\u0000-\u001f]/.test(v);
const bytes = text => new TextEncoder().encode(text);
export function clusterCanonical(v, depth = 0) {
 check(depth <= 32);
 if (v === null || typeof v === 'boolean' || typeof v === 'number' && Number.isSafeInteger(v)) return JSON.stringify(v);
 if (typeof v === 'string') { check(!/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/.test(v)); return JSON.stringify(v); }
 if (Array.isArray(v)) { check(v.length <= 10000); return '[' + v.map(x => clusterCanonical(x, depth + 1)).join(',') + ']'; }
 check(object(v) && Object.keys(v).length <= 10000 && Object.keys(v).every(k => /^[\x00-\x7f]{0,200}$/.test(k)));
 return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + clusterCanonical(v[k], depth + 1)).join(',') + '}';
}
const hex = value => Array.from(value, n => n.toString(16).padStart(2, '0')).join('');
const digest = async value => hex(new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256', value)));
const fromBase64 = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
const base64url = raw => btoa(String.fromCharCode(...raw)).replaceAll('+', '-').replaceAll('/', '_').replace(/=+$/, '');
function der(raw, at = 0) {
 check(at + 2 <= raw.length, 'invalid_cluster_certificate');
 const start = at, tag = raw[at++]; let length = raw[at++];
 if (length & 128) { const n = length & 127; check(n > 0 && n <= 3 && at + n <= raw.length && raw[at] !== 0, 'invalid_cluster_certificate'); length = 0; for (let i=0;i<n;i++) length = length * 256 + raw[at++]; check(length >= 128, 'invalid_cluster_certificate'); }
 check(at + length <= raw.length, 'invalid_cluster_certificate');
 return { tag, start, body: at, end: at + length, raw: raw.slice(start, at + length), value: raw.slice(at, at + length) };
}
function children(raw, item) { const out=[]; for(let at=item.body;at<item.end;) { const c=der(raw,at);check(c.end<=item.end,'invalid_cluster_certificate');out.push(c);at=c.end;check(out.length<=64,'invalid_cluster_certificate'); } return out; }
function certificate(pem, now) {
 check(typeof pem === 'string' && pem.length <= 8192 && /^-----BEGIN CERTIFICATE-----\n[A-Za-z0-9+/=\r\n]+-----END CERTIFICATE-----\n?$/.test(pem), 'invalid_cluster_certificate');
 const raw=fromBase64(pem.replace(/-----[^\n]+-----/g,'').replace(/\s/g,'')), cert=der(raw);
 check(cert.tag===48 && cert.end===raw.length,'invalid_cluster_certificate');
 const top=children(raw,cert);check(top.length===3 && top[0].tag===48,'invalid_cluster_certificate');
 const tbs=children(raw,top[0]), offset=tbs[0]?.tag===160?1:0, validity=tbs[3+offset], spki=tbs[5+offset];
 check(validity?.tag===48 && spki?.tag===48,'invalid_cluster_certificate');
 const dates=children(raw,validity);check(dates.length===2,'invalid_cluster_certificate');
 const parse=item=> {const s=new TextDecoder('ascii',{fatal:true}).decode(item.value),match=(item.tag===23?/^(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/:item.tag===24?/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/:/$a/).exec(s);check(match,'invalid_cluster_certificate');let year=Number(match[1]);if(item.tag===23)year+=year>=50?1900:2000;const parts=[year,...match.slice(2).map(Number)],ms=Date.UTC(parts[0],parts[1]-1,...parts.slice(2)),d=new Date(ms);check(d.getUTCFullYear()===parts[0]&&d.getUTCMonth()===parts[1]-1&&d.getUTCDate()===parts[2]&&d.getUTCHours()===parts[3]&&d.getUTCMinutes()===parts[4]&&d.getUTCSeconds()===parts[5],'invalid_cluster_certificate');return ms;};
 check(now>=parse(dates[0])&&now<=parse(dates[1]),'cluster_certificate_expired');
 const key=children(raw,spki);check(key.length===2&&key[0].tag===48&&key[1].tag===3&&key[1].value.length===66&&key[1].value[0]===0&&key[1].value[1]===4,'invalid_cluster_certificate');
 const oid=children(raw,key[0]);check(oid.length===2&&hex(oid[0].raw)==='06072a8648ce3d0201'&&hex(oid[1].raw)==='06082a8648ce3d030107','cluster_key_algorithm');
 return spki.raw;
}
function rawSignature(value) {
 check(typeof value==='string'&&/^[A-Za-z0-9_-]{8,200}$/.test(value),'invalid_manifest_signature');
 const raw=fromBase64(value.replaceAll('-','+').replaceAll('_','/')+'='.repeat((4-value.length%4)%4));check(base64url(raw)===value,'invalid_manifest_signature');
 const sequence=der(raw);check(sequence.tag===48&&sequence.end===raw.length,'invalid_manifest_signature');
 const parts=children(raw,sequence);check(parts.length===2,'invalid_manifest_signature');
 const result=new Uint8Array(64);parts.forEach((part,i)=>{check(part.tag===2&&part.value.length>0&&!(part.value[0]&128),'invalid_manifest_signature');let v=part.value;if(v[0]===0){check(v.length>1&&(v[1]&128),'invalid_manifest_signature');v=v.slice(1);}check(v.length<=32,'invalid_manifest_signature');result.set(v,i*32+32-v.length);});return result;
}
function endpoint(value, protocol) {
 check(typeof value==='string'&&value.length<=1024,'untrusted_cluster_endpoint');
 let u;try{u=new URL(value);}catch{check(false,'untrusted_cluster_endpoint');}
 check(u.protocol===protocol+':'&&!u.username&&!u.password&&!u.search&&!u.hash&&u.hostname&&(!u.port||integer(Number(u.port),1,65535))&&(protocol==='https'?u.pathname==='/':u.pathname==='/mobile/ws'),'untrusted_cluster_endpoint');
 return protocol==='https'?u.origin:u.href;
}
function address(v) {check(exact(v,'host port server_name')&&[v.host,v.server_name].every(h=>typeof h==='string'&&h.length>0&&h.length<=253&&/^[A-Za-z0-9._:\-]+$/.test(h))&&integer(v.port,1,65535));}
export async function verifyClusterDescriptor(value, { pin, acceptedAnchor, origin, installationId, now = Date.now() } = {}) {
 check(exact(value,'schema_version mode cluster_id generation manifest_revision node_id installation_id manifest anchor_certificate anchor_key_id authority')&&value.schema_version===1&&value.mode==='cluster'&&uuid(value.cluster_id)&&uuid(value.generation)&&uuid(value.node_id)&&uuid(value.installation_id)&&integer(value.manifest_revision,1)&&hash(value.anchor_key_id));
 check(integer(now));
 if(pin) check(exact(pin,'cluster_id generation anchor_key_id manifest_revision manifest_sha256')&&uuid(pin.cluster_id)&&uuid(pin.generation)&&hash(pin.anchor_key_id)&&hash(pin.manifest_sha256)&&integer(pin.manifest_revision,1)&&pin.cluster_id===value.cluster_id&&pin.generation===value.generation&&pin.anchor_key_id===value.anchor_key_id,'cluster_changed');
 else check(acceptedAnchor===value.anchor_key_id,'cluster_onboarding_required');
 check(bytes(clusterCanonical(value.manifest)).length<=128*1024,'manifest_capacity');
 const e=value.manifest;check(exact(e,'schema manifest signature')&&e.schema==='netclaw.ncfed.cluster-manifest.v1'&&exact(e.signature,'algorithm key_id value')&&e.signature.algorithm==='ecdsa-p256-sha256'&&e.signature.key_id===value.anchor_key_id,'invalid_manifest_signature');
 const anchor=certificate(value.anchor_certificate,now);check(await digest(anchor)===value.anchor_key_id,'manifest_anchor_mismatch');
 const key=await globalThis.crypto.subtle.importKey('spki',anchor,{name:'ECDSA',namedCurve:'P-256'},false,['verify']);
 check(await globalThis.crypto.subtle.verify({name:'ECDSA',hash:'SHA-256'},key,rawSignature(e.signature.value),bytes('netclaw.ncfed.ha/manifest/v1\0'+clusterCanonical({schema:e.schema,manifest:e.manifest}))),'invalid_manifest_signature');
 const m=e.manifest;check(exact(m,'schema_version cluster_id generation organization revision nodes limits')&&m.schema_version===1&&m.cluster_id===value.cluster_id&&m.generation===value.generation&&identifier(m.organization)&&m.revision===value.manifest_revision&&Array.isArray(m.nodes)&&m.nodes.length>=1&&m.nodes.length<=3);
 const seen={node_id:new Set(),installation_id:new Set(),key_id:new Set()};
 for(const node of m.nodes){check(exact(node,'node_id installation_id identity key_id certificate role endpoints')&&uuid(node.node_id)&&uuid(node.installation_id)&&node.installation_id!==m.cluster_id&&identifier(node.identity)&&hash(node.key_id)&&node.role==='border');for(const field of Object.keys(seen)){check(!seen[field].has(node[field]),'duplicate_node_identity');seen[field].add(node[field]);}check(await digest(certificate(node.certificate,now))===node.key_id,'node_key_mismatch');check(exact(node.endpoints,'cluster in2n https wss'));address(node.endpoints.cluster);address(node.endpoints.in2n);endpoint(node.endpoints.https,'https');endpoint(node.endpoints.wss,'wss');}
 const l=m.limits;check(exact(l,'leader_lease_s renewal_s admission_ms clock_uncertainty_ms max_operations max_members')&&integer(l.leader_lease_s,6,60)&&integer(l.renewal_s,1,Math.floor(l.leader_lease_s/3))&&integer(l.admission_ms,100,10000)&&integer(l.clock_uncertainty_ms,0,1000)&&integer(l.max_operations,1,1024)&&integer(l.max_members,1,32));
 const selected=m.nodes.find(n=>n.node_id===value.node_id);check(selected&&selected.installation_id===value.installation_id&&(!installationId||installationId===value.installation_id),'cluster_node_changed');
 if(origin)check(endpoint(selected.endpoints.https,'https')===endpoint(origin,'https'),'untrusted_cluster_endpoint');
 const a=value.authority;check(exact(a,'state leader_node_id epoch observed_at_ms')&&['leader','follower','no_quorum','fenced','retired'].includes(a.state)&&integer(a.observed_at_ms)&& (a.leader_node_id===null||uuid(a.leader_node_id)&&m.nodes.some(n=>n.node_id===a.leader_node_id))&&(a.epoch===null||integer(a.epoch,1)));
 check(!['leader','follower'].includes(a.state)||a.leader_node_id!==null&&a.epoch!==null);check(a.state!=='leader'||a.leader_node_id===value.node_id);
 const manifestHash=await digest(bytes(clusterCanonical(m)));
 if(pin)check(m.revision>=pin.manifest_revision,'stale_manifest');
 if(pin&&m.revision===pin.manifest_revision)check(manifestHash===pin.manifest_sha256,'manifest_revision_conflict');
 return {descriptor:structuredClone(value),pin:{cluster_id:m.cluster_id,generation:m.generation,anchor_key_id:value.anchor_key_id,manifest_revision:m.revision,manifest_sha256:manifestHash}};
}
export function clusterAudience(cluster, principal) {check(cluster&&uuid(cluster.cluster_id)&&uuid(cluster.generation)&&identifier(principal?.issuer)&&identifier(principal?.subject));return `cluster.${cluster.cluster_id}.${cluster.generation}.${encodeURIComponent(principal.issuer)}.${encodeURIComponent(principal.subject)}`;}
export function clusterReviewMatches(cluster, review, principal) {
 const c=review?.cluster,node=cluster?.manifest?.manifest?.nodes?.find(n=>n.node_id===c?.issuer_node_id);
 return Boolean(c&&exact(c,'cluster_id generation manifest_revision issuer_node_id authority_epoch')&&c.cluster_id===cluster.cluster_id&&c.generation===cluster.generation&&integer(c.manifest_revision,1,cluster.manifest_revision)&&integer(c.authority_epoch,1)&&node&&review.border?.installation_id===node.installation_id&&review.border?.key_id===node.key_id&&(!principal||clusterCanonical(review.principal)===clusterCanonical(principal)));
}
export const clusterCanAdmit = c => !c || ['leader','follower'].includes(c.authority?.state)&&integer(c.authority?.epoch,1);
export const clusterCanDecide = (c,op) => !c || clusterCanAdmit(c)&&clusterReviewMatches(c,op?.review)&&op.review.cluster.authority_epoch===c.authority.epoch;
export function clusterStatusText(c) {if(!c)return '';const a=c.authority;return ({leader:'This Border holds execution authority.',follower:'This Border forwards protected requests to the current authority.',no_quorum:'Quorum is unavailable. New protected work is stopped; retained results remain recoverable.',fenced:'This cluster is fenced. New protected work is stopped.',retired:'This Border is retired. Select a trusted active cluster endpoint.'})[a?.state]||'Cluster authority is unavailable.';}
export function clusterErrorMessage(code) {return ({no_quorum:'Quorum is unavailable. Recover the same operation after authority returns.',quorum_unavailable:'Quorum is unavailable. Recover the same operation after authority returns.',stale_authority:'Authority changed. Recover the same operation and review its current state.',stale_review:'This review belongs to an earlier authority. Recover the same operation; no decision was resent.',cluster_changed:'Cluster identity or generation changed. The original references are preserved.',node_retired:'This Border is retired. Select an enrolled cluster endpoint.',stale_manifest:'The endpoint advertised an older cluster manifest. The saved binding is preserved.'})[code];}
export async function clusterLabPrincipal(clusterId) {
 check(uuid(clusterId));const prefix=Uint8Array.from(clusterId.replaceAll('-','').match(/../g),v=>parseInt(v,16)),name=bytes('netclaw.open-lab.operator'),input=new Uint8Array(prefix.length+name.length);input.set(prefix);input.set(name,prefix.length);
 const raw=new Uint8Array(await globalThis.crypto.subtle.digest('SHA-1',input)).slice(0,16);raw[6]=(raw[6]&15)|80;raw[8]=(raw[8]&63)|128;const h=hex(raw),subject=[h.slice(0,8),h.slice(8,12),h.slice(12,16),h.slice(16,20),h.slice(20)].join('-');
 return {issuer:'open-lab',subject,display_name:'Unauthenticated lab operator',roles:['lab-operator']};
}
export async function verifyClusterRuntime(runtime, options) {
 check(runtime?.role==='border'&&runtime.kind==='openclaw'&&runtime.access?.mode==='open-lab'&&runtime.capabilities?.protectedOperations===true&&runtime.capabilities?.protectedProduction===true,'invalid_cluster_runtime');
 const result=await verifyClusterDescriptor(runtime.cluster,{...options,installationId:runtime.installationId});
 check(clusterCanonical(runtime.access.principal)===clusterCanonical(await clusterLabPrincipal(result.descriptor.cluster_id)),'cluster_principal_changed');return result;
}
