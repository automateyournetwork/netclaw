import fs from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
export function logSources(home) {
  const source = (id,name,file,command) => ({id,name,file,command,kind:'file'});
  return [
    source('gateway','Gateway',path.join(home,'.openclaw/logs/gateway.log'),'tail -n 200 ~/.openclaw/logs/gateway.log'),
    source('gateway-errors','Gateway errors',path.join(home,'.openclaw/logs/gateway.err.log'),'tail -n 200 ~/.openclaw/logs/gateway.err.log'),
    source('mesh','BGP / federation','/tmp/bgp-daemon-v2.log','tail -n 200 /tmp/bgp-daemon-v2.log'),
    source('ngrok','ngrok mesh','/tmp/ngrok-mesh.log','tail -n 200 /tmp/ngrok-mesh.log'),
    source('openshell-build','OpenShell sandbox build','/tmp/sandbox-build.log','tail -n 200 /tmp/sandbox-build.log'),
    source('defenseclaw','DefenseClaw',path.join(home,'.defenseclaw/gateway.log'),'tail -n 200 ~/.defenseclaw/gateway.log'),
    ...[['gateway-journal','Gateway journal','openclaw-gateway.service'],['mesh-journal','Mesh journal','netclaw-mesh.service'],['defenseclaw-journal','DefenseClaw journal','defenseclaw-sidecar.service']].map(([id,name,unit])=>({id,name,unit,kind:'journal',command:`journalctl --user -u ${unit} -n 200 --no-pager`}))
  ];
}
export function redactLogs(value) {
  return value.replace(/-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?(?:-----END [^-]*PRIVATE KEY-----|$)/g,'[PRIVATE KEY REDACTED]')
    .split('\n').map(line => /(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|enrollment[_-]?token|password|passwd|secret|authorization|cookie)\s*["']?\s*[:=]/i.test(line) || /\bBearer\s+\S+/i.test(line) ? '[Sensitive log line redacted]' : line.replace(/https?:\/\/[^\s]+/g,url=>url.replace(/\/\/[^/@\s]+:[^/@\s]+@/,'//[redacted]@').replace(/\?[^\s]*/,'?[query redacted]'))).join('\n');
}
export function logRows(content, {query='',severity='all'}={}) {
  return redactLogs(content).split('\n').filter(Boolean).map((line,i)=>{
    let payload;try{payload=JSON.parse(line);}catch{}
    const level=String(payload?.level||payload?.lvl||payload?.severity||'').toLowerCase();
    const inferred=/\b(emerg|alert|crit|fatal|error|err)\b/i.test(level||line)?'error':/\b(warning|warn)\b/i.test(level||line)?'warning':/\bdebug\b/i.test(level||line)?'debug':/\binfo\b/i.test(level||line)?'info':'unknown';
    return {id:i,severity:inferred,timestamp:String(payload?.timestamp||payload?.time||payload?.t||line.match(/^\d{4}-\d\d-\d\d[T ][\d:.+Z-]+/)?.[0]||''),message:line.slice(0,8192)};
  }).filter(row=>(severity==='all'||row.severity===severity)&&row.message.toLowerCase().includes(query.toLowerCase())).slice(-250);
}
export function tailFile(file) {
  const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
  try {const stat=fs.fstatSync(fd);if(!stat.isFile())throw Error('Not a regular log');const length=Math.min(stat.size,256*1024),buffer=Buffer.alloc(length);fs.readSync(fd,buffer,0,length,stat.size-length);const text=buffer.toString('utf8');return {content:stat.size>length?text.slice(text.indexOf('\n')+1):text,truncated:stat.size>length};}finally{fs.closeSync(fd);}
}
const journal = unit => new Promise((resolve,reject)=>execFile('journalctl',['--user','-u',unit,'-n','250','--no-pager','-o','short-iso'],{timeout:5000,maxBuffer:512*1024},(e,stdout)=>e?reject(e):resolve({content:stdout,truncated:true})));
export function mountLogs(app,home,{readFile=tailFile,readJournal=journal,runtimeHome}={}) {
  const sources=logSources(home).map(s => runtimeHome && s.file?.startsWith(path.join(home,'.openclaw') + path.sep) ? {...s,file:path.join(runtimeHome,path.relative(path.join(home,'.openclaw'),s.file))} : s);let active=0;
  app.get('/api/hud/logs',(_req,res)=>res.json({sources:sources.map(({file,unit,...s})=>s)}));
  app.get('/api/hud/logs/:id',async(req,res)=>{
    res.setHeader('Cache-Control','no-store');
    const source=sources.find(s=>s.id===req.params.id);if(!source)return res.status(404).json({error:'Unknown log source'});
    const query=req.query.q||'',severity=req.query.severity||'all';
    if(typeof query!=='string'||query.length>200||!['all','error','warning','info','debug','unknown'].includes(severity))return res.status(400).json({error:'Invalid log filter'});
    if(active>=2)return res.status(429).json({error:'Log reader busy'});active++;
    try {const data=source.kind==='file'?await readFile(source.file):await readJournal(source.unit);res.json({available:true,source:source.id,rows:logRows(data.content,{query,severity}),truncated:data.truncated,readAt:new Date().toISOString(),scope:'Latest bounded tail, not the complete log. Severity is parsed or inferred. Credential-pattern redaction is best effort.'});}
    catch {res.status(503).json({available:false,error:'Log unavailable on this host or permission denied. Use the documented service command.'});}finally{active--;}
  });
}
