import { openSync, closeSync, fstatSync, lstatSync, readFileSync, constants } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { createHash } from 'node:crypto';

// Coordinator launch pins only. No MCP or HTTP argument can choose an export.
const pins = Object.freeze({ path: process.env.NETCLAW_GENIE_APPROVED_PROJECTION,
  sha256: process.env.NETCLAW_GENIE_APPROVED_PROJECTION_SHA256 });
function requireValue(ok, code) { if (!ok) { const e=new Error(code); e.code=code; throw e; } }
const canonical = v => Array.isArray(v) ? v.map(canonical) : v && typeof v==='object'
  ? Object.fromEntries(Object.keys(v).sort().map(k=>[k,canonical(v[k])])) : v;
const digest = v => createHash('sha256').update(JSON.stringify(canonical(v))).digest('hex');
export function readApprovedProjection(config = pins) {
  if (!config.path && !config.sha256) return null;
  requireValue(typeof config.path==='string' && resolve(config.path)===config.path && /^[a-f0-9]{64}$/.test(config.sha256||''),'approved_projection_pin_required');
  for(let p=config.path;p!==dirname(p);p=dirname(p)) requireValue(!lstatSync(p).isSymbolicLink(),'approved_projection_symlink');
  const fd=openSync(config.path,constants.O_RDONLY|constants.O_NOFOLLOW);
  let bytes;
  try {
    const s=fstatSync(fd); requireValue(s.isFile()&&s.uid===process.getuid()&&!(s.mode&0o077)&&s.nlink===1&&s.size>0&&s.size<=16384,'approved_projection_private_file');
    bytes=readFileSync(fd);const after=fstatSync(fd);
    requireValue(after.size===s.size&&after.mtimeMs===s.mtimeMs&&bytes.length===s.size,'approved_projection_changed');
  } finally {closeSync(fd);}
  requireValue(createHash('sha256').update(bytes).digest('hex')===config.sha256,'approved_projection_changed');
  const grant=JSON.parse(bytes);
  requireValue(Object.keys(grant).every(k=>['schema','authorized','authorization_ref','projection'].includes(k))&&grant.schema===1&&grant.authorized===true&&typeof grant.authorization_ref==='string'&&grant.authorization_ref.length>0,'approved_projection_authorization');
  const p=grant.projection;
  requireValue(p&&Object.keys(p).every(k=>['classification','snapshot_ref','manifest_sha256','style_id','text','event_id','event_text','event_send_count','sha256'].includes(k))&&p.classification==='private_derived','approved_projection_schema');
  requireValue(/^[a-z0-9-]{1,96}$/.test(p.snapshot_ref||'')&&/^[a-f0-9]{64}$/.test(p.manifest_sha256||'')&&['blueprint','fantasy','network-city','packet-scale','data-center'].includes(p.style_id),'approved_projection_source');
  requireValue(typeof p.text==='string'&&p.text.length>0&&Buffer.byteLength(p.text)<=10000&&typeof p.event_text==='string'&&Buffer.byteLength(p.event_text)<=1500&&p.event_id==='snapshot-link-amber-v1'&&[1,10].includes(p.event_send_count),'approved_projection_bounds');
  requireValue(!/\b(?:\d{1,3}\.){3}\d{1,3}\b|BEGIN.*PRIVATE KEY|\b(?:password|secret|username)\s*[:=]/i.test(p.text+' '+p.event_text),'approved_projection_sensitive_text');
  const {sha256,...body}=p;requireValue(digest(body)===sha256,'approved_projection_digest');
  return structuredClone(p);
}
